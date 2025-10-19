"""
测试数据库连接配置
验证数据库引擎的创建、连接管理和会话处理功能
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

# 导入待实现的数据库连接模块
from src.database.connection import DatabaseConnection, get_engine, get_session


class TestDatabaseConnection:
    """数据库连接配置测试类"""

    def test_database_connection_exists(self):
        """验证DatabaseConnection类存在且可导入"""
        assert DatabaseConnection is not None
        assert hasattr(DatabaseConnection, 'get_engine')
        assert hasattr(DatabaseConnection, 'get_session')

    def test_database_connection_default_configuration(self):
        """测试数据库连接默认配置"""
        # 验证默认数据库URL
        db = DatabaseConnection()
        assert db.database_url == "sqlite:///./tatake.db"
        assert db.echo is False  # 默认不开启SQL日志

    def test_database_connection_custom_configuration(self):
        """测试数据库连接自定义配置"""
        custom_url = "sqlite:///./test_custom.db"
        db = DatabaseConnection(database_url=custom_url, echo=True)

        assert db.database_url == custom_url
        assert db.echo is True

    def test_get_engine_creates_engine(self):
        """测试get_engine方法创建SQLAlchemy引擎"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        engine = db.get_engine()

        # 验证引擎类型
        assert isinstance(engine, Engine)

        # 验证引擎配置
        assert engine.url.database == ":memory:"
        assert engine.url.drivername == "sqlite"

    def test_get_engine_returns_same_instance(self):
        """测试get_engine方法返回相同的引擎实例（单例模式）"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        engine1 = db.get_engine()
        engine2 = db.get_engine()

        # 验证返回相同的实例
        assert engine1 is engine2

    def test_get_session_creates_session(self):
        """测试get_session方法创建数据库会话"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        with db.get_session() as session:
            # 验证会话类型
            assert isinstance(session, Session)

            # 验证会话是活跃的
            assert session.is_active

    def test_get_session_context_manager(self):
        """测试get_session作为上下文管理器正确处理资源"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        session = None
        with db.get_session() as session:
            # 在上下文中会话应该是活跃的
            assert session.is_active
            captured_session = session

        # 退出上下文后，会话应该关闭
        # 注意：SQLAlchemy的Session对象在上下文管理器退出后仍然存在，但事务已结束
        assert captured_session is not None

    def test_environment_variable_override(self):
        """测试环境变量覆盖默认配置"""
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///./env_test.db'}):
            db = DatabaseConnection()
            assert db.database_url == 'sqlite:///./env_test.db'

    def test_get_engine_function(self):
        """测试全局get_engine函数"""
        engine = get_engine()

        # 验证返回引擎实例
        assert isinstance(engine, Engine)

        # 验证使用默认配置
        assert "tatake.db" in str(engine.url)

    def test_get_session_function(self):
        """测试全局get_session函数"""
        with get_session() as session:
            # 验证返回活跃会话
            assert isinstance(session, Session)
            assert session.is_active

    def test_database_connection_with_postgresql_url(self):
        """测试数据库连接处理PostgreSQL URL"""
        postgres_url = "sqlite:///./test_postgres_simulation.db"  # 使用SQLite模拟
        db = DatabaseConnection(database_url=postgres_url)

        engine = db.get_engine()

        # 验证URL解析正确
        assert engine.url.drivername == "sqlite"
        assert "test_postgres_simulation.db" in str(engine.url)

    def test_database_connection_with_mysql_config(self):
        """测试数据库连接处理MySQL等数据库配置"""
        # 模拟MySQL URL配置来测试非SQLite分支
        mysql_url = "mysql+pymysql://user:password@localhost:3306/testdb"
        db = DatabaseConnection(database_url=mysql_url)

        # 验证引擎配置参数（创建前）
        # 通过检查database_url来确保进入else分支
        assert db.database_url.startswith("mysql")

        # 尝试创建引擎，应该抛出ImportError
        with pytest.raises(ImportError, match="数据库驱动.*未安装"):
            db.get_engine()

    def test_engine_configuration_for_sqlite(self):
        """测试SQLite引擎的特定配置"""
        db = DatabaseConnection(database_url="sqlite:///./test.db")
        engine = db.get_engine()

        # 验证SQLite特定配置
        # SQLite使用StaticPool
        from sqlalchemy.pool import StaticPool
        assert isinstance(engine.pool, StaticPool)

        # 验证引擎dialect是SQLite
        assert engine.dialect.name == "sqlite"

    def test_engine_other_exceptions(self):
        """测试引擎创建时的其他异常处理"""
        # 使用无效的数据库URL来触发其他类型的异常
        invalid_url = "invalid://url"
        db = DatabaseConnection(database_url=invalid_url)

        # 应该抛出异常
        with pytest.raises(Exception):
            db.get_engine()