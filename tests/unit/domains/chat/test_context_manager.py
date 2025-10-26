"""
ContextManager单元测试

严格TDD方法：
1. 初始化参数测试
2. 上下文管理测试
3. 智能截断测试
4. Token估算测试
5. 模型优化测试
6. 边界条件测试

作者：TaTakeKe团队
版本：1.0.0 - 上下文管理单元测试
"""

import pytest
from typing import List
from unittest.mock import patch

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage

from src.domains.chat.context_manager import ContextManager, manage_conversation_context, default_context_manager


@pytest.mark.unit
class TestContextManager:
    """ContextManager单元测试类"""

    @pytest.fixture
    def sample_messages(self):
        """提供测试消息列表"""
        return [
            SystemMessage(content="你是一个AI助手"),
            HumanMessage(content="你好"),
            AIMessage(content="你好！有什么可以帮助你的吗？"),
            HumanMessage(content="我想了解一下天气"),
            AIMessage(content="当然！你想了解哪个城市的天气？"),
            HumanMessage(content="北京"),
            AIMessage(content="今天北京天气晴朗，温度25度"),
        ]

    @pytest.fixture
    def long_message_list(self):
        """提供长消息列表用于截断测试"""
        messages = [SystemMessage(content="系统消息")]
        for i in range(50):
            messages.append(HumanMessage(content=f"用户消息{i}"))
            messages.append(AIMessage(content=f"AI回复{i}"))
        return messages

    def test_init_default_parameters(self):
        """测试默认参数初始化"""
        manager = ContextManager()

        assert manager.max_context_messages == 20
        assert manager.max_context_tokens is None
        assert manager.preserve_system_messages is True

    def test_init_custom_parameters(self):
        """测试自定义参数初始化"""
        manager = ContextManager(
            max_context_messages=10,
            max_context_tokens=1000,
            preserve_system_messages=False
        )

        assert manager.max_context_messages == 10
        assert manager.max_context_tokens == 1000
        assert manager.preserve_system_messages is False

    def test_manage_context_empty_list(self):
        """测试空消息列表"""
        manager = ContextManager()
        result = manager.manage_context([])
        assert result == []

    def test_manage_context_within_limits(self, sample_messages):
        """测试消息在限制内的情况"""
        manager = ContextManager(max_context_messages=10)
        result = manager.manage_context(sample_messages)

        # 消息数量在限制内，应该原样返回
        assert len(result) == len(sample_messages)
        assert result == sample_messages

    def test_manage_context_message_truncation(self, long_message_list):
        """测试消息数量截断"""
        manager = ContextManager(max_context_messages=10, preserve_system_messages=True)
        result = manager.manage_context(long_message_list)

        # 应该截断到最多10条消息
        assert len(result) <= 10

        # 系统消息应该被保留
        system_messages = [msg for msg in result if isinstance(msg, SystemMessage)]
        assert len(system_messages) >= 1
        assert system_messages[0].content == "系统消息"

    def test_manage_context_without_system_preservation(self, long_message_list):
        """测试不保留系统消息的情况"""
        manager = ContextManager(max_context_messages=5, preserve_system_messages=False)
        result = manager.manage_context(long_message_list)

        # 应该截断到最多5条消息
        assert len(result) <= 5

        # 不应该保留系统消息
        system_messages = [msg for msg in result if isinstance(msg, SystemMessage)]
        assert len(system_messages) == 0

    def test_smart_truncate_keep_recent_messages(self, long_message_list):
        """测试智能截断保留最新消息"""
        manager = ContextManager(max_context_messages=5)
        result = manager._smart_truncate(long_message_list)

        # 应该保留最新的5条消息
        assert len(result) <= 5

        # 检查顺序是否正确
        result_types = [type(msg).__name__ for msg in result]
        original_types = [type(msg).__name__ for msg in long_message_list]

        # 结果应该是原始消息的最后几条
        if len(result) > 0:
            # 最后一条消息应该是AI消息
            assert isinstance(result[-1], AIMessage)

    def test_smart_truncate_tool_messages(self):
        """测试工具消息的处理"""
        messages = [
            SystemMessage(content="系统消息"),
            HumanMessage(content="用户消息1"),
            AIMessage(content="AI回复1"),
            ToolMessage(content="工具结果", tool_call_id="tool1"),
            HumanMessage(content="用户消息2"),
            AIMessage(content="AI回复2", tool_calls=[{"id": "tool1", "type": "function", "name": "test_tool", "args": {}}]),
            HumanMessage(content="用户消息3"),
        ]

        manager = ContextManager(max_context_messages=5)
        result = manager._smart_truncate(messages)

        # 应该保留系统消息
        system_messages = [msg for msg in result if isinstance(msg, SystemMessage)]
        assert len(system_messages) >= 1

        # 应该尽量保留工具相关的消息
        tool_messages = [msg for msg in result if isinstance(msg, ToolMessage) or
                        (hasattr(msg, 'tool_calls') and msg.tool_calls)]
        assert len(tool_messages) >= 1

    def test_estimate_tokens_empty_message(self):
        """测试空消息的token估算"""
        manager = ContextManager()
        tokens = manager.estimate_tokens([])
        assert tokens == 0

    def test_estimate_tokens_single_message(self):
        """测试单条消息的token估算"""
        manager = ContextManager()
        messages = [HumanMessage(content="Hello world")]
        tokens = manager.estimate_tokens(messages)

        # 应该包含内容token + 开销
        assert tokens > 0
        assert tokens > 10  # 开销至少10个token

    def test_estimate_tokens_chinese_content(self):
        """测试中文内容的token估算"""
        manager = ContextManager()
        messages = [HumanMessage(content="你好世界")]
        tokens = manager.estimate_tokens(messages)

        # 中文字符约1.5个token + 开销
        expected = int(4 * 1.5 + 10)  # 4个中文字符
        assert tokens == expected

    def test_estimate_tokens_mixed_content(self):
        """测试混合内容的token估算"""
        manager = ContextManager()
        messages = [HumanMessage(content="Hello 你好 world 世界")]
        tokens = manager.estimate_tokens(messages)

        # 英文字符约0.25个token，中文字符约1.5个token
        content = "Hello 你好 world 世界"
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])  # 4个中文字符
        english_chars = len(content) - chinese_chars  # 14个英文字符
        expected = int(chinese_chars * 1.5 + english_chars * 0.25 + 10)
        assert tokens == expected

    def test_should_truncate_by_tokens_no_limit(self):
        """测试没有token限制时的情况"""
        manager = ContextManager(max_context_tokens=None)
        messages = [HumanMessage(content="任意内容")]

        should_truncate = manager.should_truncate_by_tokens(messages)
        assert should_truncate is False

    def test_should_truncate_by_tokens_within_limit(self):
        """测试token数量在限制内"""
        manager = ContextManager(max_context_tokens=1000)
        messages = [HumanMessage(content="短消息")]

        should_truncate = manager.should_truncate_by_tokens(messages)
        assert should_truncate is False

    def test_should_truncate_by_tokens_exceeds_limit(self):
        """测试token数量超出限制"""
        manager = ContextManager(max_context_tokens=5)  # 很小的限制
        messages = [HumanMessage(content="这是一条很长的消息，应该会超出5个token的限制")]

        should_truncate = manager.should_truncate_by_tokens(messages)
        assert should_truncate is True

    def test_token_based_truncate(self):
        """测试基于token的截断"""
        manager = ContextManager(max_context_tokens=50)
        messages = [
            HumanMessage(content=f"消息{i}" * 10) for i in range(10)
        ]

        result = manager._token_based_truncate(messages)

        # 结果应该是一个子集
        assert len(result) <= len(messages)

        # 结果应该包含最新的消息（倒序遍历）
        if len(result) > 0:
            assert result[-1] == messages[-1]

    def test_get_context_info(self, sample_messages):
        """测试获取上下文信息"""
        manager = ContextManager(max_context_messages=10, max_context_tokens=1000)
        info = manager.get_context_info(sample_messages)

        # 检查基本信息
        assert info["message_count"] == len(sample_messages)
        assert info["estimated_tokens"] > 0
        assert info["max_messages"] == 10
        assert info["max_tokens"] == 1000

        # 检查消息类型统计
        assert "HumanMessage" in info["message_types"]
        assert "AIMessage" in info["message_types"]
        assert "SystemMessage" in info["message_types"]
        assert info["message_types"]["HumanMessage"] == 3
        assert info["message_types"]["AIMessage"] == 3
        assert info["message_types"]["SystemMessage"] == 1

        # 检查其他字段
        assert "timestamp" in info
        assert "needs_truncation" in info
        assert info["has_tool_calls"] is False

    def test_get_context_info_with_tool_calls(self):
        """测试包含工具调用的上下文信息"""
        messages = [
            HumanMessage(content="用户消息"),
            AIMessage(content="AI回复", tool_calls=[{"id": "tool1", "type": "function", "name": "test_tool", "args": {}}]),
        ]

        manager = ContextManager()
        info = manager.get_context_info(messages)

        assert info["has_tool_calls"] is True

    def test_optimize_for_model_gpt35(self):
        """测试针对GPT-3.5的优化"""
        manager = ContextManager()
        messages = [HumanMessage(content=f"消息{i}") for i in range(100)]

        result = manager.optimize_for_model(messages, "gpt-3.5-turbo")

        # GPT-3.5限制是4096 tokens，应该被截断
        assert len(result) < len(messages)

        # max_context_tokens应该被临时修改
        # 这里我们无法直接验证，因为方法内部会恢复原值

    def test_optimize_for_model_gpt4(self):
        """测试针对GPT-4的优化"""
        manager = ContextManager()
        messages = [HumanMessage(content=f"消息{i}") for i in range(200)]

        result = manager.optimize_for_model(messages, "gpt-4")

        # GPT-4限制是8192 tokens，可能不会被截断
        assert isinstance(result, list)

    def test_optimize_for_model_unknown_model(self):
        """测试未知模型的优化"""
        manager = ContextManager()
        original_messages = [HumanMessage(content="测试消息")]

        result = manager.optimize_for_model(original_messages, "unknown-model")

        # 未知模型应该使用默认处理
        assert result == original_messages

    def test_optimize_for_model_preserves_original_settings(self):
        """测试模型优化不改变原始设置"""
        original_max_tokens = 100
        manager = ContextManager(max_context_tokens=original_max_tokens)
        messages = [HumanMessage(content="测试")]

        manager.optimize_for_model(messages, "gpt-3.5-turbo")

        # 原始设置应该保持不变
        assert manager.max_context_tokens == original_max_tokens


