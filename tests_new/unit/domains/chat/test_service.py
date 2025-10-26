"""
聊天服务层单元测试

严格TDD方法：
1. ChatService基本功能测试
2. 会话管理测试
3. 消息处理测试
4. 类型安全checkpointer测试
5. 错误处理测试
6. 历史记录查询测试
7. 权限验证测试
8. 健康检查测试
9. UUID转换测试
10. 边界条件和异常处理测试

作者：TaTakeKe团队
版本：1.0.0 - 聊天服务层单元测试
"""

import pytest
import uuid
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, Mock, ANY
from pathlib import Path

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from src.domains.chat.service import ChatService, chat_service
from src.domains.chat.models import ChatSession, ChatMessage
from src.core.uuid_converter import UUIDConverter


@pytest.mark.unit
class TestChatServiceBasic:
    """ChatService基础功能测试"""

    def test_init(self):
        """测试ChatService初始化"""
        service = ChatService()

        assert service.db_manager is not None
        assert service._store is not None
        assert service._graph is None

    def test_chat_service_singleton(self):
        """测试全局chat_service实例"""
        assert chat_service is not None
        assert isinstance(chat_service, ChatService)

    def test_create_thread_id(self):
        """测试线程ID创建"""
        service = ChatService()
        thread_id1 = service._create_thread_id()
        thread_id2 = service._create_thread_id()

        assert isinstance(thread_id1, str)
        assert isinstance(thread_id2, str)
        assert len(thread_id1) > 0
        assert len(thread_id2) > 0
        assert thread_id1 != thread_id2  # 确保唯一性

    def test_create_runnable_config_valid_uuids(self):
        """测试创建运行配置（有效UUID）"""
        service = ChatService()
        user_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())

        config = service._create_runnable_config(user_id, thread_id)

        assert isinstance(config, dict)
        assert "configurable" in config
        assert config["configurable"]["thread_id"] == thread_id
        assert config["configurable"]["user_id"] == user_id

    def test_create_runnable_config_invalid_uuids(self):
        """测试创建运行配置（无效UUID）"""
        service = ChatService()

        with pytest.raises(ValueError) as exc_info:
            service._create_runnable_config("invalid-uuid", "thread123")

        assert "UUID格式错误" in str(exc_info.value)


@pytest.mark.unit
class TestTypeSafeCheckpointer:
    """类型安全checkpointer测试"""

    def test_create_type_safe_checkpointer(self):
        """测试创建类型安全checkpointer"""
        service = ChatService()
        base_checkpointer = MagicMock()

        safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

        assert safe_checkpointer is not None
        assert safe_checkpointer.base_checkpointer == base_checkpointer

    def test_fix_string_version_number_simple_integer(self):
        """测试修复简单整数字符串版本号"""
        service = ChatService()
        base_checkpointer = MagicMock()
        safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

        channel_versions = {"messages": "1"}
        checkpoint = {"channel_versions": channel_versions}

        safe_checkpointer._fix_string_version_number("messages", "1", channel_versions)

        assert channel_versions["messages"] == 1

    def test_fix_string_version_number_float_string(self):
        """测试修复浮点数字符串版本号"""
        service = ChatService()
        base_checkpointer = MagicMock()
        safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

        channel_versions = {"messages": "2.0"}
        checkpoint = {"channel_versions": channel_versions}

        safe_checkpointer._fix_string_version_number("messages", "2.0", channel_versions)

        assert channel_versions["messages"] == 2

    def test_fix_string_version_number_langgraph_format(self):
        """测试修复LangGraph特殊格式版本号"""
        service = ChatService()
        base_checkpointer = MagicMock()
        safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

        channel_versions = {"__start__": "00000000000000000000000000000002.0.243798848838515"}
        checkpoint = {"channel_versions": channel_versions}

        safe_checkpointer._fix_string_version_number("__start__",
            "00000000000000000000000000000002.0.243798848838515", channel_versions)

        assert channel_versions["__start__"] == 2

    def test_fix_string_version_number_complex_uuid(self):
        """测试修复复杂UUID字符串版本号"""
        service = ChatService()
        base_checkpointer = MagicMock()
        safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

        channel_versions = {"channel": "complex-uuid-string-12345"}
        checkpoint = {"channel_versions": channel_versions}

        safe_checkpointer._fix_string_version_number("channel",
            "complex-uuid-string-12345", channel_versions)

        # 应该生成稳定的哈希整数
        assert isinstance(channel_versions["channel"], int)
        assert channel_versions["channel"] > 0

    def test_fix_non_integer_version(self):
        """测试修复非整数类型版本号"""
        service = ChatService()
        base_checkpointer = MagicMock()
        safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

        channel_versions = {"messages": 2.5}
        checkpoint = {"channel_versions": channel_versions}

        safe_checkpointer._fix_non_integer_version("messages", 2.5, channel_versions)

        assert channel_versions["messages"] == 2

    def test_put_with_type_fixing(self):
        """测试put方法的类型修复功能"""
        service = ChatService()
        base_checkpointer = MagicMock()
        safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

        config = {"configurable": {"thread_id": "test"}}
        checkpoint = {
            "channel_versions": {
                "messages": 1,
                "__start__": "00000000000000000000000000000002.0.243798848838515"
            }
        }
        metadata = {"user_id": "test"}
        new_versions = {"messages": 2}

        safe_checkpointer.put(config, checkpoint, metadata, new_versions)

        # 验证修复后的checkpoint被传递给原始checkpointer
        base_checkpointer.put.assert_called_once()
        call_args = base_checkpointer.put.call_args
        fixed_checkpoint = call_args[0][1]  # 第二个参数是checkpoint

        assert fixed_checkpoint["channel_versions"]["__start__"] == 2
        assert fixed_checkpoint["channel_versions"]["messages"] == 1


