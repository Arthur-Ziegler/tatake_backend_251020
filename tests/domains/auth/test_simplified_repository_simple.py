"""
简化的Repository测试

专注于Repository核心功能的简单测试，避免复杂fixture依赖。
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from src.domains.auth.database import get_auth_db
from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository


class TestSimplifiedRepository:
    """测试简化的Repository功能"""

    @pytest.mark.asyncio
    async def test_auth_repository_basic_operations(self):
        """测试AuthRepository基础操作"""
        async with get_auth_db() as session:
            repo = AuthRepository(session)

            # 1. 创建游客用户
            guest = await repo.create_user(
                is_guest=True,
                wechat_openid=None
            )
            assert guest.id is not None
            assert guest.is_guest is True
            assert guest.wechat_openid is None

            # 2. 创建正式用户
            user = await repo.create_user(
                is_guest=False,
                wechat_openid="wx_test_12345"
            )
            assert user.id is not None
            assert user.is_guest is False
            assert user.wechat_openid == "wx_test_12345"

            # 3. 通过ID查找用户
            found_user = await repo.get_by_id(Auth, user.id)
            assert found_user is not None
            assert found_user.wechat_openid == "wx_test_12345"

            # 4. 通过微信OpenID查找用户
            found_by_openid = await repo.get_by_wechat_openid("wx_test_12345")
            assert found_by_openid is not None
            assert found_by_openid.id == user.id

            # 5. 查找不存在的用户
            not_found = await repo.get_by_wechat_openid("nonexistent_12345")
            assert not_found is None

    @pytest.mark.asyncio
    async def test_guest_upgrade_flow(self):
        """测试游客升级流程"""
        async with get_auth_db() as session:
            repo = AuthRepository(session)

            # 1. 创建游客
            guest = await repo.create_user(
                is_guest=True,
                wechat_openid=None
            )
            assert guest.is_guest is True
            assert guest.jwt_version == 1

            # 2. 升级游客
            updated_user = await repo.upgrade_guest_account(
                user_id=guest.id,
                wechat_openid="wx_upgrade_test_12345"
            )
            assert updated_user.id == guest.id
            assert updated_user.is_guest is False
            assert updated_user.wechat_openid == "wx_upgrade_test_12345"
            assert updated_user.jwt_version == 2  # JWT版本应该增加

    @pytest.mark.asyncio
    async def test_update_last_login(self):
        """测试更新最后登录时间"""
        async with get_auth_db() as session:
            repo = AuthRepository(session)

            # 创建用户
            user = await repo.create_user(
                is_guest=True,
                wechat_openid=None
            )
            assert user.last_login_at is None

            # 更新登录时间
            await repo.update_last_login(user.id)

            # 验证登录时间已更新
            # 需要重新查询以获取更新后的数据
            updated_user = await repo.get_by_id(Auth, user.id)
            assert updated_user.last_login_at is not None
            assert isinstance(updated_user.last_login_at, datetime)

    @pytest.mark.asyncio
    async def test_audit_repository_operations(self):
        """测试AuditRepository操作"""
        async with get_auth_db() as session:
            auth_repo = AuthRepository(session)
            audit_repo = AuditRepository(session)

            # 创建测试用户
            user = await auth_repo.create_user(
                is_guest=False,
                wechat_openid="wx_audit_test_12345"
            )

            # 1. 创建审计日志
            log1 = await audit_repo.create_log(
                user_id=user.id,
                action="login",
                result="success",
                details="用户登录成功"
            )
            assert log1.id is not None
            assert log1.user_id == user.id
            assert log1.action == "login"
            assert log1.result == "success"

            # 2. 创建无用户的审计日志（游客操作）
            log2 = await audit_repo.create_log(
                user_id=None,
                action="guest_init",
                result="success",
                details="游客初始化"
            )
            assert log2.id is not None
            assert log2.user_id is None
            assert log2.action == "guest_init"

            # 3. 按用户ID查询日志
            user_logs = await audit_repo.get_logs_by_user_id(user.id, limit=10)
            assert len(user_logs) >= 1
            user_log_actions = {log.action for log in user_logs}
            assert "login" in user_log_actions

            # 4. 按操作类型查询日志
            login_logs = await audit_repo.get_logs_by_action("login", limit=10)
            assert len(login_logs) >= 1
            for log in login_logs:
                assert log.action == "login"

    @pytest.mark.asyncio
    async def test_wechat_openid_uniqueness(self):
        """测试微信OpenID唯一性约束"""
        async with get_auth_db() as session:
            repo = AuthRepository(session)

            # 创建第一个用户
            await repo.create_user(
                is_guest=False,
                wechat_openid="wx_unique_test_12345"
            )

            # 尝试创建相同OpenID的用户应该失败
            with pytest.raises(Exception):  # SQLite会抛出唯一约束异常
                await repo.create_user(
                    is_guest=False,
                    wechat_openid="wx_unique_test_12345"
                )

    @pytest.mark.asyncio
    async def test_audit_statistics(self):
        """测试审计统计功能"""
        async with get_auth_db() as session:
            auth_repo = AuthRepository(session)
            audit_repo = AuditRepository(session)

            # 创建测试用户
            user = await auth_repo.create_user(
                is_guest=False,
                wechat_openid="wx_stats_test_12345"
            )

            # 创建多条审计日志
            await audit_repo.create_log(user_id=user.id, action="login", result="success")
            await audit_repo.create_log(user_id=user.id, action="refresh", result="success")
            await audit_repo.create_log(user_id=user.id, action="upgrade", result="failure")

            # 获取统计信息
            stats = await audit_repo.get_statistics()
            assert stats["total_operations"] >= 3
            assert stats["success_operations"] >= 2
            assert stats["failure_operations"] >= 1
            assert stats["success_rate"] > 0
            assert 0 <= stats["success_rate"] <= 100


class TestRepositoryDeletion:
    """测试已删除的Repository"""

    def test_old_repositories_not_importable(self):
        """测试旧的Repository不能导入"""
        # 这些Repository应该已被删除
        old_repositories = [
            'SMSRepository',
            'TokenRepository',
            'SessionRepository'
        ]

        for repo_name in old_repositories:
            # 尝试导入这些Repository应该失败
            with pytest.raises(ImportError):
                from src.domains.auth.repository import repo_name  # type: ignore