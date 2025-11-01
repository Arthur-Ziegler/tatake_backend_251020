"""
Task领域API路由 - 微服务代理模式

将task domain的基础CRUD功能代理到Task微服务(localhost:20252)，
保持API路径、响应格式、认证方式完全不变。

替换的端点（5个）：
1. POST /tasks → 代理创建任务
2. GET /tasks/{task_id} → 代理查询单个
3. PUT /tasks/{task_id} → 代理更新任务
4. DELETE /tasks/{task_id} → 代理删除任务
5. GET /tasks → 代理查询列表

保留的端点（2个）：
- POST /tasks/{task_id}/complete（依赖奖励系统）
- POST /tasks/{task_id}/uncomplete

设计原则：
1. 代理模式：保持API路径完全不变
2. 格式转换：微服务格式 → 本地格式
3. 字段处理：缺失字段返回null
4. 错误处理：统一的异常处理机制

作者：TaKeKe团队
版本：2.0.0（微服务代理）
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

# 导入微服务客户端
from src.services.task_microservice_client import (
    call_task_service, TaskMicroserviceError,
    get_all_tasks, create_task, delete_task, update_task, complete_task,
    send_focus_status, get_pomodoro_count
)
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
# 认证模块已迁移到微服务，使用共用的统一响应格式
from src.api.schemas import UnifiedResponse
from .exceptions import (
    TaskException,
    TaskNotFoundException,
    TaskPermissionDeniedException,
    CircularReferenceException,
    InvalidTimeRangeException,
    TaskValidationException,
    TaskDatabaseException
)
# 导入认证依赖（认证模块已迁移到微服务）
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


def adapt_request_for_microservice(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    适配请求数据格式给微服务

    Args:
        request_data (Dict[str, Any]): 原始请求数据

    Returns:
        Dict[str, Any]: 适配后的请求数据
    """
    # 微服务可能不支持的字段，在请求中过滤掉
    unsupported_fields = {
        'parent_id', 'tags', 'service_ids',
        'planned_start_time', 'planned_end_time',
        'last_claimed_date', 'completion_percentage', 'is_deleted'
    }

    adapted_data = {k: v for k, v in request_data.items() if k not in unsupported_fields}
    return adapted_data


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

    # 映射状态字段
    if 'status' in microservice_data:
        microservice_data = microservice_data.copy()
        microservice_data['status'] = status_mapping.get(
            microservice_data['status'],
            microservice_data['status']  # 如果没有映射，保持原值
        )

    # 合并微服务数据和缺失字段
    adapted_data = {**missing_fields, **microservice_data}
    return adapted_data


