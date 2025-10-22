"""
聊天上下文管理器测试

测试多轮对话的上下文窗口管理功能，包括智能消息截断、
token管理和上下文优化。

测试重点：
1. 消息历史截断功能
2. Token计数和限制
3. 重要消息保留策略
4. 模型特定优化

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from src.domains.chat.context_manager import (
    ContextManager,
    manage_conversation_context,
    default_context_manager
)


class TestContextManager:
    """
    上下文管理器基础测试类
    """

    def test_basic_context_management(self):
        """
        测试基础上下文管理功能
        """
        manager = ContextManager(max_context_messages=5)

        # 创建测试消息
        messages = [
            HumanMessage(content=f"用户消息 {i}")
            for i in range(10)
        ]

        # 管理上下文
        result = manager.manage_context(messages)

        # 验证截断
        assert len(result) <= 5, "消息数量应该被限制在5条"
        assert len(result) == 5, "应该保留最新的5条消息"

        # 验证保留的是最新的消息
        for i, msg in enumerate(result):
            expected_content = f"用户消息 {i + 5}"  # 最新的5条：5,6,7,8,9
            assert msg.content == expected_content

    def test_system_message_preservation(self):
        """
        测试系统消息保留
        """
        manager = ContextManager(max_context_messages=3, preserve_system_messages=True)

        messages = [
            SystemMessage(content="系统提示词"),
            HumanMessage(content="用户消息1"),
            AIMessage(content="AI回复1"),
            HumanMessage(content="用户消息2"),
            AIMessage(content="AI回复2"),
            HumanMessage(content="用户消息3"),
        ]

        result = manager.manage_context(messages)

        # 验证系统消息被保留
        system_messages = [msg for msg in result if isinstance(msg, SystemMessage)]
        assert len(system_messages) == 1, "系统消息应该被保留"
        assert system_messages[0].content == "系统提示词"

        # 验证总消息数不超过限制
        assert len(result) <= 3, "总消息数应该不超过限制"

    def test_tool_call_message_preservation(self):
        """
        测试工具调用消息保留
        """
        manager = ContextManager(max_context_messages=4)

        # 创建包含工具调用的消息
        messages = [
            HumanMessage(content="请帮我打开门"),
            AIMessage(
                content="我来帮你打开门",
                additional_kwargs={
                    "tool_calls": [{"name": "sesame_opener", "args": {"action": "open"}}]
                }
            ),
            ToolMessage(content="门已打开", tool_call_id="test_tool_id"),
            HumanMessage(content="谢谢"),
            AIMessage(content="不客气"),
            HumanMessage(content="还有别的事情吗？"),
        ]

        result = manager.manage_context(messages)

        # 验证工具相关消息被优先保留
        tool_messages = [msg for msg in result if hasattr(msg, 'tool_calls') or isinstance(msg, ToolMessage)]
        assert len(tool_messages) >= 2, "工具相关消息应该被优先保留"

        # 验证消息数量限制
        assert len(result) <= 4, "消息数量应该被限制"

    def test_token_estimation(self):
        """
        测试Token估算功能
        """
        manager = ContextManager()

        # 创建包含中英文的消息
        messages = [
            HumanMessage(content="Hello 你好"),
            AIMessage(content="Hello 你好 too"),
        ]

        tokens = manager.estimate_tokens(messages)

        # 验证token数量合理性
        # 2个中文字符 * 1.5 + 4个英文字符 * 0.25 + 开销
        expected_min = 3 + 1 + 20  # 最小期望值
        expected_max = 3 + 1 + 40  # 最大期望值

        assert expected_min <= tokens <= expected_max, f"Token估算应该在合理范围内: {tokens}"

    def test_token_based_truncation(self):
        """
        测试基于token数量的截断
        """
        manager = ContextManager(max_context_messages=10, max_context_tokens=50)

        # 创建较长的消息
        long_content = "这是一段很长的中文内容，" * 20  # 重复20次
        messages = [
            HumanMessage(content=long_content),
            AIMessage(content=long_content),
            HumanMessage(content=long_content),
        ]

        should_truncate = manager.should_truncate_by_tokens(messages)
        assert should_truncate, "长消息应该被标记为需要截断"

        # 管理上下文
        result = manager.manage_context(messages)
        assert manager.estimate_tokens(result) <= 50, "截断后token数量应该在限制内"

    def test_context_info(self):
        """
        测试上下文信息获取
        """
        manager = ContextManager(max_context_messages=5, max_context_tokens=100)

        messages = [
            SystemMessage(content="系统提示"),
            HumanMessage(content="用户消息1"),
            AIMessage(content="AI回复1", additional_kwargs={"tool_calls": []}),
            HumanMessage(content="用户消息2"),
        ]

        info = manager.get_context_info(messages)

        # 验证信息结构
        assert "message_count" in info
        assert "estimated_tokens" in info
        assert "max_messages" in info
        assert "max_tokens" in info
        assert "message_types" in info
        assert "has_tool_calls" in info
        assert "needs_truncation" in info

        # 验证信息内容
        assert info["message_count"] == 4
        assert info["max_messages"] == 5
        assert info["max_tokens"] == 100
        assert info["has_tool_calls"] is True
        assert "SystemMessage" in info["message_types"]
        assert "HumanMessage" in info["message_types"]
        assert "AIMessage" in info["message_types"]

    def test_model_specific_optimization(self):
        """
        测试模型特定的优化
        """
        manager = ContextManager()

        # 创建超长消息列表
        messages = [HumanMessage(content=f"消息 {i}") for i in range(50)]

        # 测试GPT-3.5-turbo优化
        result_gpt35 = manager.optimize_for_model(messages, "gpt-3.5-turbo")
        assert len(result_gpt35) <= 20, "GPT-3.5应该有更严格的限制"

        # 测试GPT-4-turbo优化
        result_gpt4 = manager.optimize_for_model(messages, "gpt-4-turbo")
        assert len(result_gpt4) >= len(result_gpt35), "GPT-4-turbo应该允许更多消息"


class TestConvenienceFunction:
    """
    便捷函数测试类
    """

    def test_manage_conversation_context_function(self):
        """
        测试便捷函数
        """
        # 创建测试消息
        messages = [HumanMessage(content=f"消息 {i}") for i in range(25)]

        # 使用便捷函数
        result = manage_conversation_context(messages, "gpt-3.5-turbo")

        # 验证结果
        assert len(result) <= 20, "便捷函数应该正确限制消息数量"
        assert isinstance(result[0], HumanMessage), "应该保持消息类型"

    def test_default_context_manager(self):
        """
        测试默认上下文管理器
        """
        assert default_context_manager is not None, "默认上下文管理器应该存在"
        assert isinstance(default_context_manager, ContextManager), "应该是ContextManager实例"


class TestEdgeCases:
    """
    边界情况测试类
    """

    def test_empty_messages(self):
        """
        测试空消息列表
        """
        manager = ContextManager()
        result = manager.manage_context([])
        assert result == [], "空消息列表应该返回空列表"

    def test_single_message(self):
        """
        测试单条消息
        """
        manager = ContextManager(max_context_messages=5)
        message = HumanMessage(content="单条消息")
        result = manager.manage_context([message])

        assert len(result) == 1, "单条消息应该被保留"
        assert result[0] == message, "消息内容应该保持不变"

    def test_all_system_messages(self):
        """
        测试全部是系统消息的情况
        """
        manager = ContextManager(max_context_messages=2, preserve_system_messages=True)
        messages = [
            SystemMessage(content=f"系统消息 {i}")
            for i in range(5)
        ]

        result = manager.manage_context(messages)

        # 系统消息应该被保留，但不超过限制
        assert len(result) == 2, "系统消息数量应该被限制"
        assert all(isinstance(msg, SystemMessage) for msg in result), "所有消息都应该是系统消息"

    def test_messages_without_tool_calls_attribute(self):
        """
        测试没有tool_calls属性的消息
        """
        manager = ContextManager(max_context_messages=3)

        # 创建自定义消息类（没有tool_calls属性）
        class CustomMessage:
            def __init__(self, content):
                self.content = content

        messages = [
            HumanMessage(content="正常消息1"),
            CustomMessage(content="自定义消息"),
            HumanMessage(content="正常消息2"),
        ]

        # 应该不会抛出异常
        result = manager.manage_context(messages)
        assert len(result) <= 3, "应该正常处理自定义消息"


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])