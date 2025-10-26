# 架构设计

## 设计原则
1. **KISS**：复用现有认证架构，最小化新增逻辑
2. **开闭原则**：SMS客户端抽象化，支持Mock/真实SDK切换，未来可扩展其他短信服务商
3. **单一职责**：验证码发送/验证/锁定逻辑独立封装

## 数据库设计

### Auth 表变更
```python
# 新增字段
phone: Optional[str] = Field(
    default=None,
    max_length=11,
    unique=True,
    index=True,
    description="手机号，唯一"
)

# 新增索引
Index('idx_auth_phone', 'phone')
```

**设计决策**：
- 手机号与微信 OpenID 同级，都是唯一登录凭证
- 允许 NULL，兼容纯微信登录用户
- 唯一约束确保一个手机号只能绑定一个账号

### SMSVerification 表（新增）
```python
class SMSVerification(SQLModel, table=True):
    __tablename__ = "sms_verification"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    phone: str = Field(max_length=11, index=True)
    code: str = Field(max_length=6)  # 6位数字
    scene: str = Field(max_length=20)  # register/login/bind
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = Field(default=False)
    verified_at: Optional[datetime] = None
    ip_address: Optional[str] = Field(default=None, max_length=45)
    error_count: int = Field(default=0)
    locked_until: Optional[datetime] = None

    # 索引
    __table_args__ = (
        Index('idx_sms_phone_scene', 'phone', 'scene'),
        Index('idx_sms_created_at', 'created_at'),
        Index('idx_sms_locked_until', 'locked_until'),
    )
```

**设计决策**：
- **无 expires_at 字段**：有效期通过 `created_at + 5分钟` 动态计算，减少存储
- **error_count + locked_until**：按手机号锁定，不是按单条记录
- **scene 字段**：区分验证码用途，支持未来扩展（如安全验证）
- **verified/verified_at**：防止验证码重复使用

### 数据库路径迁移
```python
# 旧路径
AUTH_DATABASE_URL = "sqlite:///./tatake_auth.db"

# 新路径
AUTH_DATABASE_URL = "sqlite:///./data/auth.db"
```

**设计决策**：
- 统一数据文件管理（`data/` 目录已被 chat.db 使用）
- 为未来多数据库架构（task.db, focus.db 等）建立规范

## API 设计

### 端点 1: POST /auth/sms/send

**请求**：
```json
{
  "phone": "13800138000",
  "scene": "register"  // register | login | bind
}
```

**响应**：
```json
{
  "code": 200,
  "message": "验证码已发送",
  "data": {
    "expires_in": 300,
    "retry_after": 60
  }
}
```

**业务流程**：
```
1. 参数验证（手机号格式：11位数字）
2. 检查手机号锁定状态（locked_until > now）→ 423 Locked
3. 检查60秒限流（最新验证码 created_at < 60秒前）→ 429 Too Many Requests
4. 检查今日发送次数（count(created_at >= today) < 5）→ 429
5. 生成6位随机验证码
6. 调用 SMS 客户端发送（Mock/Aliyun）
7. 保存 SMSVerification 记录
8. 审计日志 AuthLog(action=sms_send)
```

**错误码**：
- `400` - 手机号格式错误
- `423` - 账号已锁定（5次验证失败）
- `429` - 发送频率过高（60秒/5次限制）
- `500` - 短信发送失败（阿里云API异常）

---

### 端点 2: POST /auth/sms/verify

**请求**：
```json
{
  "phone": "13800138000",
  "code": "123456",
  "scene": "register"
}
```

