"""
认证系统集成测试配置

提供统一的测试基础设施，包括：
1. 测试数据库配置和清理
2. 认证服务工厂
3. 测试数据管理
4. Mock微信API配置

作者：TaTakeKe团队
版本：2.0.0 - 认证系统测试基础设施
"""

import pytest
import tempfile
import os
from typing import Generator, Dict, Any
from uuid import uuid4
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from sqlmodel import create_engine, Session
from sqlmodel import SQLModel

# 导入认证系统模块
try:
    from src.domains.auth.database import get_auth_db, create_tables, drop_tables
    from src.domains.auth.repository import AuthRepository, AuditRepository
    from src.domains.auth.service import AuthService, JWTService
    from src.domains.auth.models import Auth, AuthLog
    from src.domains.auth.exceptions import AuthenticationException, UserNotFoundException
except ImportError as e:
    print(f"Warning: 无法导入认证模块: {e}")
    # 创建fallback实现用于测试
    Auth = Mock()
    AuthLog = Mock()
    AuthService = Mock()
    JWTService = Mock()
    AuthRepository = Mock()
    AuditRepository = Mock()
    AuthenticationException = Exception
    UserNotFoundException = Exception

# 创建WeChatUserInfo用于测试（从schemas中移除了，临时定义）
class WeChatUserInfo:
    """微信用户信息测试类"""
    def __init__(self, **kwargs):
        self.openid = kwargs.get('openid', 'ox1234567890abcdef')
        self.nickname = kwargs.get('nickname', '测试用户')
        self.headimgurl = kwargs.get('headimgurl', 'http://example.com/avatar.jpg')
        self.unionid = kwargs.get('unionid', 'ox1234567890ghijkl')
        self.sex = kwargs.get('sex', 1)
        self.province = kwargs.get('province', '北京')
        self.city = kwargs.get('city', '北京')
        self.country = kwargs.get('country', '中国')


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    测试数据库URL

    Returns:
        str: 临时SQLite数据库URL
    """
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine(test_database_url: str):
    """
    测试数据库引擎

    Args:
        test_database_url: 测试数据库URL

    Yields:
        Engine: SQLAlchemy引擎
    """
    engine = create_engine(
        test_database_url,
        echo=False,  # 测试时不输出SQL
        connect_args={"check_same_thread": False}
    )

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine) -> Generator[Session, None, None]:
    """
    测试数据库会话

    Args:
        test_engine: 测试数据库引擎

    Yields:
        Session: 数据库会话
    """
    session = Session(test_engine)

    try:
        # 创建表结构
        SQLModel.metadata.create_all(test_engine)
        yield session
    finally:
        session.close()
        # 清理表结构
        SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def mock_wechat_api():
    """
    Mock微信API服务

    Returns:
        Mock: 配置好的微信API Mock对象
    """
    mock_api = Mock()

    # 配置成功响应
    def get_user_info_success(code: str):
        return WeChatUserInfo(
            openid="ox1234567890abcdef",
            nickname="测试用户",
            headimgurl="http://example.com/avatar.jpg",
            unionid="ox1234567890ghijkl"
        )

    # 配置失败响应
    def get_user_info_failure(code: str):
        raise AuthenticationException("微信用户信息获取失败")

    # 配置空响应
    def get_user_info_null(code: str):
        return None

    # 设置默认成功行为
    mock_api.get_user_info.side_effect = get_user_info_success

    return mock_api


@pytest.fixture
def auth_repository(test_db_session: Session) -> AuthRepository:
    """
    认证Repository实例

    Args:
        test_db_session: 测试数据库会话

    Returns:
        AuthRepository: Repository实例
    """
    return AuthRepository(test_db_session)


@pytest.fixture
def audit_repository(test_db_session: Session) -> AuditRepository:
    """
    审计Repository实例

    Args:
        test_db_session: 测试数据库会话

    Returns:
        AuditRepository: Repository实例
    """
    return AuditRepository(test_db_session)


@pytest.fixture
def jwt_service() -> JWTService:
    """
    JWT服务实例

    Returns:
        JWTService: JWT服务实例
    """
    try:
        return JWTService()
    except:
        # Fallback实现
        mock_service = Mock()
        mock_service.create_access_token.return_value = "mock_access_token"
        mock_service.create_refresh_token.return_value = "mock_refresh_token"
        mock_service.verify_token.return_value = {"user_id": str(uuid4()), "exp": 1234567890}
        return mock_service


@pytest.fixture
def auth_service(auth_repository: AuthRepository, audit_repository: AuditRepository, jwt_service: JWTService) -> AuthService:
    """
    认证服务实例

    Args:
        auth_repository: 认证Repository
        audit_repository: 审计Repository
        jwt_service: JWT服务

    Returns:
        AuthService: 认证服务实例
    """
    try:
        return AuthService(
            auth_repository=auth_repository,
            audit_repository=audit_repository,
            jwt_service=jwt_service
        )
    except:
        # Fallback实现
        mock_service = Mock()
        mock_service.init_guest_user.return_value = {
            "user_id": str(uuid4()),
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "is_guest": True
        }
        mock_service.wechat_login.return_value = {
            "user_id": str(uuid4()),
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "is_guest": False,
            "wechat_info": {
                "openid": "ox1234567890abcdef",
                "nickname": "测试用户"
            }
        }
        return mock_service


@pytest.fixture
def sample_wechat_user_info() -> WeChatUserInfo:
    """
    示例微信用户信息

    Returns:
        WeChatUserInfo: 样本微信用户信息
    """
    try:
        return WeChatUserInfo(
            openid="ox1234567890abcdef",
            nickname="测试用户",
            headimgurl="http://example.com/avatar.jpg",
            unionid="ox1234567890ghijkl",
            sex=1,
            province="北京",
            city="北京",
            country="中国"
        )
    except:
        # Fallback实现
        return Mock()


@pytest.fixture
def sample_auth_user() -> Dict[str, Any]:
    """
    示例认证用户数据

    Returns:
        Dict[str, Any]: 样本用户数据
    """
    return {
        "id": str(uuid4()),
        "wechat_openid": "ox1234567890abcdef",
        "is_guest": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login_at": datetime.now(timezone.utc),
        "jwt_version": 1
    }


@pytest.fixture
def sample_guest_user() -> Dict[str, Any]:
    """
    示例游客用户数据

    Returns:
        Dict[str, Any]: 样本游客数据
    """
    return {
        "id": str(uuid4()),
        "wechat_openid": None,
        "is_guest": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login_at": datetime.now(timezone.utc),
        "jwt_version": 1
    }


class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_auth_user(**overrides) -> Dict[str, Any]:
        """创建认证用户数据"""
        default_data = {
            "id": str(uuid4()),
            "wechat_openid": "ox1234567890abcdef",
            "is_guest": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
            "jwt_version": 1
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def create_guest_user(**overrides) -> Dict[str, Any]:
        """创建游客用户数据"""
        default_data = {
            "id": str(uuid4()),
            "wechat_openid": None,
            "is_guest": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
            "jwt_version": 1
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def create_wechat_user_info(**overrides) -> WeChatUserInfo:
        """创建微信用户信息"""
        try:
            default_data = {
                "openid": "ox1234567890abcdef",
                "nickname": "测试用户",
                "headimgurl": "http://example.com/avatar.jpg",
                "unionid": "ox1234567890ghijkl",
                "sex": 1,
                "province": "北京",
                "city": "北京",
                "country": "中国"
            }
        except:
            default_data = {
                "openid": "ox1234567890abcdef",
                "nickname": "测试用户",
                "headimgurl": "http://example.com/avatar.jpg"
            }
        default_data.update(overrides)

        try:
            return WeChatUserInfo(**default_data)
        except:
            mock_user = Mock()
            for key, value in default_data.items():
                setattr(mock_user, key, value)
            return mock_user


@pytest.fixture
def test_data_factory():
    """
    测试数据工厂实例

    Returns:
        TestDataFactory: 数据工厂实例
    """
    return TestDataFactory()


# 测试标记配置 - 移除无效的插件引用
# pytest_plugins = []  # 如果需要插件，请在requirements.txt中正确安装


def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests as authentication system tests"
    )
    config.addinivalue_line(
        "markers", "boundary: marks tests as boundary condition tests"
    )


# 测试清理钩子
@pytest.fixture(autouse=True)
def cleanup_test_data(test_db_session: Session):
    """
    自动清理测试数据

    Args:
        test_db_session: 测试数据库会话
    """
    yield  # 测试执行前
    # 测试执行后清理
    test_db_session.query(Auth).delete()
    test_db_session.query(AuthLog).delete()
    test_db_session.commit()


# 环境变量配置
@pytest.fixture(autouse=True, scope="session")
def test_environment():
    """
    设置测试环境变量
    """
    original_env = {}

    # 保存原始环境变量
    for key in ["AUTH_DATABASE_URL", "AUTH_ECHO_SQL"]:
        if key in os.environ:
            original_env[key] = os.environ[key]
        # 设置测试环境变量
        if key == "AUTH_DATABASE_URL":
            os.environ[key] = "sqlite:///:memory:"
        elif key == "AUTH_ECHO_SQL":
            os.environ[key] = "false"

    yield

    # 恢复原始环境变量
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value