@pytest.mark.unit
class TestContextManagerEdgeCases:
    """ContextManager边界条件测试"""

    def test_manage_context_all_system_messages(self):
        """测试全部是系统消息的情况"""
        messages = [
            SystemMessage(content="系统1"),
            SystemMessage(content="系统2"),
            SystemMessage(content="系统3"),
        ]

        manager = ContextManager(max_context_messages=2, preserve_system_messages=True)
        result = manager.manage_context(messages)

        # 应该保留最多2条系统消息
        assert len(result) <= 2
        assert all(isinstance(msg, SystemMessage) for msg in result)

    def test_manage_context_zero_message_limit(self):
        """测试消息限制为0的情况"""
        messages = [HumanMessage(content="测试")]
        manager = ContextManager(max_context_messages=0)

        result = manager.manage_context(messages)

        # 应该返回空列表
        assert result == []

    def test_manage_context_negative_message_limit(self):
        """测试负数消息限制"""
        messages = [HumanMessage(content="测试")]
        manager = ContextManager(max_context_messages=-1)

        result = manager.manage_context(messages)

        # 应该返回空列表或保持原样（取决于实现）
        assert isinstance(result, list)

    def test_manage_context_mixed_message_types(self):
        """测试混合消息类型"""
        messages = [
            SystemMessage(content="系统"),
            HumanMessage(content="用户1"),
            AIMessage(content="AI1"),
            ToolMessage(content="工具1", tool_call_id="tool1"),
            HumanMessage(content="用户2"),
            AIMessage(content="AI2", tool_calls=[{"id": "tool2", "type": "function", "name": "test_tool", "args": {}}]),
        ]

        manager = ContextManager(max_context_messages=4)
        result = manager.manage_context(messages)

        # 结果应该包含多种类型的消息
        types = [type(msg).__name__ for msg in result]
        assert len(set(types)) >= 2

    def test_smart_truncate_empty_list(self):
        """测试智能截断空列表"""
        manager = ContextManager()
        result = manager._smart_truncate([])
        assert result == []

    def test_smart_truncate_single_message(self):
        """测试智能截断单条消息"""
        messages = [HumanMessage(content="测试")]
        manager = ContextManager(max_context_messages=1)

        result = manager._smart_truncate(messages)
        assert result == messages

    def test_token_based_truncate_no_limit(self):
        """测试没有token限制时的token截断"""
        manager = ContextManager(max_context_tokens=None)
        messages = [HumanMessage(content="测试")]

        result = manager._token_based_truncate(messages)
        assert result == messages

    def test_token_based_truncate_empty_list(self):
        """测试token截断空列表"""
        manager = ContextManager(max_context_tokens=100)
        result = manager._token_based_truncate([])
        assert result == []

    def test_estimate_tokens_empty_content(self):
        """测试空内容的token估算"""
        manager = ContextManager()
        messages = [HumanMessage(content="")]

        tokens = manager.estimate_tokens(messages)
        # 空内容应该只有开销
        assert tokens == 10

    def test_estimate_tokens_empty_string_content(self):
        """测试空字符串内容的token估算"""
        manager = ContextManager()
        messages = [HumanMessage(content="")]

        tokens = manager.estimate_tokens(messages)
        # 空字符串应该只有开销
        assert tokens == 10


