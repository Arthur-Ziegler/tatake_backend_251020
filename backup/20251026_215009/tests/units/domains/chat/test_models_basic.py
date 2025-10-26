"""
Chat领域模型测试套件

测试ChatMessage、ChatSession、ChatState、ToolCallResult模型的基本功能，
包括字段验证、消息序列化和状态管理。

遵循TDD原则，专注于模型层的数据验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict, Any

from src.domains.chat.models import ChatMessage, ChatSession, ChatState, ToolCallResult


@pytest.mark.unit
class TestChatMessageModel:
    """ChatMessage模型测试类"""

    def test_chat_message_creation_user_role(self):
        """测试用户角色消息创建"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content="Hello, AI assistant!"
        )

        assert message.session_id == session_id
        assert message.user_id == user_id
        assert message.role == "user"
        assert message.content == "Hello, AI assistant!"
        assert message.id is not None
        assert message.created_at is not None
        assert message.tool_calls is None
        assert message.tool_response is None

    def test_chat_message_creation_assistant_role(self):
        """测试助手角色消息创建"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content="Hello! How can I help you today?"
        )

        assert message.role == "assistant"
        assert message.content == "Hello! How can I help you today?"

    def test_chat_message_creation_tool_role(self):
        """测试工具角色消息创建"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="tool",
            content="Tool execution result: success"
        )

        assert message.role == "tool"
        assert message.content == "Tool execution result: success"

    def test_chat_message_creation_system_role(self):
        """测试系统角色消息创建"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="system",
            content="You are a helpful AI assistant."
        )

        assert message.role == "system"
        assert message.content == "You are a helpful AI assistant."

    def test_chat_message_with_tool_calls(self):
        """测试带工具调用的消息"""
        session_id = str(uuid4())
        user_id = str(uuid4())
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Beijing"}'
                }
            }
        ]

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content="I'll check the weather for you.",
            tool_calls=tool_calls
        )

        assert message.tool_calls == tool_calls
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0]["function"]["name"] == "get_weather"

    def test_chat_message_with_tool_response(self):
        """测试带工具响应的消息"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="tool",
            content='{"temperature": 25, "condition": "sunny"}',
            tool_response='{"temperature": 25, "condition": "sunny"}'
        )

        assert message.tool_response == '{"temperature": 25, "condition": "sunny"}'

    def test_chat_message_invalid_role(self):
        """测试无效角色"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        with pytest.raises(ValueError):  # Pydantic验证错误
            ChatMessage(
                session_id=session_id,
                user_id=user_id,
                role="invalid_role",
                content="This should fail"
            )

    def test_chat_message_auto_id_generation(self):
        """测试自动生成消息ID"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        message1 = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content="Message 1"
        )

        message2 = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content="Message 2"
        )

        # 验证ID自动生成且唯一
        assert message1.id is not None
        assert message2.id is not None
        assert message1.id != message2.id

    def test_chat_message_timestamp(self):
        """测试时间戳自动生成"""
        session_id = str(uuid4())
        user_id = str(uuid4())
        before_creation = datetime.now(timezone.utc)

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content="Test message"
        )

        after_creation = datetime.now(timezone.utc)

        # 验证创建时间在合理范围内
        assert before_creation <= message.created_at <= after_creation

    def test_chat_message_string_representation(self):
        """测试字符串表示"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content="Test representation"
        )

        repr_str = repr(message)

        # 验证字符串包含关键信息
        assert "ChatMessage" in repr_str
        assert message.id in repr_str
        assert "user" in repr_str
        assert "Test representation" in repr_str


@pytest.mark.unit
class TestChatSessionModel:
    """ChatSession模型测试类"""

    def test_chat_session_creation(self):
        """测试聊天会话创建"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        session = ChatSession(
            id=session_id,
            user_id=user_id,
            title="测试会话"
        )

        assert session.id == session_id
        assert session.user_id == user_id
        assert session.title == "测试会话"
        assert session.status is not None  # 检查默认状态
        assert session.created_at is not None

    def test_chat_session_with_welcome_message(self):
        """测试带欢迎消息的会话"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        session = ChatSession(
            id=session_id,
            user_id=user_id,
            title="带欢迎消息的会话",
            welcome_message="欢迎使用AI助手！"
        )

        assert session.welcome_message == "欢迎使用AI助手！"

    def test_chat_session_status_validation(self):
        """测试会话状态验证"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        # 测试活跃状态
        active_session = ChatSession(
            id=session_id,
            user_id=user_id,
            title="活跃会话",
            status="active"
        )
        assert active_session.status == "active"

        # 测试归档状态
        archived_session = ChatSession(
            id=str(uuid4()),
            user_id=user_id,
            title="归档会话",
            status="archived"
        )
        assert archived_session.status == "archived"

    def test_chat_session_message_count(self):
        """测试消息计数"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        session = ChatSession(
            id=session_id,
            user_id=user_id,
            title="计数测试会话"
        )

        # 初始消息计数应该为0
        assert session.message_count == 0

    def test_chat_session_last_activity(self):
        """测试最后活动时间"""
        session_id = str(uuid4())
        user_id = str(uuid4())
        last_activity = datetime.now(timezone.utc)

        session = ChatSession(
            id=session_id,
            user_id=user_id,
            title="活动测试会话",
            last_activity_at=last_activity
        )

        assert session.last_activity_at == last_activity


@pytest.mark.unit
class TestChatStateModel:
    """ChatState模型测试类"""

    def test_chat_state_creation(self):
        """测试聊天状态创建"""
        state = ChatState()

        # 验证基本属性
        assert hasattr(state, 'messages')
        assert hasattr(state, 'user_id')
        assert hasattr(state, 'session_id')

    def test_chat_state_with_messages(self):
        """测试带消息的聊天状态"""
        state = ChatState()
        user_id = str(uuid4())
        session_id = str(uuid4())

        state.user_id = user_id
        state.session_id = session_id

        assert state.user_id == user_id
        assert state.session_id == session_id

    def test_chat_state_serialization(self):
        """测试状态序列化"""
        state = ChatState()
        user_id = str(uuid4())
        session_id = str(uuid4())

        state.user_id = user_id
        state.session_id = session_id

        # 转换为字典
        state_dict = state.model_dump()

        assert 'user_id' in state_dict
        assert 'session_id' in state_dict
        assert state_dict['user_id'] == user_id
        assert state_dict['session_id'] == session_id


@pytest.mark.unit
class TestToolCallResultModel:
    """ToolCallResult模型测试类"""

    def test_tool_call_result_creation(self):
        """测试工具调用结果创建"""
        call_id = str(uuid4())
        tool_name = "get_weather"

        result = ToolCallResult(
            call_id=call_id,
            tool_name=tool_name,
            result='{"temperature": 25, "condition": "sunny"}'
        )

        assert result.call_id == call_id
        assert result.tool_name == tool_name
        assert result.result == '{"temperature": 25, "condition": "sunny"}'
        assert result.status == "success"
        assert result.created_at is not None

    def test_tool_call_result_with_error(self):
        """测试带错误的工具调用结果"""
        call_id = str(uuid4())
        tool_name = "invalid_tool"

        result = ToolCallResult(
            call_id=call_id,
            tool_name=tool_name,
            error="Tool not found",
            status="error"
        )

        assert result.status == "error"
        assert result.error == "Tool not found"
        assert result.result is None

    def test_tool_call_result_with_execution_time(self):
        """测试带执行时间的工具调用结果"""
        call_id = str(uuid4())
        tool_name = "slow_tool"

        result = ToolCallResult(
            call_id=call_id,
            tool_name=tool_name,
            result="Operation completed",
            execution_time_ms=1500
        )

        assert result.execution_time_ms == 1500
        assert result.execution_time_ms > 0

    def test_tool_call_result_metadata(self):
        """测试带元数据的工具调用结果"""
        call_id = str(uuid4())
        tool_name = "data_query"
        metadata = {
            "query_type": "SELECT",
            "rows_affected": 10,
            "execution_plan": "index_scan"
        }

        result = ToolCallResult(
            call_id=call_id,
            tool_name=tool_name,
            result="Query successful",
            metadata=metadata
        )

        assert result.metadata == metadata
        assert result.metadata["rows_affected"] == 10
        assert result.metadata["execution_plan"] == "index_scan"

    def test_tool_call_result_string_representation(self):
        """测试工具调用结果字符串表示"""
        call_id = str(uuid4())
        tool_name = "test_tool"

        result = ToolCallResult(
            call_id=call_id,
            tool_name=tool_name,
            result="Test result"
        )

        repr_str = repr(result)

        # 验证字符串包含关键信息
        assert "ToolCallResult" in repr_str
        assert call_id in repr_str
        assert tool_name in repr_str
        assert "success" in repr_str


@pytest.mark.unit
class TestChatModelRelationships:
    """测试聊天模型间的关系"""

    def test_message_to_session_relationship(self):
        """测试消息与会话的关系"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        # 创建会话
        session = ChatSession(
            id=session_id,
            user_id=user_id,
            title="测试会话"
        )

        # 创建属于该会话的消息
        message1 = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content="Hello"
        )

        message2 = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content="Hi there!"
        )

        # 验证消息属于同一会话
        assert message1.session_id == session.id
        assert message2.session_id == session.id
        assert message1.user_id == session.user_id
        assert message2.user_id == session.user_id

    def test_message_conversation_flow(self):
        """测试对话流程"""
        session_id = str(uuid4())
        user_id = str(uuid4())

        # 创建对话流程
        user_message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content="What's the weather?"
        )

        assistant_message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content="I'll check the weather for you.",
            tool_calls=[{
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": "{}"}
            }]
        )

        tool_message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="tool",
            content='{"temperature": 25, "condition": "sunny"}',
            tool_response='{"temperature": 25, "condition": "sunny"}'
        )

        final_assistant_message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content="The weather is sunny with a temperature of 25°C."
        )

        # 验证对话顺序
        messages = [user_message, assistant_message, tool_message, final_assistant_message]
        roles = [msg.role for msg in messages]

        assert roles == ["user", "assistant", "tool", "assistant"]
        assert all(msg.session_id == session_id for msg in messages)
        assert all(msg.user_id == user_id for msg in messages)