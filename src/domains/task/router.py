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

from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi import status
from fastapi import Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from sqlmodel import Session

from .service import TaskService
from src.domains.points.service import PointsService
from src.domains.reward.service import RewardService
from .completion_service import TaskCompletionService
from .schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListQuery,
    TaskResponse,
    TaskListResponse,
    TaskDeleteResponse,
    CompleteTaskRequest,
    CompleteTaskResponse,
    UncompleteTaskRequest,
    UncompleteTaskResponse,
    PaginationInfo
)
from src.domains.auth.schemas import UnifiedResponse
from .exceptions import (
    TaskException,
    TaskNotFoundException,
    TaskPermissionDeniedException,
    CircularReferenceException,
    InvalidTimeRangeException,
    TaskValidationException,
    TaskDatabaseException
)
# 导入认证依赖
from src.domains.auth.service import AuthService
from src.api.dependencies import get_current_user_id

# 导入优化后的数据库依赖
from src.database import SessionDep, get_db_session

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


@router.post("/", response_model=UnifiedResponse[TaskResponse], summary="创建新任务", description="创建一个新的任务，支持设置标题、描述、状态、优先级、父任务等完整信息。")
async def create_task(
    request: CreateTaskRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskResponse]:
    """
    创建新任务

    创建一个新的任务，支持设置标题、描述、状态、优先级、父任务等信息。

    Args:
        request (CreateTaskRequest): 创建任务请求
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[TaskResponse]: 创建成功的任务响应

    Raises:
        HTTPException: 请求参数错误或业务规则验证失败
    """
    try:
        logger.info(f"创建任务API调用: user_id={user_id}, title={request.title}")

        # 创建任务服务
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)

        # 执行业务逻辑
        task_result = task_service.create_task(request, user_id)

        # 构造TaskResponse
        task_data = TaskResponse(**task_result)

        # 返回成功响应
        return UnifiedResponse(
            code=201,
            data=task_data,
            message="任务创建成功"
        )

    except TaskException as e:
        logger.error(f"创建任务失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"创建任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.get("/{task_id}", response_model=UnifiedResponse[TaskResponse], summary="获取任务详情")
async def get_task(
    task_id: UUID,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskResponse]:
    """
    获取任务详情

    根据任务ID获取任务的详细信息，包括所有字段和计算字段。

    Args:
        task_id (UUID): 任务ID
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[TaskResponse]: 任务详情响应

    Raises:
        HTTPException: 任务不存在或无权限访问
    """
    try:
        logger.debug(f"获取任务API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务服务
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)

        # 执行业务逻辑
        task_result = task_service.get_task(task_id, user_id)

        # 构造TaskResponse
        task_data = TaskResponse(**task_result)

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=task_data,
            message="获取任务成功"
        )

    except TaskException as e:
        logger.error(f"获取任务失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.put("/{task_id}", response_model=UnifiedResponse[TaskResponse], summary="更新任务信息", description="更新现有任务的信息，包括标题、描述、状态、优先级等，支持部分更新。")
async def update_task(
    task_id: UUID,
    request: UpdateTaskRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskResponse]:
    """
    更新任务

    更新现有任务的信息，支持部分更新。只更新提供的字段。

    Args:
        task_id (UUID): 任务ID
        request (UpdateTaskRequest): 更新任务请求
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[TaskResponse]: 更新后的任务响应

    Raises:
        HTTPException: 任务不存在、无权限访问或业务规则验证失败
    """
    try:
        logger.info(f"更新任务API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务服务
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)

        # 执行业务逻辑（使用支持树结构的方法）
        task_result = task_service.update_task_with_tree_structure(task_id, request, user_id)

        # 构造TaskResponse
        task_data = TaskResponse(**task_result)

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=task_data,
            message="任务更新成功"
        )

    except TaskException as e:
        logger.error(f"更新任务失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"更新任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.delete("/{task_id}", response_model=UnifiedResponse[TaskDeleteResponse], summary="删除任务", description="软删除指定任务，任务会被标记为已删除但不会物理删除，支持恢复操作。")
async def delete_task(
    task_id: UUID,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskDeleteResponse]:
    """
    删除任务

    软删除指定的任务及其所有子任务。删除操作不可逆，请谨慎操作。

    Args:
        task_id (UUID): 任务ID
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[TaskDeleteResponse]: 删除操作结果响应

    Raises:
        HTTPException: 任务不存在或无权限访问
    """
    try:
        logger.info(f"删除任务API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务服务
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)

        # 执行业务逻辑
        delete_result = task_service.delete_task(task_id, user_id)

        # 构造TaskDeleteResponse
        deleted_count = delete_result.get("deleted_count", 0)
        delete_data = TaskDeleteResponse(
            deleted_task_id=str(task_id),
            deleted_count=deleted_count,
            cascade_deleted=deleted_count > 1
        )

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=delete_data,
            message=f"任务删除成功，共删除{deleted_count}个任务"
        )

    except TaskException as e:
        logger.error(f"删除任务失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"删除任务异常: {e}")
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
    page_size: int = Query(20, ge=1, le=100, description="每页大小，1-100"),
    include_deleted: bool = Query(False, description="是否包含已删除的任务")
) -> UnifiedResponse[TaskListResponse]:
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
        UnifiedResponse[TaskListResponse]: 任务列表和分页信息响应

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
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)

        # 执行业务逻辑
        list_result = task_service.get_task_list(query, user_id)

        # 构造TaskListResponse
        # 转换任务列表
        tasks = [TaskResponse(**task_data) for task_data in list_result.get("tasks", [])]

        # 构造分页信息
        pagination_info = PaginationInfo(
            current_page=list_result.get("current_page", page),
            page_size=list_result.get("page_size", page_size),
            total_count=list_result.get("total_count", 0),
            total_pages=list_result.get("total_pages", 0),
            has_next=list_result.get("has_next", False),
            has_prev=list_result.get("has_prev", False)
        )

        # 构造TaskListResponse
        list_data = TaskListResponse(
            tasks=tasks,
            pagination=pagination_info
        )

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=list_data,
            message="获取任务列表成功"
        )

    except TaskException as e:
        logger.error(f"获取任务列表失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务列表异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.post("/{task_id}/complete",
              response_model=UnifiedResponse[CompleteTaskResponse],
              summary="完成任务",
              description="完成任务并触发奖励分发。支持普通任务和Top3任务，奖励机制不同。",
              responses={
                  200: {
                      "description": "任务完成成功",
                      "content": {
                          "application/json": {
                              "examples": {
                                  "NormalTaskCompletion": {
                                      "summary": "普通任务完成",
                                      "description": "完成普通任务，获得2积分基础奖励",
                                      "value": {
                                          "code": 200,
                                          "data": {
                                              "task": {"status": "completed"},
                                              "completion_result": {"success": True},
                                              "message": "任务完成成功"
                                          }
                                      }
                                  },
                                  "Top3TaskCompletion": {
                                      "summary": "Top3任务完成",
                                      "description": "完成Top3任务，有概率获得100积分或随机奖品",
                                      "value": {
                                          "code": 200,
                                          "data": {
                                              "task": {"status": "completed"},
                                              "completion_result": {"success": True},
                                              "lottery_result": {"reward_type": "points", "amount": 100},
                                              "message": "恭喜！获得100积分奖励"
                                          }
                                      }
                                  }
                              }
                          }
                      }
                  }
              }
          )
