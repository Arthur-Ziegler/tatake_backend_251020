"""
聊天工具 - 任务CRUD工具

实现任务的创建、更新、删除工具，支持通过自然语言管理任务。
基于LangGraph工具调用机制，与TaskService层集成。

设计原则：
1. 简洁直接：避免过度抽象，保持代码简单易懂
2. 错误友好：提供详细的错误信息和异常处理
3. 类型安全：使用类型注解确保参数类型正确
4. 资源安全：正确管理数据库连接和事务
5. 测试驱动：所有函数都有对应的测试用例

核心功能：
1. create_task：创建新任务（支持全字段）
2. update_task：更新现有任务
3. delete_task：软删除任务

基于LangGraph最佳实践：
- 使用@tool装饰器确保工具调用规范
- 支持上下文管理器模式
- 兼容现有DDD架构
- 提供友好的错误信息

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

# 导入辅助函数
from .utils import (
    get_task_service_context,
    safe_uuid_convert,
    parse_datetime,
    _success_response,
    _error_response
)

# 导入Schema定义
from src.domains.task.schemas import CreateTaskRequest, UpdateTaskRequest

# 配置日志
logger = logging.getLogger(__name__)


@tool
def create_task(
    title: str,
    description: Optional[str] = None,
    status: str = "pending",
    priority: str = "medium",
    parent_id: Optional[str] = None,
    tags: Optional[str] = None,
    due_date: Optional[str] = None,
    planned_start_time: Optional[str] = None,
    planned_end_time: Optional[str] = None
) -> str:
    """
    创建新任务工具

    通过自然语言创建新的任务，支持设置任务的各种属性。
    所有时间字段使用ISO 8601格式。

    Args:
        title (str): 任务标题，必填，1-100字符
        description (str, optional): 任务描述，最多5000字符
        status (str): 任务状态，默认为"pending"，可选值：pending/in_progress/completed
        priority (str): 任务优先级，默认为"medium"，可选值：low/medium/high
        parent_id (str, optional): 父任务ID，支持任务树结构
        tags (str, optional): 任务标签，逗号分隔，如："标签1,标签2"
        due_date (str, optional): 截止日期，ISO 8601格式，如："2024-12-31T23:59:59Z"
        planned_start_time (str, optional): 计划开始时间，ISO 8601格式
        planned_end_time (str, optional): 计划结束时间，ISO 8601格式

    Returns:
        str: JSON格式的创建结果，包含任务ID和详细信息

    Examples:
        >>> create_task("完成项目文档", "编写技术文档", "high", "2024-12-31T23:59:59Z")
        '{"success": true, "data": {"task_id": "uuid"}, "message": "任务创建成功"}'

        >>> create_task("测试任务", parent_id="parent-uuid")
        '{"success": true, "data": {"task_id": "uuid"}, "message": "任务创建成功"}'
    """
    try:
        logger.info(f"🔧 create_task工具被调用，标题: {title}")

        # 获取任务服务上下文
        with get_task_service_context() as ctx:
            task_service = ctx['task_service']

            # 解析parent_id（如果提供）
            parent_uuid = safe_uuid_convert(parent_id)

            # 解析时间字段
            parsed_due_date = parse_datetime(due_date)
            parsed_start_time = parse_datetime(planned_start_time)
            parsed_end_time = parse_datetime(planned_end_time)

            # 解析标签（如果提供）
            tag_list = []
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

            # 构造创建任务请求
            create_request = CreateTaskRequest(
                title=title,
                description=description,
                status=status,
                priority=priority,
                parent_id=parent_uuid,
                tags=tag_list,
                due_date=parsed_due_date,
                planned_start_time=parsed_start_time,
                planned_end_time=parsed_end_time
            )

            # 暂时使用固定的用户ID（后续可以从上下文获取）
            user_id = safe_uuid_convert("550e8400-e29b-41d4-a716-446655440000")

            # 调用任务服务创建任务
            result = task_service.create_task(create_request, user_id)

            # 构建成功响应
            response = _success_response(result, "任务创建成功")

            logger.info(f"✅ create_task工具调用成功，任务ID: {result.get('task_id')}")
            return str(response).replace("'", '"')  # 返回JSON字符串

    except ValueError as e:
        # 处理参数验证错误
        error_msg = f"参数验证失败: {str(e)}"
        logger.warning(f"❌ create_task参数验证失败: {e}")
        response = _error_response(error_msg, "VALIDATION_ERROR")
        return str(response).replace("'", '"')

    except Exception as e:
        # 处理其他异常
        error_msg = f"创建任务失败: {str(e)}"
        logger.error(f"❌ create_task工具异常: {e}")
        response = _error_response(error_msg, "CREATE_TASK_ERROR")
        return str(response).replace("'", '"')


@tool
def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    parent_id: Optional[str] = None,
    tags: Optional[str] = None,
    due_date: Optional[str] = None
) -> str:
    """
    更新任务工具

    通过自然语言更新现有任务的各种属性。所有参数都是可选的，
    只更新提供的字段，未提供的字段保持不变。

    Args:
        task_id (str): 任务ID，必填
        title (str, optional): 新的任务标题
        description (str, optional): 新的任务描述
        status (str, optional): 新的任务状态，可选值：pending/in_progress/completed
        priority (str, optional): 新的任务优先级，可选值：low/medium/high
        parent_id (str, optional): 新的父任务ID，设置为None表示移至根级别
        tags (str, optional): 新的任务标签，逗号分隔，会完全替换现有标签
        due_date (str, optional): 新的截止日期，ISO 8601格式

    Returns:
        str: JSON格式的更新结果，包含更新后的任务信息

    Examples:
        >>> update_task("task-uuid", title="更新后的标题", status="completed")
        '{"success": true, "data": {...}, "message": "任务更新成功"}'

        >>> update_task("task-uuid", parent_id=None)
        '{"success": true, "data": {...}, "message": "任务更新成功"}'
    """
    try:
        logger.info(f"🔧 update_task工具被调用，任务ID: {task_id}")

        # 获取任务服务上下文
        with get_task_service_context() as ctx:
            task_service = ctx['task_service']

            # 转换任务ID
            task_uuid = safe_uuid_convert(task_id)
            if task_uuid is None:
                raise ValueError("任务ID不能为空")

            # 转换parent_id（如果提供）
            parent_uuid = safe_uuid_convert(parent_id)

            # 解析时间字段（如果提供）
            parsed_due_date = parse_datetime(due_date)

            # 解析标签（如果提供）
            tag_list = None
            if tags is not None:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

            # 构造更新任务请求（只包含非None的字段）
            update_data = {}
            if title is not None:
                update_data['title'] = title
            if description is not None:
                update_data['description'] = description
            if status is not None:
                update_data['status'] = status
            if priority is not None:
                update_data['priority'] = priority
            if parent_id is not None:
                update_data['parent_id'] = parent_uuid
            if tags is not None:
                update_data['tags'] = tag_list
            if due_date is not None:
                update_data['due_date'] = parsed_due_date

            update_request = UpdateTaskRequest(**update_data)

            # 暂时使用固定的用户ID（后续可以从上下文获取）
            user_id = safe_uuid_convert("550e8400-e29b-41d4-a716-446655440000")

            # 调用任务服务更新任务
            result = task_service.update_task_with_tree_structure(task_uuid, update_request, user_id)

            # 构建成功响应
            response = _success_response(result, "任务更新成功")

            logger.info(f"✅ update_task工具调用成功，任务ID: {task_id}")
            return str(response).replace("'", '"')  # 返回JSON字符串

    except ValueError as e:
        # 处理参数验证错误
        error_msg = f"参数验证失败: {str(e)}"
        logger.warning(f"❌ update_task参数验证失败: {e}")
        response = _error_response(error_msg, "VALIDATION_ERROR")
        return str(response).replace("'", '"')

    except Exception as e:
        # 处理其他异常
        error_msg = f"更新任务失败: {str(e)}"
        logger.error(f"❌ update_task工具异常: {e}")
        response = _error_response(error_msg, "UPDATE_TASK_ERROR")
        return str(response).replace("'", '"')


@tool
def delete_task(task_id: str) -> str:
    """
    删除任务工具

    通过自然语言软删除指定任务及其所有子任务。
    软删除意味着任务数据仍然保留，但标记为已删除状态。

    Args:
        task_id (str): 要删除的任务ID，必填

    Returns:
        str: JSON格式的删除结果，包含删除确认信息

    Examples:
        >>> delete_task("task-uuid")
        '{"success": true, "data": {"deleted_task_id": "task-uuid"}, "message": "任务删除成功"}'

        >>> delete_task("invalid-uuid")
        '{"success": false, "error": "任务不存在", "error_code": "TASK_NOT_FOUND"}'
    """
    try:
        logger.info(f"🔧 delete_task工具被调用，任务ID: {task_id}")

        # 获取任务服务上下文
        with get_task_service_context() as ctx:
            task_service = ctx['task_service']

            # 转换任务ID
            task_uuid = safe_uuid_convert(task_id)
            if task_uuid is None:
                raise ValueError("任务ID不能为空")

            # 暂时使用固定的用户ID（后续可以从上下文获取）
            user_id = safe_uuid_convert("550e8400-e29b-41d4-a716-446655440000")

            # 调用任务服务删除任务
            result = task_service.delete_task(task_uuid, user_id)

            # 构建成功响应
            response = _success_response(result, "任务删除成功")

            logger.info(f"✅ delete_task工具调用成功，任务ID: {task_id}")
            return str(response).replace("'", '"')  # 返回JSON字符串

    except ValueError as e:
        # 处理参数验证错误
        error_msg = f"参数验证失败: {str(e)}"
        logger.warning(f"❌ delete_task参数验证失败: {e}")
        response = _error_response(error_msg, "VALIDATION_ERROR")
        return str(response).replace("'", '"')

    except Exception as e:
        # 处理其他异常
        error_msg = f"删除任务失败: {str(e)}"
        logger.error(f"❌ delete_task工具异常: {e}")
        response = _error_response(error_msg, "DELETE_TASK_ERROR")
        return str(response).replace("'", '"')


# 工具注册列表
AVAILABLE_TOOLS = [create_task, update_task, delete_task]


def get_tool_info() -> Dict[str, Any]:
    """
    获取任务CRUD工具信息

    Returns:
        Dict[str, Any]: 工具信息字典
    """
    return {
        "tools": [
            {
                "name": "create_task",
                "description": "创建新任务，支持设置标题、描述、优先级、截止时间等",
                "parameters": {
                    "title": {"type": "string", "description": "任务标题，必填"},
                    "description": {"type": "string", "description": "任务描述，可选"},
                    "status": {"type": "string", "description": "任务状态：pending/in_progress/completed"},
                    "priority": {"type": "string", "description": "任务优先级：low/medium/high"},
                    "parent_id": {"type": "string", "description": "父任务ID，可选"},
                    "tags": {"type": "string", "description": "任务标签，逗号分隔"},
                    "due_date": {"type": "string", "description": "截止日期，ISO 8601格式"},
                    "planned_start_time": {"type": "string", "description": "计划开始时间，ISO 8601格式"},
                    "planned_end_time": {"type": "string", "description": "计划结束时间，ISO 8601格式"}
                }
            },
            {
                "name": "update_task",
                "description": "更新现有任务，支持部分更新",
                "parameters": {
                    "task_id": {"type": "string", "description": "任务ID，必填"},
                    "title": {"type": "string", "description": "新的任务标题"},
                    "description": {"type": "string", "description": "新的任务描述"},
                    "status": {"type": "string", "description": "新的任务状态"},
                    "priority": {"type": "string", "description": "新的任务优先级"},
                    "parent_id": {"type": "string", "description": "新的父任务ID"},
                    "tags": {"type": "string", "description": "新的任务标签"},
                    "due_date": {"type": "string", "description": "新的截止日期"}
                }
            },
            {
                "name": "delete_task",
                "description": "软删除指定任务及其所有子任务",
                "parameters": {
                    "task_id": {"type": "string", "description": "要删除的任务ID，必填"}
                }
            }
        ]
    }


# 导出所有公共函数和工具
__all__ = [
    'create_task',
    'update_task',
    'delete_task',
    'AVAILABLE_TOOLS',
    'get_tool_info'
]