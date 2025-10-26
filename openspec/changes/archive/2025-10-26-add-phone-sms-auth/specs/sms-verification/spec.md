# 短信验证码功能规格

## ADDED Requirements

### Requirement: 短信验证码发送接口
系统 SHALL 提供发送6位数字验证码到指定手机号的接口，MUST 实现限流和锁定机制。

#### Scenario: 首次发送验证码成功
- **Given**: 手机号 `13800138000` 未发送过验证码
- **When**: POST `/auth/sms/send` with `{"phone": "13800138000", "scene": "register"}`
- **Then**:
  - 返回 200 `{"code": 200, "data": {"expires_in": 300, "retry_after": 60}}`
  - 数据库创建 `SMSVerification` 记录
  - 调用 SMS 客户端发送验证码
  - 审计日志记录 `sms_send` 操作

#### Scenario: 60秒内重复发送被拒绝
- **Given**: 手机号 `13800138000` 在30秒前已发送验证码
- **When**: POST `/auth/sms/send` with `{"phone": "13800138000", "scene": "login"}`
- **Then**: 返回 429 `{"code": 429, "message": "发送过于频繁，请稍后重试"}`

#### Scenario: 当日发送次数超限
- **Given**: 手机号 `13800138000` 今日已发送5次验证码
- **When**: POST `/auth/sms/send` with `{"phone": "13800138000", "scene": "bind"}`
- **Then**: 返回 429 `{"code": 429, "message": "今日发送次数已达上限"}`

#### Scenario: 被锁定手机号发送失败
- **Given**: 手机号 `13800138000` 因验证失败5次被锁定至未来1小时
- **When**: POST `/auth/sms/send` with `{"phone": "13800138000", "scene": "register"}`
- **Then**: 返回 423 `{"code": 423, "message": "账号已锁定，请1小时后重试"}`

#### Scenario: 手机号格式错误
- **Given**: 无前置条件
- **When**: POST `/auth/sms/send` with `{"phone": "138001380", "scene": "register"}`
- **Then**: 返回 400 `{"code": 400, "message": "手机号格式错误"}`

---

### Requirement: 短信验证码验证接口
系统 SHALL 提供手机号+验证码验证接口，MUST 支持注册/登录/绑定三种场景。

#### Scenario: 注册场景验证成功创建新用户
- **Given**:
  - 手机号 `13800138000` 已收到验证码 `123456`
  - 该手机号未注册过
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "123456", "scene": "register"}`
- **Then**:
  - 返回 200 `{"code": 200, "data": {"access_token": "...", "user_id": "...", "is_new_user": true}}`
  - 创建 `Auth` 记录：`is_guest=False, phone=13800138000`
  - 验证码标记为已使用：`verified=True, verified_at=now()`
  - 审计日志记录 `phone_register`

#### Scenario: 登录场景验证成功
- **Given**:
  - 手机号 `13800138000` 已注册且收到验证码 `654321`
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "654321", "scene": "login"}`
- **Then**:
  - 返回 200 `{"code": 200, "data": {"access_token": "...", "user_id": "...", "is_new_user": false}}`
  - 更新 `last_login_at`
  - 审计日志记录 `phone_login`

#### Scenario: 绑定场景验证成功并升级游客账号
- **Given**:
  - 用户已登录（JWT token），user_id=`user-123`, is_guest=True
  - 手机号 `13800138000` 已收到验证码 `888888`，未被其他账号绑定
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "888888", "scene": "bind"}` + JWT Header
- **Then**:
  - 返回 200 `{"code": 200, "data": {"user_id": "user-123", "phone": "13800138000", "upgraded": true}}`
  - 更新 `Auth`：`phone=13800138000, is_guest=False`
  - 审计日志记录 `phone_bind`

#### Scenario: 验证码错误累计5次锁定
- **Given**: 手机号 `13800138000` 已发送验证码 `123456`，当前 error_count=4
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "wrong", "scene": "login"}` (5次)
- **Then**:
  - 返回 401 `{"code": 401, "message": "验证码错误"}`
  - `error_count` 累加至 5
  - 设置 `locked_until = now() + 1小时`
  - 后续发送/验证均返回 423

