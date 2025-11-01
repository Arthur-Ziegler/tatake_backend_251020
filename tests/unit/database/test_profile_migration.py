"""
Profile数据库迁移测试

测试Profile数据库的迁移功能，包括表创建、字段添加和数据迁移。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
import tempfile
import os
from typing import Generator
from sqlmodel import SQLModel, Session, select, text
from pathlib import Path

from src.database.profile_connection import ProfileDatabaseConnection
from src.domains.user.models import User, UserSettings, UserStats


class TestProfileDatabaseMigration:
    """Profile数据库迁移测试类"""

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
    def profile_db(self, temp_database: str) -> ProfileDatabaseConnection:
        """Profile数据库连接fixture"""
        db_url = f"sqlite:///{temp_database}"
        return ProfileDatabaseConnection(database_url=db_url, echo=False)

    def test_create_profile_tables_success(self, profile_db: ProfileDatabaseConnection):
        """
        测试成功创建Profile数据库表

        Given: 有效的Profile数据库连接
        When: 调用create_tables方法
        Then: 应该成功创建所有必要的表
        """
        # 获取引擎并创建表
        engine = profile_db.get_engine()

        # 导入所有需要的模型
        from src.domains.user.models import User, UserSettings, UserStats

        # 创建所有表
        SQLModel.metadata.create_all(bind=engine)

        # 验证表是否创建成功
        with profile_db.get_session() as session:
            # 检查User表
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user'"))
            user_table_exists = result.fetchone() is not None
            assert user_table_exists, "User表应该被创建"

            # 检查UserSettings表
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='usersettings'"))
            settings_table_exists = result.fetchone() is not None
            assert settings_table_exists, "UserSettings表应该被创建"

            # 检查UserStats表
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='userstats'"))
            stats_table_exists = result.fetchone() is not None
            assert stats_table_exists, "UserStats表应该被创建"

    def test_new_columns_exist_in_user_table(self, profile_db: ProfileDatabaseConnection):
        """
        测试User表包含新增的字段

        Given: 创建的Profile数据库表
        When: 检查表结构
        Then: 应该包含gender和birthday字段
        """
        # 创建表
        engine = profile_db.get_engine()
        SQLModel.metadata.create_all(bind=engine)

        # 验证新字段存在
        with profile_db.get_session() as session:
            # 检查User表的列信息
            result = session.execute(text("PRAGMA table_info(user)"))
            columns = [row[1] for row in result.fetchall()]

            assert "gender" in columns, "gender字段应该存在"
            assert "birthday" in columns, "birthday字段应该存在"
            assert "nickname" in columns, "nickname字段应该存在"
            assert "avatar_url" in columns, "avatar_url字段应该存在"
            assert "bio" in columns, "bio字段应该存在"

    def test_foreign_key_constraints(self, profile_db: ProfileDatabaseConnection):
        """
        测试外键约束是否正确设置

        Given: 创建的Profile数据库表
        When: 检查外键关系
        Then: UserSettings和UserStats应该正确关联到User
        """
        # 创建表
        engine = profile_db.get_engine()
        SQLModel.metadata.create_all(bind=engine)

        # 注意：SQLite外键约束默认是关闭的，所以这里只检查表结构
        # 实际的外键约束需要在应用逻辑中处理
        with profile_db.get_session() as session:
            # 启用外键约束检查
            session.execute(text("PRAGMA foreign_keys = ON"))

            # 检查UserSettings表的字段
            result = session.execute(text("PRAGMA table_info(usersettings)"))
            settings_columns = [row[1] for row in result.fetchall()]
            assert "user_id" in settings_columns, "UserSettings表应该有user_id字段"

            # 检查UserStats表的字段
            result = session.execute(text("PRAGMA table_info(userstats)"))
            stats_columns = [row[1] for row in result.fetchall()]
            assert "user_id" in stats_columns, "UserStats表应该有user_id字段"

    def test_create_tables_idempotent(self, profile_db: ProfileDatabaseConnection):
        """
        测试create_tables方法的幂等性

        Given: 已创建的Profile数据库表
        When: 再次调用create_tables
        Then: 应该不会报错，表结构保持不变
        """
        # 创建表
        engine = profile_db.get_engine()
        SQLModel.metadata.create_all(bind=engine)

        # 再次创建表（应该不报错）
        SQLModel.metadata.create_all(bind=engine)

        # 验证表仍然存在且结构正确
        with profile_db.get_session() as session:
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]

            assert "user" in tables, "User表应该存在"
            assert "usersettings" in tables, "UserSettings表应该存在"
            assert "userstats" in tables, "UserStats表应该存在"

    def test_migration_with_data(self, profile_db: ProfileDatabaseConnection):
        """
        测试带有数据的迁移

        Given: Profile数据库和现有数据
        When: 创建新表结构
        Then: 数据应该能够正确插入和查询
        """
        # 创建表
        engine = profile_db.get_engine()
        SQLModel.metadata.create_all(bind=engine)

        # 插入测试数据
        from uuid import uuid4
        from datetime import date, datetime

        test_user_id = uuid4()

        with profile_db.get_session() as session:
            # 创建用户
            user = User(
                user_id=test_user_id,
                nickname="测试用户",
                avatar_url="https://example.com/avatar.jpg",
                bio="测试用户简介",
                gender="male",
                birthday=date(1990, 5, 15),
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(user)

            # 创建用户设置
            settings = UserSettings(
                user_id=test_user_id,
                theme="dark",
                language="zh-CN"
            )
            session.add(settings)

            # 创建用户统计
            stats = UserStats(
                user_id=test_user_id,
                tasks_completed=10,
                total_points=500,
                login_count=5
            )
            session.add(stats)

            session.commit()

        # 验证数据可以正确查询
        with profile_db.get_session() as session:
            # 查询用户
            user = session.get(User, test_user_id)
            assert user is not None
            assert user.nickname == "测试用户"
            assert user.gender == "male"
            assert user.birthday == date(1990, 5, 15)

            # 查询用户设置
            settings = session.exec(select(UserSettings).where(UserSettings.user_id == test_user_id)).first()
            assert settings is not None
            assert settings.theme == "dark"
            assert settings.language == "zh-CN"

            # 查询用户统计
            stats = session.exec(select(UserStats).where(UserStats.user_id == test_user_id)).first()
            assert stats is not None
            assert stats.tasks_completed == 10
            assert stats.total_points == 500

    def test_profile_database_connection_initialization(self, temp_database: str):
        """
        测试Profile数据库连接初始化

        Given: 临时数据库路径
        When: 创建ProfileDatabaseConnection实例
        Then: 应该正确初始化连接配置
        """
        db_url = f"sqlite:///{temp_database}"
        profile_db = ProfileDatabaseConnection(database_url=db_url, echo=False)

        # 验证配置
        assert profile_db.database_url == db_url
        assert profile_db.echo is False
        assert profile_db._engine is None  # 引擎应该延迟初始化

        # 验证可以获取引擎
        engine = profile_db.get_engine()
        assert engine is not None
        assert profile_db._engine is engine  # 应该缓存引擎实例

    def test_check_connection_success(self, profile_db: ProfileDatabaseConnection):
        """
        测试数据库连接检查功能

        Given: 有效的Profile数据库连接
        When: 调用check_connection方法
        Then: 应该返回True
        """
        # 创建表以确保连接可用
        engine = profile_db.get_engine()
        SQLModel.metadata.create_all(bind=engine)

        # 检查连接
        is_connected = profile_db.check_connection()
        assert is_connected is True

    def test_check_connection_failure(self):
        """
        测试无效数据库连接检查

        Given: 无效的数据库连接URL
        When: 调用check_connection方法
        Then: 应该返回False或抛出异常
        """
        # 使用无效的数据库路径
        invalid_db_url = "sqlite:///invalid/path/nonexistent.db"
        profile_db = ProfileDatabaseConnection(database_url=invalid_db_url, echo=False)

        # 检查连接（应该失败）
        is_connected = profile_db.check_connection()
        assert is_connected is False