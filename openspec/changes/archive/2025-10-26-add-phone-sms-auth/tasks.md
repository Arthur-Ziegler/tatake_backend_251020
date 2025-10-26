# 实施任务清单

## 阶段 1: 数据库与模型层（并行）

### 1.1 数据库迁移与目录创建
- [ ] 创建 `data/` 目录（如不存在）
- [ ] 修改 `src/domains/auth/database.py`：
  - 更新 `AUTH_DATABASE_URL` 默认值为 `sqlite:///./data/auth.db`
  - 验证 `create_tables()` 能正确创建新表
- [ ] 验证：运行 `ls data/` 确认 `auth.db` 文件存在

### 1.2 Auth模型扩展
- [ ] 修改 `src/domains/auth/models.py`：
  - Auth表新增 `phone` 字段（Optional[str], max_length=11, unique=True, index=True）
  - 新增索引 `Index('idx_auth_phone', 'phone')`
- [ ] 验证：运行迁移脚本，检查表结构包含 `phone` 字段

### 1.3 SMSVerification模型创建
- [ ] 在 `src/domains/auth/models.py` 新增 `SMSVerification` 类：
  - 字段：`id`, `phone`, `code`, `scene`, `created_at`, `verified`, `verified_at`, `ip_address`, `error_count`, `locked_until`
  - 索引：`idx_sms_phone_scene`, `idx_sms_created_at`, `idx_sms_locked_until`
- [ ] 更新 `database.py` 的 `create_tables()` 导入新模型
- [ ] 验证：`PRAGMA table_info(sms_verification)` 显示完整字段

### 1.4 单元测试（模型层）
- [ ] 创建 `tests/units/auth/test_sms_models.py`：
  - 测试 SMSVerification 模型字段验证
  - 测试 Auth.phone 唯一性约束
  - 测试索引创建
  - 覆盖率 ≥ 97%

---

## 阶段 2: SMS客户端与异常定义（并行）

### 2.1 SMS客户端抽象层
- [ ] 创建 `src/domains/auth/sms_client.py`：
  - 定义 `SMSClientInterface` 抽象基类
  - 实现 `MockSMSClient`（打印日志，返回mock结果）
  - 实现 `AliyunSMSClient`（集成阿里云SDK）
  - 实现 `get_sms_client()` 工厂函数（根据 `SMS_MODE` 环境变量）
- [ ] 验证：手动测试 Mock 和 Aliyun 模式切换

### 2.2 异常类定义
- [ ] 修改 `src/domains/auth/exceptions.py`：
  - `RateLimitException` - 429 发送频率限制
  - `DailyLimitException` - 429 每日次数限制
  - `AccountLockedException` - 423 账号锁定
  - `VerificationNotFoundException` - 404 验证码不存在
  - `VerificationExpiredException` - 410 验证码过期
  - `InvalidVerificationCodeException` - 401 验证码错误
  - `PhoneNotFoundException` - 404 手机号未注册
  - `PhoneAlreadyExistsException` - 409 手机号已注册
  - `PhoneAlreadyBoundException` - 409 手机号已绑定

### 2.3 依赖安装
- [ ] 更新 `pyproject.toml`：
  - 添加 `alibabacloud-dysmsapi20180501 = "^2.0.24"`
  - 添加 `alibabacloud-tea-openapi = "^0.3.9"`
  - 添加 `alibabacloud-tea-console = "^0.1.0"`
  - 添加 `alibabacloud-tea-util = "^0.3.12"`
- [ ] 运行 `uv add <packages>` 安装依赖
- [ ] 验证：`import alibabacloud_dysmsapi20180501` 无报错

### 2.4 单元测试（SMS客户端）
- [ ] 创建 `tests/units/auth/test_sms_client.py`：
  - 测试 MockSMSClient.send_code() 返回正确格式
  - 测试 AliyunSMSClient 构造（Mock SDK）
  - 测试 get_sms_client() 工厂函数切换
  - 覆盖率 ≥ 97%