**响应（register/login）**：
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user_id": "uuid-xxx",
    "is_new_user": true  // 仅 register=true
  }
}
```

**响应（bind）**：
```json
{
  "code": 200,
  "message": "绑定成功",
  "data": {
    "user_id": "uuid-xxx",
    "phone": "13800138000",
    "upgraded": true  // 游客升级
  }
}
```

**业务流程（分场景）**：

#### 通用验证步骤
```
1. 查询最新未验证验证码（phone + scene + verified=False）→ 404 Not Found
2. 检查手机号锁定（locked_until > now）→ 423 Locked
3. 检查验证码过期（created_at + 5分钟 < now）→ 410 Gone
4. 验证码匹配：
   - 匹配成功 → 继续场景逻辑
   - 匹配失败 → error_count++，若 ≥5 则设置 locked_until=now+1h → 401 Unauthorized
```

#### scene=register
```
5. 检查手机号是否已注册（Auth.phone exists）→ 409 Conflict
6. 创建正式用户：Auth(is_guest=False, phone=phone)
7. 生成 JWT（user_id, jwt_version）
8. 标记验证码已使用：verified=True, verified_at=now
9. 审计日志：phone_register
10. 返回 tokens + is_new_user=True
```

#### scene=login
```
5. 查询 Auth(phone=phone)
   - 未找到 → 404 手机号未注册
   - 找到 → 继续
6. 更新 last_login_at=now
7. 生成 JWT
8. 标记验证码已使用
9. 审计日志：phone_login
10. 返回 tokens + is_new_user=False
```

#### scene=bind
```
5. JWT 认证（从 Header 获取 user_id）→ 401 Unauthorized
6. 检查手机号是否已被其他账号绑定（Auth.phone exists AND id != user_id）→ 409 Conflict
7. 绑定手机号：Auth.phone = phone
8. 若 is_guest=True → 升级：is_guest=False, upgraded=True
9. 标记验证码已使用
10. 审计日志：phone_bind
11. 返回 user_id + phone + upgraded
```

**错误码**：
- `400` - 参数错误
- `401` - 验证码错误/未认证（bind场景）
- `404` - 验证码不存在/手机号未注册（login场景）
- `409` - 手机号已注册（register）/已被绑定（bind）
- `410` - 验证码已过期
- `423` - 账号已锁定

## 技术方案

### SMS 客户端架构
```python
# 抽象接口
class SMSClientInterface(ABC):
    @abstractmethod
    async def send_code(self, phone: str, code: str) -> dict:
        """返回 {success: bool, message_id: str}"""
        pass

# 真实实现
class AliyunSMSClient(SMSClientInterface):
    def __init__(self):
        self.client = Client(Config(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
            endpoint="dysmsapi.ap-southeast-1.aliyuncs.com"
        ))

    async def send_code(self, phone: str, code: str) -> dict:
        req = SendMessageWithTemplateRequest(
            to=f"86{phone}",
            from_=os.getenv("ALIYUN_SMS_SIGN_NAME"),
            template_code=os.getenv("ALIYUN_SMS_TEMPLATE_CODE"),
            template_param=json.dumps({"code": code})
        )
        resp = await self.client.send_message_with_template_async(req)
        return {
            "success": resp.response_code == "OK",
            "message_id": resp.message_id
        }

# Mock实现
class MockSMSClient(SMSClientInterface):
    async def send_code(self, phone: str, code: str) -> dict:
        print(f"📱 [MOCK SMS] {phone} -> {code}")
        return {"success": True, "message_id": "mock_123"}

# 工厂函数
def get_sms_client() -> SMSClientInterface:
    mode = os.getenv("SMS_MODE", "mock")
    return AliyunSMSClient() if mode == "aliyun" else MockSMSClient()
```

**设计优势**：
- 测试无需真实短信服务，提升测试速度
- 开发环境默认 Mock，避免短信费用
- 未来可轻松扩展其他服务商（腾讯云、华为云等）

### 锁定机制设计

**按手机号全局锁定**（方案A）：
```python
def check_phone_lock(phone: str):
    """检查手机号是否被锁定"""
    latest = repo.get_latest_verification(phone)
    if latest and latest.locked_until and latest.locked_until > now():
        raise AccountLockedException(
            f"账号已锁定至 {latest.locked_until.strftime('%H:%M:%S')}"
        )

