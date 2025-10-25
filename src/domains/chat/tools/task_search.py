"""
聊天工具 - 任务搜索

提供任务搜索功能，返回简化任务列表供LLM分析匹配。
用户可以通过自然语言描述搜索相关任务。

设计原则：
1. 简洁直接：避免过度抽象，保持代码简单易懂
2. LLM友好：返回简化任务信息，便于LLM分析匹配
3. 错误友好：提供详细的错误信息和异常处理
4. 资源安全：正确管理数据库连接和事务
5. 测试驱动：所有函数都有对应的测试用例

核心功能：
- search_tasks：返回所有任务供LLM分析（方案D）
- 简化任务信息：id, title, status, priority, 时间字段
- Token优化：限制返回数量，控制Token消耗
- 智能提示：附加提示信息供LLM分析

基于LangGraph最佳实践：
- 使用@tool装饰器
- 支持上下文管理器模式
- 兼容现有DDD架构
- 提供友好的错误信息

作者：TaKeKe团队
版本：1.0.0
"""

import logging
import json
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool

# 导入辅助函数
from .utils import get_task_service_context, _success_response, _error_response

# 配置日志
logger = logging.getLogger(__name__)


def _search_tasks_impl(query: str, limit: int = 50, state: Optional[str] = None) -> str:
    """
    搜索任务 - 返回简化任务列表供LLM分析匹配

    这个工具可以搜索用户的任务，返回简化的任务信息供LLM分析匹配。
    支持通过自然语言描述搜索相关任务，LLM需要根据任务内容进行匹配。

    功能特性：
    - 返回所有任务（最多limit个）供LLM分析
    - 简化任务信息：id, title, status, priority, 时间字段
    - 支持状态筛选：pending, completed
    - 优化Token消耗：限制返回数量

    Args:
        query (str): 搜索查询，用户的自然语言描述
                        例如："完成关于项目的任务", "找一些未完成的工作"
        limit (int): 限制返回任务数量，默认50，最多100
                       用于控制Token消耗
        state (Optional[str]): 任务状态筛选，可选值：pending, completed
                              None表示获取所有状态的任务

    Returns:
        str: JSON格式的任务列表，包含任务信息和LLM分析提示
             格式：{"success": true, "tasks": [...], "total": n, "llm_hint": "..."}

    Raises:
        ValueError: 参数验证失败时抛出
        Exception: 搜索失败时抛出异常

    Examples:
        >>> search_tasks("关于编程的任务", 20)
        '{"success": true, "tasks": [...], "total": 15, "llm_hint": "..."}'

        >>> search_tasks("未完成的工作", 30, "pending")
        '{"success": true, "tasks": [...], "total": 8, "llm_hint": "..."}'
    """
    try:
        # 参数验证
        if not query or not query.strip():
            raise ValueError("搜索查询不能为空")

        query = query.strip()

        if limit <= 0:
            raise ValueError("限制数量必须大于0")

        if limit > 100:
            limit = 100
            logger.info("搜索限制调整为100个任务")

        # 状态验证
        valid_states = [None, "pending", "completed"]
        if state not in valid_states:
            raise ValueError(f"状态筛选必须是以下之一：{[s for s in valid_states if s is not None]}")

        logger.info(f"开始搜索任务: query='{query}', limit={limit}, state={state}")

        # 使用上下文管理器获取服务
        with get_task_service_context() as ctx:
            task_service = ctx['task_service']

            # 调用TaskService.get_tasks获取所有任务
            # 注意：这里暂时硬编码user_id，实际应该从上下文获取
            # TODO: 实现用户上下文管理，获取当前用户ID
            all_tasks = task_service.get_tasks(
                user_id="temp-user-id",  # 临时用户ID，需要后续实现用户上下文
                status=state,
                parent_id=None,
                limit=limit,
                offset=0
            )

            # 进一步简化任务信息，减少Token消耗
            # 只保留LLM分析需要的核心字段
            simplified_tasks = []
            for task in all_tasks[:limit]:  # 确保不超过limit
                simplified_task = {
                    "id": task["id"],
                    "title": task["title"],
                    "description": task["description"][:100] + "..." if task["description"] and len(task["description"]) > 100 else task["description"],
                    "status": task["status"],
                    "priority": task["priority"],
                    "created_at": task["created_at"],
                    "completion_percentage": task.get("completion_percentage", 0.0)
                }
                simplified_tasks.append(simplified_task)

            # 估算Token消耗（粗略估算：1个字符约等于0.25个tokens）
            tasks_json = json.dumps(simplified_tasks, ensure_ascii=False)
            estimated_tokens = int(len(tasks_json) * 0.25)

            # 构建LLM分析提示
            llm_hint = (
                f"用户搜索：'{query}'\n"
                f"找到{len(simplified_tasks)}个任务（估算Token消耗：{estimated_tokens}）\n"
                "请根据用户意图分析任务匹配度：\n"
                "1. 重点关注任务标题和描述的关键词匹配\n"
                "2. 考虑任务状态（pending/completed）是否符合用户需求\n"
                "3. 优先级可作为参考\n"
                "4. 用完成百分比判断任务进度\n"
                f"5. 返回最相关的{min(5, len(simplified_tasks))}个任务"
            )

            # 构建响应
            response = {
                "success": True,
                "query": query,
                "tasks": simplified_tasks,
                "total": len(simplified_tasks),
                "limit": limit,
                "state_filter": state,
                "estimated_tokens": estimated_tokens,
                "llm_hint": llm_hint,
                "message": f"找到{len(simplified_tasks)}个任务，请根据LLM提示分析匹配度"
            }

            logger.info(f"任务搜索完成: 找到{len(simplified_tasks)}个任务，估算{estimated_tokens}tokens")
            return json.dumps(response, ensure_ascii=False, indent=2)

    except ValueError as ve:
        # 参数验证错误
        error_msg = str(ve)
        logger.warning(f"任务搜索参数错误: {error_msg}")
        error_response = _error_response(error_msg, "INVALID_PARAMETERS")
        return json.dumps(error_response, ensure_ascii=False)

    except Exception as e:
        # 其他错误
        error_msg = f"任务搜索失败: {str(e)}"
        logger.error(f"任务搜索异常: {error_msg}")
        error_response = _error_response(error_msg, "SEARCH_FAILED")
        return json.dumps(error_response, ensure_ascii=False)


