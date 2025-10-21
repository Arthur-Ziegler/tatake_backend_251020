# API Layer Architecture Specification Changes

## MODIFIED Requirements

### Requirement: Unified Response Format
系统 SHALL实现统一的API响应格式，确保前端一致性。所有端点必须使用相同的响应结构。

#### Scenario: Standard Response Structure
- **GIVEN** 需要统一的响应格式
- **WHEN** 设计API响应时
- **THEN** 系统 SHALL使用以下格式：
  ```json
  {
    "code": 200,
    "data": {...},
    "message": "success"
  }
  ```
- **AND** `code` 字段必须是整数类型的 HTTP 状态码
- **AND** `data` 字段必须包含所有业务数据
- **AND** `message` 字段在成功时为 "success"，失败时为具体错误描述
- **AND** 不再包含 `timestamp` 和 `traceId` 字段

#### Scenario: Error Response Format
- **GIVEN** 需要统一的错误响应格式
- **WHEN** 处理API错误时
- **THEN** 错误响应 SHALL使用以下格式：
  ```json
  {
    "code": 4xx或5xx,
    "data": null,
    "message": "具体的错误描述"
  }
  ```
- **AND** `code` 字段必须与 HTTP 响应状态码一致
- **AND** `data` 字段必须为 null
- **AND** `message` 字段必须包含人类可读的错误信息

### Requirement: Authentication Module
系统 SHALL实现简化的认证系统API，统一为微信单一登录方式。

#### Scenario: Guest User System
- **GIVEN** 需要降低用户使用门槛
- **WHEN** 实现认证系统时
- **THEN** 系统 SHALL支持游客模式：
  - `POST /api/v1/auth/guest/init` - 游客账号初始化（无需任何参数）
  - `POST /api/v1/auth/guest/upgrade` - 游客账号升级（需要 access_token 和 wechat_openid）
- **AND** 游客初始化 SHALL每次创建全新的随机身份
- **AND** 游客升级 SHALL将游客转换为正式微信用户

#### Scenario: WeChat Authentication
- **GIVEN** 需要支持微信认证
- **WHEN** 实现登录功能时
- **THEN** 系统 SHALL提供：
  - `POST /api/v1/auth/register` - 微信账号注册（需要 wechat_openid）
  - `POST /api/v1/auth/login` - 微信账号登录（需要 wechat_openid）
  - `POST /api/v1/auth/refresh` - 刷新访问令牌（需要 refresh_token）
- **AND** 注册时 SHALL检查 wechat_openid 唯一性
- **AND** 登录时 SHALL验证用户存在性，不自动创建新用户
- **AND** 所有认证端点 SHALL返回 user_id, access_token, refresh_token

## REMOVED Requirements

### Requirement: Multi-Method Authentication
**原因**：简化认证流程，统一为微信单一登录方式

**受影响的场景**：
- 移除手机号 + 短信验证码登录
- 移除邮箱 + 验证码登录
- 移除 Apple ID 登录
- 只保留微信 OpenID 登录和游客模式

### Requirement: SMS Verification
**原因**：不再支持手机号登录，SMS 验证功能不再需要

**受影响的端点**：
- 删除 `POST /api/v1/auth/sms/send` 端点
- 移除所有短信验证相关的 API 功能

### Requirement: User Logout
**原因**：简化系统设计，移除登出功能

**受影响的端点**：
- 删除 `POST /api/v1/auth/logout` 端点
- 移除 token 黑名单管理功能

### Requirement: User Info Query in Auth
**原因**：认证领域不负责用户信息管理

**受影响的端点**：
- 删除 `GET /api/v1/auth/user-info` 端点
- 用户信息查询应由独立的 user 领域提供
