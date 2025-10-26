"""
Chat领域测试配置

提供chat领域测试所需的特定fixtures和工具函数。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domains.chat.models import ChatMessage, ChatSession, ChatState, ToolCallResult


@pytest.fixture(scope="function")
def chat_service(chat_db_session):
    """提供ChatService实例的fixture（如果存在）"""
    # 如果chat服务存在，在这里创建
    # try:
    #     from src.domains.chat.service import ChatService
    #     return ChatService(chat_db_session)
    # except ImportError:
    #     pytest.skip("ChatService not implemented")
    return None


@pytest.fixture(scope="function")
def sample_user_id():
    """提供测试用户ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def sample_session_id():
    """提供测试会话ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def sample_chat_session(sample_user_id):
    """创建测试用的聊天会话"""
    return ChatSession(
        id=str(uuid4()),
        user_id=sample_user_id,
        title="测试会话",
        welcome_message="欢迎使用AI助手！"
    )


@pytest.fixture(scope="function")
def sample_user_message(sample_session_id, sample_user_id):
    """创建测试用户消息"""
    return ChatMessage(
        session_id=sample_session_id,
        user_id=sample_user_id,
        role="user",
        content="你好，这是一个测试消息"
    )


@pytest.fixture(scope="function")
def sample_assistant_message(sample_session_id, sample_user_id):
    """创建测试助手消息"""
    return ChatMessage(
        session_id=sample_session_id,
        user_id=sample_user_id,
        role="assistant",
        content="你好！我是AI助手，很高兴为你服务。"
    )


@pytest.fixture(scope="function")
def sample_tool_message(sample_session_id, sample_user_id):
    """创建测试工具消息"""
    return ChatMessage(
        session_id=sample_session_id,
        user_id=sample_user_id,
        role="tool",
        content='{"result": "success", "data": "测试数据"}',
        tool_response='{"result": "success", "data": "测试数据"}'
    )


@pytest.fixture(scope="function")
def conversation_flow(sample_session_id, sample_user_id):
    """创建一个完整的对话流程"""
    messages = []

    # 用户提问
    messages.append(ChatMessage(
        session_id=sample_session_id,
        user_id=sample_user_id,
        role="user",
        content="今天天气怎么样？"
    ))

    # 助手回复并调用工具
    messages.append(ChatMessage(
        session_id=sample_session_id,
        user_id=sample_user_id,
        role="assistant",
        content="我来帮你查询天气信息。",
        tool_calls=[{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "北京"}'
            }
        }]
    ))

    # 工具返回结果
    messages.append(ChatMessage(
        session_id=sample_session_id,
        user_id=sample_user_id,
        role="tool",
        content='{"temperature": 25, "condition": "晴朗", "humidity": 60}',
        tool_response='{"temperature": 25, "condition": "晴朗", "humidity": 60}'
    ))

    # 助手最终回复
    messages.append(ChatMessage(
        session_id=sample_session_id,
        user_id=sample_user_id,
        role="assistant",
        content="今天北京天气晴朗，温度25度，湿度60%。是个不错的好天气！"
    ))

    return messages


@pytest.fixture(scope="function")
def sample_chat_state(sample_session_id, sample_user_id):
    """创建测试用的聊天状态"""
    state = ChatState()
    state.user_id = sample_user_id
    state.session_id = sample_session_id
    return state


@pytest.fixture(scope="function")
def sample_tool_call_result():
    """创建测试用的工具调用结果"""
    return ToolCallResult(
        call_id=str(uuid4()),
        tool_name="get_weather",
        result='{"temperature": 25, "condition": "sunny"}',
        execution_time_ms=500,
        metadata={"location": "北京", "source": "weather_api"}
    )


@pytest.fixture(scope="function")
def sample_error_tool_call_result():
    """创建测试用的错误工具调用结果"""
    return ToolCallResult(
        call_id=str(uuid4()),
        tool_name="invalid_tool",
        error="Tool not found or configuration error",
        status="error",
        execution_time_ms=100
    )


@pytest.fixture(scope="function")
def multiple_chat_sessions(sample_user_id):
    """创建多个测试聊天会话"""
    sessions = []

    # 创建不同状态的会话
    sessions.append(ChatSession(
        id=str(uuid4()),
        user_id=sample_user_id,
        title="活跃会话",
        status="active"
    ))

    sessions.append(ChatSession(
        id=str(uuid4()),
        user_id=sample_user_id,
        title="归档会话",
        status="archived"
    ))

    sessions.append(ChatSession(
        id=str(uuid4()),
        user_id=sample_user_id,
        title="技术支持会话",
        welcome_message="您好！我是技术支持助手。"
    ))

    return sessions


@pytest.fixture(scope="function")
def chat_session_with_messages(sample_session_id, sample_user_id):
    """创建带消息的聊天会话"""
    session = ChatSession(
        id=sample_session_id,
        user_id=sample_user_id,
        title="带消息的会话"
    )

    messages = [
        ChatMessage(
            session_id=sample_session_id,
            user_id=sample_user_id,
            role="user",
            content="第一条消息"
        ),
        ChatMessage(
            session_id=sample_session_id,
            user_id=sample_user_id,
            role="assistant",
            content="第一条回复"
        ),
        ChatMessage(
            session_id=sample_session_id,
            user_id=sample_user_id,
            role="user",
            content="第二条消息"
        )
    ]

    return session, messages


@pytest.fixture(scope="function")
def sample_message_data():
    """提供测试用的消息数据"""
    return {
        "role": "user",
        "content": "这是一个测试消息",
        "tool_calls": None,
        "tool_response": None
    }


@pytest.fixture(scope="function")
def sample_session_data():
    """提供测试用的会话数据"""
    return {
        "title": "测试会话",
        "welcome_message": "欢迎使用AI助手！",
        "status": "active"
    }