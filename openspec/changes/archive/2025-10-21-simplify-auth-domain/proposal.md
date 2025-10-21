# 简化认证领域架构

## Why

当前认证领域过于复杂，支持多种登录方式（手机号+验证码、密码、微信、Apple ID），管理大量用户信息（昵称、头像、积分、等级），并且游客初始化需要上传设备信息作为唯一标识。这导致：

1. **职责不清**：认证领域混杂了用户资料管理、积分系统、设备管理等非核心职责
2. **复杂度高**：维护多套认证流程，SMS验证码服务、多表关联查询增加维护成本
3. **安全隐患**：将设备信息作为游客身份标识，容易产生碰撞和被滥用
4. **响应格式不统一**：不同端点返回格式不一致，缺乏标准化

需要将认证领域简化为纯粹的身份认证职责，统一为单一微信登录方式，移除所有非核心功能。

## What Changes

### 核心变更

1. **游客初始化简化**
   - 移除所有设备信息参数，游客初始化不接受任何输入
   - 每次请求创建全新的随机游客身份，不再基于设备信息查找已有账号
   - 服务端记录创建时间和登录时间，客户端自行管理本地游客标识

2. **统一为微信单一登录**
   - **BREAKING**: 移除手机号+验证码登录
   - **BREAKING**: 移除密码登录
   - **BREAKING**: 移除Apple ID登录
   - **BREAKING**: 删除 `/api/v1/auth/sms/send` 端点
   - 只保留微信 OpenID 作为唯一身份标识
   - 明确区分注册和登录两个独立端点

3. **响应格式统一化**
   - 所有端点统一使用格式：`{ "code": 200, "data": {...}, "message": "success" }`
   - `code` 使用标准 HTTP 状态码
   - 成功时 `message` 为 `"success"`，失败时为具体错误描述
   - 所有认证端点（包括刷新）统一返回 `user_id`, `access_token`, `refresh_token`

4. **数据库表结构简化**
   - **BREAKING**: 将 `auth_users` 表重命名为 `auth` 表
   - **BREAKING**: 删除字段：`phone`, `email`, `password_hash`, `nickname`, `avatar`, `total_points`, `available_points`, `level`, `experience_points`, `device_id`, `device_type`, `username`, `wechat_unionid`
   - 保留字段：`id`, `wechat_openid`, `is_guest`, `created_at`, `updated_at`, `last_login_at`, `jwt_version`
   - **BREAKING**: 删除表：`auth_sms_verification`, `auth_token_blacklist`, `auth_user_sessions`, `auth_user_settings`
   - 保留 `auth_audit_logs` 表用于审计

5. **功能调整**
   - **BREAKING**: 移除用户登出功能（删除 `/api/v1/auth/logout` 端点）
   - **BREAKING**: 移除用户信息查询功能（删除 `/api/v1/auth/user-info` 端点）
   - 保留游客升级功能，升级时需要提供游客的 access_token 和微信 openid
   - 保留令牌刷新功能

6. **微信注册流程说明**
   - 微信注册本质上是"先创建游客 + 立即升级"的组合操作
   - 内部实现：自动创建游客账号，然后用微信 openid 完成升级
   - 这一设计在代码注释和文档中需要明确说明

## Impact

### 受影响的规范
- `auth-domain` - 核心认证领域规范需要完全重写
- `api-layer-architecture` - API 响应格式需要更新
- `api-layer-testing` - 测试用例需要更新以匹配新接口

### 受影响的代码
- `src/domains/auth/models.py` - 大幅简化数据模型
- `src/domains/auth/schemas.py` - 重写请求/响应 Schema
- `src/domains/auth/router.py` - 移除多个端点，简化保留端点
- `src/domains/auth/service.py` - 移除 SMS 服务、登出逻辑、用户信息查询
- `src/domains/auth/repository.py` - 简化数据访问层
- `src/domains/auth/database.py` - 数据库迁移脚本
- `src/domains/auth/tests/*` - 所有测试需要重写
- `src/api/main.py` - 更新响应格式中间件
- `src/api/responses.py` - 统一响应格式工具

### 迁移影响
- **数据库迁移**：需要提供脚本将现有用户数据迁移到新表结构
- **客户端适配**：所有调用认证 API 的客户端需要更新
- **不兼容变更**：这是一次完全的 breaking change，旧客户端无法继续使用

### 外部依赖变更
- 不再需要短信服务提供商
- 需要微信开放平台 API（用于验证 openid，可选）

### 风险
- **高风险变更**：移除多种登录方式可能影响部分用户
- **数据丢失风险**：昵称、头像、积分等数据需要迁移到其他领域
- **无法回滚**：数据库表结构变更后难以快速回滚

### 缓解措施
- 在其他领域（如 user 领域）准备好用户信息表
- 执行数据迁移前进行完整备份
- 分阶段部署，先部署后端，确认稳定后再要求客户端更新
