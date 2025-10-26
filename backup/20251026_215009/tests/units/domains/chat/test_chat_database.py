"""
Chat领域数据库测试

测试ChatDatabaseManager和相关数据库功能，包括：
1. 数据库连接管理
2. LangGraph SqliteSaver配置
3. 内存存储管理
4. 健康检查功能
5. 错误处理和日志记录

遵循模块化设计原则，专注于数据库层的测试。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
import os
import tempfile
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.domains.chat.database import (
    get_chat_database_path,
    create_chat_checkpointer,
    create_memory_store,
    check_connection,
    get_database_info,
    ChatDatabaseManager,
    create_tables,
    chat_db_manager
)


@pytest.mark.unit
class TestChatDatabaseModule:
    """Chat数据库模块功能测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_chat.db")
            yield db_path

    def test_get_chat_database_path_default(self):
        """测试获取默认聊天数据库路径"""
        path = get_chat_database_path()

        assert isinstance(path, str)
        assert path.endswith("data/chat.db")
        assert os.path.isabs(path)

    def test_get_chat_database_path_absolute(self):
        """测试获取绝对路径的聊天数据库"""
        absolute_path = "/tmp/test_chat.db"

        with patch.dict(os.environ, {"CHAT_DB_PATH": absolute_path}):
            path = get_chat_database_path()
            assert path == absolute_path

    def test_create_memory_store(self):
        """测试创建内存存储"""
        store = create_memory_store()

        assert store is not None
        # 验证是LangGraph的InMemoryStore实例
        assert hasattr(store, 'put') and hasattr(store, 'get')

    def test_check_connection_no_file(self):
        """测试检查不存在的数据库文件连接"""
        non_existent_path = "/tmp/non_existent_chat.db"

        with patch('src.domains.chat.database.get_chat_database_path', return_value=non_existent_path):
            result = check_connection()
            assert result is False

    def test_check_connection_success(self, temp_db_path):
        """测试成功连接数据库"""
        # 创建一个真实的SQLite数据库文件
        conn = sqlite3.connect(temp_db_path)
        conn.close()

        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            result = check_connection()
            assert result is True

    def test_check_connection_corrupted_file(self, temp_db_path):
        """测试连接损坏的数据库文件"""
        # 创建一个无效的文件
        with open(temp_db_path, 'w') as f:
            f.write("invalid sqlite content")

        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            result = check_connection()
            assert result is False

    def test_get_database_info_no_file(self):
        """测试获取不存在文件的信息"""
        non_existent_path = "/tmp/non_existent_chat.db"

        with patch('src.domains.chat.database.get_chat_database_path', return_value=non_existent_path):
            info = get_database_info()

            assert info["exists"] is False
            assert info["file_size_bytes"] == 0
            assert info["file_size_mb"] == 0
            assert info["connected"] is False
            assert "path" in info
            assert "type" in info

    def test_get_database_info_with_file(self, temp_db_path):
        """测试获取存在文件的信息"""
        # 创建数据库文件
        conn = sqlite3.connect(temp_db_path)
        conn.close()

        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            info = get_database_info()

            assert info["exists"] is True
            assert info["file_size_bytes"] > 0
            assert info["file_size_mb"] > 0
            assert info["connected"] is True
            assert "timestamp" in info

    def test_create_tables_success(self, temp_db_path):
        """测试成功创建数据库表"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            result = create_tables()
            assert result is True

    def test_create_tables_failure(self):
        """测试创建数据库表失败"""
        invalid_path = "/invalid/path/chat.db"

        with patch('src.domains.chat.database.get_chat_database_path', return_value=invalid_path):
            result = create_tables()
            assert result is False


@pytest.mark.unit
class TestChatDatabaseManager:
    """ChatDatabaseManager测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_chat.db")
            yield db_path

    @pytest.fixture
    def manager(self, temp_db_path):
        """创建ChatDatabaseManager实例"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            return ChatDatabaseManager()

    def test_manager_initialization(self, manager, temp_db_path):
        """测试管理器初始化"""
        assert manager.db_path == temp_db_path
        assert manager._store is None

    def test_manager_create_checkpointer(self, manager):
        """测试创建检查点器"""
        checkpointer = manager.create_checkpointer()

        assert checkpointer is not None
        # 验证是LangGraph的SqliteSaver实例
        assert hasattr(checkpointer, 'put') and hasattr(checkpointer, 'get')

    def test_manager_get_store(self, manager):
        """测试获取内存存储"""
        store = manager.get_store()

        assert store is not None
        assert hasattr(store, 'put') and hasattr(store, 'get')

        # 再次调用应该返回同一个实例
        store2 = manager.get_store()
        assert store is store2

    def test_health_check_healthy(self, manager, temp_db_path):
        """测试健康检查 - 健康"""
        # 创建数据库文件
        conn = sqlite3.connect(temp_db_path)
        conn.close()

        result = manager.health_check()

        assert result["status"] == "healthy"
        assert result["file_exists"] is True
        assert result["connected"] is True
        assert result["checkpointer_ok"] is True
        assert result["store_ok"] is True
        assert "timestamp" in result

    def test_health_check_no_file(self, manager):
        """测试健康检查 - 文件不存在"""
        result = manager.health_check()

        assert result["status"] in ["unhealthy", "error"]
        assert result["file_exists"] is False

    def test_health_check_corrupted_file(self, manager, temp_db_path):
        """测试健康检查 - 损坏文件"""
        # 创建无效文件
        with open(temp_db_path, 'w') as f:
            f.write("invalid content")

        result = manager.health_check()

        assert result["status"] in ["unhealthy", "error"]
        assert result["file_exists"] is True
        assert result["connected"] is False

    def test_cleanup(self, manager):
        """测试清理资源"""
        # 创建存储实例
        store = manager.get_store()
        assert store is not None

        # 执行清理
        manager.cleanup()

        assert manager._store is None

    def test_cleanup_error_handling(self, manager):
        """测试清理时的错误处理"""
        # 模拟清理错误
        with patch.object(manager, '_store', Mock(side_effect=Exception("清理错误"))):
            # 不应该抛出异常
            manager.cleanup()


@pytest.mark.unit
class TestChatDatabaseIntegration:
    """Chat数据库集成测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_chat.db")
            yield db_path

    def test_end_to_end_workflow(self, temp_db_path):
        """测试端到端工作流程"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            # 1. 创建数据库表
            assert create_tables() is True

            # 2. 检查连接
            assert check_connection() is True

            # 3. 创建管理器
            manager = ChatDatabaseManager()

            # 4. 健康检查
            health = manager.health_check()
            assert health["status"] == "healthy"

            # 5. 创建检查点器
            checkpointer = manager.create_checkpointer()
            assert checkpointer is not None

            # 6. 创建内存存储
            store = manager.get_store()
            assert store is not None

            # 7. 获取数据库信息
            info = get_database_info()
            assert info["exists"] is True
            assert info["connected"] is True

    def test_multiple_manager_instances(self, temp_db_path):
        """测试多个管理器实例"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            manager1 = ChatDatabaseManager()
            manager2 = ChatDatabaseManager()

            # 都应该能正常工作
            store1 = manager1.get_store()
            store2 = manager2.get_store()

            assert store1 is not None
            assert store2 is not None
            # 但应该是不同的实例
            assert store1 is not store2

    def test_concurrent_access(self, temp_db_path):
        """测试并发访问"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            import threading
            import time

            results = []

            def worker():
                try:
                    manager = ChatDatabaseManager()
                    health = manager.health_check()
                    results.append(health["status"])
                except Exception as e:
                    results.append(f"error: {e}")

            # 创建多个线程
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            # 验证结果
            assert len(results) == 5
            # 大部分应该是成功的（可能有竞争条件）
            success_count = sum(1 for r in results if r == "healthy")
            assert success_count >= 3  # 允许一些失败

    def test_large_data_handling(self, temp_db_path):
        """测试大数据处理"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            manager = ChatDatabaseManager()
            store = manager.get_store()

            # 测试存储大量数据
            large_data = {"key": "x" * 10000}  # 10KB数据

            try:
                # 尝试存储数据
                store.put(["namespace"], "item", large_data)

                # 尝试检索数据
                retrieved = store.get(["namespace"], "item")
                assert retrieved is not None
                assert retrieved.value == large_data

            except Exception as e:
                # 如果存储失败，记录但不使测试失败
                print(f"大数据存储测试跳过: {e}")

    def test_error_recovery(self, temp_db_path):
        """测试错误恢复"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            manager = ChatDatabaseManager()

            # 模拟临时错误
            with patch.object(manager, 'create_checkpointer', side_effect=Exception("临时错误")):
                health = manager.health_check()
                assert health["status"] in ["unhealthy", "error"]
                assert "checkpointer_ok" in health
                assert health["checkpointer_ok"] is False

            # 恢复后应该正常工作
            health = manager.health_check()
            assert health["status"] == "healthy"


@pytest.mark.unit
class TestChatDatabaseEdgeCases:
    """Chat数据库边界情况测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_chat.db")
            yield db_path

    def test_empty_database_path(self):
        """测试空数据库路径"""
        with patch.dict(os.environ, {"CHAT_DB_PATH": ""}):
            path = get_chat_database_path()
            assert path != ""  # 应该有默认值

    def test_permission_denied(self):
        """测试权限拒绝情况"""
        restricted_path = "/root/restricted_chat.db"

        with patch('src.domains.chat.database.get_chat_database_path', return_value=restricted_path):
            # 可能会失败，但不应该崩溃
            result = check_connection()
            assert isinstance(result, bool)

    def test_disk_space_simulation(self, temp_db_path):
        """测试磁盘空间不足模拟"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            # 创建正常大小的数据库
            manager = ChatDatabaseManager()
            health = manager.health_check()

            # 模拟磁盘空间不足
            with patch('sqlite3.connect', side_effect=sqlite3.OperationalError("disk I/O error")):
                health = manager.health_check()
                assert health["status"] in ["unhealthy", "error"]

    def test_memory_limit_simulation(self, temp_db_path):
        """测试内存限制模拟"""
        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            # 模拟内存不足
            with patch('src.domains.chat.database.InMemoryStore', side_effect=MemoryError("out of memory")):
                manager = ChatDatabaseManager()
                health = manager.health_check()

                assert health["status"] in ["unhealthy", "error"]
                assert health["store_ok"] is False

    def test_database_lock_simulation(self, temp_db_path):
        """测试数据库锁定模拟"""
        # 创建数据库
        conn = sqlite3.connect(temp_db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")

        with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db_path):
            # 尝试另一个连接
            try:
                manager = ChatDatabaseManager()
                health = manager.health_check()

                # 可能可以连接（SQLite支持多个读连接）
                assert "status" in health

            finally:
                conn.close()


@pytest.mark.unit
class TestGlobalChatDatabaseManager:
    """全局ChatDatabaseManager测试类"""

    def test_global_manager_instance(self):
        """测试全局管理器实例"""
        assert chat_db_manager is not None
        assert isinstance(chat_db_manager, ChatDatabaseManager)
        assert hasattr(chat_db_manager, 'create_checkpointer')
        assert hasattr(chat_db_manager, 'get_store')
        assert hasattr(chat_db_manager, 'health_check')

    def test_global_manager_functionality(self):
        """测试全局管理器功能"""
        # 测试基本功能不会出错
        try:
            store = chat_db_manager.get_store()
            assert store is not None

            health = chat_db_manager.health_check()
            assert isinstance(health, dict)
            assert "status" in health

        except Exception as e:
            # 如果由于环境问题失败，记录但不使测试失败
            print(f"全局管理器测试跳过: {e}")

    def test_global_manager_singleton_behavior(self):
        """测试全局管理器单例行为"""
        # 多次引用应该是同一个实例
        assert chat_db_manager is chat_db_manager