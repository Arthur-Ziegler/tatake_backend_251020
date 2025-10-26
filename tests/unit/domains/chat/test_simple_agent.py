"""
SimpleChatAgent单元测试

严格TDD方法：
1. 测试驱动开发
2. 98%+测试覆盖率
3. 边界条件测试
4. 错误处理测试
5. 性能测试

作者：TaKeKe团队
版本：1.0.0 - 全面单元测试
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.domains.chat.simple_agent import SimpleChatAgent
from src.domains.chat.simple_database import ChatDatabaseManager
from src.domains.chat.simple_state import MessageMetadata, SessionInfo


@pytest.mark.unit
class TestSimpleChatAgent:
    """SimpleChatAgent单元测试类"""

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
    def mock_model(self):
        """模拟聊天模型"""
        model = Mock()
        model.invoke = Mock()
        return model

    @pytest.fixture
    def simple_agent(self, mock_model, temp_db_path):
        """创建SimpleChatAgent实例"""
        return SimpleChatAgent(mock_model, temp_db_path)

    @pytest.fixture
    def sample_user_id(self):
        """提供测试用户ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_session_id(self):
        """提供测试会话ID"""
        return str(uuid4())

    def test_init_success(self, mock_model, temp_db_path):
        """测试成功初始化"""
        agent = SimpleChatAgent(mock_model, temp_db_path)

        assert agent._model == mock_model
        assert agent._db_manager is not None
        assert agent._store is not None
        assert agent._tools == []
        assert agent._agent is None

    def test_init_failure(self):
        """测试初始化失败"""
        with patch('src.domains.chat.simple_agent.ChatDatabaseManager') as mock_db:
            mock_db.side_effect = Exception("数据库初始化失败")

            with pytest.raises(Exception) as exc_info:
                SimpleChatAgent(Mock(), "invalid_path")

            assert "SimpleChatAgent初始化失败" in str(exc_info.value)

    def test_create_agent_success(self, simple_agent):
        """测试代理创建成功"""
        with patch('src.domains.chat.simple_agent.create_react_agent') as mock_create:
            mock_agent = Mock()
            mock_create.return_value = mock_agent

            result = simple_agent._create_agent()

            assert result == mock_agent
            assert simple_agent._agent == mock_agent
            mock_create.assert_called_once_with(
                simple_agent._model,
                tools=[],
                prompt="你是一个有用的AI助手。请用简洁、友好的方式回答用户问题。"
            )

    def test_create_agent_cached(self, simple_agent):
        """测试代理创建缓存"""
        # 设置缓存的代理
        cached_agent = Mock()
        simple_agent._agent = cached_agent

        result = simple_agent._create_agent()

        assert result == cached_agent

    def test_create_agent_failure(self, simple_agent):
        """测试代理创建失败"""
        with patch('src.domains.chat.simple_agent.create_react_agent') as mock_create:
            mock_create.side_effect = Exception("代理创建失败")

            with pytest.raises(Exception) as exc_info:
                simple_agent._create_agent()

            assert "ReAct代理创建失败" in str(exc_info.value)

    def test_create_config_success(self, simple_agent, sample_user_id, sample_session_id):
        """测试配置创建成功"""
        config = simple_agent._create_config(sample_user_id, sample_session_id)

        expected_config = {
            "configurable": {
                "thread_id": sample_session_id,
                "user_id": sample_user_id
            }
        }

        assert config == expected_config

    def test_create_config_validation(self, simple_agent):
        """测试配置创建参数验证"""
        # 测试空user_id
        with pytest.raises(ValueError) as exc_info:
            simple_agent._create_config("", "session123")
        assert "user_id必须是非空字符串" in str(exc_info.value)

        # 测试None user_id
        with pytest.raises(ValueError) as exc_info:
            simple_agent._create_config(None, "session123")
        assert "user_id必须是非空字符串" in str(exc_info.value)

        # 测试空session_id
        with pytest.raises(ValueError) as exc_info:
            simple_agent._create_config("user123", "")
        assert "session_id必须是非空字符串" in str(exc_info.value)

        # 测试None session_id
        with pytest.raises(ValueError) as exc_info:
            simple_agent._create_config("user123", None)
        assert "session_id必须是非空字符串" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_success(self, simple_agent, sample_user_id, sample_session_id):
        """测试消息发送成功"""
        # 模拟数据库操作
        with patch.object(simple_agent._db_manager, 'get_recent_messages') as mock_get:
            mock_get.return_value = []

            with patch.object(simple_agent._db_manager, 'save_message') as mock_save:
                mock_save.return_value = "msg123"

                # 模拟代理响应
                with patch('src.domains.chat.simple_agent.create_react_agent') as mock_create:
                    mock_agent = Mock()
                    from langchain_core.messages import AIMessage
                    mock_agent.invoke.return_value = {
                        "messages": [AIMessage(content="AI回复")]
                    }
                    mock_create.return_value = mock_agent

                    result = await simple_agent.send_message(
                        sample_user_id,
                        sample_session_id,
                        "测试消息"
                    )

                    assert result["status"] == "success"
                    assert result["user_id"] == sample_user_id
                    assert result["session_id"] == sample_session_id
                    assert result["user_message"] == "测试消息"
                    assert result["ai_response"] == "AI回复"
                    assert "timestamp" in result

                    # 验证数据库调用
                    assert mock_get.call_count == 1
                    assert mock_save.call_count == 2  # 保存用户消息和AI回复

    @pytest.mark.asyncio
    async def test_send_message_validation(self, simple_agent):
        """测试消息发送参数验证"""
        # 测试空消息
        with pytest.raises(ValueError) as exc_info:
            await simple_agent.send_message("user123", "session123", "")
        assert "消息内容不能为空" in str(exc_info.value)

        # 测试None消息
        with pytest.raises(ValueError) as exc_info:
            await simple_agent.send_message("user123", "session123", None)
        assert "消息内容不能为空" in str(exc_info.value)

        # 测试空用户ID
        with pytest.raises(ValueError) as exc_info:
            await simple_agent.send_message("", "session123", "消息")
        assert "用户ID和会话ID不能为空" in str(exc_info.value)

        # 测试空会话ID
        with pytest.raises(ValueError) as exc_info:
            await simple_agent.send_message("user123", "", "消息")
        assert "用户ID和会话ID不能为空" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_with_history(self, simple_agent, sample_user_id, sample_session_id):
        """测试带历史消息的消息发送"""
        # 模拟历史消息
        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"}
        ]

        with patch.object(simple_agent._db_manager, 'get_recent_messages') as mock_get:
            mock_get.return_value = history

            with patch.object(simple_agent._db_manager, 'save_message') as mock_save:
                mock_save.return_value = "msg123"

                with patch('src.domains.chat.simple_agent.create_react_agent') as mock_create:
                    mock_agent = Mock()
                    from langchain_core.messages import AIMessage
                    mock_agent.invoke.return_value = {
                        "messages": [AIMessage(content="新的AI回复")]
                    }
                    mock_create.return_value = mock_agent

                    result = await simple_agent.send_message(
                        sample_user_id,
                        sample_session_id,
                        "新的问题"
                    )

                    # 验证历史消息被正确传递
                    mock_agent.invoke.assert_called_once()
                    call_args = mock_agent.invoke.call_args
                    messages = call_args[0][0]["messages"]

                    # 应该有3条消息：历史2条 + 当前用户1条（agent.invoke的输入）
                    assert len(messages) == 3

                    # 验证消息内容
                    from langchain_core.messages import HumanMessage, AIMessage
                    assert isinstance(messages[0], HumanMessage)
                    assert messages[0].content == "之前的问题"
                    assert isinstance(messages[1], AIMessage)
                    assert messages[1].content == "之前的回答"
                    assert isinstance(messages[2], HumanMessage)
                    assert messages[2].content == "新的问题"

    @pytest.mark.asyncio
    async def test_send_message_agent_failure(self, simple_agent, sample_user_id, sample_session_id):
        """测试代理调用失败"""
        with patch.object(simple_agent._db_manager, 'get_recent_messages') as mock_get:
            mock_get.return_value = []

            with patch('src.domains.chat.simple_agent.create_react_agent') as mock_create:
                mock_agent = Mock()
                mock_agent.invoke.side_effect = Exception("代理调用失败")
                mock_create.return_value = mock_agent

                with pytest.raises(Exception) as exc_info:
                    await simple_agent.send_message(
                        sample_user_id,
                        sample_session_id,
                        "测试消息"
                    )

                assert "消息处理失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_message_history_success(self, simple_agent, sample_session_id):
        """测试获取消息历史成功"""
        expected_messages = [
            {"role": "user", "content": "消息1"},
            {"role": "assistant", "content": "回复1"}
        ]

        with patch.object(simple_agent._db_manager, 'get_recent_messages') as mock_get:
            mock_get.return_value = expected_messages

            result = await simple_agent.get_message_history(sample_session_id)

            assert result["status"] == "success"
            assert result["session_id"] == sample_session_id
            assert result["messages"] == expected_messages
            assert result["total"] == 2
            assert result["limit"] == 50  # 默认值
            assert result["offset"] == 0  # 默认值

    @pytest.mark.asyncio
    async def test_get_message_history_validation(self, simple_agent):
        """测试获取消息历史参数验证"""
        # 测试空会话ID
        with pytest.raises(ValueError) as exc_info:
            await simple_agent.get_message_history("")
        assert "会话ID不能为空" in str(exc_info.value)

        # 测试无效limit
        with pytest.raises(ValueError) as exc_info:
            await simple_agent.get_message_history("session123", limit=0)
        assert "limit必须在1-100之间" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            await simple_agent.get_message_history("session123", limit=101)
        assert "limit必须在1-100之间" in str(exc_info.value)

        # 测试无效offset
        with pytest.raises(ValueError) as exc_info:
            await simple_agent.get_message_history("session123", offset=-1)
        assert "offset不能为负数" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_clear_session_success(self, simple_agent, sample_session_id):
        """测试清除会话成功"""
        with patch.object(simple_agent._db_manager, 'clear_session_messages') as mock_clear:
            mock_clear.return_value = True

            result = await simple_agent.clear_session(sample_session_id)

            assert result["status"] == "success"
            assert result["session_id"] == sample_session_id
            assert "cleared_at" in result
            mock_clear.assert_called_once_with(sample_session_id)

    @pytest.mark.asyncio
    async def test_clear_session_failure(self, simple_agent, sample_session_id):
        """测试清除会话失败"""
        with patch.object(simple_agent._db_manager, 'clear_session_messages') as mock_clear:
            mock_clear.return_value = False

            with pytest.raises(Exception) as exc_info:
                await simple_agent.clear_session(sample_session_id)

            assert "清除会话失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_session_stats_success(self, simple_agent, sample_session_id):
        """测试获取会话统计成功"""
        expected_stats = {
            "message_count": 10,
            "last_message_at": datetime.now(timezone.utc).isoformat()
        }

        with patch.object(simple_agent._db_manager, 'get_session_stats') as mock_stats:
            mock_stats.return_value = expected_stats

            result = await simple_agent.get_session_stats(sample_session_id)

            assert result["status"] == "success"
            assert result["session_id"] == sample_session_id
            assert result["message_count"] == 10
            assert result["last_message_at"] == expected_stats["last_message_at"]
            mock_stats.assert_called_once_with(sample_session_id)

    def test_add_tool_success(self, simple_agent):
        """测试添加工具成功"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"

        simple_agent.add_tool(mock_tool)

        assert mock_tool in simple_agent._tools
        assert simple_agent._agent is None  # 代理应该被重置

    def test_add_tool_validation(self, simple_agent):
        """测试添加工具参数验证"""
        # 测试缺少name属性
        invalid_tool1 = Mock()
        del invalid_tool1.name

        with pytest.raises(ValueError) as exc_info:
            simple_agent.add_tool(invalid_tool1)
        assert "工具必须具有name和description属性" in str(exc_info.value)

        # 测试缺少description属性
        invalid_tool2 = Mock()
        invalid_tool2.name = "test"
        del invalid_tool2.description

        with pytest.raises(ValueError) as exc_info:
            simple_agent.add_tool(invalid_tool2)
        assert "工具必须具有name和description属性" in str(exc_info.value)

    def test_get_tool_count(self, simple_agent):
        """测试获取工具数量"""
        assert simple_agent.get_tool_count() == 0

        mock_tool = Mock()
        mock_tool.name = "test"
        mock_tool.description = "测试工具"
        simple_agent.add_tool(mock_tool)

        assert simple_agent.get_tool_count() == 1

    def test_is_agent_ready(self, simple_agent):
        """测试代理就绪状态"""
        # 初始状态
        assert not simple_agent.is_agent_ready()

        # 创建代理后
        simple_agent._agent = Mock()
        assert simple_agent.is_agent_ready()

    @pytest.mark.performance
    def test_performance_message_creation(self, simple_agent):
        """测试消息创建性能"""
        import time

        # 测试大量配置创建的性能
        start_time = time.time()
        for _ in range(1000):
            config = simple_agent._create_config("user123", "session123")
        end_time = time.time()

        execution_time = end_time - start_time
        assert execution_time < 0.1, f"配置创建性能不达标，耗时: {execution_time:.3f}秒"

    @pytest.mark.integration
    def test_integration_full_workflow(self, simple_agent, sample_user_id, sample_session_id):
        """集成测试：完整工作流"""
        async def run_workflow():
            # 1. 发送消息
            with patch.object(simple_agent._db_manager, 'get_recent_messages') as mock_get:
                mock_get.return_value = []

                with patch.object(simple_agent._db_manager, 'save_message') as mock_save:
                    mock_save.return_value = "msg123"

                    with patch('src.domains.chat.simple_agent.create_react_agent') as mock_create:
                        mock_agent = Mock()
                        from langchain_core.messages import AIMessage
                        mock_agent.invoke.return_value = {
                            "messages": [AIMessage(content="AI回复")]
                        }
                        mock_create.return_value = mock_agent

                        # 发送消息
                        result1 = await simple_agent.send_message(
                            sample_user_id,
                            sample_session_id,
                            "第一个消息"
                        )
                        assert result1["status"] == "success"

                        # 2. 获取历史
                        with patch.object(simple_agent._db_manager, 'get_recent_messages') as mock_get_history:
                            mock_get_history.return_value = [
                                {"role": "user", "content": "第一个消息"},
                                {"role": "assistant", "content": "AI回复"}
                            ]

                            result2 = await simple_agent.get_message_history(sample_session_id)
                            assert result2["status"] == "success"
                            assert len(result2["messages"]) == 2

                        # 3. 获取统计
                        with patch.object(simple_agent._db_manager, 'get_session_stats') as mock_stats:
                            mock_stats.return_value = {"message_count": 2}

                            result3 = await simple_agent.get_session_stats(sample_session_id)
                            assert result3["status"] == "success"
                            assert result3["message_count"] == 2

        # 运行集成测试
        asyncio.run(run_workflow())


@pytest.mark.regression
class TestSimpleChatAgentRegression:
    """SimpleChatAgent回归测试"""

    def test_regression_empty_message_handling(self):
        """回归测试：空消息处理"""
        agent = SimpleChatAgent(Mock(), ":memory:")

        async def test_empty_message():
            with pytest.raises(ValueError) as exc_info:
                await agent.send_message("user123", "session123", "   ")
            assert "消息内容不能为空" in str(exc_info.value)

        asyncio.run(test_empty_message())

    def test_regression_config_isolation(self):
        """回归测试：配置隔离"""
        agent = SimpleChatAgent(Mock(), ":memory:")

        config1 = agent._create_config("user1", "session1")
        config2 = agent._create_config("user2", "session2")

        assert config1["configurable"]["user_id"] != config2["configurable"]["user_id"]
        assert config1["configurable"]["thread_id"] != config2["configurable"]["thread_id"]