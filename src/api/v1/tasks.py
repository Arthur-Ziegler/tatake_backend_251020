"""
Tasks API v1

基于Phase 1 Day 2 Service层实现的TaskService，提供任务相关的HTTP API端点。

设计原则：
1. RESTful API设计，遵循OpenAPI规范
2. 统一响应格式，所有API返回标准JSON格式
3. 完整的错误处理和验证
4. JWT认证集成，确保API安全
5. 业务逻辑封装，所有复杂逻辑在Service层处理

端点设计：
- POST /tasks/{id}/complete - 完成任务并发放奖励
- GET /tasks - 获取用户任务列表
- GET /tasks/{id} - 获取单个任务详情

作者：TaKeKe团队
版本：1.0.0
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
import uvicorn

from fastapi import APIRouter, HTTPException, Depends, status, Query, BackgroundTasks
from sqlmodel import Session

from src.domains.task.service import TaskService
from src.domains.points.service import PointsService

router = APIRouter(prefix="/tasks", tags=["tasks"])

# 全局变量，模拟用户数据（实际项目中需要从JWT中获取）
TASK_COMPLETION_REWARDS = {
    "regular": 30,
    "top3": 50
}

class TaskResponse:
    """任务响应模型"""
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    parent_id: Optional[str] = None
    level: Optional[int] = None
    completion_percentage: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    points_rewarded: bool = False
    last_claimed_date: Optional[datetime] = None


class TaskCompletionResponse:
    """任务完成响应模型"""
    success: bool
    task_id: str
    reward_earned: int
    message: str
    reward_type: str


class TaskListResponse:
    """任务列表响应模型"""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class CreateTaskRequest:
    """创建任务请求模型"""
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    parent_id: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class UpdateTaskRequest:
    """更新任务请求模型"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    parent_id: Optional[str] = None
    completion_percentage: Optional[float] = None


# 错误处理器
@router.exception_handler(status_code=404)
async def task_not_found_exception(request: Request, exc: HTTPException):
    """任务未找到异常处理"""
    return {
        "code": "NOT_FOUND",
        "message": f"任务 {request.path_params.get('task_id', '')} 未找到",
        "details": "请检查任务ID是否正确"
    }

@router.exception_handler(status_code=403)
async def task_permission_denied_exception(request: Request, exc: HTTPException):
    """任务权限被拒绝异常处理"""
    return {
        "code": "PERMISSION_DENIED",
        "message": f"用户 {request.path_params.get('user_id', '')} 无权限操作此任务",
        "details": "请检查任务所有权或权限设置"
    }

@router.exception_handler(status_code=400)
async def validation_exception(request: Request, exc: Exception):
    """参数验证异常处理"""
    return {
        "code": "VALIDATION_ERROR",
        "message": f"请求参数验证失败: {str(exc)}",
        "details": "请检查请求参数格式和内容"
    }

@router.exception_handler(status_code=500)
async def internal_server_error(request: Request, exc: Exception):
    """服务器内部错误异常处理"""
    return {
        "code": "INTERNAL_ERROR",
        "message": f"服务器内部错误: {str(exc)}",
        "details": "请稍后重试"
    }

def get_task_service(session: Session) -> TaskService:
    """获取TaskService实例"""
    return TaskService(session, PointsService(session))

