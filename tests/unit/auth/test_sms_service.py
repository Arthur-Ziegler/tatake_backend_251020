"""
SMS认证Service层单元测试

测试新增的SMS认证相关Service方法，确保业务逻辑的正确性和异常处理。
采用TDD方式，先写测试再实现Service方法。

测试覆盖：
- 发送短信验证码的所有分支（成功/限流/锁定/格式错误）
- 验证短信验证码的三种场景（register/login/bind）
- 错误累计和锁定逻辑
- 验证码过期逻辑
- 辅助方法的正确性
- 与Repository和SMS客户端的集成
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from src.domains.auth.service import AuthService
from src.domains.auth.models import Auth, SMSVerification
from src.domains.auth.exceptions import (
    RateLimitException,
    DailyLimitException,
    AccountLockedException,
    VerificationNotFoundException,
    VerificationExpiredException,
    InvalidVerificationCodeException,
    PhoneNotFoundException,
    PhoneAlreadyExistsException,
    PhoneAlreadyBoundException,
    ValidationError
)


class TestSendSMSCode:
    """发送短信验证码测试"""

    @pytest.fixture
    def mock_auth_service(self):
        """创建Mock的AuthService实例"""
        with patch('src.domains.auth.service.get_auth_db') as mock_db:
            with patch('src.domains.auth.sms_client.get_sms_client') as mock_client:
                service = AuthService(mock_db.return_value)
                service.sms_client = mock_client.return_value
                return service

    @pytest.fixture
    def mock_auth_repo(self):
        """创建Mock的AuthRepository"""
        repo = Mock()
        repo.get_auth_by_phone.return_value = None
        repo.create_sms_verification.return_value = Mock()
        repo.count_today_sends.return_value = 0
        repo.get_latest_verification.return_value = None
        return repo

    def test_send_sms_code_success(self, mock_auth_service, mock_auth_repo):
        """测试发送短信验证码成功"""
        # 设置Mock
        mock_auth_service.repository = mock_auth_repo
        mock_auth_service.sms_client.send_code.return_value = {"success": True, "message_id": "test_123"}

        # 执行发送
        result = mock_auth_service.send_sms_code("13800138000", "register", "127.0.0.1")

        # 验证结果
        assert result["success"] is True
        assert "expires_in" in result
        assert "retry_after" in result
        assert result["expires_in"] == 300  # 5分钟
        assert result["retry_after"] == 60   # 60秒限流

        # 验证调用
        mock_auth_repo.get_auth_by_phone.assert_called_once_with("13800138000")
        mock_auth_service.sms_client.send_code.assert_called_once()
        mock_auth_repo.create_sms_verification.assert_called_once()

    def test_send_sms_code_invalid_phone_format(self, mock_auth_service, mock_auth_repo):
        """测试手机号格式错误"""
        mock_auth_service.repository = mock_auth_repo

        # 测试各种无效格式
        invalid_phones = [
            "123",           # 太短
            "123456789012", # 太长
            "abcdefghijk",  # 非数字
            "138-0013-8000", # 带分隔符
            "138 0013 8000", # 带空格
            "+8613800138000", # 带国际号码
        ]

        for phone in invalid_phones:
            with pytest.raises(ValidationError, match="手机号格式错误"):
                mock_auth_service.send_sms_code(phone, "register", "127.0.0.1")

    def test_send_sms_code_account_locked(self, mock_auth_service, mock_auth_repo):
        """测试账号被锁定"""
        # 设置Mock返回已锁定的验证码
        locked_verification = Mock()
        locked_verification.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_auth_repo.get_latest_verification.return_value = locked_verification

        mock_auth_service.repository = mock_auth_repo

        # 应该抛出账号锁定异常
        with pytest.raises(AccountLockedException):
            mock_auth_service.send_sms_code("13800138000", "register", "127.0.0.1")

    def test_send_sms_code_rate_limit(self, mock_auth_service, mock_auth_repo):
        """测试发送频率限制"""
        # 设置Mock返回60秒内的验证码
        recent_verification = Mock()
        recent_verification.created_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        mock_auth_repo.get_latest_verification.return_value = recent_verification

        mock_auth_service.repository = mock_auth_repo

        # 应该抛出频率限制异常
        with pytest.raises(RateLimitException):
            mock_auth_service.send_sms_code("13800138000", "register", "127.0.0.1")

    def test_send_sms_code_daily_limit(self, mock_auth_service, mock_auth_repo):
        """测试每日发送次数限制"""
        # 设置Mock返回今日已发送5次
        mock_auth_repo.count_today_sends.return_value = 5

        mock_auth_service.repository = mock_auth_repo

        # 应该抛出每日限制异常
        with pytest.raises(DailyLimitException):
            mock_auth_service.send_sms_code("13800138000", "register", "127.0.0.1")

    def test_send_sms_code_register_phone_exists(self, mock_auth_service, mock_auth_repo):
        """测试注册时手机号已存在"""
        # 设置Mock返回已存在的用户
        existing_user = Mock()
        existing_user.phone = "13800138000"
        mock_auth_repo.get_auth_by_phone.return_value = existing_user

        mock_auth_service.repository = mock_auth_repo

        # 注册场景下应该抛出手机号已存在异常
        with pytest.raises(PhoneAlreadyExistsException):
            mock_auth_service.send_sms_code("13800138000", "register", "127.0.0.1")

    def test_send_sms_code_login_phone_not_exists(self, mock_auth_service, mock_auth_repo):
        """测试登录时手机号不存在"""
        # 设置Mock返回空结果
        mock_auth_repo.get_auth_by_phone.return_value = None

        mock_auth_service.repository = mock_auth_repo

        # 登录场景下应该抛出手机号不存在异常
        with pytest.raises(PhoneNotFoundException):
            mock_auth_service.send_sms_code("13800138000", "login", "127.0.0.1")

    def test_send_sms_code_bind_phone_already_bound(self, mock_auth_service, mock_auth_repo):
        """测试绑定时手机号已被其他账号绑定"""
        # 设置Mock返回已绑定其他账号的手机号
        existing_user = Mock()
        existing_user.phone = "13800138000"
        existing_user.wechat_openid = "different_openid"
        mock_auth_repo.get_auth_by_phone.return_value = existing_user

        mock_auth_service.repository = mock_auth_repo

        # 绑定场景下应该抛出手机号已绑定异常
        with pytest.raises(PhoneAlreadyBoundException):
            mock_auth_service.send_sms_code("13800138000", "bind", "127.0.0.1", user_wechat_openid="current_openid")

    def test_generate_code_length(self, mock_auth_service):
        """测试验证码生成长度"""
        code = mock_auth_service.generate_code()

        assert len(code) == 6
        assert code.isdigit()
        assert 100000 <= int(code) <= 999999

    def test_generate_code_custom_length(self, mock_auth_service):
        """测试自定义长度的验证码生成"""
        code_4 = mock_auth_service.generate_code(4)
        code_8 = mock_auth_service.generate_code(8)

        assert len(code_4) == 4
        assert len(code_8) == 8
        assert code_4.isdigit()
        assert code_8.isdigit()


class TestVerifySMSCode:
    """验证短信验证码测试"""

    @pytest.fixture
    def mock_auth_service(self):
        """创建Mock的AuthService实例"""
        with patch('src.domains.auth.service.get_auth_db') as mock_db:
            service = AuthService(mock_db.return_value)
            return service

    @pytest.fixture
    def mock_auth_repo(self):
        """创建Mock的AuthRepository"""
        repo = Mock()
        return repo

    @pytest.fixture
    def mock_verification(self):
        """创建Mock的SMS验证码"""
        verification = Mock()
        verification.code = "123456"
        verification.scene = "register"
        verification.verified = False
        verification.error_count = 0
        verification.locked_until = None
        verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        verification.verified_at = None
        verification.ip_address = "127.0.0.1"
        return verification

    def test_verify_sms_code_register_success(self, mock_auth_service, mock_auth_repo, mock_verification):
        """测试注册场景验证成功"""
        # 设置Mock
        mock_auth_repo.get_latest_unverified.return_value = mock_verification
        mock_auth_repo.get_auth_by_phone.return_value = None
        mock_auth_service.repository = mock_auth_repo

        # 执行验证
        result = mock_auth_service.verify_sms_code("13800138000", "123456", "register")

        # 验证结果
        assert result["success"] is True
        assert result["is_new_user"] is True
        assert "access_token" in result
        assert "refresh_token" in result
        assert "user_id" in result

        # 验证调用
        mock_auth_repo.get_latest_unverified.assert_called_once()
        mock_auth_repo.get_auth_by_phone.assert_called_once()
        mock_auth_repo.update_verification.assert_called_once()

    def test_verify_sms_code_login_success(self, mock_auth_service, mock_auth_repo, mock_verification):
        """测试登录场景验证成功"""
        # 设置Mock
        existing_user = Mock()
        existing_user.id = str(uuid4())
        existing_user.phone = "13800138000"
        existing_user.jwt_version = 1

        mock_auth_repo.get_latest_unverified.return_value = mock_verification
        mock_auth_repo.get_auth_by_phone.return_value = existing_user
        mock_auth_service.repository = mock_auth_repo

        # 执行验证
        result = mock_auth_service.verify_sms_code("13800138000", "123456", "login")

        # 验证结果
        assert result["success"] is True
        assert result["is_new_user"] is False
        assert "access_token" in result

    def test_verify_sms_code_bind_success(self, mock_auth_service, mock_auth_repo, mock_verification):
        """测试绑定场景验证成功"""
        # 设置Mock
        user = Mock()
        user.id = str(uuid4())
        user.wechat_openid = "test_openid"
        user.phone = None

        mock_auth_repo.get_latest_unverified.return_value = mock_verification
        mock_auth_repo.get_auth_by_phone.return_value = None
        mock_auth_service.repository = mock_auth_repo

        # 执行验证
        result = mock_auth_service.verify_sms_code(
            "13800138000", "123456", "bind", user_wechat_openid="test_openid"
        )

        # 验证结果
        assert result["success"] is True
        assert result["upgraded"] is True
        assert "access_token" in result

    def test_verify_sms_code_not_found(self, mock_auth_service, mock_auth_repo):
        """测试验证码不存在"""
        mock_auth_repo.get_latest_unverified.return_value = None
        mock_auth_service.repository = mock_auth_repo

        # 应该抛出验证码不存在异常
        with pytest.raises(VerificationNotFoundException):
            mock_auth_service.verify_sms_code("13800138000", "123456", "register")

    def test_verify_sms_code_expired(self, mock_auth_service, mock_auth_repo, mock_verification):
        """测试验证码过期"""
        # 设置过期的验证码
        mock_verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_auth_repo.get_latest_unverified.return_value = mock_verification
        mock_auth_service.repository = mock_auth_repo

        # 应该抛出验证码过期异常
        with pytest.raises(VerificationExpiredException):
            mock_auth_service.verify_sms_code("13800138000", "123456", "register")

    def test_verify_sms_code_wrong_code(self, mock_auth_service, mock_auth_repo, mock_verification):
        """测试验证码错误"""
        # 设置Mock返回错误计数为3，触发锁定
        mock_verification.error_count = 3
        mock_auth_repo.get_latest_unverified.return_value = mock_verification
        mock_auth_service.repository = mock_auth_repo

        # 第4次错误应该抛出账号锁定异常
        with pytest.raises(AccountLockedException):
            mock_auth_service.verify_sms_code("13800138000", "654321", "register")

    def test_verify_sms_code_already_verified(self, mock_auth_service, mock_auth_repo, mock_verification):
        """测试验证码已验证"""
        # 设置已验证的验证码
        mock_verification.verified = True
        mock_verification.verified_at = datetime.now(timezone.utc)
        mock_auth_repo.get_latest_unverified.return_value = mock_verification
        mock_auth_service.repository = mock_auth_repo

        # 应该抛出验证码不存在异常（因为已验证）
        with pytest.raises(VerificationNotFoundException):
            mock_auth_service.verify_sms_code("13800138000", "123456", "register")

    def test_verify_sms_code_different_scene(self, mock_auth_service, mock_auth_repo, mock_verification):
        """测试验证码场景不匹配"""
        # 设置不同场景的验证码
        mock_verification.scene = "login"
        mock_auth_repo.get_latest_unverified.return_value = mock_verification
        mock_auth_service.repository = mock_auth_repo

        # 应该抛出验证码不存在异常
        with pytest.raises(VerificationNotFoundException):
            mock_auth_service.verify_sms_code("13800138000", "123456", "register")

    def test_is_code_expired(self, mock_auth_service):
        """测试验证码过期检查"""
        now = datetime.now(timezone.utc)

        # 未过期的验证码
        fresh_verification = Mock()
        fresh_verification.created_at = now - timedelta(minutes=2)
        assert mock_auth_service.is_code_expired(fresh_verification) is False

        # 过期的验证码
        expired_verification = Mock()
        expired_verification.created_at = now - timedelta(minutes=10)
        assert mock_auth_service.is_code_expired(expired_verification) is True

    def test_check_phone_lock(self, mock_auth_service):
        """测试手机号锁定检查"""
        now = datetime.now(timezone.utc)

        # 未锁定的手机号
        unlocked_verification = Mock()
        unlocked_verification.locked_until = None
        assert mock_auth_service._check_phone_lock(unlocked_verification) is False

        # 已锁定的手机号
        locked_verification = Mock()
        locked_verification.locked_until = now + timedelta(hours=1)

        with pytest.raises(AccountLockedException):
            mock_auth_service._check_phone_lock(locked_verification)

        # 锁定已过期的手机号
        expired_lock_verification = Mock()
        expired_lock_verification.locked_until = now - timedelta(minutes=10)
        assert mock_auth_service._check_phone_lock(expired_lock_verification) is False

    def test_check_rate_limit(self, mock_auth_service):
        """测试发送频率限制检查"""
        now = datetime.now(timezone.utc)

        # 未超过60秒限制
        old_verification = Mock()
        old_verification.created_at = now - timedelta(minutes=2)
        assert mock_auth_service._check_rate_limit(old_verification) is False

        # 超过60秒限制
        recent_verification = Mock()
        recent_verification.created_at = now - timedelta(seconds=30)

        with pytest.raises(RateLimitException):
            mock_auth_service._check_rate_limit(recent_verification)

    def test_check_daily_limit(self, mock_auth_service):
        """测试每日发送次数限制检查"""
        # 未超过每日限制
        assert mock_auth_service._check_daily_limit(3) is False
        assert mock_auth_service._check_daily_limit(4) is False

        # 超过每日限制
        with pytest.raises(DailyLimitException):
            mock_auth_service._check_daily_limit(5)


class TestServiceIntegration:
    """Service层集成测试"""

    @pytest.fixture
    def service_with_mocks(self):
        """创建带有完整Mock的Service实例"""
        with patch('src.domains.auth.service.get_auth_db') as mock_db:
            with patch('src.domains.auth.sms_client.get_sms_client') as mock_client:
                service = AuthService(mock_db.return_value)
                service.repository = Mock()
                service.sms_client = mock_client.return_value
                return service

    def test_complete_sms_flow(self, service_with_mocks):
        """测试完整的SMS认证流程"""
        service = service_with_mocks
        user_id = str(uuid4())

        # 1. 发送验证码成功
        service.repository.get_auth_by_phone.return_value = None
        service.repository.count_today_sends.return_value = 0
        service.repository.get_latest_verification.return_value = None
        service.sms_client.send_code.return_value = {"success": True, "message_id": "test_123"}

        send_result = service.send_sms_code("13800138000", "register", "127.0.0.1")
        assert send_result["success"] is True

        # 2. 验证验证码成功
        verification = Mock()
        verification.code = "123456"
        verification.scene = "register"
        verification.verified = False
        verification.error_count = 0
        verification.locked_until = None
        verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        service.repository.get_latest_unverified.return_value = verification
        service.repository.get_auth_by_phone.return_value = None

        with patch.object(service, 'generate_code', return_value="123456"):
            verify_result = service.verify_sms_code("13800138000", "123456", "register")
            assert verify_result["success"] is True
            assert verify_result["is_new_user"] is True

    def test_error_accumulation_and_lock(self, service_with_mocks):
        """测试错误累计和锁定机制"""
        service = service_with_mocks

        # 模拟3次错误后的第4次验证
        verification = Mock()
        verification.code = "123456"
        verification.scene = "register"
        verification.error_count = 3  # 已经错误3次
        verification.locked_until = None
        verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        service.repository.get_latest_unverified.return_value = verification

        # 第4次错误应该触发锁定
        with pytest.raises(AccountLockException):
            service.verify_sms_code("13800138000", "654321", "register")

        # 验证错误计数增加到4次
        updated_verification = Mock()
        updated_verification.error_count = 4
        service.repository.update_verification.assert_called_once()

        # 验证锁定时间设置
        call_args = service.repository.update_verification.call_args[0][0]
        assert call_args.error_count == 4
        assert call_args.locked_until is not None

    def test_concurrent_verification_handling(self, service_with_mocks):
        """测试并发验证处理"""
        service = service_with_mocks

        # 模拟有多个未验证的验证码，应该取最新的
        old_verification = Mock()
        old_verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        old_verification.code = "111111"

        new_verification = Mock()
        new_verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        new_verification.code = "123456"

        # Mock返回最新验证码
        service.repository.get_latest_unverified.return_value = new_verification

        # 应该使用最新的验证码进行验证
        service.verify_sms_code("13800138000", "123456", "register")

        # 验证调用的是最新验证码
        service.repository.get_latest_unverified.assert_called_once_with("13800138000", "register")

    def test_jwt_token_generation_and_validation(self, service_with_mocks):
        """测试JWT令牌生成和验证"""
        service = service_with_mocks

        # Mock用户数据
        user_id = str(uuid4())
        user = Mock()
        user.id = user_id
        user.jwt_version = 1

        service.repository.get_auth_by_phone.return_value = user

        # 模拟验证码验证成功，生成令牌
        verification = Mock()
        verification.code = "123456"
        verification.scene = "login"
        verification.verified = False
        verification.error_count = 0
        verification.locked_until = None
        verification.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        service.repository.get_latest_unverified.return_value = verification

        with patch.object(service, 'generate_code', return_value="123456"):
            result = service.verify_sms_code("13800138000", "123456", "login")

            # 验证令牌生成
            assert "access_token" in result
            assert "refresh_token" in result
            assert "expires_in" in result

            # 验证令牌格式
            token = result["access_token"]
            assert isinstance(token, str)
            assert len(token) > 20  # JWT令牌应该有足够的长度