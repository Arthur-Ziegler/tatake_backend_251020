"""
认证领域Service层测试

测试Service层的业务逻辑，包括：
- JWT令牌管理
- 短信验证服务
- 用户管理服务
- 核心认证服务
- 业务规则验证
- 异常处理
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from ..service import JWTService, SMSService, UserService, AuthService
from ..exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    SMSException,
    ValidationError
)

# 为测试添加缺少的异常类
class UserNotFoundException(Exception):
    """用户未找到异常"""
    pass


@pytest.mark.asyncio
class TestJWTService:
    """JWT服务测试"""

    def test_generate_tokens_success(self):
        """测试成功生成令牌"""
        jwt_service = JWTService(
            secret_key="test-secret-key",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )

        user_data = {
            "user_id": str(uuid4()),
            "user_type": "registered",
            "is_guest": False,
            "jwt_version": 1
        }

        tokens = jwt_service.generate_tokens(user_data)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] == 1800  # 30分钟 = 1800秒

    def test_verify_access_token_success(self):
        """测试成功验证访问令牌"""
        jwt_service = JWTService(secret_key="test-secret-key")

        user_data = {
            "user_id": str(uuid4()),
            "user_type": "registered",
            "is_guest": False,
            "jwt_version": 1
        }

        tokens = jwt_service.generate_tokens(user_data)
        payload = jwt_service.verify_token(tokens["access_token"], "access")

        assert payload["sub"] == user_data["user_id"]
        assert payload["user_type"] == "registered"
        assert payload["is_guest"] is False
        assert payload["jwt_version"] == 1
        assert payload["token_type"] == "access"

    def test_verify_refresh_token_success(self):
        """测试成功验证刷新令牌"""
        jwt_service = JWTService(secret_key="test-secret-key")

        user_data = {
            "user_id": str(uuid4()),
            "user_type": "guest",
            "is_guest": True,
            "jwt_version": 2
        }

        tokens = jwt_service.generate_tokens(user_data)
        payload = jwt_service.verify_token(tokens["refresh_token"], "refresh")

        assert payload["sub"] == user_data["user_id"]
        assert payload["token_type"] == "refresh"
        assert payload["is_guest"] is True

    def test_verify_token_wrong_type_fails(self):
        """测试验证错误类型的令牌失败"""
        jwt_service = JWTService(secret_key="test-secret-key")

        user_data = {"user_id": str(uuid4()), "user_type": "registered"}
        tokens = jwt_service.generate_tokens(user_data)

        # 尝试用refresh令牌验证为access类型
        with pytest.raises(TokenException):
            jwt_service.verify_token(tokens["refresh_token"], "access")

    def test_verify_expired_token_fails(self):
        """测试验证过期令牌失败"""
        # 创建一个立即过期的JWT服务
        jwt_service = JWTService(
            secret_key="test-secret-key",
            access_token_expire_minutes=0.001  # 约0.06秒后过期
        )

        user_data = {"user_id": str(uuid4()), "user_type": "registered"}
        tokens = jwt_service.generate_tokens(user_data)

        # 等待令牌过期
        import time
        time.sleep(0.1)

        with pytest.raises(TokenException, match="令牌已过期"):
            jwt_service.verify_token(tokens["access_token"], "access")

    def test_verify_invalid_token_fails(self):
        """测试验证无效令牌失败"""
        jwt_service = JWTService(secret_key="test-secret-key")

        with pytest.raises(TokenException):
            jwt_service.verify_token("invalid.token.here", "access")

    def test_get_token_jti_success(self):
        """测试成功获取令牌JTI"""
        jwt_service = JWTService(secret_key="test-secret-key")

        user_data = {"user_id": str(uuid4()), "user_type": "registered"}
        tokens = jwt_service.generate_tokens(user_data)

        jti = jwt_service.get_token_jti(tokens["access_token"])
        assert jti is not None
        assert len(jti) > 0


@pytest.mark.asyncio
class TestSMSService:
    """短信服务测试"""

    async def test_send_verification_code_success(self, mock_sms_service):
        """测试成功发送验证码"""
        sms_service = SMSService(mock_sms_service)
        phone = "13800138000"

        with patch('builtins.print') as mock_print:
            code = await sms_service.send_verification_code(phone, "login")

        assert code is not None
        assert len(code) == 6  # 6位数字验证码
        assert code.isdigit()

        # 验证控制台输出被调用
        mock_print.assert_called()

    async def test_send_verification_code_rate_limit(self, mock_sms_service):
        """测试发送验证码频率限制"""
        sms_service = SMSService(mock_sms_service)
        phone = "13800138000"

        # 第一次发送应该成功
        code1 = await sms_service.send_verification_code(phone, "login")
        assert code1 is not None

        # 立即再次发送应该被限制
        with pytest.raises(SMSException, match="发送过于频繁"):
            await sms_service.send_verification_code(phone, "login")

    async def test_verify_code_success(self, mock_sms_service):
        """测试成功验证验证码"""
        sms_service = SMSService(mock_sms_service)
        phone = "13800138000"
        code = "123456"

        # 先发送验证码
        await sms_service.send_verification_code(phone, "login")

        # 验证正确的验证码
        result = await sms_service.verify_code(phone, code, "login")
        assert result is True

    async def test_verify_code_invalid_fails(self, mock_sms_service):
        """测试验证错误验证码失败"""
        sms_service = SMSService(mock_sms_service)
        phone = "13800138000"

        # 发送验证码
        await sms_service.send_verification_code(phone, "login")

        # 验证错误的验证码
        with pytest.raises(SMSException, match="验证码无效或已过期"):
            await sms_service.verify_code(phone, "999999", "login")

    async def test_verify_code_max_attempts(self, mock_sms_service):
        """测试验证码最大尝试次数"""
        sms_service = SMSService(mock_sms_service)
        phone = "13800138000"

        # 发送验证码
        await sms_service.send_verification_code(phone, "login")

        # 多次尝试错误的验证码
        for _ in range(5):  # 最大尝试次数是5
            try:
                await sms_service.verify_code(phone, "wrong_code", "login")
            except SMSException:
                pass  # 忽略中间的失败

        # 最后一次尝试正确的验证码，应该仍然失败
        with pytest.raises(SMSException, match="验证码尝试次数过多"):
            await sms_service.verify_code(phone, "123456", "login")

    async def test_generate_code_format(self, mock_sms_service):
        """测试生成的验证码格式"""
        sms_service = SMSService(mock_sms_service)

        # 生成多个验证码验证格式
        for _ in range(10):
            code = sms_service.generate_code()
            assert len(code) == 6
            assert code.isdigit()
            assert 100000 <= int(code) <= 999999


@pytest.mark.asyncio
class TestUserService:
    """用户服务测试"""

    async def test_create_guest_user_success(self, auth_repository):
        """测试成功创建游客用户"""
        user_service = UserService(auth_repository)

        guest_user = await user_service.create_guest_user(
            device_id="test-device-123",
            device_type="ios",
            app_version="1.0.0"
        )

        assert guest_user.id is not None
        assert guest_user.is_guest is True
        assert guest_user.device_id == "test-device-123"
        assert guest_user.device_type == "ios"
        assert "游客_" in guest_user.nickname

    async def test_create_guest_user_device_exists(self, auth_repository):
        """测试设备已存在时返回现有游客用户"""
        user_service = UserService(auth_repository)

        # 创建第一个游客用户
        guest1 = await user_service.create_guest_user(
            device_id="same-device-123",
            device_type="ios"
        )

        # 使用相同设备再次创建，应该返回同一个用户
        guest2 = await user_service.create_guest_user(
            device_id="same-device-123",
            device_type="android"
        )

        assert guest1.id == guest2.id
        assert guest1.device_id == guest2.device_id

    async def test_upgrade_guest_account_success(self, auth_repository):
        """测试成功升级游客账号"""
        user_service = UserService(auth_repository)

        # 先创建游客用户
        guest_user = await user_service.create_guest_user(
            device_id="test-device-456",
            device_type="ios"
        )

        # 升级账号
        upgraded_user = await user_service.upgrade_guest_account(
            guest_user_id=guest_user.id,
            phone="13800138000",
            password="test_password_123",
            nickname="正式用户"
        )

        assert upgraded_user.id == guest_user.id
        assert upgraded_user.is_guest is False
        assert upgraded_user.is_verified is True
        assert upgraded_user.phone == "13800138000"
        assert upgraded_user.nickname == "正式用户"
        assert upgraded_user.password_hash is not None

    async def test_upgrade_guest_account_no_identity_fails(self, auth_repository):
        """测试升级游客账号没有身份信息失败"""
        user_service = UserService(auth_repository)

        guest_user = await user_service.create_guest_user(
            device_id="test-device-789",
            device_type="ios"
        )

        # 不提供手机号或邮箱
        with pytest.raises(ValidationError, match="升级账号需要提供手机号或邮箱"):
            await user_service.upgrade_guest_account(guest_user.id)

    async def test_upgrade_guest_account_phone_exists_fails(self, auth_repository):
        """测试升级游客账号手机号已存在失败"""
        user_service = UserService(auth_repository)

        # 创建一个正式用户
        existing_user = await user_service.create_guest_user(
            device_id="existing-device",
            device_type="ios"
        )
        await auth_repository.create_user(
            phone="13800138000",
            password_hash="hash",
            nickname="现有用户"
        )

        # 创建游客用户并尝试升级为已存在的手机号
        guest_user = await user_service.create_guest_user(
            device_id="new-device",
            device_type="ios"
        )

        with pytest.raises(ValidationError, match="手机号已被注册"):
            await user_service.upgrade_guest_account(
                guest_user.id,
                phone="13800138000"
            )

    async def test_authenticate_user_by_username_success(self, auth_repository):
        """测试通过用户名认证用户成功"""
        user_service = UserService(auth_repository)

        # 创建用户
        password = "test_password_123"
        user = await auth_repository.create_user(
            username="testuser",
            password_hash=user_service.hash_password(password),
            nickname="测试用户"
        )

        # 认证
        authenticated_user = await user_service.authenticate_user("testuser", password)
        assert authenticated_user is not None
        assert authenticated_user.id == user.id

    async def test_authenticate_user_by_phone_success(self, auth_repository):
        """测试通过手机号认证用户成功"""
        user_service = UserService(auth_repository)

        # 创建用户
        password = "test_password_123"
        user = await auth_repository.create_user(
            phone="13800138000",
            password_hash=user_service.hash_password(password),
            nickname="测试用户"
        )

        # 认证
        authenticated_user = await user_service.authenticate_user("13800138000", password)
        assert authenticated_user is not None
        assert authenticated_user.id == user.id

    async def test_authenticate_user_wrong_password_fails(self, auth_repository):
        """测试错误密码认证失败"""
        user_service = UserService(auth_repository)

        # 创建用户
        user = await auth_repository.create_user(
            username="testuser",
            password_hash=user_service.hash_password("correct_password"),
            nickname="测试用户"
        )

        # 用错误密码认证
        authenticated_user = await user_service.authenticate_user("testuser", "wrong_password")
        assert authenticated_user is None

    async def test_authenticate_user_not_exists_fails(self, auth_repository):
        """测试认证不存在的用户失败"""
        user_service = UserService(auth_repository)

        authenticated_user = await user_service.authenticate_user("nonexistent", "password")
        assert authenticated_user is None

    def test_hash_password_consistency(self):
        """测试密码哈希一致性"""
        user_service = UserService(None)
        password = "test_password_123"

        hash1 = user_service.hash_password(password)
        hash2 = user_service.hash_password(password)

        # 相同密码的哈希应该不同（因为使用了随机salt）
        assert hash1 != hash2

        # 但都应该能验证原始密码
        assert user_service.verify_password(password, hash1) is True
        assert user_service.verify_password(password, hash2) is True

    def test_verify_password_wrong_fails(self):
        """测试验证错误密码失败"""
        user_service = UserService(None)
        password = "correct_password"
        wrong_password = "wrong_password"

        password_hash = user_service.hash_password(password)

        assert user_service.verify_password(wrong_password, password_hash) is False


@pytest.mark.asyncio
class TestAuthService:
    """核心认证服务测试"""

    async def test_init_guest_account_success(self, auth_service):
        """测试成功初始化游客账号"""
        from src.domains.auth.schemas import GuestInitRequest

        request = GuestInitRequest(
            device_id="test-device-123",
            device_type="ios",
            app_version="1.0.0"
        )

        with patch('builtins.print'):
            result = await auth_service.init_guest_account(
                request=request,
                ip_address="127.0.0.1",
                user_agent="TestAgent"
            )

        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["is_guest"] is True

    async def test_upgrade_guest_account_success(self, auth_service):
        """测试成功升级游客账号"""
        from src.domains.auth.schemas import GuestUpgradeRequest

        # 先初始化游客账号
        init_request = GuestInitRequest(device_id="test-device-456")
        guest_result = await auth_service.init_guest_account(init_request)
        guest_user_id = uuid4()  # 模拟用户ID

        upgrade_request = GuestUpgradeRequest(
            phone="13800138000",
            sms_code="123456",  # Mock验证码
            password="new_password_123",
            nickname="正式用户"
        )

        with patch('builtins.print'):
            with patch.object(auth_service.sms_service, 'verify_code', return_value=True):
                result = await auth_service.upgrade_guest_account(
                    request=upgrade_request,
                    current_user_id=guest_user_id,
                    ip_address="127.0.0.1"
                )

        assert "user_id" in result
        assert "access_token" in result
        assert result["is_guest"] is False

    async def test_login_with_sms_success(self, auth_service):
        """测试短信验证码登录成功"""
        from src.domains.auth.schemas import LoginRequest

        request = LoginRequest(
            identifier="13800138000",
            login_type="sms",
            sms_code="123456"
        )

        with patch('builtins.print'):
            with patch.object(auth_service.user_service, 'authenticate_by_sms',
                           return_value=Mock(id=uuid4(), is_guest=False)):
                result = await auth_service.login(
                    request=request,
                    ip_address="127.0.0.1"
                )

        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result

    async def test_login_with_password_success(self, auth_service):
        """测试密码登录成功"""
        from src.domains.auth.schemas import LoginRequest

        request = LoginRequest(
            identifier="testuser",
            login_type="password",
            password="test_password_123"
        )

        with patch('builtins.print'):
            with patch.object(auth_service.user_service, 'authenticate_user',
                           return_value=Mock(id=uuid4(), is_guest=False)):
                result = await auth_service.login(
                    request=request,
                    ip_address="127.0.0.1"
                )

        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result

    async def test_login_invalid_credentials_fails(self, auth_service):
        """测试登录无效凭据失败"""
        from src.domains.auth.schemas import LoginRequest

        request = LoginRequest(
            identifier="testuser",
            login_type="password",
            password="wrong_password"
        )

        with patch('builtins.print'):
            with patch.object(auth_service.user_service, 'authenticate_user',
                           return_value=None):
                with pytest.raises(AuthenticationException):
                    await auth_service.login(request=request)

    async def test_refresh_token_success(self, auth_service):
        """测试成功刷新令牌"""
        from src.domains.auth.schemas import TokenRefreshRequest

        request = TokenRefreshRequest(refresh_token="valid_refresh_token")

        mock_payload = {
            "sub": str(uuid4()),
            "user_type": "registered",
            "is_guest": False,
            "jwt_version": 1,
            "jti": str(uuid4()),
            "exp": datetime.now(timezone.utc).timestamp() + 3600
        }

        with patch('builtins.print'):
            with patch.object(auth_service.jwt_service, 'verify_token',
                           return_value=mock_payload):
                with patch.object(auth_service.token_repository, 'is_token_blacklisted',
                               return_value=False):
                    with patch.object(auth_service.auth_repository, 'get_by_id',
                                   return_value=Mock(jwt_version=1, is_active=True)):
                        result = await auth_service.refresh_token(request=request)

        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert "expires_in" in result

    async def test_logout_success(self, auth_service):
        """测试成功登出"""
        user_id = uuid4()
        token_jti = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch('builtins.print'):
            await auth_service.logout(
                token_jti=token_jti,
                user_id=user_id,
                expires_at=expires_at
            )

        # 如果没有抛出异常，说明登出成功

    async def test_send_sms_code_success(self, auth_service):
        """测试成功发送短信验证码"""
        from src.domains.auth.schemas import SMSCodeRequest

        request = SMSCodeRequest(
            phone="13800138000",
            verification_type="login"
        )

        with patch('builtins.print'):
            code = await auth_service.send_sms_code(request=request)

        assert code is not None
        assert len(code) == 6

    async def test_get_user_info_success(self, auth_service):
        """测试成功获取用户信息"""
        user_id = uuid4()

        mock_user = Mock(
            id=user_id,
            username="testuser",
            nickname="测试用户",
            email="test@example.com",
            phone="13800138000",
            avatar=None,
            is_guest=False,
            is_verified=True,
            level=1,
            total_points=100,
            created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc)
        )

        with patch.object(auth_service.auth_repository, 'get_by_id', return_value=mock_user):
            user_info = await auth_service.get_user_info(user_id)

        assert user_info["user_id"] == str(user_id)
        assert user_info["username"] == "testuser"
        assert user_info["nickname"] == "测试用户"
        assert user_info["is_guest"] is False

    async def test_get_user_info_not_found_fails(self, auth_service):
        """测试获取不存在用户信息失败"""
        user_id = uuid4()

        with patch.object(auth_service.auth_repository, 'get_by_id', return_value=None):
            with pytest.raises(UserNotFoundException):
                await auth_service.get_user_info(user_id)


# Mock对象用于测试
class Mock:
    """简单的Mock对象"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# 边界条件和异常处理测试