@pytest.mark.unit
class TestChatServiceSessionManagement:
    """会话管理测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    def test_create_session_success(self, mock_db_manager):
        """测试成功创建会话"""
        # 模拟数据库管理器
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        service = ChatService()
        user_id = str(uuid.uuid4())
        title = "测试会话"

        with patch.object(service, '_create_session_record_directly') as mock_create:
            result = service.create_session(user_id, title)

            mock_create.assert_called_once_with(user_id, ANY, title)

        assert "session_id" in result
        assert result["title"] == title
        assert "welcome_message" in result
        assert result["status"] == "created"
        assert "created_at" in result

    @patch('src.domains.chat.service.chat_db_manager')
    def test_create_session_without_title(self, mock_db_manager):
        """测试创建会话（无标题）"""
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        service = ChatService()
        user_id = str(uuid.uuid4())

        with patch.object(service, '_create_session_record_directly') as mock_create:
            result = service.create_session(user_id)

            mock_create.assert_called_once_with(user_id, ANY, "新会话")

        assert result["title"] == "新会话"

    @patch('src.domains.chat.service.chat_db_manager')
    def test_create_session_failure(self, mock_db_manager):
        """测试创建会话失败"""
        mock_db_manager.create_checkpointer.side_effect = Exception("Database error")

        service = ChatService()
        user_id = str(uuid.uuid4())

        with pytest.raises(Exception) as exc_info:
            service.create_session(user_id)

        assert "创建会话失败" in str(exc_info.value)

    def test_create_session_record_directly(self):
        """测试直接创建会话记录"""
        service = ChatService()

        with patch.object(service.db_manager, 'create_checkpointer') as mock_create_check:
            mock_checkpointer = MagicMock()
            mock_create_check.return_value.__enter__.return_value = mock_checkpointer
            mock_create_check.return_value.__exit__.return_value = None

            user_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            title = "测试会话"

            service._create_session_record_directly(user_id, session_id, title)

            # 验证checkpointer.put被调用
            mock_checkpointer.put.assert_called_once()


@pytest.mark.unit
class TestChatServiceMessageProcessing:
    """消息处理测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_send_message_success(self, mock_create_graph, mock_db_manager):
        """测试成功发送消息"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        # 模拟图实例 - 需要设置更完整的mock来支持LangGraph内部操作
        mock_graph_instance = MagicMock()
        mock_graph_instance.graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!")
            ]
        }
        # 设置checkpoint mock以支持LangGraph的所有必要字段
        mock_checkpointer.get_tuple.return_value.checkpoint = {
            "v": 4,  # 设置正确的版本号
            "id": "test-checkpoint-id",  # LangGraph需要的checkpoint ID
            "ts": 1640995200.0,  # 时间戳
            "channel_values": {"messages": []},
            "channel_versions": {"messages": 1},
            "versions_seen": {},
            "pending_sends": []
        }
        mock_create_graph.return_value = mock_graph_instance

        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        message = "Hello, AI!"

        result = service.send_message(user_id, session_id, message)

        assert "session_id" in result
        assert result["user_message"] == message
        assert result["ai_response"] == "Hi there!"
        assert result["status"] == "success"
        assert "timestamp" in result

    def test_send_message_empty_content(self):
        """测试发送空消息"""
        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError) as exc_info:
            service.send_message(user_id, session_id, "")

        assert "消息内容不能为空" in str(exc_info.value)

    def test_send_message_whitespace_only(self):
        """测试发送仅包含空格的消息"""
        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError) as exc_info:
            service.send_message(user_id, session_id, "   ")

        assert "消息内容不能为空" in str(exc_info.value)

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_send_message_with_tool_calls(self, mock_create_graph, mock_db_manager):
        """测试发送带工具调用的消息"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        # 模拟带工具调用的图实例
        mock_graph_instance = MagicMock()
        mock_graph_instance.graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="What's the weather?"),
                AIMessage(content="I'll check the weather", tool_calls=[{"id": "1", "name": "weather_tool"}]),
                ToolMessage(content="Sunny, 25°C", tool_call_id="1"),
                AIMessage(content="It's sunny and 25°C")
            ]
        }
        mock_create_graph.return_value = mock_graph_instance

        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        message = "What's the weather?"

        result = service.send_message(user_id, session_id, message)

        assert result["ai_response"] == "It's sunny and 25°C"

    def test_extract_ai_response_simple(self):
        """测试提取AI回复（简单情况）"""
        service = ChatService()
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!")
        ]

        response = service._extract_ai_response(messages)

        assert response == "Hi there!"

    def test_extract_ai_response_with_tools(self):
        """测试提取AI回复（包含工具调用）"""
        service = ChatService()
        messages = [
            HumanMessage(content="What's the weather?"),
            AIMessage(content="I'll check", tool_calls=[{"id": "1"}]),
            ToolMessage(content="Sunny", tool_call_id="1")
        ]

        response = service._extract_ai_response(messages)

        assert response == "工具调用已完成。"

    def test_extract_ai_response_no_ai_message(self):
        """测试提取AI回复（无AI消息）"""
        service = ChatService()
        messages = [
            HumanMessage(content="Hello")
        ]

        response = service._extract_ai_response(messages)

        assert response == "抱歉，我现在无法处理您的消息，请稍后再试。"


