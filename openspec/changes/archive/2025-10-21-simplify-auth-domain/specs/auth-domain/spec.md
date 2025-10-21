# 认证领域规范

## ADDED Requirements

### Requirement: 游客账号初始化
系统 SHALL 支持无需任何用户输入的游客账号初始化功能。每次初始化都 MUST 创建全新的随机游客身份，不依赖设备信息或任何客户端标识。

#### Scenario: 成功初始化游客账号
- **WHEN** 客户端调用 `POST /api/v1/auth/guest/init` 且不传递任何参数
- **THEN** 系统创建新的游客用户记录（is_guest=true, wechat_openid=null）
- **AND** 返回 HTTP 200 响应，包含 user_id, access_token, refresh_token
- **AND** 响应格式为 `{ "code": 200, "data": {...}, "message": "success" }`

#### Scenario: 游客账号的唯一性
- **WHEN** 同一客户端多次调用游客初始化接口
- **THEN** 每次调用都必须返回不同的 user_id
- **AND** 系统不应尝试识别或重用已有的游客账号

### Requirement: 微信账号注册
系统 SHALL 支持通过微信 OpenID 注册新用户。注册时 MUST 检查 OpenID 唯一性，防止重复注册。

**实现说明**：微信注册在内部实现上等同于"创建游客 + 立即升级"的组合操作。这一设计应在代码注释和 API 文档中明确说明。

#### Scenario: 成功注册新用户
- **WHEN** 客户端调用 `POST /api/v1/auth/register` 并传递有效的 wechat_openid
- **AND** 该 wechat_openid 在系统中不存在
- **THEN** 系统创建新用户（is_guest=false, wechat_openid=传入值）
- **AND** 返回 HTTP 200 响应，包含 user_id, access_token, refresh_token
- **AND** 响应格式为 `{ "code": 200, "data": {...}, "message": "success" }`

#### Scenario: 重复注册检测
- **WHEN** 客户端尝试注册一个已存在的 wechat_openid
- **THEN** 系统返回 HTTP 409 响应
- **AND** 响应格式为 `{ "code": 409, "data": null, "message": "该微信账号已注册" }`
- **AND** 不创建新的用户记录

### Requirement: 微信账号登录
系统 SHALL 支持通过微信 OpenID 登录已注册用户。登录时 MUST 验证用户存在性，不自动创建新用户。

#### Scenario: 成功登录已有用户
- **WHEN** 客户端调用 `POST /api/v1/auth/login` 并传递有效的 wechat_openid
- **AND** 该 wechat_openid 对应的用户存在
- **THEN** 系统更新用户的 last_login_at 字段
- **AND** 返回 HTTP 200 响应，包含 user_id, access_token, refresh_token
- **AND** 响应格式为 `{ "code": 200, "data": {...}, "message": "success" }`

#### Scenario: 登录不存在的用户
- **WHEN** 客户端尝试登录一个不存在的 wechat_openid
- **THEN** 系统返回 HTTP 404 响应
- **AND** 响应格式为 `{ "code": 404, "data": null, "message": "用户不存在，请先注册" }`
- **AND** 不自动创建新用户

### Requirement: 游客账号升级
系统 SHALL 支持将游客账号升级为正式微信用户。升级时 MUST 验证当前用户身份、游客状态和 OpenID 唯一性。

#### Scenario: 成功升级游客账号
- **WHEN** 游客用户调用 `POST /api/v1/auth/guest/upgrade` 并在 Header 中携带有效的 access_token
- **AND** 请求体包含有效的 wechat_openid
- **AND** 当前用户确实是游客（is_guest=true）
- **AND** 该 wechat_openid 未被其他用户使用
- **THEN** 系统更新用户信息：is_guest=false, wechat_openid=传入值, jwt_version+=1
- **AND** 返回 HTTP 200 响应，包含 user_id, access_token, refresh_token（新token）
- **AND** 响应格式为 `{ "code": 200, "data": {...}, "message": "success" }`
- **AND** 旧的 access_token 和 refresh_token 因 jwt_version 变更而失效

#### Scenario: 非游客用户尝试升级
- **WHEN** 已注册用户（is_guest=false）尝试调用升级接口
- **THEN** 系统返回 HTTP 403 响应
- **AND** 响应格式为 `{ "code": 403, "data": null, "message": "当前用户不是游客" }`

