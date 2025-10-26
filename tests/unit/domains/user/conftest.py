"""
User领域测试配置

提供User领域测试专用的fixtures和配置。
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlmodel import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from src.domains.auth.models import Auth
from src.domains.user.repository import UserRepository
from src.domains.points.service import PointsService
from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.api.main import app

# User领域测试数据库配置
USER_TEST_DATABASE_URL = "sqlite:///:memory:"
user_test_engine = create_engine(
    USER_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    pool_pre_ping=True
)
UserTestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_test_engine)


@pytest.fixture(scope="function")
def user_test_db_session() -> Session:
    """
    User领域专用测试数据库会话

    提供包含Auth表的独立数据库会话，用于User领域测试。
    """
    # 创建Auth表（User领域依赖Auth模型）
    Auth.metadata.create_all(user_test_engine)

    session = UserTestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # 清理数据库
        Auth.metadata.drop_all(user_test_engine)


@pytest.fixture(scope="function")
def sample_auth_user(user_test_db_session: Session) -> Auth:
    """
    创建示例Auth用户

    返回一个保存到数据库的Auth用户实例，用于测试。
    """
    user_id = str(uuid4())
    auth_user = Auth(
        id=user_id,
        wechat_openid="test_openid_sample",
        is_guest=False
    )

    user_test_db_session.add(auth_user)
    user_test_db_session.commit()
    user_test_db_session.refresh(auth_user)

    return auth_user


@pytest.fixture(scope="function")
def sample_guest_user(user_test_db_session: Session) -> Auth:
    """
    创建示例游客用户

    返回一个保存到数据库的游客用户实例。
    """
    user_id = str(uuid4())
    guest_user = Auth(
        id=user_id,
        wechat_openid=None,  # 游客用户没有微信OpenID
        is_guest=True
    )

    user_test_db_session.add(guest_user)
    user_test_db_session.commit()
    user_test_db_session.refresh(guest_user)

    return guest_user


@pytest.fixture(scope="function")
def multiple_test_users(user_test_db_session: Session) -> list[Auth]:
    """
    创建多个测试用户

    返回一个包含多个用户的列表，用于批量测试。
    """
    users = []
    for i in range(3):
        user_id = str(uuid4())
        user = Auth(
            id=user_id,
            wechat_openid=f"test_openid_{i}",
            is_guest=i == 0  # 第一个是游客
        )
        user_test_db_session.add(user)
        users.append(user)

    user_test_db_session.commit()

    # 刷新所有用户以获取数据库生成的值
    for user in users:
        user_test_db_session.refresh(user)

    return users


@pytest_asyncio.fixture
async def authenticated_user_client(test_client: AsyncClient) -> tuple[AsyncClient, dict]:
    """
    创建已认证的测试客户端

    返回带有认证token的客户端和用户信息。
    """
    # 创建游客用户
    response = await test_client.post("/api/v3/auth/guest-init")
    assert response.status_code == 200
    data = response.json()["data"]

    headers = {"Authorization": f"Bearer {data['access_token']}"}

    return test_client, {
        "user_id": data["user_id"],
        "access_token": data["access_token"],
        "headers": headers
    }


@pytest.fixture
def uuid_string_sample():
    """返回示例UUID字符串"""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def uuid_object_sample():
    """返回示例UUID对象"""
    return uuid4()


@pytest.fixture(scope="function")
def user_repository(user_test_db_session: Session):
    """
    UserRepository实例

    提供UserRepository实例用于测试。
    """
    return UserRepository(user_test_db_session)


@pytest.fixture(scope="function")
def user_service(user_repository: UserRepository):
    """
    UserService实例

    提供UserService实例用于测试。
    """
    from src.domains.user.service import UserService
    return UserService(user_repository)


@pytest.fixture(scope="function")
def points_service(user_test_db_session: Session):
    """
    PointsService实例

    提供PointsService实例用于测试。
    """
    from src.domains.points.service import PointsService
    return PointsService(user_test_db_session)


@pytest.fixture(scope="function")
def welcome_gift_service(user_test_db_session: Session, points_service: PointsService):
    """
    WelcomeGiftService实例

    提供WelcomeGiftService实例用于测试。
    """
    from src.domains.reward.welcome_gift_service import WelcomeGiftService
    return WelcomeGiftService(user_test_db_session, points_service)


@pytest.fixture(scope="function")
def sample_user_with_uuid(user_test_db_session: Session):
    """
    创建包含UUID的示例用户

    返回Auth用户实例和对应的UUID对象。
    """
    from uuid import uuid4
    user_id = uuid4()
    auth_user = Auth(
        id=str(user_id),
        wechat_openid="uuid_test_openid",
        is_guest=False
    )

    user_test_db_session.add(auth_user)
    user_test_db_session.commit()
    user_test_db_session.refresh(auth_user)

    return {
        "auth_user": auth_user,
        "user_id": user_id,
        "user_id_str": str(user_id)
    }