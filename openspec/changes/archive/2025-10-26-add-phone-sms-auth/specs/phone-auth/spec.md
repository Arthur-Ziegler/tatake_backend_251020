# 手机号认证能力规格

## MODIFIED Requirements

### Requirement: Auth模型支持手机号字段
Auth表 MUST 新增phone字段，SHALL 实施手机号唯一性约束。

#### Scenario: 创建仅绑定手机号的用户
- **Given**: 无前置条件
- **When**: 创建 `Auth(phone="13800138000", is_guest=False)`
- **Then**:
  - 数据库成功插入
  - `wechat_openid` 为 NULL
  - `phone` 值为 `13800138000`

#### Scenario: 手机号唯一性约束
- **Given**: 已存在 `Auth(phone="13800138000")`
- **When**: 尝试创建另一个 `Auth(phone="13800138000")`
- **Then**: 抛出唯一性约束异常

#### Scenario: 通过手机号查询用户
- **Given**: 数据库存在 `Auth(phone="13800138000", id="user-123")`
- **When**: 查询 `Auth.filter_by(phone="13800138000")`
- **Then**: 返回 user_id=`user-123` 的记录

#### Scenario: 手机号和微信OpenID可同时存在
- **Given**: 无前置条件
- **When**: 创建 `Auth(phone="13800138000", wechat_openid="wx-openid-abc")`
- **Then**: 数据库成功插入，两个字段都有值

#### Scenario: 游客账号绑定手机号后升级
- **Given**: 存在游客账号 `Auth(id="user-123", is_guest=True, phone=NULL)`
- **When**: 更新 `phone="13800138000", is_guest=False`
- **Then**:
  - 用户升级为正式用户
  - `is_guest=False`
  - `phone` 有值

---

### Requirement: 手机号索引优化
系统 SHALL 为phone字段创建索引以提升查询性能。

#### Scenario: 索引创建成功
- **Given**: Auth表已创建
- **When**: 执行数据库迁移
- **Then**:
  - 存在索引 `idx_auth_phone`
  - EXPLAIN查询显示使用索引

#### Scenario: 手机号查询使用索引
- **Given**: 数据库中有10000条Auth记录
- **When**: 执行 `SELECT * FROM auth WHERE phone='13800138000'`
- **Then**:
  - 查询使用 `idx_auth_phone` 索引
  - 响应时间 < 10ms

---

## ADDED Requirements

### Requirement: AuthLog新增手机号相关审计类型
AuthLog MUST 记录手机号注册/登录/绑定等关键操作。

#### Scenario: 记录手机号注册审计
- **Given**: 用户通过手机号注册成功
- **When**: 插入 `AuthLog(action="phone_register", user_id="user-123", result="success")`
- **Then**:
  - 审计日志成功保存
  - 可通过 action 查询所有手机号注册记录

#### Scenario: 记录手机号登录审计
- **Given**: 用户通过手机号登录成功
- **When**: 插入 `AuthLog(action="phone_login", user_id="user-123", ip_address="1.2.3.4")`
- **Then**: 审计日志包含登录IP

#### Scenario: 记录手机号绑定审计
- **Given**: 游客账号绑定手机号成功
- **When**: 插入 `AuthLog(action="phone_bind", user_id="user-123", details="upgraded from guest")`
- **Then**: 审计日志记录详细信息

#### Scenario: 记录短信发送审计
- **Given**: 验证码发送成功
- **When**: 插入 `AuthLog(action="sms_send", details="phone=13800138000, scene=register")`
- **Then**: 审计日志记录发送场景

#### Scenario: 记录验证失败审计
- **Given**: 验证码验证失败
- **When**: 插入 `AuthLog(action="sms_verify_failed", result="failure", error_code="INVALID_CODE")`
- **Then**: 审计日志记录失败原因

---

### Requirement: JWT生成逻辑复用
手机号登录 MUST 复用现有JWT生成逻辑，payload SHALL NOT 区分登录方式。

#### Scenario: 手机号登录生成标准JWT
- **Given**: 用户通过手机号登录成功，user_id=`user-123`
- **When**: 调用 `generate_tokens(user_id="user-123", jwt_version=1)`
- **Then**:
  - 返回 `access_token` 和 `refresh_token`
  - payload 包含 `{"sub": "user-123", "jwt_version": 1}`
  - 不包含登录方式标识

#### Scenario: 微信登录和手机号登录JWT可互换
- **Given**:
  - 用户A通过微信登录获得 token_wechat
  - 用户A绑定手机号后通过手机号登录获得 token_phone
- **When**: 使用两个token访问受保护API
- **Then**: 两个token都能正常认证，访问相同资源

---

### Requirement: 手机号格式验证
系统 MUST 验证手机号为11位数字且以1开头。

#### Scenario: 有效手机号通过验证
- **Given**: 输入 `phone="13800138000"`
- **When**: 执行格式验证
- **Then**: 验证通过

#### Scenario: 非11位手机号被拒绝
- **Given**: 输入 `phone="138001380"`
- **When**: 执行格式验证
- **Then**: 抛出 `ValueError("手机号格式错误")`

#### Scenario: 包含非数字字符被拒绝
- **Given**: 输入 `phone="138-0013-8000"`
- **When**: 执行格式验证
- **Then**: 抛出 `ValueError("手机号格式错误")`

#### Scenario: 非1开头被拒绝
- **Given**: 输入 `phone="23800138000"`
- **When**: 执行格式验证
- **Then**: 抛出 `ValueError("手机号格式错误")`
