"""
聊天数据库持久化测试

测试聊天系统的数据持久化功能，确保数据库正确创建和消息保存。
采用TDD方法，先写测试，再修复实现。

测试重点：
1. 数据库文件正确创建在 data/chat.db
2. 聊天消息能够正确保存
3. 系统重启后数据仍然存在
4. 数据库连接健康检查

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from src.domains.chat.database import (
    create_chat_checkpointer,
    get_chat_database_path,
    check_connection,
    chat_db_manager
)


class TestChatDatabasePersistence:
    """
    聊天数据库持久化测试类

    测试聊天系统的数据持久化功能，确保数据库正确创建和使用。
    """

    def test_database_file_creation(self):
        """
        测试数据库文件正确创建

        验证使用 SqliteSaver 后，
        data/chat.db 文件被正确创建。
        """
        # 获取数据库路径
        db_path = get_chat_database_path()

        # 如果文件存在，先删除以测试创建过程
        if os.path.exists(db_path):
            os.remove(db_path)

        # 创建检查点器并使用上下文管理器
        with create_chat_checkpointer() as checkpointer:
            # SqliteSaver 是延迟初始化的，文件不会立即创建
            # 需要执行一个操作来触发数据库创建
            config = {"configurable": {"thread_id": "test-init", "checkpoint_ns": ""}}
            checkpoint = {
                "v": 4,
                "id": "test-init-checkpoint",
                "ts": "2025-01-01T00:00:00.804150+00:00",
                "channel_values": {
                    "messages": []
                },
                "channel_versions": {
                    "__start__": 2
                },
                "versions_seen": {
                    "__input__": {},
                    "__start__": {
                        "__start__": 1
                    }
                }
            }

            # 执行操作会触发数据库文件创建
            checkpointer.put(config, checkpoint, {"source": "test-init"}, {})

        # 退出 with 语句后，验证数据库文件被创建
        assert os.path.exists(db_path), f"数据库文件应该被创建: {db_path}"
        assert os.path.getsize(db_path) > 0, "数据库文件应该有内容"

        # 验证文件是有效的SQLite数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查是否有LangGraph创建的表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        assert len(tables) > 0, "数据库应该包含LangGraph创建的表"

        conn.close()

    def test_database_path_resolution(self):
        """
        测试数据库路径解析

        验证 get_chat_database_path 返回正确的路径。
        """
        db_path = get_chat_database_path()

        # 验证路径包含 data/chat.db
        assert db_path.endswith("data/chat.db"), f"路径应该以 data/chat.db 结尾: {db_path}"

        # 验证路径是绝对路径
        assert os.path.isabs(db_path), f"路径应该是绝对路径: {db_path}"

        # 验证目录部分存在（或可以创建）
        db_dir = os.path.dirname(db_path)
        assert os.path.exists(db_dir) or os.access(os.path.dirname(db_dir), os.W_OK), \
            f"数据库目录应该存在或可创建: {db_dir}"

    def test_connection_health_check(self):
        """
        测试数据库连接健康检查

        验证 check_connection 函数能够正确检测数据库状态。
        """
        # 确保数据库文件存在
        checkpointer = create_chat_checkpointer()
        db_path = get_chat_database_path()

        # 测试正常连接
        assert check_connection(), "数据库连接应该正常"

        # 测试不存在的数据库
        fake_path = "/tmp/nonexistent_chat.db"
        with patch('src.domains.chat.database.get_chat_database_path', return_value=fake_path):
            assert not check_connection(), "不存在的数据库应该返回False"

        # 清理
        checkpointer = None

    def test_chat_db_manager_singleton(self):
        """
        测试数据库管理器单例行为

        验证 chat_db_manager 提供一致的实例。
        """
        manager1 = chat_db_manager
        manager2 = chat_db_manager

        assert manager1 is manager2, "chat_db_manager 应该是同一个实例"

        # 测试创建检查点器
        checkpointer1 = manager1.create_checkpointer()
        checkpointer2 = manager2.create_checkpointer()

        # 验证检查点器被正确创建（是上下文管理器）
        assert checkpointer1 is not None, "检查点器应该被创建"
        assert checkpointer2 is not None, "第二个检查点器也应该被创建"
        # 注意：由于是上下文管理器，每次创建都是新实例

    def test_persistence_across_restarts(self):
        """
        测试跨重启的数据持久化

        验证数据在重新创建检查点器后仍然存在。
        """
        db_path = get_chat_database_path()

        # 如果文件存在，先删除
        if os.path.exists(db_path):
            os.remove(db_path)

        # 使用正确的 LangGraph checkpoint 格式
        config = {"configurable": {"thread_id": "test-thread", "checkpoint_ns": ""}}
        checkpoint = {
            "v": 4,
            "id": "test-checkpoint",
            "ts": "2025-01-01T00:00:00.804150+00:00",
            "channel_values": {
                "messages": []
            },
            "channel_versions": {
                "__start__": 2
            },
            "versions_seen": {
                "__input__": {},
                "__start__": {
                    "__start__": 1
                }
            }
        }

        # 创建第一个检查点器并保存数据
        with create_chat_checkpointer() as checkpointer1:
            checkpointer1.put(config, checkpoint, {"source": "test"}, {})

        # 创建新的检查点器（模拟重启）
        with create_chat_checkpointer() as checkpointer2:
            # 验证数据仍然存在
            retrieved = checkpointer2.get(config)
            assert retrieved is not None, "重启后数据应该仍然存在"
            assert retrieved.checkpoint["id"] == "test-checkpoint", "数据内容应该正确"

    def test_database_manager_health_check(self):
        """
        测试数据库管理器健康检查

        验证 health_check 方法返回正确的状态信息。
        """
        # 确保数据库存在
        checkpointer = create_chat_checkpointer()

        # 执行健康检查
        health = chat_db_manager.health_check()

        # 验证健康检查结果
        assert isinstance(health, dict), "健康检查应该返回字典"
        assert "status" in health, "应该包含状态字段"
        assert "file_exists" in health, "应该包含文件存在状态"
        assert "connected" in health, "应该包含连接状态"
        assert "path" in health, "应该包含路径信息"

        # 验证状态值
        assert health["status"] in ["healthy", "unhealthy", "error"], "状态值应该有效"
        assert health["file_exists"] is True, "文件应该存在"
        assert health["connected"] is True, "应该能连接"
        assert health["path"] == get_chat_database_path(), "路径应该正确"

        # 清理
        checkpointer = None

    @pytest.fixture
    def temp_db_path(self):
        """
        临时数据库路径fixture

        为测试提供临时的数据库路径，避免污染实际数据。
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = os.path.join(temp_dir, "test_chat.db")
            with patch('src.domains.chat.database.get_chat_database_path', return_value=temp_db):
                yield temp_db

    def test_with_temporary_database(self, temp_db_path):
        """
        使用临时数据库测试

        验证在不同路径下数据库功能正常。
        """
        # 确保临时数据库不存在
        assert not os.path.exists(temp_db_path), "临时数据库不应该预先存在"

        # 创建检查点器并使用它
        with create_chat_checkpointer() as checkpointer:
            # 执行一个简单操作来触发数据库创建
            config = {"configurable": {"thread_id": "temp-test", "checkpoint_ns": ""}}
            checkpoint = {
                "v": 4,
                "id": "temp-checkpoint",
                "ts": "2025-01-01T00:00:00.804150+00:00",
                "channel_values": {
                    "messages": []
                },
                "channel_versions": {
                    "__start__": 2
                },
                "versions_seen": {
                    "__input__": {},
                    "__start__": {
                        "__start__": 1
                    }
                }
            }
            checkpointer.put(config, checkpoint, {"source": "temp-test"}, {})

        # 验证文件被创建
        assert os.path.exists(temp_db_path), "临时数据库应该被创建"

    def test_error_handling_invalid_path(self):
        """
        测试错误处理：无效路径

        验证在无效路径下的错误处理。
        """
        # 模拟无效路径（无权限目录）
        invalid_path = "/root/invalid_chat.db"

        with patch('src.domains.chat.database.get_chat_database_path', return_value=invalid_path):
            # 应该抛出异常或返回错误
            with pytest.raises(Exception):
                create_chat_checkpointer()


