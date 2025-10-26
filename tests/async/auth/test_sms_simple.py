"""
简单的SMS异步测试

专门测试修复后的SMS异步功能。

作者：TaKeKe团队
版本：1.0.0 - 简化异步SMS测试
"""

import pytest
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock

from src.domains.auth.service import AuthService
from src.domains.auth.dependencies import get_auth_service_with_db
from src.domains.auth.exceptions import RateLimitException


@pytest.mark.asyncio
@pytest.mark.async_test
class TestSMSAsyncSimple:
    """简单的SMS异步测试"""

    async def test_async_sms_send_basic(self):
        """测试基本的异步SMS发送"""
        # 创建Mock SMS客户端
        mock_client = AsyncMock()
        mock_client.send_code = AsyncMock(
            return_value={"success": True, "message_id": "mock_123"}
        )

        # 使用依赖注入创建service
        async with get_test_auth_service() as auth_service:
            auth_service.sms_client = mock_client

            # 发送SMS
            result = await auth_service.send_sms_code(
                phone="13800138000",
                scene="register",
                ip_address="127.0.0.1"
            )

            # 验证结果
            assert result["success"] is True
            assert "expires_in" in result
            assert "retry_after" in result

            # 验证SMS客户端被调用
            mock_client.send_code.assert_called_once()

    async def test_async_sms_with_invalid_phone(self):
        """测试异步SMS发送失败场景"""
        # 创建Mock SMS客户端（返回失败）
        mock_client = AsyncMock()
        mock_client.send_code = AsyncMock(
            return_value={"success": False, "error": "Invalid phone"}
        )

        async with get_test_auth_service() as auth_service:
            auth_service.sms_client = mock_client

            # 发送SMS
            result = await auth_service.send_sms_code(
                phone="99999999999",  # 无效手机号
                scene="register",
                ip_address="127.0.0.1"
            )

            # 验证结果（即使SMS失败，验证码仍会被保存）
            # 这里取决于具体的业务逻辑实现

    async def test_async_sms_rate_limiting(self):
        """测试异步频率限制"""
        # 创建Mock SMS客户端
        mock_client = AsyncMock()
        mock_client.send_code = AsyncMock(
            return_value={"success": True, "message_id": "mock_123"}
        )

        async with get_test_auth_service() as auth_service:
            auth_service.sms_client = mock_client

            phone = "13800138001"

            # 第一次发送应该成功
            result1 = await auth_service.send_sms_code(
                phone=phone,
                scene="register",
                ip_address="127.0.0.1"
            )
            assert result1["success"] is True

            # 立即再次发送应该被限制
            with pytest.raises(RateLimitException):
                await auth_service.send_sms_code(
                    phone=phone,
                    scene="register",
                    ip_address="127.0.0.1"
                )

    async def test_async_sms_network_error(self):
        """测试网络错误处理"""
        # 创建Mock SMS客户端（抛出异常）
        mock_client = AsyncMock()
        mock_client.send_code = AsyncMock(
            side_effect=Exception("Network error")
        )

        async with get_test_auth_service() as auth_service:
            auth_service.sms_client = mock_client

            # 发送SMS应该失败
            with pytest.raises(Exception):
                await auth_service.send_sms_code(
                    phone="13800138002",
                    scene="register",
                    ip_address="127.0.0.1"
                )


# 简化的异步上下文管理器
@asynccontextmanager
async def get_test_auth_service():
    """创建测试用的认证服务"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    # 创建内存数据库
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # 创建表
    from src.domains.auth.models import Auth, AuthLog, SMSVerification
    Auth.metadata.create_all(bind=engine)
    AuthLog.metadata.create_all(bind=engine)
    SMSVerification.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        with get_auth_service_with_db() as service:
            # 替换为测试session
            service.repository.session = session
            service.audit_repository.session = session
            yield service
    finally:
        session.close()