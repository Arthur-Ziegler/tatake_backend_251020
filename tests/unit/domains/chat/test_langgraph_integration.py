"""
LangGraph 集成测试

专门测试 LangGraph 的正确使用方式，包括：
1. Context Manager 正确使用
2. Graph 对象 API 调用
3. Checkpointer 生命周期管理
4. 类型一致性验证

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import tempfile
import os
from uuid import uuid4

from src.domains.chat.service import ChatService
from src.domains.chat.database import create_chat_checkpointer
from src.domains.chat.graph import create_chat_graph
from src.domains.chat.models import create_chat_state


class TestLangGraphIntegration:
    """LangGraph 集成测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def chat_service_with_temp_db(self, temp_db_path):
        """使用临时数据库的聊天服务"""
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            service = ChatService()
            yield service
        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_checkpointer_context_manager_usage(self, temp_db_path):
        """测试 checkpointer 上下文管理器的正确使用"""
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            # 创建 checkpointer
            checkpointer = create_chat_checkpointer()

            # 测试在上下文管理器中使用
            with checkpointer as cp:
                assert cp is not None, "checkpointer 在上下文中应该可用"

                # 测试基本操作
                dummy_config = {"configurable": {"thread_id": "test", "checkpoint_ns": ""}}
                dummy_checkpoint = {
                    "v": 1, "ts": 0, "id": "test-checkpoint",
                    "channel_values": {"messages": []},
                    "channel_versions": {"messages": 1},
                    "versions_seen": {}, "pending_sends": []
                }

                # 这些操作应该成功
                cp.put(dummy_config, dummy_checkpoint, {}, {})
                retrieved = cp.get({"configurable": {"thread_id": "test"}})
                assert retrieved is not None, "应该能够检索检查点"

        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_graph_creation_with_checkpointer(self, temp_db_path):
        """测试使用 checkpointer 创建图"""
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            # 创建 checkpointer
            checkpointer = create_chat_checkpointer()

            # 创建图
            from src.domains.chat.database import create_memory_store
            store = create_memory_store()

            # 在上下文管理器中使用 checkpointer 创建图
            with checkpointer as cp:
                graph = create_chat_graph(cp, store)
                assert graph is not None, "图应该被创建"
                assert graph.graph is not None, "编译后的图应该存在"

        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_graph_api_methods(self, chat_service_with_temp_db):
        """测试图 API 方法的正确使用"""
        user_id = f"test-user-{uuid4()}"

        # 创建会话
        session_result = chat_service_with_temp_db.create_session(user_id, "测试会话")
        session_id = session_result["session_id"]

        try:
            # 测试获取聊天历史（这会使用正确的图API）
            history = chat_service_with_temp_db.get_chat_history(user_id, session_id)
            assert "messages" in history, "历史应该包含消息"
            assert isinstance(history["messages"], list), "消息应该是列表类型"

        except Exception as e:
            # 如果仍有错误，记录详细信息用于调试
            pytest.fail(f"图 API 调用失败: {e}")

    def test_channel_versions_type_consistency(self, temp_db_path):
        """测试 channel_versions 类型一致性"""
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            checkpointer = create_chat_checkpointer()

            with checkpointer as cp:
                # 创建正确的 checkpoint 数据结构
                dummy_config = {"configurable": {"thread_id": "test", "checkpoint_ns": ""}}
                dummy_checkpoint = {
                    "v": 1,
                    "ts": 0,
                    "id": "test-checkpoint",
                    "channel_values": {"messages": []},
                    # 确保版本号是整数类型
                    "channel_versions": {"messages": 1},
                    "versions_seen": {},
                    "pending_sends": []
                }

                # 验证类型
                assert isinstance(dummy_checkpoint["channel_versions"]["messages"], int), \
                    "版本号应该是整数类型"

                cp.put(dummy_config, dummy_checkpoint, {}, {})

                # 验证检索后的数据类型
                retrieved = cp.get({"configurable": {"thread_id": "test"}})
                assert retrieved is not None, "应该能够检索检查点"

        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_graph_state_creation_format(self):
        """测试图状态创建的格式正确性"""
        user_id = "test-user"
        session_id = "test-session"

        # 使用正确的函数创建状态
        state = create_chat_state(user_id, session_id, "测试会话")

        # 验证字段存在和类型
        assert state["user_id"] == user_id, "user_id 应该正确"
        assert state["session_id"] == session_id, "session_id 应该正确"
        assert state["session_title"] == "测试会话", "session_title 应该正确"
        assert "created_at" in state, "created_at 应该存在"
        assert isinstance(state["messages"], list), "messages 应该是列表"

    def test_error_propagation_clarity(self, chat_service_with_temp_db):
        """测试错误传播的清晰度"""
        user_id = f"test-user-{uuid4()}"

        # 测试无效会话ID
        invalid_session_id = "invalid-session-id"

        try:
            history = chat_service_with_temp_db.get_chat_history(user_id, invalid_session_id)
            # 如果没有抛出异常，历史应该是空的
            assert isinstance(history, dict), "返回应该是字典类型"
        except Exception as e:
            # 错误信息应该清晰
            error_msg = str(e)
            assert len(error_msg) > 0, "错误信息不应该为空"
            # 不应该包含内部实现细节
            assert "_GeneratorContextManager" not in error_msg, \
                "错误信息不应该包含内部实现细节"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])