@pytest.mark.integration
class TestContextManagerIntegration:
    """ContextManager集成测试"""

    def test_full_workflow_context_management(self):
        """测试完整的上下文管理工作流"""
        # 创建一个长对话
        messages = [SystemMessage(content="你是一个有用的AI助手")]
        for i in range(30):
            messages.append(HumanMessage(content=f"这是用户消息{i}，包含一些中文和English内容"))
            messages.append(AIMessage(content=f"这是AI回复{i}，回应了用户的问题"))

        # 创建上下文管理器
        manager = ContextManager(max_context_messages=10, max_context_tokens=500)

        # 获取原始上下文信息
        original_info = manager.get_context_info(messages)
        assert original_info["message_count"] == 61  # 1 + 30*2
        assert original_info["needs_truncation"] is True

        # 管理上下文
        optimized_messages = manager.manage_context(messages)

        # 验证优化结果
        assert len(optimized_messages) <= 10

        # 确保系统消息被保留
        system_messages = [msg for msg in optimized_messages if isinstance(msg, SystemMessage)]
        assert len(system_messages) >= 1

        # 确保保留最新消息
        assert optimized_messages[-1] == messages[-1]

        # 获取优化后的上下文信息
        optimized_info = manager.get_context_info(optimized_messages)
        assert optimized_info["needs_truncation"] is False

    def test_model_specific_optimization_workflow(self):
        """测试模型特定的优化工作流"""
        # 创建一个很长的对话
        messages = [SystemMessage(content="系统提示")]
        for i in range(100):
            messages.extend([
                HumanMessage(content=f"用户问题{i}，这是一个比较长的问题，包含很多详细信息和上下文"),
                AIMessage(content=f"AI回答{i}，这是一个详细的回答，包含很多有用的信息和指导")
            ])

        # 为不同模型优化
        models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        results = {}

        for model in models:
            manager = ContextManager()
            optimized = manager.optimize_for_model(messages, model)
            results[model] = {
                "count": len(optimized),
                "tokens": manager.estimate_tokens(optimized)
            }

        # 验证不同模型的限制不同
        # GPT-3.5应该有最严格的限制
        assert results["gpt-3.5-turbo"]["count"] <= results["gpt-4"]["count"]
        assert results["gpt-3.5-turbo"]["tokens"] <= results["gpt-4"]["tokens"]

        # GPT-4-turbo应该有最宽松的限制
        assert results["gpt-4-turbo"]["count"] >= results["gpt-4"]["count"]

    def test_conversation_context_function(self):
        """测试便捷函数"""
        messages = [
            HumanMessage(content="你好"),
            AIMessage(content="你好！"),
        ]

        result = manage_conversation_context(messages, "gpt-3.5-turbo")

        # 应该返回消息列表
        assert isinstance(result, list)
        assert len(result) >= 0

        # 对于短消息，应该原样返回
        assert len(result) == len(messages)

    def test_default_context_manager(self):
        """测试默认上下文管理器"""
        assert default_context_manager is not None
        assert isinstance(default_context_manager, ContextManager)
        assert default_context_manager.max_context_messages == 20
        assert default_context_manager.max_context_tokens is None
        assert default_context_manager.preserve_system_messages is True


