"""
Task领域API路由 - 纯微服务代理模式

完全重构为纯代理模式，所有9个核心接口都通过增强版微服务客户端调用。
移除所有本地业务逻辑和数据库操作，实现智能路径映射和错误处理。

9个核心接口：
1. POST /tasks - 创建任务（微服务代理）
2. POST /tasks/query - 查询任务列表（微服务代理，路径重写）
3. PUT /tasks/{task_id} - 修改任务（微服务代理）
4. DELETE /tasks/{task_id} - 删除任务（微服务代理）
5. POST /tasks/special/top3 - 设置Top3（微服务代理）
6. GET /tasks/special/top3/{date} - 查看Top3（微服务代理）
7. POST /tasks/{task_id}/complete - 任务完成（微服务代理）
8. POST /tasks/focus-status - 专注状态（微服务代理）
9. GET /tasks/pomodoro-count - 番茄钟计数（微服务代理）

路径映射策略：
- POST /tasks/query → GET /api/v1/tasks/{user_id}
- PUT /tasks/{task_id} → PUT /api/v1/tasks/{user_id}/{task_id}
- DELETE /tasks/{task_id} → DELETE /api/v1/tasks/{user_id}/{task_id}
- POST /tasks/{task_id}/complete → POST /api/v1/tasks/{user_id}/{task_id}/complete
- POST /tasks/top3/query → GET /api/v1/tasks/top3/{user_id}/{date}
- POST /tasks/focus-status → POST /api/v1/focus/sessions
- GET /tasks/pomodoro-count → GET /api/v1/pomodoros/count

作者：TaKeKe团队
版本：5.0.0（纯微服务代理）
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from fastapi import status
from pydantic import BaseModel, Field

# 导入增强版微服务客户端
from src.services.enhanced_task_microservice_client import (
    EnhancedTaskMicroserviceClient,
    TaskMicroserviceError,
    get_enhanced_task_microservice_client
)

# 导入认证依赖
from src.api.dependencies import get_current_user_id
from src.api.config import config

# 导入响应模型
from .schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListQuery,
    TaskResponse,
    TaskListResponse,
    TaskDeleteResponse,
    PaginationInfo
)
from src.api.schemas import UnifiedResponse

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/tasks", tags=["任务管理"])


class TaskQueryRequest(BaseModel):
    """任务查询请求模型"""
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=100, description="每页大小，1-100")
    status: Optional[str] = Field(None, description="任务状态筛选")
    priority: Optional[str] = Field(None, description="优先级筛选")


class Top3SetRequest(BaseModel):
    """Top3设置请求模型"""
    date: str = Field(..., description="日期，格式：YYYY-MM-DD")
    task_ids: List[str] = Field(..., description="任务ID列表，最多3个")


class FocusStatusRequest(BaseModel):
    """专注状态请求模型"""
    focus_status: str = Field(..., description="专注状态")
    duration_minutes: int = Field(..., gt=0, description="专注时长（分钟）")
    task_id: Optional[str] = Field(None, description="关联的任务ID")


def create_error_response(status_code: int, message: str) -> UnifiedResponse:
    """创建错误响应"""
    return UnifiedResponse(
        code=status_code,
        data=None,
        message=message
    )


def adapt_microservice_response_to_client(microservice_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    适配微服务响应数据为客户端格式

    Args:
        microservice_data (Dict[str, Any]): 微服务响应数据

    Returns:
        Dict[str, Any]: 适配后的响应数据
    """
    # 微服务响应格式已经是标准格式，直接透传
    # 但需要确保包含必要字段
    if not isinstance(microservice_data, dict):
        return microservice_data

    # 确保响应包含必要的字段
    adapted_data = microservice_data.copy()

    # 处理任务列表响应的分页信息
    if "data" in adapted_data and isinstance(adapted_data["data"], list):
        # 微服务返回的是任务数组，需要包装成分页格式
        tasks_array = adapted_data["data"]
        # 适配每个任务的数据格式
        adapted_tasks = []
        for task in tasks_array:
            adapted_task = adapt_single_task_data(task)
            adapted_tasks.append(adapted_task)

        adapted_data["data"] = {
            "tasks": adapted_tasks,
            "pagination": {
                "current_page": 1,
                "page_size": len(adapted_tasks),
                "total_count": len(adapted_tasks),
                "total_pages": 1,
                "has_next": False,
                "has_prev": False
            }
        }
    elif "data" in adapted_data and isinstance(adapted_data["data"], dict):
        # 检查是否是任务列表格式: {"tasks": [...], "total": N, ...}
        if "tasks" in adapted_data["data"] and isinstance(adapted_data["data"]["tasks"], list):
            # 任务列表格式，适配每个任务
            tasks_array = adapted_data["data"]["tasks"]
            adapted_tasks = []
            for task in tasks_array:
                adapted_task = adapt_single_task_data(task)
                adapted_tasks.append(adapted_task)

            # 构建分页信息
            total = adapted_data["data"].get("total", len(adapted_tasks))
            limit = adapted_data["data"].get("limit", 20)
            offset = adapted_data["data"].get("offset", 0)

            current_page = (offset // limit) + 1 if limit > 0 else 1
            total_pages = (total + limit - 1) // limit if limit > 0 else 1

            adapted_data["data"] = {
                "tasks": adapted_tasks,
                "pagination": {
                    "current_page": current_page,
                    "page_size": limit,
                    "total_count": total,
                    "total_pages": total_pages,
                    "has_next": current_page < total_pages,
                    "has_prev": current_page > 1
                }
            }
        else:
            # 单个任务对象，适配数据格式
            adapted_data["data"] = adapt_single_task_data(adapted_data["data"])

    return adapted_data


def adapt_single_task_data(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    适配单个任务数据格式

    Args:
        task_data (Dict[str, Any]): 原始任务数据

    Returns:
        Dict[str, Any]: 适配后的任务数据
    """
    adapted_task = task_data.copy()

    # 优先级映射：微服务 -> 本地(小写)
    # 支持多种格式: 首字母大写, 全小写, 全大写
    priority_mapping = {
        'Low': 'low',
        'low': 'low',
        'Medium': 'medium',
        'medium': 'medium',
        'High': 'high',
        'high': 'high',
        'HIGH': 'high',      # Task微服务返回的全大写格式
        'MEDIUM': 'medium',
        'LOW': 'low'
    }

    # 状态映射：微服务 -> 本地
    # 支持多种格式: 小写, 全大写, 下划线分隔
    status_mapping = {
        'todo': 'pending',
        'TODO': 'pending',
        'pending': 'pending',
        'NOT_STARTED': 'pending',    # Task微服务返回的NOT_STARTED状态
        'inprogress': 'in_progress',
        'IN_PROGRESS': 'in_progress',
        'in_progress': 'in_progress',
        'completed': 'completed',
        'COMPLETED': 'completed'
    }

    # 映射优先级字段 - 支持不区分大小写
    if 'priority' in adapted_task and adapted_task['priority']:
        original_priority = str(adapted_task['priority'])
        mapped_priority = priority_mapping.get(original_priority)
        if mapped_priority:
            adapted_task['priority'] = mapped_priority
        else:
            # 降级处理: 尝试转换为小写后映射
            logger.warning(f"未知的优先级格式: {original_priority}, 尝试转换为小写")
            adapted_task['priority'] = original_priority.lower()

    # 映射状态字段 - 支持不区分大小写和特殊格式
    if 'status' in adapted_task and adapted_task['status']:
        original_status = str(adapted_task['status'])
        mapped_status = status_mapping.get(original_status)
        if mapped_status:
            adapted_task['status'] = mapped_status
        else:
            # 降级处理: 特殊状态转换
            logger.warning(f"未知的状态格式: {original_status}, 尝试智能转换")
            if original_status.upper() == 'NOT_STARTED':
                adapted_task['status'] = 'pending'
            elif '_' in original_status:
                # 处理下划线格式: IN_PROGRESS -> in_progress
                adapted_task['status'] = original_status.lower()
            else:
                adapted_task['status'] = original_status.lower()

    # 添加缺失的必需字段（如果不存在）
    required_fields = {
        'parent_id': None,
        'tags': [],
        'service_ids': [],
        'planned_start_time': None,
        'planned_end_time': None,
        'last_claimed_date': None,
        'is_deleted': False,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'completion_percentage': 0.0
    }

    for field, default_value in required_fields.items():
        if field not in adapted_task:
            adapted_task[field] = default_value

    return adapted_task


# ===================
# 基础CRUD接口 (4个)
# ===================

@router.post("/", response_model=UnifiedResponse[TaskResponse], summary="创建新任务")
async def create_task_endpoint(
    request: CreateTaskRequest,
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[TaskResponse]:
    """
    创建任务 - 微服务代理

    Args:
        request: 创建任务请求
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[TaskResponse]: 创建的任务响应
    """
    try:
        logger.info(f"创建任务API调用: user_id={user_id}, title={request.title}")

        # 准备请求数据
        task_data = {
            "title": request.title,
            "description": request.description or "",
            "priority": request.priority.upper() if request.priority else "MEDIUM",  # Task微服务要求全大写: LOW/MEDIUM/HIGH/URGENT
            "due_date": request.due_date.strftime("%Y-%m-%d") if request.due_date else None,  # Task微服务要求date格式(YYYY-MM-DD),不是datetime
            "tags": request.tags or [],
            "services": request.service_ids or [],
            "user_id": str(user_id)
        }

        # 调用微服务
        response = await client.call_microservice(
            method="POST",
            path="tasks",
            user_id=str(user_id),
            data=task_data
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        # 构造TaskResponse对象
        if adapted_response.get("success") and adapted_response.get("data"):
            task_data = adapted_response["data"]
            task_response = TaskResponse(**task_data)

            return UnifiedResponse(
                code=adapted_response.get("code", 201),
                data=task_response,
                message=adapted_response.get("message", "任务创建成功")
            )
        else:
            return UnifiedResponse(
                code=adapted_response.get("code", 500),
                data=None,
                message=adapted_response.get("message", "任务创建失败")
            )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"创建任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.post("/query", response_model=UnifiedResponse[TaskListResponse], summary="查询任务列表")
async def query_tasks_endpoint(
    request: TaskQueryRequest,
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[TaskListResponse]:
    """
    查询任务列表 - 微服务代理（路径重写）

    Args:
        request: 查询请求
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[TaskListResponse]: 任务列表响应
    """
    try:
        print(f"🔍 QUERY_TASKS_ENDPOINT 被调用: user_id={user_id}, page={request.page}")
        logger.info(f"查询任务列表API调用: user_id={user_id}, page={request.page}")
        print(f"🚀 即将调用增强版微服务客户端...")

        # 准备查询参数
        query_params = {
            "page": request.page,
            "page_size": request.page_size
        }

        if request.status:
            query_params["status"] = request.status
        if request.priority:
            query_params["priority"] = request.priority

        # 调用微服务（路径会被重写为 GET /api/v1/tasks/{user_id}）
        print(f"📡 准备调用微服务客户端: client={client}")
        print(f"📋 调用参数: method=POST, path=tasks/query, user_id={str(user_id)}, data={query_params}")

        try:
            response = await client.call_microservice(
                method="POST",
                path="tasks/query",
                user_id=str(user_id),
                data=query_params
            )
            print(f"✅ 微服务调用完成: response={response}")
        except Exception as e:
            print(f"❌ 微服务调用异常: {type(e).__name__}: {e}")
            raise

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        # 构造TaskListResponse对象
        if adapted_response.get("success") and adapted_response.get("data"):
            list_data = adapted_response["data"]

            # 处理分页信息
            if "pagination" in list_data:
                pagination_info = PaginationInfo(**list_data["pagination"])
            else:
                # 如果没有分页信息，使用默认值
                tasks_count = len(list_data.get("tasks", []))
                pagination_info = PaginationInfo(
                    current_page=request.page,
                    page_size=request.page_size,
                    total_count=tasks_count,
                    total_pages=1,
                    has_next=False,
                    has_prev=False
                )

            # 转换任务数据
            tasks = [TaskResponse(**task_data) for task_data in list_data.get("tasks", [])]

            task_list_response = TaskListResponse(
                tasks=tasks,
                pagination=pagination_info
            )

            return UnifiedResponse(
                code=adapted_response.get("code", 200),
                data=task_list_response,
                message=adapted_response.get("message", "查询成功")
            )
        else:
            return UnifiedResponse(
                code=adapted_response.get("code", 500),
                data=None,
                message=adapted_response.get("message", "查询失败")
            )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"查询任务列表异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.put("/{task_id}", response_model=UnifiedResponse[TaskResponse], summary="更新任务")
async def update_task_endpoint(
    task_id: str = Path(..., description="任务ID"),
    request: UpdateTaskRequest = Body(...),
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[TaskResponse]:
    """
    更新任务 - 微服务代理（路径重写）

    Args:
        task_id: 任务ID
        request: 更新请求
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[TaskResponse]: 更新后的任务响应
    """
    try:
        logger.info(f"更新任务API调用: user_id={user_id}, task_id={task_id}")

        # 准备更新数据（仅包含非None字段，支持部分更新）
        update_data = {"user_id": str(user_id)}

        if request.title is not None:
            update_data["title"] = request.title
        if request.description is not None:
            update_data["description"] = request.description
        if request.priority is not None:
            update_data["priority"] = request.priority.upper()  # Task微服务要求全大写
        if request.due_date is not None:
            update_data["due_date"] = request.due_date.strftime("%Y-%m-%d")  # Task微服务要求date格式
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.service_ids is not None:
            update_data["services"] = request.service_ids
        if request.status is not None:
            update_data["status"] = request.status.upper()  # Task微服务status也是全大写

        # 调用微服务（路径会被重写为 PUT /api/v1/tasks/{user_id}/{task_id}）
        response = await client.call_microservice(
            method="PUT",
            path="tasks/{task_id}",
            user_id=str(user_id),
            data=update_data,
            task_id=task_id
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        # 构造TaskResponse对象
        if adapted_response.get("success") and adapted_response.get("data"):
            task_data = adapted_response["data"]
            task_response = TaskResponse(**task_data)

            return UnifiedResponse(
                code=adapted_response.get("code", 200),
                data=task_response,
                message=adapted_response.get("message", "任务更新成功")
            )
        else:
            return UnifiedResponse(
                code=adapted_response.get("code", 500),
                data=None,
                message=adapted_response.get("message", "任务更新失败")
            )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"更新任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.delete("/{task_id}", response_model=UnifiedResponse[TaskDeleteResponse], summary="删除任务")
async def delete_task_endpoint(
    task_id: str = Path(..., description="任务ID"),
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[TaskDeleteResponse]:
    """
    删除任务 - 微服务代理（路径重写）

    Args:
        task_id: 任务ID
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[TaskDeleteResponse]: 删除结果响应
    """
    try:
        logger.info(f"删除任务API调用: user_id={user_id}, task_id={task_id}")

        # 调用微服务（路径会被重写为 DELETE /api/v1/tasks/{user_id}/{task_id}）
        response = await client.call_microservice(
            method="DELETE",
            path="tasks/{task_id}",
            user_id=str(user_id),
            task_id=task_id
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        # 构造TaskDeleteResponse对象
        delete_response = TaskDeleteResponse(
            deleted_task_id=task_id,
            deleted_count=1 if adapted_response.get("success", False) else 0,
            cascade_deleted=False
        )

        return UnifiedResponse(
            code=adapted_response.get("code", 200),
            data=delete_response,
            message=adapted_response.get("message", "任务删除成功")
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=TaskDeleteResponse(
                deleted_task_id=task_id,
                deleted_count=0,
                cascade_deleted=False
            ),
            message=e.message
        )
    except Exception as e:
        logger.error(f"删除任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=TaskDeleteResponse(
                deleted_task_id=task_id,
                deleted_count=0,
                cascade_deleted=False
            ),
            message="内部服务器错误"
        )


# ===================
# 任务完成接口 (1个)
# ===================

@router.post("/{task_id}/complete", response_model=UnifiedResponse[Dict[str, Any]], summary="完成任务")
async def complete_task_endpoint(
    task_id: str = Path(..., description="任务ID"),
    completion_data: Optional[Dict[str, Any]] = Body(None),
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    完成任务 - 微服务代理（路径重写，支持Top3抽奖）

    Args:
        task_id: 任务ID
        completion_data: 完成数据（可选）
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 完成结果响应（包含奖励信息）

    注意：包含Top3抽奖机制和积分奖励
    """
    try:
        logger.info(f"完成任务API调用: user_id={user_id}, task_id={task_id}")

        # 准备完成数据
        complete_data = completion_data or {}
        complete_data["user_id"] = str(user_id)
        complete_data["task_id"] = task_id

        # 调用微服务（路径会被重写为 POST /api/v1/tasks/{user_id}/{task_id}/complete）
        response = await client.call_microservice(
            method="POST",
            path="tasks/{task_id}/complete",
            user_id=str(user_id),
            data=complete_data,
            task_id=task_id
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        # 增强响应数据：添加Top3抽奖检查
        final_data = adapted_response.get("data", {})

        # 检查是否需要触发Top3抽奖（仅在Mock模式下）
        # Top3任务完成逻辑已移除（免费使用，无积分奖励）
        # 任务完成本身的奖励由Task微服务内部处理

        return UnifiedResponse(
            code=adapted_response.get("code", 200),
            data=final_data,
            message=adapted_response.get("message", "任务完成成功")
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"完成任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


# ===================
# Top3管理接口 (2个)
# ===================

@router.post("/special/top3", response_model=UnifiedResponse[Dict[str, Any]], summary="设置Top3任务")
async def set_top3_endpoint(
    request: Top3SetRequest,
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    设置Top3任务 - 微服务代理 (Mock模式)

    Args:
        request: Top3设置请求
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 设置结果响应

    注意：当前使用Mock实现，等待Top3服务完成后切换到真实微服务
    """
    try:
        logger.info(f"设置Top3 API调用: user_id={user_id}, date={request.date}")

        # Top3功能现在免费使用，直接调用Task微服务

        # 准备Top3数据
        top3_data = {
            "user_id": str(user_id),
            "date": request.date,
            "task_ids": request.task_ids[:3]  # 最多3个任务
        }

        # 调用微服务
        response = await client.call_microservice(
            method="POST",
            path="tasks/special/top3",
            user_id=str(user_id),
            data=top3_data
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        return UnifiedResponse(
            code=adapted_response.get("code", 200),
            data=adapted_response.get("data", {}),
            message=adapted_response.get("message", "Top3设置成功")
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"设置Top3异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.get("/special/top3/{query_date}", response_model=UnifiedResponse[Dict[str, Any]], summary="获取Top3任务")
async def get_top3_endpoint(
    query_date: str = Path(..., description="查询日期，格式：YYYY-MM-DD"),
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    获取Top3任务 - 微服务代理（路径重写，Mock模式）

    Args:
        query_date: 查询日期
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: Top3任务响应

    注意：当前使用Mock实现，等待Top3服务完成后切换到真实微服务
    """
    try:
        logger.info(f"获取Top3 API调用: user_id={user_id}, date={query_date}")

        # 调用微服务（路径会被重写为 GET /api/v1/tasks/top3/{user_id}/{date}）
        response = await client.call_microservice(
            method="POST",
            path="tasks/top3/query",
            user_id=str(user_id),
            date=query_date
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        return UnifiedResponse(
            code=adapted_response.get("code", 200),
            data=adapted_response.get("data", {}),
            message=adapted_response.get("message", "Top3查询成功")
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"获取Top3异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


# ===================
# 专注和番茄钟接口 (2个)
# ===================

@router.post("/focus-status", response_model=UnifiedResponse[Dict[str, Any]], summary="记录专注状态")
async def record_focus_status_endpoint(
    request: FocusStatusRequest,
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    记录专注状态 - 微服务代理（路径重写）

    Args:
        request: 专注状态请求
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 记录结果响应
    """
    try:
        logger.info(f"记录专注状态API调用: user_id={user_id}, status={request.focus_status}")

        # 准备专注状态数据
        focus_data = {
            "user_id": str(user_id),
            "focus_status": request.focus_status,
            "duration_minutes": request.duration_minutes,
            "task_id": request.task_id
        }

        # 调用微服务（路径会被重写为 POST /api/v1/focus/sessions）
        response = await client.call_microservice(
            method="POST",
            path="tasks/focus-status",
            user_id=str(user_id),
            data=focus_data
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        return UnifiedResponse(
            code=adapted_response.get("code", 200),
            data=adapted_response.get("data", {}),
            message=adapted_response.get("message", "专注状态记录成功")
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"记录专注状态异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.get("/pomodoro-count", response_model=UnifiedResponse[Dict[str, Any]], summary="获取番茄钟计数")
async def get_pomodoro_count_endpoint(
    date_filter: str = Query("today", description="日期筛选：today, week, month"),
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    获取番茄钟计数 - 微服务代理（路径重写）

    Args:
        date_filter: 日期筛选条件
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 番茄钟计数响应
    """
    try:
        logger.info(f"获取番茄钟计数API调用: user_id={user_id}, filter={date_filter}")

        # 准备查询参数
        params = {
            "date_filter": date_filter,
            "user_id": str(user_id)
        }

        # 调用微服务（路径会被重写为 GET /api/v1/pomodoros/count）
        response = await client.call_microservice(
            method="GET",
            path="tasks/pomodoro-count",
            user_id=str(user_id),
            params=params
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        return UnifiedResponse(
            code=adapted_response.get("code", 200),
            data=adapted_response.get("data", {}),
            message=adapted_response.get("message", "番茄钟计数查询成功")
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"获取番茄钟计数异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


# ===================
# 健康检查接口
# ===================

@router.get("/health", response_model=UnifiedResponse[Dict[str, Any]], summary="微服务健康检查")
async def health_check_endpoint(
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    微服务健康检查

    Args:
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 健康状态响应
    """
    try:
        is_healthy = await client.health_check()

        return UnifiedResponse(
            code=200,
            data={
                "healthy": is_healthy,
                "timestamp": datetime.now().isoformat(),
                "service": "task-microservice-proxy"
            },
            message="健康" if is_healthy else "不健康"
        )

    except Exception as e:
        logger.error(f"健康检查异常: {e}")
        return UnifiedResponse(
            code=500,
            data={
                "healthy": False,
                "timestamp": datetime.now().isoformat(),
                "service": "task-microservice-proxy",
                "error": str(e)
            },
            message="健康检查失败"
        )