async def complete_task(
    task_id: UUID,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id),
    request: Optional[CompleteTaskRequest] = Body(None)  # 修复：请求体可选，支持空请求
) -> UnifiedResponse[CompleteTaskResponse]:
    """
    完成任务并触发奖励分发

    业务流程：
    1. 验证任务存在性和权限
    2. 检查任务是否已完成
    3. 更新任务状态为完成（包含父任务完成度递归更新）
    4. 检测是否是Top3任务
    5. 分发积分奖励（普通任务2分，Top3任务抽奖）
    6. 记录所有流水
    7. 返回完成结果和奖励信息

    完成逻辑：
    - Top3任务：50%获得100积分，50%获得随机奖品
    - 非Top3任务：固定2积分
    - 支持多层任务树的父任务完成度自动更新
    - 永久防刷机制：一旦完成任务不能重复获得积分

    Args:
        task_id (UUID): 任务ID
        request (CompleteTaskRequest): 完成任务请求（空请求体）
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[CompleteTaskResponse]: 任务完成结果响应

    Raises:
        HTTPException: 任务不存在、无权限访问或业务逻辑异常
    """
    try:
        logger.info(f"完成任务API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务完成集成服务
        completion_service = TaskCompletionService(session)

        # 执行任务完成业务流程
        result = completion_service.complete_task(task_id, user_id)

        # 构建响应数据
        response_data = CompleteTaskResponse(
            task=result["data"]["task"],
            completion_result=result["data"]["completion_result"],
            lottery_result=result["data"].get("lottery_result"),
            parent_update=result["data"].get("parent_update"),
            message=result["data"]["message"]
        )

        # 返回成功响应
        return UnifiedResponse(
            code=result["code"],
            data=response_data,
            message=result["message"]
        )

    except TaskException as e:
        logger.error(f"完成任务失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"完成任务异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.post("/{task_id}/uncomplete",
              response_model=UnifiedResponse[UncompleteTaskResponse],
              summary="取消任务完成")
async def uncomplete_task(
    task_id: UUID,
    request: UncompleteTaskRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[UncompleteTaskResponse]:
    """
    取消任务完成状态

    业务流程：
    1. 验证任务存在性和权限
    2. 检查任务是否处于完成状态
    3. 更新任务状态为pending
    4. 递归更新父任务完成度
    5. 记录操作日志
    6. 返回操作结果

    注意事项：
    - 取消完成不会回收已发放的积分或奖励，这是业务规则决定
    - 支持多层任务树的父任务完成度自动回退
    - 操作不可逆，请谨慎执行

    Args:
        task_id (UUID): 任务ID
        request (UncompleteTaskRequest): 取消完成请求（空请求体）
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[UncompleteTaskResponse]: 取消完成操作结果响应

    Raises:
        HTTPException: 任务不存在、无权限访问或业务逻辑异常
    """
    try:
        logger.info(f"取消任务完成API调用: task_id={task_id}, user_id={user_id}")

        # 创建任务完成集成服务
        completion_service = TaskCompletionService(session)

        # 执行取消任务完成业务流程
        result = completion_service.uncomplete_task(task_id, user_id)

        # 构建响应数据
        response_data = UncompleteTaskResponse(
            task=result["data"]["task"],
            parent_update=result["data"].get("parent_update"),
            message=result["data"]["message"]
        )

        # 返回成功响应
        return UnifiedResponse(
            code=result["code"],
            data=response_data,
            message=result["message"]
        )

    except TaskException as e:
        logger.error(f"取消任务完成失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"取消任务完成异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


# 注释：异常处理器应该在主应用中定义，而不是在路由器中
# FastAPI使用app.exception_handler而不是router.exception_handler
# 任务领域的异常处理已在每个端点的try-catch块中处理