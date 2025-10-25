#!/usr/bin/env python3
"""
ChatService UUID格式化修复测试

测试目标：
1. 确保ChatService只接受标准UUID格式
2. 验证LangGraph状态管理不再出现类型冲突
3. 测试TypeSafeCheckpointer增强功能
4. 验证错误处理和日志记录

遵循TDD原则：先写测试，再写实现
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from src.domains.chat.service import ChatService
from src.domains.chat.database import ChatDatabaseManager
from src.core.uuid_converter import UUIDConverter
from langchain_core.messages import HumanMessage


class TestChatUUIDFormatFix:
    """ChatService UUID格式化修复测试套件"""

    @pytest.fixture
    def chat_service(self):
        """创建ChatService测试实例"""
        # 模拟数据库管理器
        mock_db_manager = MagicMock(spec=ChatDatabaseManager)
        service = ChatService()
        service.db_manager = mock_db_manager
        return service

    @pytest.fixture
    def standard_uuids(self):
        """标准UUID测试数据"""
        return {
            "valid_user_id": uuid.uuid4(),
            "valid_session_id": uuid.uuid4(),
            "invalid_user_id": "test-user-123",
            "invalid_session_id": "test-session-456",
            "empty_user_id": "",
            "none_user_id": None
        }

    @pytest.fixture
    def mock_langgraph_config(self):
        """模拟LangGraph配置"""
        return {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4())
            }
        }

    # ========== 测试1: UUID格式验证 ==========

    def test_validate_standard_uuid_input(self, chat_service, standard_uuids):
        """测试1.1: 验证标准UUID输入被正确接受"""
        # 标准UUID应该被接受
        user_id = standard_uuids["valid_user_id"]
        session_id = standard_uuids["valid_session_id"]

        config = chat_service._create_runnable_config(str(user_id), str(session_id))

        assert config is not None
        assert "configurable" in config
        assert config["configurable"]["thread_id"] == str(session_id)
        assert config["configurable"]["user_id"] == str(user_id)

    def test_reject_non_standard_uuid_input(self, chat_service, standard_uuids):
        """测试1.2: 非标准UUID输入应该被拒绝或转换"""
        # 非标准UUID应该触发错误处理
        with pytest.raises((ValueError, AttributeError)) as exc_info:
            invalid_user_id = standard_uuids["invalid_user_id"]
            config = chat_service._create_runnable_config(invalid_user_id, uuid.uuid4())

        # 验证错误信息包含UUID格式相关内容
        error_message = str(exc_info.value)
        assert any(keyword in error_message.lower() for keyword in ["uuid", "format", "invalid"])

    def test_handle_none_empty_uuid(self, chat_service, standard_uuids):
        """测试1.3: 处理None和空字符串UUID"""
        # None值应该被正确处理
        with pytest.raises((ValueError, TypeError, AttributeError)):
            chat_service._create_runnable_config(None, uuid.uuid4())

        # 空字符串应该被正确处理
        with pytest.raises((ValueError, AttributeError)):
            chat_service._create_runnable_config("", uuid.uuid4())

    # ========== 测试2: LangGraph状态管理 ==========

    @patch('src.domains.chat.graph.create_chat_graph')
    def test_langgraph_state_type_safety(self, mock_create_chat_graph, chat_service, standard_uuids):
        """测试2.1: LangGraph状态管理类型安全"""
        # 模拟LangGraph图实例
        mock_graph_instance = MagicMock()
        mock_create_chat_graph.return_value = mock_graph_instance

        # 模拟正常的invoke行为
        mock_graph_instance.invoke.return_value = {
            "messages": [MagicMock()],
            "user_id": str(standard_uuids["valid_user_id"]),
            "session_id": str(standard_uuids["valid_session_id"])
        }

        # 执行send_message
        user_id = standard_uuids["valid_user_id"]
        session_id = standard_uuids["valid_session_id"]
        message = "测试消息"

        result = chat_service.send_message(user_id, session_id, message)

        # 验证LangGraph.invoke被调用
        mock_graph_instance.invoke.assert_called_once()

        # 验证传递给LangGraph的数据格式正确
        call_args = mock_graph_instance.invoke.call_args
        state_data = call_args[0][0]  # 第一个位置参数是state数据

        # 验证UUID字段格式
        assert isinstance(state_data.get("user_id"), str)
        assert isinstance(state_data.get("session_id"), str)

        # 验证UUID格式符合标准
        uuid.UUID(state_data["user_id"])  # 如果格式错误会抛出异常
        uuid.UUID(state_data["session_id"])

    def test_current_state_structure_validation(self, chat_service, standard_uuids):
        """测试2.2: current_state结构验证"""
        user_id = standard_uuids["valid_user_id"]
        session_id = standard_uuids["valid_session_id"]
        message = "测试消息"

        # 创建当前状态
        current_state = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "session_title": "测试会话",
            "messages": [HumanMessage(content=message)]
        }

        # 验证状态结构
        assert "user_id" in current_state
        assert "session_id" in current_state
        assert "session_title" in current_state
        assert "messages" in current_state

        # 验证UUID格式
        uuid.UUID(current_state["user_id"])
        uuid.UUID(current_state["session_id"])

        # 验证消息格式
        assert len(current_state["messages"]) > 0
        assert isinstance(current_state["messages"][0], HumanMessage)

    # ========== 测试3: 增强TypeSafeCheckpointer ==========

    def test_type_safe_checkpointer_uuid_handling(self, chat_service):
        """测试3.1: TypeSafeCheckpointer UUID处理增强"""
        # 创建模拟的基础checkpointer
        mock_base_checkpointer = MagicMock()

        # 创建增强的TypeSafeCheckpointer
        safe_checkpointer = chat_service._create_type_safe_checkpointer(mock_base_checkpointer)

        # 测试数据：包含LangGraph特殊版本号格式
        test_checkpoint = {
            "channel_versions": {
                "__start__": "00000000000000000000000000000002.0.243798848838515",  # LangGraph特殊格式
                "messages": 1,  # 整数版本号
                "user_id": "123e4567-e89b-12d3-a456-426614174000.1.123456789",     # UUID格式版本号
                "session_id": 2  # 正常整数版本号
            },
            "values": {
                "messages": [],
                "user_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4())
            }
        }

        # 测试put方法的类型修复
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        safe_checkpointer.put(config, test_checkpoint, {}, None)

        # 验证基础checkpointer被调用
        mock_base_checkpointer.put.assert_called_once()

        # 获取传递给基础checkpointer的数据
        call_args = mock_base_checkpointer.put.call_args
        processed_checkpoint = call_args[0][1]  # 第二个位置参数是checkpoint

        # 验证所有channel_versions都是整数
        channel_versions = processed_checkpoint["channel_versions"]
        for key, value in channel_versions.items():
            assert isinstance(value, int), f"channel_versions[{key}] 应该是整数，实际是 {type(value)}: {value}"

    def test_type_safe_checkpointer_error_handling(self, chat_service):
        """测试3.2: TypeSafeCheckpointer错误处理"""
        # 创建会抛出异常的模拟checkpointer
        mock_base_checkpointer = MagicMock()
        mock_base_checkpointer.put.side_effect = Exception("数据库连接错误")

        safe_checkpointer = chat_service._create_type_safe_checkpointer(mock_base_checkpointer)

        # 测试错误处理
        with pytest.raises(Exception) as exc_info:
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            checkpoint = {"channel_versions": {}, "values": {}}
            safe_checkpointer.put(config, checkpoint, {}, None)

        # 验证错误信息包含有用的调试信息
        assert "数据库连接错误" in str(exc_info.value)

    # ========== 测试4: 错误处理和日志 ==========

    @patch('src.domains.chat.service.logger')
    def test_error_logging_and_debugging(self, mock_logger, chat_service):
        """测试4.1: 错误处理和日志记录"""
        # 测试UUID格式错误的日志记录
        with pytest.raises((ValueError, AttributeError)):
            chat_service._create_runnable_config("invalid-uuid", uuid.uuid4())

        # 验证错误日志被记录
        mock_logger.error.assert_called()

        # 验证日志消息包含有用的调试信息
        log_calls = mock_logger.error.call_args_list
        assert any("uuid" in str(call).lower() for call in log_calls)

    def test_performance_validation(self, chat_service):
        """测试4.2: 性能验证"""
        import time

        # 测试大量UUID转换的性能
        user_ids = [uuid.uuid4() for _ in range(1000)]
        session_id = uuid.uuid4()

        start_time = time.time()

        for user_id in user_ids:
            try:
                chat_service._create_runnable_config(user_id, session_id)
            except Exception:
                # 忽略其他依赖相关的错误，只关注UUID处理性能
                pass

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证性能在合理范围内（1000个UUID转换应该在1秒内完成）
        assert processing_time < 1.0, f"UUID处理性能过慢: {processing_time:.3f}秒"

    # ========== 测试5: 集成测试 ==========

    @patch('src.domains.chat.graph.create_chat_graph')
    def test_end_to_end_uuid_processing(self, mock_create_chat_graph, chat_service, standard_uuids):
        """测试5.1: 端到端UUID处理流程"""
        # 模拟完整的LangGraph交互
        mock_graph_instance = MagicMock()
        mock_create_chat_graph.return_value = mock_graph_instance

        # 模拟AI响应
        mock_response = MagicMock()
        mock_response.content = "AI回复内容"
        mock_graph_instance.invoke.return_value = {
            "messages": [mock_response],
            "user_id": str(standard_uuids["valid_user_id"]),
            "session_id": str(standard_uuids["valid_session_id"])
        }

        # 执行完整的send_message流程
        user_id = standard_uuids["valid_user_id"]
        session_id = standard_uuids["valid_session_id"]
        message = "用户输入消息"

        result = chat_service.send_message(user_id, session_id, message)

        # 验证结果
        assert result is not None
        assert "content" in result
        assert result["content"] == "AI回复内容"

        # 验证LangGraph被正确调用
        mock_graph_instance.invoke.assert_called_once()

        # 验证传递的数据格式正确
        call_args = mock_graph_instance.invoke.call_args
        state_data = call_args[0][0]

        # 验证UUID格式
        uuid.UUID(state_data["user_id"])
        uuid.UUID(state_data["session_id"])


class TestUUIDConverterEnhancements:
    """UUIDConverter增强功能测试"""

    def test_langgraph_special_format_handling(self):
        """测试LangGraph特殊格式处理"""
        from src.core.uuid_converter import UUIDConverter

        converter = UUIDConverter()

        # 测试LangGraph特殊版本号格式
        langgraph_formats = [
            "00000000000000000000000000000002.0.243798848838515",
            "123e4567-e89b-12d3-a456-426614174000.1.123456789",
            "550e8400-e29b-41d4-a716-446655440000.2.987654321"
        ]

        for format_str in langgraph_formats:
            # 测试版本号提取
            extracted_version = converter._extract_version_from_langgraph_format(format_str)
            assert isinstance(extracted_version, int)
            assert extracted_version >= 0

    def test_uuid_validation_enhancement(self):
        """测试UUID验证增强"""
        from src.core.uuid_converter import UUIDConverter

        converter = UUIDConverter()

        # 测试各种UUID格式
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000",
            str(uuid.uuid4())
        ]

        invalid_uuids = [
            "test-user-123",
            "test-session-456",
            "not-a-uuid",
            "",
            None
        ]

        # 验证有效UUID
        for valid_uuid in valid_uuids:
            assert converter.is_valid_uuid_format(valid_uuid), f"应该验证有效UUID: {valid_uuid}"

        # 验证无效UUID
        for invalid_uuid in invalid_uuids:
            assert not converter.is_valid_uuid_format(invalid_uuid), f"应该拒绝无效UUID: {invalid_uuid}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])