#### Scenario: 升级时 OpenID 已被使用
- **WHEN** 游客用户尝试升级，但提供的 wechat_openid 已被其他用户占用
- **THEN** 系统返回 HTTP 409 响应
- **AND** 响应格式为 `{ "code": 409, "data": null, "message": "该微信账号已被使用" }`

#### Scenario: 未认证用户尝试升级
- **WHEN** 客户端调用升级接口但未提供 access_token 或 token 无效
- **THEN** 系统返回 HTTP 401 响应
- **AND** 响应格式为 `{ "code": 401, "data": null, "message": "认证令牌无效或已过期" }`

### Requirement: 访问令牌刷新
系统 SHALL 支持使用 refresh_token 获取新的 access_token。刷新时 MUST 验证 refresh_token 的有效性和 jwt_version 一致性。

#### Scenario: 成功刷新令牌
- **WHEN** 客户端调用 `POST /api/v1/auth/refresh` 并传递有效的 refresh_token
- **AND** 该 refresh_token 未过期且 jwt_version 与用户当前版本一致
- **THEN** 系统生成新的 access_token 和 refresh_token
- **AND** 返回 HTTP 200 响应，包含 user_id, access_token, refresh_token
- **AND** 响应格式为 `{ "code": 200, "data": {...}, "message": "success" }`

#### Scenario: 刷新令牌无效或过期
- **WHEN** 客户端尝试使用无效、过期或被撤销的 refresh_token
- **THEN** 系统返回 HTTP 401 响应
- **AND** 响应格式为 `{ "code": 401, "data": null, "message": "refresh_token 无效或已过期" }`

#### Scenario: JWT 版本不匹配
- **WHEN** 客户端使用的 refresh_token 中的 jwt_version 与数据库中的不一致
- **THEN** 系统返回 HTTP 401 响应
- **AND** 响应格式为 `{ "code": 401, "data": null, "message": "令牌版本不匹配" }`

### Requirement: 统一响应格式
所有认证领域的 API 端点 MUST 使用统一的响应格式，便于客户端统一处理。

#### Scenario: 成功响应格式
- **WHEN** 任何认证 API 调用成功
- **THEN** 响应必须符合以下 JSON 结构：
  ```json
  {
    "code": 200,
    "data": { /* 业务数据 */ },
    "message": "success"
  }
  ```
- **AND** `code` 字段必须是整数类型的 HTTP 状态码
- **AND** `data` 字段必须是对象类型（object），包含具体的业务数据
- **AND** `message` 字段在成功时必须为字符串 "success"

#### Scenario: 错误响应格式
- **WHEN** 任何认证 API 调用失败
- **THEN** 响应必须符合以下 JSON 结构：
  ```json
  {
    "code": 4xx或5xx,
    "data": null,
    "message": "具体的错误描述"
  }
  ```
- **AND** `code` 字段必须是对应的 HTTP 错误状态码
- **AND** `data` 字段必须为 null
- **AND** `message` 字段必须包含人类可读的错误描述

### Requirement: JWT 令牌结构
系统生成的 JWT 令牌 MUST 包含特定的标准字段，用于身份验证和令牌管理。

#### Scenario: Access Token 结构
- **WHEN** 系统生成 access_token
- **THEN** token payload 必须包含以下字段：
  - `sub`: 用户 ID（UUID 字符串）
  - `is_guest`: 是否为游客（boolean）
  - `jwt_version`: JWT 版本号（integer）
  - `token_type`: "access"（string）
  - `exp`: 过期时间戳（30分钟后）
  - `iat`: 签发时间戳
  - `jti`: token 唯一标识（UUID 字符串）

#### Scenario: Refresh Token 结构
- **WHEN** 系统生成 refresh_token
- **THEN** token payload 必须包含与 access_token 相同的字段
- **AND** `token_type` 字段必须为 "refresh"
- **AND** `exp` 字段必须设置为 7 天后

### Requirement: 数据库表结构
系统 MUST 使用简化的 `auth` 表存储所有用户的认证信息，只包含身份认证所需的核心字段。