class TestDatabasePerformance:
    """
    数据库性能测试

    测试数据库操作的性能表现。
    """

    def test_multiple_checkpoints_performance(self):
        """
        测试多个检查点的性能

        验证保存和检索多个检查点的性能。
        """
        import time

        # 测试保存多个检查点的时间
        start_time = time.time()

        with create_chat_checkpointer() as checkpointer:
            for i in range(10):
                config = {"configurable": {"thread_id": f"perf-test-{i}", "checkpoint_ns": ""}}
                checkpoint = {
                    "v": 4,
                    "id": f"perf-checkpoint-{i}",
                    "ts": "2025-01-01T00:00:00.804150+00:00",
                    "channel_values": {
                        "messages": []
                    },
                    "channel_versions": {
                        "__start__": 2
                    },
                    "versions_seen": {
                        "__input__": {},
                        "__start__": {
                            "__start__": 1
                        }
                    }
                }
                checkpointer.put(config, checkpoint, {"source": "perf-test"}, {})

        save_time = time.time() - start_time

        # 测试检索时间
        start_time = time.time()

        with create_chat_checkpointer() as checkpointer:
            for i in range(10):
                config = {"configurable": {"thread_id": f"perf-test-{i}", "checkpoint_ns": ""}}
                retrieved = checkpointer.get(config)
                assert retrieved is not None, f"检查点 {i} 应该能被检索"

        retrieve_time = time.time() - start_time

        # 性能断言（这些数值可能需要根据实际情况调整）
        assert save_time < 5.0, f"保存10个检查点应该少于5秒，实际: {save_time:.2f}秒"
        assert retrieve_time < 1.0, f"检索10个检查点应该少于1秒，实际: {retrieve_time:.2f}秒"


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])