def parse_query_params(
    page: Optional[int] = Query(None, description="页码", ge=1, le=1000),
    page_size: Optional[int] = Query(None, description="每页大小", ge=10, le=50),
    status: Optional[str] = Query(None, description="任务状态筛选", enum=["pending", "completed", "cancelled"]),
    parent_id: Optional[str] = Query(None, description="父任务ID筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选", enum=["low", "medium", "high"]
):
    """解析查询参数"""
    return {
        "page": max(page or 1, 1),
        "page_size": min(page_size or 100, 100),
        "offset": (page - 1) * (page_size or 100),
        "status": status,
        "parent_id": parent_id
    }


@router.get("", response_model=TaskListResponse, status_code=status.HTTP_200_OK)
async def get_tasks(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    parent_id: Optional[str] = None,
    priority: Optional[str] = None,
    task_service: TaskService = Depends(get_task_service)
):
    """获取用户任务列表"""

    query_params = parse_query_params(page, page_size, status, parent_id, priority)

    # 验证用户权限（这里应该从JWT中获取）
    # user_id = getattr(request.state, "user_id", "未找到用户ID")

    # 获取任务列表
    tasks = task_service.get_tasks(
        user_id="demo_user",  # 实际项目中应从JWT获取
        limit=query_params["page_size"],
        offset=query_params["offset"],
        **query_params
    )

    # 构建响应
    total_tasks = len(tasks)
    total_pages = (total_tasks + page_size - 1) // page_size
    current_page = page

    response_data = [
        TaskResponse(
            id=str(task.id),
            user_id=str(task.user_id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            parent_id=task.parent_id,
            level=task.level,
            completion_percentage=task.completion_percentage,
            created_at=task.created_at,
            updated_at=task.updated_at,
            tags=task.tags,
            points_rewarded=task.points_rewarded
            last_claimed_date=task.last_claimed_date
        ) for task in tasks
    ]

    return TaskListResponse(
        tasks=response_data,
        total=total_tasks,
        page=current_page,
        page_size=page_size
    )


@router.get("/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def get_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """获取单个任务详情"""

    # 验证用户权限
    # user_id = getattr(request.state, "user_id", "未找到用户ID")

    # 获取任务详情
    task = task_service.get_task_details(user_id, task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 未找到")

    return TaskResponse(
        id=str(task.id),
        user_id=str(task.user_id),
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        parent_id=task.parent_id,
        level=task.level,
        completion_percentage=task.completion_percentage,
        created_at=task.created_at,
        updated_at=task.updated_at,
        tags=task.tags,
        points_rewarded=task.points_rewarded,
        last_claimed_date=task.last_claimed_date
    )


@router.post("/{task_id}/complete", response_model=TaskCompletionResponse, status_code=status.HTTP_200_OK)
async def complete_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
    completion_request: Optional[CreateTaskRequest] = None,
    task_service: TaskService = Depends(get_task_service)
):
    """完成任务并发放奖励"""

    # 验证用户权限
    # user_id = getattr(request.state, "user_id", "未找到用户ID")

    # 解析请求体
    if completion_request is None:
        try:
            request_body = await request.json()
        title = request_body.get("title", "")
        description = request_body.get("description", "")
        priority = request_body.get("priority", "medium")
    else:
        title = completion_request.title
        description = completion_request.description
        priority = completion_request.priority

    try:
        # 调用TaskService完成任务
        result = task_service.complete_task(user_id, task_id)

        # 返回完成结果
        return TaskCompletionResponse(
            success=result["success"],
            task_id=task_id,
            reward_earned=result["points_awarded"],
            message=result["message"],
            reward_type=result["reward_type"]
        )

    except HTTPException as exc:
        # 重新抛出由Service处理的异常
        raise exc


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CreateTaskRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """创建新任务"""

    # 验证用户权限
    # user_id = getattr(request.state, "user_id", "未找到用户ID")

    # 解析请求体
    title = request.title
    description = request.description
    priority = request.priority
    parent_id = request.parent_id

    try:
        # 创建任务
        task = task_service.create_task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id
        )

        return TaskResponse(
            id=str(task.id),
            user_id=user_id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            parent_id=task.parent_id,
            level=task.level,
            completion_percentage=task.completion_percentage,
            created_at=task.created_at,
            updated_at=task.updated_at,
            tags=task.tags,
            points_rewarded=task.points_rewarded,
            last_claimed_date=task.last_claimed_date
        )

    except HTTPException as exc:
        raise exc