@pytest.mark.unit
class TestChatServiceHistoryManagement:
    """历史记录管理测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_get_chat_history_success(self, mock_create_graph, mock_db_manager):
        """测试成功获取聊天历史"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        # 模拟图实例
        mock_graph_instance = MagicMock()
        mock_graph_instance.graph.get_state.return_value = MagicMock()
        mock_graph_instance.graph.get_state.return_value.values = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
                ToolMessage(content="Tool result", tool_call_id="1")
            ]
        }
        mock_create_graph.return_value = mock_graph_instance

        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        result = service.get_chat_history(user_id, session_id, limit=50)

        assert "session_id" in result
        assert "messages" in result
        assert len(result["messages"]) == 3
        assert result["total_count"] == 3
        assert result["limit"] == 50
        assert result["status"] == "success"

        # 验证消息格式
        messages = result["messages"]
        assert messages[0]["type"] == "human"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["type"] == "ai"
        assert messages[1]["content"] == "Hi there!"
        assert messages[2]["type"] == "tool"
        assert messages[2]["content"] == "Tool result"

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_get_chat_history_with_limit(self, mock_create_graph, mock_db_manager):
        """测试获取聊天历史（带限制）"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        # 模拟大量消息
        messages = []
        for i in range(100):
            if i % 2 == 0:
                messages.append(HumanMessage(content=f"Human {i}"))
            else:
                messages.append(AIMessage(content=f"AI {i}"))

        mock_graph_instance = MagicMock()
        mock_graph_instance.graph.get_state.return_value = MagicMock()
        mock_graph_instance.graph.get_state.return_value.values = {"messages": messages}
        mock_create_graph.return_value = mock_graph_instance

        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        result = service.get_chat_history(user_id, session_id, limit=10)

        assert len(result["messages"]) == 10  # 应该只返回最新的10条
        assert result["total_count"] == 10

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_get_chat_history_empty(self, mock_create_graph, mock_db_manager):
        """测试获取空的聊天历史"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        mock_graph_instance = MagicMock()
        mock_graph_instance.graph.get_state.return_value = MagicMock()
        mock_graph_instance.graph.get_state.return_value.values = {"messages": []}
        mock_create_graph.return_value = mock_graph_instance

        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        result = service.get_chat_history(user_id, session_id)

        assert len(result["messages"]) == 0
        assert result["total_count"] == 0


