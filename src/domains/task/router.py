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

# 导入Focus微服务客户端
from src.services.focus_microservice_client import (
    FocusMicroserviceClient,
    get_focus_client
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
    page: int = Field(1, ge=1, description="页码，从1开始", example=1)
    page_size: int = Field(20, ge=1, le=100, description="每页大小，1-100", example=20)
    status: Optional[str] = Field(None, description="任务状态筛选", example="pending")
    priority: Optional[str] = Field(None, description="优先级筛选", example="high")


class Top3SetRequest(BaseModel):
    """Top3设置请求模型"""
    date: str = Field(..., description="日期，格式：YYYY-MM-DD", example="2024-12-25")
    task_ids: List[str] = Field(..., description="任务ID列表，最多3个", example=["550e8400-e29b-41d4-a716-446655440000", "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "6ba7b811-9dad-11d1-80b4-00c04fd430c8"])


class FocusStatusRequest(BaseModel):
    """专注状态请求模型"""
    focus_status: str = Field(..., description="专注状态", example="focused")
    duration_minutes: int = Field(..., gt=0, description="专注时长（分钟）", example=25)
    task_id: Optional[str] = Field(None, description="关联的任务ID", example="550e8400-e29b-41d4-a716-446655440000")


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
        # 注意：user_id将由微服务客户端自动添加到query参数中
        task_data = {
            "title": request.title,
            "description": request.description or "",
            "status": request.status.upper() if request.status else "PENDING",  # Task微服务要求全大写: PENDING/IN_PROGRESS/COMPLETED/CANCELLED
            "priority": request.priority.upper() if request.priority else "MEDIUM",  # Task微服务要求全大写: LOW/MEDIUM/HIGH/URGENT
            "parent_id": request.parent_id,  # 支持任务树结构
            "due_date": request.due_date.strftime("%Y-%m-%d") if request.due_date else None,  # Task微服务要求date格式(YYYY-MM-DD),不是datetime
            "planned_start_time": request.planned_start_time.isoformat() if request.planned_start_time else None,
            "planned_end_time": request.planned_end_time.isoformat() if request.planned_end_time else None,
            "tags": request.tags or [],
            "services": request.service_ids or []
            # user_id由微服务客户端处理，不在这里添加
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


@router.get("/", response_model=UnifiedResponse[TaskListResponse], summary="获取任务列表")
async def get_tasks_endpoint(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小，1-100"),
    status: Optional[str] = Query(None, description="任务状态筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选"),
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[TaskListResponse]:
    """
    获取任务列表 - RESTful GET接口（符合docs/标准）

    Args:
        page: 页码
        page_size: 每页大小
        status: 任务状态筛选
        priority: 优先级筛选
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[TaskListResponse]: 任务列表响应
    """
    try:
        logger.info(f"GET任务列表API调用: user_id={user_id}, page={page}")

        # 准备查询参数
        query_params = {
            "page": page,
            "page_size": page_size
        }

        if status:
            query_params["status"] = status
        if priority:
            query_params["priority"] = priority

        # 调用微服务
        response = await client.call_microservice(
            method="GET",
            path="tasks",
            user_id=str(user_id),
            params=query_params
        )

        # 适配响应数据
        adapted_response = adapt_microservice_response_to_client(response)

        # 构造TaskListResponse对象
        if adapted_response.get("success") and adapted_response.get("data"):
            list_data = adapted_response["data"]

            # 处理分页信息
            if "pagination" in list_data:
                pagination_info = PaginationInfo(**list_data["pagination"])
            else:
                tasks_count = len(list_data.get("tasks", []))
                pagination_info = PaginationInfo(
                    current_page=page,
                    page_size=page_size,
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


@router.get("/tags", response_model=UnifiedResponse[Dict[str, Any]], summary="获取所有标签")
async def get_tags_endpoint(
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    获取所有任务标签 - 微服务代理

    获取当前用户所有任务的标签列表，用于标签选择和管理。

    Args:
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 标签列表响应
    """
    try:
        logger.info(f"获取标签API调用: user_id={user_id}")

        # 调用微服务
        # TODO: 该端点在任务微服务中尚未实现，当前会返回404或500
        # 需要在任务微服务中添加 GET /tasks/tags 端点支持
        # 临时方案：捕获错误并返回空标签列表
        response = await client.call_microservice(
            method="GET",
            path="tasks/tags",
            user_id=str(user_id)
        )

        # tags接口返回简单数据结构，不是任务对象，直接使用微服务响应
        # 不需要通过 adapt_microservice_response_to_client 进行任务数据适配
        return UnifiedResponse(
            code=response.get("code", 200),
            data=response.get("data", {"tags": []}),
            message=response.get("message", "查询成功")
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data={"tags": []},
            message=e.message
        )
    except Exception as e:
        logger.error(f"获取标签异常: {e}")
        return UnifiedResponse(
            code=500,
            data={"tags": []},
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
        # 注意：user_id将由微服务客户端自动添加到query参数中
        update_data = {}

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
        if request.planned_start_time is not None:
            update_data["planned_start_time"] = request.planned_start_time.isoformat()
        if request.planned_end_time is not None:
            update_data["planned_end_time"] = request.planned_end_time.isoformat()

        # 调用微服务（路径会被重写为 PUT /api/v1/tasks/{user_id}/{task_id}）
        response = await client.call_microservice(
            method="PUT",
            path="tasks/{task_id}",
            user_id=str(user_id),
            data=update_data,
            task_id=task_id
        )

        # 更新接口返回任务对象，但使用简化的响应处理
        # 微服务已经返回标准格式，直接使用，避免复杂的适配逻辑导致错误

        # 构造TaskResponse对象
        if response.get("success") and response.get("data"):
            task_data = response["data"]

            # 直接使用微服务返回的数据，只做必要的字段适配
            # 优先级和状态转换为小写
            if "priority" in task_data and task_data["priority"]:
                task_data["priority"] = task_data["priority"].lower()
            if "status" in task_data and task_data["status"]:
                status_map = {
                    "NOT_STARTED": "pending",
                    "IN_PROGRESS": "in_progress",
                    "COMPLETED": "completed",
                    "CANCELLED": "cancelled"
                }
                task_data["status"] = status_map.get(task_data["status"], task_data["status"].lower())

            # 补充微服务缺失的completion_percentage字段（临时方案）
            task_data.setdefault('completion_percentage', 0.0)

            task_response = TaskResponse(**task_data)

            return UnifiedResponse(
                code=response.get("code", 200),
                data=task_response,
                message=response.get("message", "任务更新成功")
            )
        else:
            return UnifiedResponse(
                code=response.get("code", 500),
                data=None,
                message=response.get("message", "任务更新失败")
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

        # 删除接口返回简单操作结果，不是任务对象，直接使用微服务响应
        # 不需要通过 adapt_microservice_response_to_client 进行任务数据适配

        # 构造TaskDeleteResponse对象
        delete_response = TaskDeleteResponse(
            deleted_task_id=task_id,
            deleted_count=1 if response.get("success", False) else 0,
            cascade_deleted=False
        )

        return UnifiedResponse(
            code=response.get("code", 200),
            data=delete_response,
            message=response.get("message", "任务删除成功")
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
    user_id: UUID = Depends(get_current_user_id),
    client: EnhancedTaskMicroserviceClient = Depends(get_enhanced_task_microservice_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    完成任务 - 通过PUT更新status实现（设计决策）

    实现方式：映射到 PUT /tasks/{task_id}，更新status为COMPLETED

    Args:
        task_id: 任务ID
        user_id: 用户ID（从JWT token提取）
        client: 增强版微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 完成结果响应，包含task和reward信息

    设计说明：
    - 微服务没有独立的complete端点
    - 通过PUT更新status=COMPLETED实现任务完成
    - 符合RESTful设计原则
    - 不需要请求体，只需任务ID即可完成
    """
    try:
        logger.info(f"完成任务API调用: user_id={user_id}, task_id={task_id}")

        # 准备完成数据：通过PUT更新status为COMPLETED
        complete_data = {
            "status": "COMPLETED"  # Task微服务要求全大写
        }

        # 调用微服务（映射为 PUT /tasks/{task_id}/?user_id={user_id}）
        response = await client.call_microservice(
            method="POST",
            path="tasks/{task_id}/complete",
            user_id=str(user_id),
            data=complete_data,
            task_id=task_id
        )

        # 处理Task微服务返回空响应的bug - 补偿性GET
        # TODO: Task微服务bug，PUT应返回完整任务，当前返回空需补偿性GET
        task_data = response.get("data")
        if not task_data or not isinstance(task_data, dict):
            logger.warning(f"Task微服务返回空响应，执行补偿性GET: task_id={task_id}")
            # 补偿性GET获取更新后的任务数据
            get_response = await client.call_microservice(
                method="GET",
                path=f"tasks/{task_id}",
                user_id=str(user_id)
            )
            task_data = get_response.get("data", {})

        # 补充completion_percentage（任务完成为100%）
        task_data.setdefault('completion_percentage', 100.0)

        # 组装task响应数据
        task_info = {
            "id": task_data.get("id", task_id),
            "title": task_data.get("title", ""),
            "status": "completed",
            "completed_at": task_data.get("updated_at", "")
        }

        # Mock reward数据（硬编码）
        # TODO: 临时mock iPhone17Pro奖励，后续需实现真实Reward微服务调用和抽奖逻辑
        reward_info = {
            "description": "恭喜获得iPhone 17 Pro!",
            "id": "mock-reward-iphone17pro",
            "quantity": 1,
            "name": "iPhone 17 Pro",
            "value": 9999
        }

        return UnifiedResponse(
            code=200,
            message="任务完成成功",
            data={
                "task": task_info,
                "reward": reward_info
            }
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
        # 注意：user_id将由微服务客户端自动添加到query参数中
        top3_data = {
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

        # Top3设置接口返回操作结果，不是任务对象，直接使用微服务响应
        # 不需要通过 adapt_microservice_response_to_client 进行任务数据适配

        return UnifiedResponse(
            code=response.get("code", 200),
            data=response.get("data", {}),
            message=response.get("message", "Top3设置成功")
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

        # Top3查询接口返回任务ID列表，不是任务对象，直接使用微服务响应
        # 不需要通过 adapt_microservice_response_to_client 进行任务数据适配

        return UnifiedResponse(
            code=response.get("code", 200),
            data=response.get("data", {}),
            message=response.get("message", "Top3查询成功")
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
    client: FocusMicroserviceClient = Depends(get_focus_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    记录专注状态 - Focus微服务代理

    Args:
        request: 专注状态请求
        user_id: 用户ID（从JWT token提取）
        client: Focus微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 记录结果响应
    """
    try:
        logger.info(f"记录专注状态API调用: user_id={user_id}, status={request.focus_status}")

        # 调用Focus微服务记录专注状态
        response = await client.record_focus_status(
            user_id=str(user_id),
            focus_status=request.focus_status,
            duration_minutes=request.duration_minutes,
            task_id=request.task_id
        )

        # 提取响应数据
        return UnifiedResponse(
            code=response.get("code", 200),
            data=response.get("data", {}),
            message=response.get("message", "专注状态记录成功")
        )

    except HTTPException as e:
        logger.error(f"Focus微服务调用失败: {e.detail}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e.detail) if isinstance(e.detail, str) else e.detail.get("message", "Focus微服务调用失败")
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
    client: FocusMicroserviceClient = Depends(get_focus_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    获取番茄钟计数 - Focus微服务代理

    Args:
        date_filter: 日期筛选条件
        user_id: 用户ID（从JWT token提取）
        client: Focus微服务客户端

    Returns:
        UnifiedResponse[Dict[str, Any]]: 番茄钟计数响应
    """
    try:
        logger.info(f"获取番茄钟计数API调用: user_id={user_id}, filter={date_filter}")

        # 调用Focus微服务获取番茄钟计数
        response = await client.get_pomodoro_count(
            user_id=str(user_id),
            date_filter=date_filter
        )

        # 提取响应数据
        return UnifiedResponse(
            code=response.get("code", 200),
            data=response.get("data", {}),
            message=response.get("message", "番茄钟计数查询成功")
        )

    except HTTPException as e:
        logger.error(f"Focus微服务调用失败: {e.detail}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e.detail) if isinstance(e.detail, str) else e.detail.get("message", "Focus微服务调用失败")
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