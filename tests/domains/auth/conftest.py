"""
Auth领域测试配置

提供auth领域测试所需的特定fixtures和工具函数。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from uuid import uuid4

from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository
from src.domains.auth.service import AuthService


@pytest.fixture(scope="function")
def auth_repository(auth_db_session):
    """提供AuthRepository实例的fixture"""
    return AuthRepository(auth_db_session)


@pytest.fixture(scope="function")
def audit_repository(auth_db_session):
    """提供AuditRepository实例的fixture"""
    return AuditRepository(auth_db_session)


@pytest.fixture(scope="function")
def auth_service():
    """提供AuthService实例的fixture"""
    return AuthService()


@pytest.fixture(scope="function")
def sample_guest_user(auth_repository):
    """创建测试用的游客用户"""
    return auth_repository.create_user(
        is_guest=True,
        wechat_openid=None
    )


@pytest.fixture(scope="function")
def sample_registered_user(auth_repository):
    """创建测试用的正式用户"""
    wechat_openid = f"wx_test_{uuid4().hex[:8]}"
    return auth_repository.create_user(
        is_guest=False,
        wechat_openid=wechat_openid
    )


@pytest.fixture(scope="function")
def sample_wechat_openid():
    """提供测试用的微信OpenID"""
    return f"wx_test_{uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def auth_user_with_tokens(auth_service):
    """创建带有令牌的测试用户"""
    from src.domains.auth.schemas import GuestInitRequest

    # 创建用户（使用实际的API）
    result = auth_service.init_guest_account(GuestInitRequest())

    return {
        "user_id": result["user_id"],
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "is_guest": result["is_guest"]
    }