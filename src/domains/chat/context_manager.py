"""
聊天上下文管理器

实现多轮对话的上下文窗口管理，包括智能消息截断、
历史压缩和token管理，确保对话连贯性的同时控制上下文长度。

设计原则：
1. 保持对话连贯性
2. 智能截断长历史
3. 保留重要信息
4. 优化token使用

功能特性：
- 消息历史截断
- Token计数管理
- 上下文窗口优化
- 重要消息保留

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage

logger = logging.getLogger(__name__)


class ContextManager:
    """
    聊天上下文管理器

    负责管理多轮对话的上下文窗口，实现智能的消息历史管理，
    确保在不超出token限制的同时保持对话的连贯性。
    """

    def __init__(self,
                 max_context_messages: int = 20,
                 max_context_tokens: Optional[int] = None,
                 preserve_system_messages: bool = True):
        """
        初始化上下文管理器

        Args:
            max_context_messages: 最大保留消息数量
            max_context_tokens: 最大token数量（可选）
            preserve_system_messages: 是否保留系统消息
        """
        self.max_context_messages = max_context_messages
        self.max_context_tokens = max_context_tokens
        self.preserve_system_messages = preserve_system_messages

        logger.info(f"上下文管理器初始化: max_messages={max_context_messages}, max_tokens={max_context_tokens}")

    def manage_context(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        管理消息上下文

        根据配置的规则对消息列表进行智能截断和优化。

        Args:
            messages: 原始消息列表

        Returns:
            List[BaseMessage]: 优化后的消息列表
        """
        if not messages:
            return []

        original_count = len(messages)

        # 如果消息数量在限制内且token数量在限制内，直接返回
        if (original_count <= self.max_context_messages and
            not self.should_truncate_by_tokens(messages)):
            logger.debug(f"消息在限制内: {original_count} 条消息")
            return messages

        # 智能截断消息
        optimized_messages = self._smart_truncate(messages)

        # 如果基于token的限制仍然超出，进行更激进的截断
        if self.should_truncate_by_tokens(optimized_messages):
            optimized_messages = self._token_based_truncate(optimized_messages)

        optimized_count = len(optimized_messages)
        logger.info(f"上下文优化完成: {original_count} -> {optimized_count} 条消息")

        return optimized_messages

    def _smart_truncate(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        智能截断消息 - 简化版本

        保留最新的消息，优先保留系统消息和工具相关消息。

        Args:
            messages: 原始消息列表

        Returns:
            List[BaseMessage]: 截断后的消息列表
        """
        # 如果消息数量在限制内，直接返回
        if len(messages) <= self.max_context_messages:
            return messages

        # 分离不同类型的消息
        system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
        tool_messages = []
        dialogue_messages = []

        for i, msg in enumerate(messages):
            if isinstance(msg, SystemMessage):
                continue  # 系统消息已处理
            elif isinstance(msg, ToolMessage) or (hasattr(msg, 'tool_calls') and msg.tool_calls):
                tool_messages.append((i, msg))
            else:
                dialogue_messages.append((i, msg))

        # 优先保留系统消息
        result = []
        if self.preserve_system_messages and system_messages:
            # 如果全部是系统消息，保留至少1条，但不超过限制
            if len(system_messages) == len(messages):
                max_system = min(len(system_messages), max(1, self.max_context_messages))
            else:
                # 如果有其他类型消息，按比例分配系统消息
                max_system = min(len(system_messages), max(1, self.max_context_messages // 3))
            result.extend(system_messages[:max_system])

        # 计算剩余槽位
        remaining_slots = self.max_context_messages - len(result)

        # 保留工具消息
        if tool_messages:
            max_tools = min(len(tool_messages), remaining_slots // 2)
            recent_tools = sorted(tool_messages, key=lambda x: x[0])[-max_tools:]
            result.extend([msg for _, msg in recent_tools])
            remaining_slots -= len(recent_tools)

        # 保留最新对话消息
        if dialogue_messages and remaining_slots > 0:
            recent_dialogue = sorted(dialogue_messages, key=lambda x: x[0])[-remaining_slots:]
            result.extend([msg for _, msg in recent_dialogue])

        # 按原始顺序重新排序
        indexed_result = []
        for msg in result:
            try:
                idx = messages.index(msg)
                indexed_result.append((idx, msg))
            except ValueError:
                indexed_result.append((len(messages), msg))

        indexed_result.sort(key=lambda x: x[0])
        return [msg for _, msg in indexed_result]

    def estimate_tokens(self, messages: List[BaseMessage]) -> int:
        """
        估算消息的token数量

        简单的token估算：中文字符约等于1.5个token，
        英文单词约等于1.3个token，加上一些开销。

        Args:
            messages: 消息列表

        Returns:
            int: 估算的token数量
        """
        total_tokens = 0

        for message in messages:
            content = message.content or ""

            # 简单的token估算
            chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
            english_chars = len(content) - chinese_chars

            # 中文字符约1.5个token，英文字符约0.25个token（约4个字符一个单词）
            tokens = chinese_chars * 1.5 + english_chars * 0.25

            # 消息开销（role、metadata等）
            tokens += 10

            total_tokens += int(tokens)

        return total_tokens

    def _token_based_truncate(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        基于token数量进行激进截断

        当消息数量限制不足以满足token限制时，使用此方法。

        Args:
            messages: 消息列表

        Returns:
            List[BaseMessage]: 截断后的消息列表
        """
        if not self.max_context_tokens:
            return messages

        # 保留最新的消息，直到token数量满足要求
        result = []
        current_tokens = 0

        # 倒序遍历消息
        for message in reversed(messages):
            message_tokens = self.estimate_tokens([message])

            if current_tokens + message_tokens <= self.max_context_tokens:
                result.insert(0, message)  # 插入到开头
                current_tokens += message_tokens
            else:
                break

        logger.warning(f"Token激进截断: 保留 {len(result)} 条消息，约 {current_tokens} tokens")
        return result

    def should_truncate_by_tokens(self, messages: List[BaseMessage]) -> bool:
        """
        判断是否需要基于token数量进行截断

        Args:
            messages: 消息列表

        Returns:
            bool: 是否需要截断
        """
        if not self.max_context_tokens:
            return False

        estimated_tokens = self.estimate_tokens(messages)
        should_truncate = estimated_tokens > self.max_context_tokens

        if should_truncate:
            logger.warning(f"Token数量超限: {estimated_tokens} > {self.max_context_tokens}")

        return should_truncate

    def get_context_info(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        获取上下文信息

        Args:
            messages: 消息列表

        Returns:
            Dict[str, Any]: 上下文信息
        """
        message_count = len(messages)
        token_estimate = self.estimate_tokens(messages)

        # 按类型统计消息
        type_counts = {}
        for msg in messages:
            msg_type = type(msg).__name__
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1

        # 检查是否有工具调用
        has_tool_calls = any(
            (hasattr(msg, 'tool_calls') and msg.tool_calls) or
            (hasattr(msg, 'additional_kwargs') and
             msg.additional_kwargs.get('tool_calls') is not None)
            for msg in messages
        )

        return {
            "message_count": message_count,
            "estimated_tokens": token_estimate,
            "max_messages": self.max_context_messages,
            "max_tokens": self.max_context_tokens,
            "message_types": type_counts,
            "has_tool_calls": has_tool_calls,
            "needs_truncation": (
                message_count > self.max_context_messages or
                (self.max_context_tokens and token_estimate > self.max_context_tokens)
            ),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def optimize_for_model(self, messages: List[BaseMessage], model_name: str = "gpt-3.5-turbo") -> List[BaseMessage]:
        """
        针对特定模型优化上下文

        不同模型的上下文窗口限制不同：
        - GPT-3.5-turbo: 4096 tokens
        - GPT-4: 8192 tokens
        - GPT-4-turbo: 128k tokens

        Args:
            messages: 原始消息列表
            model_name: 模型名称

        Returns:
            List[BaseMessage]: 优化后的消息列表
        """
        # 根据模型调整限制
        model_limits = {
            "gpt-3.5-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
        }

        # 检查模型名称是否包含已知模型
        model_tokens = None
        for model, limit in model_limits.items():
            if model in model_name.lower():
                model_tokens = limit
                break

        # 如果是已知模型，使用模型特定的token限制
        if model_tokens:
            original_max_tokens = self.max_context_tokens
            self.max_context_tokens = model_tokens * 0.8  # 留20%余量

            logger.info(f"使用模型 {model_name} 的token限制: {self.max_context_tokens:.0f}")

            # 管理上下文
            result = self.manage_context(messages)

            # 恢复原始设置
            self.max_context_tokens = original_max_tokens

            return result

        # 默认处理
        return self.manage_context(messages)


# 创建默认上下文管理器实例
default_context_manager = ContextManager()

def manage_conversation_context(messages: List[BaseMessage],
                              model_name: str = "gpt-3.5-turbo") -> List[BaseMessage]:
    """
    管理对话上下文的便捷函数

    Args:
        messages: 原始消息列表
        model_name: 模型名称

    Returns:
        List[BaseMessage]: 优化后的消息列表
    """
    return default_context_manager.optimize_for_model(messages, model_name)