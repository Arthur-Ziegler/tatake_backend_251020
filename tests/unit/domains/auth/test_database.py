"""
Auth领域数据库模块测试

测试数据库连接、表管理、健康检查等功能，包括：
1. 数据库连接管理
2. 表创建和删除
3. 连接检查和健康状态
4. 数据库信息获取
5. 数据库结构验证

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import os
import pytest
from unittest.mock import patch

from src.domains.auth.database import (
    get_auth_db,
    create_tables,
    drop_tables,
    check_connection,
    get_database_info,
    AuthDatabaseManager,
    auth_db_manager
)


@pytest.mark.unit
class TestDatabaseConnection:
    """数据库连接测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        # 设置内存数据库
        os.environ["AUTH_DATABASE_URL"] = "sqlite:///:memory:"

        # 重新导入数据库模块以使用新的数据库URL
        import importlib
        import src.domains.auth.database
        importlib.reload(src.domains.auth.database)

        yield

        # 测试结束后清理
        if "AUTH_DATABASE_URL" in os.environ:
            del os.environ["AUTH_DATABASE_URL"]

    def test_get_auth_db_context_manager(self):
        """测试数据库会话上下文管理器"""
        with get_auth_db() as session:
            assert session is not None
            # 验证会话是活跃的
            assert session.is_active

    def test_get_auth_db_automatic_rollback_on_error(self):
        """测试错误时自动回滚"""
        with pytest.raises(Exception):
            with get_auth_db() as session:
                # 执行一个会失败的操作
                from sqlalchemy import text
                session.execute(text("INVALID SQL STATEMENT"))

        # 即使出错，会话也应该正确关闭
        assert not session.is_active

    def test_get_auth_db_session_closed_after_context(self):
        """测试上下文结束后会话自动关闭"""
        with get_auth_db() as session:
            db_session = session
            assert db_session.is_active

        # 上下文结束后会话应该关闭
        assert not db_session.is_active


@pytest.mark.unit
class TestTableManagement:
    """表管理测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        os.environ["AUTH_DATABASE_URL"] = "sqlite:///:memory:"

        import importlib
        import src.domains.auth.database
        importlib.reload(src.domains.auth.database)

        yield

        if "AUTH_DATABASE_URL" in os.environ:
            del os.environ["AUTH_DATABASE_URL"]

    def test_create_tables_success(self):
        """测试成功创建表"""
        # 创建表应该不抛出异常
        create_tables()

        # 验证表确实存在
        with get_auth_db() as session:
            from sqlalchemy import text

            # 检查auth表
            result = session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='auth'"
            ))
            assert result.scalar() == 1

            # 检查auth_audit_logs表
            result = session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='auth_audit_logs'"
            ))
            assert result.scalar() == 1

    def test_create_tables_idempotent(self):
        """测试创建表的幂等性（重复创建不报错）"""
        # 第一次创建
        create_tables()

        # 第二次创建应该不报错
        create_tables()

        # 验证表仍然存在且数量正确
        with get_auth_db() as session:
            from sqlalchemy import text
            result = session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ))
            # 至少应该有2个表（auth和auth_audit_logs）
            assert result.scalar() >= 2

    def test_drop_tables_success(self):
        """测试成功删除表"""
        # 先创建表
        create_tables()

        # 验证表存在
        with get_auth_db() as session:
            from sqlalchemy import text
            result = session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='auth'"
            ))
            assert result.scalar() == 1

        # 删除表
        drop_tables()

        # 验证表不存在
        with get_auth_db() as session:
            from sqlalchemy import text
            result = session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='auth'"
            ))
            assert result.scalar() == 0

    def test_drop_tables_idempotent(self):
        """测试删除表的幂等性（重复删除不报错）"""
        # 删除不存在的表应该不报错
        drop_tables()

        # 再次删除应该也不报错
        drop_tables()


@pytest.mark.unit
class TestConnectionCheck:
    """连接检查测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        os.environ["AUTH_DATABASE_URL"] = "sqlite:///:memory:"

        import importlib
        import src.domains.auth.database
        importlib.reload(src.domains.auth.database)

        yield

        if "AUTH_DATABASE_URL" in os.environ:
            del os.environ["AUTH_DATABASE_URL"]

    def test_check_connection_success(self):
        """测试连接检查成功"""
        result = check_connection()
        assert result is True

    def test_check_connection_failure(self):
        """测试连接检查失败"""
        # 使用无效的数据库URL
        with patch('src.domains.auth.database.AUTH_DATABASE_URL', 'invalid://url'):
            result = check_connection()
            assert result is False