@pytest.mark.unit
class TestChatServiceSessionInfo:
    """会话信息测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    def test_get_session_info_success(self, mock_db_manager):
        """测试成功获取会话信息"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        # 模拟检查点数据
        mock_checkpoint = MagicMock()
        mock_checkpoint.checkpoint = {
            "channel_values": {
                "messages": [
                    HumanMessage(content="Hello"),
                    AIMessage(content="Hi")
                ]
            }
        }
        mock_checkpoint.metadata = {
            "user_id": "test_user",
            "title": "测试会话",
            "source": {"time": "2024-01-01T10:00:00Z"}
        }
        mock_checkpointer.list.return_value = [mock_checkpoint]

        service = ChatService()
        user_id = "test_user"
        session_id = str(uuid.uuid4())

        result = service.get_session_info(user_id, session_id)

        assert result["session_id"] == session_id
        assert result["title"] == "测试会话"
        assert result["message_count"] == 2
        assert result["status"] == "active"

    @patch('src.domains.chat.service.chat_db_manager')
    def test_get_session_info_not_found(self, mock_db_manager):
        """测试获取不存在的会话信息"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        mock_checkpointer.list.return_value = []

        service = ChatService()
        user_id = "test_user"
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError) as exc_info:
            service.get_session_info(user_id, session_id)

        assert "会话不存在" in str(exc_info.value)

    @patch('src.domains.chat.service.chat_db_manager')
    def test_get_session_info_permission_denied(self, mock_db_manager):
        """测试获取会话信息（权限不足）"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        mock_checkpoint = MagicMock()
        mock_checkpoint.metadata = {"user_id": "other_user"}
        mock_checkpointer.list.return_value = [mock_checkpoint]

        service = ChatService()
        user_id = "test_user"
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError) as exc_info:
            service.get_session_info(user_id, session_id)

        assert "无权访问此会话" in str(exc_info.value)


@pytest.mark.unit
class TestChatServiceSessionList:
    """会话列表测试"""

    @patch('src.domains.chat.service.get_chat_database_path')
    @patch('sqlite3.connect')
    def test_list_sessions_success(self, mock_connect, mock_get_path):
        """测试成功列出会话"""
        # 模拟数据库路径
        mock_get_path.return_value = "/tmp/test.db"

        # 模拟数据库连接和查询结果
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.row_factory = sqlite3.Row
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 模拟查询结果
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            'thread_id': 'session123',
            'checkpoint_id': 1,
            'checkpoint': '{"channel_values":{"messages":[]}}',
            'metadata': '{"user_id":"test_user","title":"测试会话"}'
        }[key]
        mock_cursor.fetchall.return_value = [mock_row]

        # 模拟计数查询
        mock_count_row = {'checkpoint_count': 5}
        mock_cursor.fetchone.return_value = mock_count_row

        service = ChatService()
        user_id = "test_user"

        result = service.list_sessions(user_id, limit=20)

        assert "sessions" in result
        assert len(result["sessions"]) == 1
        assert result["total_count"] == 1
        assert result["status"] == "success"
        assert result["sessions"][0]["title"] == "测试会话"

    @patch('src.domains.chat.service.get_chat_database_path')
    @patch('sqlite3.connect')
    def test_list_sessions_empty(self, mock_connect, mock_get_path):
        """测试列出空会话列表"""
        mock_get_path.return_value = "/tmp/test.db"
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.row_factory = sqlite3.Row
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        service = ChatService()
        user_id = "test_user"

        result = service.list_sessions(user_id, limit=20)

        assert len(result["sessions"]) == 0
        assert result["total_count"] == 0


@pytest.mark.unit
class TestChatServiceSessionDeletion:
    """会话删除测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_delete_session_success(self, mock_create_graph, mock_db_manager):
        """测试成功删除会话"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        # 模拟删除操作
        mock_checkpointer.delete_thread.return_value = True

        service = ChatService()
        user_id = "test_user"
        session_id = str(uuid.uuid4())

        with patch.object(service, 'get_session_info') as mock_get_info:
            # 模拟会话存在且属于用户
            mock_get_info.return_value = {"session_id": session_id, "user_id": user_id}

            # 模拟删除后验证失败
            with patch.object(service, 'get_session_info') as mock_verify:
                mock_verify.side_effect = ValueError("会话不存在")

                result = service.delete_session(user_id, session_id)

        assert result["session_id"] == session_id
        assert result["status"] == "deleted"
        assert result["user_id"] == user_id

    @patch('src.domains.chat.service.chat_db_manager')
    def test_delete_session_not_found(self, mock_db_manager):
        """测试删除不存在的会话"""
        service = ChatService()
        user_id = "test_user"
        session_id = str(uuid.uuid4())

        with patch.object(service, 'get_session_info') as mock_get_info:
            mock_get_info.side_effect = ValueError("会话不存在")

            with pytest.raises(Exception) as exc_info:
                service.delete_session(user_id, session_id)

        assert "会话不存在或无权访问" in str(exc_info.value)


