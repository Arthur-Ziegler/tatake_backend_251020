"""
聊天系统提示词

定义LangGraph聊天系统的系统提示词和模板，指导AI的行为和响应风格。
保持简洁明了，避免过于复杂的指令。

设计原则：
1. 简单明确的AI行为指导
2. 友好的交互风格定义
3. 清晰的工具使用说明
4. 支持动态参数注入

功能特性：
- 系统提示词模板
- 用户上下文支持
- 工具调用指导
- 会话管理规则

作者：TaKeKe团队
版本：1.0.0
"""

from typing import Optional, Dict, Any


# 基础系统提示词
SYSTEM_PROMPT = """你是一个友好的AI助手，可以帮助用户进行日常对话。

你的主要职责：
1. 提供友好、有用的对话体验
2. 在需要时使用计算器工具进行简单的加减法计算
3. 保持对话连贯性和上下文理解

计算器工具使用说明：
- 当用户需要进行数学计算时，主动使用calculator工具
- 工具可以处理简单的加减法表达式，如"1+2"、"10-5"、"1+2-3+4"等
- 在计算完成后，向用户解释结果

对话风格：
- 友好自然，避免过于正式
- 简洁明了，不要过于冗长
- 在不确定时主动询问澄清

当前会话信息：
- 用户ID: {user_id}
- 会话ID: {session_id}

请记住这些信息，在对话中为用户提供个性化的帮助。"""


def format_system_prompt(user_id: str, session_id: str, title: Optional[str] = None) -> str:
    """
    格式化系统提示词

    根据用户和会话信息动态生成系统提示词。

    Args:
        user_id: 用户ID
        session_id: 会话ID
        title: 会话标题（可选）

    Returns:
        str: 格式化后的系统提示词
    """
    prompt = SYSTEM_PROMPT.format(
        user_id=user_id,
        session_id=session_id
    )

    if title:
        prompt += f"\n\n当前会话主题：{title}"

    return prompt


def get_context_info(user_id: str, session_id: str, message_count: int = 0) -> Dict[str, Any]:
    """
    获取上下文信息字典

    为AI提供会话相关的上下文信息。

    Args:
        user_id: 用户ID
        session_id: 会话ID
        message_count: 当前消息数量

    Returns:
        Dict[str, Any]: 上下文信息字典
    """
    return {
        "user_id": user_id,
        "session_id": session_id,
        "message_count": message_count,
        "available_tools": ["calculator"],
        "guidelines": [
            "保持友好和专业的对话风格",
            "在需要计算时使用工具",
            "提供准确的信息",
            "在不确定时主动询问"
        ]
    }


# 工具使用指导
TOOL_USAGE_GUIDE = """
工具使用指南：

1. 计算器工具 (calculator)
   - 用途：进行简单的加减法计算
   - 触发条件：用户提到任何数学计算需求
   - 输入格式：数学表达式，如"1+2"、"10-5"、"1.5+2.5"等
   - 输出格式：直接使用工具返回的结果

2. 使用原则
   - 主动识别用户的计算需求
   - 不要等用户明确要求使用工具
   - 在工具返回结果后，向用户解释计算结果

3. 示例对话
   用户："帮我算一下1+2等于多少？"
   AI：(使用calculator工具"1+2")"计算结果：3"
   AI："1+2等于3，还有其他需要计算的吗？"
"""


def get_tool_instructions() -> str:
    """
    获取工具使用指导

    Returns:
        str: 工具使用指导文本
    """
    return TOOL_USAGE_GUIDE


# 会话管理规则
SESSION_MANAGEMENT_RULES = """
会话管理规则：

1. 会话连续性
   - 记住之前的对话内容
   - 引用之前的对话要点
   - 保持话题的连贯性

2. 用户个性化
   - 使用用户ID识别用户
   - 记住用户提到的个人信息
   - 提供个性化的建议

3. 会话边界
   - 在会话开始时进行友好问候
   - 适当总结会话要点
   - 为后续对话做好铺垫
"""


def format_welcome_message(user_id: str, session_id: str, title: Optional[str] = None) -> str:
    """
    格式化欢迎消息

    生成新会话的欢迎消息。

    Args:
        user_id: 用户ID
        session_id: 会话ID
        title: 会话标题（可选）

    Returns:
        str: 欢迎消息
    """
    base_message = "你好！我是你的AI助手，很高兴为你服务。"

    if title:
        base_message += f"我看到这次的会话主题是「{title}」。"

    base_message += """
我可以帮你：
- 进行日常对话和问答
- 进行简单的数学计算
- 提供友好的建议和帮助

有什么我可以帮助你的吗？
"""

    return base_message


def format_session_summary(messages: list) -> str:
    """
    格式化会话总结

    生成会话总结信息。

    Args:
        messages: 消息列表

    Returns:
        str: 会话总结
    """
    if not messages:
        return "这是一个新的会话。"

    message_count = len(messages)

    summary = f"本次会话共包含{message_count}条消息。"

    if message_count > 1:
        summary += "我们讨论了一些有趣的话题。"

    summary += "期待下次继续我们的对话！"

    return summary