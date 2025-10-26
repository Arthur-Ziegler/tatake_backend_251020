"""
Chat图定义单元测试

严格TDD方法：
1. 图构建测试
2. 节点逻辑测试
3. 路由决策测试
4. 配置测试
5. 错误处理测试
6. 模拟测试
7. 边界条件测试

作者：TaTakeKe团队
版本：1.0.0 - Chat图单元测试
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from src.domains.chat.graph import ChatGraph, create_chat_graph


@pytest.mark.unit
class TestChatGraph:
    """ChatGraph类单元测试"""

    @pytest.fixture
    def mock_checkpointer(self):
        """模拟检查点器"""
        mock_cp = MagicMock(spec=SqliteSaver)
        return mock_cp

    @pytest.fixture
    def mock_store(self):
        """模拟内存存储"""
        mock_store = MagicMock(spec=InMemoryStore)
        return mock_store

    @pytest.fixture
    def chat_graph(self, mock_checkpointer, mock_store):
        """创建ChatGraph实例（使用模拟依赖）"""
        with patch('src.domains.chat.graph.StateGraph') as mock_state_graph:
            with patch('src.domains.chat.graph.ToolNode') as mock_tool_node:
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        # 模拟StateGraph
                        mock_builder = MagicMock()
                        mock_state_graph.return_value = mock_builder

                        # 模拟编译后的图
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        graph = ChatGraph(mock_checkpointer, mock_store)
                        graph.graph = mock_compiled_graph
                        return graph

    def test_init_success(self, mock_checkpointer, mock_store):
        """测试成功初始化"""
        with patch('src.domains.chat.graph.StateGraph') as mock_state_graph:
            with patch('src.domains.chat.graph.ToolNode') as mock_tool_node:
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        mock_state_graph.return_value = mock_builder
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        graph = ChatGraph(mock_checkpointer, mock_store)

                        assert graph.checkpointer == mock_checkpointer
                        assert graph.store == mock_store
                        assert graph.graph == mock_compiled_graph

    def test_init_build_graph_called(self, mock_checkpointer, mock_store):
        """测试初始化时构建图"""
        with patch('src.domains.chat.graph.StateGraph') as mock_state_graph:
            with patch('src.domains.chat.graph.ToolNode') as mock_tool_node:
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        mock_state_graph.return_value = mock_builder
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        ChatGraph(mock_checkpointer, mock_store)

                        # 验证图构建方法被调用
                        mock_builder.add_node.assert_called()
                        mock_builder.add_edge.assert_called()
                        mock_builder.add_conditional_edges.assert_called()
                        mock_builder.compile.assert_called()

    def test_build_graph_structure(self, mock_checkpointer, mock_store):
        """测试图结构构建"""
        with patch('src.domains.chat.graph.StateGraph') as mock_state_graph:
            with patch('src.domains.chat.graph.ToolNode') as mock_tool_node:
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        mock_state_graph.return_value = mock_builder
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        graph = ChatGraph(mock_checkpointer, mock_store)
                        # 重置mock调用计数器，因为我们只需要测试_build_graph方法
                        mock_builder.reset_mock()
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        graph._build_graph()

                        # 验证节点添加
                        mock_builder.add_node.assert_any_call("agent", graph._agent_node)
                        mock_builder.add_node.assert_any_call("tools", mock_tool_node.return_value)

                        # 验证边添加
                        mock_builder.add_edge.assert_any_call("START", "agent")
                        mock_builder.add_edge.assert_any_call("tools", "agent")

                        # 验证条件边添加
                        mock_builder.add_conditional_edges.assert_called_once()

    @patch('src.domains.chat.graph.manage_conversation_context')
    @patch('src.domains.chat.graph.format_system_prompt')
    def test_agent_node_with_config(self, mock_format_prompt, mock_manage_context, chat_graph):
        """测试agent节点处理配置"""
        # 设置模拟
        mock_format_prompt.return_value = "系统提示"
        mock_manage_context.return_value = [HumanMessage(content="优化后的消息")]

        # 模拟模型
        mock_model = MagicMock(spec=ChatOpenAI)
        mock_model.model_name = "gpt-3.5-turbo"
        mock_response = AIMessage(content="AI回复")
        mock_model.invoke.return_value = mock_response

        with patch.object(chat_graph, '_get_model', return_value=mock_model):
            # 设置状态 - 使用多条消息以触发上下文管理
            state = {"messages": [HumanMessage(content="消息1"), AIMessage(content="回复1")]}
            config = RunnableConfig(
                configurable={"user_id": "test_user", "thread_id": "test_session"}
            )

            # 调用agent节点
            result = chat_graph._agent_node(state, config)

            # 验证结果
            assert "messages" in result
            assert len(result["messages"]) == 1
            assert result["messages"][0].content == "AI回复"

            # 验证模拟调用
            mock_format_prompt.assert_called_once_with("test_user", "test_session")
            mock_manage_context.assert_called_once()

    def test_agent_node_missing_config(self, chat_graph):
        """测试agent节点缺少配置"""
        state = {"messages": [HumanMessage(content="用户消息")]}
        config = RunnableConfig(configurable={})  # 缺少user_id和thread_id

        with patch.object(chat_graph, '_get_model') as mock_get_model:
            result = chat_graph._agent_node(state, config)

            # 应该返回错误消息
            assert "messages" in result
            assert "遇到了一些问题" in result["messages"][0].content

    @patch('src.domains.chat.graph.format_system_prompt')
    def test_agent_node_with_tool_calls(self, mock_format_prompt, chat_graph):
        """测试agent节点处理工具调用"""
        # 设置模拟
        mock_format_prompt.return_value = "系统提示"

        # 模拟带工具调用的模型
        mock_model = MagicMock(spec=ChatOpenAI)
        mock_model.model_name = "gpt-3.5-turbo"
        mock_response = AIMessage(content="AI回复")
        mock_response.tool_calls = [{"name": "test_tool", "id": "call_123"}]
        mock_model.invoke.return_value = mock_response

        with patch.object(chat_graph, '_get_model', return_value=mock_model):
            state = {"messages": [HumanMessage(content="用户消息")]}
            config = RunnableConfig(
                configurable={"user_id": "test_user", "thread_id": "test_session"}
            )

            result = chat_graph._agent_node(state, config)

            # 验证结果包含工具调用
            assert "messages" in result
            assert len(result["messages"]) == 1

    def test_agent_node_exception_handling(self, chat_graph):
        """测试agent节点异常处理"""
        state = {"messages": [HumanMessage(content="用户消息")]}
        config = RunnableConfig(
            configurable={"user_id": "test_user", "thread_id": "test_session"}
        )

        with patch.object(chat_graph, '_get_model', side_effect=Exception("模型错误")):
            result = chat_graph._agent_node(state, config)

            # 应该返回错误消息
            assert "messages" in result
            assert "遇到了一些问题" in result["messages"][0].content

    def test_route_to_tools_with_tool_calls(self, chat_graph):
        """测试路由到工具节点"""
        # 创建带工具调用的消息
        message = AIMessage(content="AI回复")
        message.tool_calls = [{"name": "test_tool", "id": "call_123"}]

        state = {"messages": [message]}

        result = chat_graph._route_to_tools(state)

        assert result == "tools"

    def test_route_to_tools_without_tool_calls(self, chat_graph):
        """测试路由到结束节点"""
        state = {"messages": [AIMessage(content="AI回复")]}

        result = chat_graph._route_to_tools(state)

        assert result == "end"

    def test_route_to_tools_empty_messages(self, chat_graph):
        """测试空消息列表路由"""
        state = {"messages": []}

        result = chat_graph._route_to_tools(state)

        assert result == "end"

    def test_route_to_tools_exception_handling(self, chat_graph):
        """测试路由异常处理"""
        # 创建会导致异常的状态
        state = {"messages": None}

        result = chat_graph._route_to_tools(state)

        # 异常情况应该路由到结束
        assert result == "end"

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test_api_key",
        "OPENAI_MODEL": "gpt-3.5-turbo",
        "OPENAI_TEMPERATURE": "0.7"
    })
    def test_get_model_success(self):
        """测试成功获取模型"""
        with patch('src.domains.chat.graph.ChatOpenAI') as mock_chat_openai:
            mock_model = MagicMock()
            mock_chat_openai.return_value = mock_model
            # 模拟bind_tools返回值
            mock_bound_model = MagicMock()
            mock_model.bind_tools.return_value = mock_bound_model

            mock_checkpointer = MagicMock()
            mock_store = MagicMock()

            with patch('src.domains.chat.graph.StateGraph'):
                with patch('src.domains.chat.graph.ToolNode'):
                    with patch('src.domains.chat.graph.START', 'START'):
                        with patch('src.domains.chat.graph.END', 'END'):
                            mock_builder = MagicMock()
                            with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                                with patch('src.domains.chat.graph.ToolNode'):
                                    with patch('src.domains.chat.graph.START', 'START'):
                                        with patch('src.domains.chat.graph.END', 'END'):
                                            mock_builder.compile.return_value = MagicMock()
                                            graph = ChatGraph(mock_checkpointer, mock_store)

                                            result = graph._get_model()

                                            # 应该返回bind_tools的结果，而不是原始model
                                            assert result == mock_bound_model
                                            mock_chat_openai.assert_called_once()
                                            mock_model.bind_tools.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_get_model_missing_api_key(self):
        """测试缺少API密钥"""
        mock_checkpointer = MagicMock()
        mock_store = MagicMock()

        with patch('src.domains.chat.graph.StateGraph'):
            with patch('src.domains.chat.graph.ToolNode'):
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                            with patch('src.domains.chat.graph.ToolNode'):
                                with patch('src.domains.chat.graph.START', 'START'):
                                    with patch('src.domains.chat.graph.END', 'END'):
                                        mock_builder.compile.return_value = MagicMock()
                                        graph = ChatGraph(mock_checkpointer, mock_store)

                                        with pytest.raises(ValueError, match="API密钥未设置"):
                                            graph._get_model()

    def test_get_model_exception_handling(self, chat_graph):
        """测试模型创建异常处理"""
        with patch('src.domains.chat.graph.ChatOpenAI', side_effect=Exception("创建失败")):
            with pytest.raises(Exception, match="创建失败"):
                chat_graph._get_model()

    def test_invoke_success(self, chat_graph):
        """测试成功调用图"""
        state = {"messages": [HumanMessage(content="测试")]}
        config = RunnableConfig(configurable={"user_id": "test_user"})

        # 模拟图调用结果
        expected_result = {"messages": [AIMessage(content="回复")]}
        chat_graph.graph.invoke.return_value = expected_result

        result = chat_graph.invoke(state, config)

        assert result == expected_result
        chat_graph.graph.invoke.assert_called_once_with(state, config)

    def test_invoke_graph_not_initialized(self, mock_checkpointer, mock_store):
        """测试图未初始化时的调用"""
        with patch('src.domains.chat.graph.StateGraph'):
            with patch('src.domains.chat.graph.ToolNode'):
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                            with patch('src.domains.chat.graph.ToolNode'):
                                with patch('src.domains.chat.graph.START', 'START'):
                                    with patch('src.domains.chat.graph.END', 'END'):
                                        # 不设置graph属性
                                        graph = ChatGraph.__new__(ChatGraph)
                                        graph.checkpointer = mock_checkpointer
                                        graph.store = mock_store
                                        graph.graph = None

                                        state = {"messages": []}
                                        config = RunnableConfig()

                                        with pytest.raises(RuntimeError, match="聊天图未初始化"):
                                            graph.invoke(state, config)

    def test_stream_success(self, chat_graph):
        """测试成功流式调用"""
        state = {"messages": [HumanMessage(content="测试")]}
        config = RunnableConfig(configurable={"user_id": "test_user"})

        # 模拟流式结果
        mock_chunks = [
            {"messages": [AIMessage(content="回")]},
            {"messages": [AIMessage(content="复")]}
        ]
        chat_graph.graph.stream.return_value = iter(mock_chunks)

        results = list(chat_graph.stream(state, config))

        assert len(results) == 2
        assert results[0]["messages"][0].content == "回"
        assert results[1]["messages"][0].content == "复"

    def test_stream_graph_not_initialized(self, mock_checkpointer, mock_store):
        """测试图未初始化时的流式调用"""
        with patch('src.domains.chat.graph.StateGraph'):
            with patch('src.domains.chat.graph.ToolNode'):
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                            with patch('src.domains.chat.graph.ToolNode'):
                                with patch('src.domains.chat.graph.START', 'START'):
                                    with patch('src.domains.chat.graph.END', 'END'):
                                        graph = ChatGraph.__new__(ChatGraph)
                                        graph.checkpointer = mock_checkpointer
                                        graph.store = mock_store
                                        graph.graph = None

                                        state = {"messages": []}
                                        config = RunnableConfig()

                                        with pytest.raises(RuntimeError, match="聊天图未初始化"):
                                            list(graph.stream(state, config))


@pytest.mark.unit
class TestCreateChatGraph:
    """create_chat_graph函数测试类"""

    @pytest.fixture
    def mock_checkpointer(self):
        """模拟检查点器"""
        return MagicMock(spec=SqliteSaver)

    @pytest.fixture
    def mock_store(self):
        """模拟内存存储"""
        return MagicMock(spec=InMemoryStore)

    def test_create_chat_graph_success(self, mock_checkpointer, mock_store):
        """测试成功创建聊天图"""
        with patch('src.domains.chat.graph.ChatGraph') as mock_chat_graph:
            mock_graph_instance = MagicMock()
            mock_chat_graph.return_value = mock_graph_instance

            result = create_chat_graph(mock_checkpointer, mock_store)

            assert result == mock_graph_instance
            mock_chat_graph.assert_called_once_with(mock_checkpointer, mock_store)

    def test_create_chat_graph_exception(self, mock_checkpointer, mock_store):
        """测试创建聊天图异常"""
        with patch('src.domains.chat.graph.ChatGraph', side_effect=Exception("创建失败")):
            with pytest.raises(Exception, match="创建失败"):
                create_chat_graph(mock_checkpointer, mock_store)


@pytest.mark.integration
class TestChatGraphIntegration:
    """ChatGraph集成测试类"""

    @pytest.fixture
    def mock_checkpointer(self):
        """模拟检查点器"""
        return MagicMock(spec=SqliteSaver)

    @pytest.fixture
    def mock_store(self):
        """模拟内存存储"""
        return MagicMock(spec=InMemoryStore)

    def test_complete_workflow_simulation(self, mock_checkpointer, mock_store):
        """测试完整工作流程模拟"""
        with patch('src.domains.chat.graph.StateGraph') as mock_state_graph:
            with patch('src.domains.chat.graph.ToolNode') as mock_tool_node:
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        # 设置模拟
                        mock_builder = MagicMock()
                        mock_state_graph.return_value = mock_builder
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        # 创建图
                        graph = ChatGraph(mock_checkpointer, mock_store)

                        # 模拟完整对话流程
                        state = {"messages": [HumanMessage(content="你好")]}
                        config = RunnableConfig(
                            configurable={"user_id": "test_user", "thread_id": "test_session"}
                        )

                        # 模拟agent节点处理
                        with patch.object(graph, '_get_model') as mock_get_model:
                            mock_model = MagicMock()
                            mock_model.model_name = "gpt-3.5-turbo"
                            mock_response = AIMessage(content="你好！有什么可以帮助你的吗？")
                            mock_model.invoke.return_value = mock_response
                            mock_get_model.return_value = mock_model

                            with patch('src.domains.chat.graph.format_system_prompt'):
                                with patch('src.domains.chat.graph.manage_conversation_context'):
                                    agent_result = graph._agent_node(state, config)

                                    # 模拟路由决策
                                    route_result = graph._route_to_tools(agent_result)

                                    # 验证流程
                                    assert route_result == "end"
                                    assert "messages" in agent_result

    def test_tool_call_workflow_simulation(self, mock_checkpointer, mock_store):
        """测试工具调用工作流程模拟"""
        with patch('src.domains.chat.graph.StateGraph') as mock_state_graph:
            with patch('src.domains.chat.graph.ToolNode') as mock_tool_node:
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        mock_state_graph.return_value = mock_builder
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        graph = ChatGraph(mock_checkpointer, mock_store)

                        # 创建带工具调用的状态
                        message = AIMessage(content="我需要查询任务")
                        message.tool_calls = [{"name": "query_tasks", "id": "call_123"}]

                        state = {"messages": [message]}

                        # 测试路由
                        route_result = graph._route_to_tools(state)

                        # 应该路由到工具节点
                        assert route_result == "tools"

    def test_error_handling_workflow(self, mock_checkpointer, mock_store):
        """测试错误处理工作流程"""
        with patch('src.domains.chat.graph.StateGraph') as mock_state_graph:
            with patch('src.domains.chat.graph.ToolNode') as mock_tool_node:
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        mock_state_graph.return_value = mock_builder
                        mock_compiled_graph = MagicMock()
                        mock_builder.compile.return_value = mock_compiled_graph

                        graph = ChatGraph(mock_checkpointer, mock_store)

                        # 测试各种错误情况
                        error_cases = [
                            {"messages": None},  # 无效消息
                            {"messages": []},   # 空消息列表
                            {},               # 缺少messages字段
                        ]

                        for error_state in error_cases:
                            route_result = graph._route_to_tools(error_state)
                            assert route_result == "end"  # 错误情况应该结束


@pytest.mark.performance
class TestChatGraphPerformance:
    """ChatGraph性能测试类"""

    def test_route_decision_performance(self):
        """测试路由决策性能"""
        import time

        mock_checkpointer = MagicMock()
        mock_store = MagicMock()

        with patch('src.domains.chat.graph.StateGraph'):
            with patch('src.domains.chat.graph.ToolNode'):
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                            with patch('src.domains.chat.graph.ToolNode'):
                                with patch('src.domains.chat.graph.START', 'START'):
                                    with patch('src.domains.chat.graph.END', 'END'):
                                        mock_builder.compile.return_value = MagicMock()
                                        graph = ChatGraph(mock_checkpointer, mock_store)

                                        # 创建测试状态
                                        states = [
                                            {"messages": [AIMessage(content=f"消息{i}")]}
                                            for i in range(1000)
                                        ]

                                        start_time = time.time()
                                        for state in states:
                                            graph._route_to_tools(state)
                                        duration = time.time() - start_time

                                        # 应该在合理时间内完成
                                        assert duration < 1.0, f"路由决策性能不达标: {duration:.3f}秒"

    def test_model_creation_performance(self):
        """测试模型创建性能"""
        import time

        mock_checkpointer = MagicMock()
        mock_store = MagicMock()

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test_key",
            "OPENAI_MODEL": "gpt-3.5-turbo"
        }):
            with patch('src.domains.chat.graph.StateGraph'):
                with patch('src.domains.chat.graph.ToolNode'):
                    with patch('src.domains.chat.graph.START', 'START'):
                        with patch('src.domains.chat.graph.END', 'END'):
                            mock_builder = MagicMock()
                            with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                                with patch('src.domains.chat.graph.ToolNode'):
                                    with patch('src.domains.chat.graph.START', 'START'):
                                        with patch('src.domains.chat.graph.END', 'END'):
                                            mock_builder.compile.return_value = MagicMock()
                                            graph = ChatGraph(mock_checkpointer, mock_store)

                                            start_time = time.time()
                                            for _ in range(100):
                                                try:
                                                    graph._get_model()
                                                except:
                                                    pass
                                            duration = time.time() - start_time

                                            # 应该在合理时间内完成
                                            assert duration < 2.0, f"模型创建性能不达标: {duration:.3f}秒"


@pytest.mark.regression
class TestChatGraphRegression:
    """ChatGraph回归测试类"""

    def test_regression_config_validation(self):
        """回归测试：配置验证"""
        mock_checkpointer = MagicMock()
        mock_store = MagicMock()

        with patch('src.domains.chat.graph.StateGraph'):
            with patch('src.domains.chat.graph.ToolNode'):
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                            with patch('src.domains.chat.graph.ToolNode'):
                                with patch('src.domains.chat.graph.START', 'START'):
                                    with patch('src.domains.chat.graph.END', 'END'):
                                        mock_builder.compile.return_value = MagicMock()
                                        graph = ChatGraph(mock_checkpointer, mock_store)

                                        # 测试各种配置情况
                                        state = {"messages": [HumanMessage(content="测试")]}

                                        # 缺少配置
                                        config1 = RunnableConfig()
                                        config2 = RunnableConfig(configurable={})
                                        config3 = RunnableConfig(configurable={"user_id": ""})
                                        config4 = RunnableConfig(configurable={"thread_id": ""})

                                        for config in [config1, config2, config3, config4]:
                                            with patch.object(graph, '_get_model'):
                                                result = graph._agent_node(state, config)
                                                # 应该返回错误消息
                                                assert "messages" in result
                                                assert "遇到了一些问题" in result["messages"][0].content

    def test_regression_message_handling(self):
        """回归测试：消息处理"""
        mock_checkpointer = MagicMock()
        mock_store = MagicMock()

        with patch('src.domains.chat.graph.StateGraph'):
            with patch('src.domains.chat.graph.ToolNode'):
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                            with patch('src.domains.chat.graph.ToolNode'):
                                with patch('src.domains.chat.graph.START', 'START'):
                                    with patch('src.domains.chat.graph.END', 'END'):
                                        mock_builder.compile.return_value = MagicMock()
                                        graph = ChatGraph(mock_checkpointer, mock_store)

                                        # 测试各种消息类型
                                        message_types = [
                                            HumanMessage(content="用户消息"),
                                            AIMessage(content="AI回复"),
                                            SystemMessage(content="系统提示"),
                                        ]

                                        for message in message_types:
                                            state = {"messages": [message]}
                                            result = graph._route_to_tools(state)
                                            assert result in ["tools", "end"]

    def test_regression_tool_call_detection(self):
        """回归测试：工具调用检测"""
        mock_checkpointer = MagicMock()
        mock_store = MagicMock()

        with patch('src.domains.chat.graph.StateGraph'):
            with patch('src.domains.chat.graph.ToolNode'):
                with patch('src.domains.chat.graph.START', 'START'):
                    with patch('src.domains.chat.graph.END', 'END'):
                        mock_builder = MagicMock()
                        with patch('src.domains.chat.graph.StateGraph', return_value=mock_builder):
                            with patch('src.domains.chat.graph.ToolNode'):
                                with patch('src.domains.chat.graph.START', 'START'):
                                    with patch('src.domains.chat.graph.END', 'END'):
                                        mock_builder.compile.return_value = MagicMock()
                                        graph = ChatGraph(mock_checkpointer, mock_store)

                                        # 测试工具调用检测
                                        normal_message = AIMessage(content="正常回复")
                                        tool_message = AIMessage(content="工具调用")
                                        tool_message.tool_calls = [{"name": "test_tool"}]

                                        state1 = {"messages": [normal_message]}
                                        state2 = {"messages": [tool_message]}

                                        result1 = graph._route_to_tools(state1)
                                        result2 = graph._route_to_tools(state2)

                                        assert result1 == "end"
                                        assert result2 == "tools"