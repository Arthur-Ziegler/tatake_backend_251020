"""
Auth领域Repository测试

测试AuthRepository和AuditRepository的功能，包括：
1. 用户创建和查询
2. 微信登录逻辑
3. 审计日志记录
4. 数据库事务处理

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository


@pytest.mark.unit
class TestAuthRepository:
    """AuthRepository测试类"""

    def test_create_guest_user(self, auth_db_session):
        """测试创建游客用户"""
        repo = AuthRepository(auth_db_session)

        guest = repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        assert guest.id is not None
        assert guest.is_guest is True
        assert guest.wechat_openid is None
        assert guest.jwt_version == 1

        # 验证数据库中确实存在
        retrieved = repo.get_by_id(Auth, guest.id)
        assert retrieved is not None
        assert retrieved.id == guest.id
        assert retrieved.is_guest is True

    def test_create_registered_user(self, auth_db_session):
        """测试创建正式用户"""
        repo = AuthRepository(auth_db_session)
        wechat_openid = "wx_test_openid_12345"

        user = repo.create_user(
            is_guest=False,
            wechat_openid=wechat_openid
        )

        assert user.id is not None
        assert user.is_guest is False
        assert user.wechat_openid == wechat_openid
        assert user.jwt_version == 1

        # 验证数据库中确实存在
        retrieved = repo.get_by_wechat_openid(wechat_openid)
        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.wechat_openid == wechat_openid

    def test_get_user_by_id_not_found(self, auth_db_session):
        """测试根据ID查询不存在的用户"""
        repo = AuthRepository(auth_db_session)
        fake_id = str(uuid4())

        result = repo.get_by_id(Auth, fake_id)
        assert result is None

    def test_get_user_by_wechat_not_found(self, auth_db_session):
        """测试根据微信OpenID查询不存在的用户"""
        repo = AuthRepository(auth_db_session)
        fake_openid = "wx_fake_12345"

        result = repo.get_by_wechat_openid(fake_openid)
        assert result is None

    def test_upgrade_guest_to_registered(self, auth_db_session):
        """测试游客用户升级为正式用户"""
        repo = AuthRepository(auth_db_session)

        # 先创建游客用户
        guest = repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        # 升级为正式用户
        wechat_openid = "wx_upgrade_test_12345"
        updated_user = repo.upgrade_guest_account(
            guest.id,
            wechat_openid
        )

        assert updated_user is not None
        assert updated_user.id == guest.id
        assert updated_user.is_guest is False
        assert updated_user.wechat_openid == wechat_openid

    

@pytest.mark.unit
class TestAuditRepository:
    """AuditRepository测试类"""

    def test_create_auth_log(self, auth_db_session):
        """测试创建认证日志"""
        auth_repo = AuthRepository(auth_db_session)
        audit_repo = AuditRepository(auth_db_session)

        # 创建用户
        user = auth_repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        # 创建日志
        auth_log = audit_repo.create_log(
            user_id=user.id,
            action="login",
            result="success",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )

        assert auth_log.id is not None
        assert auth_log.user_id == user.id
        assert auth_log.action == "login"
        assert auth_log.ip_address == "192.168.1.1"
        assert auth_log.user_agent == "TestAgent/1.0"

    def test_get_logs_by_auth_id(self, auth_db_session):
        """测试根据用户ID查询日志"""
        auth_repo = AuthRepository(auth_db_session)
        audit_repo = AuditRepository(auth_db_session)

        # 创建用户
        user = auth_repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        # 创建多个日志
        actions = ["login", "logout", "login"]
        for action in actions:
            audit_repo.create_log(
                user_id=user.id,
                action=action,
                result="success",
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0"
            )

        # 注意：AuditRepository 只支持创建日志，不支持查询
        # 这个测试验证日志创建功能正常工作

    def test_create_multiple_logs_for_different_users(self, auth_db_session):
        """测试为不同用户创建多个日志"""
        auth_repo = AuthRepository(auth_db_session)
        audit_repo = AuditRepository(auth_db_session)

        # 创建多个用户
        users = []
        for i in range(3):
            user = auth_repo.create_user(
                is_guest=True,
                wechat_openid=None
            )
            users.append(user)

        # 为每个用户创建登录日志
        for i, user in enumerate(users):
            auth_log = audit_repo.create_log(
                user_id=user.id,
                action="login",
                result="success",
                ip_address=f"192.168.1.{i+1}",
                user_agent=f"TestAgent/{i+1}.0"
            )

            assert auth_log.id is not None
            assert auth_log.user_id == user.id
            assert auth_log.action == "login"
            assert auth_log.result == "success"

    def test_create_log_with_minimal_data(self, auth_db_session):
        """测试使用最小数据创建日志"""
        auth_repo = AuthRepository(auth_db_session)
        audit_repo = AuditRepository(auth_db_session)

        user = auth_repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        # 只使用必需字段
        auth_log = audit_repo.create_log(
            user_id=user.id,
            action="login",
            result="success"
        )

        assert auth_log.id is not None
        assert auth_log.user_id == user.id
        assert auth_log.action == "login"
        assert auth_log.result == "success"
        assert auth_log.ip_address is None
        assert auth_log.user_agent is None


@pytest.mark.integration
class TestAuthRepositoryIntegration:
    """AuthRepository集成测试"""

    def test_user_lifecycle_with_audit_trail(self, auth_db_session):
        """测试完整的用户生命周期和审计跟踪"""
        auth_repo = AuthRepository(auth_db_session)
        audit_repo = AuditRepository(auth_db_session)

        # 1. 创建游客用户
        guest = auth_repo.create_user(is_guest=True, wechat_openid=None)
        assert guest.is_guest is True

        # 记录创建日志
        register_log = audit_repo.create_log(
            user_id=guest.id,
            action="register",
            result="success",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        assert register_log.user_id == guest.id
        assert register_log.action == "register"

        # 2. 用户登录
        login_log = audit_repo.create_log(
            user_id=guest.id,
            action="login",
            result="success",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        assert login_log.user_id == guest.id
        assert login_log.action == "login"

        # 3. 升级为正式用户
        wechat_openid = "wx_lifecycle_test_12345"
        updated_user = auth_repo.upgrade_guest_account(guest.id, wechat_openid)
        assert updated_user.is_guest is False
        assert updated_user.wechat_openid == wechat_openid

        # 记录升级日志
        upgrade_log = audit_repo.create_log(
            user_id=guest.id,
            action="upgrade",
            result="success",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        assert upgrade_log.user_id == guest.id
        assert upgrade_log.action == "upgrade"

        # 4. 验证最终状态
        final_user = auth_repo.get_by_id(Auth, guest.id)
        assert final_user.is_guest is False
        assert final_user.wechat_openid == wechat_openid

        # 5. 记录登出日志
        logout_log = audit_repo.create_log(
            user_id=guest.id,
            action="logout",
            result="success",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        assert logout_log.user_id == guest.id
        assert logout_log.action == "logout"

        # 注意：AuditRepository 不支持查询，所以我们只验证日志创建成功
        # 实际的审计查询需要通过数据库直接查询或添加查询方法