@pytest.mark.asyncio
class TestAuthServiceEdgeCases:
    """认证服务边界条件测试"""

    async def test_init_guest_account_minimal_data(self, auth_service):
        """测试最少的游客初始化数据"""
        from src.domains.auth.schemas import GuestInitRequest

        request = GuestInitRequest()  # 所有字段都是可选的

        with patch('builtins.print'):
            result = await auth_service.init_guest_account(request=request)

        assert "user_id" in result
        assert result["is_guest"] is True

    async def test_upgrade_guest_account_multiple_identities(self, auth_service):
        """测试升级游客账号提供多种身份信息"""
        from src.domains.auth.schemas import GuestUpgradeRequest

        upgrade_request = GuestUpgradeRequest(
            phone="13800138000",
            email="user@example.com",
            password="password123",
            username="newuser",
            nickname="新用户"
        )

        with patch('builtins.print'):
            with patch.object(auth_service.sms_service, 'verify_code', return_value=True):
                result = await auth_service.upgrade_guest_account(
                    request=upgrade_request,
                    current_user_id=uuid4()
                )

        assert result["is_guest"] is False

    async def test_refresh_token_version_mismatch_fails(self, auth_service):
        """测试令牌版本不匹配刷新失败"""
        from src.domains.auth.schemas import TokenRefreshRequest

        request = TokenRefreshRequest(refresh_token="valid_refresh_token")

        mock_payload = {
            "sub": str(uuid4()),
            "jwt_version": 1,  # 令牌版本1
            "jti": str(uuid4()),
            "exp": datetime.now(timezone.utc).timestamp() + 3600
        }

        mock_user = Mock(jwt_version=2)  # 用户版本2，不匹配

        with patch('builtins.print'):
            with patch.object(auth_service.jwt_service, 'verify_token',
                           return_value=mock_payload):
                with patch.object(auth_service.token_repository, 'is_token_blacklisted',
                               return_value=False):
                    with patch.object(auth_service.auth_repository, 'get_by_id',
                                   return_value=mock_user):
                        with pytest.raises(TokenException, match="令牌版本不匹配"):
                            await auth_service.refresh_token(request=request)

    async def test_login_unsupported_type_fails(self, auth_service):
        """测试不支持的登录类型失败"""
        from src.domains.auth.schemas import LoginRequest

        request = LoginRequest(
            identifier="testuser",
            login_type="unsupported_type",
            password="password"
        )

        with pytest.raises(ValidationError, match="不支持的登录类型"):
            await auth_service.login(request=request)

    async def test_send_sms_rate_limit_per_ip(self, auth_service):
        """测试基于IP的短信发送频率限制"""
        from src.domains.auth.schemas import SMSCodeRequest

        request = SMSCodeRequest(
            phone="13800138000",
            verification_type="login"
        )

        # 发送第一条短信
        with patch('builtins.print'):
            await auth_service.send_sms_code(request=request)

        # 立即发送第二条短信应该被限制
        with patch('builtins.print'):
            with pytest.raises(SMSException):
                await auth_service.send_sms_code(request=request)