"""
聊天工具 - 计算器

提供简单的加减法计算功能，作为LangGraph工具调用的示例实现。
这是一个占位工具，用于演示LangGraph的工具集成能力。

设计原则：
1. 简单直接的加减法计算
2. 完整的错误处理和输入验证
3. 清晰的工具描述和参数说明
4. 符合LangGraph工具调用规范

功能特性：
- 支持简单的加法计算
- 支持简单的减法计算
- 输入表达式验证
- 错误处理和异常管理
- 详细的计算结果说明

作者：TaKeKe团队
版本：1.0.0
"""

import re
import logging
from typing import Union, Dict, Any
from langchain_core.tools import tool

# 配置日志
logger = logging.getLogger(__name__)


@tool
def calculator(expression: str) -> str:
    """
    计算简单的加减法表达式

    这个工具可以计算只包含加减法的数学表达式，例如：
    - "1+2" → 3
    - "10-5" → 5
    - "1+2-3+4" → 4

    Args:
        expression (str): 要计算的数学表达式，只能包含数字、加号(+)和减号(-)
                           支持整数和小数，例如："1+2.5-3"

    Returns:
        str: 计算结果，格式为："计算结果：[结果]"

    Raises:
        ValueError: 当表达式格式不正确或包含不支持的运算符时

    Examples:
        >>> calculator("1+2")
        '计算结果：3'

        >>> calculator("10-5+2")
        '计算结果：7'

        >>> calculator("1.5+2.5")
        '计算结果：4.0'
    """
    try:
        # 清理输入表达式
        cleaned_expr = expression.strip().replace(" ", "")

        # 验证表达式格式
        if not cleaned_expr:
            raise ValueError("表达式不能为空")

        # 检查是否只包含数字、加减号和小数点
        if not re.match(r'^[0-9+\.\-]+$', cleaned_expr):
            raise ValueError("表达式只能包含数字、加号(+)、减号(-)和小数点(.)")

        # 检查表达式是否以数字开头和结尾
        if cleaned_expr[0] in "+-" or cleaned_expr[-1] in "+-":
            raise ValueError("表达式必须以数字开头和结尾")

        # 检查是否有连续的运算符
        if re.search(r'[+\-]{2,}', cleaned_expr):
            raise ValueError("不能有连续的运算符")

        # 使用Python的eval进行安全计算（仅限加减法）
        # 在实际环境中，你可能想要更安全的计算方式
        result = eval(cleaned_expr)

        # 格式化结果
        if isinstance(result, int):
            formatted_result = str(result)
        elif isinstance(result, float):
            # 如果是整数的小数，显示为整数
            if result.is_integer():
                formatted_result = str(int(result))
            else:
                formatted_result = f"{result:.2f}".rstrip('0').rstrip('.')
        else:
            formatted_result = str(result)

        logger.info(f"计算器工具计算成功: {expression} = {result}")

        return f"计算结果：{formatted_result}"

    except ValueError as ve:
        error_msg = f"表达式格式错误：{str(ve)}"
        logger.warning(f"计算器工具错误: {error_msg}")
        return error_msg

    except ZeroDivisionError:
        error_msg = "计算错误：除数不能为零"
        logger.warning(f"计算器工具错误: {error_msg}")
        return error_msg

    except Exception as e:
        error_msg = f"计算失败：{str(e)}"
        logger.error(f"计算器工具异常: {error_msg}")
        return error_msg


# 工具注册列表
AVAILABLE_TOOLS = [calculator]


def get_tool_info() -> Dict[str, Any]:
    """
    获取工具信息

    Returns:
        Dict[str, Any]: 工具信息字典
    """
    return {
        "name": "calculator",
        "description": "计算简单的加减法表达式",
        "parameters": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式，只能包含数字、加号(+)和减号(-)",
                "examples": ["1+2", "10-5", "1+2-3+4", "1.5+2.5"]
            }
        },
        "examples": [
            {"input": "1+2", "output": "计算结果：3"},
            {"input": "10-5+2", "output": "计算结果：7"},
            {"input": "1.5+2.5", "output": "计算结果：4"}
        ]
    }


def validate_expression(expression: str) -> bool:
    """
    验证表达式是否有效

    Args:
        expression: 要验证的表达式

    Returns:
        bool: 表达式是否有效
    """
    try:
        cleaned_expr = expression.strip().replace(" ", "")

        # 基本格式检查
        if not cleaned_expr:
            return False

        if not re.match(r'^[0-9+\.\-]+$', cleaned_expr):
            return False

        if cleaned_expr[0] in "+-" or cleaned_expr[-1] in "+-":
            return False

        if re.search(r'[+\-]{2,}', cleaned_expr):
            return False

        # 尝试计算
        eval(cleaned_expr)
        return True

    except:
        return False


def calculate_safely(expression: str) -> Union[float, int, None]:
    """
    安全地计算表达式

    Args:
        expression: 要计算的表达式

    Returns:
        计算结果，失败时返回None
    """
    try:
        if not validate_expression(expression):
            return None

        cleaned_expr = expression.strip().replace(" ", "")
        result = eval(cleaned_expr)

        # 统一返回类型：如果是整数小数则返回整数
        if isinstance(result, float) and result.is_integer():
            return int(result)

        return result

    except:
        return None