---

## 阶段 3: Repository层扩展（串行依赖阶段1）

### 3.1 Repository方法新增
- [ ] 修改 `src/domains/auth/repository.py`：
  - `get_auth_by_phone(phone: str) -> Optional[Auth]`
  - `create_sms_verification(verification: SMSVerification) -> SMSVerification`
  - `get_latest_verification(phone: str) -> Optional[SMSVerification]`
  - `get_latest_unverified(phone: str, scene: str) -> Optional[SMSVerification]`
  - `count_today_sends(phone: str) -> int`
  - `update_verification(verification: SMSVerification)`
  - `create_audit_log(action: str, user_id: str, ...)`

### 3.2 单元测试（Repository）
- [ ] 创建 `tests/units/auth/test_sms_repository.py`：
  - 测试所有新增方法
  - 使用 in-memory SQLite
  - 测试边界条件（空结果、多条记录等）
  - 覆盖率 ≥ 97%

---

## 阶段 4: Service层业务逻辑（串行依赖阶段2、3）

### 4.1 Service方法实现
- [ ] 修改 `src/domains/auth/service.py`：
  - `send_sms_code(phone: str, scene: str, ip: str) -> dict`
    - 格式验证、锁定检查、限流检查
    - 调用 SMS 客户端、保存记录、审计日志
  - `verify_sms_code(phone: str, code: str, scene: str, user_id: str = None) -> dict`
    - 通用验证逻辑、错误累计
    - 分场景处理：`_handle_register()`, `_handle_login()`, `_handle_bind()`
  - 辅助方法：
    - `_check_phone_lock(phone: str)`
    - `_check_rate_limit(phone: str)`
    - `_check_daily_limit(phone: str)`
    - `generate_code(length: int = 6) -> str`
    - `is_code_expired(verification: SMSVerification) -> bool`

### 4.2 单元测试（Service）
- [ ] 创建 `tests/units/auth/test_sms_service.py`：
  - 测试 send_sms_code 所有分支（成功/限流/锁定/格式错误）
  - 测试 verify_sms_code 三种场景（register/login/bind）
  - 测试错误累计和锁定逻辑
  - 测试验证码过期逻辑
  - Mock SMS客户端和Repository
  - 覆盖率 ≥ 97%

---

## 阶段 5: Schema与Router层（串行依赖阶段4）

### 5.1 Schema定义
- [ ] 修改 `src/domains/auth/schemas.py`：
  - 请求模型：
    - `SMSSendRequest(phone, scene)`
    - `SMSVerifyRequest(phone, code, scene)`
  - 响应模型：
    - `SMSSendResponse(expires_in, retry_after)`
    - `SMSVerifyResponse(access_token, refresh_token, user_id, is_new_user)` （复用现有AuthResponse或创建）
    - `PhoneBindResponse(user_id, phone, upgraded)`

### 5.2 Router端点实现
- [ ] 修改 `src/domains/auth/router.py`：
  - `POST /auth/sms/send` → `send_sms_code_endpoint()`
    - 调用 `auth_service.send_sms_code()`
    - 统一异常处理（转换为标准响应格式）
  - `POST /auth/sms/verify` → `verify_sms_code_endpoint()`
    - 根据 scene 决定是否需要 JWT 认证（bind场景）
    - 调用 `auth_service.verify_sms_code()`
    - 返回统一格式 `{code, message, data}`

### 5.3 单元测试（Router）
- [ ] 创建 `tests/units/auth/test_sms_router.py`：
  - 测试两个端点的请求/响应格式
  - 测试异常转换（Service异常 → HTTP状态码）
  - Mock Service层
  - 覆盖率 ≥ 97%

---

## 阶段 6: 集成测试与端到端测试（串行依赖阶段5）

