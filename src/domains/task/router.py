"""
Task领域API路由 - 混合模式（微服务+本地实现）

实现9个核心接口，微服务支持的接口使用代理，不支持的接口使用本地实现。

9个核心接口：
1. POST /tasks - 创建任务（微服务）
2. GET /tasks - 查询所有任务（微服务，前端过滤）
3. PUT /tasks/{task_id} - 修改任务（微服务）
4. DELETE /tasks/{task_id} - 删除任务（本地实现）
5. POST /tasks/special/top3 - 设置Top3（本地实现）
6. GET /tasks/special/top3/{date} - 查看Top3（本地实现）
7. POST /tasks/{task_id}/complete - 任务完成按钮（本地实现）
8. POST /tasks/focus-status - 发送专注状态（本地实现）
9. GET /tasks/pomodoro-count - 查看番茄钟计数（本地实现）

作者：TaKeKe团队
版本：4.0.0（混合模式）
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from fastapi import status

from sqlmodel import Session

# 导入微服务客户端
from src.services.task_microservice_client import (
    TaskMicroserviceError,
    get_all_tasks, create_task, update_task, delete_task,
    set_top3, get_top3, complete_task
)

# 导入本地服务
from .service_local import TaskLocalService
from .schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListQuery,
    TaskResponse,
    TaskListResponse,
    TaskDeleteResponse,
    PaginationInfo
)
# 认证模块已迁移到微服务，使用共用的统一响应格式
from src.api.schemas import UnifiedResponse

# 导入认证依赖（认证模块已迁移到微服务）
from src.api.dependencies import get_current_user_id

# 导入优化后的数据库依赖
from src.database import SessionDep, get_db_session

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/tasks", tags=["任务管理"])


def create_error_response(status_code: int, message: str) -> UnifiedResponse:
    """创建错误响应"""
    return UnifiedResponse(
        code=status_code,
        data=None,
        message=message
    )


def adapt_response_from_microservice(microservice_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    适配微服务响应数据为本地格式

    Args:
        microservice_data (Dict[str, Any]): 微服务响应数据

    Returns:
        Dict[str, Any]: 适配后的响应数据
    """
    # 微服务缺失字段返回null
    missing_fields = {
        'parent_id': None,
        'tags': [],
        'service_ids': [],
        'planned_start_time': None,
        'planned_end_time': None,
        'last_claimed_date': None,
        'completion_percentage': 0.0,
        'is_deleted': False
    }

    # 状态映射：微服务 -> 本地
    status_mapping = {
        'todo': 'pending',
        'inprogress': 'in_progress',
        'completed': 'completed'
    }

    # Priority映射：微服务(首字母大写) -> 本地(小写)
    priority_mapping = {
        'Low': 'low',
        'Medium': 'medium',
        'High': 'high'
    }

    # 复制数据以避免修改原始数据
    microservice_data = microservice_data.copy()

    # 映射状态字段
    if 'status' in microservice_data:
        microservice_data['status'] = status_mapping.get(
            microservice_data['status'],
            microservice_data['status']  # 如果没有映射，保持原值
        )

    # 映射priority字段
    if 'priority' in microservice_data:
        microservice_data['priority'] = priority_mapping.get(
            microservice_data['priority'],
            microservice_data['priority']  # 如果没有映射，保持原值
        )

    # 合并微服务数据和缺失字段
    adapted_data = {**missing_fields, **microservice_data}
    return adapted_data


# ===================
# 基础CRUD接口 (4个)
# ===================

