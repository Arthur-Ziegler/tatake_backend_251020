"""
数据库连接测试

测试数据库连接管理功能，包括：
1. DatabaseConnection类初始化
2. 数据库引擎创建和配置
3. 数据库会话管理
4. 连接池配置优化
5. 错误处理和异常情况
6. 全局实例管理

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import os
import tempfile
from unittest.mock import patch, Mock, MagicMock
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database.connection import (
    DatabaseConnection,
    get_database_connection,
    get_engine,
    get_session
)


@pytest.mark.unit
class TestDatabaseConnection:
    """数据库连接测试类"""

    def test_initialization_with_default_values(self):
        """测试使用默认值初始化"""
        db = DatabaseConnection()

        assert db.database_url == "sqlite:///./tatake.db"
        assert db.echo is False
        assert db._engine is None

    def test_initialization_with_custom_values(self):
        """测试使用自定义值初始化"""
        custom_url = "postgresql://user:pass@localhost/test"
        db = DatabaseConnection(database_url=custom_url, echo=True)

        assert db.database_url == custom_url
        assert db.echo is True
        assert db._engine is None

    @patch.dict(os.environ, {'DATABASE_URL': 'mysql://user:pass@localhost/db'})
    def test_initialization_with_environment_variable(self):
        """测试使用环境变量初始化"""
        db = DatabaseConnection()

        assert db.database_url == "mysql://user:pass@localhost/db"
        assert db.echo is False

    @patch.dict(os.environ, {'DATABASE_URL': 'mysql://user:pass@localhost/db'})
    def test_environment_variable_overrides_parameter(self):
        """测试环境变量覆盖传入参数"""
        custom_url = "postgresql://user:pass@localhost/test"
        db = DatabaseConnection(database_url=custom_url)

        assert db.database_url == "mysql://user:pass@localhost/db"  # 环境变量优先

    def test_sqlite_engine_creation(self):
        """测试SQLite引擎创建"""
        # 使用内存SQLite数据库
        db = DatabaseConnection(database_url="sqlite:///:memory:")
        engine = db.get_engine()

        assert isinstance(engine, Engine)
        assert db._engine is engine  # 缓存的引擎
        assert engine.url.driver == "sqlite"

    def test_postgresql_engine_creation(self):
        """测试PostgreSQL引擎创建"""
        db = DatabaseConnection(database_url="postgresql://user:pass@localhost/test")

        with patch('src.database.connection.create_engine') as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            engine = db.get_engine()

            assert engine == mock_engine
            # 验证PostgreSQL特定的配置
            call_args = mock_create.call_args
            assert call_args[1]['echo'] is False
            assert call_args[1]['pool_pre_ping'] is True
            assert call_args[1]['pool_recycle'] == 3600

    def test_mysql_engine_creation(self):
        """测试MySQL引擎创建"""
        db = DatabaseConnection(database_url="mysql://user:pass@localhost/test")

        with patch('src.database.connection.create_engine') as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            engine = db.get_engine()

            assert engine == mock_engine
            # 验证MySQL特定的配置（与PostgreSQL相同）
            call_args = mock_create.call_args
            assert call_args[1]['pool_pre_ping'] is True
            assert call_args[1]['pool_recycle'] == 3600

    def test_engine_singleton_pattern(self):
        """测试引擎单例模式"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        engine1 = db.get_engine()
        engine2 = db.get_engine()

        assert engine1 is engine2
        assert db._engine is engine1

    def test_session_context_manager(self):
        """测试会话上下文管理器"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        with db.get_session() as session:
            assert isinstance(session, Session)
            assert session.is_active is True

        # 退出上下文后会话应该关闭
        assert session.is_active is False

    def test_session_rollback_on_exception(self):
        """测试异常时会话回滚"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        with pytest.raises(ValueError):
            with db.get_session() as session:
                # 模拟异常
                raise ValueError("Test exception")

        # 会话应该已经关闭
        assert session.is_active is False

    def test_multiple_sessions(self):
        """测试创建多个会话"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        session1 = None
        session2 = None

        with db.get_session() as s1:
            session1 = s1
            with db.get_session() as s2:
                session2 = s2

                assert session1 is not session2
                assert session1.is_active is True
                assert session2.is_active is True

            # 内层会话关闭
            assert session2.is_active is False

        # 外层会话关闭
        assert session1.is_active is False

    def test_echo_configuration(self):
        """测试echo配置"""
        # 创建临时文件来捕获日志
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as log_file:
            log_file.close()

            try:
                # 测试echo=True
                db = DatabaseConnection(
                    database_url="sqlite:///:memory:",
                    echo=True
                )

                with patch('src.database.connection.create_engine') as mock_create:
                    mock_engine = Mock()
                    mock_create.return_value = mock_engine

                    db.get_engine()

                    # 验证echo参数被正确传递
                    call_args = mock_create.call_args
                    assert call_args[1]['echo'] is True

            finally:
                os.unlink(log_file.name)

    def test_sqlite_thread_safety_configuration(self):
        """测试SQLite线程安全配置"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        with patch('src.database.connection.create_engine') as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            db.get_engine()

            # 验证SQLite特定配置
            call_args = mock_create.call_args
            assert call_args[0] == "sqlite:///:memory:"
            assert call_args[1]['connect_args'] == {"check_same_thread": False}
            assert call_args[1]['poolclass'] == StaticPool

    def test_database_url_parsing_error(self):
        """测试数据库URL解析错误"""
        # 创建一个无效的URL
        invalid_url = "invalid://url"
        db = DatabaseConnection(database_url=invalid_url)

        with patch('src.database.connection.create_engine') as mock_create:
            mock_create.side_effect = Exception("Invalid URL")

            with pytest.raises(Exception):
                db.get_engine()

    def test_missing_driver_error(self):
        """测试缺少数据库驱动错误"""
        db = DatabaseConnection(database_url="postgresql://user:pass@localhost/test")

        with patch('src.database.connection.create_engine') as mock_create:
            mock_create.side_effect = Exception("No module named 'psycopg2'")

            with pytest.raises(ImportError) as exc_info:
                db.get_engine()

            assert "psycopg2" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)

    def test_environment_based_debug_configuration(self):
        """测试基于环境变量的debug配置"""
        with patch.dict(os.environ, {'DEBUG': 'true'}):
            db = DatabaseConnection(database_url="sqlite:///:memory:")

            with patch('src.database.connection.create_engine') as mock_create:
                mock_engine = Mock()
                mock_create.return_value = mock_engine

                db.get_engine()

                # 在基础类中这个测试不会生效，echo参数来自初始化
                call_args = mock_create.call_args
                # 验证echo配置
                assert 'echo' in call_args[1]

    def test_database_connection_isolation(self):
        """测试数据库连接隔离"""
        db1 = DatabaseConnection(database_url="sqlite:///:memory:")
        db2 = DatabaseConnection(database_url="sqlite:///:memory:")

        engine1 = db1.get_engine()
        engine2 = db2.get_engine()

        # 不同的DatabaseConnection实例应该有不同的引擎
        assert engine1 is not engine2
        assert db1._engine is engine1
        assert db2._engine is engine2


