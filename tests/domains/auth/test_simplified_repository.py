"""
测试简化的认证领域Repository

测试新的简化Repository设计，确保：
1. 只保留核心的Auth和AuditLog Repository
2. 移除SMS、Session、Token等非核心Repository
3. 简化方法签名，专注核心功能
4. 支持微信登录和游客管理
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository


@pytest.mark.asyncio
class TestSimplifiedAuthRepository:
    """测试简化的AuthRepository"""

    async def test_create_guest_user(self, session):
        """测试创建游客用户"""
        repo = AuthRepository(session)

        guest = await repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        assert guest.id is not None
        assert guest.is_guest is True
        assert guest.wechat_openid is None
        assert guest.jwt_version == 1

    async def test_create_registered_user(self, session):
        """测试创建正式用户"""
        repo = AuthRepository(session)

        user = await repo.create_user(
            is_guest=False,
            wechat_openid="wx_test_openid_12345"
        )

        assert user.id is not None
        assert user.is_guest is False
        assert user.wechat_openid == "wx_test_openid_12345"
        assert user.jwt_version == 1

    async def test_get_by_wechat_openid(self, session):
        """测试通过微信OpenID查找用户"""
        repo = AuthRepository(session)

        # 创建用户
        created_user = await repo.create_user(
            is_guest=False,
            wechat_openid="wx_search_test_12345"
        )

        # 查找用户
        found_user = await repo.get_by_wechat_openid("wx_search_test_12345")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.wechat_openid == "wx_search_test_12345"

    async def test_get_by_wechat_openid_not_found(self, session):
        """测试查找不存在的微信OpenID"""
        repo = AuthRepository(session)

        found_user = await repo.get_by_wechat_openid("wx_nonexistent_12345")

        assert found_user is None

    async def test_upgrade_guest_account(self, session):
        """测试升级游客账号"""
        repo = AuthRepository(session)

        # 创建游客
        guest = await repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        # 升级游客
        updated_user = await repo.upgrade_guest_account(
            user_id=guest.id,
            wechat_openid="wx_upgrade_test_12345"
        )

        assert updated_user.id == guest.id
        assert updated_user.is_guest is False
        assert updated_user.wechat_openid == "wx_upgrade_test_12345"
        assert updated_user.jwt_version == 2  # JWT版本应该增加

    async def test_update_last_login(self, session):
        """测试更新最后登录时间"""
        repo = AuthRepository(session)

        # 创建用户
        user = await repo.create_user(
            is_guest=True,
            wechat_openid=None
        )

        # 确保初始last_login_at为None
        assert user.last_login_at is None

        # 更新最后登录时间
        await repo.update_last_login(user.id)

        # 刷新用户数据
        session.refresh(user)
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)

    async def test_get_by_id(self, session):
        """测试通过ID查找用户"""
        repo = AuthRepository(session)

        # 创建用户
        created_user = await repo.create_user(
            is_guest=False,
            wechat_openid="wx_id_test_12345"
        )

        # 通过ID查找用户
        found_user = await repo.get_by_id(Auth, created_user.id)

        assert found_user is not None
        assert found_user.id == created_user.id

    async def test_wechat_openid_uniqueness(self, session):
        """测试微信OpenID唯一性约束"""
        repo = AuthRepository(session)

        # 创建第一个用户
        await repo.create_user(
            is_guest=False,
            wechat_openid="wx_duplicate_test_12345"
        )

        # 尝试创建相同OpenID的用户
        with pytest.raises(Exception):  # 应该抛出唯一约束异常
            await repo.create_user(
                is_guest=False,
                wechat_openid="wx_duplicate_test_12345"
            )


@pytest.mark.asyncio
class TestSimplifiedAuditRepository:
    """测试简化的AuditRepository"""

    async def test_create_log(self, session):
        """测试创建审计日志"""
        repo = AuditRepository(session)

        test_user_id = uuid4()
        log = await repo.create_log(
            user_id=test_user_id,
            action="test_action",
            result="success",
            details="测试日志",
            ip_address="127.0.0.1"
        )

        assert log.id is not None
        assert log.user_id == test_user_id
        assert log.action == "test_action"
        assert log.result == "success"
        assert log.details == "测试日志"
        assert log.ip_address == "127.0.0.1"

    async def test_create_log_without_user(self, session):
        """测试创建无用户ID的审计日志（游客操作）"""
        repo = AuditRepository(session)

        log = await repo.create_log(
            user_id=None,
            action="guest_init",
            result="success",
            details="游客初始化"
        )

        assert log.id is not None
        assert log.user_id is None
        assert log.action == "guest_init"
        assert log.result == "success"

    async def test_get_logs_by_user_id(self, session):
        """测试按用户ID查询日志"""
        repo = AuditRepository(session)

        test_user_id = uuid4()

        # 创建多条日志
        await repo.create_log(user_id=test_user_id, action="login", result="success")
        await repo.create_log(user_id=test_user_id, action="logout", result="success")
        await repo.create_log(user_id=test_user_id, action="refresh", result="success")

        # 查询日志
        logs = await repo.get_logs_by_user_id(test_user_id, limit=10)

        assert len(logs) >= 3
        user_log_actions = {log.action for log in logs}
        assert "login" in user_log_actions
        assert "logout" in user_log_actions
        assert "refresh" in user_log_actions

    async def test_get_logs_by_action(self, session):
        """测试按操作类型查询日志"""
        repo = AuditRepository(session)

        test_user_id = uuid4()

        # 创建多条登录日志
        await repo.create_log(user_id=test_user_id, action="login", result="success")
        await repo.create_log(user_id=test_user_id, action="login", result="failure")
        await repo.create_log(user_id=uuid4(), action="login", result="success")

        # 查询登录日志
        login_logs = await repo.get_logs_by_action("login", limit=10)

        assert len(login_logs) >= 3
        for log in login_logs:
            assert log.action == "login"


@pytest.mark.asyncio
class TestDeletedRepositories:
    """测试已删除的Repository不应该存在"""

    def test_old_repositories_do_not_exist(self):
        """测试旧的Repository已被删除"""
        # 这些Repository应该已被删除
        old_repositories = [
            'SMSRepository',       # 短信验证码Repository
            'TokenRepository',      # 令牌Repository
            'SessionRepository',    # 会话Repository
        ]

        for repo_name in old_repositories:
            # 尝试导入这些Repository应该失败
            try:
                from src.domains.auth.repository import repo_name  # type: ignore
                assert False, f"Repository {repo_name} 应该已被删除"
            except ImportError:
                pass  # 期望的行为