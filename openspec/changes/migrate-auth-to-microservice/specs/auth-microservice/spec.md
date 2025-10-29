## ADDED Requirements

### Requirement: 微服务认证透传
系统 SHALL实现认证微服务的HTTP透传层，自动注入project参数并转发所有请求到微服务。

#### Scenario: 微信认证注册
- **WHEN** 前端调用POST /auth/wechat/register
- **THEN** 系统自动添加project字段并转发到微服务
- **AND** 返回标准的认证令牌响应

#### Scenario: 邮箱验证码发送
- **WHEN** 前端调用POST /auth/email/send-code
- **THEN** 系统自动添加project字段并转发到微服务
- **AND** 返回验证码发送状态和过期时间

### Requirement: JWT本地验证
系统SHALL通过微服务公钥接口实现JWT令牌的本地验证，避免每次验证都调用微服务。

#### Scenario: JWT令牌验证
- **WHEN** 受保护的API端点收到JWT令牌
- **THEN** 系统使用微服务公钥验证令牌有效性
- **AND** 提取用户ID用于后续业务逻辑

#### Scenario: 公钥缓存更新
- **WHEN** JWT验证失败或公钥过期
- **THEN** 系统重新从微服务获取公钥
- **AND** 更新本地缓存

### Requirement: 邮箱认证集成
系统SHALL集成微服务的邮箱认证功能，支持邮箱验证码发送、注册、登录和绑定。

#### Scenario: 邮箱注册流程
- **WHEN** 用户请求邮箱验证码并完成注册
- **THEN** 系统通过微服务验证邮箱和验证码
- **AND** 创建正式用户账号并返回认证令牌

#### Scenario: 邮箱绑定流程
- **WHEN** 已登录用户请求绑定邮箱
- **THEN** 系统通过微服务验证邮箱验证码
- **AND** 将邮箱绑定到当前用户账号

### Requirement: API路径一致性
系统SHALL采用与微服务完全一致的API路径格式，确保前后端接口规范统一。

#### Scenario: 路径映射
- **WHEN** 前端调用认证相关API
- **THEN** 所有路径格式与微服务API文档一致
- **AND** 不存在任何路径转换或适配逻辑

### Requirement: 多租户配置
系统SHALL为所有认证请求自动注入project参数，值为"tatake_backend"，实现多租户数据隔离。

#### Scenario: 自动注入project
- **WHEN** 任何认证请求发送到微服务
- **THEN** 请求体自动包含"project": "tatake_backend"
- **AND** 前端无需手动传递此参数

## REMOVED Requirements

### Requirement: 本地认证数据库
**Reason**: 认证功能完全迁移到微服务，不再需要本地认证数据库。
**Migration**: 删除所有认证相关的表结构和数据访问代码。

### Requirement: 本地JWT生成
**Reason**: JWT令牌生成和验证由微服务负责，本地只做验证。
**Migration**: 删除JWT生成相关代码，保留验证逻辑。

### Requirement: 简化的认证逻辑
**Reason**: 原有简化认证功能被功能更丰富的微服务替代。
**Migration**: 删除所有本地认证服务实现。