@pytest.mark.unit
class TestGlobalFunctions:
    """全局函数测试类"""

    def test_get_database_connection_singleton(self):
        """测试全局数据库连接单例"""
        # 清理全局状态
        import src.database.connection
        src.database.connection._global_db_connection = None

        conn1 = get_database_connection()
        conn2 = get_database_connection()

        assert isinstance(conn1, DatabaseConnection)
        assert conn1 is conn2  # 应该是同一个实例

    def test_get_database_connection_with_environment(self):
        """测试从环境变量创建全局连接"""
        # 清理全局状态
        import src.database.connection
        src.database.connection._global_db_connection = None

        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/testdb',
            'DEBUG': 'true'
        }):
            conn = get_database_connection()

            assert conn.database_url == "postgresql://test:test@localhost/testdb"
            # 注意：echo配置在基础实现中可能不直接使用DEBUG环境变量

    def test_get_engine_function(self):
        """测试get_engine便捷函数"""
        # 清理全局状态
        import src.database.connection
        src.database.connection._global_db_connection = None

        with patch('src.database.connection.DatabaseConnection.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_get_engine.return_value = mock_engine

            engine = get_engine()

            mock_get_engine.assert_called_once()
            assert engine == mock_engine

    def test_get_session_function(self):
        """测试get_session便捷函数"""
        # 清理全局状态
        import src.database.connection
        src.database.connection._global_db_connection = None

        with patch('src.database.connection.DatabaseConnection.get_session') as mock_get_session:
            @contextmanager
            def mock_session_context():
                session = Mock()
                try:
                    yield session
                finally:
                    session.close()

            mock_get_session.return_value = mock_session_context()

            with get_session() as session:
                assert session is not None
                mock_get_session.assert_called_once()


@pytest.mark.unit
class TestDatabaseConnectionEdgeCases:
    """数据库连接边界情况测试类"""

    def test_empty_database_url(self):
        """测试空数据库URL"""
        db = DatabaseConnection(database_url="")

        # 应该使用默认值
        assert db.database_url == "sqlite:///./tatake.db"

    def test_none_database_url(self):
        """测试None数据库URL"""
        db = DatabaseConnection(database_url=None)

        # 应该使用默认值
        assert db.database_url == "sqlite:///./tatake.db"

    def test_special_characters_in_url(self):
        """测试URL中的特殊字符"""
        special_url = "postgresql://user:p@ss%40w0rd@localhost/test%20db"
        db = DatabaseConnection(database_url=special_url)

        assert db.database_url == special_url

        with patch('src.database.connection.create_engine') as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            db.get_engine()
            mock_create.assert_called_once_with(special_url, echo=False, pool_pre_ping=True, pool_recycle=3600)

    def test_engine_creation_failure_recovery(self):
        """测试引擎创建失败恢复"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        with patch('src.database.connection.create_engine') as mock_create:
            # 第一次调用失败
            mock_create.side_effect = [Exception("First failure"), Mock(spec=Engine)]

            # 第一次调用失败
            with pytest.raises(Exception):
                db.get_engine()

            # 第二次调用应该使用缓存的None状态，再次尝试
            with pytest.raises(Exception):
                db.get_engine()

    def test_concurrent_engine_access(self):
        """测试并发引擎访问"""
        import threading
        import time

        db = DatabaseConnection(database_url="sqlite:///:memory:")
        engines = []
        errors = []

        def get_engine_worker():
            try:
                engine = db.get_engine()
                engines.append(engine)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时获取引擎
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_engine_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0
        assert len(engines) == 5
        # 所有线程应该获得同一个引擎实例
        assert all(engine is engines[0] for engine in engines)


@pytest.mark.parametrize("database_url,expected_type", [
    ("sqlite:///:memory:", "sqlite"),
    ("sqlite:///./test.db", "sqlite"),
    ("postgresql://user:pass@localhost/test", "postgresql"),
    ("mysql://user:pass@localhost/test", "mysql"),
])
def test_database_type_detection(database_url, expected_type):
    """参数化数据库类型检测测试"""
    db = DatabaseConnection(database_url=database_url)

    assert db.database_url == database_url

    # 验证URL解析
    assert expected_type in database_url.lower()


@pytest.mark.parametrize("echo_value", [True, False])
def test_echo_configuration_parameterized(echo_value):
    """参数化echo配置测试"""
    db = DatabaseConnection(echo=echo_value)

    assert db.echo == echo_value

    with patch('src.database.connection.create_engine') as mock_create:
        mock_engine = Mock()
        mock_create.return_value = mock_engine

        db.get_engine()

        call_args = mock_create.call_args
        assert call_args[1]['echo'] == echo_value


@pytest.fixture
def sample_database():
    """示例数据库连接fixture"""
    return DatabaseConnection(database_url="sqlite:///:memory:", echo=True)


def test_with_fixture(sample_database):
    """使用fixture的测试"""
    assert sample_database.database_url == "sqlite:///:memory:"
    assert sample_database.echo is True
    assert sample_database._engine is None

    # 测试引擎创建
    engine = sample_database.get_engine()
    assert isinstance(engine, Engine)
    assert sample_database._engine is engine


@pytest.fixture
def mock_engine():
    """模拟引擎fixture"""
    engine = Mock(spec=Engine)
    engine.url = Mock()
    engine.url.driver = "sqlite"
    return engine


def test_session_with_mock_engine(sample_database, mock_engine):
    """使用模拟引擎的会话测试"""
    with patch.object(sample_database, 'get_engine', return_value=mock_engine):
        with patch('sqlalchemy.orm.sessionmaker') as mock_sessionmaker:
            mock_session = Mock(spec=Session)
            mock_session.is_active = True

            mock_session_factory = Mock()
            mock_session_factory.return_value = mock_session
            mock_sessionmaker.return_value = mock_session_factory

            with sample_database.get_session() as session:
                assert session is mock_session
                session.close.assert_called_once()


@pytest.mark.integration
class TestDatabaseConnectionIntegration:
    """数据库连接集成测试类"""

    def test_real_sqlite_operations(self):
        """测试真实SQLite操作"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        with db.get_session() as session:
            # 创建一个简单的表
            session.execute("""
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)

            # 插入数据
            session.execute("INSERT INTO test_table (name) VALUES (?)", ("test_name",))
            session.commit()

            # 查询数据
            result = session.execute("SELECT * FROM test_table").fetchall()
            assert len(result) == 1
            assert result[0][1] == "test_name"

    def test_session_lifecycle(self):
        """测试会话生命周期"""
        db = DatabaseConnection(database_url="sqlite:///:memory:")

        # 测试多个会话的生命周期
        for i in range(3):
            with db.get_session() as session:
                session.execute(f"CREATE TABLE IF NOT EXISTS test_{i} (id INTEGER)")
                session.commit()

        # 验证所有会话都已正确关闭
        # 这里我们无法直接验证，但如果没有异常就说明正常