"""
测试简化的认证领域数据模型

测试新的简化表结构，确保数据迁移和功能正常。
按照设计文档，新的auth表只包含7个核心字段：
- id, wechat_openid, is_guest, created_at, updated_at, last_login_at, jwt_version
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text
from src.domains.auth.models import Auth, AuthLog


@pytest.mark.asyncio
class TestSimplifiedAuthModel:
    """测试简化的Auth模型"""

    async def test_auth_table_exists(self, session):
        """测试auth表是否存在且有正确的结构"""
        # 检查表是否存在
        result = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' AND name='auth'"))
        table_exists = result.first() is not None
        assert table_exists, "auth表应该存在"

        # 检查字段结构
        result = session.exec(text("PRAGMA table_info(auth)"))
        columns = [row[1] for row in result.fetchall()]

        expected_columns = {
            'id', 'wechat_openid', 'is_guest', 'created_at',
            'updated_at', 'last_login_at', 'jwt_version'
        }

        actual_columns = set(columns)
        assert actual_columns == expected_columns, f"auth表字段不匹配。期望: {expected_columns}, 实际: {actual_columns}"

    async def test_create_guest_user(self, session):
        """测试创建游客用户"""
        guest = Auth(
            is_guest=True,
            wechat_openid=None
        )

        session.add(guest)
        session.commit()
        session.refresh(guest)

        assert guest.id is not None
        assert guest.is_guest is True
        assert guest.wechat_openid is None
        assert guest.created_at is not None
        assert guest.updated_at is not None
        assert guest.jwt_version == 1

    async def test_create_registered_user(self, session):
        """测试创建正式用户"""
        user = Auth(
            is_guest=False,
            wechat_openid="wx_test_openid_12345"
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.id is not None
        assert user.is_guest is False
        assert user.wechat_openid == "wx_test_openid_12345"
        assert user.created_at is not None
        assert user.jwt_version == 1

    async def test_wechat_openid_unique_constraint(self, session):
        """测试微信OpenID唯一约束"""
        # 创建第一个用户
        user1 = Auth(
            is_guest=False,
            wechat_openid="wx_duplicated_openid"
        )

        session.add(user1)
        session.commit()

        # 尝试创建相同OpenID的用户
        user2 = Auth(
            is_guest=False,
            wechat_openid="wx_duplicated_openid"
        )

        session.add(user2)

        with pytest.raises(Exception):  # 应该抛出唯一约束异常
            session.commit()

    async def test_old_tables_do_not_exist(self, session):
        """测试旧表已被删除"""
        old_tables = [
            'auth_users', 'auth_sms_verification', 'auth_token_blacklist',
            'auth_user_sessions', 'auth_user_settings'
        ]

        for table_name in old_tables:
            result = session.exec(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"))
            table_exists = result.first() is not None
            assert not table_exists, f"旧表 {table_name} 应该已被删除"

    async def test_auth_log_table_still_exists(self, session):
        """测试auth_audit_logs表仍然存在"""
        result = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_audit_logs'"))
        table_exists = result.first() is not None
        assert table_exists, "auth_audit_logs表应该保留"

        # 检查能否创建审计日志
        auth_log = AuthLog(
            user_id=uuid4(),
            action="test_action",
            result="success",
            details="测试日志"
        )

        session.add(auth_log)
        session.commit()
        session.refresh(auth_log)

        assert auth_log.id is not None
        assert auth_log.action == "test_action"
        assert auth_log.result == "success"


@pytest.mark.asyncio
class TestDatabaseMigration:
    """测试数据库迁移功能"""

    async def test_migration_data_integrity(self, session):
        """测试迁移数据完整性（如果存在旧数据）"""
        # 这个测试在有旧数据时验证迁移的正确性
        # 在新系统上，这个测试主要是确保迁移脚本可以运行

        # 检查是否有迁移数据
        result = session.exec(text("SELECT COUNT(*) FROM auth"))
        row = result.first()
        count = row[0] if row else 0

        # 验证新表结构存在且正确
        result = session.exec(text("PRAGMA table_info(auth)"))
        columns = [row[1] for row in result.fetchall()]

        expected_columns = {
            'id', 'wechat_openid', 'is_guest', 'created_at',
            'updated_at', 'last_login_at', 'jwt_version'
        }

        actual_columns = set(columns)
        assert actual_columns == expected_columns, f"auth表字段不匹配。期望: {expected_columns}, 实际: {actual_columns}"

        # 如果有数据，验证数据完整性
        if count > 0:
            # 验证至少有一条记录有必需的字段
            result = session.exec(text("""
                SELECT COUNT(*) FROM auth
                WHERE id IS NOT NULL
                AND created_at IS NOT NULL
                AND updated_at IS NOT NULL
                AND jwt_version IS NOT NULL
                LIMIT 1
            """))
            row = result.first()
            valid_exists = row[0] if row else 0

            assert valid_exists > 0, "应该至少有一条记录有完整的必需字段"

    async def test_new_indexes_performance(self, session):
        """测试新索引的性能"""
        # 插入测试数据
        test_openid = "test_performance_openid"
        user = Auth(
            is_guest=False,
            wechat_openid=test_openid
        )
        session.add(user)
        session.commit()

        # 测试按wechat_openid查询（应该使用索引）
        start_time = datetime.now()
        result = session.exec(text("SELECT * FROM auth WHERE wechat_openid = :openid").bindparams(openid=test_openid))
        found_user = result.first()
        end_time = datetime.now()

        query_time = (end_time - start_time).total_seconds()
        assert found_user is not None, "应该能找到用户"
        assert query_time < 1.0, f"查询时间应该很快，实际耗时: {query_time}秒"

        # 测试按is_guest查询
        result = session.exec(text("SELECT COUNT(*) FROM auth WHERE is_guest = 1"))
        row = result.first()
        guest_count = row[0] if row else 0
        assert isinstance(guest_count, int), "应该能正确统计游客数量"