"""
认证Repository测试

测试新创建的认证相关Repository，包括JWT令牌黑名单、
短信验证码、用户会话和认证日志的数据访问功能。
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.repositories.auth import (
    TokenBlacklistRepository,
    SmsVerificationRepository,
    UserSessionRepository,
    AuthLogRepository
)
from src.models.auth import (
    TokenBlacklist, SmsVerification, UserSession, AuthLog
)
from src.services.exceptions import (
    BusinessException,
    ValidationException
)


class TestTokenBlacklistRepository:
    """JWT令牌黑名单Repository测试类"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """创建TokenBlacklistRepository实例"""
        return TokenBlacklistRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_blacklist_record(self, repository):
        """测试创建黑名单记录"""
        # 准备测试数据
        blacklist_data = {
            'jti': 'test_jti_123',
            'user_id': uuid4(),
            'reason': '用户登出',
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=1),
            'token': 'test_token'
        }

        # 模拟数据库查询返回None（不存在重复）
        repository.get_by_jti = AsyncMock(return_value=None)
        repository.create = AsyncMock(return_value=blacklist_data)

        # 执行测试
        result = await repository.create_blacklist_record(blacklist_data)

        # 验证结果
        assert result is not None
        repository.get_by_jti.assert_called_once_with('test_jti_123')
        repository.create.assert_called_once_with(blacklist_data)

    @pytest.mark.asyncio
    async def test_create_duplicate_blacklist_record(self, repository):
        """测试创建重复的黑名单记录"""
        # 准备测试数据
        blacklist_data = {
            'jti': 'test_jti_123',
            'user_id': uuid4(),
            'reason': '用户登出',
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)
        }

        # 模拟数据库查询返回已存在的记录
        existing_record = AsyncMock()
        repository.get_by_jti = AsyncMock(return_value=existing_record)

        # 执行测试并验证异常
        with pytest.raises(BusinessException) as exc_info:
            await repository.create_blacklist_record(blacklist_data)

        assert "令牌已在黑名单中" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, repository):
        """测试令牌在黑名单中的情况"""
        # 模拟数据库查询返回计数1
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 1
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await repository.is_token_blacklisted('test_jti_123')

        # 验证结果
        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, repository):
        """测试令牌不在黑名单中的情况"""
        # 模拟数据库查询返回计数0
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 0
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await repository.is_token_blacklisted('test_jti_123')

        # 验证结果
        assert result is False


class TestSmsVerificationRepository:
    """短信验证码Repository测试类"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """创建SmsVerificationRepository实例"""
        return SmsVerificationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_verification_success(self, repository):
        """测试成功创建验证码"""
        # 准备测试数据
        verification_data = {
            'phone_number': '13800138000',
            'code': '123456',
            'verification_type': 'login',
            'expires_at': datetime.now(timezone.utc) + timedelta(minutes=5)
        }

        # 模拟频率限制检查通过
        repository._check_send_rate_limit = AsyncMock()
        repository._invalidate_existing_codes = AsyncMock()
        repository.create = AsyncMock(return_value=verification_data)

        # 执行测试
        result = await repository.create_verification(verification_data)

        # 验证结果
        assert result is not None
        repository._check_send_rate_limit.assert_called_once_with('13800138000', 'login')
        repository._invalidate_existing_codes.assert_called_once_with('13800138000', 'login')
        repository.create.assert_called_once_with(verification_data)

    @pytest.mark.asyncio
    async def test_verify_code_success(self, repository):
        """测试验证码验证成功"""
        # 创建模拟验证码记录
        verification_record = SmsVerification(
            phone_number='13800138000',
            code='123456',
            verification_type='login',
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            is_used=False,
            attempt_count=0,
            max_attempts=5
        )

        # 模拟数据库查询返回验证码记录
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = verification_record
        repository.session.execute = AsyncMock(return_value=mock_result)
        repository.session.commit = AsyncMock()

        # 执行测试
        result = await repository.verify_code('13800138000', '123456', 'login')

        # 验证结果
        assert result is True
        assert verification_record.is_used is True
        assert verification_record.used_at is not None

    @pytest.mark.asyncio
    async def test_verify_code_failure(self, repository):
        """测试验证码验证失败"""
        # 模拟数据库查询返回None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await repository.verify_code('13800138000', '000000', 'login')

        # 验证结果
        assert result is False

    @pytest.mark.asyncio
    async def test_check_send_rate_limit_exceeded(self, repository):
        """测试发送频率限制触发"""
        # 模拟数据库查询返回最近的发送计数
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 1  # 1分钟内已发送1次
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试并验证异常
        with pytest.raises(BusinessException) as exc_info:
            await repository._check_send_rate_limit('13800138000', 'login')

        assert "发送频率过快" in str(exc_info.value)


class TestUserSessionRepository:
    """用户会话Repository测试类"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """创建UserSessionRepository实例"""
        return UserSessionRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_session(self, repository):
        """测试创建用户会话"""
        # 准备测试数据
        session_data = {
            'user_id': uuid4(),
            'session_token': 'test_session_token',
            'ip_address': '192.168.1.1',
            'expires_at': datetime.now(timezone.utc) + timedelta(days=7)
        }

        # 模拟创建成功
        repository.create = AsyncMock(return_value=session_data)

        # 执行测试
        result = await repository.create_session(session_data)

        # 验证结果
        assert result is not None
        repository.create.assert_called_once_with(session_data)

    @pytest.mark.asyncio
    async def test_get_by_session_token_found(self, repository):
        """测试根据会话令牌获取会话（找到）"""
        # 创建模拟会话记录
        session_record = UserSession(
            user_id=uuid4(),
            session_token='test_session_token',
            ip_address='192.168.1.1',
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # 模拟数据库查询返回会话记录
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = session_record
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await repository.get_by_session_token('test_session_token')

        # 验证结果
        assert result is not None
        assert result.session_token == 'test_session_token'

    @pytest.mark.asyncio
    async def test_get_by_session_token_not_found(self, repository):
        """测试根据会话令牌获取会话（未找到）"""
        # 模拟数据库查询返回None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await repository.get_by_session_token('invalid_token')

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_update_session_activity_success(self, repository):
        """测试更新会话活跃时间成功"""
        # 创建模拟会话记录
        session_record = UserSession(
            user_id=uuid4(),
            session_token='test_session_token',
            ip_address='192.168.1.1',
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # 模拟数据库查询返回会话记录
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = session_record
        repository.session.execute = AsyncMock(return_value=mock_result)
        repository.session.commit = AsyncMock()

        # 执行测试
        result = await repository.update_session_activity('test_session_token')

        # 验证结果
        assert result is True
        assert session_record.last_activity_at is not None

    @pytest.mark.asyncio
    async def test_revoke_session_success(self, repository):
        """测试撤销会话成功"""
        # 创建模拟会话记录
        session_record = UserSession(
            user_id=uuid4(),
            session_token='test_session_token',
            ip_address='192.168.1.1',
            is_active=True
        )

        # 模拟数据库查询返回会话记录
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = session_record
        repository.session.execute = AsyncMock(return_value=mock_result)
        repository.session.commit = AsyncMock()

        # 执行测试
        result = await repository.revoke_session('test_session_token')

        # 验证结果
        assert result is True
        assert session_record.is_active is False


class TestAuthLogRepository:
    """认证日志Repository测试类"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """创建AuthLogRepository实例"""
        return AuthLogRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_log(self, repository):
        """测试创建认证日志"""
        # 准备测试数据
        log_data = {
            'user_id': uuid4(),
            'action': 'login',
            'identifier': '13800138000',
            'success': True,
            'ip_address': '192.168.1.1'
        }

        # 模拟创建成功
        repository.create = AsyncMock(return_value=log_data)

        # 执行测试
        result = await repository.create_log(log_data)

        # 验证结果
        assert result is not None
        repository.create.assert_called_once_with(log_data)

    @pytest.mark.asyncio
    async def test_get_failed_attempts(self, repository):
        """测试获取失败尝试次数"""
        # 模拟数据库查询返回失败次数
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 3
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await repository.get_failed_attempts('13800138000', 15, 'login')

        # 验证结果
        assert result == 3

    @pytest.mark.asyncio
    async def test_get_user_logs(self, repository):
        """测试获取用户认证日志"""
        user_id = uuid4()

        # 创建模拟日志记录
        log_records = [
            AuthLog(
                user_id=user_id,
                action='login',
                identifier='13800138000',
                success=True
            ),
            AuthLog(
                user_id=user_id,
                action='logout',
                identifier='13800138000',
                success=True
            )
        ]

        # 模拟数据库查询返回日志记录
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = log_records
        repository.session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await repository.get_user_logs(user_id)

        # 验证结果
        assert len(result) == 2
        assert result[0].action == 'login'
        assert result[1].action == 'logout'


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])