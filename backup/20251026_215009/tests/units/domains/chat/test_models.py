"""
聊天模型单元测试

严格TDD方法：
1. ChatMessage模型测试
2. ChatSession模型测试
3. ChatState状态管理测试（简化版，针对TypedDict）
4. ToolCallResult模型测试
5. 便捷函数测试
6. 边界条件测试
7. 序列化测试
8. 类型转换测试

作者：TaTakeKe团队
版本：1.0.0 - 聊天模型单元测试
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage

from src.domains.chat.models import (
    ChatMessage,
    ChatSession,
    ChatState,
    ToolCallResult,
    create_chat_state,
    message_to_chat_message
)


@pytest.mark.unit
class TestChatMessage:
    """ChatMessage模型测试类"""

    def test_init_with_minimal_data(self):
        """测试最小数据初始化"""
        msg = ChatMessage(
            session_id="session123",
            user_id="user123",
            role="user",
            content="Hello"
        )

        assert msg.session_id == "session123"
        assert msg.user_id == "user123"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.id, str)
        assert len(msg.id) > 0
        assert isinstance(msg.created_at, datetime)
        assert msg.tool_calls is None
        assert msg.tool_response is None
        assert msg.metadata is None

    def test_init_with_all_data(self):
        """测试完整数据初始化"""
        tool_calls = [{"name": "test_tool", "args": {"param": "value"}}]
        metadata = {"source": "test"}

        msg = ChatMessage(
            session_id="session123",
            user_id="user123",
            role="assistant",
            content="Response",
            tool_calls=tool_calls,
            tool_response="Tool result",
            metadata=metadata
        )

        assert msg.tool_calls == tool_calls
        assert msg.tool_response == "Tool result"
        assert msg.metadata == metadata

    def test_role_validation_valid_roles(self):
        """测试有效角色验证"""
        valid_roles = ["user", "assistant", "tool", "system"]

        for role in valid_roles:
            msg = ChatMessage(
                session_id="session123",
                user_id="user123",
                role=role,
                content="test"
            )
            assert msg.role == role

    def test_role_validation_invalid_role(self):
        """测试无效角色验证"""
        with pytest.raises(ValueError):
            ChatMessage(
                session_id="session123",
                user_id="user123",
                role="invalid",
                content="test"
            )

    def test_id_generation_uniqueness(self):
        """测试ID生成的唯一性"""
        messages = []
        for i in range(100):
            msg = ChatMessage(
                session_id="session123",
                user_id="user123",
                role="user",
                content=f"Message {i}"
            )
            messages.append(msg)

        # 检查所有ID都是唯一的
        ids = [msg.id for msg in messages]
        assert len(ids) == len(set(ids))

    def test_created_at_timezone(self):
        """测试创建时间时区"""
        msg = ChatMessage(
            session_id="session123",
            user_id="user123",
            role="user",
            content="test"
        )

        # 确保时间是UTC时区
        assert msg.created_at.tzinfo == timezone.utc

    def test_json_serialization(self):
        """测试JSON序列化"""
        msg = ChatMessage(
            session_id="session123",
            user_id="user123",
            role="user",
            content="test"
        )

        # 测试序列化
        data = msg.model_dump()

        assert "id" in data
        assert "created_at" in data
        assert data["session_id"] == "session123"
        assert data["user_id"] == "user123"
        assert data["role"] == "user"
        assert data["content"] == "test"


@pytest.mark.unit
class TestChatSession:
    """ChatSession模型测试类"""

    def test_init_with_minimal_data(self):
        """测试最小数据初始化"""
        session = ChatSession(
            user_id="user123"
        )

        assert session.user_id == "user123"
        assert isinstance(session.id, str)
        assert len(session.id) > 0
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert session.title is None
        assert session.message_count == 0
        assert session.is_active is True

    def test_init_with_all_data(self):
        """测试完整数据初始化"""
        session = ChatSession(
            user_id="user123",
            title="Test Session",
            message_count=5,
            is_active=False
        )

        assert session.title == "Test Session"
        assert session.message_count == 5
        assert session.is_active is False

    def test_id_generation_uniqueness(self):
        """测试会话ID生成的唯一性"""
        sessions = []
        for i in range(50):
            session = ChatSession(user_id=f"user{i}")
            sessions.append(session)

        # 检查所有ID都是唯一的
        ids = [session.id for session in sessions]
        assert len(ids) == len(set(ids))

    def test_timestamps_timezone(self):
        """测试时间戳时区"""
        session = ChatSession(user_id="user123")

        assert session.created_at.tzinfo == timezone.utc
        assert session.updated_at.tzinfo == timezone.utc


@pytest.mark.unit
class TestChatState:
    """ChatState状态管理测试类（简化版）"""

    def test_create_chat_state_empty(self):
        """测试创建空的聊天状态"""
        state = create_chat_state()

        # MessagesState是TypedDict，返回的是dict
        assert isinstance(state, dict)
        assert "messages" in state
        assert len(state["messages"]) == 0

    def test_create_chat_state_function_returns_dict(self):
        """测试create_chat_state函数返回字典"""
        state1 = create_chat_state()
        state2 = create_chat_state()

        assert isinstance(state1, dict)
        assert isinstance(state2, dict)
        assert state1 is not state2  # 确保是不同实例
        assert len(state1["messages"]) == 0
        assert len(state2["messages"]) == 0

    def test_chat_state_manipulation(self):
        """测试ChatState手动操作消息"""
        state = create_chat_state()

        # 手动添加消息
        human_msg = HumanMessage(content="Hello")
        ai_msg = AIMessage(content="Hi there!")

        state["messages"].append(human_msg)
        state["messages"].append(ai_msg)

        assert len(state["messages"]) == 2
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)
        assert state["messages"][0].content == "Hello"
        assert state["messages"][1].content == "Hi there!"

    def test_chat_state_typeddict_structure(self):
        """测试ChatState的TypedDict结构"""
        state = create_chat_state()

        # 验证TypedDict结构
        assert "messages" in state
        assert isinstance(state["messages"], list)

        # 验证可以添加BaseMessage
        tool_msg = ToolMessage(content="Tool result", tool_call_id="tool123")
        state["messages"].append(tool_msg)

        assert len(state["messages"]) == 1
        assert isinstance(state["messages"][0], ToolMessage)


@pytest.mark.unit
class TestToolCallResult:
    """ToolCallResult模型测试类"""

    def test_init_success_result(self):
        """测试成功结果初始化"""
        result = ToolCallResult(
            tool_name="test_tool",
            tool_args={"param": "value"},
            result="Success",
            success=True
        )

        assert result.tool_name == "test_tool"
        assert result.tool_args == {"param": "value"}
        assert result.result == "Success"
        assert result.success is True
        assert result.error is None
        assert result.execution_time is None

    def test_init_failure_result(self):
        """测试失败结果初始化"""
        result = ToolCallResult(
            tool_name="test_tool",
            tool_args={"param": "value"},
            result=None,
            success=False,
            error="Something went wrong",
            execution_time=1.5
        )

        assert result.tool_name == "test_tool"
        assert result.tool_args == {"param": "value"}
        assert result.result is None
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.execution_time == 1.5

    def test_json_serialization(self):
        """测试JSON序列化"""
        result = ToolCallResult(
            tool_name="test_tool",
            tool_args={"param": "value"},
            result="Success",
            success=True,
            execution_time=0.5
        )

        data = result.model_dump()

        assert data["tool_name"] == "test_tool"
        assert data["tool_args"] == {"param": "value"}
        assert data["result"] == "Success"
        assert data["success"] is True
        assert data["error"] is None
        assert data["execution_time"] == 0.5


@pytest.mark.unit
class TestConvenienceFunctions:
    """便捷函数测试类"""

    def test_message_to_chat_message_human(self):
        """测试HumanMessage转换"""
        human_msg = HumanMessage(content="Hello, AI!")

        chat_msg = message_to_chat_message(
            human_msg,
            session_id="session123",
            user_id="user123"
        )

        assert isinstance(chat_msg, ChatMessage)
        assert chat_msg.session_id == "session123"
        assert chat_msg.user_id == "user123"
        assert chat_msg.role == "user"
        assert chat_msg.content == "Hello, AI!"
        assert chat_msg.tool_calls is None
        assert chat_msg.tool_response is None

    def test_message_to_chat_message_ai(self):
        """测试AIMessage转换"""
        ai_msg = AIMessage(content="Hello, human!")

        chat_msg = message_to_chat_message(
            ai_msg,
            session_id="session123",
            user_id="user123"
        )

        assert chat_msg.role == "assistant"
        assert chat_msg.content == "Hello, human!"

    def test_message_to_chat_message_ai_with_tools(self):
        """测试带工具调用的AIMessage转换"""
        tool_calls = [{"name": "test_tool", "args": {"param": "value"}}]
        ai_msg = AIMessage(content="I'll call a tool")
        ai_msg.additional_kwargs["tool_calls"] = tool_calls

        chat_msg = message_to_chat_message(
            ai_msg,
            session_id="session123",
            user_id="user123"
        )

        assert chat_msg.role == "assistant"
        assert chat_msg.content == "I'll call a tool"
        assert chat_msg.tool_calls == tool_calls

    def test_message_to_chat_message_tool(self):
        """测试ToolMessage转换"""
        tool_msg = ToolMessage(
            content="Tool executed successfully",
            tool_call_id="tool_call_123"
        )

        chat_msg = message_to_chat_message(
            tool_msg,
            session_id="session123",
            user_id="user123"
        )

        assert chat_msg.role == "tool"
        assert chat_msg.content == "Tool executed successfully"
        assert chat_msg.tool_calls is None
        assert chat_msg.tool_response == "Tool executed successfully"

    def test_message_to_chat_message_system(self):
        """测试SystemMessage转换"""
        system_msg = SystemMessage(content="System instruction")

        chat_msg = message_to_chat_message(
            system_msg,
            session_id="session123",
            user_id="user123"
        )

        assert chat_msg.role == "system"
        assert chat_msg.content == "System instruction"


@pytest.mark.integration
class TestModelIntegration:
    """模型集成测试"""

    def test_full_chat_workflow(self):
        """测试完整聊天工作流"""
        # 创建会话
        session = ChatSession(user_id="user123", title="Test Chat")

        # 创建聊天状态
        state = create_chat_state()

        # 手动添加消息
        human_msg = HumanMessage(content="What's the weather?")
        ai_msg = AIMessage(content="I'll check the weather for you.")
        tool_msg = ToolMessage(content="Weather: sunny, 25°C", tool_call_id="weather_tool")
        final_ai_msg = AIMessage(content="It's sunny and 25°C outside.")

        state["messages"].extend([human_msg, ai_msg, tool_msg, final_ai_msg])

        # 验证状态
        assert len(state["messages"]) == 4

        # 转换消息为ChatMessage
        chat_messages = []
        for msg in state["messages"]:
            chat_msg = message_to_chat_message(
                msg,
                session.id,
                session.user_id
            )
            chat_messages.append(chat_msg)

        # 验证转换结果
        assert len(chat_messages) == 4
        assert chat_messages[0].role == "user"
        assert chat_messages[1].role == "assistant"
        assert chat_messages[2].role == "tool"
        assert chat_messages[3].role == "assistant"

        # 验证工具响应
        assert chat_messages[2].tool_response == "Weather: sunny, 25°C"

    def test_tool_result_integration(self):
        """测试工具结果集成"""
        # 模拟工具调用
        tool_result = ToolCallResult(
            tool_name="weather_api",
            tool_args={"city": "Beijing"},
            result={"temperature": 25, "condition": "sunny"},
            success=True,
            execution_time=0.8
        )

        # 创建聊天状态
        state = create_chat_state()

        # 添加消息
        human_msg = HumanMessage(content="What's the weather in Beijing?")
        ai_msg = AIMessage(content="I'll check the weather in Beijing")

        state["messages"].extend([human_msg, ai_msg])

        # 使用工具结果
        if tool_result.success:
            response = f"The weather in Beijing is {tool_result.result['temperature']}°C and {tool_result.result['condition']}."
        else:
            response = f"Sorry, I couldn't get the weather: {tool_result.error}"

        final_ai_msg = AIMessage(content=response)
        state["messages"].append(final_ai_msg)

        # 验证工作流
        assert len(state["messages"]) == 3
        assert "25°C" in state["messages"][-1].content


@pytest.mark.performance
class TestModelPerformance:
    """模型性能测试"""

    def test_large_message_list_performance(self):
        """测试大量消息的性能"""
        import time

        state = create_chat_state()

        start_time = time.time()

        # 添加1000条消息
        for i in range(1000):
            if i % 2 == 0:
                state["messages"].append(HumanMessage(content=f"User message {i}"))
            else:
                state["messages"].append(AIMessage(content=f"AI response {i}"))

        duration = time.time() - start_time

        assert len(state["messages"]) == 1000
        assert duration < 1.0, f"Adding 1000 messages took too long: {duration:.3f}s"

    def test_message_conversion_performance(self):
        """测试消息转换性能"""
        import time

        # 创建大量LangGraph消息
        messages = []
        for i in range(500):
            if i % 3 == 0:
                messages.append(HumanMessage(content=f"Human {i}"))
            elif i % 3 == 1:
                messages.append(AIMessage(content=f"AI {i}"))
            else:
                messages.append(ToolMessage(content=f"Tool {i}", tool_call_id=f"tool_{i}"))

        start_time = time.time()

        # 转换所有消息
        chat_messages = []
        for msg in messages:
            chat_msg = message_to_chat_message(msg, "session123", "user123")
            chat_messages.append(chat_msg)

        duration = time.time() - start_time

        assert len(chat_messages) == 500
        assert duration < 0.5, f"Converting 500 messages took too long: {duration:.3f}s"


@pytest.mark.regression
class TestModelRegression:
    """模型回归测试"""

    def test_regression_uuid_consistency(self):
        """回归测试：UUID一致性"""
        # 确保生成的UUID是有效的UUID字符串
        msg = ChatMessage(
            session_id="session123",
            user_id="user123",
            role="user",
            content="test"
        )

        # 验证这是有效的UUID
        try:
            uuid.UUID(msg.id)
            assert True  # 如果没有异常，说明是有效的UUID
        except ValueError:
            assert False, f"Generated ID {msg.id} is not a valid UUID"

    def test_regression_timezone_handling(self):
        """回归测试：时区处理"""
        # 确保所有时间都是UTC时区
        msg = ChatMessage(
            session_id="session123",
            user_id="user123",
            role="user",
            content="test"
        )

        session = ChatSession(user_id="user123")

        assert msg.created_at.tzinfo == timezone.utc
        assert session.created_at.tzinfo == timezone.utc
        assert session.updated_at.tzinfo == timezone.utc

    def test_regression_message_type_handling(self):
        """回归测试：消息类型处理"""
        # 测试所有支持的消息类型都能正确转换
        state = create_chat_state()

        # 添加各种类型的消息
        state["messages"].append(HumanMessage(content="Human message"))
        state["messages"].append(AIMessage(content="AI message"))
        state["messages"].append(ToolMessage(content="Tool result", tool_call_id="tool123"))

        # 验证消息类型
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)
        assert isinstance(state["messages"][2], ToolMessage)

        # 验证可以转换为ChatMessage
        for msg in state["messages"]:
            chat_msg = message_to_chat_message(msg, "session123", "user123")
            assert isinstance(chat_msg, ChatMessage)
            assert chat_msg.role in ["user", "assistant", "tool"]