"""
数据库初始化测试

专门测试聊天数据库的初始化过程，确保所有必要的表结构都被正确创建。
这个测试用于捕获 "no such table: checkpoints" 类型的错误。

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import os
import tempfile
import sqlite3
from pathlib import Path

from src.domains.chat.service import ChatService
from src.domains.chat.database import get_chat_database_path, create_chat_checkpointer


class TestDatabaseInitialization:
    """数据库初始化测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def chat_service_with_temp_db(self, temp_db_path):
        """使用临时数据库的聊天服务"""
        # 临时修改环境变量指向测试数据库
        original_db_path = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            service = ChatService()
            yield service
        finally:
            # 恢复原始环境变量
            if original_db_path:
                os.environ['CHAT_DB_PATH'] = original_db_path
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_database_table_creation_on_first_use(self, temp_db_path):
        """测试数据库表在首次使用时被创建"""
        # 确保数据库文件不存在
        assert not os.path.exists(temp_db_path), "测试数据库文件不应存在"

        # 创建checkpointer会创建数据库文件，但不会立即创建表
        checkpointer = create_chat_checkpointer()

        # 数据库文件应该已创建
        assert os.path.exists(temp_db_path), "数据库文件应该被创建"

        # 但此时表还不存在
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'")
            result = cursor.fetchone()
            assert result is None, "checkpoints表还不应该存在"
        finally:
            conn.close()

        # 使用checkpointer应该会创建表
        with checkpointer:
            # 尝试访问不存在的thread_id来触发表创建
            try:
                list(checkpointer.list({"thread_id": "__init__"}))
            except Exception:
                pass  # 预期失败，但会触发表创建

        # 现在表应该存在
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'")
            result = cursor.fetchone()
            assert result is not None, "checkpoints表应该存在"
            assert result[0] == 'checkpoints', "表名应该是checkpoints"

            # 检查表结构
            cursor.execute("PRAGMA table_info(checkpoints)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            expected_columns = ['thread_id', 'checkpoint_ns', 'checkpoint_id', 'type', 'checkpoint', 'metadata']
            for expected_col in expected_columns:
                assert expected_col in column_names, f"checkpoints表应该包含{expected_col}列"

        finally:
            conn.close()

    def test_ensure_database_initialized_method(self, chat_service_with_temp_db):
        """测试_ensure_database_initialized方法正确初始化数据库"""
        temp_db_path = get_chat_database_path()

        # 确保数据库文件不存在
        assert not os.path.exists(temp_db_path), "测试数据库文件不应存在"

        # 调用_ensure_database_initialized
        chat_service_with_temp_db._ensure_database_initialized()

        # 现在数据库文件和表都应该存在
        assert os.path.exists(temp_db_path), "数据库文件应该被创建"

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoints'")
            result = cursor.fetchone()
            assert result is not None, "checkpoints表应该存在"
            assert result[0] == 'checkpoints', "表名应该是checkpoints"
        finally:
            conn.close()

    def test_create_session_after_database_initialization(self, chat_service_with_temp_db):
        """测试数据库初始化后创建会话成功"""
        user_id = "test-user"
        title = "测试会话"

        # 确保数据库已初始化
        chat_service_with_temp_db._ensure_database_initialized()

        # 现在创建会话应该成功
        result = chat_service_with_temp_db.create_session(user_id, title)

        assert result is not None, "创建会话应该成功"
        assert result["title"] == title, "会话标题应该正确"
        assert result["session_id"] is not None, "应该有session_id"
        assert "created_at" in result, "应该有created_at"

    def test_create_session_without_initialization_fails(self, chat_service_with_temp_db):
        """测试未初始化数据库时创建会话失败"""
        user_id = "test-user"
        title = "测试会话"

        # 不调用_ensure_database_initialized，直接创建会话
        with pytest.raises(Exception) as exc_info:
            chat_service_with_temp_db.create_session(user_id, title)

        assert "no such table: checkpoints" in str(exc_info.value), "应该报告checkpoints表不存在"
        assert "创建会话记录失败" in str(exc_info.value), "应该包含具体的错误信息"

    def test_multiple_service_instances_share_database(self, temp_db_path):
        """测试多个服务实例共享同一个数据库"""
        # 创建第一个服务实例并初始化数据库
        service1 = ChatService()
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            service1._ensure_database_initialized()

            # 创建第二个服务实例
            service2 = ChatService()

            # 第二个服务应该能够正常使用数据库
            user_id = "test-user"
            title = "测试会话"

            result1 = service1.create_session(user_id + "1", title + "1")
            result2 = service2.create_session(user_id + "2", title + "2")

            assert result1 is not None, "第一个服务创建会话应该成功"
            assert result2 is not None, "第二个服务创建会话应该成功"
            assert result1["session_id"] != result2["session_id"], "会话ID应该不同"

        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])