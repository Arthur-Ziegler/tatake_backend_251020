"""
任务管理API路由

处理任务管理相关请求，包括任务CRUD操作、状态管理、批量操作、搜索筛选等功能。
"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.security import HTTPBearer

from ..dependencies import get_current_user, get_task_service
from ..schemas import (
    # 任务相关模型
    TaskResponse,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskCompleteRequest,
    TaskStatisticsResponse,

    # Top3任务相关模型
    Top3TaskResponse,
    Top3TaskRequest,

    # 基础响应模型
    BaseResponse,
    PaginatedResponse
)
from ..responses import create_success_response, create_error_response

# 创建路由器
router = APIRouter(prefix="/tasks", tags=["任务管理"])

# HTTP Bearer认证方案
security = HTTPBearer()


# ================================
# 任务基础CRUD操作
# ================================

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    创建任务

    创建新任务，支持设置父任务建立层次结构。

    Args:
        request: 任务创建请求
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        TaskResponse: 创建的任务信息

    Raises:
        HTTPException: 当任务创建失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务创建方法
        # task = task_service.create_task(user_id, request.dict())

        # 临时模拟创建
        task_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": request.title,
            "description": request.description,
            "status": "pending",
            "priority": request.priority or "medium",
            "parent_id": request.parent_id,
            "sort_order": 0,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,
            "estimated_minutes": request.estimated_minutes,
            "actual_minutes": 0,
            "tags": request.tags or [],
            "subtasks_count": 0,
            "depth": 0
        }

        return create_success_response(
            data=TaskResponse(**task_data),
            message="任务创建成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 创建任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务创建失败: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    获取任务详情

    根据任务ID获取任务的详细信息。

    Args:
        task_id: 任务ID
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        TaskResponse: 任务详细信息

    Raises:
        HTTPException: 当任务不存在或无权访问时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务获取方法
        # task = task_service.get_task(task_id, user_id)

        # 临时模拟数据
        task_data = {
            "id": task_id,
            "user_id": user_id,
            "title": "示例任务",
            "description": "这是一个示例任务",
            "status": "pending",
            "priority": "medium",
            "parent_id": None,
            "sort_order": 0,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,
            "estimated_minutes": 30,
            "actual_minutes": 0,
            "tags": ["工作", "重要"],
            "subtasks_count": 0,
            "depth": 0
        }

        return create_success_response(
            data=TaskResponse(**task_data),
            message="获取任务成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 获取任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务失败: {str(e)}"
        )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    更新任务

    更新任务的基本信息，不包括状态。

    Args:
        task_id: 任务ID
        request: 任务更新请求
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        TaskResponse: 更新后的任务信息

    Raises:
        HTTPException: 当任务不存在、无权访问或更新失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务更新方法
        # task = task_service.update_task(task_id, user_id, request.dict())

        # 临时模拟更新
        task_data = {
            "id": task_id,
            "user_id": user_id,
            "title": request.title or "更新后的任务",
            "description": request.description,
            "status": "pending",
            "priority": request.priority or "medium",
            "parent_id": request.parent_id,
            "sort_order": request.sort_order or 0,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,
            "estimated_minutes": request.estimated_minutes,
            "actual_minutes": 0,
            "tags": request.tags or [],
            "subtasks_count": 0,
            "depth": 0
        }

        return create_success_response(
            data=TaskResponse(**task_data),
            message="任务更新成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 更新任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务更新失败: {str(e)}"
        )


@router.delete("/{task_id}", response_model=BaseResponse)
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    删除任务

    软删除任务，支持批量删除子任务。

    Args:
        task_id: 任务ID
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当任务不存在、无权访问或删除失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务删除方法
        # await task_service.delete_task(task_id, user_id)

        return create_success_response(
            message="任务删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 删除任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务删除失败: {str(e)}"
        )


# ================================
# 任务状态管理
# ================================

@router.put("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str,
    status: str = Body(..., description="任务状态"),
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    更新任务状态

    更新任务的状态，支持状态流转验证。

    Args:
        task_id: 任务ID
        status: 新的任务状态
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        TaskResponse: 更新后的任务信息

    Raises:
        HTTPException: 当状态流转无效或更新失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务状态更新方法
        # task = task_service.update_task_status(task_id, user_id, status)

        # 临时模拟状态更新
        task_data = {
            "id": task_id,
            "user_id": user_id,
            "title": "示例任务",
            "description": "这是一个示例任务",
            "status": status,
            "priority": "medium",
            "parent_id": None,
            "sort_order": 0,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": datetime.utcnow() if status == "completed" else None,
            "estimated_minutes": 30,
            "actual_minutes": 0,
            "tags": [],
            "subtasks_count": 0,
            "depth": 0
        }

        return create_success_response(
            data=TaskResponse(**task_data),
            message=f"任务状态已更新为: {status}"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 更新任务状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新任务状态失败: {str(e)}"
        )


@router.post("/{task_id}/complete", response_model=BaseResponse)
async def complete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    完成任务

    标记任务为已完成，触发完成逻辑（如奖励计算）。

    Args:
        task_id: 任务ID
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        BaseResponse: 任务完成结果

    Raises:
        HTTPException: 当任务完成失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务完成方法
        # result = task_service.complete_task(task_id, user_id)

        # 临时模拟完成结果
        completion_data = {
            "task_id": task_id,
            "completed_at": datetime.utcnow(),
            "experience_gained": 10,
            "fragments_gained": {"fragment1": 1, "fragment2": 2}
        }

        return create_success_response(
            message="任务完成！",
            data=completion_data
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 完成任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"完成任务失败: {str(e)}"
        )


# ================================
# 任务列表和搜索
# ================================

@router.get("/", response_model=PaginatedResponse)
async def get_tasks(
    parent_id: Optional[str] = Query(None, description="父任务ID"),
    status: Optional[str] = Query(None, description="任务状态"),
    priority: Optional[str] = Query(None, description="优先级"),
    tags: Optional[str] = Query(None, description="标签，多个用逗号分隔"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    获取任务列表

    支持多种筛选条件和分页。

    Args:
        parent_id: 父任务ID筛选
        status: 状态筛选
        priority: 优先级筛选
        tags: 标签筛选
        keyword: 关键词搜索
        page: 页码
        limit: 每页数量
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        PaginatedResponse: 分页的任务列表

    Raises:
        HTTPException: 当获取失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务获取列表方法
        # result = task_service.get_tasks(user_id, {
        #     "parent_id": parent_id,
        #     "status": status,
        #     "priority": priority,
        #     "tags": tags.split(',') if tags else [],
        #     "keyword": keyword,
        #     "page": page,
        #     "limit": limit
        # })

        # 临时模拟数据
        tasks = [
            {
                "id": f"task_{i}",
                "user_id": user_id,
                "title": f"任务 {i}",
                "description": f"这是第{i}个任务",
                "status": "pending",
                "priority": "medium",
                "parent_id": parent_id,
                "sort_order": i,
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "completed_at": None,
                "estimated_minutes": 30,
                "actual_minutes": 0,
                "tags": ["工作"],
                "subtasks_count": 0,
                "depth": 0
            }
            for i in range(1, min(limit + 1, 6))
        ]

        return create_success_response(
            data=PaginatedResponse(
                items=tasks,
                total=100,
                page=page,
                limit=limit,
                has_more=page * limit < 100,
                pages=(100 + limit - 1) // limit
            ),
            message="获取任务列表成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 获取任务列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务列表失败: {str(e)}"
        )


# ================================
# Top3任务管理
# ================================

@router.get("/top3/daily", response_model=Top3TaskResponse)
async def get_daily_top3(
    date: Optional[str] = Query(None, description="日期，格式YYYY-MM-DD，默认今天"),
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    获取每日Top3任务

    获取指定日期的Top3任务列表。

    Args:
        date: 日期，默认为今天
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        Top3TaskResponse: Top3任务列表

    Raises:
        HTTPException: 当获取失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务获取Top3方法
        # top3_tasks = task_service.get_daily_top3(user_id, date)

        # 临时模拟数据
        top3_data = {
            "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
            "tasks": [
                {
                    "id": "top3_1",
                    "title": "最重要的任务",
                    "description": "今天最重要的工作",
                    "status": "pending",
                    "priority": "high",
                    "estimated_minutes": 60
                },
                {
                    "id": "top3_2",
                    "title": "次要重要任务",
                    "description": "第二重要的工作",
                    "status": "pending",
                    "priority": "medium",
                    "estimated_minutes": 45
                },
                {
                    "id": "top3_3",
                    "title": "第三重要任务",
                    "description": "第三重要的工作",
                    "status": "completed",
                    "priority": "medium",
                    "estimated_minutes": 30
                }
            ],
            "completion_rate": 33.3
        }

        return create_success_response(
            data=Top3TaskResponse(**top3_data),
            message="获取每日Top3任务成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 获取每日Top3失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取每日Top3失败: {str(e)}"
        )


@router.put("/top3/daily", response_model=BaseResponse)
async def update_daily_top3(
    task_ids: List[str] = Body(..., description="Top3任务ID列表"),
    date: Optional[str] = Body(None, description="日期，格式YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    更新每日Top3任务

    设置或更新指定日期的Top3任务。

    Args:
        task_ids: Top3任务ID列表
        date: 日期
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当更新失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务更新Top3方法
        # top3_tasks = task_service.update_daily_top3(user_id, task_ids, date)

        return create_success_response(
            message="每日Top3任务更新成功",
            data={
                "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
                "task_ids": task_ids,
                "updated_at": datetime.utcnow()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 更新每日Top3失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新每日Top3失败: {str(e)}"
        )


# ================================
# 统计和分析
# ================================

@router.get("/statistics", response_model=TaskStatisticsResponse)
async def get_task_statistics(
    period: str = Query("week", regex="^(day|week|month|year)$", description="统计周期"),
    current_user: dict = Depends(get_current_user),
    task_service = Depends(get_task_service)
):
    """
    获取任务统计信息

    获取指定周期的任务统计数据。

    Args:
        period: 统计周期（day/week/month/year）
        current_user: 当前用户信息
        task_service: 任务服务实例

    Returns:
        TaskStatisticsResponse: 任务统计信息

    Raises:
        HTTPException: 当获取失败时
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现任务服务统计方法
        # stats = task_service.get_task_statistics(user_id, period)

        # 临时模拟统计数据
        stats_data = {
            "period": period,
            "total_tasks": 25,
            "completed_tasks": 18,
            "pending_tasks": 5,
            "cancelled_tasks": 2,
            "completion_rate": 72.0,
            "total_estimated_minutes": 750,
            "total_actual_minutes": 680,
            "efficiency_rate": 90.7,
            "on_time_completion_rate": 85.0,
            "priority_distribution": {
                "high": 8,
                "medium": 12,
                "low": 5
            },
            "daily_completion": [
                {"date": "2025-10-14", "completed": 3, "created": 4},
                {"date": "2025-10-15", "completed": 5, "created": 3},
                {"date": "2025-10-16", "completed": 4, "created": 2},
                {"date": "2025-10-17", "completed": 6, "created": 5},
                {"date": "2025-10-18", "completed": 0, "created": 1},
                {"date": "2025-10-19", "completed": 0, "created": 0},
                {"date": "2025-10-20", "completed": 0, "created": 0}
            ]
        }

        return create_success_response(
            data=TaskStatisticsResponse(**stats_data),
            message="获取任务统计成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[Task] 获取任务统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务统计失败: {str(e)}"
        )