"""
SMS异步功能测试

专门测试SMS功能的异步行为，包括：
1. 异步SMS发送
2. 异步数据库操作
3. 并发SMS请求
4. 异步错误处理
5. 异步性能测试

这些测试验证了之前修复的异步调用问题。

作者：TaKeKe团队
版本：1.0.0 - SMS异步测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.domains.auth.service import AuthService
from src.domains.auth.dependencies import get_auth_service_with_db
from src.domains.auth.exceptions import RateLimitException, DailyLimitException
from tests.utils.async_helpers import AsyncTestHelper, AsyncSMSMock, AsyncAssertionHelper


@pytest.mark.asyncio
@pytest.mark.async_test
class TestSMSAsyncFunctionality:
    """SMS异步功能测试类"""

    async def test_async_sms_send_success(self):
        """测试异步SMS发送成功"""
        # 使用Mock SMS客户端
        with patch('src.domains.auth.service.get_sms_client') as mock_get_client:
            mock_client = AsyncSMSMock()
            mock_get_client.return_value = mock_client

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

                # 验证SMS被发送
                last_message = mock_client.get_last_message()
                assert last_message is not None
                assert last_message["phone"] == "13800138000"
                assert last_message["code"] is not None

    async def test_async_sms_with_database_operations(self):
        """测试SMS与数据库操作的异步集成"""
        async with get_test_auth_service() as auth_service:
            # 使用Mock SMS客户端
            mock_client = AsyncSMSMock()
            auth_service.sms_client = mock_client

            # 发送SMS
            result = await auth_service.send_sms_code(
                phone="13900139000",
                scene="login",
                ip_address="192.168.1.1"
            )

            # 验证SMS发送成功
            assert result["success"] is True

            # 验证验证码记录被保存到数据库
            verification = auth_service.repository.get_latest_unverified("13900139000", "login")
            assert verification is not None
            assert verification.phone == "13900139000"
            assert verification.scene == "login"

    async def test_concurrent_sms_requests(self):
        """测试并发SMS请求处理"""
        async with get_test_auth_service() as auth_service:
            mock_client = AsyncSMSMock()
            auth_service.sms_client = mock_client

            # 准备并发任务
            phones = ["13800138001", "13800138002", "13800138003"]
            tasks = []

            # 创建并发SMS发送任务
            for i, phone in enumerate(phones):
                task = auth_service.send_sms_code(
                    phone=phone,
                    scene="register",
                    ip_address=f"127.0.0.{i+1}"
                )
                tasks.append(task)

            # 并发执行所有任务
            results = await AsyncTestHelper.gather_async(*tasks)

            # 验证所有任务都成功
            assert len(results) == len(phones)
            for result in results:
                assert result["success"] is True

            # 验证所有消息都被发送
            assert len(mock_client.messages) == len(phones)

    async def test_async_sms_rate_limiting(self):
        """测试异步SMS频率限制"""
        async with get_test_auth_service() as auth_service:
            mock_client = AsyncSMSMock()
            auth_service.sms_client = mock_client

            phone = "13800138010"

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

    async def test_async_sms_error_handling(self):
        """测试异步SMS错误处理"""
        async with get_test_auth_service() as auth_service:
            # 模拟SMS发送失败
            mock_client = AsyncSMSMock()
            mock_client.send_code = AsyncMock(side_effect=Exception("Network error"))
            auth_service.sms_client = mock_client

            # 发送SMS应该失败
            with pytest.raises(Exception):
                await auth_service.send_sms_code(
                    phone="13800138020",
                    scene="register",
                    ip_address="127.0.0.1"
                )

    async def test_async_sms_performance(self):
        """测试异步SMS性能"""
        async with get_test_auth_service() as auth_service:
            mock_client = AsyncSMSMock()
            auth_service.sms_client = mock_client

            # 测量单次SMS发送时间
            _, duration = await AsyncTestHelper.measure_async_time(
                auth_service.send_sms_code,
                phone="13800138030",
                scene="register",
                ip_address="127.0.0.1"
            )

            # 验证性能合理（应该在100ms内）
            assert duration < 0.1, f"SMS sending took too long: {duration:.3f}s"

    async def test_async_sms_verification_flow(self):
        """测试完整的异步SMS验证流程"""
        async with get_test_auth_service() as auth_service:
            mock_client = AsyncSMSMock()
            auth_service.sms_client = mock_client

            phone = "13800138040"
            code = "123456"

            # 1. 发送验证码
            send_result = await auth_service.send_sms_code(
                phone=phone,
                scene="register",
                ip_address="127.0.0.1"
            )
            assert send_result["success"] is True

            # 2. 验证验证码
            verify_result = auth_service.verify_sms_code(
                phone=phone,
                code=code,
                scene="register"
            )

            # 验证验证成功
            assert verify_result["success"] is True
            assert "access_token" in verify_result
            assert "refresh_token" in verify_result
            assert "user_id" in verify_result


@pytest.mark.asyncio
@pytest.mark.async_test
class TestSMSAsyncErrorScenarios:
    """SMS异步错误场景测试"""

    async def test_async_sms_with_database_error(self):
        """测试数据库错误时的异步处理"""
        with patch('src.domains.auth.repository.AuthRepository.create_sms_verification') as mock_create:
            mock_create.side_effect = Exception("Database error")

            async with get_test_auth_service() as auth_service:
                mock_client = AsyncSMSMock()
                auth_service.sms_client = mock_client

                # SMS发送应该因数据库错误而失败
                with pytest.raises(Exception):
                    await auth_service.send_sms_code(
                        phone="13800138050",
                        scene="register",
                        ip_address="127.0.0.1"
                    )

    async def test_async_sms_with_timeout(self):
        """测试SMS超时处理"""
        async with get_test_auth_service() as auth_service:
            # 模拟慢速SMS客户端
            mock_client = AsyncSMSMock()

            async def slow_send_code(phone: str, code: str):
                await asyncio.sleep(2.0)  # 模拟2秒延迟
                return await AsyncSMSMock.send_code(mock_client, phone, code)

            mock_client.send_code = slow_send_code
            auth_service.sms_client = mock_client

            # 使用较短的超时时间测试
            helper = AsyncTestHelper()
            start_time = asyncio.get_event_loop().time()

            try:
                await asyncio.wait_for(
                    auth_service.send_sms_code(
                        phone="13800138060",
                        scene="register",
                        ip_address="127.0.0.1"
                    ),
                    timeout=1.0
                )
                assert False, "Expected timeout but operation succeeded"
            except asyncio.TimeoutError:
                # 验证确实超时了
                duration = asyncio.get_event_loop().time() - start_time
                assert 1.0 <= duration < 1.2

    async def test_async_sms_memory_cleanup(self):
        """测试异步SMS后的内存清理"""
        async with get_test_auth_service() as auth_service:
            mock_client = AsyncSMSMock()
            auth_service.sms_client = mock_client

            # 发送多条SMS
            for i in range(5):
                await auth_service.send_sms_code(
                    phone=f"1380013807{i}",
                    scene="register",
                    ip_address=f"127.0.0.{i+1}"
                )

            # 验证消息数量
            assert len(mock_client.messages) == 5

            # 清理消息
            mock_client.clear_messages()
            assert len(mock_client.messages) == 0

            # 验证数据库中也有相应记录
            # 注意：这里我们无法直接清理数据库记录，因为session会被清理


@pytest.mark.asyncio
@pytest.mark.async_test
class TestSMSAsyncIntegration:
    """SMS异步集成测试"""

    async def test_async_sms_end_to_end(self):
        """端到端异步SMS测试"""
        from httpx import AsyncClient
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 发送SMS请求
            response = await client.post(
                "/auth/sms/send",
                json={"phone": "13900139001", "scene": "register"}
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 200
            assert "data" in data
            assert data["data"]["expires_in"] == 300

    async def test_async_sms_dependency_injection(self):
        """测试异步依赖注入工作正常"""
        async with get_test_auth_service() as auth_service:
            # 验证service被正确注入
            assert auth_service is not None
            assert hasattr(auth_service, 'repository')
            assert hasattr(auth_service, 'sms_client')
            assert auth_service.repository is not None
            assert auth_service.audit_repository is not None

            # 验证依赖注入的service可以正常工作
            mock_client = AsyncSMSMock()
            auth_service.sms_client = mock_client

            result = await auth_service.send_sms_code(
                phone="13900139002",
                scene="login",
                ip_address="192.168.1.2"
            )

            assert result["success"] is True


# 异步上下文管理器（从conftest.py导入）
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