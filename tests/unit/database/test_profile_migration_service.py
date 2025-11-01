"""
Profile数据库迁移服务测试

测试Profile数据库迁移服务的功能，包括迁移检查、执行和验证。

作者：TaTakeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
import tempfile
import os
from typing import Generator
from sqlmodel import SQLModel, Session
from pathlib import Path

from src.database.profile_connection import ProfileDatabaseConnection
from src.database.profile_migration import ProfileDatabaseMigration


class TestProfileDatabaseMigrationService:
    """Profile数据库迁移服务测试类"""

    @pytest.fixture
    def temp_database(self) -> Generator[str, None, None]:
        """创建临时数据库文件fixture"""
        # 创建临时数据库文件
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()

        yield temp_db.name

        # 清理临时文件
        try:
            os.unlink(temp_db.name)
        except OSError:
            pass

    @pytest.fixture
    def migration_service(self, temp_database: str) -> ProfileDatabaseMigration:
        """Profile数据库迁移服务fixture"""
        db_url = f"sqlite:///{temp_database}"
        profile_db = ProfileDatabaseConnection(database_url=db_url, echo=False)
        return ProfileDatabaseMigration()

    @pytest.fixture
    def mock_migration_service(self, temp_database: str) -> ProfileDatabaseMigration:
        """使用临时数据库的Profile迁移服务fixture"""
        db_url = f"sqlite:///{temp_database}"

        # 创建临时连接
        from src.database.profile_connection import get_profile_database_connection, reset_profile_database_connection
        reset_profile_database_connection()

        # 设置环境变量以使用临时数据库
        os.environ['PROFILE_DATABASE_URL'] = db_url

        yield ProfileDatabaseMigration()

        # 清理环境变量
        if 'PROFILE_DATABASE_URL' in os.environ:
            del os.environ['PROFILE_DATABASE_URL']
        reset_profile_database_connection()

    def test_create_profile_tables_success(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试成功创建Profile数据库表

        Given: 有效的迁移服务实例
        When: 调用create_profile_tables方法
        Then: 应该成功创建所有必要的表
        """
        result = mock_migration_service.create_profile_tables()

        assert result is True, "创建Profile数据库表应该成功"

        # 验证表是否创建成功
        status = mock_migration_service.get_migration_status()
        assert status["database_connected"] is True
        assert status["tables_exist"] is True
        assert "user" in status["tables"]
        assert "usersettings" in status["tables"]
        assert "userstats" in status["tables"]

    def test_verify_table_structure_success(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试验证表结构功能

        Given: 已创建的Profile数据库表
        When: 调用verify_table_structure方法
        Then: 应该验证通过
        """
        # 先创建表
        mock_migration_service.create_profile_tables()

        # 验证表结构
        result = mock_migration_service.verify_table_structure()

        assert result is True, "表结构验证应该通过"

    def test_check_migration_needed_new_database(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试检查新数据库是否需要迁移

        Given: 空的数据库
        When: 调用check_migration_needed方法
        Then: 应该返回True
        """
        result = mock_migration_service.check_migration_needed()

        assert result is True, "新数据库需要迁移"

    def test_check_migration_needed_existing_tables(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试检查已存在表的数据库是否需要迁移

        Given: 已创建表的数据库
        When: 调用check_migration_needed方法
        Then: 应该返回False
        """
        # 先创建表
        mock_migration_service.create_profile_tables()

        # 检查是否需要迁移
        result = mock_migration_service.check_migration_needed()

        assert result is False, "已创建完整表的数据库不需要迁移"

    def test_run_migration_success(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试成功执行完整迁移流程

        Given: 空的数据库
        When: 调用run_migration方法
        Then: 应该成功完成迁移
        """
        result = mock_migration_service.run_migration()

        assert result is True, "数据库迁移应该成功"

        # 验证迁移结果
        status = mock_migration_service.get_migration_status()
        assert status["database_connected"] is True
        assert status["tables_exist"] is True
        assert status["table_structure_valid"] is True
        assert status["migration_needed"] is False

    def test_get_migration_status_initial(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试获取初始迁移状态

        Given: 空的数据库
        When: 调用get_migration_status方法
        Then: 应该返回正确的初始状态
        """
        status = mock_migration_service.get_migration_status()

        assert status["database_connected"] is True
        assert status["migration_needed"] is True
        assert status["tables_exist"] is False
        assert status["table_structure_valid"] is False
        assert status["tables"] == []

    def test_get_migration_status_after_migration(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试迁移后的状态

        Given: 已完成迁移的数据库
        When: 调用get_migration_status方法
        Then: 应该返回迁移完成的状态
        """
        # 执行迁移
        mock_migration_service.run_migration()

        # 获取状态
        status = mock_migration_service.get_migration_status()

        assert status["database_connected"] is True
        assert status["migration_needed"] is False
        assert status["tables_exist"] is True
        assert status["table_structure_valid"] is True
        assert len(status["tables"]) > 0

    def test_run_migration_idempotent(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试迁移的幂等性

        Given: 已迁移的数据库
        When: 再次调用run_migration方法
        Then: 应该不会报错且结果一致
        """
        # 第一次迁移
        result1 = mock_migration_service.run_migration()
        assert result1 is True

        # 第二次迁移（应该成功且不会重复创建）
        result2 = mock_migration_service.run_migration()
        assert result2 is True

        # 验证状态一致
        status = mock_migration_service.get_migration_status()
        assert status["migration_needed"] is False

    def test_migration_with_existing_data(self, mock_migration_service: ProfileDatabaseMigration):
        """
        测试在有数据情况下的迁移

        Given: 包含数据的数据库
        When: 执行迁移
        Then: 数据应该保持完整
        """
        # 先执行迁移
        mock_migration_service.create_profile_tables()

        # 插入测试数据
        from uuid import uuid4
        from datetime import date, datetime
        from src.domains.user.models import User, UserSettings, UserStats

        test_user_id = uuid4()

        with mock_migration_service.profile_db.get_session() as session:
            # 创建用户
            user = User(
                user_id=test_user_id,
                nickname="迁移测试用户",
                avatar_url="https://example.com/migration.jpg",
                bio="迁移测试用户简介",
                gender="female",
                birthday=date(1985, 8, 20),
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(user)

            # 创建用户设置
            settings = UserSettings(
                user_id=test_user_id,
                theme="light",
                language="en-US"
            )
            session.add(settings)

            # 创建用户统计
            stats = UserStats(
                user_id=test_user_id,
                tasks_completed=25,
                total_points=1250,
                login_count=12
            )
            session.add(stats)

            session.commit()

        # 再次运行迁移（应该不会影响现有数据）
        result = mock_migration_service.run_migration()
        assert result is True

        # 验证数据完整性
        with mock_migration_service.profile_db.get_session() as session:
            # 查询用户
            user = session.get(User, test_user_id)
            assert user is not None
            assert user.nickname == "迁移测试用户"
            assert user.gender == "female"

            # 查询用户设置
            from sqlmodel import select
            settings = session.exec(select(UserSettings).where(UserSettings.user_id == test_user_id)).first()
            assert settings is not None
            assert settings.theme == "light"

            # 查询用户统计
            stats = session.exec(select(UserStats).where(UserStats.user_id == test_user_id)).first()
            assert stats is not None
            assert stats.tasks_completed == 25

    def test_convenience_functions(self):
        """
        测试便捷函数

        Given: 有效的配置
        When: 调用便捷函数
        Then: 应该正常工作
        """
        from src.database.profile_migration import (
            get_profile_migration,
            run_profile_migration,
            check_profile_migration_needed
        )

        # 测试获取迁移实例
        migration = get_profile_migration()
        assert migration is not None
        assert isinstance(migration, ProfileDatabaseMigration)

        # 测试检查迁移需求
        needed = check_profile_migration_needed()
        assert isinstance(needed, bool)

        # 测试执行迁移（使用临时数据库）
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()

        try:
            db_url = f"sqlite:///{temp_db.name}"
            os.environ['PROFILE_DATABASE_URL'] = db_url

            from src.database.profile_connection import reset_profile_database_connection
            reset_profile_database_connection()

            # 执行迁移
            result = run_profile_migration()
            assert result is True

        finally:
            if 'PROFILE_DATABASE_URL' in os.environ:
                del os.environ['PROFILE_DATABASE_URL']
            reset_profile_database_connection()
            os.unlink(temp_db.name)