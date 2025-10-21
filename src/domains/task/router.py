"""
Task领域API路由

提供任务管理的HTTP API端点，实现RESTful接口设计。

API端点设计：
1. POST /tasks - 创建任务
2. GET /tasks/{id} - 获取任务详情
3. PUT /tasks/{id} - 更新任务
4. DELETE /tasks/{id} - 删除任务
5. GET /tasks - 获取任务列表

设计原则：
1. RESTful设计：遵循REST API设计规范
2. 统一响应格式：所有API返回统一格式
3. 详细参数验证：使用Pydantic进行请求验证
4. 完整错误处理：提供详细的错误信息
5. 自动文档生成：支持FastAPI自动文档

权限控制：
- 所有API都需要JWT认证
- 用户只能操作自己的任务
- 自动从JWT token中提取用户ID

响应格式：
{
    "code": 200,
    "data": {...},
    "message": "success"
}

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from fastapi import status
from fastapi import Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from sqlmodel import Session

from .service import TaskService
from .schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListQuery,
    TaskCreateResponse,
    TaskGetResponse,
    TaskUpdateResponse,
    TaskDeleteResponseWrapper,
    TaskListResponseWrapper
)
from .exceptions import (
    TaskException,
    TaskNotFoundException,
    TaskPermissionDeniedException,
    CircularReferenceException,
    InvalidTimeRangeException,
    TaskValidationException,
    TaskDatabaseException
)
from .database import get_task_session

# 导入认证依赖
from src.domains.auth.service import AuthService
from src.api.dependencies import get_current_user_id

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/tasks", tags=["任务管理"])

# JWT认证
security = HTTPBearer()


def create_error_response(exception: TaskException) -> JSONResponse:
    """
    创建统一的错误响应

    Args:
        exception (TaskException): 任务异常

    Returns:
        JSONResponse: 错误响应
    """
    return JSONResponse(
        status_code=exception.status_code,
        content={
            "code": exception.status_code,
            "data": None,
            "message": exception.detail
        }
    )


@router.post("/", response_model=TaskCreateResponse, summary="创建任务")
async def create_task(
    request: CreateTaskRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_task_session)
) -> TaskCreateResponse:
    """
    创建新任务

    创建一个新的任务，支持设置标题、描述、状态、优先级、父任务等信息。

    Args:
        request (CreateTaskRequest): 创建任务请求
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        TaskCreateResponse: 创建成功的任务响应

    Raises:
        HTTPException: 请求参数错误或业务规则验证失败
    """
    try:
        logger.info(f"创建任务API调用: user_id={user_id}, title={request.title}")

        # 创建任务服务
        task_service = TaskService(session)

        # 执行业务逻辑
        task_response = task_service.create_task(request, user_id)

        # 返回成功响应
        return TaskCreateResponse(
            code=201,
            data=task_response,
            message="任务创建成功"
        )

    except TaskException as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        logger.error(f"创建任务异常: {e}")
        raise HTTPException(
            status_code=500,
            detail="内部服务器错误"
        )


@router.get("/{task_id}", response_model=TaskGetResponse, summary="获取任务详情")
async def get_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_task_session)
) -> TaskGetResponse:
    """
    获取任务详情

    根据任务ID获取任务的详细信息，包括所有字段和计算字段。

    Args:
        task_id (UUID): 任务ID
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        TaskGetResponse: 任务详情响应

    Raises:
        HTTPException: 任务不存在或无权限访问
    """
    try:
        logger.debug(f"获取任务API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务服务
        task_service = TaskService(session)

        # 执行业务逻辑
        task_response = task_service.get_task(task_id, user_id)

        # 返回成功响应
        return TaskGetResponse(
            code=200,
            data=task_response,
            message="获取任务成功"
        )

    except TaskException as e:
        logger.error(f"获取任务失败: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        logger.error(f"获取任务异常: {e}")
        raise HTTPException(
            status_code=500,
            detail="内部服务器错误"
        )


@router.put("/{task_id}", response_model=TaskUpdateResponse, summary="更新任务")
async def update_task(
    task_id: UUID,
    request: UpdateTaskRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_task_session)
) -> TaskUpdateResponse:
    """
    更新任务

    更新现有任务的信息，支持部分更新。只更新提供的字段。

    Args:
        task_id (UUID): 任务ID
        request (UpdateTaskRequest): 更新任务请求
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        TaskUpdateResponse: 更新后的任务响应

    Raises:
        HTTPException: 任务不存在、无权限访问或业务规则验证失败
    """
    try:
        logger.info(f"更新任务API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务服务
        task_service = TaskService(session)

        # 执行业务逻辑
        task_response = task_service.update_task(task_id, request, user_id)

        # 返回成功响应
        return TaskUpdateResponse(
            code=200,
            data=task_response,
            message="任务更新成功"
        )

    except TaskException as e:
        logger.error(f"更新任务失败: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        logger.error(f"更新任务异常: {e}")
        raise HTTPException(
            status_code=500,
            detail="内部服务器错误"
        )


@router.delete("/{task_id}", response_model=TaskDeleteResponseWrapper, summary="删除任务")
async def delete_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_task_session)
) -> TaskDeleteResponseWrapper:
    """
    删除任务

    软删除指定的任务及其所有子任务。删除操作不可逆，请谨慎操作。

    Args:
        task_id (UUID): 任务ID
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        TaskDeleteResponseWrapper: 删除操作结果响应

    Raises:
        HTTPException: 任务不存在或无权限访问
    """
    try:
        logger.info(f"删除任务API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务服务
        task_service = TaskService(session)

        # 执行业务逻辑
        delete_result = task_service.delete_task(task_id, user_id)

        # 返回成功响应
        return TaskDeleteResponseWrapper(
            code=200,
            data=delete_result,
            message=f"任务删除成功，共删除{delete_result.deleted_count}个任务"
        )

    except TaskException as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        logger.error(f"删除任务异常: {e}")
        raise HTTPException(
            status_code=500,
            detail="内部服务器错误"
        )


@router.get("/", response_model=TaskListResponseWrapper, summary="获取任务列表")
async def get_task_list(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小，1-100"),
    include_deleted: bool = Query(False, description="是否包含已删除的任务"),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_task_session)
) -> TaskListResponseWrapper:
    """
    获取任务列表 - 简化版本，只支持基本分页

    获取当前用户的任务列表，按创建时间倒序排列，支持分页和是否包含已删除任务。

    Args:
        page (int): 页码，从1开始
        page_size (int): 每页大小，1-100
        include_deleted (bool): 是否包含已删除的任务
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        TaskListResponseWrapper: 任务列表和分页信息响应

    Raises:
        HTTPException: 查询参数错误或业务逻辑异常
    """
    try:
        logger.debug(f"获取任务列表API调用: user_id={user_id}, page={page}")

        # 构建简化的查询对象
        query = TaskListQuery(
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
            sort_by="created_at",
            sort_order="desc"
        )

        # 创建任务服务
        task_service = TaskService(session)

        # 执行业务逻辑
        list_response = task_service.get_task_list(query, user_id)

        # 返回成功响应
        return TaskListResponseWrapper(
            code=200,
            data=list_response,
            message="获取任务列表成功"
        )

    except TaskException as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        logger.error(f"获取任务列表异常: {e}")
        raise HTTPException(
            status_code=500,
            detail="内部服务器错误"
        )


# 注释：异常处理器应该在主应用中定义，而不是在路由器中
# FastAPI使用app.exception_handler而不是router.exception_handler
# 任务领域的异常处理已在每个端点的try-catch块中处理