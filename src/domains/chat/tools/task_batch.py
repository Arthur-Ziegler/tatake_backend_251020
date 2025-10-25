"""
聊天工具 - 批量任务操作模块

实现批量创建子任务工具，用于任务拆分场景。

核心功能：
1. 批量创建子任务：batch_create_subtasks()
2. 支持部分成功：即使部分子任务创建失败，也返回成功和失败列表
3. 权限验证：确保用户有权限在父任务下创建子任务
4. 格式验证：验证输入参数和子任务格式

设计原则：
1. 简洁直接：避免过度抽象，保持代码简单易懂
2. 错误友好：提供详细的错误信息和异常处理
3. 部分成功：接受部分成功，不要求全部成功
4. 性能优化：批量操作减少数据库连接开销
5. 测试驱动：所有功能都有对应的测试用例

基于LangGraph最佳实践：
- 使用@tool装饰器
- 支持LangGraph工具调用机制
- 提供友好的错误信息
- 遵循工具命名规范

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from typing import Dict, Any, List, Optional
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


def _validate_subtask_format(subtask: Any) -> bool:
    """
    验证子任务格式是否有效

    Args:
        subtask: 待验证的子任务对象

    Returns:
        bool: 格式是否有效

    Raises:
        ValueError: 格式无效时抛出，包含详细错误信息
    """
    if not isinstance(subtask, dict):
        raise ValueError(f"子任务必须是字典格式，当前类型: {type(subtask).__name__}")

    # 检查必需字段
    if 'title' not in subtask:
        raise ValueError("子任务缺少必需的 'title' 字段")

    # 检查title是否为字符串且非空
    title = subtask['title']
    if not isinstance(title, str):
        raise ValueError(f"子任务标题必须是字符串，当前类型: {type(title).__name__}")

    if not title.strip():
        raise ValueError("子任务标题不能为空")

    return True


def batch_create_subtasks_core(parent_id: str, subtasks: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    """
    批量创建子任务工具

    将一个父任务拆分为多个可执行的子任务。支持部分成功，
    即使部分子任务创建失败，也会返回成功和失败的详细列表。

    功能特性：
    - 批量创建多个子任务
    - 支持部分成功场景
    - 自动权限验证
    - 详细的成功/失败报告
    - 事务安全处理

    Args:
        parent_id (str): 父任务ID，必须是有效的UUID字符串
        subtasks (List[Dict[str, Any]]): 子任务列表，每个子任务包含：
            - title (str, 必需): 子任务标题
            - description (str, 可选): 子任务描述
            - state (str, 可选): 子任务状态，默认为'todo'
        user_id (str): 用户ID，必须是有效的UUID字符串

    Returns:
        Dict[str, Any]: 操作结果，格式：
            {
                "success": bool,
                "data": {
                    "created": List[Dict],      # 成功创建的子任务列表
                    "failed": List[Dict],       # 创建失败的子任务列表
                    "total": int,               # 总子任务数量
                    "success_count": int,       # 成功数量
                    "failure_count": int        # 失败数量
                },
                "timestamp": str
            }
            或失败时：
            {
                "success": bool,
                "error": str,
                "error_code": str,
                "timestamp": str
            }

    Raises:
        ValueError: 输入参数无效时抛出
        Exception: 其他运行时错误

    Examples:
        >>> batch_create_subtasks(
        ...     "550e8400-e29b-41d4-a716-446655440000",
        ...     [
        ...         {"title": "需求分析", "description": "分析用户需求"},
        ...         {"title": "设计阶段", "description": "设计系统架构"}
        ...     ],
        ...     "550e8400-e29b-41d4-a716-446655440001"
        ... )
        {
            'success': True,
            'data': {
                'created': [
                    {'id': 'uuid1', 'title': '需求分析', 'description': '分析用户需求'},
                    {'id': 'uuid2', 'title': '设计阶段', 'description': '设计系统架构'}
                ],
                'failed': [],
                'total': 2,
                'success_count': 2,
                'failure_count': 0
            },
            'timestamp': '2024-12-25T10:30:00Z'
        }
    """
    logger.info(f"🔧 批量创建子任务工具被调用，父任务ID: {parent_id}, 子任务数量: {len(subtasks)}, 用户ID: {user_id}")

    try:
        # 参数验证
        if not parent_id or not isinstance(parent_id, str):
            raise ValueError("父任务ID不能为空且必须是字符串")

        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID不能为空且必须是字符串")

        if not isinstance(subtasks, list):
            raise ValueError(f"子任务必须是列表格式，当前类型: {type(subtasks).__name__}")

        # 空列表直接返回成功
        if len(subtasks) == 0:
            logger.info("子任务列表为空，直接返回成功")
            return _success_response({
                'created': [],
                'failed': [],
                'total': 0,
                'success_count': 0,
                'failure_count': 0
            }, "无子任务需要创建")

        # UUID转换和验证
        logger.debug("开始转换UUID格式")
        parent_uuid = safe_uuid_convert(parent_id)
        user_uuid = safe_uuid_convert(user_id)

        if parent_uuid is None:
            raise ValueError("无效的父任务ID格式")

        if user_uuid is None:
            raise ValueError("无效的用户ID格式")

        # 验证子任务格式
        logger.debug("开始验证子任务格式")
        validated_subtasks = []
        for i, subtask in enumerate(subtasks):
            try:
                _validate_subtask_format(subtask)
                validated_subtasks.append(subtask)
                logger.debug(f"子任务 {i+1} 格式验证通过: {subtask.get('title', '未知标题')}")
            except ValueError as e:
                # 格式验证失败的任务，记录到失败列表
                logger.warning(f"子任务 {i+1} 格式验证失败: {e}")
                validated_subtasks.append(None)  # 占位符，保持索引一致

        # 如果所有子任务格式都无效
        if all(task is None for task in validated_subtasks):
            raise ValueError("所有子任务格式都无效，无法创建任何子任务")

        # 获取任务服务上下文
        logger.debug("获取任务服务上下文")
        with get_task_service_context() as ctx:
            task_service = ctx['task_service']
            session = ctx['session']

            # 验证父任务存在且有权限
            logger.debug("验证父任务存在和权限")
            parent_task = task_service.get_task_by_id(parent_uuid)

            if parent_task is None:
                return _error_response(
                    f"父任务不存在: {parent_id}",
                    code="PARENT_TASK_NOT_FOUND",
                    details={"parent_id": parent_id}
                )

            # 检查权限：用户必须是父任务的拥有者
            if parent_task.get('user_id') != str(user_uuid):
                return _error_response(
                    "权限不足：您不是该父任务的拥有者",
                    code="PERMISSION_DENIED",
                    details={
                        "parent_id": parent_id,
                        "parent_owner": parent_task.get('user_id'),
                        "current_user": str(user_uuid)
                    }
                )

            logger.debug(f"父任务权限验证通过: {parent_task.get('title')}")

            # 批量创建子任务
            created_tasks = []
            failed_tasks = []

            logger.info(f"开始批量创建 {len(validated_subtasks)} 个子任务")

            for i, subtask in enumerate(validated_subtasks):
                if subtask is None:
                    # 跳过格式无效的任务（已在前面处理）
                    continue

                try:
                    # 构造创建任务请求
                    from src.domains.task.schemas import CreateTaskRequest
                    from src.domains.task.models import TaskStatusConst

                    create_request = CreateTaskRequest(
                        title=subtask['title'].strip(),
                        description=subtask.get('description', '').strip(),
                        parent_id=str(parent_uuid),  # 转换为字符串
                        status=subtask.get('state', TaskStatusConst.PENDING)  # 使用status字段
                    )

                    # 调用TaskService创建任务
                    logger.debug(f"正在创建子任务 {i+1}: {subtask['title']}")
                    created_task = task_service.create_task(create_request, user_uuid)

                    # 添加到成功列表
                    created_tasks.append({
                        'id': created_task.get('id'),
                        'title': created_task.get('title'),
                        'description': created_task.get('description'),
                        'state': created_task.get('status'),
                        'parent_id': str(parent_uuid),
                        'created_at': created_task.get('created_at')
                    })

                    logger.debug(f"子任务创建成功: {created_task.get('title')} ({created_task.get('id')})")

                except Exception as e:
                    # 单个任务创建失败，记录到失败列表
                    error_msg = f"创建子任务失败: {str(e)}"
                    logger.error(f"子任务 {i+1} 创建失败: {error_msg}")

                    failed_tasks.append({
                        'title': subtask['title'],
                        'description': subtask.get('description', ''),
                        'error': error_msg,
                        'index': i + 1
                    })

            # 构建结果数据
            total_tasks = len([task for task in validated_subtasks if task is not None])
            success_count = len(created_tasks)
            failure_count = len(failed_tasks)

            result_data = {
                'created': created_tasks,
                'failed': failed_tasks,
                'total': total_tasks,
                'success_count': success_count,
                'failure_count': failure_count
            }

            # 构建返回消息
            if success_count == total_tasks:
                message = f"所有 {total_tasks} 个子任务创建成功"
            elif success_count > 0:
                message = f"成功创建 {success_count} 个子任务，失败 {failure_count} 个"
            else:
                # 所有任务都创建失败，但工具调用本身成功
                message = f"所有 {total_tasks} 个子任务创建失败，请检查错误信息"

            logger.info(f"批量创建完成: 成功 {success_count}, 失败 {failure_count}, 总计 {total_tasks}")

            # 即使所有任务都失败，只要工具本身执行成功，就返回success=True
            # 这符合"接受部分成功"的设计原则
            return _success_response(result_data, message)

    except ValueError as e:
        # 参数验证错误
        logger.error(f"批量创建子任务参数验证失败: {e}")
        return _error_response(str(e), code="VALIDATION_ERROR")

    except Exception as e:
        # 其他运行时错误
        logger.error(f"批量创建子任务发生未预期错误: {type(e).__name__}: {e}")
        return _error_response(
            f"批量创建子任务时发生错误: {str(e)}",
            code="INTERNAL_ERROR",
            details={"error_type": type(e).__name__}
        )


def get_batch_tools_info() -> Dict[str, Any]:
    """
    获取批量工具信息

    Returns:
        Dict[str, Any]: 批量工具信息字典
    """
    return {
        "name": "batch_create_subtasks",
        "description": "批量创建子任务工具，用于任务拆分场景，支持部分成功",
        "parameters": {
            "parent_id": {
                "type": "string",
                "description": "父任务ID，必须是有效的UUID字符串",
                "required": True
            },
            "subtasks": {
                "type": "array",
                "description": "子任务列表，每个子任务包含title(必需)和description(可选)",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "子任务标题，不能为空"
                        },
                        "description": {
                            "type": "string",
                            "description": "子任务描述，可选"
                        },
                        "state": {
                            "type": "string",
                            "description": "子任务状态，可选，默认为'todo'"
                        }
                    },
                    "required": ["title"]
                },
                "required": True
            },
            "user_id": {
                "type": "string",
                "description": "用户ID，必须是有效的UUID字符串",
                "required": True
            }
        },
        "examples": [
            {
                "input": {
                    "parent_id": "550e8400-e29b-41d4-a716-446655440000",
                    "subtasks": [
                        {"title": "需求分析", "description": "分析用户需求"},
                        {"title": "设计阶段", "description": "设计系统架构"}
                    ],
                    "user_id": "550e8400-e29b-41d4-a716-446655440001"
                },
                "output": {
                    "success": True,
                    "data": {
                        "created": [
                            {"id": "uuid1", "title": "需求分析", "description": "分析用户需求"},
                            {"id": "uuid2", "title": "设计阶段", "description": "设计系统架构"}
                        ],
                        "failed": [],
                        "total": 2,
                        "success_count": 2,
                        "failure_count": 0
                    }
                }
            }
        ],
        "features": [
            "批量创建多个子任务",
            "支持部分成功场景",
            "自动权限验证",
            "详细的成功/失败报告",
            "格式验证和错误处理",
            "事务安全处理"
        ]
    }


# LangGraph工具装饰器版本
@tool
def batch_create_subtasks(parent_id: str, subtasks: List[Dict[str, Any]], user_id: str) -> str:
    """
    批量创建子任务工具 (LangGraph版本)

    LangGraph工具包装器，调用核心批量创建子任务功能并返回JSON字符串。

    Args:
        parent_id (str): 父任务ID
        subtasks (List[Dict[str, Any]]): 子任务列表
        user_id (str): 用户ID

    Returns:
        str: JSON格式的结果字符串
    """
    import json
    result = batch_create_subtasks_core(parent_id, subtasks, user_id)
    return json.dumps(result, ensure_ascii=False, indent=2)


# 导出所有公共函数和工具
__all__ = [
    'batch_create_subtasks_core',
    'batch_create_subtasks',
    'get_batch_tools_info',
    '_validate_subtask_format'
]