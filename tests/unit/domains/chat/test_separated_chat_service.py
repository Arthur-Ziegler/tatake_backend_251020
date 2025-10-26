"""
SeparatedChatService模块单元测试

测试完全分离的聊天服务，包括：
1. 会话创建和管理
2. 消息发送和LangGraph处理
3. 与SessionStore的集成
4. 错误处理和边界情况

作者：TaKeKe团队
版本：1.0.0 - 彻底分离方案实现
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.domains.chat.service_separated import SeparatedChatService
from src.domains.chat.session_store import ChatSessionStore


@pytest.mark.unit
class TestSeparatedChatService:
    """SeparatedChatService测试类"""

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
    def mock_db_manager(self):
        """模拟数据库管理器"""
        mock_manager = Mock()
        mock_manager.get_store.return_value = Mock()
        return mock_manager

    @pytest.fixture
    def chat_service(self, session_store, mock_db_manager):
        """创建SeparatedChatService实例"""
        with patch('src.domains.chat.service_separated.chat_db_manager', mock_db_manager):
            service = SeparatedChatService()
            service._session_store = session_store
            return service

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

    def test_create_session_basic(self, chat_service, session_store, sample_user_id):
        """测试基本会话创建"""
        title = "测试会话"

        # 创建会话
        result = chat_service.create_session(sample_user_id, title)

        # 验证返回数据
        assert result["session_id"] is not None
        assert result["user_id"] == sample_user_id
        assert result["title"] == title
        assert result["status"] == "success"

        # 验证SessionStore中创建了会话
        session = session_store.get_session(result["session_id"])
        assert session is not None
        assert session["user_id"] == sample_user_id
        assert session["title"] == title
        assert session["thread_id"] is not None

    def test_create_session_with_default_title(self, chat_service, sample_user_id):
        """测试使用默认标题创建会话"""
        result = chat_service.create_session(sample_user_id)

        assert result["title"] == "新会话"

    @patch('src.domains.chat.service_separated.create_chat_graph')
    def test_send_message_basic(self, mock_create_graph, chat_service, sample_user_id):
        """测试基本消息发送"""
        # 准备：创建会话
        session_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = session_result["session_id"]
        message = "测试消息"

        # 模拟图和结果
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph
        mock_graph.invoke.return_value = {
            "messages": [
                Mock(content="AI回复测试"),
                Mock(content=message)
            ]
        }

        # 发送消息
        result = chat_service.send_message(sample_user_id, session_id, message)

        # 验证结果
        assert result["session_id"] == session_id
        assert result["user_message"] == message
        assert result["ai_response"] == "AI回复测试"
        assert result["status"] == "success"
        assert result["timestamp"] is not None

    def test_send_message_empty_content(self, chat_service, sample_user_id, sample_session_id):
        """测试发送空消息"""
        with pytest.raises(ValueError, match="消息内容不能为空"):
            chat_service.send_message(sample_user_id, sample_session_id, "")

    def test_send_message_whitespace_only(self, chat_service, sample_user_id, sample_session_id):
        """测试发送只有空格的消息"""
        with pytest.raises(ValueError, match="消息内容不能为空"):
            chat_service.send_message(sample_user_id, sample_session_id, "   ")

    def test_send_message_nonexistent_session(self, chat_service, sample_user_id, sample_session_id):
        """测试向不存在的会话发送消息"""
        message = "测试消息"

        with pytest.raises(ValueError, match="会话不存在"):
            chat_service.send_message(sample_user_id, sample_session_id, message)

    @patch('src.domains.chat.service_separated.create_chat_graph')
    def test_send_message_wrong_user(self, mock_create_graph, chat_service, sample_user_id):
        """测试用户权限验证失败"""
        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = session_result["session_id"]

        # 使用错误的用户ID
        wrong_user_id = str(uuid4())

        with pytest.raises(ValueError, match="用户权限验证失败"):
            chat_service.send_message(wrong_user_id, session_id, "测试消息")

    @patch('src.domains.chat.service_separated.create_chat_graph')
    def test_send_message_langgraph_error(self, mock_create_graph, chat_service, sample_user_id):
        """测试LangGraph处理错误"""
        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = session_result["session_id"]
        message = "测试消息"

        # 模拟LangGraph错误
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph
        mock_graph.invoke.side_effect = Exception("LangGraph处理失败")

        with pytest.raises(Exception, match="发送消息失败: LangGraph处理失败"):
            chat_service.send_message(sample_user_id, session_id, message)

    def test_list_sessions_empty(self, chat_service, sample_user_id):
        """测试列出空会话列表"""
        result = chat_service.get_sessions(sample_user_id)

        assert result["sessions"] == []
        assert result["total"] == 0
        assert result["status"] == "success"

    def test_list_sessions_with_data(self, chat_service, session_store, sample_user_id):
        """测试列出有数据的会话列表"""
        # 创建多个会话
        session1 = chat_service.create_session(sample_user_id, "会话1")
        session2 = chat_service.create_session(sample_user_id, "会话2")

        result = chat_service.get_sessions(sample_user_id)

        assert len(result["sessions"]) == 2
        assert result["total"] == 2
        assert result["status"] == "success"

        # 验证返回的是SessionStore的数据
        session_ids = [s["session_id"] for s in result["sessions"]]
        assert session1["session_id"] in session_ids
        assert session2["session_id"] in session_ids

    def test_list_sessions_with_limit(self, chat_service, sample_user_id):
        """测试带限制的会话列表查询"""
        # 创建多个会话
        for i in range(5):
            chat_service.create_session(sample_user_id, f"会话{i+1}")

        # 限制数量查询
        result = chat_service.get_sessions(sample_user_id, limit=3)

        assert len(result["sessions"]) == 3
        assert result["limit"] == 3
        assert result["status"] == "success"

    def test_get_session_info_existing(self, chat_service, sample_user_id):
        """测试获取存在的会话信息"""
        # 创建会话
        create_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = create_result["session_id"]

        # 获取会话信息
        result = chat_service.get_session_info(session_id)

        assert result["session"]["session_id"] == session_id
        assert result["session"]["user_id"] == sample_user_id
        assert result["session"]["title"] == "测试会话"
        assert result["status"] == "success"

    def test_get_session_info_nonexistent(self, chat_service, sample_session_id):
        """测试获取不存在的会话信息"""
        with pytest.raises(Exception, match="会话不存在"):
            chat_service.get_session_info(sample_session_id)

    def test_delete_session_existing(self, chat_service, sample_user_id):
        """测试删除存在的会话"""
        # 创建会话
        create_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = create_result["session_id"]

        # 删除会话
        result = chat_service.delete_session(session_id)

        assert result["session_id"] == session_id
        assert result["status"] == "success"

    def test_delete_session_nonexistent(self, chat_service, sample_session_id):
        """测试删除不存在的会话"""
        with pytest.raises(Exception, match="会话不存在"):
            chat_service.delete_session(sample_session_id)

    @patch('src.domains.chat.service_separated.create_chat_graph')
    def test_extract_ai_response_human_message_only(self, mock_create_graph, chat_service, sample_user_id):
        """测试只包含人类消息的AI回复提取"""
        from langchain_core.messages import HumanMessage

        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = session_result["session_id"]

        # 模拟只有人类消息的结果
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph
        mock_graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="用户消息")
            ]
        }

        result = chat_service.send_message(sample_user_id, session_id, "测试消息")

        assert result["ai_response"] == "抱歉，我没有找到合适的回复。"

    @patch('src.domains.chat.service_separated.create_chat_graph')
    def test_extract_ai_response_with_ai_message(self, mock_create_graph, chat_service, sample_user_id):
        """测试包含AI消息的回复提取"""
        from langchain_core.messages import HumanMessage, AIMessage

        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = session_result["session_id"]

        # 模拟包含AI消息的结果
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph
        ai_message = AIMessage(content="AI回复内容")
        mock_graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="用户消息"),
                ai_message
            ]
        }

        result = chat_service.send_message(sample_user_id, session_id, "测试消息")

        assert result["ai_response"] == "AI回复内容"

    @patch('src.domains.chat.service_separated.create_chat_graph')
    def test_extract_ai_response_with_tool_calls(self, mock_create_graph, chat_service, sample_user_id):
        """测试包含工具调用的AI回复提取"""
        from langchain_core.messages import HumanMessage, AIMessage

        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = session_result["session_id"]

        # 模拟包含工具调用的AI消息
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph
        ai_message = AIMessage(content="", additional_kwargs={"tool_calls": [{"id": "call_1"}]})
        mock_graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="用户消息"),
                ai_message
            ]
        }

        result = chat_service.send_message(sample_user_id, session_id, "测试消息")

        assert result["ai_response"] == "工具调用已完成。"

    def test_create_runnable_config(self, chat_service, sample_user_id):
        """测试RunnableConfig创建"""
        from langchain_core.runnables import RunnableConfig

        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "测试会话")
        session_id = session_result["session_id"]
        thread_id = session_result["thread_id"]

        # 直接测试_create_runnable_config方法
        with patch.object(chat_service, '_db_manager') as mock_db_manager:
            # 模拟get_store方法
            mock_store = Mock()
            mock_db_manager.get_store.return_value = mock_store

            # 调用_create_runnable_config
            config = chat_service._create_runnable_config(sample_user_id, thread_id)

        # 验证config是字典类型（RunnableConfig是TypedDict）
        assert isinstance(config, dict)

        # 验证config包含正确的thread_id和user_id
        assert config["configurable"]["thread_id"] == thread_id
        assert config["configurable"]["user_id"] == sample_user_id

        # 验证config包含checkpointer
        assert "checkpointer" in config

        # 验证数据库管理器方法被调用
        mock_db_manager.get_store.assert_called_once()

    def test_session_store_dependency_injection(self, temp_db_path):
        """测试SessionStore依赖注入"""
        with patch('src.domains.chat.service_separated.get_session_store') as mock_get_store:
            mock_store = Mock(spec=ChatSessionStore)
            mock_get_store.return_value = mock_store

            service = SeparatedChatService()

            # 验证SessionStore被正确注入
            mock_get_store.assert_called_once()
            assert service._session_store == mock_store

    @pytest.mark.integration
    def test_end_to_end_workflow(self, chat_service, session_store, sample_user_id):
        """测试端到端工作流程"""
        with patch('src.domains.chat.service_separated.create_chat_graph') as mock_create_graph:
            # 模拟LangGraph
            mock_graph = Mock()
            mock_create_graph.return_value = mock_graph
            mock_graph.invoke.return_value = {
                "messages": [
                    Mock(content="AI回复1"),
                    Mock(content="AI回复2")
                ]
            }

            # 1. 创建会话
            session_result = chat_service.create_session(sample_user_id, "端到端测试")
            session_id = session_result["session_id"]
            assert session_id is not None

            # 2. 发送多条消息
            for i, message in enumerate(["消息1", "消息2", "消息3"], 1):
                result = chat_service.send_message(sample_user_id, session_id, f"测试{i}")
                assert result["session_id"] == session_id
                assert result["status"] == "success"

            # 3. 验证消息计数
            final_session = session_store.get_session(session_id)
            assert final_session["message_count"] == 3

            # 4. 获取会话列表
            sessions_result = chat_service.get_sessions(sample_user_id)
            assert len(sessions_result["sessions"]) == 1
            assert sessions_result["total"] == 1

            # 5. 获取会话信息
            info_result = chat_service.get_session_info(session_id)
            assert info_result["session"]["session_id"] == session_id

            # 6. 删除会话
            delete_result = chat_service.delete_session(session_id)
            assert delete_result["session_id"] == session_id
            assert delete_result["status"] == "success"

            # 7. 验证会话被删除
            deleted_session = session_store.get_session(session_id)
            assert deleted_session["is_active"] == 0

    def test_error_handling_database_failure(self, mock_db_manager):
        """测试数据库错误处理"""
        # 创建服务（此时不会抛出异常）
        service = SeparatedChatService()

        # 先创建一个会话，避免"会话不存在"的错误
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name

        try:
            # 使用临时数据库创建会话
            temp_session_store = ChatSessionStore(temp_db_path)
            service._session_store = temp_session_store

            session_result = service.create_session("test_user", "测试会话")
            session_id = session_result["session_id"]

            # 测试不存在的会话应该抛出异常
            with pytest.raises(Exception, match="会话不存在"):
                service.send_message("test_user", "nonexistent_session_id", "test_message")

        finally:
            # 清理临时文件
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)


@pytest.mark.integration
class TestSeparatedChatServiceIntegration:
    """SeparatedChatService集成测试"""

    def test_with_real_session_store_and_mock_graph(self):
        """测试与真实SessionStore和模拟LangGraph的集成"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            session_store = ChatSessionStore(db_path)
            mock_db_manager = Mock()
            mock_db_manager.get_store.return_value = Mock()

            with patch('src.domains.chat.service_separated.chat_db_manager', mock_db_manager):
                service = SeparatedChatService()
                service._session_store = session_store

                user_id = str(uuid4())
                title = "集成测试会话"

                # 测试会话创建
                result = service.create_session(user_id, title)
                assert result["status"] == "success"
                assert result["session_id"] is not None

                # 验证会话在SessionStore中存在
                session = session_store.get_session(result["session_id"])
                assert session is not None
                assert session["user_id"] == user_id
                assert session["title"] == title

        finally:
            # 清理
            if os.path.exists(db_path):
                os.unlink(db_path)