### 6.1 集成测试
- [ ] 创建 `tests/integration/auth/test_sms_integration.py`：
  - 完整注册流程（发送验证码 → 验证 → 创建用户 → 获取JWT）
  - 完整登录流程（发送验证码 → 验证 → 获取JWT）
  - 完整绑定流程（登录 → 发送验证码 → 验证 → 绑定手机号）
  - 限流场景（60秒、5次/天）
  - 锁定场景（5次错误）
  - 使用真实数据库（测试环境）
  - 使用 Mock SMS 客户端

### 6.2 异常场景测试
- [ ] 测试手机号格式错误
- [ ] 测试验证码过期
- [ ] 测试手机号已注册/未注册
- [ ] 测试手机号已被其他账号绑定
- [ ] 测试 bind 场景无JWT认证

### 6.3 测试覆盖率验证
- [ ] 运行 `uv run pytest --cov=src/domains/auth --cov-report=term-missing`
- [ ] 确认覆盖率 ≥ 97%
- [ ] 修复所有未覆盖代码

---

## 阶段 7: 配置与文档（并行）

### 7.1 环境变量配置
- [ ] 更新 `.env.example`：
  ```bash
  # 阿里云短信配置
  ALIYUN_ACCESS_KEY_ID=
  ALIYUN_ACCESS_KEY_SECRET=
  ALIYUN_SMS_SIGN_NAME=
  ALIYUN_SMS_TEMPLATE_CODE=
  ALIYUN_SMS_ENDPOINT=dysmsapi.ap-southeast-1.aliyuncs.com

  # SMS模式切换
  SMS_MODE=mock  # mock | aliyun

  # 数据库路径
  AUTH_DATABASE_URL=sqlite:///./data/auth.db
  ```

### 7.2 API文档更新
- [ ] 确保 FastAPI 自动生成的 Swagger 文档包含：
  - `/auth/sms/send` 端点说明、请求示例、响应示例
  - `/auth/sms/verify` 端点说明、三种场景说明、错误码说明
- [ ] 验证：访问 `/docs` 页面测试端点

---

## 阶段 8: 验证与清理（串行，最终阶段）

### 8.1 OpenSpec验证
- [ ] 运行 `openspec validate add-phone-sms-auth --strict`
- [ ] 解决所有验证错误
- [ ] 确认所有 spec 的 scenario 都有对应测试

### 8.2 手动功能测试
- [ ] Mock模式下完整测试注册/登录/绑定流程
- [ ] 测试限流机制（60秒、5次/天）
- [ ] 测试锁定机制（5次错误）
- [ ] 测试数据库健康检查

### 8.3 代码清理
- [ ] 移除所有调试日志和注释
- [ ] 统一代码风格（格式化）
- [ ] 更新所有文档字符串（Google风格）
- [ ] 删除未使用的导入和变量

### 8.4 提交前检查
- [ ] 所有测试通过（`uv run pytest`）
- [ ] 覆盖率报告 ≥ 97%
- [ ] 代码风格检查通过（如使用 ruff/black）
- [ ] Git 提交信息符合约定式提交格式
- [ ] 提案文档与实现一致

---

## 依赖关系说明

**并行任务**：
- 阶段1（数据库）和 阶段2（SMS客户端）可同时进行
- 阶段7（配置）可在任意时间进行

**串行依赖**：
- 阶段3 依赖 阶段1（需要模型定义）
- 阶段4 依赖 阶段2、3（需要客户端和Repository）
- 阶段5 依赖 阶段4（需要Service方法）
- 阶段6 依赖 阶段5（需要完整API）
- 阶段8 依赖 所有阶段完成

**关键验证点**：
- [ ] 阶段1结束：模型单元测试通过
- [ ] 阶段2结束：SMS客户端单元测试通过
- [ ] 阶段4结束：Service层单元测试通过
- [ ] 阶段6结束：集成测试全部通过，覆盖率达标
- [ ] 阶段8结束：OpenSpec验证通过，手动测试通过
