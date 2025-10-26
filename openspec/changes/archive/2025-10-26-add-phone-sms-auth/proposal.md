# 手机号+短信验证码双通道认证

## What
为认证系统新增手机号验证码登录/注册/绑定能力，作为微信登录的补充通道。实现数据库独立化（迁移至 `data/auth.db`）和阿里云短信集成（支持Mock切换）。

## Why
- **业务扩展**：支持非微信用户通过手机号注册登录
- **账号绑定**：微信用户可绑定手机号，提升账号安全性
- **架构优化**：认证数据库独立化，为微服务架构演进铺路

## What Changes
This change implements:
1. **Phone SMS Authentication System**: Complete phone number + SMS verification authentication flow
2. **Database Separation**: Migrates authentication data to separate `./data/auth.db` database
3. **Domain Architecture**: Proper separation between authentication domain and user domain
4. **SMS Integration**: Aliyun SMS service integration with Mock mode for testing
5. **API Endpoints**: New SMS send and verify endpoints with rate limiting
6. **Security Features**: Phone number locking after failed attempts, rate limiting
7. **User Domain Models**: Independent user business data models separate from auth data

## 核心目标
1. **双通道认证**：微信 OpenID 和手机号+验证码并存，互不干扰
2. **数据库独立**：迁移至 `data/auth.db`，独立于其他领域
3. **极简设计**：复用现有 JWT 机制，新增最小必要字段和表
4. **可测试性**：SMS 客户端支持 Mock/真实 SDK 无缝切换

## 核心变更

### 数据模型
- **Auth 表**：新增 `phone` 字段（唯一索引）
- **SMSVerification 表**：新增，字段 `id`, `phone`, `code`, `scene`, `created_at`, `verified`, `verified_at`, `ip_address`, `error_count`, `locked_until`
- **AuthLog 表**：新增 action 类型 `sms_send`, `sms_verify_*`, `phone_*`
- **数据库路径**：`tatake_auth.db` → `data/auth.db`

### API 端点
- `POST /auth/sms/send` - 发送验证码（限流：60秒/次，5次/天）
- `POST /auth/sms/verify` - 验证码验证（支持 register/login/bind 场景）

### 业务规则
- **验证码**：6位数字，5分钟有效期
- **限流**：60秒重发间隔，每日5次上限
- **安全锁定**：5次验证失败后，该手机号锁定1小时（不可发送/验证）
- **场景**：
  - `register`：直接创建正式用户（`is_guest=False, phone=xxx`）
  - `login`：已注册手机号登录，未注册返回 404
  - `bind`：需 JWT 认证，绑定手机号并升级游客账号

### 技术方案
- **SMS 客户端**：抽象接口 + 工厂模式，`.env` 控制 `SMS_MODE=mock|aliyun`
- **阿里云集成**：`SendMessageWithTemplate` API，单模板 `{"code": "123456"}`
- **JWT 复用**：统一 payload 格式，不区分登录方式

## 影响范围
- **新增**：`sms_client.py` + 5个测试文件
- **修改**：7个领域文件（models/database/repository/service/router/schemas/exceptions）
- **配置**：`.env` 新增 6 项（阿里云AK/签名/模板 + SMS_MODE）

## 风险与限制
- **成本监控**：短信发送量需监控，防止恶意刷量
- **依赖新增**：阿里云SDK（`alibabacloud-dysmsapi20180501`等4个包）

## 成功标准
- 测试覆盖率 ≥ 97%，每个源文件对应单元测试
- Mock 模式下全测试通过，无需真实阿里云凭证
- `openspec validate add-phone-sms-auth --strict` 零错误
- 统一响应格式 `{code, message, data}`

## 相关文档
- 参考规格：`api-layer-architecture`, `service-layer-architecture`, `unit-testing`
- 外部文档：阿里云 SendMessageWithTemplate API
