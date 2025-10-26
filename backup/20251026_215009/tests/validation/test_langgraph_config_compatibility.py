"""
LangGraph 配置兼容性测试

专门检测 SeparatedChatService 与 LangGraph Agent 节点的配置兼容性问题
确保传递给 LangGraph 的配置包含所有必需的参数

作者：TaKeKe团队
版本：1.0.0 - 配置兼容性专项测试
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from uuid import uuid4

from src.domains.chat.service_separated import SeparatedChatService
from src.domains.chat.session_store import ChatSessionStore


@pytest.mark.unit
class TestLangGraphConfigCompatibility:
    """LangGraph 配置兼容性测试类"""

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

    def test_create_runnable_config_contains_user_id(self, chat_service, sample_user_id):
        """测试_runnable_config 包含必需的 user_id 参数"""
        thread_id = str(uuid4())

        # 调用配置创建方法
        config = chat_service._create_runnable_config(sample_user_id, thread_id)

        # 验证配置结构
        assert "configurable" in config
        assert "checkpointer" in config

        # 验证必需的参数存在
        configurable = config["configurable"]
        assert "user_id" in configurable, "configurable 中必须包含 user_id"
        assert "thread_id" in configurable, "configurable 中必须包含 thread_id"

        # 验证参数值正确
        assert configurable["user_id"] == sample_user_id
        assert configurable["thread_id"] == thread_id

    def test_create_runnable_config_missing_user_id_raises_error(self, chat_service):
        """测试缺少 user_id 参数时是否正确处理"""
        thread_id = str(uuid4())

        # 检查方法签名要求 user_id 参数
        import inspect
        sig = inspect.signature(chat_service._create_runnable_config)
        params = sig.parameters

        assert "user_id" in params, "方法签名必须包含 user_id 参数"
        assert "thread_id" in params, "方法签名必须包含 thread_id 参数"

    def test_send_message_config_flow(self, chat_service, sample_user_id):
        """测试完整的消息发送配置流程"""
        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "配置测试会话")
        session_id = session_result["session_id"]

        # 模拟 LangGraph 处理以捕获配置
        captured_config = None

        def mock_graph_invoke(state, config):
            nonlocal captured_config
            captured_config = config
            # 返回模拟结果
            from langchain_core.messages import AIMessage
            return {"messages": [AIMessage(content="测试回复")]}

        # 模拟图创建和调用
        with patch('src.domains.chat.service_separated.create_chat_graph') as mock_create_graph:
            mock_graph = Mock()
            mock_graph.invoke.side_effect = mock_graph_invoke
            mock_create_graph.return_value = mock_graph

            # 发送消息
            result = chat_service.send_message(
                user_id=sample_user_id,
                session_id=session_id,
                message="测试配置传递"
            )

            # 验证配置被正确传递
            assert captured_config is not None, "配置必须传递给 LangGraph"
            assert "configurable" in captured_config, "配置必须包含 configurable"

            configurable = captured_config["configurable"]
            assert "user_id" in configurable, "传递给 LangGraph 的配置必须包含 user_id"
            assert "thread_id" in configurable, "传递给 LangGraph 的配置必须包含 thread_id"

            assert configurable["user_id"] == sample_user_id, "user_id 必须正确传递"
            assert configurable["thread_id"] == session_result["thread_id"], "thread_id 必须正确传递"

    def test_config_validation_compatibility_with_agent_node(self, chat_service, sample_user_id):
        """测试配置与 Agent 节点要求的兼容性"""
        thread_id = str(uuid4())

        # 创建配置
        config = chat_service._create_runnable_config(sample_user_id, thread_id)

        # 模拟 Agent 节点的配置检查逻辑
        def check_agent_node_compatibility(cfg):
            """模拟 Agent 节点的配置验证逻辑"""
            user_id = cfg.get("configurable", {}).get("user_id")
            session_id = cfg.get("configurable", {}).get("thread_id")

            if not user_id or not session_id:
                raise ValueError("缺少user_id或thread_id配置")

            return True

        # 验证配置兼容性
        try:
            is_compatible = check_agent_node_compatibility(config)
            assert is_compatible, "配置必须与 Agent 节点兼容"
        except ValueError as e:
            pytest.fail(f"配置与 Agent 节点不兼容: {e}")

    def test_config_parameter_types(self, chat_service, sample_user_id):
        """测试配置参数类型正确性"""
        thread_id = str(uuid4())

        config = chat_service._create_runnable_config(sample_user_id, thread_id)
        configurable = config["configurable"]

        # 验证参数类型
        assert isinstance(configurable["user_id"], str), "user_id 必须是字符串类型"
        assert isinstance(configurable["thread_id"], str), "thread_id 必须是字符串类型"

        # 验证参数不为空
        assert configurable["user_id"].strip() != "", "user_id 不能为空字符串"
        assert configurable["thread_id"].strip() != "", "thread_id 不能为空字符串"

    def test_error_handling_invalid_user_id(self, chat_service):
        """测试无效 user_id 的错误处理"""
        thread_id = str(uuid4())

        # 测试空字符串
        with pytest.raises((ValueError, AssertionError)):
            config = chat_service._create_runnable_config("", thread_id)
            if config["configurable"]["user_id"].strip() == "":
                raise ValueError("user_id 不能为空")

        # 测试 None
        with pytest.raises((TypeError, ValueError)):
            config = chat_service._create_runnable_config(None, thread_id)

    @pytest.mark.integration
    def test_end_to_end_config_integration(self, chat_service, sample_user_id):
        """端到端配置集成测试"""
        # 创建会话
        session_result = chat_service.create_session(sample_user_id, "端到端配置测试")
        session_id = session_result["session_id"]

        # 捕获所有传递给 LangGraph 的配置
        captured_configs = []

        def mock_graph_invoke(state, config):
            captured_configs.append(config.copy())
            from langchain_core.messages import AIMessage
            return {"messages": [AIMessage(content="端到端测试成功")]}

        with patch('src.domains.chat.service_separated.create_chat_graph') as mock_create_graph:
            mock_graph = Mock()
            mock_graph.invoke.side_effect = mock_graph_invoke
            mock_create_graph.return_value = mock_graph

            # 发送多条消息
            messages = [
                "第一条测试消息",
                "第二条测试消息",
                "第三条测试消息"
            ]

            for i, message in enumerate(messages, 1):
                result = chat_service.send_message(
                    user_id=sample_user_id,
                    session_id=session_id,
                    message=message
                )

                # 验证每次调用的配置都正确
                assert len(captured_configs) == i, f"第 {i} 次调用应该产生配置"

                current_config = captured_configs[-1]
                assert current_config["configurable"]["user_id"] == sample_user_id
                assert current_config["configurable"]["thread_id"] == session_result["thread_id"]

                # 验证配置在多次调用间保持一致性
                if i > 1:
                    assert captured_configs[-2]["configurable"]["user_id"] == current_config["configurable"]["user_id"]
                    assert captured_configs[-2]["configurable"]["thread_id"] == current_config["configurable"]["thread_id"]

    def test_config_isolation_between_users(self, chat_service):
        """测试不同用户间的配置隔离"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        thread_id1 = str(uuid4())
        thread_id2 = str(uuid4())

        # 创建不同用户的配置
        config1 = chat_service._create_runnable_config(user1_id, thread_id1)
        config2 = chat_service._create_runnable_config(user2_id, thread_id2)

        # 验证配置隔离
        assert config1["configurable"]["user_id"] != config2["configurable"]["user_id"]
        assert config1["configurable"]["thread_id"] != config2["configurable"]["thread_id"]

        # 验证每个配置都包含正确的用户信息
        assert config1["configurable"]["user_id"] == user1_id
        assert config2["configurable"]["user_id"] == user2_id

    @pytest.mark.performance
    def test_config_creation_performance(self, chat_service, sample_user_id):
        """测试配置创建性能"""
        import time

        thread_id = str(uuid4())

        # 测试多次配置创建的性能
        start_time = time.time()
        for _ in range(100):
            config = chat_service._create_runnable_config(sample_user_id, thread_id)
        end_time = time.time()

        # 验证性能要求（100次创建应该在1秒内完成）
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"配置创建性能不达标，耗时: {execution_time:.3f}秒"

        # 验证所有配置都正确
        config = chat_service._create_runnable_config(sample_user_id, thread_id)
        assert config["configurable"]["user_id"] == sample_user_id
        assert config["configurable"]["thread_id"] == thread_id


@pytest.mark.regression
class TestRegressionConfigIssues:
    """回归测试：防止配置问题重现"""

    def test_regression_missing_user_id_in_config(self):
        """回归测试：防止配置中缺少 user_id 的问题重现"""
        service = SeparatedChatService()

        # 验证方法签名包含必需参数
        import inspect
        sig = inspect.signature(service._create_runnable_config)

        required_params = [name for name, param in sig.parameters.items()
                          if param.default == inspect.Parameter.empty]

        assert "user_id" in required_params, "user_id 必须是必需参数"
        assert "thread_id" in required_params, "thread_id 必须是必需参数"

    def test_regression_config_pass_to_langgraph(self):
        """回归测试：防止配置未正确传递给 LangGraph 的问题"""
        service = SeparatedChatService()
        user_id = str(uuid4())
        thread_id = str(uuid4())

        # 创建配置
        config = service._create_runnable_config(user_id, thread_id)

        # 验证配置包含 Agent 节点需要的所有参数
        required_keys = ["user_id", "thread_id"]
        for key in required_keys:
            assert key in config["configurable"], f"配置必须包含 {key}"
            assert config["configurable"][key] is not None, f"{key} 不能为 None"
            assert config["configurable"][key] != "", f"{key} 不能为空字符串"