#### Scenario: 验证码已过期
- **Given**: 手机号 `13800138000` 在6分钟前收到验证码 `123456`
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "123456", "scene": "register"}`
- **Then**: 返回 410 `{"code": 410, "message": "验证码已过期"}`

#### Scenario: 登录时手机号未注册
- **Given**: 手机号 `13900139000` 未注册过，但收到验证码 `111111`
- **When**: POST `/auth/sms/verify` with `{"phone": "13900139000", "code": "111111", "scene": "login"}`
- **Then**: 返回 404 `{"code": 404, "message": "手机号未注册"}`

#### Scenario: 注册时手机号已存在
- **Given**: 手机号 `13800138000` 已注册，但收到新验证码 `222222`
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "222222", "scene": "register"}`
- **Then**: 返回 409 `{"code": 409, "message": "手机号已注册"}`

#### Scenario: 绑定时手机号已被其他账号使用
- **Given**:
  - 当前用户 user_id=`user-123`
  - 手机号 `13800138000` 已绑定到 user_id=`user-456`
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "333333", "scene": "bind"}` + JWT(user-123)
- **Then**: 返回 409 `{"code": 409, "message": "手机号已被其他账号绑定"}`

#### Scenario: 绑定时未提供JWT认证
- **Given**: 手机号 `13800138000` 收到验证码 `444444`
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "444444", "scene": "bind"}` (无 JWT Header)
- **Then**: 返回 401 `{"code": 401, "message": "需要登录"}`

---

### Requirement: SMS客户端抽象与Mock支持
SMS客户端 MUST 提供抽象接口，SHALL 通过环境变量切换真实/Mock实现以支持无依赖测试。

#### Scenario: Mock模式发送验证码
- **Given**: `.env` 设置 `SMS_MODE=mock`
- **When**: 调用 `sms_client.send_code("13800138000", "123456")`
- **Then**:
  - 控制台输出 `📱 [MOCK SMS] 13800138000 -> 123456`
  - 返回 `{"success": True, "message_id": "mock_123"}`
  - 不调用真实阿里云API

#### Scenario: Aliyun模式发送验证码
- **Given**:
  - `.env` 设置 `SMS_MODE=aliyun`
  - 配置有效的阿里云AK/签名/模板
- **When**: 调用 `sms_client.send_code("13800138000", "654321")`
- **Then**:
  - 调用阿里云 `SendMessageWithTemplate` API
  - 请求参数：`to=8613800138000, template_param={"code": "654321"}`
  - 返回 `{"success": True, "message_id": "实际message_id"}`

#### Scenario: 工厂函数根据环境变量创建客户端
- **Given**: 无前置条件
- **When**:
  - `SMS_MODE=mock` → `get_sms_client()` 返回 `MockSMSClient` 实例
  - `SMS_MODE=aliyun` → `get_sms_client()` 返回 `AliyunSMSClient` 实例
- **Then**: 客户端类型正确，接口行为符合预期

---

### Requirement: 验证码锁定机制
系统 MUST 按手机号全局锁定，SHALL 在5次验证失败后禁止该手机号1小时内发送和验证。

#### Scenario: 锁定期间禁止发送验证码
- **Given**: 手机号 `13800138000` 已被锁定至未来30分钟
- **When**: POST `/auth/sms/send` with `{"phone": "13800138000", "scene": "login"}`
- **Then**: 返回 423 `{"code": 423, "message": "账号已锁定"}`

#### Scenario: 锁定期间禁止验证
- **Given**: 手机号 `13800138000` 已被锁定，且有未过期验证码
- **When**: POST `/auth/sms/verify` with `{"phone": "13800138000", "code": "123456", "scene": "login"}`
- **Then**: 返回 423 `{"code": 423, "message": "账号已锁定"}`

#### Scenario: 锁定1小时后自动解锁
- **Given**: 手机号 `13800138000` 在1小时零1分钟前被锁定
- **When**: POST `/auth/sms/send` with `{"phone": "13800138000", "scene": "register"}`
- **Then**:
  - 正常发送验证码
  - 返回 200
  - 创建新的 `SMSVerification` 记录（error_count=0, locked_until=null）

#### Scenario: 验证成功后清除错误计数和锁定
- **Given**: 手机号 `13800138000` 当前 error_count=3
- **When**: POST `/auth/sms/verify` with 正确验证码
- **Then**:
  - 验证成功
  - `error_count` 重置为 0
  - `locked_until` 设为 NULL
