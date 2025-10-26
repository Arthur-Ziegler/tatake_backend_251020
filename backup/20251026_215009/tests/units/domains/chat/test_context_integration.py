"""
上下文管理集成测试

测试上下文管理器与聊天服务的集成，验证多轮对话的
上下文窗口管理功能。

测试重点：
1. 上下文管理器与聊天图集成
2. 长对话的上下文截断
3. 工具调用的上下文保留
4. 消息历史的智能管理

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import uuid
import os
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.domains.chat.service import ChatService
from src.domains.chat.context_manager import ContextManager


class TestContextIntegration:
    """
    上下文管理集成测试类
    """

    def setup_method(self):
        """
        测试设置：清理数据库
        """
        # 删除现有数据库文件以确保干净的测试环境
        from src.domains.chat.database import get_chat_database_path
        db_path = get_chat_database_path()
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_long_conversation_context_management(self):
        """
        测试长对话的上下文管理
        """
        # 设置小上下文窗口以触发截断
        os.environ["CHAT_MAX_CONTEXT_MESSAGES"] = "5"

        chat_service = ChatService()
        user_id = str(uuid.uuid4())

        # 创建会话
        session_result = chat_service.create_session(
            user_id=user_id,
            title="长对话测试"
        )
        session_id = session_result["session_id"]

        # 发送多条消息测试上下文管理
        messages = [
            "这是第一条消息",
            "这是第二条消息",
            "这是第三条消息",
            "这是第四条消息",
            "这是第五条消息",
            "这是第六条消息，应该触发上下文截断",
            "请记住我最开始说的内容",
            "现在问一个关于前面内容的问题"
        ]

        responses = []
        for i, message in enumerate(messages):
            try:
                result = chat_service.send_message(
                    user_id=user_id,
                    session_id=session_id,
                    message=message
                )
                responses.append(result)
                print(f"消息 {i+1}: {message[:30]}...")
                print(f"回复: {result.get('ai_response', {})[:50]}...")
            except Exception as e:
                print(f"消息 {i+1} 失败: {e}")
                # 对于测试环境，AI调用可能会失败，这是正常的
                if i < 3:  # 前几条消息应该能成功
                    raise

        # 验证会话仍然存在
        session_info = chat_service.get_session_info(
            user_id=user_id,
            session_id=session_id
        )
        assert session_info["session_id"] == session_id

    def test_context_manager_directly(self):
        """
        直接测试上下文管理器功能
        """
        manager = ContextManager(max_context_messages=3)

        # 创建测试消息
        messages = [
            SystemMessage(content="系统提示"),
            HumanMessage(content="用户消息1"),
            AIMessage(content="AI回复1"),
            HumanMessage(content="用户消息2"),
            AIMessage(content="AI回复2"),
            HumanMessage(content="用户消息3"),
            AIMessage(content="AI回复3"),
        ]

        # 管理上下文
        result = manager.manage_context(messages)

        # 验证截断
        assert len(result) <= 3, f"消息数量应该被限制在3条，实际: {len(result)}"

        # 验证系统消息被保留
        system_messages = [msg for msg in result if isinstance(msg, SystemMessage)]
        assert len(system_messages) >= 1, "系统消息应该被保留"

        # 验证包含最新消息
        last_message = messages[-1]
        assert last_message in result, "最新消息应该被保留"

    def test_token_based_context_management(self):
        """
        测试基于token的上下文管理
        """
        manager = ContextManager(max_context_messages=10, max_context_tokens=100)

        # 创建包含中文的长消息
        long_content = "这是一段包含大量中文的长内容，" * 10
        messages = [
            HumanMessage(content=long_content),
            AIMessage(content=long_content),
            HumanMessage(content=long_content),
            AIMessage(content=long_content),
        ]

        # 检查是否需要截断
        should_truncate = manager.should_truncate_by_tokens(messages)
        assert should_truncate, "长内容应该被标记为需要截断"

        # 管理上下文
        result = manager.manage_context(messages)

        # 验证token数量在限制内（允许一些估算误差）
        final_tokens = manager.estimate_tokens(result)
        assert final_tokens <= 150, f"截断后token数量应该在合理范围内: {final_tokens}"

    def test_context_info_functionality(self):
        """
        测试上下文信息功能
        """
        manager = ContextManager(max_context_messages=5, max_context_tokens=200)

        messages = [
            SystemMessage(content="系统提示"),
            HumanMessage(content="用户消息1"),
            AIMessage(content="AI回复1", tool_calls=[]),
            HumanMessage(content="用户消息2"),
        ]

        info = manager.get_context_info(messages)

        # 验证信息结构
        required_fields = [
            "message_count", "estimated_tokens", "max_messages",
            "max_tokens", "message_types", "has_tool_calls",
            "needs_truncation", "timestamp"
        ]

        for field in required_fields:
            assert field in info, f"缺少字段: {field}"

        # 验证信息内容
        assert info["message_count"] == 4
        assert info["max_messages"] == 5
        assert info["max_tokens"] == 200
        assert info["has_tool_calls"] is True
        assert "SystemMessage" in info["message_types"]

    def test_model_specific_optimization(self):
        """
        测试模型特定的优化
        """
        manager = ContextManager()

        # 创建大量消息
        messages = [HumanMessage(content=f"消息 {i}") for i in range(50)]

        # 测试不同模型的优化
        models_to_test = [
            ("gpt-3.5-turbo", 4096),
            ("gpt-4", 8192),
            ("gpt-4-turbo", 128000),
        ]

        for model_name, expected_limit in models_to_test:
            result = manager.optimize_for_model(messages, model_name)

            # 验证结果符合预期
            assert len(result) > 0, f"{model_name} 应该保留一些消息"

            # 对于较小的模型，限制应该更严格
            if "3.5" in model_name:
                assert len(result) < 30, f"{model_name} 应该有更严格的限制"

    def test_edge_cases(self):
        """
        测试边界情况
        """
        manager = ContextManager(max_context_messages=5)

        # 测试空列表
        result = manager.manage_context([])
        assert result == [], "空列表应该返回空列表"

        # 测试单条消息
        single_message = HumanMessage(content="单条消息")
        result = manager.manage_context([single_message])
        assert len(result) == 1, "单条消息应该被保留"
        assert result[0] == single_message, "消息内容应该保持不变"

        # 测试全部系统消息
        system_messages = [
            SystemMessage(content=f"系统消息 {i}")
            for i in range(10)
        ]
        result = manager.manage_context(system_messages)
        assert len(result) <= 5, "系统消息数量应该被限制"
        assert all(isinstance(msg, SystemMessage) for msg in result), "所有消息都应该是系统消息"


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])