@pytest.mark.unit
class TestChatServiceHealthCheck:
    """健康检查测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_health_check_success(self, mock_create_graph, mock_db_manager):
        """测试健康检查成功"""
        # 模拟数据库健康检查
        mock_db_manager.health_check.return_value = {"status": "healthy"}

        # 模拟图创建测试
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        service = ChatService()
        result = service.health_check()

        assert result["status"] == "healthy"
        assert "database" in result
        assert result["graph_initialized"] is True

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_health_check_database_failure(self, mock_create_graph, mock_db_manager):
        """测试健康检查（数据库失败）"""
        mock_db_manager.health_check.return_value = {"status": "error", "error": "DB error"}

        service = ChatService()
        result = service.health_check()

        assert result["status"] == "error"

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_health_check_graph_failure(self, mock_create_graph, mock_db_manager):
        """测试健康检查（图创建失败）"""
        mock_db_manager.health_check.return_value = {"status": "healthy"}
        mock_db_manager.create_checkpointer.side_effect = Exception("Graph error")

        service = ChatService()
        result = service.health_check()

        assert result["status"] == "unhealthy"
        assert result["graph_initialized"] is False


@pytest.mark.integration
class TestChatServiceIntegration:
    """ChatService集成测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    def test_full_session_workflow(self, mock_db_manager):
        """测试完整会话工作流"""
        # 模拟数据库管理器
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        service = ChatService()
        user_id = str(uuid.uuid4())

        with patch.object(service, '_create_session_record_directly'):
            # 1. 创建会话
            session_result = service.create_session(user_id, "测试会话")
            session_id = session_result["session_id"]

            # 2. 发送消息
            with patch('src.domains.chat.service.create_chat_graph') as mock_create_graph:
                mock_graph_instance = MagicMock()
                mock_graph_instance.graph.invoke.return_value = {
                    "messages": [HumanMessage(content="Hello"), AIMessage(content="Hi!")]
                }
                mock_create_graph.return_value = mock_graph_instance

                message_result = service.send_message(user_id, session_id, "Hello")

            # 3. 获取历史
            with patch('src.domains.chat.service.create_chat_graph') as mock_create_graph:
                mock_graph_instance = MagicMock()
                mock_graph_instance.graph.get_state.return_value = MagicMock()
                mock_graph_instance.graph.get_state.return_value.values = {
                    "messages": [HumanMessage(content="Hello"), AIMessage(content="Hi!")]
                }
                mock_create_graph.return_value = mock_graph_instance

                history_result = service.get_chat_history(user_id, session_id)

        # 验证工作流
        assert session_result["status"] == "created"
        assert message_result["status"] == "success"
        assert history_result["status"] == "success"
        assert len(history_result["messages"]) == 2