@router.post("/", response_model=UnifiedResponse[TaskResponse], summary="创建新任务")
async def create_task_endpoint(
    request: CreateTaskRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskResponse]:
    """
    1. 创建任务 - 微服务代理
    """
    try:
        logger.info(f"创建任务API调用: user_id={user_id}, title={request.title}")

        # 处理priority格式：确保首字母大写（微服务要求）
        priority_value = request.priority or "medium"
        if priority_value:
            priority_value = priority_value.capitalize()  # 确保首字母大写

        # 调用微服务便捷方法
        microservice_response = await create_task(
            user_id=str(user_id),
            title=request.title,
            description=request.description,
            priority=priority_value,
            due_date=request.due_date.isoformat() if request.due_date else None
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200 and microservice_response["code"] != 201:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        # 适配响应数据
        task_data_dict = adapt_response_from_microservice(microservice_response["data"])
        task_data = TaskResponse(**task_data_dict)

        return UnifiedResponse(
            code=201,
            data=task_data,
            message="任务创建成功"
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
async def get_task_list(
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小，1-100")
) -> UnifiedResponse[TaskListResponse]:
    """
    2. 查询所有任务（前端过滤） - 微服务代理
    """
    try:
        logger.debug(f"获取任务列表API调用: user_id={user_id}, page={page}")

        # 调用微服务便捷方法
        microservice_response = await get_all_tasks(
            user_id=str(user_id),
            page=page,
            page_size=page_size
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        # 处理微服务响应数据
        # 微服务可能返回直接的数组或包含分页信息的对象
        if isinstance(microservice_response["data"], list):
            # 直接返回任务数组
            tasks_array = microservice_response["data"]
            # 简单分页逻辑：基于数组长度和请求参数计算
            total_count = len(tasks_array)
            total_pages = (total_count + page_size - 1) // page_size  # 向上取整

            # 构造分页信息
            pagination_info = PaginationInfo(
                current_page=page,
                page_size=page_size,
                total_count=total_count,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
        else:
            # 返回包含分页信息的对象
            list_data = microservice_response["data"]
            tasks_array = list_data.get("tasks", [])

            # 构造分页信息
            pagination_info = PaginationInfo(
                current_page=list_data.get("current_page", page),
                page_size=list_data.get("page_size", page_size),
                total_count=list_data.get("total_count", 0),
                total_pages=list_data.get("total_pages", 0),
                has_next=list_data.get("has_next", False),
                has_prev=list_data.get("has_prev", False)
            )

        # 适配任务列表数据
        tasks = []
        for task_dict in tasks_array:
            adapted_task_dict = adapt_response_from_microservice(task_dict)
            tasks.append(TaskResponse(**adapted_task_dict))

        # 构造TaskListResponse
        task_list_response = TaskListResponse(
            tasks=tasks,
            pagination=pagination_info
        )

        return UnifiedResponse(
            code=200,
            data=task_list_response,
            message="获取任务列表成功"
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"获取任务列表异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.put("/{task_id}", response_model=UnifiedResponse[TaskResponse], summary="更新任务信息")
async def update_task_endpoint(
    task_id: UUID,
    request: UpdateTaskRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskResponse]:
    """
    3. 修改任务 - 微服务代理
    """
    try:
        logger.info(f"更新任务API调用: task_id={task_id}, user_id={user_id}")

        # 调用微服务便捷方法
        microservice_response = await update_task(
            user_id=str(user_id),
            task_id=str(task_id),
            title=request.title,
            description=request.description,
            priority=request.priority,
            status=request.status,
            due_date=request.due_date.isoformat() if request.due_date else None
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        # 适配响应数据
        task_data_dict = adapt_response_from_microservice(microservice_response["data"])
        task_data = TaskResponse(**task_data_dict)

        return UnifiedResponse(
            code=200,
            data=task_data,
            message="任务更新成功"
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
    task_id: UUID,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskDeleteResponse]:
    """
    4. 删除任务 - 微服务代理
    """
    try:
        logger.info(f"删除任务API调用: task_id={task_id}, user_id={user_id}")

        # 调用微服务便捷方法
        microservice_response = await delete_task(
            user_id=str(user_id),
            task_id=str(task_id)
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        # 构造删除响应数据
        delete_data = TaskDeleteResponse(
            deleted_task_id=str(task_id),
            deleted_count=1,
            cascade_deleted=False
        )

        return UnifiedResponse(
            code=200,
            data=delete_data,
            message="任务删除成功"
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"删除任务异常: {e}")
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
    request: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    5. 设置Top3（无积分消耗） - 微服务代理
    """
    try:
        logger.info(f"设置Top3 API调用: user_id={user_id}")

        # 调用微服务便捷方法
        microservice_response = await set_top3(
            user_id=str(user_id),
            date=request.get("date"),
            task_ids=request.get("task_ids", [])
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        return UnifiedResponse(
            code=200,
            data=microservice_response["data"],
            message="success"
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
            message="设置Top3失败"
        )


@router.get("/special/top3/{date}", response_model=UnifiedResponse[Dict[str, Any]], summary="获取Top3任务")
async def get_top3_endpoint(
    date: str,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    6. 查看Top3 - 微服务代理
    """
    try:
        logger.info(f"获取Top3 API调用: user_id={user_id}, date={date}")

        # 调用微服务便捷方法
        microservice_response = await get_top3(
            user_id=str(user_id),
            date=date
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        return UnifiedResponse(
            code=200,
            data=microservice_response["data"],
            message="success"
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"获取Top3失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="获取Top3失败"
        )


# ===================
# 任务完成接口 (1个)
# ===================

@router.post("/{task_id}/complete", response_model=UnifiedResponse[Dict[str, Any]], summary="完成任务")
async def complete_task_endpoint(
    task_id: UUID,
    request: Optional[Dict[str, Any]] = Body(None),
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    7. 任务完成按钮（含奖励） - 微服务代理
    """
    try:
        logger.info(f"完成任务API调用: task_id={task_id}, user_id={user_id}")

        # 调用微服务便捷方法
        microservice_response = await complete_task(
            user_id=str(user_id),
            task_id=str(task_id),
            completion_data=request or {}
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        return UnifiedResponse(
            code=200,
            data=microservice_response["data"],
            message="任务完成成功"
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
# 专注和番茄钟接口 (2个)
# ===================

@router.post("/focus-status", response_model=UnifiedResponse[Dict[str, Any]], summary="发送专注状态")
async def send_focus_status_endpoint(
    request: Dict[str, Any],
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    8. 发送专注状态 - 本地实现
    """
    try:
        logger.info(f"发送专注状态API调用: user_id={user_id}")

        # 创建本地服务实例
        local_service = TaskLocalService(session)

        # 记录专注状态
        focus_record = local_service.record_focus_status(
            user_id=user_id,
            focus_status=request.get("focus_status"),
            task_id=request.get("task_id"),
            duration_minutes=request.get("duration_minutes"),
            status_data=request.get("status_data", {})
        )

        # 构造响应数据
        response_data = {
            "id": focus_record.id,
            "user_id": str(focus_record.user_id),
            "focus_status": focus_record.focus_status,
            "task_id": focus_record.task_id,
            "duration_minutes": focus_record.duration_minutes,
            "created_at": focus_record.created_at.isoformat() if focus_record.created_at else None
        }

        return UnifiedResponse(
            code=200,
            data=response_data,
            message="专注状态记录成功"
        )

    except Exception as e:
        logger.error(f"发送专注状态异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.get("/pomodoro-count", response_model=UnifiedResponse[Dict[str, Any]], summary="查看番茄钟计数")
async def get_pomodoro_count_endpoint(
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id),
    date_filter: Optional[str] = Query("today", description="时间过滤: today, week, month")
) -> UnifiedResponse[Dict[str, Any]]:
    """
    9. 查看番茄钟计数 - 本地实现
    """
    try:
        logger.info(f"获取番茄钟计数API调用: user_id={user_id}, filter={date_filter}")

        # 创建本地服务实例
        local_service = TaskLocalService(session)

        # 获取番茄钟计数
        pomodoro_record = local_service.get_pomodoro_count(
            user_id=user_id,
            date_filter=date_filter
        )

        # 构造响应数据
        response_data = {
            "date_filter": date_filter,
            "count": pomodoro_record.count,
            "last_updated": pomodoro_record.last_updated.isoformat() if pomodoro_record.last_updated else None
        }

        return UnifiedResponse(
            code=200,
            data=response_data,
            message="获取番茄钟统计成功"
        )

    except Exception as e:
        logger.error(f"获取番茄钟计数异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )