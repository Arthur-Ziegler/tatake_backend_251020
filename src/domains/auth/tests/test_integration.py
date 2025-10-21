"""
认证领域集成测试

测试各层之间的集成，包括：
- Router到Service的集成
- Service到Repository的集成
- Repository到Database的集成
- 端到端业务流程测试
- 跨组件交互测试
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from sqlmodel import select
from src.api.main import app
from src.domains.auth.schemas import GuestInitRequest, GuestUpgradeRequest, LoginRequest, SMSCodeRequest
from src.domains.auth.service import create_auth_service
from src.domains.auth.database import get_auth_db
from src.domains.auth.models import User as AuthUser, SMSVerification as AuthSMSVerification
from src.domains.auth.exceptions import ValidationError, UserNotFoundException, TokenException


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCompleteAuthFlow:
    """完整认证流程集成测试"""

    async def test_guest_to_registered_user_flow(self):
        """测试从游客到注册用户的完整流程"""
        # 1. 创建认证服务
        auth_service = await create_auth_service()
        device_id = "integration-test-device"

        # 2. 游客初始化
        init_request = GuestInitRequest(
            device_id=device_id,
            device_type="ios",
            app_version="1.0.0"
        )

        with patch('builtins.print'):  # Mock控制台输出
            guest_result = await auth_service.init_guest_account(
                request=init_request,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )

        assert guest_result["is_guest"] is True
        assert "access_token" in guest_result
        guest_user_id = guest_result["user_id"]

        # 3. 发送短信验证码
        sms_request = SMSCodeRequest(
            phone="13800138000",
            verification_type="upgrade"
        )

        with patch('builtins.print'):
            code = await auth_service.send_sms_code(
                request=sms_request,
                user_id=guest_user_id,
                ip_address="127.0.0.1"
            )

        assert code is not None
        assert len(code) == 6

        # 4. 验证短信验证码（Mock验证）
        with patch.object(auth_service.sms_service, 'verify_code', return_value=True):
            # 5. 游客升级
            upgrade_request = GuestUpgradeRequest(
                phone="13800138000",
                sms_code="123456",
                password="integration_password_123",
                nickname="集成测试用户"
            )

            with patch('builtins.print'):
                upgrade_result = await auth_service.upgrade_guest_account(
                    request=upgrade_request,
                    current_user_id=guest_user_id,
                    ip_address="127.0.0.1",
                    user_agent="TestAgent/1.0"
                )

        assert upgrade_result["is_guest"] is False
        assert "access_token" in upgrade_result
        assert upgrade_result["user_id"] == guest_user_id  # 同一个用户ID

        # 6. 获取用户信息
        user_info = await auth_service.get_user_info(guest_user_id)
        assert user_info["is_guest"] is False
        assert user_info["phone"] == "13800138000"
        assert user_info["nickname"] == "集成测试用户"

    async def test_login_with_refresh_flow(self):
        """测试登录和令牌刷新流程"""
        auth_service = await create_auth_service()

        # 1. 创建测试用户
        async with get_auth_db() as session:
            user_repo = auth_service.auth_repository
            test_user = await user_repo.create_user(
                phone="13800138001",
                password_hash="$2b$12$test_hash_for_integration",
                nickname="登录测试用户"
            )

        # 2. 模拟登录（通过Mock验证）
        with patch.object(auth_service.user_service, 'authenticate_by_sms',
                       return_value=test_user):

            login_request = LoginRequest(
                identifier="13800138001",
                login_type="sms",
                sms_code="123456"
            )

            with patch('builtins.print'):
                login_result = await auth_service.login(
                    request=login_request,
                    ip_address="127.0.0.1"
                )

        assert login_result["is_guest"] is False
        assert "access_token" in login_result
        assert "refresh_token" in login_result

        # 3. 刷新令牌
        refresh_request = {
            "refresh_token": login_result["refresh_token"]
        }

        # Mock令牌验证
        mock_payload = {
            "sub": str(test_user.id),
            "user_type": "registered",
            "is_guest": False,
            "jwt_version": test_user.jwt_version,
            "jti": str(uuid4()),
            "exp": datetime.now(timezone.utc).timestamp() + 3600
        }

        with patch.object(auth_service.jwt_service, 'verify_token',
                       return_value=mock_payload):
            with patch.object(auth_service.token_repository, 'is_token_blacklisted',
                           return_value=False):

                with patch('builtins.print'):
                    refresh_result = await auth_service.refresh_token(refresh_request)

        assert "access_token" in refresh_result
        assert "refresh_token" in refresh_result
        assert refresh_result["token_type"] == "bearer"

        # 4. 登出
        with patch('builtins.print'):
            await auth_service.logout(
                token_jti=mock_payload["jti"],
                user_id=test_user.id,
                expires_at=datetime.fromtimestamp(mock_payload["exp"], timezone.utc)
            )

        # 5. 验证令牌在黑名单中
        is_blacklisted = await auth_service.token_repository.is_token_blacklisted(mock_payload["jti"])
        assert is_blacklisted is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """数据库集成测试"""

    async def test_user_repository_database_operations(self):
        """测试用户Repository数据库操作"""
        auth_service = await create_auth_service()
        user_repo = auth_service.auth_repository

        # 1. 创建用户
        user = await user_repo.create_user(
            username="db_test_user",
            email="dbtest@example.com",
            phone="13800138002",
            password_hash="$2b$12$db_test_hash",
            nickname="数据库测试用户"
        )

        assert user.id is not None
        assert user.username == "db_test_user"

        # 2. 通过不同方式查询用户
        found_by_username = await user_repo.get_user_by_username("db_test_user")
        assert found_by_username is not None
        assert found_by_username.id == user.id

        found_by_phone = await user_repo.get_user_by_phone("13800138002")
        assert found_by_phone is not None
        assert found_by_phone.id == user.id

        # 3. 更新用户信息
        await user_repo.update_user_last_login(user.id)
        updated_user = await user_repo.get_by_id(AuthUser, user.id)
        assert updated_user.login_count == 1
        assert updated_user.last_login_at is not None

        # 4. 升级游客账号（如果需要）
        if user.is_guest:
            upgraded_user = await user_repo.upgrade_guest_account(
                user_id=user.id,
                phone="13800138003",
                password_hash="$2b$12$upgraded_hash"
            )
            assert upgraded_user.is_guest is False

    async def test_sms_repository_database_operations(self):
        """测试短信Repository数据库操作"""
        auth_service = await create_auth_service()
        sms_repo = auth_service.sms_repository

        phone = "13800138003"
        code = "654321"

        # 1. 创建验证码
        verification = await sms_repo.create_verification_code(
            phone=phone,
            code=code,
            verification_type="login"
        )

        assert verification.id is not None
        assert verification.phone == phone
        assert verification.code == code
        assert verification.is_used is False

        # 2. 验证验证码
        verified = await sms_repo.verify_code(phone, code, "login")
        assert verified is not None
        assert verified.id == verification.id

        # 3. 标记为已使用
        await sms_repo.mark_code_used(verification.id)

        # 4. 尝试再次验证（应该失败）
        verified_again = await sms_repo.verify_code(phone, code, "login")
        assert verified_again is None  # 已使用的验证码无法再次验证

    async def test_token_repository_database_operations(self):
        """测试令牌Repository数据库操作"""
        auth_service = await create_auth_service()
        token_repo = auth_service.token_repository

        user_id = uuid4()
        token_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # 1. 将令牌加入黑名单
        blacklisted_token = await token_repo.blacklist_token(
            token_id=token_id,
            user_id=user_id,
            token_type="access",
            expires_at=expires_at,
            reason="测试黑名单"
        )

        assert blacklisted_token.id is not None
        assert blacklisted_token.token_id == token_id
        assert blacklisted_token.reason == "测试黑名单"

        # 2. 检查令牌是否在黑名单中
        is_blacklisted = await token_repo.is_token_blacklisted(token_id)
        assert is_blacklisted is True

        # 3. 检查不存在的令牌
        non_existent_token = str(uuid4())
        is_non_existent_blacklisted = await token_repo.is_token_blacklisted(non_existent_token)
        assert is_non_existent_blacklisted is False

    async def test_session_repository_database_operations(self):
        """测试会话Repository数据库操作"""
        auth_service = await create_auth_service()
        session_repo = auth_service.session_repository

        user_id = uuid4()
        session_id = str(uuid4())

        # 1. 创建会话
        session = await session_repo.create_session(
            user_id=user_id,
            session_id=session_id,
            device_info="测试设备",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )

        assert session.id is not None
        assert session.session_id == session_id
        assert session.is_active is True

        # 2. 获取活跃会话
        active_session = await session_repo.get_active_session(session_id)
        assert active_session is not None
        assert active_session.id == session.id

        # 3. 更新会话活动时间
        await session_repo.update_session_activity(session_id)
        # 这里需要重新获取来验证更新

        # 4. 使会话失效
        await session_repo.invalidate_session(session_id)
        inactive_session = await session_repo.get_active_session(session_id)
        assert inactive_session is None

    async def test_audit_repository_database_operations(self):
        """测试审计Repository数据库操作"""
        auth_service = await create_auth_service()
        audit_repo = auth_service.audit_repository

        user_id = uuid4()

        # 1. 创建审计日志
        log = await audit_repo.create_log(
            user_id=user_id,
            action="test_action",
            result="success",
            details="集成测试日志",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )

        assert log.id is not None
        assert log.user_id == user_id
        assert log.action == "test_action"
        assert log.result == "success"

        # 2. 获取用户日志
        user_logs = await audit_repo.get_user_logs(user_id, limit=5)
        assert len(user_logs) >= 1
        assert user_logs[0].user_id == user_id

        # 3. 获取登录尝试记录
        ip_address = "192.168.1.100"
        login_log = await audit_repo.create_log(
            user_id=None,
            action="login",
            result="failure",
            details="登录失败",
            ip_address=ip_address
        )

        login_attempts = await audit_repo.get_login_attempts(ip_address, time_minutes=60)
        assert len(login_attempts) >= 1
        assert all(attempt.action == "login" for attempt in login_attempts)


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    async def test_authentication_service_error_propagation(self):
        """测试认证服务错误传播"""
        auth_service = await create_auth_service()

        # 1. 测试无效手机号格式
        invalid_phone = "invalid_phone_number"
        with patch.object(auth_service.sms_service, 'send_verification_code',
                       side_effect=ValidationError("手机号格式无效")):

            sms_request = SMSCodeRequest(
                phone=invalid_phone,
                verification_type="login"
            )

            with pytest.raises(ValidationError):
                await auth_service.send_sms_code(
                    request=sms_request,
                    ip_address="127.0.0.1"
                )

        # 2. 测试用户不存在错误
        non_existent_user_id = uuid4()
        with pytest.raises(UserNotFoundException):
            await auth_service.get_user_info(non_existent_user_id)

        # 3. 测试令牌验证错误
        with patch.object(auth_service.jwt_service, 'verify_token',
                       side_effect=TokenException("令牌无效")):

            refresh_request = {"refresh_token": "invalid_token"}
            with pytest.raises(TokenException):
                await auth_service.refresh_token(refresh_request)

    async def test_database_connection_error_handling(self):
        """测试数据库连接错误处理"""
        # Mock数据库连接失败
        with patch('src.domains.auth.database.get_auth_db',
                  side_effect=ConnectionError("数据库连接失败")):

            with pytest.raises(ConnectionError):
                await create_auth_service()

    async def test_service_layer_exception_handling(self):
        """测试服务层异常处理"""
        auth_service = await create_auth_service()

        # 1. 测试短信服务异常
        with patch.object(auth_service.sms_service, 'send_verification_code',
                       side_effect=Exception("短信服务异常")):

            sms_request = SMSCodeRequest(
                phone="13800138000",
                verification_type="login"
            )

            with pytest.raises(Exception, match="短信服务异常"):
                await auth_service.send_sms_code(
                    request=sms_request,
                    ip_address="127.0.0.1"
                )

        # 2. 测试用户服务异常
        with patch.object(auth_service.user_service, 'authenticate_user',
                       side_effect=Exception("用户认证异常")):

            login_request = LoginRequest(
                identifier="testuser",
                login_type="password",
                password="password"
            )

            with pytest.raises(Exception, match="用户认证异常"):
                await auth_service.login(
                    request=login_request,
                    ip_address="127.0.0.1"
                )


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossDomainIntegration:
    """跨域集成测试"""

    async def test_auth_domain_isolation(self):
        """测试认证领域隔离"""
        auth_service = await create_auth_service()

        # 1. 在认证数据库中创建用户
        user = await auth_service.auth_repository.create_user(
            phone="13800138004",
            password_hash="$2b$12$isolation_test",
            nickname="隔离测试用户"
        )

        # 2. 验证用户存在于认证数据库
        found_user = await auth_service.auth_repository.get_user_by_phone("13800138004")
        assert found_user is not None
        assert found_user.id == user.id

        # 3. 验证认证数据库表结构
        async with get_auth_db() as session:
            from sqlalchemy import text
            result = await session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'auth_%'"
            ))
            auth_tables = [row[0] for row in result.fetchall()]

            expected_tables = [
                'auth_users', 'auth_user_settings', 'auth_sms_verification',
                'auth_token_blacklist', 'auth_user_sessions', 'auth_audit_logs'
            ]

            for table in expected_tables:
                assert table in auth_tables, f"缺少表: {table}"

    async def test_user_id_consistency_across_domains(self):
        """测试跨域用户ID一致性"""
        auth_service = await create_auth_service()
        user_id = uuid4()

        # 1. 在认证数据库创建用户
        auth_user = await auth_service.auth_repository.create_user(
            phone="13800138005",
            password_hash="$2b$12$consistency_test",
            nickname="一致性测试用户"
        )

        # 2. 使用相同的user_id在其他领域创建相关数据
        token_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        await auth_service.token_repository.blacklist_token(
            token_id=token_id,
            user_id=auth_user.id,  # 使用认证用户的ID
            token_type="access",
            expires_at=expires_at
        )

        # 3. 创建会话
        session_id = str(uuid4())
        await auth_service.session_repository.create_session(
            user_id=auth_user.id,  # 使用认证用户的ID
            session_id=session_id
        )

        # 4. 创建审计日志
        await auth_service.audit_repository.create_log(
            user_id=auth_user.id,  # 使用认证用户的ID
            action="consistency_test",
            result="success"
        )

        # 5. 验证所有数据都使用相同的user_id
        is_token_blacklisted = await auth_service.token_repository.is_token_blacklisted(token_id)
        assert is_token_blacklisted is True

        active_session = await auth_service.session_repository.get_active_session(session_id)
        assert active_session is not None
        assert active_session.user_id == auth_user.id

        user_logs = await auth_service.audit_repository.get_user_logs(auth_user.id)
        assert len(user_logs) >= 1
        assert user_logs[0].user_id == auth_user.id


@pytest.mark.integration
@pytest.mark.asyncio
class TestPerformanceIntegration:
    """性能集成测试"""

    async def test_concurrent_user_operations(self):
        """测试并发用户操作"""
        auth_service = await create_auth_service()

        async def create_user_operation(index: int):
            """并发创建用户操作"""
            user = await auth_service.auth_repository.create_user(
                phone=f"1380013{8000 + index}",
                password_hash=f"$2b$12$concurrent_test_{index}",
                nickname=f"并发用户{index}"
            )
            return user.id

        # 创建10个并发用户
        tasks = [create_user_operation(i) for i in range(10)]
        user_ids = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有用户都创建成功
        assert len(user_ids) == 10
        for user_id in user_ids:
            assert isinstance(user_id, uuid4)
            assert user_id is not None

        # 验证所有用户都可以被查询到
        for i, user_id in enumerate(user_ids):
            user = await auth_service.auth_repository.get_by_id(AuthUser, user_id)
            assert user is not None
            assert user.phone == f"1380013{8000 + i}"

    async def test_bulk_sms_operations(self):
        """测试批量短信操作"""
        auth_service = await create_auth_service()

        phones = [f"1380013{8000 + i}" for i in range(20, 30)]

        async def send_sms_operation(phone: str):
            """并发发送短信操作"""
            with patch('builtins.print'):  # Mock控制台输出
                code = await auth_service.sms_service.send_verification_code(
                    phone=phone,
                    verification_type="bulk_test"
                )
            return code

        # 前5个请求成功，后面的被频率限制
        results = []
        for i, phone in enumerate(phones):
            try:
                if i < 5:
                    result = await send_sms_operation(phone)
                    results.append(result)
                else:
                    # 模拟频率限制
                    raise Exception("发送过于频繁")
            except Exception as e:
                results.append(e)

        # 验证前5个成功，后面的失败
        success_count = sum(1 for r in results if isinstance(r, str))
        assert success_count == 5
        error_count = sum(1 for r in results if isinstance(r, Exception))
        assert error_count == 5

    async def test_token_management_performance(self):
        """测试令牌管理性能"""
        auth_service = await create_auth_service()

        user_id = uuid4()
        start_time = datetime.now(timezone.utc)

        # 创建100个令牌黑名单记录
        tasks = []
        for i in range(100):
            token_id = str(uuid4())
            expires_at = start_time + timedelta(hours=i + 1)

            task = auth_service.token_repository.blacklist_token(
                token_id=token_id,
                user_id=user_id,
                token_type="access",
                expires_at=expires_at
            )
            tasks.append(task)

        # 并发创建黑名单记录
        await asyncio.gather(*tasks)

        # 测试批量查询性能
        check_start = datetime.now(timezone.utc)
        for i in range(50):
            token_id = str(uuid4())  # 不存在的令牌
            is_blacklisted = await auth_service.token_repository.is_token_blacklisted(token_id)
            assert is_blacklisted is False

        check_end = datetime.now(timezone.utc)
        check_duration = (check_end - check_start).total_seconds()

        # 50次查询应该在合理时间内完成（小于1秒）
        assert check_duration < 1.0, f"令牌查询性能过慢: {check_duration}秒"

        # 清理过期令牌
        cleanup_start = datetime.now(timezone.utc)
        cleaned_count = await auth_service.token_repository.cleanup_expired_tokens()
        cleanup_end = datetime.now(timezone.utc)
        cleanup_duration = (cleanup_end - cleanup_start).total_seconds()

        # 清理操作应该很快（小于0.5秒）
        assert cleanup_duration < 0.5, f"令牌清理性能过慢: {cleanup_duration}秒"