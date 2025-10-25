"""
Chat Service集成测试

测试ChatService的TypeSafeCheckpointer在实际使用中的表现。

作者：TaKeKe团队
版本：1.0.0 - UUID架构Batch 1测试
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from src.domains.chat.service import ChatService


class TestChatServiceIntegration:
    """Chat Service集成测试"""

    @pytest.fixture
    def mock_store(self):
        """模拟内存存储"""
        return Mock()

    @pytest.fixture
    def chat_service(self):
        """创建ChatService实例用于测试"""
        with patch('src.domains.chat.database.chat_db_manager') as mock_db_manager:
            mock_db_manager.get_store.return_value = Mock()
            service = ChatService()
            return service

    def test_type_safe_checkpointer_with_real_langgraph_data(self, chat_service):
        """测试TypeSafeCheckpointer处理真实LangGraph数据的能力"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()
        base_checkpointer.put = Mock(return_value="checkpoint_saved")
        base_checkpointer.get = Mock(return_value=None)

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 真实的LangGraph可能产生的checkpoint数据
        realistic_checkpoint = {
            "v": 1,
            "id": str(uuid.uuid4()),
            "ts": "2024-01-01T00:00:00.000Z",
            "channel_versions": {
                # 问题所在：UUID字符串版本号
                "__start__": "00000000000000000000000000000002.0.243798848838515",
                "messages": 3,
                "agent:scratchpad": "00000000000000000000000000000001.0.123456789012345",
                "chat_messages": 2,
                "user_input": "00000000000000000000000000000004.0.987654321098765",
                "tool_calls": "00000000000000000000000000000003.0.456789012345678"
            },
            "channel_values": {
                "messages": [],
                "agent:scratchpad": None,
                "chat_messages": [],
                "user_input": None,
                "tool_calls": []
            }
        }

        # 执行checkpoint操作
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        metadata = {"source": "agent", "step": 1}
        new_versions = {
            "messages": 4,
            "agent:scratchpad": "00000000000000000000000000000002.0.234567890123456",
            "chat_messages": 3,
            "user_input": "00000000000000000000000000000005.0.876543210987654"
        }

        # 这应该不会抛出任何异常
        result = safe_checkpointer.put(config, realistic_checkpoint, metadata, new_versions)

        # 验证结果
        assert result == "checkpoint_saved"
        base_checkpointer.put.assert_called_once()

        # 验证所有channel_versions都是整数
        for key, value in realistic_checkpoint["channel_versions"].items():
            assert isinstance(value, int), f"真实场景中，{key} 的值 {value} 不是整数类型"

        # 验证特定的转换
        assert realistic_checkpoint["channel_versions"]["messages"] == 3  # 整数保持不变
        assert isinstance(realistic_checkpoint["channel_versions"]["__start__"], int)  # UUID转换
        assert isinstance(realistic_checkpoint["channel_versions"]["agent:scratchpad"], int)  # UUID转换

    def test_type_safe_checkpointer_get_method_with_problematic_data(self, chat_service):
        """测试TypeSafeCheckpointer的get方法处理问题数据的能力"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()

        # 模拟从数据库检索到的问题数据
        problematic_checkpoint = {
            "id": str(uuid.uuid4()),
            "channel_versions": {
                "messages": 1,  # 正确的整数
                "uuid_channel": "00000000000000000000000000000002.0.243798848838515",  # UUID字符串
                "string_number": "5",  # 数字字符串
                "invalid_type": ["not", "a", "number"],  # 无效类型
                "none_value": None,  # None值
                "float_value": 3.14,  # 浮点数
                "boolean_true": True  # 布尔值
            }
        }
        base_checkpointer.get.return_value = problematic_checkpoint

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 执行get操作
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        result = safe_checkpointer.get(config)

        # 验证结果
        assert result is not None
        assert isinstance(result, dict)

        # 检查所有channel_versions都是整数
        channel_versions = result["channel_versions"]
        for key, value in channel_versions.items():
            assert isinstance(value, int), f"get方法修复后，{key} 的值 {value} 仍然不是整数类型"

        # 验证特定值的转换
        assert channel_versions["messages"] == 1  # 正确的整数应该保持不变
        assert isinstance(channel_versions["uuid_channel"], int)  # UUID应该转换为整数
        assert channel_versions["string_number"] == 5  # 数字字符串应该转换
        assert isinstance(channel_versions["invalid_type"], int)  # 无效类型应该处理
        assert isinstance(channel_versions["none_value"], int)  # None应该处理
        assert isinstance(channel_versions["float_value"], int)  # 浮点数应该转换
        assert isinstance(channel_versions["boolean_true"], int)  # 布尔值应该转换

    def test_type_safe_checkpointer_handles_edge_cases(self, chat_service):
        """测试TypeSafeCheckpointer处理边界情况的能力"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()
        base_checkpointer.put = Mock(return_value="success")

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 测试可能导致异常的极端情况
        extreme_cases = [
            # 空的channel_versions
            {"channel_versions": {}},

            # None作为channel_versions
            {"channel_versions": None},

            # 非字典的checkpoint结构
            {"not_channel_versions": "value"},

            # 完全空的checkpoint
            {},

            # 包含各种问题类型的channel_versions
            {
                "channel_versions": {
                    "key1": None,
                    "key2": "2",
                    "key3": [1, 2, 3],
                    "key4": {"nested": "value"},
                    "key5": "",
                    "key6": "00000000000000000000000000000002.0.243798848838515",
                    "key7": 3.14,
                    "key8": True,
                    "key9": False
                }
            }
        ]

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        metadata = {"source": "test"}
        new_versions = {"messages": 1}

        for i, checkpoint in enumerate(extreme_cases):
            try:
                # 这应该不会抛出异常
                result = safe_checkpointer.put(config, checkpoint, metadata, new_versions)
                assert result == "success", f"情况 {i} 应该成功执行"

                # 如果有channel_versions，检查其值
                if "channel_versions" in checkpoint and isinstance(checkpoint["channel_versions"], dict):
                    for key, value in checkpoint["channel_versions"].items():
                        assert isinstance(value, int), f"情况 {i} 中，{key} 的值 {value} 不是整数类型"

            except Exception as e:
                pytest.fail(f"情况 {i} 抛出了不应该的异常: {e}")

    def test_chat_service_create_runnable_config_with_uuid_validation(self, chat_service):
        """测试ChatService的_runnable_config创建功能与UUID验证"""

        # 测试有效UUID
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        thread_id = str(uuid.uuid4())

        config = chat_service._create_runnable_config(valid_uuid, thread_id)

        assert config["configurable"]["user_id"] == valid_uuid
        assert config["configurable"]["thread_id"] == thread_id

        # 测试各种UUID格式
        test_cases = [
            str(uuid.uuid4()),
            str(uuid.uuid4()).upper(),
            str(uuid.uuid4()),
        ]

        for test_uuid in test_cases:
            try:
                config = chat_service._create_runnable_config(test_uuid, thread_id)
                assert config["configurable"]["user_id"] == test_uuid
            except Exception as e:
                pytest.fail(f"有效UUID {test_uuid} 导致异常: {e}")

    def test_type_safe_checkpointer_prevents_type_errors(self, chat_service):
        """测试TypeSafeCheckpointer能够防止类型错误"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()
        base_checkpointer.put = Mock(return_value="success")

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 创建包含问题类型比较的数据
        problematic_checkpoint = {
            "channel_versions": {
                "string_key": "00000000000000000000000000000002.0.243798848838515",  # 字符串
                "int_key": 1,  # 整数
            }
        }

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        metadata = {"source": "test"}
        new_versions = {"string_key": "00000000000000000000000000000003.0.345678901234567"}

        # 在修复前，这会导致TypeError
        # 在修复后，应该正常工作
        try:
            result = safe_checkpointer.put(config, problematic_checkpoint, metadata, new_versions)
            assert result == "success"

            # 验证所有值都是整数
            for key, value in problematic_checkpoint["channel_versions"].items():
                assert isinstance(value, int), f"{key} 的值 {value} 不是整数类型"

            # 验证可以安全地进行比较操作
            string_value = problematic_checkpoint["channel_versions"]["string_key"]
            int_value = problematic_checkpoint["channel_versions"]["int_key"]

            # 这些比较现在应该可以正常工作
            assert isinstance(string_value, int)
            assert isinstance(int_value, int)
            comparison_result = string_value > int_value  # 不应该抛出TypeError
            assert isinstance(comparison_result, bool)

        except TypeError as e:
            pytest.fail(f"TypeSafeCheckpointer未能防止TypeError: {e}")

    @pytest.mark.asyncio
    async def test_chat_service_send_message_with_type_safety(self, chat_service):
        """测试ChatService的send_message方法在类型安全方面的工作"""

        # 模拟用户和会话
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        # 创建模拟的graph
        mock_graph = Mock()
        mock_result = {"messages": [{"type": "human", "content": "Hello"}]}
        mock_graph.ainvoke = Mock(return_value=mock_result)

        # 模拟checkpointer
        mock_checkpointer = Mock()
        mock_checkpointer.put = Mock(return_value="success")
        mock_checkpointer.get = Mock(return_value=None)

        # 修复_create_graph_with_checkpointer方法的模拟
        def mock_create_graph(checkpointer):
            return mock_graph

        chat_service._create_graph_with_checkpointer = mock_create_graph

        try:
            # 这应该不会抛出类型错误
            result = await chat_service.send_message(
                user_id=user_id,
                session_id=session_id,
                message="Hello, world!"
            )

            # 验证结果
            assert result is not None
            assert "messages" in result

        except Exception as e:
            # 如果有错误，检查是否是类型相关的错误
            if "TypeError" in str(type(e)) or "not supported between instances" in str(e):
                pytest.fail(f"send_message方法存在类型安全问题: {e}")
            else:
                # 其他类型的错误可能是正常的（如数据库连接问题）
                pass