@pytest.mark.unit
class TestDatabaseInfo:
    """数据库信息测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        os.environ["AUTH_DATABASE_URL"] = "sqlite:///:memory:"

        import importlib
        import src.domains.auth.database
        importlib.reload(src.domains.auth.database)

        yield

        if "AUTH_DATABASE_URL" in os.environ:
            del os.environ["AUTH_DATABASE_URL"]

    def test_get_database_info_success(self):
        """测试成功获取数据库信息"""
        # 先创建表
        create_tables()

        info = get_database_info()

        # 验证基本信息
        assert "url" in info
        assert "echo_sql" in info
        assert "table_count" in info
        assert "file_size_mb" in info
        assert "dialect" in info
        assert "driver" in info
        assert "simplified" in info

        # 验证具体值
        assert info["url"] == "sqlite:///:memory:"
        assert isinstance(info["echo_sql"], bool)
        assert info["table_count"] >= 2  # 至少auth和auth_audit_logs
        assert info["file_size_mb"] == 0  # 内存数据库文件大小为0
        assert info["simplified"] is True

    def test_get_database_info_empty_database(self):
        """测试空数据库的信息获取"""
        info = get_database_info()

        # 即使没有表，也应该返回基本信息
        assert "url" in info
        assert info["table_count"] == 0


@pytest.mark.unit
class TestAuthDatabaseManager:
    """数据库管理器测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        os.environ["AUTH_DATABASE_URL"] = "sqlite:///:memory:"

        import importlib
        import src.domains.auth.database
        importlib.reload(src.domains.auth.database)

        yield

        if "AUTH_DATABASE_URL" in os.environ:
            del os.environ["AUTH_DATABASE_URL"]

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = AuthDatabaseManager()

        assert manager.engine is not None
        assert manager.session_factory is not None

    def test_health_check_healthy(self):
        """测试健康检查 - 健康"""
        # 创建表
        create_tables()

        result = auth_db_manager.health_check()

        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert "tables" in result
        assert "timestamp" in result
        assert result["simplified"] is True

        # 验证表检查结果
        tables = result["tables"]
        assert "auth" in tables
        assert "auth_audit_logs" in tables
        assert tables["auth"] is True
        assert tables["auth_audit_logs"] is True

    def test_health_check_unhealthy(self):
        """测试健康检查 - 不健康"""
        # 使用无效的数据库连接
        with patch('src.domains.auth.database.check_connection', return_value=False):
            result = auth_db_manager.health_check()

            assert result["status"] == "unhealthy"
            assert result["connected"] is False

    def test_health_check_error(self):
        """测试健康检查 - 错误"""
        # 模拟异常
        with patch('src.domains.auth.database.check_connection', side_effect=Exception("Connection error")):
            result = auth_db_manager.health_check()

            assert result["status"] == "error"
            assert "error" in result
            assert "Connection error" in result["error"]

    def test_verify_simplified_structure_success(self):
        """测试简化结构验证 - 成功"""
        # 创建表
        create_tables()

        result = auth_db_manager.verify_simplified_structure()

        assert result["auth_table_valid"] is True
        assert result["auth_log_table_valid"] is True
        assert result["old_tables_cleaned"] is True
        assert result["overall_valid"] is True
        assert "timestamp" in result

    def test_verify_simplified_structure_missing_tables(self):
        """测试简化结构验证 - 缺少表"""
        # 不创建表直接验证
        result = auth_db_manager.verify_simplified_structure()

        assert result["auth_table_valid"] is False
        assert result["auth_log_table_valid"] is False
        assert result["overall_valid"] is False

    def test_verify_simplified_structure_error(self):
        """测试简化结构验证 - 错误"""
        # 模拟数据库异常
        with patch('src.domains.auth.database.get_auth_db', side_effect=Exception("Database error")):
            result = auth_db_manager.verify_simplified_structure()

            assert result["overall_valid"] is False
            assert "error" in result
            assert "Database error" in result["error"]


@pytest.mark.integration
class TestDatabaseIntegration:
    """数据库集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        os.environ["AUTH_DATABASE_URL"] = "sqlite:///:memory:"

        import importlib
        import src.domains.auth.database
        importlib.reload(src.domains.auth.database)

        yield

        if "AUTH_DATABASE_URL" in os.environ:
            del os.environ["AUTH_DATABASE_URL"]

    def test_full_database_lifecycle(self):
        """测试完整的数据库生命周期"""
        # 1. 检查初始状态
        assert check_connection() is True

        # 2. 创建表
        create_tables()

        # 3. 验证健康状态
        health = auth_db_manager.health_check()
        assert health["status"] == "healthy"

        # 4. 验证结构
        structure = auth_db_manager.verify_simplified_structure()
        assert structure["overall_valid"] is True

        # 5. 获取信息
        info = get_database_info()
        assert info["table_count"] >= 2

        # 6. 清理表
        drop_tables()

        # 7. 验证清理完成
        info_after = get_database_info()
        assert info_after["table_count"] == 0

    def test_concurrent_sessions(self):
        """测试并发会话处理"""
        create_tables()

        # 创建多个会话
        results = []

        def create_session_and_query():
            with get_auth_db() as session:
                from sqlalchemy import text
                result = session.execute(text("SELECT 1"))
                results.append(result.scalar())

        # 顺序执行多个会话
        create_session_and_query()
        create_session_and_query()
        create_session_and_query()

        # 所有会话都应该成功
        assert len(results) == 3
        assert all(r == 1 for r in results)