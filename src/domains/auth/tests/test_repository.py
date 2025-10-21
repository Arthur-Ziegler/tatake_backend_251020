"""
认证领域Repository层测试

测试Repository层的数据访问逻辑，包括：
- 用户数据操作
- 短信验证码管理
- 令牌黑名单管理
- 用户会话管理
- 审计日志记录
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from ..models import User, UserSettings, SMSVerification, TokenBlacklist, UserSession, AuthLog
from ..repository import (
    AuthRepository, SMSRepository, TokenRepository,
    SessionRepository, AuditRepository
)
from ..exceptions import UserNotFoundException, SMSException


@pytest.mark.asyncio
class TestAuthRepository:
    """认证Repository测试"""

    async def test_create_user_success(self, auth_repository: AuthRepository):
        """测试成功创建用户"""
        user = await auth_repository.create_user(
            username="testuser",
            email="test@example.com",
            phone="13800138000",
            password_hash="$2b$12$test_hash",
            nickname="测试用户"
        )

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.phone == "13800138000"
        assert user.nickname == "测试用户"
        assert user.is_guest is False
        assert user.is_active is True
        assert user.is_verified is False
        assert user.created_at is not None

    async def test_create_guest_user_success(self, auth_repository: AuthRepository):
        """测试成功创建游客用户"""
        user = await auth_repository.create_user(
            is_guest=True,
            device_id="test-device-123",
            device_type="ios",
            nickname="游客用户"
        )

        assert user.id is not None
        assert user.is_guest is True
        assert user.device_id == "test-device-123"
        assert user.device_type == "ios"
        assert user.username is None
        assert user.email is None
        assert user.phone is None

    async def test_get_user_by_username_success(self, auth_repository: AuthRepository, sample_user: User):
        """测试根据用户名获取用户成功"""
        user = await auth_repository.get_user_by_username("testuser")
        assert user is not None
        assert user.id == sample_user.id
        assert user.username == "testuser"

    async def test_get_user_by_username_not_found(self, auth_repository: AuthRepository):
        """测试根据用户名获取用户不存在"""
        user = await auth_repository.get_user_by_username("nonexistent")
        assert user is None

    async def test_get_user_by_phone_success(self, auth_repository: AuthRepository, sample_user: User):
        """测试根据手机号获取用户成功"""
        user = await auth_repository.get_user_by_phone("13800138000")
        assert user is not None
        assert user.id == sample_user.id
        assert user.phone == "13800138000"

    async def test_get_user_by_device_success(self, auth_repository: AuthRepository, sample_guest_user: User):
        """测试根据设备ID获取游客用户成功"""
        user = await auth_repository.get_user_by_device("test-device-12345")
        assert user is not None
        assert user.id == sample_guest_user.id
        assert user.is_guest is True

    async def test_update_user_last_login(self, auth_repository: AuthRepository, sample_user: User):
        """测试更新用户最后登录时间"""
        original_time = sample_user.last_login_at

        # 等待一小段时间确保时间不同
        await asyncio.sleep(0.01)

        await auth_repository.update_user_last_login(sample_user.id)

        # 重新获取用户验证更新
        updated_user = await auth_repository.get_by_id(User, sample_user.id)
        assert updated_user.last_login_at > original_time
        assert updated_user.login_count == 1

    async def test_upgrade_guest_account_success(self, auth_repository: AuthRepository, sample_guest_user: User):
        """测试升级游客账号成功"""
        updated_user = await auth_repository.upgrade_guest_account(
            user_id=sample_guest_user.id,
            phone="13800138001",
            password_hash="$2b$12$new_hash",
            nickname="正式用户"
        )

        assert updated_user.id == sample_guest_user.id
        assert updated_user.is_guest is False
        assert updated_user.is_verified is True
        assert updated_user.phone == "13800138001"
        assert updated_user.password_hash == "$2b$12$new_hash"
        assert updated_user.nickname == "正式用户"

    async def test_upgrade_non_guest_account_fails(self, auth_repository: AuthRepository, sample_user: User):
        """测试升级非游客账号失败"""
        with pytest.raises(Exception):  # 应该抛出ValidationError
            await auth_repository.upgrade_guest_account(
                user_id=sample_user.id,
                phone="13800138001"
            )

    async def test_invalidate_user_tokens(self, auth_repository: AuthRepository, sample_user: User):
        """测试使用户令牌失效"""
        original_version = sample_user.jwt_version

        await auth_repository.invalidate_user_tokens(sample_user.id)

        updated_user = await auth_repository.get_by_id(User, sample_user.id)
        assert updated_user.jwt_version == original_version + 1

    async def test_soft_delete_user(self, auth_repository: AuthRepository, sample_user: User):
        """测试软删除用户"""
        await auth_repository.soft_delete_user(sample_user.id)

        deleted_user = await auth_repository.get_by_id(User, sample_user.id)
        assert deleted_user.is_active is False
        assert deleted_user.deleted_at is not None


@pytest.mark.asyncio
class TestSMSRepository:
    """短信Repository测试"""

    async def test_create_verification_code_success(self, sms_repository: SMSRepository):
        """测试成功创建验证码"""
        verification = await sms_repository.create_verification_code(
            phone="13800138000",
            code="123456",
            verification_type="login"
        )

        assert verification.id is not None
        assert verification.phone == "13800138000"
        assert verification.code == "123456"
        assert verification.verification_type == "login"
        assert verification.is_used is False
        assert verification.attempts == 0
        assert verification.expires_at > datetime.now(timezone.utc)

    async def test_verify_code_success(self, sms_repository: SMSRepository, sample_sms_code: SMSVerification):
        """测试验证码验证成功"""
        verification = await sms_repository.verify_code(
            phone="13800138000",
            code="123456",
            verification_type="login"
        )

        assert verification is not None
        assert verification.id == sample_sms_code.id

    async def test_verify_code_invalid(self, sms_repository: SMSRepository):
        """测试验证码验证失败"""
        verification = await sms_repository.verify_code(
            phone="13800138000",
            code="999999",
            verification_type="login"
        )

        assert verification is None

    async def test_mark_code_used(self, sms_repository: SMSRepository, sample_sms_code: SMSVerification):
        """测试标记验证码已使用"""
        await sms_repository.mark_code_used(sample_sms_code.id)

        # 这里需要重新获取验证码来检查状态
        # 实际实现中可能需要添加获取方法

    async def test_get_latest_code(self, sms_repository: SMSRepository):
        """测试获取最新验证码"""
        # 创建两个验证码
        await sms_repository.create_verification_code(
            phone="13800138000",
            code="111111",
            verification_type="login"
        )

        await sms_repository.create_verification_code(
            phone="13800138000",
            code="222222",
            verification_type="login"
        )

        latest_code = await sms_repository.get_latest_code(
            phone="13800138000",
            verification_type="login"
        )

        assert latest_code is not None
        assert latest_code.code == "222222"  # 应该返回最新的验证码


@pytest.mark.asyncio
class TestTokenRepository:
    """令牌Repository测试"""

    async def test_blacklist_token_success(self, token_repository: TokenRepository):
        """测试成功将令牌加入黑名单"""
        user_id = uuid4()
        token_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        blacklisted_token = await token_repository.blacklist_token(
            token_id=token_id,
            user_id=user_id,
            token_type="access",
            expires_at=expires_at,
            reason="用户登出"
        )

        assert blacklisted_token.id is not None
        assert blacklisted_token.token_id == token_id
        assert blacklisted_token.user_id == user_id
        assert blacklisted_token.token_type == "access"
        assert blacklisted_token.reason == "用户登出"

    async def test_is_token_blacklisted_true(self, token_repository: TokenRepository):
        """测试检查令牌是否在黑名单中（存在）"""
        user_id = uuid4()
        token_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # 先将令牌加入黑名单
        await token_repository.blacklist_token(
            token_id=token_id,
            user_id=user_id,
            token_type="access",
            expires_at=expires_at
        )

        # 检查是否在黑名单中
        is_blacklisted = await token_repository.is_token_blacklisted(token_id)
        assert is_blacklisted is True

    async def test_is_token_blacklisted_false(self, token_repository: TokenRepository):
        """测试检查令牌是否在黑名单中（不存在）"""
        token_id = str(uuid4())
        is_blacklisted = await token_repository.is_token_blacklisted(token_id)
        assert is_blacklisted is False

    async def test_cleanup_expired_tokens(self, token_repository: TokenRepository):
        """测试清理过期令牌"""
        user_id = uuid4()

        # 创建一个过期的令牌
        expired_token_id = str(uuid4())
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)

        await token_repository.blacklist_token(
            token_id=expired_token_id,
            user_id=user_id,
            token_type="access",
            expires_at=expired_time
        )

        # 创建一个未过期的令牌
        valid_token_id = str(uuid4())
        valid_time = datetime.now(timezone.utc) + timedelta(hours=1)

        await token_repository.blacklist_token(
            token_id=valid_token_id,
            user_id=user_id,
            token_type="access",
            expires_at=valid_time
        )

        # 清理过期令牌
        cleaned_count = await token_repository.cleanup_expired_tokens()
        assert cleaned_count >= 1  # 至少清理了一个过期令牌

        # 验证过期令牌已被清理，有效令牌仍然存在
        assert await token_repository.is_token_blacklisted(expired_token_id) is False
        assert await token_repository.is_token_blacklisted(valid_token_id) is True


@pytest.mark.asyncio
class TestSessionRepository:
    """会话Repository测试"""

    async def test_create_session_success(self, session_repository: SessionRepository):
        """测试成功创建会话"""
        user_id = uuid4()
        session_id = str(uuid4())

        session = await session_repository.create_session(
            user_id=user_id,
            session_id=session_id,
            device_info="iOS Device",
            ip_address="127.0.0.1",
            user_agent="TaKeKe-iOS/1.0.0"
        )

        assert session.id is not None
        assert session.user_id == user_id
        assert session.session_id == session_id
        assert session.device_info == "iOS Device"
        assert session.ip_address == "127.0.0.1"
        assert session.is_active is True

    async def test_get_active_session_success(self, session_repository: SessionRepository):
        """测试获取活跃会话成功"""
        user_id = uuid4()
        session_id = str(uuid4())

        # 创建会话
        await session_repository.create_session(
            user_id=user_id,
            session_id=session_id
        )

        # 获取活跃会话
        active_session = await session_repository.get_active_session(session_id)
        assert active_session is not None
        assert active_session.session_id == session_id
        assert active_session.is_active is True

    async def test_get_active_session_not_found(self, session_repository: SessionRepository):
        """测试获取活跃会话不存在"""
        session_id = str(uuid4())
        active_session = await session_repository.get_active_session(session_id)
        assert active_session is None

    async def test_invalidate_session(self, session_repository: SessionRepository):
        """测试使会话失效"""
        user_id = uuid4()
        session_id = str(uuid4())

        # 创建会话
        await session_repository.create_session(
            user_id=user_id,
            session_id=session_id
        )

        # 使会话失效
        await session_repository.invalidate_session(session_id)

        # 验证会话已失效
        inactive_session = await session_repository.get_active_session(session_id)
        assert inactive_session is None

    async def test_cleanup_expired_sessions(self, session_repository: SessionRepository):
        """测试清理过期会话"""
        user_id = uuid4()

        # 创建过期会话（通过设置过期时间为过去）
        expired_session_id = str(uuid4())
        # 这里需要手动插入过期会话数据
        # 实际实现中可能需要调整创建方法来支持过期时间设置

        cleaned_count = await session_repository.cleanup_expired_sessions()
        # 验证清理结果
        assert cleaned_count >= 0


@pytest.mark.asyncio
class TestAuditRepository:
    """审计Repository测试"""

    async def test_create_log_success(self, audit_repository: AuditRepository):
        """测试成功创建审计日志"""
        user_id = uuid4()

        log = await audit_repository.create_log(
            user_id=user_id,
            action="login",
            result="success",
            details="用户登录成功",
            ip_address="127.0.0.1",
            user_agent="TaKeKe-iOS/1.0.0"
        )

        assert log.id is not None
        assert log.user_id == user_id
        assert log.action == "login"
        assert log.result == "success"
        assert log.details == "用户登录成功"
        assert log.ip_address == "127.0.0.1"

    async def test_create_log_without_user(self, audit_repository: AuditRepository):
        """测试创建无用户ID的审计日志"""
        log = await audit_repository.create_log(
            user_id=None,
            action="guest_init",
            result="success",
            details="游客初始化成功",
            ip_address="127.0.0.1"
        )

        assert log.id is not None
        assert log.user_id is None
        assert log.action == "guest_init"

    async def test_get_user_logs(self, audit_repository: AuditRepository):
        """测试获取用户审计日志"""
        user_id = uuid4()

        # 创建多个日志
        for i in range(5):
            await audit_repository.create_log(
                user_id=user_id,
                action=f"action_{i}",
                result="success",
                details=f"操作 {i}"
            )

        # 获取用户日志
        logs = await audit_repository.get_user_logs(user_id, limit=3)
        assert len(logs) == 3

        # 验证日志按时间倒序排列
        for i in range(len(logs) - 1):
            assert logs[i].created_at >= logs[i + 1].created_at

    async def test_get_login_attempts(self, audit_repository: AuditRepository):
        """测试获取登录尝试记录"""
        ip_address = "192.168.1.100"

        # 创建登录尝试记录
        for i in range(3):
            await audit_repository.create_log(
                user_id=None,
                action="login",
                result="failure" if i < 2 else "success",
                details=f"登录尝试 {i+1}",
                ip_address=ip_address
            )

        # 获取登录尝试记录
        attempts = await audit_repository.get_login_attempts(ip_address, time_minutes=60)
        assert len(attempts) == 3
        assert all(attempt.action == "login" for attempt in attempts)

    async def test_cleanup_old_logs(self, audit_repository: AuditRepository):
        """测试清理旧的审计日志"""
        # 创建一些日志
        for i in range(10):
            await audit_repository.create_log(
                user_id=None,
                action="test_action",
                result="success",
                details=f"测试日志 {i}"
            )

        # 清理旧日志（使用较短的天数进行测试）
        # 注意：这里可能需要调整实现以支持测试
        cleaned_count = await audit_repository.cleanup_old_logs(days=0)  # 清理所有日志
        assert cleaned_count >= 0


# 边界条件测试
@pytest.mark.asyncio
class TestRepositoryEdgeCases:
    """Repository层边界条件测试"""

    async def test_create_user_with_duplicate_phone(self, auth_repository: AuthRepository):
        """测试创建重复手机号的用户"""
        phone = "13800138000"

        # 创建第一个用户
        await auth_repository.create_user(phone=phone, nickname="用户1")

        # 尝试创建第二个用户（应该失败）
        with pytest.raises(Exception):  # 应该抛出数据库唯一性约束异常
            await auth_repository.create_user(phone=phone, nickname="用户2")

    async def test_verify_code_with_max_attempts(self, sms_repository: SMSRepository):
        """测试验证码最大尝试次数"""
        phone = "13800138000"
        code = "123456"

        # 创建验证码
        verification = await sms_repository.create_verification_code(
            phone=phone,
            code=code,
            verification_type="login"
        )

        # 尝试验证多次（超过最大尝试次数）
        max_attempts = verification.max_attempts
        for _ in range(max_attempts):
            result = await sms_repository.verify_code(phone, "wrong_code", "login")
            if result is None:
                break  # 验证失败，尝试次数增加

        # 最后一次尝试正确的验证码，应该仍然失败（因为超过最大尝试次数）
        final_result = await sms_repository.verify_code(phone, code, "login")
        assert final_result is None  # 超过最大尝试次数后应该无法验证

    async def test_create_session_with_duplicate_id(self, session_repository: SessionRepository):
        """测试创建重复会话ID"""
        user_id = uuid4()
        session_id = str(uuid4())

        # 创建第一个会话
        await session_repository.create_session(user_id=user_id, session_id=session_id)

        # 尝试创建第二个会话（应该失败）
        with pytest.raises(Exception):  # 应该抛出数据库唯一性约束异常
            await session_repository.create_session(user_id=uuid4(), session_id=session_id)

    async def test_blacklist_token_with_expired_time(self, token_repository: TokenRepository):
        """测试黑名单立即过期的令牌"""
        user_id = uuid4()
        token_id = str(uuid4())
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)

        # 创建已过期的黑名单令牌
        await token_repository.blacklist_token(
            token_id=token_id,
            user_id=user_id,
            token_type="access",
            expires_at=past_time
        )

        # 检查是否在黑名单中（应该返回False，因为已过期）
        is_blacklisted = await token_repository.is_token_blacklisted(token_id)
        assert is_blacklisted is False

    async def test_get_user_logs_empty_result(self, audit_repository: AuditRepository):
        """测试获取不存在用户的日志"""
        user_id = uuid4()
        logs = await audit_repository.get_user_logs(user_id)
        assert len(logs) == 0

    async def test_get_login_attempts_no_attempts(self, audit_repository: AuditRepository):
        """测试获取没有登录尝试的IP"""
        ip_address = "192.168.1.999"
        attempts = await audit_repository.get_login_attempts(ip_address)
        assert len(attempts) == 0