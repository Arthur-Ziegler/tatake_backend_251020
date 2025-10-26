"""
ChatDatabaseManager单元测试

严格TDD方法：
1. 异步数据库操作测试
2. 事务安全测试
3. 数据完整性测试
4. 性能测试
5. 错误处理测试

作者：TaKeKe团队
版本：1.0.0 - 数据库单元测试
"""

import pytest
import asyncio
import tempfile
import os
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from src.domains.chat.simple_database import ChatDatabaseManager
from src.domains.chat.simple_state import MessageMetadata, SessionInfo


@pytest.mark.unit
class TestChatDatabaseManager:
    """ChatDatabaseManager单元测试类"""

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
    def db_manager(self, temp_db_path):
        """创建ChatDatabaseManager实例"""
        return ChatDatabaseManager(temp_db_path)

    @pytest.fixture
    def sample_user_id(self):
        """提供测试用户ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_session_id(self):
        """提供测试会话ID"""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_init_success(self, temp_db_path):
        """测试成功初始化"""
        manager = ChatDatabaseManager(temp_db_path)

        assert manager._db_path == temp_db_path

        # 触发数据库初始化（懒加载模式）
        await manager._ensure_initialized()

        # 验证数据库表是否创建
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # 检查sessions表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        assert cursor.fetchone() is not None

        # 检查messages表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        assert cursor.fetchone() is not None

        conn.close()

    def test_init_with_default_path(self):
        """测试使用默认路径初始化"""
        manager = ChatDatabaseManager()

        assert manager._db_path == "data/chat_simple.db"

    def test_init_directory_creation(self):
        """测试数据目录自动创建"""
        deep_path = "data/subdir/deep/test.db"
        manager = ChatDatabaseManager(deep_path)

        # 验证目录被创建
        assert os.path.exists("data/subdir/deep")

        # 清理
        if os.path.exists(deep_path):
            os.remove(deep_path)
        if os.path.exists("data/subdir/deep"):
            os.rmdir("data/subdir/deep")
        if os.path.exists("data/subdir"):
            os.rmdir("data/subdir")

    @pytest.mark.asyncio
    async def test_save_message_success(self, db_manager, sample_session_id):
        """测试保存消息成功"""
        message_id = await db_manager.save_message(
            sample_session_id,
            "user",
            "测试消息内容"
        )

        assert message_id is not None
        assert isinstance(message_id, str)

        # 验证消息确实被保存
        conn = sqlite3.connect(db_manager._db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT message_id, session_id, role, content FROM messages WHERE message_id = ?",
            (message_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == message_id
        assert row[1] == sample_session_id
        assert row[2] == "user"
        assert row[3] == "测试消息内容"

    @pytest.mark.asyncio
    async def test_save_message_auto_session_creation(self, db_manager, sample_session_id, sample_user_id):
        """测试保存消息时自动创建会话"""
        message_id = await db_manager.save_message(
            sample_session_id,
            "user",
            "测试消息"
        )

        # 验证会话被自动创建
        session_info = await db_manager.get_session_info(sample_session_id)
        assert session_info is not None
        assert session_info["session_id"] == sample_session_id

    @pytest.mark.asyncio
    async def test_save_message_validation(self, db_manager):
        """测试保存消息参数验证"""
        # 测试空会话ID
        with pytest.raises(ValueError) as exc_info:
            await db_manager.save_message("", "user", "消息")
        assert "会话ID不能为空" in str(exc_info.value)

        # 测试空角色
        with pytest.raises(ValueError) as exc_info:
            await db_manager.save_message("session123", "", "消息")
        assert "角色不能为空" in str(exc_info.value)

        # 测试空内容
        with pytest.raises(ValueError) as exc_info:
            await db_manager.save_message("session123", "user", "")
        assert "消息内容不能为空" in str(exc_info.value)

        # 测试无效角色
        with pytest.raises(ValueError) as exc_info:
            await db_manager.save_message("session123", "invalid_role", "消息")
        assert "角色必须是user或assistant" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_recent_messages_success(self, db_manager, sample_session_id):
        """测试获取最近消息成功"""
        # 先保存一些消息
        messages = [
            ("user", "第一个消息"),
            ("assistant", "第一个回复"),
            ("user", "第二个消息"),
            ("assistant", "第二个回复")
        ]

        for role, content in messages:
            await db_manager.save_message(sample_session_id, role, content)

        # 获取消息
        retrieved_messages = await db_manager.get_recent_messages(sample_session_id, limit=10)

        assert len(retrieved_messages) == 4
        assert retrieved_messages[0]["role"] == "user"
        assert retrieved_messages[0]["content"] == "第一个消息"
        assert retrieved_messages[1]["role"] == "assistant"
        assert retrieved_messages[1]["content"] == "第一个回复"

    @pytest.mark.asyncio
    async def test_get_recent_messages_with_limit(self, db_manager, sample_session_id):
        """测试带限制的消息获取"""
        # 保存5条消息
        for i in range(5):
            await db_manager.save_message(sample_session_id, "user", f"消息{i}")

        # 只获取前3条
        messages = await db_manager.get_recent_messages(sample_session_id, limit=3)

        assert len(messages) == 3

    @pytest.mark.asyncio
    async def test_get_recent_messages_empty_session(self, db_manager):
        """测试获取空会话消息"""
        messages = await db_manager.get_recent_messages("nonexistent_session")
        assert messages == []

    @pytest.mark.asyncio
    async def test_get_recent_messages_validation(self, db_manager):
        """测试获取消息参数验证"""
        # 测试空会话ID
        with pytest.raises(ValueError) as exc_info:
            await db_manager.get_recent_messages("")
        assert "会话ID不能为空" in str(exc_info.value)

        # 测试负数limit（应该被重置为默认值）
        messages = await db_manager.get_recent_messages("session123", limit=-1)
        # 应该使用默认值10，但因为是空会话，返回空列表
        assert messages == []

    @pytest.mark.asyncio
    async def test_create_session_success(self, db_manager, sample_session_id, sample_user_id):
        """测试创建会话成功"""
        session_info = await db_manager.create_session(
            sample_session_id,
            sample_user_id,
            "测试会话"
        )

        assert session_info["session_id"] == sample_session_id
        assert session_info["user_id"] == sample_user_id
        assert session_info["title"] == "测试会话"
        assert "created_at" in session_info
        assert "last_message_at" in session_info

    @pytest.mark.asyncio
    async def test_create_session_validation(self, db_manager):
        """测试创建会话参数验证"""
        # 测试空会话ID
        with pytest.raises(ValueError) as exc_info:
            await db_manager.create_session("", "user123")
        assert "会话ID和用户ID不能为空" in str(exc_info.value)

        # 测试空用户ID
        with pytest.raises(ValueError) as exc_info:
            await db_manager.create_session("session123", "")
        assert "会话ID和用户ID不能为空" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_session_info_success(self, db_manager, sample_session_id, sample_user_id):
        """测试获取会话信息成功"""
        # 先创建会话
        await db_manager.create_session(sample_session_id, sample_user_id, "测试会话")

        # 获取会话信息
        session_info = await db_manager.get_session_info(sample_session_id)

        assert session_info is not None
        assert session_info["session_id"] == sample_session_id
        assert session_info["user_id"] == sample_user_id
        assert session_info["title"] == "测试会话"

    @pytest.mark.asyncio
    async def test_get_session_info_nonexistent(self, db_manager):
        """测试获取不存在的会话信息"""
        session_info = await db_manager.get_session_info("nonexistent_session")
        assert session_info is None

    @pytest.mark.asyncio
    async def test_clear_session_messages_success(self, db_manager, sample_session_id):
        """测试清除会话消息成功"""
        # 先保存一些消息
        await db_manager.save_message(sample_session_id, "user", "消息1")
        await db_manager.save_message(sample_session_id, "assistant", "回复1")

        # 清除消息
        success = await db_manager.clear_session_messages(sample_session_id)
        assert success is True

        # 验证消息被清除
        messages = await db_manager.get_recent_messages(sample_session_id)
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_clear_session_messages_validation(self, db_manager):
        """测试清除会话消息参数验证"""
        with pytest.raises(ValueError) as exc_info:
            await db_manager.clear_session_messages("")
        assert "会话ID不能为空" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_session_stats_success(self, db_manager, sample_session_id, sample_user_id):
        """测试获取会话统计成功"""
        # 创建会话并保存消息
        await db_manager.create_session(sample_session_id, sample_user_id)
        await db_manager.save_message(sample_session_id, "user", "消息1")
        await db_manager.save_message(sample_session_id, "assistant", "回复1")

        # 获取统计
        stats = await db_manager.get_session_stats(sample_session_id)

        assert stats["message_count"] == 2
        assert stats["created_at"] is not None
        assert stats["last_message_at"] is not None

    @pytest.mark.asyncio
    async def test_get_session_stats_nonexistent(self, db_manager):
        """测试获取不存在会话的统计"""
        stats = await db_manager.get_session_stats("nonexistent_session")
        assert stats["message_count"] == 0
        assert stats["created_at"] is None
        assert stats["last_message_at"] is None

    @pytest.mark.asyncio
    async def test_list_user_sessions_success(self, db_manager, sample_user_id):
        """测试获取用户会话列表成功"""
        # 创建多个会话
        session1 = str(uuid4())
        session2 = str(uuid4())
        session3 = str(uuid4())

        await db_manager.create_session(session1, sample_user_id, "会话1")
        await db_manager.create_session(session2, sample_user_id, "会话2")
        await db_manager.create_session(session3, "other_user", "其他会话")

        # 获取用户的会话列表
        sessions = await db_manager.list_user_sessions(sample_user_id)

        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert session1 in session_ids
        assert session2 in session_ids
        assert session3 not in session_ids

    @pytest.mark.asyncio
    async def test_list_user_sessions_with_pagination(self, db_manager, sample_user_id):
        """测试分页获取用户会话列表"""
        # 创建多个会话
        for i in range(5):
            session_id = str(uuid4())
            await db_manager.create_session(session_id, sample_user_id, f"会话{i}")

        # 分页获取
        sessions_page1 = await db_manager.list_user_sessions(sample_user_id, limit=2, offset=0)
        sessions_page2 = await db_manager.list_user_sessions(sample_user_id, limit=2, offset=2)

        assert len(sessions_page1) == 2
        assert len(sessions_page2) == 2

        # 确保没有重复
        page1_ids = {s["session_id"] for s in sessions_page1}
        page2_ids = {s["session_id"] for s in sessions_page2}
        assert len(page1_ids.intersection(page2_ids)) == 0

    @pytest.mark.asyncio
    async def test_list_user_sessions_validation(self, db_manager):
        """测试获取用户会话列表参数验证"""
        with pytest.raises(ValueError) as exc_info:
            await db_manager.list_user_sessions("")
        assert "用户ID不能为空" in str(exc_info.value)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_bulk_message_operations(self, db_manager, sample_session_id):
        """测试批量消息操作性能"""
        import time

        # 测试保存大量消息的性能
        start_time = time.time()
        message_count = 100

        for i in range(message_count):
            await db_manager.save_message(sample_session_id, "user", f"消息{i}")

        save_time = time.time() - start_time
        assert save_time < 2.0, f"保存{message_count}条消息性能不达标，耗时: {save_time:.3f}秒"

        # 测试获取消息的性能
        start_time = time.time()
        messages = await db_manager.get_recent_messages(sample_session_id, limit=50)
        get_time = time.time() - start_time

        assert get_time < 0.1, f"获取消息性能不达标，耗时: {get_time:.3f}秒"
        assert len(messages) == 50

    @pytest.mark.concurrency
    @pytest.mark.asyncio
    async def test_concurrent_message_operations(self, db_manager, sample_session_id):
        """测试并发消息操作"""
        async def save_messages(start_index: int, count: int):
            for i in range(count):
                await db_manager.save_message(
                    sample_session_id,
                    "user",
                    f"并发消息{start_index + i}"
                )

        # 并发保存消息
        tasks = [
            save_messages(0, 10),
            save_messages(10, 10),
            save_messages(20, 10)
        ]

        await asyncio.gather(*tasks)

        # 验证所有消息都被保存
        messages = await db_manager.get_recent_messages(sample_session_id, limit=100)
        assert len(messages) == 30

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_integration_full_workflow(self, db_manager, sample_user_id):
        """集成测试：完整工作流"""
        # 1. 创建会话
        session_id = str(uuid4())
        session_info = await db_manager.create_session(session_id, sample_user_id, "集成测试会话")
        assert session_info["session_id"] == session_id

        # 2. 保存消息
        await db_manager.save_message(session_id, "user", "你好")
        await db_manager.save_message(session_id, "assistant", "你好！有什么可以帮助你的吗？")
        await db_manager.save_message(session_id, "user", "我想了解一下你的功能")

        # 3. 获取消息历史
        messages = await db_manager.get_recent_messages(session_id)
        assert len(messages) == 3

        # 4. 获取会话统计
        stats = await db_manager.get_session_stats(session_id)
        assert stats["message_count"] == 3

        # 5. 获取会话信息
        info = await db_manager.get_session_info(session_id)
        assert info["title"] == "集成测试会话"

        # 6. 列出用户会话
        user_sessions = await db_manager.list_user_sessions(sample_user_id)
        assert len(user_sessions) == 1
        assert user_sessions[0]["session_id"] == session_id

        # 7. 清除会话消息
        success = await db_manager.clear_session_messages(session_id)
        assert success is True

        # 8. 验证消息被清除
        messages_after_clear = await db_manager.get_recent_messages(session_id)
        assert len(messages_after_clear) == 0

        # 9. 验证会话仍然存在
        info_after_clear = await db_manager.get_session_info(session_id)
        assert info_after_clear is not None


@pytest.mark.regression
class TestChatDatabaseManagerRegression:
    """ChatDatabaseManager回归测试"""

    @pytest.mark.asyncio
    async def test_regression_message_timestamp_ordering(self, temp_db_path):
        """回归测试：消息时间戳排序"""
        manager = ChatDatabaseManager(temp_db_path)
        session_id = str(uuid4())

        # 确保数据库初始化
        await manager._ensure_initialized()

        # 快速连续保存消息
        timestamps = []
        for i in range(3):
            await manager.save_message(session_id, "user", f"消息{i}")
            timestamps.append(datetime.now(timezone.utc))
            await asyncio.sleep(0.01)  # 确保时间戳不同

        # 获取消息并验证顺序
        messages = await manager.get_recent_messages(session_id)
        assert len(messages) == 3

        # 验证消息按时间戳升序排列
        for i in range(1, len(messages)):
            assert messages[i]["timestamp"] >= messages[i-1]["timestamp"]

    @pytest.mark.asyncio
    async def test_regression_session_last_message_update(self, temp_db_path):
        """回归测试：会话最后消息时间更新"""
        manager = ChatDatabaseManager(temp_db_path)
        session_id = str(uuid4())
        user_id = str(uuid4())

        # 确保数据库初始化
        await manager._ensure_initialized()

        # 创建会话
        await manager.create_session(session_id, user_id)
        initial_stats = await manager.get_session_stats(session_id)
        initial_time = initial_stats["last_message_at"]

        # 等待一小段时间确保时间戳不同
        await asyncio.sleep(0.01)

        # 保存消息
        await manager.save_message(session_id, "user", "测试消息")

        # 验证最后消息时间被更新
        updated_stats = await manager.get_session_stats(session_id)
        updated_time = updated_stats["last_message_at"]

        assert updated_time > initial_time

    @pytest.mark.asyncio
    async def test_regression_database_schema_compatibility(self, temp_db_path):
        """回归测试：数据库模式兼容性"""
        manager = ChatDatabaseManager(temp_db_path)

        # 确保数据库初始化
        await manager._ensure_initialized()

        # 验证所有必需的表和索引存在
        conn = sqlite3.connect(manager._db_path)
        cursor = conn.cursor()

        # 检查表结构
        cursor.execute("PRAGMA table_info(sessions)")
        session_columns = [row[1] for row in cursor.fetchall()]
        required_session_columns = ["session_id", "user_id", "title", "created_at", "last_message_at"]
        for col in required_session_columns:
            assert col in session_columns, f"缺少sessions表列: {col}"

        cursor.execute("PRAGMA table_info(messages)")
        message_columns = [row[1] for row in cursor.fetchall()]
        required_message_columns = ["message_id", "session_id", "role", "content", "timestamp"]
        for col in required_message_columns:
            assert col in message_columns, f"缺少messages表列: {col}"

        # 检查索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_messages_session_timestamp'")
        message_index = cursor.fetchone()
        assert message_index is not None, "缺少消息时间戳索引"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_sessions_user_created'")
        session_index = cursor.fetchone()
        assert session_index is not None, "缺少会话用户创建时间索引"

        conn.close()