def increment_error_count(verification: SMSVerification):
    """累计错误次数，达到阈值则锁定"""
    verification.error_count += 1
    if verification.error_count >= 5:
        verification.locked_until = now() + timedelta(hours=1)
    repo.update(verification)
```

**设计决策**：
- 锁定后，该手机号**发送**和**验证**都被阻止
- 即使重新发送新验证码，仍需检查最新记录的 `locked_until`
- 安全优先，防止暴力破解

### 验证码生成与存储
```python
import random

def generate_code(length: int = 6) -> str:
    """生成随机数字验证码"""
    return ''.join(random.choices('0123456789', k=length))

def is_code_expired(verification: SMSVerification) -> bool:
    """判断验证码是否过期（5分钟）"""
    return (datetime.now(timezone.utc) - verification.created_at).seconds > 300
```

**安全考虑**：
- 验证码不加密存储（明文），因其短期有效且一次性使用
- 验证成功后立即标记 `verified=True`，防止重放攻击

## 测试策略

### Mock SMS 客户端测试
```python
# tests/units/auth/test_sms_client.py
@pytest.mark.asyncio
async def test_mock_sms_client():
    client = MockSMSClient()
    result = await client.send_code("13800138000", "123456")
    assert result["success"] is True
    assert "message_id" in result
```

### Service 层测试
```python
# tests/units/auth/test_sms_service.py
@pytest.mark.asyncio
async def test_send_sms_rate_limit(mock_repo):
    """测试60秒限流"""
    # 创建60秒内的验证码记录
    mock_repo.get_latest_verification.return_value = SMSVerification(
        phone="13800138000",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=30)
    )

    with pytest.raises(RateLimitException):
        await auth_service.send_sms_code("13800138000", "register")
```

### 集成测试
```python
# tests/integration/auth/test_sms_integration.py
async def test_register_flow_e2e(client):
    """端到端注册流程"""
    # 1. 发送验证码
    resp = await client.post("/auth/sms/send", json={
        "phone": "13800138000",
        "scene": "register"
    })
    assert resp.status_code == 200

    # 2. 从数据库获取验证码（测试环境）
    with get_auth_db() as db:
        verification = db.query(SMSVerification).filter_by(
            phone="13800138000"
        ).first()
        code = verification.code

    # 3. 验证验证码
    resp = await client.post("/auth/sms/verify", json={
        "phone": "13800138000",
        "code": code,
        "scene": "register"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]
```

## 配置管理

### 环境变量
```bash
# .env
# 阿里云配置
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_SMS_SIGN_NAME=
ALIYUN_SMS_TEMPLATE_CODE=
ALIYUN_SMS_ENDPOINT=dysmsapi.ap-southeast-1.aliyuncs.com

# SMS 模式切换
SMS_MODE=mock  # mock | aliyun

# 数据库路径
AUTH_DATABASE_URL=sqlite:///./data/auth.db
```

### 依赖包
```toml
# pyproject.toml 新增
alibabacloud-dysmsapi20180501 = "^2.0.24"
alibabacloud-tea-openapi = "^0.3.9"
alibabacloud-tea-console = "^0.1.0"
alibabacloud-tea-util = "^0.3.12"
```

## 安全考虑

1. **防暴力破解**：5次错误锁定1小时，按手机号全局锁定
2. **防刷量攻击**：60秒重发间隔 + 每日5次上限
3. **验证码强度**：6位数字，5分钟有效期（共 10^6 种组合，5分钟内暴力破解概率极低）
4. **IP记录**：记录发送IP，支持后续风控分析
5. **审计完整**：所有关键操作记录到 AuthLog

## 未来扩展方向

1. **多服务商支持**：腾讯云、华为云SMS客户端
2. **图形验证码**：发送前增加人机验证
3. **风控系统**：基于IP/设备指纹的异常检测
4. **国际化**：支持国际手机号格式
