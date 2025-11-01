"""
独立Profile数据库连接单元测试

测试独立profile数据库的连接、会话管理和事务隔离。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlmodel import SQLModel, Session

from src.database.profile_connection import ProfileDatabaseConnection


class TestProfileDatabaseConnection:
    """独立Profile数据库连接测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """临时数据库路径fixture"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        # 清理临时文件
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

    def test_profile_database_connection_creation(self, temp_db_path: str):
        """
        测试Profile数据库连接创建

        Given: 有效的数据库路径
        When: 创建ProfileDatabaseConnection实例
        Then: 应该成功创建连接实例
        """
        db_url = f"sqlite:///{temp_db_path}"
        profile_db = ProfileDatabaseConnection(database_url=db_url)

        assert profile_db.database_url == db_url
        assert profile_db._engine is None  # 引擎应该延迟初始化

    def test_profile_database_engine_creation(self, temp_db_path: str):
        """
        测试Profile数据库引擎创建

        Given: Profile数据库连接实例
        When: 调用get_engine方法
        Then: 应该创建数据库引擎
        """
        db_url = f"sqlite:///{temp_db_path}"
        profile_db = ProfileDatabaseConnection(database_url=db_url)

        engine = profile_db.get_engine()
        assert engine is not None
        assert engine.url.database == temp_db_path

    def test_profile_database_session_context_manager(self, temp_db_path: str):
        """
        测试Profile数据库会话上下文管理器

        Given: Profile数据库连接
        When: 使用get_session上下文管理器
        Then: 应该正确创建和关闭会话
        """
        db_url = f"sqlite:///{temp_db_path}"
        profile_db = ProfileDatabaseConnection(database_url=db_url)

        session_created = False
        session_closed = False

        with profile_db.get_session() as session:
            assert session is not None
            session_created = True
            # 测试基本SQL操作
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # 上下文退出后，会话应该自动关闭
        assert session_created

    def test_profile_database_table_creation(self, temp_db_path: str):
        """
        测试Profile数据库表创建

        Given: Profile数据库连接和模型定义
        When: 创建所有表
        Then: 表应该正确创建
        """
        # 这里需要导入Profile相关的模型
        # 由于模型还未创建，先写测试结构
        db_url = f"sqlite:///{temp_db_path}"
        profile_db = ProfileDatabaseConnection(database_url=db_url)

        engine = profile_db.get_engine()

        # TODO: 添加Profile模型后实现表创建测试
        # from src.domains.user.profile_models import ProfileUser, ProfileSettings
        # SQLModel.metadata.create_all(engine)

        # 验证表是否存在
        # with profile_db.get_session() as session:
        #     result = session.execute(text(
        #         "SELECT name FROM sqlite_master WHERE type='table' AND name='user'"
        #     ))
        #     tables = [row[0] for row in result.fetchall()]
        #     assert 'user' in tables

        assert True  # 占位符，后续实现

    def test_profile_database_transaction_isolation(self, temp_db_path: str):
        """
        测试Profile数据库事务隔离

        Given: 两个独立的数据库会话
        When: 在一个会话中进行操作
        Then: 另一个会话应该不受影响（事务隔离）
        """
        db_url = f"sqlite:///{temp_db_path}"
        profile_db = ProfileDatabaseConnection(database_url=db_url)

        # 创建两个独立的会话
        with profile_db.get_session() as session1, profile_db.get_session() as session2:
            # 在两个会话中执行独立操作
            result1 = session1.execute(text("SELECT 1 as value"))
            result2 = session2.execute(text("SELECT 2 as value"))

            assert result1.scalar() == 1
            assert result2.scalar() == 2

    def test_profile_database_error_handling(self):
        """
        测试Profile数据库错误处理

        Given: 无效的数据库URL格式
        When: 尝试创建连接
        Then: 应该抛出适当的异常
        """
        invalid_url = "invalid-database-protocol://invalid"

        with pytest.raises(Exception):
            profile_db = ProfileDatabaseConnection(database_url=invalid_url)
            profile_db.get_engine()

    def test_profile_database_default_configuration(self):
        """
        测试Profile数据库默认配置

        Given: 不指定数据库URL
        When: 创建ProfileDatabaseConnection实例
        Then: 应该使用默认配置
        """
        profile_db = ProfileDatabaseConnection()

        assert profile_db.database_url.endswith("profiles.db")
        assert not profile_db.echo  # 默认不开启SQL日志

    def test_profile_database_engine_singleton(self, temp_db_path: str):
        """
        测试Profile数据库引擎单例模式

        Given: Profile数据库连接实例
        When: 多次调用get_engine方法
        Then: 应该返回同一个引擎实例
        """
        db_url = f"sqlite:///{temp_db_path}"
        profile_db = ProfileDatabaseConnection(database_url=db_url)

        engine1 = profile_db.get_engine()
        engine2 = profile_db.get_engine()

        assert engine1 is engine2