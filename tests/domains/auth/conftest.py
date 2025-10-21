"""
认证领域测试配置

提供认证领域测试所需的夹具和配置。
"""
import pytest
import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.domains.auth.database import get_auth_db
from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository


@pytest.fixture(scope="function")
async def session():
    """
    提供异步数据库会话的fixture

    使用异步上下文管理器创建会话，并在测试后自动清理。
    """
    async with get_auth_db() as session:
        yield session


@pytest.fixture(scope="function")
async def auth_repository(session):
    """
    提供AuthRepository实例的fixture
    """
    return AuthRepository(session)


@pytest.fixture(scope="function")
async def audit_repository(session):
    """
    提供AuditRepository实例的fixture
    """
    return AuditRepository(session)


@pytest.fixture(scope="function")
async def sample_guest_user(auth_repository):
    """
    创建测试用的游客用户
    """
    return await auth_repository.create_user(
        is_guest=True,
        wechat_openid=None
    )


@pytest.fixture(scope="function")
async def sample_registered_user(auth_repository):
    """
    创建测试用的正式用户
    """
    return await auth_repository.create_user(
        is_guest=False,
        wechat_openid="wx_test_openid_12345"
    )


@pytest.fixture(scope="function")
async def cleanup_data(session):
    """
    清理测试数据的fixture
    """
    yield  # 测试执行期间

    # 测试结束后清理数据
    await session.exec(select(AuthLog))
    await session.exec(select(Auth))
    await session.commit()


@pytest.fixture(scope="function")
def sample_wechat_openid():
    """
    提供测试用的微信OpenID
    """
    return f"wx_test_{uuid4().hex[:8]}"