#### Scenario: Auth 表字段定义
- **WHEN** 系统创建或查询用户记录
- **THEN** auth 表必须包含且仅包含以下字段：
  - `id`: UUID 类型，主键
  - `wechat_openid`: String(100)，可为 null，唯一索引（游客为 null，正式用户有值）
  - `is_guest`: Boolean，是否为游客
  - `created_at`: DateTime(timezone=True)，创建时间
  - `updated_at`: DateTime(timezone=True)，更新时间
  - `last_login_at`: DateTime(timezone=True)，最后登录时间
  - `jwt_version`: Integer，JWT 版本号，默认为 1

#### Scenario: 索引设计
- **WHEN** 系统执行用户查询操作
- **THEN** auth 表必须包含以下索引以优化查询性能：
  - `idx_auth_wechat_openid`: UNIQUE INDEX ON (wechat_openid)
  - `idx_auth_is_guest`: INDEX ON (is_guest)
  - `idx_auth_created_at`: INDEX ON (created_at)

### Requirement: 审计日志
系统 MUST 记录所有认证相关的操作日志，用于安全审计和问题排查。

#### Scenario: 记录成功的认证操作
- **WHEN** 用户成功完成任何认证操作（初始化、注册、登录、升级、刷新）
- **THEN** 系统必须在 auth_audit_logs 表中创建日志记录
- **AND** 日志必须包含：user_id, action（操作类型）, result（"success"）, ip_address, user_agent, created_at

#### Scenario: 记录失败的认证操作
- **WHEN** 用户的认证操作失败（如登录失败、升级被拒绝）
- **THEN** 系统必须在 auth_audit_logs 表中创建日志记录
- **AND** 日志必须包含：user_id（如有）, action, result（"failure"）, details（失败原因）, ip_address, user_agent, created_at

## REMOVED Requirements

### Requirement: 短信验证码登录
**原因**：简化认证流程，统一为微信单一登录方式

**迁移路径**：
- 删除 `POST /api/v1/auth/sms/send` 端点
- 删除 `auth_sms_verification` 数据库表
- 移除所有 SMS 相关的 Service 和 Repository 代码
- 客户端必须更新为使用微信登录

### Requirement: 密码登录
**原因**：简化认证流程，统一为微信单一登录方式

**迁移路径**：
- 从 LoginRequest schema 中移除 password 字段
- 从 auth 表中移除 password_hash 字段
- 移除密码相关的加密和验证逻辑
- 现有密码登录用户需引导绑定微信账号

### Requirement: Apple ID 登录
**原因**：简化认证流程，统一为微信单一登录方式

**迁移路径**：
- 从 LoginRequest 和 GuestUpgradeRequest schema 中移除 apple_id_token 字段
- 从 auth 表中移除 apple_id 相关字段
- 现有 Apple ID 用户需引导绑定微信账号

### Requirement: 基于设备信息的游客识别
**原因**：设备信息不可靠，易伪造和碰撞，改为每次创建新随机游客

**迁移路径**：
- 从 GuestInitRequest schema 中移除 device_info 字段
- 从 auth 表中移除 device_id, device_type 字段
- 客户端负责在本地保存游客的 user_id 和 token

### Requirement: 用户信息查询
**原因**：认证领域不应负责用户资料管理，应由独立的 user 领域提供

**迁移路径**：
- 删除 `GET /api/v1/auth/user-info` 端点
- 从 auth 表中移除 nickname, avatar, phone, email 等字段
- 创建独立的 user 领域和 `/api/v1/users/{user_id}` 端点
- 客户端改为调用 user 领域的接口获取用户信息

### Requirement: 用户登出
**原因**：简化系统设计，移除 token 黑名单机制，依赖 token 自然过期

**迁移路径**：
- 删除 `POST /api/v1/auth/logout` 端点
- 删除 auth_token_blacklist 数据库表
- 删除 auth_user_sessions 数据库表
- 客户端通过删除本地 token 实现登出效果
- 如需强制失效，通过增加用户的 jwt_version 实现

### Requirement: 用户设置管理
**原因**：用户设置不属于认证领域职责

**迁移路径**：
- 删除 auth_user_settings 数据库表
- 将设置数据迁移到 user 领域或专门的 settings 领域

### Requirement: 积分和等级系统
**原因**：积分系统不属于认证领域职责

**迁移路径**：
- 从 auth 表中移除 total_points, available_points, level, experience_points 字段
- 创建独立的 points 或 gamification 领域管理积分
- 客户端改为调用专门的积分领域接口
