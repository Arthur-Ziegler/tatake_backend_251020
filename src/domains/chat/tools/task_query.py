"""
聊天工具 - 任务查询

提供任务的条件查询和详情获取功能，支持LangGraph工具调用。

基于LangChain最佳实践实现：
- 使用@tool装饰器创建工具
- 完整的类型注解和参数验证
- 详细的错误处理和日志记录
- 遵循KISS和YAGNI设计原则

功能特性：
1. query_tasks - 条件查询任务列表（状态、父任务、分页）
2. get_task_detail - 获取任务详情（包含子任务信息）
3. 完整的权限验证和错误处理
4. 统一的响应格式

依赖关系：
- 依赖sub1的utils.py辅助函数
- 使用TaskService进行业务逻辑处理
- 遵循现有DDD架构模式

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from langchain_core.tools import tool

# 导入辅助函数
from .utils import (
    get_task_service_context,
    safe_uuid_convert,
    _success_response,
    _error_response
)

# 配置日志
logger = logging.getLogger(__name__)


@tool
def query_tasks(
    status: Optional[str] = None,
    parent_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> str:
    """
    查询任务列表

    根据指定条件查询用户的任务列表，支持状态筛选、父任务筛选和分页。

    查询条件：
    - status: 任务状态筛选（可选），如 'pending', 'completed', 'cancelled'
    - parent_id: 父任务ID筛选（可选），用于查询特定父任务的子任务
    - limit: 返回结果数量限制，默认20，最大100
    - offset: 分页偏移量，默认0

    Args:
        status (Optional[str]): 任务状态筛选，例如：'pending', 'completed', 'cancelled'
        parent_id (Optional[str]): 父任务ID，用于查询子任务列表
        limit (int): 返回结果数量限制，范围1-100，默认20
        offset (int): 分页偏移量，用于翻页，默认0

    Returns:
        str: JSON格式的查询结果，包含任务列表和分页信息

    Raises:
        ValueError: 当参数格式不正确时
        Exception: 当查询失败时

    Examples:
        >>> query_tasks()
        '{"success": true, "data": {"tasks": [...], "total": 5}, "message": "查询成功"}'

        >>> query_tasks(status="completed", limit=10)
        '{"success": true, "data": {"tasks": [...], "total": 3}, "message": "查询成功"}'
    """
    try:
        logger.info(f"开始查询任务列表: status={status}, parent_id={parent_id}, limit={limit}, offset={offset}")

        # 参数验证
        if limit <= 0 or limit > 100:
            raise ValueError("limit参数必须在1-100之间")

        if offset < 0:
            raise ValueError("offset参数不能为负数")

        # 转换parent_id为UUID（如果提供）
        parent_uuid = safe_uuid_convert(parent_id)

        # 使用服务上下文执行查询
        with get_task_service_context() as ctx:
            task_service = ctx['task_service']

            # 调用TaskService的get_tasks方法
            tasks = task_service.get_tasks(
                user_id="placeholder",  # TODO: 从上下文获取实际用户ID
                status=status,
                parent_id=str(parent_uuid) if parent_uuid else None,
                limit=limit,
                offset=offset
            )

            # 构建响应数据
            result_data = {
                "tasks": tasks,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "count": len(tasks)
                }
            }

            # 返回成功响应
            response = _success_response(
                data=result_data,
                message=f"成功查询到{len(tasks)}个任务"
            )

            logger.info(f"任务查询成功: 返回{len(tasks)}个任务")
            import json
            return json.dumps(response, ensure_ascii=False, indent=2)

    except ValueError as ve:
        error_msg = f"参数错误: {str(ve)}"
        logger.warning(f"query_tasks参数验证失败: {error_msg}")
        response = _error_response(error_msg, "INVALID_PARAMETERS")
        import json
        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"查询任务列表失败: {str(e)}"
        logger.error(f"query_tasks执行失败: {error_msg}")
        response = _error_response(error_msg, "QUERY_FAILED")
        import json
        return json.dumps(response, ensure_ascii=False, indent=2)


@tool
def get_task_detail(task_id: str) -> str:
    """
    获取任务详情

    根据任务ID获取任务的详细信息，包含任务的所有属性和子任务信息。

    Args:
        task_id (str): 任务ID，必须是有效的UUID格式

    Returns:
        str: JSON格式的任务详情，包含完整任务信息

    Raises:
        ValueError: 当task_id格式不正确时
        Exception: 当查询失败时

    Examples:
        >>> get_task_detail("550e8400-e29b-41d4-a716-446655440000")
        '{"success": true, "data": {"id": "...", "title": "...", "status": "..."}, "message": "获取成功"}'
    """
    try:
        logger.info(f"开始获取任务详情: task_id={task_id}")

        # 参数验证 - 转换并验证UUID
        if not task_id or not task_id.strip():
            raise ValueError("任务ID不能为空")

        task_uuid = safe_uuid_convert(task_id.strip())

        # 使用服务上下文执行查询
        with get_task_service_context() as ctx:
            task_service = ctx['task_service']

            # 调用TaskService的get_task方法
            task = task_service.get_task(
                task_id=task_uuid,
                user_id="placeholder"  # TODO: 从上下文获取实际用户ID
            )

            # 构建响应数据
            result_data = {
                "task": task
            }

            # 返回成功响应
            response = _success_response(
                data=result_data,
                message="任务详情获取成功"
            )

            logger.info(f"任务详情获取成功: task_id={task_id}")
            import json
            return json.dumps(response, ensure_ascii=False, indent=2)

    except ValueError as ve:
        error_msg = f"参数错误: {str(ve)}"
        logger.warning(f"get_task_detail参数验证失败: {error_msg}")
        response = _error_response(error_msg, "INVALID_PARAMETERS")
        import json
        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        # 处理业务异常（如任务不存在、无权限等）
        error_msg = f"获取任务详情失败: {str(e)}"
        logger.error(f"get_task_detail执行失败: {error_msg}")
        response = _error_response(error_msg, "GET_DETAIL_FAILED")
        import json
        return json.dumps(response, ensure_ascii=False, indent=2)


# 导出工具列表，用于ChatGraph绑定
AVAILABLE_TOOLS = [query_tasks, get_task_detail]


def get_tool_info() -> Dict[str, Any]:
    """
    获取工具信息

    Returns:
        Dict[str, Any]: 工具信息字典
    """
    return {
        "tools": [
            {
                "name": "query_tasks",
                "description": "查询任务列表，支持状态筛选、父任务筛选和分页",
                "parameters": {
                    "status": {
                        "type": "string",
                        "description": "任务状态筛选（可选）：'pending', 'completed', 'cancelled'",
                        "required": False
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "父任务ID，用于查询子任务",
                        "required": False
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制，范围1-100，默认20",
                        "required": False,
                        "default": 20
                    },
                    "offset": {
                        "type": "integer",
                        "description": "分页偏移量，用于翻页，默认0",
                        "required": False,
                        "default": 0
                    }
                },
                "examples": [
                    {"input": {}, "output": "返回前20个任务"},
                    {"input": {"status": "completed", "limit": 10}, "output": "返回前10个已完成的任务"},
                    {"input": {"parent_id": "550e8400-e29b-41d4-a716-446655440000"}, "output": "返回指定父任务的子任务"}
                ]
            },
            {
                "name": "get_task_detail",
                "description": "获取任务详情，包含完整任务信息",
                "parameters": {
                    "task_id": {
                        "type": "string",
                        "description": "任务ID，必须是有效的UUID格式",
                        "required": True
                    }
                },
                "examples": [
                    {"input": {"task_id": "550e8400-e29b-41d4-a716-446655440000"}, "output": "返回指定任务的详细信息"}
                ]
            }
        ]
    }


def validate_query_parameters(status: Optional[str], parent_id: Optional[str], limit: int, offset: int) -> bool:
    """
    验证查询参数

    Args:
        status: 任务状态
        parent_id: 父任务ID
        limit: 限制数量
        offset: 偏移量

    Returns:
        bool: 参数是否有效
    """
    try:
        # 验证limit和offset
        if limit <= 0 or limit > 100:
            return False

        if offset < 0:
            return False

        # 验证status（如果提供）
        if status:
            valid_statuses = ['pending', 'completed', 'cancelled', 'in_progress']
            if status.lower() not in valid_statuses:
                return False

        # 验证parent_id（如果提供）
        if parent_id:
            safe_uuid_convert(parent_id)

        return True

    except:
        return False


def validate_task_id(task_id: str) -> bool:
    """
    验证任务ID

    Args:
        task_id: 任务ID

    Returns:
        bool: 任务ID是否有效
    """
    try:
        if not task_id or not task_id.strip():
            return False

        safe_uuid_convert(task_id.strip())
        return True

    except:
        return False