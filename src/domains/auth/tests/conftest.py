"""
认证领域测试配置

提供pytest fixtures和测试配置，用于认证领域的测试。
包含数据库设置、测试数据创建、认证服务等共享资源。
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.auth.database import get_auth_db, auth_engine
from src.domains.auth.models import User, UserSettings, SMSVerification, TokenBlacklist, UserSession, AuthLog
from src.domains.auth.service import create_auth_service
from src.domains.auth.repository import (
    AuthRepository, SMSRepository, TokenRepository,
    SessionRepository, AuditRepository
)
from src.domains.auth.schemas import GuestInitRequest, LoginRequest


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def auth_db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建认证数据库测试会话"""
    async with get_auth_db() as session:
        # 开始事务
        transaction = await session.begin()
        try:
            yield session
        finally:
            # 回滚事务，确保测试之间数据隔离
            await transaction.rollback()


@pytest.fixture
async def auth_repository(auth_db_session: AsyncSession) -> AuthRepository:
    """创建认证Repository实例"""
    return AuthRepository(auth_db_session)


@pytest.fixture
async def sms_repository(auth_db_session: AsyncSession) -> SMSRepository:
    """创建短信Repository实例"""
    return SMSRepository(auth_db_session)


@pytest.fixture
async def token_repository(auth_db_session: AsyncSession) -> TokenRepository:
    """创建令牌Repository实例"""
    return TokenRepository(auth_db_session)


@pytest.fixture
async def session_repository(auth_db_session: AsyncSession) -> SessionRepository:
    """创建会话Repository实例"""
    return SessionRepository(auth_db_session)


@pytest.fixture
async def audit_repository(auth_db_session: AsyncSession) -> AuditRepository:
    """创建审计Repository实例"""
    return AuditRepository(auth_db_session)


@pytest.fixture
async def auth_service() -> "AuthService":
    """创建认证服务实例"""
    return await create_auth_service()


@pytest.fixture
def sample_device_info() -> dict:
    """示例设备信息"""
    return {
        "device_id": "test-device-12345",
        "device_type": "ios",
        "app_version": "1.0.0",
        "ip_address": "127.0.0.1",
        "user_agent": "TaKeKe-iOS/1.0.0"
    }


@pytest.fixture
def sample_guest_init_request() -> GuestInitRequest:
    """示例游客初始化请求"""
    return GuestInitRequest(
        device_id="test-device-12345",
        device_type="ios",
        app_version="1.0.0"
    )


@pytest.fixture
def sample_login_request() -> LoginRequest:
    """示例登录请求"""
    return LoginRequest(
        identifier="13800138000",
        login_type="sms",
        sms_code="123456"
    )


@pytest.fixture
async def sample_user(auth_repository: AuthRepository) -> User:
    """创建示例用户"""
    user = await auth_repository.create_user(
        username="testuser",
        phone="13800138000",
        password_hash="$2b$12$test_password_hash",
        nickname="测试用户"
    )
    return user


@pytest.fixture
async def sample_guest_user(auth_repository: AuthRepository) -> User:
    """创建示例游客用户"""
    guest_user = await auth_repository.create_user(
        is_guest=True,
        device_id="test-device-12345",
        device_type="ios",
        nickname="游客用户"
    )
    return guest_user


@pytest.fixture
async def sample_sms_code(sms_repository: SMSRepository) -> SMSVerification:
    """创建示例短信验证码"""
    sms_code = await sms_repository.create_verification_code(
        phone="13800138000",
        code="123456",
        verification_type="login"
    )
    return sms_code


@pytest.fixture
def sample_jwt_token() -> dict:
    """示例JWT令牌数据"""
    user_id = uuid.uuid4()
    return {
        "sub": str(user_id),
        "user_type": "registered",
        "is_guest": False,
        "jwt_version": 1,
        "token_type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc).timestamp() + 1800,  # 30分钟
        "jti": str(uuid.uuid4())
    }


@pytest.fixture
def expired_jwt_token() -> dict:
    """示例过期JWT令牌数据"""
    user_id = uuid.uuid4()
    past_time = datetime.now(timezone.utc).timestamp() - 3600  # 1小时前
    return {
        "sub": str(user_id),
        "user_type": "registered",
        "is_guest": False,
        "jwt_version": 1,
        "token_type": "access",
        "iat": past_time,
        "exp": past_time + 1800,
        "jti": str(uuid.uuid4())
    }


class MockSMSService:
    """Mock短信服务，用于测试"""

    def __init__(self):
        self.sent_codes = {}  # phone -> code

    async def send_verification_code(self, phone: str, verification_type: str = "login") -> str:
        """模拟发送短信验证码"""
        code = "123456"  # 固定测试验证码
        self.sent_codes[phone] = code
        return code

    async def verify_code(self, phone: str, code: str, verification_type: str = "login") -> bool:
        """验证短信验证码"""
        return self.sent_codes.get(phone) == code


@pytest.fixture
def mock_sms_service() -> MockSMSService:
    """创建Mock短信服务实例"""
    return MockSMSService()


# 测试数据清理
@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_test_data(auth_db_session: AsyncSession):
    """自动清理测试数据"""
    yield  # 测试执行

    # 清理所有测试数据
    await auth_db_session.execute(TokenBlacklist.__table__.delete())
    await auth_db_session.execute(UserSession.__table__.delete())
    await auth_db_session.execute(AuthLog.__table__.delete())
    await auth_db_session.execute(SMSVerification.__table__.delete())
    await auth_db_session.execute(UserSettings.__table__.delete())
    await auth_db_session.execute(User.__table__.delete())
    await auth_db_session.commit()


# 测试标记
pytest_plugins = []

# 自定义标记
def pytest_configure(config):
    """配置pytest自定义标记"""
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "security: 安全测试标记"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试标记"
    )
    config.addinivalue_line(
        "markers", "edge_case: 边界条件测试标记"
    )


# 测试工具函数
async def create_test_user_with_session(
    auth_repository: AuthRepository,
    session_repository: SessionRepository,
    phone: str = "13800138000",
    device_id: str = "test-device"
) -> tuple[User, str]:
    """创建测试用户和会话"""
    user = await auth_repository.create_user(
        phone=phone,
        password_hash="$2b$12$test_hash",
        nickname="测试用户"
    )

    session_id = str(uuid.uuid4())
    await session_repository.create_session(
        user_id=user.id,
        session_id=session_id,
        device_info=device_id,
        ip_address="127.0.0.1"
    )

    return user, session_id


def assert_user_response_format(response_data: dict):
    """验证用户响应格式"""
    required_fields = ["user_id", "username", "nickname", "phone", "is_guest", "is_verified"]
    for field in required_fields:
        assert field in response_data, f"缺少必需字段: {field}"


def assert_auth_response_format(response_data: dict, include_tokens: bool = True):
    """验证认证响应格式"""
    required_fields = ["user_id", "is_guest"]
    if include_tokens:
        required_fields.extend(["access_token", "refresh_token", "token_type", "expires_in"])

    for field in required_fields:
        assert field in response_data, f"缺少必需字段: {field}"