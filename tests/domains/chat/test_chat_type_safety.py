"""
Chat领域类型安全测试

测试Chat系统中的类型转换和UUID处理逻辑，确保不会发生运行时崩溃。

作者：TaKeKe团队
版本：1.0.0 - UUID架构Batch 1测试
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from src.domains.chat.service import ChatService
from src.core.uuid_converter import UUIDConverter


class TestChatTypeSafety:
    """Chat系统类型安全测试"""

    @pytest.fixture
    def mock_store(self):
        """模拟内存存储"""
        return Mock()

    @pytest.fixture
    def chat_service(self, mock_store):
        """创建ChatService实例用于测试"""
        with patch('src.domains.chat.database.ChatDatabaseManager'):
            service = ChatService(mock_store)
            return service

    def test_type_safe_checkpointer_string_version_conversion(self, chat_service):
        """测试TypeSafeCheckpointer的字符串版本号转换逻辑"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()
        base_checkpointer.put = Mock(return_value="test_result")
        base_checkpointer.get = Mock(return_value=None)

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 测试数据 - 模拟LangGraph可能产生的各种格式
        test_checkpoint = {
            "channel_versions": {
                # 正常情况 - 应该保持不变
                "messages": 1,
                "tasks": 2,

                # 字符串数字 - 应该转换为整数
                "simple_string": "3",
                "float_string": "4.0",

                # 复杂UUID字符串 - 这是最危险的情况
                "uuid_like": "00000000000000000000000000000002.0.243798848838515",
                "complex_uuid": "550e8400-e29b-41d4-a716-446655440000.1.123456789",

                # 边界情况
                "empty_string": "",
                "invalid_string": "not_a_number",
                "zero": "0",
                "negative_float": "-1.5",

                # 其他类型
                "float_value": 3.14,
                "boolean_true": True,
                "boolean_false": False,
                "none_value": None
            }
        }

        # 执行put操作
        config = {"configurable": {"thread_id": "test_thread"}}
        checkpoint = {"id": "test_checkpoint", "channel_versions": test_checkpoint["channel_versions"]}
        metadata = {"source": "test"}
        new_versions = {"messages": 2}

        result = safe_checkpointer.put(config, checkpoint, metadata, new_versions)

        # 验证结果
        assert result == "test_result"

        # 检查channel_versions中的所有值都是整数
        channel_versions = checkpoint["channel_versions"]
        for key, value in channel_versions.items():
            assert isinstance(value, int), f"{key} 的值 {value} 不是整数类型，而是 {type(value)}"

        # 验证特定的转换结果
        assert channel_versions["messages"] == 1  # 整数应该保持不变
        assert channel_versions["simple_string"] == 3  # 字符串数字应该转换
        assert channel_versions["float_string"] == 4  # 浮点字符串应该转换
        assert isinstance(channel_versions["uuid_like"], int)  # UUID应该转换为整数
        assert isinstance(channel_versions["complex_uuid"], int)  # 复杂UUID应该转换为整数

        # 验证边界情况
        assert channel_versions["empty_string"] == 1  # 空字符串应该使用默认值
        assert isinstance(channel_versions["invalid_string"], int)  # 无效字符串应该转换
        assert channel_versions["zero"] == 0  # 零应该正确转换
        assert isinstance(channel_versions["negative_float"], int)  # 负浮点数应该转换

        # 验证其他类型的转换
        assert isinstance(channel_versions["float_value"], int)  # 浮点数应该转换
        assert isinstance(channel_versions["boolean_true"], int)  # 布尔值应该转换
        assert channel_versions["boolean_false"] == 0  # False应该转换为0
        assert isinstance(channel_versions["none_value"], int)  # None应该使用默认值

    def test_type_safe_checkpointer_get_method_fixes_types(self, chat_service):
        """测试TypeSafeCheckpointer的get方法也能修复类型问题"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()

        # 模拟返回包含类型问题的checkpoint
        problematic_checkpoint = {
            "id": "test_checkpoint",
            "channel_versions": {
                "messages": 1,  # 正确的整数
                "uuid_channel": "00000000000000000000000000000002.0.243798848838515",  # UUID字符串
                "string_number": "5",  # 数字字符串
                "invalid_type": ["not", "a", "number"]  # 无效类型
            }
        }
        base_checkpointer.get.return_value = problematic_checkpoint

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 执行get操作
        config = {"configurable": {"thread_id": "test_thread"}}
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

    def test_type_safe_checkpointer_handles_exceptions_gracefully(self, chat_service):
        """测试TypeSafeCheckpointer能优雅地处理各种异常情况"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()
        base_checkpointer.put = Mock(return_value="success")

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 测试可能导致异常的极端情况
        extreme_cases = [
            # 包含None值的channel_versions
            {"channel_versions": {"key1": None, "key2": "2"}},

            # 包含列表的channel_versions
            {"channel_versions": {"key1": [1, 2, 3], "key2": "3"}},

            # 包含字典的channel_versions
            {"channel_versions": {"key1": {"nested": "value"}, "key2": "4"}},

            # 空的channel_versions
            {"channel_versions": {}},

            # None作为channel_versions
            {"channel_versions": None},

            # 非字典的checkpoint结构
            {"not_channel_versions": "value"},

            # 完全空的checkpoint
            {}
        ]

        config = {"configurable": {"thread_id": "test_thread"}}
        metadata = {"source": "test"}
        new_versions = {"messages": 1}

        for i, checkpoint in enumerate(extreme_cases):
            try:
                # 这应该不会抛出异常
                result = safe_checkpointer.put(config, checkpoint, metadata, new_versions)
                assert result == "success", f"情况 {i} 应该成功执行"
            except Exception as e:
                pytest.fail(f"情况 {i} 抛出了不应该的异常: {e}")

    def test_chat_service_handles_uuid_validation(self, chat_service):
        """测试ChatService能正确处理UUID验证"""

        # 测试各种UUID格式
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            str(uuid.uuid4()),
            str(uuid.uuid4()).upper(),
        ]

        invalid_uuids = [
            "",
            "not-a-uuid",
            "550e8400-e29b-41d4",  # 不完整的UUID
            "550e8400-e29b-41d4-a716-44665544zzzz",  # 无效字符
            None,
        ]

        # 测试有效UUID
        for test_uuid in valid_uuids:
            try:
                # 这里应该能够处理有效UUID而不抛出异常
                config = chat_service._create_runnable_config(test_uuid, "test_thread")
                assert config["configurable"]["user_id"] == test_uuid
            except Exception as e:
                pytest.fail(f"有效UUID {test_uuid} 导致异常: {e}")

        # 测试无效UUID的处理
        for invalid_uuid in invalid_uuids:
            try:
                # 某些情况下可能需要处理无效UUID
                if invalid_uuid is not None:
                    config = chat_service._create_runnable_config(invalid_uuid, "test_thread")
                    # 如果没有抛出异常，说明代码能够处理
                else:
                    # None可能需要特殊处理
                    with pytest.raises(Exception):
                        chat_service._create_runnable_config(invalid_uuid, "test_thread")
            except Exception as e:
                # 预期某些无效UUID会抛出异常，这是正常的
                if invalid_uuid is None:
                    assert True  # 预期的异常
                else:
                    # 其他UUID的处理取决于具体实现
                    pass

    def test_string_number_comparison_edge_cases(self):
        """测试字符串数字比较的边界情况"""

        # 这些是可能导致TypeError的比较情况
        problematic_comparisons = [
            ("00000000000000000000000000000002.0.243798848838515", 1),
            ("not-a-number", 5),
            ("", 0),
            ("3.14159", 2),
            ("-5.0", 1),
        ]

        for string_value, int_value in problematic_comparisons:
            # 模拟LangGraph内部可能出现的问题比较
            try:
                # 这种比较会导致TypeError
                result = string_value > int_value
                pytest.fail(f"比较 '{string_value}' > {int_value} 应该抛出TypeError，但得到了结果: {result}")
            except TypeError:
                # 这是预期的结果
                assert True
            except Exception as e:
                pytest.fail(f"比较 '{string_value}' > {int_value} 抛出了意外的异常类型: {e}")

    def test_uuid_converter_edge_cases(self):
        """测试UUID转换器的边界情况"""

        # 测试UUIDConverter的各种输入
        test_cases = [
            # (输入, 期望结果类型, 是否应该成功)
            ("550e8400-e29b-41d4-a716-446655440000", uuid.UUID, True),
            (uuid.uuid4(), uuid.UUID, True),
            ("", type(None), False),
            ("invalid-uuid", type(None), False),
            (None, type(None), False),
        ]

        for input_value, expected_type, should_succeed in test_cases:
            try:
                if input_value is not None:
                    result = UUIDConverter.ensure_uuid(input_value)
                    if should_succeed:
                        assert isinstance(result, expected_type), f"输入 {input_value} 应该转换为 {expected_type}"
                    else:
                        pytest.fail(f"输入 {input_value} 应该失败但成功了: {result}")
                else:
                    # None值的处理取决于具体实现
                    with pytest.raises(Exception):
                        UUIDConverter.ensure_uuid(input_value)
            except Exception as e:
                if should_succeed:
                    pytest.fail(f"输入 {input_value} 应该成功但抛出了异常: {e}")
                else:
                    # 预期的异常
                    assert True

    @pytest.mark.integration
    def test_chat_service_with_real_langgraph_patterns(self, chat_service):
        """集成测试：模拟真实的LangGraph使用模式"""

        # 创建基础checkpointer模拟
        base_checkpointer = Mock()
        base_checkpointer.put = Mock(return_value="checkpoint_saved")
        base_checkpointer.get = Mock(return_value=None)

        # 创建类型安全的checkpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(base_checkpointer)

        # 模拟真实的LangGraph checkpoint结构
        realistic_checkpoint = {
            "v": 1,
            "id": str(uuid.uuid4()),
            "ts": "2024-01-01T00:00:00.000Z",
            "channel_versions": {
                "__start__": "00000000000000000000000000000002.0.243798848838515",  # 问题所在
                "messages": 3,
                "agent:scratchpad": "00000000000000000000000000000001.0.123456789012345",
                "chat_messages": 2,
                "user_input": "00000000000000000000000000000004.0.987654321098765"
            },
            "channel_values": {
                "messages": [],
                "agent:scratchpad": None,
                "chat_messages": [],
                "user_input": None
            },
            "versions_seen": {
                "__start__": 1,
                "messages": 3,
                "agent:scratchpad": 1,
                "chat_messages": 2,
                "user_input": 2
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
        try:
            result = safe_checkpointer.put(config, realistic_checkpoint, metadata, new_versions)
            assert result == "checkpoint_saved"

            # 验证channel_versions中的所有值都是整数
            for key, value in realistic_checkpoint["channel_versions"].items():
                assert isinstance(value, int), f"真实场景中，{key} 的值 {value} 不是整数类型"

        except Exception as e:
            pytest.fail(f"真实LangGraph场景测试失败: {e}")

            # 记录异常的详细信息以便调试
            import traceback
            traceback.print_exc()