def estimate_token_count(text: str) -> int:
    """
    估算文本的Token数量

    粗略估算：1个中文字符约等于1.5个tokens，1个英文字符约等于0.25个tokens

    Args:
        text (str): 要估算的文本

    Returns:
        int: 估算的Token数量
    """
    if not text:
        return 0

    # 统计中文字符和非中文字符
    # 扩展中文字符范围，包含常用中文标点
    chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff' or c in '，。？！；：""''（）【】《》'])
    other_chars = len(text) - chinese_chars

    # 粗略估算
    estimated_tokens = int(chinese_chars * 1.5 + other_chars * 0.25)

    return estimated_tokens


def validate_search_parameters(query: str, limit: int, state: Optional[str]) -> Dict[str, Any]:
    """
    验证搜索参数

    Args:
        query (str): 搜索查询
        limit (int): 限制数量
        state (Optional[str]): 状态筛选

    Returns:
        Dict[str, Any]: 验证结果
    """
    errors = []

    # 验证查询
    if not query or not query.strip():
        errors.append("搜索查询不能为空")

    # 验证限制
    if limit <= 0:
        errors.append("限制数量必须大于0")

    if limit > 100:
        errors.append("限制数量不能超过100")

    # 验证状态
    valid_states = [None, "pending", "completed"]
    if state not in valid_states:
        errors.append(f"状态筛选必须是以下之一：{[s for s in valid_states if s is not None]}")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


@tool
def search_tasks(query: str, limit: int = 50, state: Optional[str] = None) -> str:
    """
    搜索任务 - 返回简化任务列表供LLM分析匹配（LangGraph工具版本）

    这是search_tasks工具的LangGraph版本，使用@tool装饰器。
    实际逻辑由_search_tasks_impl实现。

    Args:
        query (str): 搜索查询，用户的自然语言描述
        limit (int): 限制返回任务数量，默认50，最多100
        state (Optional[str]): 任务状态筛选，可选值：pending, completed

    Returns:
        str: JSON格式的任务列表，包含任务信息和LLM分析提示
    """
    return _search_tasks_impl(query, limit, state)


# 工具注册列表（包含@tool版本）
AVAILABLE_TOOLS = [search_tasks]


def get_tool_info() -> Dict[str, Any]:
    """
    获取工具信息

    Returns:
        Dict[str, Any]: 工具信息字典
    """
    return {
        "name": "search_tasks",
        "description": "搜索任务，返回简化任务列表供LLM分析匹配",
        "parameters": {
            "query": {
                "type": "string",
                "description": "搜索查询，用户的自然语言描述",
                "examples": ["完成关于项目的任务", "找一些未完成的工作", "重要的任务"]
            },
            "limit": {
                "type": "integer",
                "description": "限制返回任务数量，默认50，最多100",
                "default": 50,
                "range": [1, 100]
            },
            "state": {
                "type": "string",
                "description": "任务状态筛选，可选值：pending, completed",
                "default": None,
                "examples": ["pending", "completed"]
            }
        },
        "examples": [
            {
                "input": {"query": "关于编程的任务", "limit": 20},
                "output": "包含编程相关任务的JSON列表"
            },
            {
                "input": {"query": "未完成的工作", "limit": 30, "state": "pending"},
                "output": "包含未完成任务JSON列表"
            }
        ],
        "token_usage": {
            "description": "100个任务约8000 tokens",
            "optimization": "通过限制返回数量控制Token消耗"
        }
    }