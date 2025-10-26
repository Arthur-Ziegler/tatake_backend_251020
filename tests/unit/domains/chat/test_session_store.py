"""
SessionStore模块单元测试

测试会话元数据存储的完整功能，包括：
1. 会话创建、查询、更新、删除
2. ThreadId关联管理
3. 数据库事务和一致性
4. 错误处理和边界情况

作者：TaKeKe团队
版本：1.0.0 - 彻底分离方案实现
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domains.chat.session_store import ChatSessionStore


@pytest.mark.unit
class TestChatSessionStore:
    """ChatSessionStore测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """提供临时数据库路径"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def session_store(self, temp_db_path):
        """创建SessionStore实例"""
        return ChatSessionStore(temp_db_path)

    @pytest.fixture
    def sample_user_id(self):
        """提供测试用户ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_session_id(self):
        """提供测试会话ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_thread_id(self):
        """提供测试thread_id"""
        return str(uuid4())

    def test_database_initialization(self, temp_db_path):
        """测试数据库初始化"""
        # 创建SessionStore会自动初始化数据库
        store = ChatSessionStore(temp_db_path)

        # 验证表是否创建成功
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()

            # 检查chat_sessions表
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_sessions'"
            )
            result = cursor.fetchone()
            assert result is not None, "chat_sessions表应该被创建"

            # 检查表结构
            cursor.execute("PRAGMA table_info(chat_sessions)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            expected_columns = [
                'session_id', 'user_id', 'title', 'created_at',
                'updated_at', 'message_count', 'is_active', 'metadata', 'thread_id'
            ]
            for col in expected_columns:
                assert col in column_names, f"列 {col} 应该存在"

    def test_create_session_basic(self, session_store, sample_user_id):
        """测试基本会话创建"""
        title = "测试会话"

        # 创建会话
        session_info = session_store.create_session(sample_user_id, title)

        # 验证返回数据
        assert session_info["session_id"] is not None
        assert session_info["user_id"] == sample_user_id
        assert session_info["title"] == title
        assert session_info["thread_id"] is not None
        assert session_info["created_at"] is not None
        assert session_info["updated_at"] is not None
        assert session_info["message_count"] == 0
        assert session_info["is_active"] == 1  # SQLite返回整数

        # 验证session_id和thread_id是UUID格式
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        assert uuid_pattern.match(session_info["session_id"])
        assert uuid_pattern.match(session_info["thread_id"])

    def test_create_session_with_default_title(self, session_store, sample_user_id):
        """测试使用默认标题创建会话"""
        session_info = session_store.create_session(sample_user_id)

        assert session_info["title"] == "新会话"

    def test_get_session_existing(self, session_store, sample_user_id):
        """测试获取存在的会话"""
        # 先创建会话
        created_session = session_store.create_session(sample_user_id, "测试会话")
        session_id = created_session["session_id"]

        # 获取会话
        retrieved_session = session_store.get_session(session_id)

        # 验证数据一致性
        assert retrieved_session is not None
        assert retrieved_session["session_id"] == session_id
        assert retrieved_session["user_id"] == sample_user_id
        assert retrieved_session["title"] == "测试会话"

    def test_get_session_nonexistent(self, session_store):
        """测试获取不存在的会话"""
        fake_session_id = str(uuid4())
        result = session_store.get_session(fake_session_id)
        assert result is None

    def test_get_session_by_thread_id(self, session_store, sample_user_id):
        """测试通过thread_id获取会话"""
        # 先创建会话
        created_session = session_store.create_session(sample_user_id, "测试会话")
        thread_id = created_session["thread_id"]

        # 通过thread_id获取会话
        retrieved_session = session_store.get_session_by_thread_id(thread_id)

        # 验证数据一致性
        assert retrieved_session is not None
        assert retrieved_session["thread_id"] == thread_id
        assert retrieved_session["session_id"] == created_session["session_id"]

    def test_get_session_by_nonexistent_thread_id(self, session_store):
        """测试通过不存在的thread_id获取会话"""
        fake_thread_id = str(uuid4())
        result = session_store.get_session_by_thread_id(fake_thread_id)
        assert result is None

    def test_update_session_title(self, session_store, sample_user_id):
        """测试更新会话标题"""
        # 创建会话
        created_session = session_store.create_session(sample_user_id, "原标题")
        session_id = created_session["session_id"]

        # 更新标题
        new_title = "更新后的标题"
        success = session_store.update_session(session_id, title=new_title)
        assert success is True

        # 验证更新
        updated_session = session_store.get_session(session_id)
        assert updated_session["title"] == new_title

        # 验证updated_at字段被更新
        original_updated_at = datetime.fromisoformat(created_session["updated_at"])
        new_updated_at = datetime.fromisoformat(updated_session["updated_at"])
        assert new_updated_at > original_updated_at

    def test_update_nonexistent_session(self, session_store):
        """测试更新不存在的会话"""
        fake_session_id = str(uuid4())
        success = session_store.update_session(fake_session_id, title="新标题")
        assert success is False

    def test_increment_message_count(self, session_store, sample_user_id):
        """测试增加消息计数"""
        # 创建会话
        created_session = session_store.create_session(sample_user_id, "测试会话")
        session_id = created_session["session_id"]
        original_count = created_session["message_count"]

        # 增加消息计数
        success = session_store.increment_message_count(session_id)
        assert success is True

        # 验证计数增加
        updated_session = session_store.get_session(session_id)
        assert updated_session["message_count"] == original_count + 1

    def test_increment_message_count_multiple_times(self, session_store, sample_user_id):
        """测试多次增加消息计数"""
        # 创建会话
        created_session = session_store.create_session(sample_user_id, "测试会话")
        session_id = created_session["session_id"]

        # 多次增加消息计数
        for i in range(5):
            session_store.increment_message_count(session_id)

        # 验证最终计数
        updated_session = session_store.get_session(session_id)
        assert updated_session["message_count"] == 5

    def test_increment_message_count_nonexistent_session(self, session_store):
        """测试为不存在的会话增加消息计数"""
        fake_session_id = str(uuid4())
        success = session_store.increment_message_count(fake_session_id)
        assert success is False

    def test_list_user_sessions_empty(self, session_store, sample_user_id):
        """测试列出用户的空会话列表"""
        sessions = session_store.list_user_sessions(sample_user_id)
        assert sessions == []

    def test_list_user_sessions_with_data(self, session_store, sample_user_id):
        """测试列出用户的会话"""
        # 创建多个会话
        session1 = session_store.create_session(sample_user_id, "会话1")
        session2 = session_store.create_session(sample_user_id, "会话2")

        # 获取会话列表
        sessions = session_store.list_user_sessions(sample_user_id)

        # 验证结果
        assert len(sessions) == 2

        # 验证按updated_at降序排列
        assert sessions[0]["updated_at"] >= sessions[1]["updated_at"]

        # 验证内容正确性
        session_ids = [s["session_id"] for s in sessions]
        assert session1["session_id"] in session_ids
        assert session2["session_id"] in session_ids

    def test_list_user_sessions_with_limit(self, session_store, sample_user_id):
        """测试带限制的会话列表查询"""
        # 创建多个会话
        for i in range(5):
            session_store.create_session(sample_user_id, f"会话{i+1}")

        # 限制数量查询
        sessions = session_store.list_user_sessions(sample_user_id, limit=3)
        assert len(sessions) == 3

    def test_list_user_sessions_other_user(self, session_store, sample_user_id):
        """测试列出其他用户的会话（应该为空）"""
        other_user_id = str(uuid4())

        # 为sample_user_id创建会话
        session_store.create_session(sample_user_id, "我的会话")

        # 用其他用户ID查询
        sessions = session_store.list_user_sessions(other_user_id)
        assert sessions == []

    def test_delete_session_soft(self, session_store, sample_user_id):
        """测试软删除会话"""
        # 创建会话
        created_session = session_store.create_session(sample_user_id, "测试会话")
        session_id = created_session["session_id"]

        # 软删除会话
        success = session_store.delete_session(session_id)
        assert success is True

        # 验证会话被标记为非活跃
        deleted_session = session_store.get_session(session_id)
        assert deleted_session["is_active"] == 0  # SQLite中False为0

        # 验证在活跃会话列表中不再出现
        active_sessions = session_store.list_user_sessions(sample_user_id)
        session_ids = [s["session_id"] for s in active_sessions]
        assert session_id not in session_ids

    def test_delete_nonexistent_session(self, session_store):
        """测试删除不存在的会话"""
        fake_session_id = str(uuid4())
        success = session_store.delete_session(fake_session_id)
        assert success is False

    def test_get_thread_id_direct(self, session_store, sample_user_id):
        """测试直接获取thread_id"""
        # 创建会话
        created_session = session_store.create_session(sample_user_id, "测试会话")
        session_id = created_session["session_id"]
        expected_thread_id = created_session["thread_id"]

        # 获取thread_id
        thread_id = session_store.get_thread_id(session_id)
        assert thread_id == expected_thread_id

    def test_get_thread_id_nonexistent_session(self, session_store):
        """测试获取不存在会话的thread_id"""
        fake_session_id = str(uuid4())
        thread_id = session_store.get_thread_id(fake_session_id)
        assert thread_id is None

    def test_session_data_integrity(self, session_store, sample_user_id):
        """测试会话数据完整性"""
        import json

        # 创建会话
        session_info = session_store.create_session(sample_user_id, "完整性测试")

        # 从数据库直接读取验证
        with session_store.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ?",
                (session_info["session_id"],)
            )
            row = cursor.fetchone()

            assert row is not None
            assert dict(row)["session_id"] == session_info["session_id"]
            assert dict(row)["user_id"] == sample_user_id
            assert dict(row)["title"] == "完整性测试"

    def test_concurrent_session_creation(self, session_store, sample_user_id):
        """测试并发会话创建"""
        import threading
        import time

        results = []
        errors = []

        def create_session_worker():
            try:
                session = session_store.create_session(sample_user_id, f"并发会话-{threading.current_thread().ident}")
                results.append(session)
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_session_worker)
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发创建出现错误: {errors}"
        assert len(results) == 5, f"应该创建5个会话，实际创建{len(results)}个"

        # 验证所有session_id都是唯一的
        session_ids = [r["session_id"] for r in results]
        assert len(set(session_ids)) == len(session_ids), "session_id应该是唯一的"

    @pytest.mark.integration
    def test_end_to_end_workflow(self, session_store, sample_user_id):
        """测试端到端工作流程"""
        # 1. 创建会话
        session = session_store.create_session(sample_user_id, "端到端测试")
        session_id = session["session_id"]
        thread_id = session["thread_id"]

        # 2. 验证会话存在
        assert session_store.get_session(session_id) is not None
        assert session_store.get_session_by_thread_id(thread_id) is not None

        # 3. 模拟消息发送（增加计数）
        for i in range(3):
            session_store.increment_message_count(session_id)

        # 4. 更新会话标题
        session_store.update_session(session_id, title="更新后的标题")

        # 5. 验证最终状态
        final_session = session_store.get_session(session_id)
        assert final_session["message_count"] == 3
        assert final_session["title"] == "更新后的标题"
        assert final_session["is_active"] == 1  # SQLite中True为1

        # 6. 验证在用户会话列表中
        user_sessions = session_store.list_user_sessions(sample_user_id)
        assert len(user_sessions) == 1
        assert user_sessions[0]["session_id"] == session_id

        # 7. 软删除会话
        session_store.delete_session(session_id)

        # 8. 验证删除后的状态
        deleted_session = session_store.get_session(session_id)
        assert deleted_session["is_active"] == 0  # SQLite中False为0

        active_sessions = session_store.list_user_sessions(sample_user_id)
        assert len(active_sessions) == 0


@pytest.mark.integration
class TestSessionStoreIntegration:
    """SessionStore集成测试"""

    def test_with_real_database_operations(self):
        """测试真实数据库操作"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            store = ChatSessionStore(db_path)
            user_id = str(uuid4())

            # 执行一系列操作
            session1 = store.create_session(user_id, "会话1")
            session2 = store.create_session(user_id, "会话2")

            # 增加消息计数
            store.increment_message_count(session1["session_id"])
            store.increment_message_count(session1["session_id"])
            store.increment_message_count(session2["session_id"])

            # 更新标题
            store.update_session(session1["session_id"], title="更新后的会话1")

            # 验证最终状态
            final_session1 = store.get_session(session1["session_id"])
            final_session2 = store.get_session(session2["session_id"])

            assert final_session1["message_count"] == 2
            assert final_session1["title"] == "更新后的会话1"
            assert final_session2["message_count"] == 1

            # 验证会话列表
            sessions = store.list_user_sessions(user_id)
            assert len(sessions) == 2

        finally:
            # 清理
            if os.path.exists(db_path):
                os.unlink(db_path)