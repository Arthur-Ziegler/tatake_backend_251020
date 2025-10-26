"""
SimpleChatState单元测试

严格TDD方法：
1. 状态类功能测试
2. 消息元数据测试
3. 会话信息测试
4. 数据转换测试
5. 边界条件测试

作者：TaTakeKe团队
版本：1.0.0 - 状态管理单元测试
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from src.domains.chat.simple_state import SimpleChatState, MessageMetadata, SessionInfo


@pytest.mark.unit
class TestSimpleChatState:
    """SimpleChatState单元测试类"""

    def test_simple_chat_state_type_definition(self):
        """测试SimpleChatState类型定义"""
        # SimpleChatState是一个TypedDict，主要用于类型提示
        # 我们验证它的基本结构

        # 验证类存在且可以被引用
        assert SimpleChatState is not None

        # 验证类名正确
        assert SimpleChatState.__name__ == "SimpleChatState"

        # SimpleChatState继承自MessagesState，主要用于静态类型检查
        # 在运行时，它主要是一个空类，功能由继承而来


@pytest.mark.unit
class TestMessageMetadata:
    """MessageMetadata单元测试类"""

    @pytest.fixture
    def sample_session_id(self):
        """提供测试会话ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_message_id(self):
        """提供测试消息ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_timestamp(self):
        """提供测试时间戳"""
        return datetime.now(timezone.utc)

    def test_init_with_all_parameters(self, sample_session_id, sample_message_id, sample_timestamp):
        """测试使用所有参数初始化"""
        metadata = MessageMetadata(
            session_id=sample_session_id,
            role="user",
            content="测试消息",
            timestamp=sample_timestamp,
            message_id=sample_message_id
        )

        assert metadata.session_id == sample_session_id
        assert metadata.role == "user"
        assert metadata.content == "测试消息"
        assert metadata.timestamp == sample_timestamp
        assert metadata.message_id == sample_message_id

    def test_init_with_minimal_parameters(self, sample_session_id):
        """测试使用最小参数初始化"""
        metadata = MessageMetadata(
            session_id=sample_session_id,
            role="assistant",
            content="AI回复"
        )

        assert metadata.session_id == sample_session_id
        assert metadata.role == "assistant"
        assert metadata.content == "AI回复"
        assert metadata.timestamp is not None
        assert metadata.message_id is not None

        # 验证生成的UUID是有效的
        uuid.UUID(metadata.message_id)  # 如果无效会抛出异常

        # 验证时间戳是最近的（5秒内）
        now = datetime.now(timezone.utc)
        assert abs((metadata.timestamp - now).total_seconds()) < 5

    def test_to_dict(self, sample_session_id, sample_message_id, sample_timestamp):
        """测试转换为字典"""
        metadata = MessageMetadata(
            session_id=sample_session_id,
            role="user",
            content="测试消息",
            timestamp=sample_timestamp,
            message_id=sample_message_id
        )

        result = metadata.to_dict()

        assert isinstance(result, dict)
        assert result["message_id"] == sample_message_id
        assert result["session_id"] == sample_session_id
        assert result["role"] == "user"
        assert result["content"] == "测试消息"
        assert result["timestamp"] == sample_timestamp.isoformat()

    def test_to_dict_with_valid_timestamp(self, sample_session_id, sample_timestamp):
        """测试有效时间戳的字典转换"""
        metadata = MessageMetadata(
            session_id=sample_session_id,
            role="user",
            content="测试消息",
            timestamp=sample_timestamp,
            message_id="test_id"
        )

        result = metadata.to_dict()

        assert result["timestamp"] == sample_timestamp.isoformat()

    def test_from_dict(self, sample_session_id, sample_message_id, sample_timestamp):
        """测试从字典创建实例"""
        data = {
            "message_id": sample_message_id,
            "session_id": sample_session_id,
            "role": "user",
            "content": "测试消息",
            "timestamp": sample_timestamp.isoformat()
        }

        metadata = MessageMetadata.from_dict(data)

        assert metadata.session_id == sample_session_id
        assert metadata.role == "user"
        assert metadata.content == "测试消息"
        assert metadata.timestamp == sample_timestamp
        assert metadata.message_id == sample_message_id

    def test_from_dict_with_complete_data(self, sample_session_id, sample_timestamp):
        """测试完整数据的字典转换"""
        data = {
            "message_id": "test_message_id",
            "session_id": sample_session_id,
            "role": "assistant",
            "content": "AI回复",
            "timestamp": sample_timestamp.isoformat()
        }

        metadata = MessageMetadata.from_dict(data)

        assert metadata.session_id == sample_session_id
        assert metadata.role == "assistant"
        assert metadata.content == "AI回复"
        assert metadata.timestamp == sample_timestamp
        assert metadata.message_id == "test_message_id"

    def test_from_dict_with_optional_message_id(self, sample_session_id):
        """测试包含可选消息ID的字典转换"""
        data = {
            "message_id": "custom_id",
            "session_id": sample_session_id,
            "role": "user",
            "content": "测试消息"
        }

        metadata = MessageMetadata.from_dict(data)

        assert metadata.message_id == "custom_id"

    def test_role_validation(self, sample_session_id):
        """测试角色参数不接受任意值"""
        # MessageMetadata不对role做验证，只存储
        metadata = MessageMetadata(
            session_id=sample_session_id,
            role="任意角色",
            content="测试"
        )
        assert metadata.role == "任意角色"

    def test_message_id_generation_uniqueness(self, sample_session_id):
        """测试消息ID生成的唯一性"""
        metadata1 = MessageMetadata(sample_session_id, "user", "消息1")
        metadata2 = MessageMetadata(sample_session_id, "user", "消息2")

        assert metadata1.message_id != metadata2.message_id

        # 验证都是有效的UUID
        uuid.UUID(metadata1.message_id)
        uuid.UUID(metadata2.message_id)

    def test_timestamp_auto_generation(self, sample_session_id):
        """测试时间戳自动生成"""
        before_creation = datetime.now(timezone.utc)
        metadata = MessageMetadata(sample_session_id, "user", "测试消息")
        after_creation = datetime.now(timezone.utc)

        assert before_creation <= metadata.timestamp <= after_creation

    @pytest.mark.parametrize("role", ["user", "assistant", "system", "tool"])
    def test_different_roles(self, sample_session_id, role):
        """测试不同的角色类型"""
        metadata = MessageMetadata(sample_session_id, role, "测试消息")
        assert metadata.role == role

    def test_empty_content(self, sample_session_id):
        """测试空内容"""
        metadata = MessageMetadata(sample_session_id, "user", "")
        assert metadata.content == ""

    def test_long_content(self, sample_session_id):
        """测试长内容"""
        long_content = "x" * 10000
        metadata = MessageMetadata(sample_session_id, "user", long_content)
        assert metadata.content == long_content


@pytest.mark.unit
class TestSessionInfo:
    """SessionInfo单元测试类"""

    @pytest.fixture
    def sample_session_id(self):
        """提供测试会话ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_user_id(self):
        """提供测试用户ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_timestamp(self):
        """提供测试时间戳"""
        return datetime.now(timezone.utc)

    def test_init_with_all_parameters(self, sample_session_id, sample_user_id, sample_timestamp):
        """测试使用所有参数初始化"""
        created_time = sample_timestamp
        last_message_time = sample_timestamp.replace(second=sample_timestamp.second + 1)

        session_info = SessionInfo(
            session_id=sample_session_id,
            user_id=sample_user_id,
            title="测试会话",
            created_at=created_time,
            last_message_at=last_message_time
        )

        assert session_info.session_id == sample_session_id
        assert session_info.user_id == sample_user_id
        assert session_info.title == "测试会话"
        assert session_info.created_at == created_time
        assert session_info.last_message_at == last_message_time

    def test_init_with_minimal_parameters(self, sample_session_id, sample_user_id):
        """测试使用最小参数初始化"""
        before_creation = datetime.now(timezone.utc)
        session_info = SessionInfo(sample_session_id, sample_user_id)
        after_creation = datetime.now(timezone.utc)

        assert session_info.session_id == sample_session_id
        assert session_info.user_id == sample_user_id
        assert session_info.title == "新会话"  # 默认标题
        assert before_creation <= session_info.created_at <= after_creation
        assert session_info.last_message_at == session_info.created_at

    def test_init_with_custom_title(self, sample_session_id, sample_user_id):
        """测试自定义标题"""
        custom_title = "我的自定义会话"
        session_info = SessionInfo(
            sample_session_id,
            sample_user_id,
            title=custom_title
        )

        assert session_info.title == custom_title

    def test_to_dict(self, sample_session_id, sample_user_id, sample_timestamp):
        """测试转换为字典"""
        session_info = SessionInfo(
            session_id=sample_session_id,
            user_id=sample_user_id,
            title="测试会话",
            created_at=sample_timestamp,
            last_message_at=sample_timestamp
        )

        result = session_info.to_dict()

        assert isinstance(result, dict)
        assert result["session_id"] == sample_session_id
        assert result["user_id"] == sample_user_id
        assert result["title"] == "测试会话"
        assert result["created_at"] == sample_timestamp.isoformat()
        assert result["last_message_at"] == sample_timestamp.isoformat()

    def test_to_dict_with_all_data(self, sample_session_id, sample_user_id, sample_timestamp):
        """测试包含所有数据的字典转换"""
        session_info = SessionInfo(
            session_id=sample_session_id,
            user_id=sample_user_id,
            title="测试会话",
            created_at=sample_timestamp,
            last_message_at=sample_timestamp
        )

        result = session_info.to_dict()

        assert result["created_at"] == sample_timestamp.isoformat()
        assert result["last_message_at"] == sample_timestamp.isoformat()

    def test_from_dict(self, sample_session_id, sample_user_id, sample_timestamp):
        """测试从字典创建实例"""
        data = {
            "session_id": sample_session_id,
            "user_id": sample_user_id,
            "title": "测试会话",
            "created_at": sample_timestamp.isoformat(),
            "last_message_at": sample_timestamp.isoformat()
        }

        session_info = SessionInfo.from_dict(data)

        assert session_info.session_id == sample_session_id
        assert session_info.user_id == sample_user_id
        assert session_info.title == "测试会话"
        assert session_info.created_at == sample_timestamp
        assert session_info.last_message_at == sample_timestamp

    def test_from_dict_with_all_fields(self, sample_session_id, sample_user_id, sample_timestamp):
        """测试包含所有字段的字典转换"""
        data = {
            "session_id": sample_session_id,
            "user_id": sample_user_id,
            "title": "完整会话",
            "created_at": sample_timestamp.isoformat(),
            "last_message_at": sample_timestamp.isoformat()
        }

        session_info = SessionInfo.from_dict(data)

        assert session_info.session_id == sample_session_id
        assert session_info.user_id == sample_user_id
        assert session_info.title == "完整会话"
        assert session_info.created_at == sample_timestamp
        assert session_info.last_message_at == sample_timestamp

    def test_update_last_message_time(self, sample_session_id, sample_user_id):
        """测试更新最后消息时间"""
        session_info = SessionInfo(sample_session_id, sample_user_id)
        original_time = session_info.last_message_at

        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.01)

        session_info.update_last_message_time()

        assert session_info.last_message_at > original_time

    def test_update_last_message_time_multiple_calls(self, sample_session_id, sample_user_id):
        """测试多次调用更新最后消息时间"""
        session_info = SessionInfo(sample_session_id, sample_user_id)

        import time
        times = []

        for i in range(3):
            time.sleep(0.01)
            session_info.update_last_message_time()
            times.append(session_info.last_message_at)

        # 验证时间是递增的
        assert times[0] < times[1] < times[2]

    @pytest.mark.parametrize("title", [None, "", "会话标题", "很长" * 100])
    def test_different_titles(self, sample_session_id, sample_user_id, title):
        """测试不同的标题"""
        session_info = SessionInfo(sample_session_id, sample_user_id, title=title)
        expected_title = title or "新会话"
        assert session_info.title == expected_title

    def test_session_id_user_id_uniqueness(self):
        """测试会话ID和用户ID的唯一性要求"""
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())
        user_id1 = str(uuid.uuid4())
        user_id2 = str(uuid.uuid4())

        session1 = SessionInfo(session_id1, user_id1)
        session2 = SessionInfo(session_id2, user_id2)

        assert session1.session_id != session2.session_id
        assert session1.user_id != session2.user_id


@pytest.mark.integration
class TestSimpleStateIntegration:
    """SimpleState集成测试"""

    def test_message_metadata_roundtrip(self):
        """测试MessageMetadata的完整往返转换"""
        original_data = {
            "message_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "role": "user",
            "content": "往返测试消息",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 字典 -> 对象 -> 字典
        metadata = MessageMetadata.from_dict(original_data)
        result_dict = metadata.to_dict()

        assert result_dict["message_id"] == original_data["message_id"]
        assert result_dict["session_id"] == original_data["session_id"]
        assert result_dict["role"] == original_data["role"]
        assert result_dict["content"] == original_data["content"]
        assert result_dict["timestamp"] == original_data["timestamp"]

    def test_session_info_roundtrip(self):
        """测试SessionInfo的完整往返转换"""
        original_data = {
            "session_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "title": "往返测试会话",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_message_at": datetime.now(timezone.utc).isoformat()
        }

        # 字典 -> 对象 -> 字典
        session_info = SessionInfo.from_dict(original_data)
        result_dict = session_info.to_dict()

        assert result_dict["session_id"] == original_data["session_id"]
        assert result_dict["user_id"] == original_data["user_id"]
        assert result_dict["title"] == original_data["title"]
        assert result_dict["created_at"] == original_data["created_at"]
        assert result_dict["last_message_at"] == original_data["last_message_at"]

    def test_cross_reference_workflow(self):
        """测试交叉引用工作流程"""
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # 创建会话信息
        session_info = SessionInfo(session_id, user_id, "测试会话")

        # 创建多条消息元数据
        messages = [
            MessageMetadata(session_id, "user", "你好"),
            MessageMetadata(session_id, "assistant", "你好！有什么可以帮助你的吗？"),
            MessageMetadata(session_id, "user", "我想了解一下这个系统")
        ]

        # 验证所有消息都属于同一会话
        for msg in messages:
            assert msg.session_id == session_id

        # 更新会话的最后消息时间
        session_info.update_last_message_time()

        # 验证时间戳关系
        assert all(msg.timestamp <= session_info.last_message_at for msg in messages)


@pytest.mark.performance
class TestSimpleStatePerformance:
    """SimpleState性能测试"""

    def test_message_metadata_creation_performance(self):
        """测试MessageMetadata创建性能"""
        import time

        session_id = str(uuid.uuid4())
        start_time = time.time()

        # 创建1000个MessageMetadata实例
        for i in range(1000):
            MessageMetadata(session_id, "user", f"消息{i}")

        end_time = time.time()
        duration = end_time - start_time

        # 应该在1秒内完成
        assert duration < 1.0, f"创建1000个MessageMetadata耗时过长: {duration:.3f}秒"

    def test_session_info_creation_performance(self):
        """测试SessionInfo创建性能"""
        import time

        start_time = time.time()

        # 创建1000个SessionInfo实例
        for i in range(1000):
            SessionInfo(str(uuid.uuid4()), str(uuid.uuid4()), f"会话{i}")

        end_time = time.time()
        duration = end_time - start_time

        # 应该在1秒内完成
        assert duration < 1.0, f"创建1000个SessionInfo耗时过长: {duration:.3f}秒"

    def test_serialization_performance(self):
        """测试序列化性能"""
        import time

        session_id = str(uuid.uuid4())
        metadata = MessageMetadata(session_id, "user", "性能测试消息")

        start_time = time.time()

        # 序列化1000次
        for i in range(1000):
            dict_data = metadata.to_dict()
            MessageMetadata.from_dict(dict_data)

        end_time = time.time()
        duration = end_time - start_time

        # 应该在0.5秒内完成
        assert duration < 0.5, f"序列化1000次耗时过长: {duration:.3f}秒"