@pytest.mark.performance
class TestChatServicePerformance:
    """ChatService性能测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    def test_multiple_session_creation_performance(self, mock_db_manager):
        """测试批量创建会话性能"""
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        service = ChatService()

        import time
        start_time = time.time()

        with patch.object(service, '_create_session_record_directly'):
            for i in range(10):
                user_id = str(uuid.uuid4())
                service.create_session(user_id, f"会话 {i}")

        duration = time.time() - start_time

        assert duration < 2.0, f"创建10个会话耗时过长: {duration:.3f}s"

    @patch('src.domains.chat.service.chat_db_manager')
    @patch('src.domains.chat.service.create_chat_graph')
    def test_extract_ai_response_performance(self, mock_create_graph, mock_db_manager):
        """测试AI回复提取性能"""
        service = ChatService()

        # 创建大量消息
        messages = []
        for i in range(1000):
            if i % 3 == 0:
                messages.append(HumanMessage(content=f"Human {i}"))
            elif i % 3 == 1:
                messages.append(AIMessage(content=f"AI {i}"))
            else:
                messages.append(ToolMessage(content=f"Tool {i}", tool_call_id=f"tool_{i}"))

        import time
        start_time = time.time()

        response = service._extract_ai_response(messages)

        duration = time.time() - start_time

        assert duration < 0.1, f"提取AI回复耗时过长: {duration:.3f}s"


@pytest.mark.regression
class TestChatServiceRegression:
    """ChatService回归测试"""

    @patch('src.domains.chat.service.chat_db_manager')
    def test_regression_uuid_handling(self, mock_db_manager):
        """回归测试：UUID处理"""
        mock_checkpointer = MagicMock()
        mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
        mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

        service = ChatService()

        # 测试各种UUID格式
        valid_uuids = [
            str(uuid.uuid4()),
            str(uuid.uuid4()).upper(),
            str(uuid.uuid4()).lower()
        ]

        for user_id in valid_uuids:
            for session_id in valid_uuids:
                config = service._create_runnable_config(user_id, session_id)
                assert isinstance(config, dict)
                assert "configurable" in config

    @patch('src.domains.chat.service.chat_db_manager')
    def test_regression_message_content_trimming(self, mock_db_manager):
        """回归测试：消息内容去除空格"""
        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        # 测试各种空格情况
        test_cases = [
            ("", "空字符串"),
            ("   ", "仅空格"),
            ("\t", "仅制表符"),
            ("\n", "仅换行符"),
            ("  \t\n  ", "混合空白字符")
        ]

        for message, desc in test_cases:
            with pytest.raises(ValueError) as exc_info:
                service.send_message(user_id, session_id, message)
            assert "消息内容不能为空" in str(exc_info.value)

    @patch('src.domains.chat.service.chat_db_manager')
    def test_regression_error_message_formatting(self, mock_db_manager):
        """回归测试：错误消息格式"""
        service = ChatService()

        with patch.object(service, '_create_session_record_directly') as mock_create:
            mock_create.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception) as exc_info:
                service.create_session("user123")

            assert "创建会话失败" in str(exc_info.value)
            assert "Database connection failed" in str(exc_info.value)


@pytest.mark.edge_cases
class TestChatServiceEdgeCases:
    """ChatService边界条件测试"""

    def test_very_long_message_content(self):
        """测试非常长的消息内容"""
        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        # 创建超长消息（10KB）
        long_message = "A" * 10000

        with patch('src.domains.chat.service.chat_db_manager') as mock_db_manager:
            mock_checkpointer = MagicMock()
            mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
            mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

            with patch('src.domains.chat.service.create_chat_graph') as mock_create_graph:
                mock_graph_instance = MagicMock()
                mock_graph_instance.graph.invoke.return_value = {"messages": [HumanMessage(content=long_message)]}
                mock_create_graph.return_value = mock_graph_instance

                # 应该能够处理长消息
                result = service.send_message(user_id, session_id, long_message)
                assert result["status"] == "success"

    def test_special_characters_in_message(self):
        """测试消息中的特殊字符"""
        service = ChatService()
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        special_message = "Hello 🌍! 特殊字符测试: αβγ, éèê, 中文, emojis 🚀🎉"

        with patch('src.domains.chat.service.chat_db_manager') as mock_db_manager:
            mock_checkpointer = MagicMock()
            mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
            mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

            with patch('src.domains.chat.service.create_chat_graph') as mock_create_graph:
                mock_graph_instance = MagicMock()
                mock_graph_instance.graph.invoke.return_value = {
                    "messages": [HumanMessage(content=special_message), AIMessage(content="Response")]
                }
                mock_create_graph.return_value = mock_graph_instance

                result = service.send_message(user_id, session_id, special_message)
                assert result["status"] == "success"

    def test_concurrent_session_operations(self):
        """测试并发会话操作"""
        service = ChatService()
        user_id = str(uuid.uuid4())

        import threading
        results = []
        errors = []

        def create_session():
            try:
                with patch('src.domains.chat.service.chat_db_manager') as mock_db_manager:
                    mock_checkpointer = MagicMock()
                    mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer
                    mock_db_manager.create_checkpointer.return_value.__exit__.return_value = None

                    with patch.object(service, '_create_session_record_directly'):
                        result = service.create_session(user_id, f"并发会话 {threading.get_ident()}")
                        results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时创建会话
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_session)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发操作出现错误: {errors}"
        assert len(results) == 5, f"期望5个结果，实际{len(results)}个"

        # 验证所有会话ID都是唯一的
        session_ids = [r["session_id"] for r in results]
        assert len(session_ids) == len(set(session_ids)), "会话ID不唯一"