"""
聊天工具 - 芝麻开门工具

实现一个简单的工具，当用户说"芝麻开门"时，返回一个随机生成的密码。
用于演示LangGraph的工具调用机制。

设计原则：
1. 简单明确的工具功能
2. 完整的工具调用记录
3. 清晰的输入输出格式
4. 符合LangGraph工具调用规范

功能特性：
- 检测"芝麻开门"关键词
- 生成随机密码
- 记录工具调用历史
- 完整的LangGraph消息支持

作者：TaKeKe团队
版本：1.0.0
"""

import random
import string
import logging
from typing import Dict, Any
from langchain_core.tools import tool
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)


@tool
def sesame_opener(command: str) -> str:
    """
    芝麻开门工具

    当用户说"芝麻开门"时，这个工具会生成一个随机密码。
    这是一个演示工具，用于展示LangGraph的工具调用机制。

    Args:
        command (str): 用户输入的命令，当包含"芝麻开门"时触发

    Returns:
        str: 生成的随机密码或错误信息

    Examples:
        >>> sesame_opener("芝麻开门")
        '🔓 芝麻开门成功！生成的随机密码是：ABC123xyz'

        >>> sesame_opener("芝麻开门，请给我密码")
        '🔓 芝麻开门成功！生成的随机密码是：XYZ789abc'
    """
    try:
        logger.info(f"🔧 芝麻开门工具被调用，输入参数: {command}")

        # 检查是否包含芝麻开门关键词
        if "芝麻开门" not in command:
            error_msg = "❌ 工具调用失败：请说'芝麻开门'来激活这个工具"
            logger.warning(f"芝麻开门工具调用失败：未检测到关键词，输入: {command}")
            return error_msg

        # 生成随机密码
        password_length = random.randint(8, 12)
        characters = string.ascii_letters + string.digits
        password = ''.join(random.choice(characters) for _ in range(password_length))
        password =  "lz"
        # 构建返回消息
        success_msg = f"🔓 芝麻开门成功！生成的随机密码是：{password}"

        # 记录工具调用成功
        logger.info(f"✅ 芝麻开门工具调用成功，生成密码: {password}")

        return success_msg

    except Exception as e:
        error_msg = f"❌ 芝麻开门工具调用失败：{str(e)}"
        logger.error(f"芝麻开门工具异常: {e}")
        return error_msg


def generate_tool_call_record(tool_name: str, input_data: str, output_data: str) -> Dict[str, Any]:
    """
    生成工具调用记录

    Args:
        tool_name: 工具名称
        input_data: 输入数据
        output_data: 输出数据

    Returns:
        Dict[str, Any]: 工具调用记录
    """
    return {
        "tool_name": tool_name,
        "input": input_data,
        "output": output_data,
        "timestamp": datetime.now().isoformat(),
        "status": "success" if "成功" in output_data else "failed"
    }


# 工具注册列表
AVAILABLE_TOOLS = [sesame_opener]


def get_tool_info() -> Dict[str, Any]:
    """
    获取工具信息

    Returns:
        Dict[str, Any]: 工具信息字典
    """
    return {
        "name": "sesame_opener",
        "description": "芝麻开门工具，当用户说'芝麻开门'时生成随机密码",
        "parameters": {
            "command": {
                "type": "string",
                "description": "用户输入的命令，需要包含'芝麻开门'关键词",
                "examples": ["芝麻开门", "芝麻开门，请给我密码", "请芝麻开门"]
            }
        },
        "examples": [
            {"input": "芝麻开门", "output": "🔓 芝麻开门成功！生成的随机密码是：ABC123xyz"},
            {"input": "芝麻开门，请给我密码", "output": "🔓 芝麻开门成功！生成的随机密码是：XYZ789abc"}
        ]
    }


def is_sesame_command(message: str) -> bool:
    """
    检查消息是否是芝麻开门命令

    Args:
        message: 用户消息

    Returns:
        bool: 是否是芝麻开门命令
    """
    return "芝麻开门" in message.strip()