@router.post("/", response_model=UnifiedResponse[TaskResponse], summary="创建新任务", description="创建一个新的任务，支持设置标题、描述、状态、优先级等基础信息。")
async def create_task(
    request: CreateTaskRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskResponse]:
    """
    创建新任务 - 微服务代理

    通过微服务代理创建任务，保持API完全兼容。
    """
    try:
        logger.info(f"创建任务API调用(微服务代理): user_id={user_id}, title={request.title}")

        # 调用新的微服务便捷方法
        microservice_response = await create_task(
            user_id=str(user_id),
            title=request.title,
            description=request.description,
            priority=request.priority or "medium",
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

        # 返回成功响应
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




@router.put("/{task_id}", response_model=UnifiedResponse[TaskResponse], summary="更新任务信息", description="更新现有任务的信息，包括标题、描述、状态、优先级等，支持部分更新。")
async def update_task(
    task_id: UUID,
    request: UpdateTaskRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskResponse]:
    """
    更新任务 - 微服务代理

    通过微服务代理更新任务信息。
    """
    try:
        logger.info(f"更新任务API调用(微服务代理): task_id={task_id}, user_id={user_id}")

        # 调用新的微服务便捷方法
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

        # 返回成功响应
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


@router.delete("/{task_id}", response_model=UnifiedResponse[TaskDeleteResponse], summary="删除任务", description="删除指定任务。")
async def delete_task(
    task_id: UUID,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[TaskDeleteResponse]:
    """
    删除任务 - 微服务代理

    通过微服务代理删除任务。
    """
    try:
        logger.info(f"删除任务API调用(微服务代理): task_id={task_id}, user_id={user_id}")

        # 调用新的微服务便捷方法
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
            deleted_count=1,  # 微服务可能不返回删除数量，默认为1
            cascade_deleted=False
        )

        # 返回成功响应
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


@router.get("/", response_model=UnifiedResponse[TaskListResponse], summary="获取任务列表")
async def get_task_list(
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小，1-100"),
    include_deleted: bool = Query(False, description="是否包含已删除的任务")
) -> UnifiedResponse[TaskListResponse]:
    """
    获取任务列表 - 微服务代理

    通过微服务代理获取任务列表。
    """
    try:
        logger.debug(f"获取任务列表API调用(微服务代理): user_id={user_id}, page={page}")

        # 调用新的微服务便捷方法
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
        list_data = microservice_response["data"]

        # 适配任务列表数据
        tasks = []
        for task_dict in list_data.get("tasks", []):
            adapted_task_dict = adapt_response_from_microservice(task_dict)
            tasks.append(TaskResponse(**adapted_task_dict))

        # 构造分页信息
        pagination_info = PaginationInfo(
            current_page=list_data.get("current_page", page),
            page_size=list_data.get("page_size", page_size),
            total_count=list_data.get("total_count", 0),
            total_pages=list_data.get("total_pages", 0),
            has_next=list_data.get("has_next", False),
            has_prev=list_data.get("has_prev", False)
        )

        # 构造TaskListResponse
        task_list_response = TaskListResponse(
            tasks=tasks,
            pagination=pagination_info
        )

        # 返回成功响应
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




# 以下端点保持不变，继续使用本地实现


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
    完成任务并触发奖励分发 - 本地实现（保持不变）

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
        logger.info(f"完成任务API调用(本地实现): task_id={task_id}, user_id={user_id}")

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
    取消任务完成状态 - 本地实现（保持不变）

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
        logger.info(f"取消任务完成API调用(本地实现): task_id={task_id}, user_id={user_id}")

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


# ============================
# 新增：专注状态和番茄钟接口
# ============================

@router.post(
    "/focus-status",
    response_model=UnifiedResponse[Dict[str, Any]],
    summary="发送专注状态",
    description="""
    发送用户专注状态到微服务

    **支持的状态：**
    - start: 开始专注
    - break: 休息
    - complete: 完成专注
    - pause: 暂停专注

    **请求参数：**
    - focus_status: 专注状态
    - task_id: 相关任务ID（可选）
    - duration_minutes: 专注时长（分钟，可选）
    """,
    responses={
        200: {
            "description": "专注状态记录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": {
                            "status": "start",
                            "task_id": "task-uuid",
                            "duration_minutes": 25,
                            "recorded_at": "2025-01-15T10:30:00Z"
                        },
                        "message": "专注状态记录成功"
                    }
                }
            }
        }
    }
)
async def send_focus_status(
    focus_status: str,
    user_id: UUID = Depends(get_current_user_id),
    task_id: Optional[UUID] = None,
    duration_minutes: Optional[int] = None
) -> UnifiedResponse[Dict[str, Any]]:
    """
    8. 发送专注状态

    Args:
        focus_status (str): 专注状态 (start, break, complete, pause)
        user_id (UUID): 用户ID
        task_id (UUID): 相关任务ID
        duration_minutes (int): 专注时长（分钟）

    Returns:
        UnifiedResponse[Dict[str, Any]]: 专注状态记录结果
    """
    try:
        logger.info(f"发送专注状态API调用: user_id={user_id}, status={focus_status}")

        # 调用微服务便捷方法
        microservice_response = await send_focus_status(
            user_id=str(user_id),
            focus_status=focus_status,
            task_id=str(task_id) if task_id else None,
            duration_minutes=duration_minutes
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=microservice_response["data"],
            message="专注状态记录成功"
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"发送专注状态异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.get(
    "/pomodoro-count",
    response_model=UnifiedResponse[Dict[str, Any]],
    summary="查看番茄钟计数",
    description="""
    获取用户的番茄钟统计数据

    **支持的时间过滤：**
    - today: 今日统计
    - week: 本周统计
    - month: 本月统计

    **响应数据：**
    - total_count: 总番茄钟数量
    - completed_count: 完成的番茄钟数量
    - total_focus_minutes: 总专注分钟数
    - average_duration: 平均专注时长
    """,
    responses={
        200: {
            "description": "番茄钟统计获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": {
                            "total_count": 12,
                            "completed_count": 10,
                            "total_focus_minutes": 250,
                            "average_duration": 25.0,
                            "date_filter": "today"
                        },
                        "message": "success"
                    }
                }
            }
        }
    }
)
async def get_pomodoro_count(
    user_id: UUID = Depends(get_current_user_id),
    date_filter: Optional[str] = Query("today", description="时间过滤: today, week, month")
) -> UnifiedResponse[Dict[str, Any]]:
    """
    9. 查看番茄钟计数

    Args:
        user_id (UUID): 用户ID
        date_filter (str): 时间过滤 (today, week, month)

    Returns:
        UnifiedResponse[Dict[str, Any]]: 番茄钟统计数据
    """
    try:
        logger.info(f"获取番茄钟计数API调用: user_id={user_id}, filter={date_filter}")

        # 调用微服务便捷方法
        microservice_response = await get_pomodoro_count(
            user_id=str(user_id),
            date_filter=date_filter
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse(
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=microservice_response["data"],
            message="获取番茄钟统计成功"
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


# 注释：异常处理器应该在主应用中定义，而不是在路由器中
# FastAPI使用app.exception_handler而不是router.exception_handler
# 任务领域的异常处理已在每个端点的try-catch块中处理