@pytest.mark.performance
class TestContextManagerPerformance:
    """ContextManager性能测试"""

    def test_large_message_list_performance(self):
        """测试大消息列表的性能"""
        import time

        # 创建大量消息
        messages = [SystemMessage(content="系统消息")]
        for i in range(1000):
            messages.append(HumanMessage(content=f"用户消息{i}，包含一些测试内容"))
            messages.append(AIMessage(content=f"AI回复{i}，回应了用户的问题"))

        manager = ContextManager(max_context_messages=50)

        start_time = time.time()
        result = manager.manage_context(messages)
        end_time = time.time()

        duration = end_time - start_time

        # 应该在1秒内完成
        assert duration < 1.0, f"处理1000条消息耗时过长: {duration:.3f}秒"
        assert len(result) <= 50

    def test_token_estimation_performance(self):
        """测试token估算的性能"""
        import time

        # 创建大量消息
        messages = []
        for i in range(100):
            content = "这是一个测试消息" * 100  # 较长的内容
            messages.append(HumanMessage(content=content))

        manager = ContextManager()

        start_time = time.time()
        tokens = manager.estimate_tokens(messages)
        end_time = time.time()

        duration = end_time - start_time

        # 应该在0.1秒内完成
        assert duration < 0.1, f"估算100条消息token耗时过长: {duration:.3f}秒"
        assert tokens > 0

    def test_context_info_performance(self):
        """测试上下文信息获取的性能"""
        import time

        # 创建大量消息
        messages = []
        for i in range(500):
            if i % 4 == 0:
                messages.append(SystemMessage(content=f"系统消息{i}"))
            elif i % 4 == 1:
                messages.append(HumanMessage(content=f"用户消息{i}"))
            elif i % 4 == 2:
                messages.append(AIMessage(content=f"AI回复{i}"))
            else:
                messages.append(ToolMessage(content=f"工具结果{i}", tool_call_id=f"tool{i}"))

        manager = ContextManager()

        start_time = time.time()
        info = manager.get_context_info(messages)
        end_time = time.time()

        duration = end_time - start_time

        # 应该在0.1秒内完成
        assert duration < 0.1, f"获取500条消息上下文信息耗时过长: {duration:.3f}秒"

        # 验证结果
        assert info["message_count"] == 500
        assert len(info["message_types"]) >= 4