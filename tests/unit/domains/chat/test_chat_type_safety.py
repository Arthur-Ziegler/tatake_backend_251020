"""
Chat领域类型安全单元测试

专门测试LangGraph版本号类型不匹配问题的修复。

这个测试文件专注于验证ChatService中的TypeSafeCheckpointer
能够正确处理LangGraph内部产生的版本号类型不一致问题。

作者：TaKeKe团队
版本：1.0.0 - Chat类型安全修复
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
import logging

from src.domains.chat.service import ChatService
from src.domains.chat.database import ChatDatabaseManager
from tests.conftest import test_db_session


@pytest.mark.unit
class TestChatTypeSafety:
    """Chat领域类型安全测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.logger = logging.getLogger(__name__)
        # 创建ChatService实例
        self.chat_service = ChatService()

    def test_type_safe_checkpointer_handles_langgraph_version_format(self):
        """测试TypeSafeCheckpointer处理LangGraph特有的版本号格式"""
        # 模拟LangGraph产生的问题数据
        problematic_checkpoint = {
            "channel_versions": {
                "__start__": "00000000000000000000000000000002.0.243798848838515",  # 问题字符串
                "messages": 1,  # 正确的整数
                "some_channel": "3.14"  # 浮点数字符串
            },
            "values": {"messages": []}
        }

        mock_config = Mock()
        mock_checkpointer = Mock()
        mock_checkpointer.put.return_value = "success"

        # 创建类型安全的checkpointer
        safe_checkpointer = self.chat_service._create_type_safe_checkpointer(mock_checkpointer)

        # 执行put操作
        result = safe_checkpointer.put(mock_config, problematic_checkpoint, {}, {})

        # 验证修复结果
        assert problematic_checkpoint["channel_versions"]["__start__"] == 2
        assert problematic_checkpoint["channel_versions"]["messages"] == 1
        assert problematic_checkpoint["channel_versions"]["some_channel"] == 3

        # 验证原方法被调用
        mock_checkpointer.put.assert_called_once()

    def test_type_safe_checkpointer_get_method_fixes_types(self):
        """测试TypeSafeCheckpointer的get方法也修复类型"""
        # 模拟数据库返回的问题数据
        problematic_result = {
            "channel_versions": {
                "__start__": "00000000000000000000000000000000003.1.123456789012345",  # 问题字符串
                "messages": 2,
                "invalid": "not_a_number"
            },
            "values": {"messages": []}
        }

        mock_config = Mock()
        mock_checkpointer = Mock()
        mock_checkpointer.get.return_value = problematic_result

        # 创建类型安全的checkpointer
        safe_checkpointer = self.chat_service._create_type_safe_checkpointer(mock_checkpointer)

        # 执行get操作
        result = safe_checkpointer.get(mock_config)

        # 验证修复结果
        assert result["channel_versions"]["__start__"] == 3
        assert result["channel_versions"]["messages"] == 2
        assert result["channel_versions"]["invalid"] == 1  # 无法转换时使用默认值

    def test_type_safe_checkpointer_handles_various_string_formats(self):
        """测试TypeSafeCheckpointer处理各种字符串格式"""
        test_cases = [
            ("simple_int", "5", 5),
            ("float_str", "10.5", 10),
            ("langgraph_uuid", "00000000000000000000000000000001.0.123456789012345", 1),
            ("negative", "-3", -3),
            ("zero", "0", 0),
            ("empty", "", 0),  # 空字符串转换为0
        ]

        mock_config = Mock()
        mock_checkpointer = Mock()
        mock_checkpointer.put.return_value = "success"

        safe_checkpointer = self.chat_service._create_type_safe_checkpointer(mock_checkpointer)

        for key, input_value, expected_output in test_cases:
            # 创建测试checkpoint
            checkpoint = {
                "channel_versions": {
                    key: input_value
                },
                "values": {}
            }

            # 执行put操作
            safe_checkpointer.put(mock_config, checkpoint, {}, {})

            # 验证结果
            assert checkpoint["channel_versions"][key] == expected_output, \
                f"Failed for key={key}, input={input_value}, expected={expected_output}"

    def test_with_checkpointer_wrapper_works(self):
        """测试with_checkpoint包装器正常工作"""
        mock_func = Mock(return_value="test_result")

        # 使用with_checkpoint包装器
        result = self.chat_service._with_checkpointer(mock_func)

        # 验证函数被调用
        mock_func.assert_called_once()
        assert result == "test_result"

    def test_send_message_method_handles_type_safety(self):
        """测试send_message方法能够处理类型安全问题"""
        user_id = str(uuid4())
        session_id = str(uuid4())
        message = "测试消息"

        # Mock DatabaseManager
        with patch.object(self.chat_service, 'db_manager') as mock_db_manager:
            # Mock checkpointer
            mock_checkpointer = Mock()
            mock_db_manager.create_checkpointer.return_value.__enter__.return_value = mock_checkpointer

            # Mock graph and AI response extraction
            mock_graph = Mock()
            mock_ai_message = Mock()
            mock_ai_message.type = "ai"
            mock_ai_message.content = "AI回复"

            with patch.object(self.chat_service, '_create_graph_with_checkpointer', return_value=mock_graph), \
                 patch.object(self.chat_service, '_extract_ai_response', return_value="AI回复") as mock_extract:

                # 执行send_message
                result = self.chat_service.send_message(user_id, session_id, message)

                # 验证结果
                assert result["status"] == "success"
                assert "ai_response" in result
                assert result["session_id"] == session_id
                assert result["user_message"] == message

                # 验证AI回复提取被调用
                mock_extract.assert_called_once()

    def test_error_handling_in_type_safe_checkpointer(self):
        """测试TypeSafeCheckpointer的错误处理"""
        # 创建一个会导致类型转换问题的数据
        problematic_checkpoint = {
            "channel_versions": {
                "broken": None,  # None值
                "float_val": 3.14,  # 浮点数
                "bool_val": True,  # 布尔值
            },
            "values": {}
        }

        mock_config = Mock()
        mock_checkpointer = Mock()
        mock_checkpointer.put.return_value = "success"

        safe_checkpointer = self.chat_service._create_type_safe_checkpointer(mock_checkpointer)

        # 执行put操作
        safe_checkpointer.put(mock_config, problematic_checkpoint, {}, {})

        # 验证所有类型都被修复为整数
        assert isinstance(problematic_checkpoint["channel_versions"]["broken"], int)
        assert isinstance(problematic_checkpoint["channel_versions"]["float_val"], int)
        assert isinstance(problematic_checkpoint["channel_versions"]["bool_val"], int)

    def test_logging_of_type_fixes(self):
        """测试类型修复的日志记录"""
        with patch('src.domains.chat.service.logger') as mock_logger:
            mock_config = Mock()
            mock_checkpointer = Mock()
            mock_checkpointer.put.return_value = "success"

            safe_checkpointer = self.chat_service._create_type_safe_checkpointer(mock_checkpointer)

            # 创建包含LangGraph版本号问题的数据
            problematic_checkpoint = {
                "channel_versions": {
                    "__start__": "00000000000000000000000000000002.0.243798848838515"
                },
                "values": {}
            }

            # 执行put操作
            safe_checkpointer.put(mock_config, problematic_checkpoint, {}, {})

            # 验证日志被调用（日志消息可能已经改变，我们只验证有日志调用）
            assert mock_logger.debug.called
            # 验证修复操作确实执行了（通过检查数据被修改）
            assert problematic_checkpoint["channel_versions"]["__start__"] == 2

    def test_defensive_programming_get_method(self):
        """测试get方法的防御性编程"""
        # 测试各种边界情况
        test_cases = [
            None,  # 返回None
            {},  # 空字典
            {"channel_versions": {}},  # 空的channel_versions
            {"channel_versions": None},  # channel_versions为None
            {"channel_versions": "not_a_dict"},  # channel_versions不是字典
        ]

        mock_config = Mock()
        mock_checkpointer = Mock()

        safe_checkpointer = self.chat_service._create_type_safe_checkpointer(mock_checkpointer)

        for i, return_value in enumerate(test_cases):
            mock_checkpointer.get.return_value = return_value

            # 执行get操作 - 应该不抛出异常
            result = safe_checkpointer.get(mock_config)
            assert result == return_value, f"Test case {i} failed"

    def test_comprehensive_type_safety_scenario(self):
        """综合测试类型安全场景"""
        # 模拟完整的LangGraph操作序列
        mock_config = Mock()
        mock_checkpointer = Mock()
        mock_checkpointer.put.return_value = "put_success"
        mock_checkpointer.get.return_value = {
            "channel_versions": {
                "__start__": "00000000000000000000000000000005.2.987654321098765",
                "messages": 10,
                "agent": "3.0",
                "tools": "invalid_version_string"
            },
            "values": {"messages": []}
        }

        safe_checkpointer = self.chat_service._create_type_safe_checkpointer(mock_checkpointer)

        # 1. 存储checkpoint
        checkpoint_to_store = {
            "channel_versions": {
                "__start__": "00000000000000000000000000000005.2.987654321098765",
                "messages": 10,
                "agent": "3.0",
                "tools": "invalid_version_string"
            },
            "values": {"messages": []}
        }

        safe_checkpointer.put(mock_config, checkpoint_to_store, {}, {})

        # 2. 检索checkpoint
        retrieved_checkpoint = safe_checkpointer.get(mock_config)

        # 验证所有版本号都是整数
        for key, value in retrieved_checkpoint["channel_versions"].items():
            assert isinstance(value, int), f"Key {key} has invalid type: {type(value)}"
            assert value > 0, f"Key {key} has invalid value: {value}"

        # 验证修复的一致性
        assert retrieved_checkpoint["channel_versions"]["__start__"] == 5
        assert retrieved_checkpoint["channel_versions"]["messages"] == 10
        assert retrieved_checkpoint["channel_versions"]["agent"] == 3
        assert retrieved_checkpoint["channel_versions"]["tools"] == 1