"""
专注系统API路由器

本模块实现专注系统的所有API端点，包括：
1. 专注会话管理（创建、开始、暂停、恢复、完成、删除）
2. 专注会话查询（列表、详情、统计）
3. 专注会话模板管理（创建、更新、删除、查询）

设计原则：
1. RESTful设计：遵循REST API设计原则
2. 状态管理：完整的会话状态流转控制
3. 数据验证：使用Pydantic进行严格的请求验证
4. 错误处理：统一的错误响应格式
5. 性能优化：数据库查询优化和响应缓存

API端点概览：
- POST   /sessions              - 创建专注会话
- POST   /sessions/{id}/start   - 开始专注会话
- POST   /sessions/{id}/pause   - 暂停专注会话
- POST   /sessions/{id}/resume  - 恢复专注会话
- POST   /sessions/{id}/complete - 完成专注会话
- GET    /sessions              - 获取专注会话列表
- GET    /sessions/{id}         - 获取专注会话详情
- DELETE /sessions/{id}         - 删除专注会话
- GET    /statistics            - 获取专注统计数据
- POST   /templates             - 创建专注模板
- GET    /templates             - 获取专注模板列表
- GET    /templates/{id}        - 获取专注模板详情
- PUT    /templates/{id}        - 更新专注模板
- DELETE /templates/{id}        - 删除专注模板

注意：由于路由器注册时使用了 /focus 前缀，所以实际API路径为：
- POST /api/v1/focus/sessions
- GET /api/v1/focus/statistics
- 等等...

使用示例：
    # 创建专注会话
    POST /focus/sessions
    {
        "task_id": "task-uuid",
        "title": "完成项目文档",
        "planned_duration_minutes": 25,
        "session_type": "focus"
    }

    # 开始专注会话
    POST /focus/sessions/session-uuid/start
"""

from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import (
    # 基础响应模型
    BaseResponse, ErrorResponse, PaginatedResponse,

    # 专注会话相关模型
    FocusSessionCreateRequest, FocusSessionUpdateRequest,
    FocusSessionResponse, FocusSessionCompleteRequest,
    FocusStatisticsParams, FocusStatisticsResponse,

    # 专注模板相关模型
    FocusTemplateCreateRequest, FocusTemplateUpdateRequest,
    FocusTemplateResponse
)
from ..dependencies import get_current_user, get_db_session
from src.services.exceptions import (
    BusinessException, ValidationException,
    ResourceNotFoundException
)
from src.repositories.focus import FocusRepository
from src.repositories.async_base import AsyncBaseRepository


# 创建路由器实例
router = APIRouter()


# ================================
# 依赖注入：获取Repository实例
# ================================

async def get_focus_repository(session: AsyncSession = Depends(get_db_session)) -> FocusRepository:
    """
    获取专注系统Repository实例

    Args:
        session: 数据库会话

    Returns:
        FocusRepository: 专注系统数据访问实例
    """
    return FocusRepository(session)


# ================================
# 专注会话管理API端点
# ================================

@router.post(
    "/sessions",
    response_model=FocusSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建专注会话",
    description="创建新的专注会话，支持番茄钟、休息等不同类型"
)
async def create_focus_session(
    request: FocusSessionCreateRequest,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    创建专注会话API端点

    创建一个新的专注会话，可以是专注工作、休息或长休息。
    支持关联到特定任务，也可以创建独立的专注会话。

    Args:
        request: 专注会话创建请求
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 创建的专注会话信息

    Raises:
        ValidationException: 请求参数验证失败
        BusinessException: 业务逻辑错误
        Exception: 数据库操作错误
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注会话创建逻辑
        # 1. 验证请求数据
        # 2. 检查关联任务是否存在（如果提供了task_id）
        # 3. 创建专注会话记录
        # 4. 返回创建的会话信息

        # 临时实现：返回模拟数据
        from uuid import uuid4
        session_data = {
            "id": str(uuid4()),
            "task_id": request.task_id,
            "title": request.title,
            "session_type": request.session_type,
            "planned_duration_minutes": request.planned_duration_minutes,
            "duration_minutes": None,
            "is_completed": False,
            "started_at": None,
            "ended_at": None,
            "mood_feedback": None,
            "notes": request.notes,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "user_id": user_id,
            "task": None,
            "efficiency_score": None,
            "is_active": False
        }

        return FocusSessionResponse(**session_data)

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": e.user_message or "请求参数验证失败",
                "details": e.details
            }
        )
    except BusinessException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "BUSINESS_ERROR",
                "message": e.user_message or "业务逻辑错误",
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.post(
    "/sessions/{session_id}/start",
    response_model=FocusSessionResponse,
    summary="开始专注会话",
    description="开始指定的专注会话，记录开始时间"
)
async def start_focus_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    开始专注会话API端点

    将指定的专注会话状态更新为进行中，记录开始时间。

    Args:
        session_id: 专注会话ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 更新后的专注会话信息

    Raises:
        ResourceNotFoundException: 专注会话不存在
        BusinessException: 会话状态不允许开始
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注会话开始逻辑
        # 1. 验证会话存在且属于当前用户
        # 2. 检查会话状态是否允许开始
        # 3. 更新会话状态和开始时间
        # 4. 返回更新后的会话信息

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话开始功能正在开发中"
        )

    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SESSION_NOT_FOUND",
                "message": e.user_message or "专注会话不存在",
                "details": e.details
            }
        )
    except BusinessException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "BUSINESS_ERROR",
                "message": e.user_message or "业务逻辑错误",
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.post(
    "/sessions/{session_id}/pause",
    response_model=FocusSessionResponse,
    summary="暂停专注会话",
    description="暂停进行中的专注会话"
)
async def pause_focus_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    暂停专注会话API端点

    暂停当前进行中的专注会话，记录暂停时间。

    Args:
        session_id: 专注会话ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 更新后的专注会话信息
    """
    try:
        # TODO: 实现专注会话暂停逻辑

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话暂停功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.post(
    "/sessions/{session_id}/resume",
    response_model=FocusSessionResponse,
    summary="恢复专注会话",
    description="恢复暂停的专注会话"
)
async def resume_focus_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    恢复专注会话API端点

    恢复之前暂停的专注会话，继续计时。

    Args:
        session_id: 专注会话ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 更新后的专注会话信息
    """
    try:
        # TODO: 实现专注会话恢复逻辑

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话恢复功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.put(
    "/sessions/{session_id}/pause",
    response_model=FocusSessionResponse,
    summary="暂停专注会话(PUT)",
    description="使用PUT方法暂停当前进行中的专注会话，记录暂停时间"
)
async def pause_focus_session_put(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    暂停专注会话API端点 (PUT方法)

    使用PUT方法暂停当前进行中的专注会话，记录暂停时间。
    遵循RESTful设计原则，PUT用于更新资源状态。

    Args:
        session_id: 专注会话ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 更新后的专注会话信息

    Raises:
        ResourceNotFoundException: 专注会话不存在
        BusinessException: 会话状态不允许暂停
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注会话暂停逻辑 (PUT版本)
        # 1. 验证会话存在且属于当前用户
        # 2. 检查会话状态是否允许暂停
        # 3. 更新会话状态为暂停，记录暂停时间
        # 4. 返回更新后的会话信息

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话暂停功能正在开发中"
        )

    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SESSION_NOT_FOUND",
                "message": e.user_message or "专注会话不存在",
                "details": e.details
            }
        )
    except BusinessException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "BUSINESS_ERROR",
                "message": e.user_message or "会话状态不允许暂停",
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.put(
    "/sessions/{session_id}/resume",
    response_model=FocusSessionResponse,
    summary="恢复专注会话(PUT)",
    description="使用PUT方法恢复已暂停的专注会话，记录恢复时间"
)
async def resume_focus_session_put(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    恢复专注会话API端点 (PUT方法)

    使用PUT方法恢复已暂停的专注会话，记录恢复时间。
    遵循RESTful设计原则，PUT用于更新资源状态。

    Args:
        session_id: 专注会话ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 更新后的专注会话信息

    Raises:
        ResourceNotFoundException: 专注会话不存在
        BusinessException: 会话状态不允许恢复
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注会话恢复逻辑 (PUT版本)
        # 1. 验证会话存在且属于当前用户
        # 2. 检查会话状态是否允许恢复
        # 3. 更新会话状态为进行中，记录恢复时间
        # 4. 返回更新后的会话信息

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话恢复功能正在开发中"
        )

    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SESSION_NOT_FOUND",
                "message": e.user_message or "专注会话不存在",
                "details": e.details
            }
        )
    except BusinessException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "BUSINESS_ERROR",
                "message": e.user_message or "会话状态不允许恢复",
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.post(
    "/sessions/{session_id}/complete",
    response_model=FocusSessionResponse,
    summary="完成专注会话",
    description="完成专注会话并记录反馈信息"
)
async def complete_focus_session(
    session_id: str,
    request: FocusSessionCompleteRequest,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    完成专注会话API端点

    完成指定的专注会话，记录结束时间、心情反馈和满意度评分。

    Args:
        session_id: 专注会话ID
        request: 专注会话完成请求
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 更新后的专注会话信息
    """
    try:
        # TODO: 实现专注会话完成逻辑
        # 1. 验证会话存在且属于当前用户
        # 2. 检查会话状态是否允许完成
        # 3. 更新会话状态、结束时间和反馈信息
        # 4. 计算实际持续时间和效率评分
        # 5. 返回更新后的会话信息

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话完成功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/sessions",
    response_model=PaginatedResponse,
    summary="获取专注会话列表",
    description="分页获取用户的专注会话列表"
)
async def get_focus_sessions(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    session_type: Optional[str] = Query(None, description="会话类型筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期筛选"),
    end_date: Optional[datetime] = Query(None, description="结束日期筛选"),
    is_completed: Optional[bool] = Query(None, description="完成状态筛选"),
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    获取专注会话列表API端点

    分页返回当前用户的专注会话列表，支持多种筛选条件。

    Args:
        page: 页码，从1开始
        limit: 每页数量，最大100
        session_type: 会话类型筛选
        start_date: 开始日期筛选
        end_date: 结束日期筛选
        is_completed: 完成状态筛选
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        PaginatedResponse: 分页的专注会话列表
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注会话列表查询逻辑
        # 1. 构建查询条件
        # 2. 执行分页查询
        # 3. 格式化返回数据

        # 临时实现：返回空列表
        return PaginatedResponse(
            items=[],
            total=0,
            page=page,
            limit=limit,
            has_more=False,
            pages=0
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/sessions/{session_id}",
    response_model=FocusSessionResponse,
    summary="获取专注会话详情",
    description="获取指定专注会话的详细信息"
)
async def get_focus_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    获取专注会话详情API端点

    返回指定专注会话的完整信息，包括关联的任务详情。

    Args:
        session_id: 专注会话ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusSessionResponse: 专注会话详细信息
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注会话详情查询逻辑
        # 1. 验证会话存在且属于当前用户
        # 2. 查询会话详细信息
        # 3. 查询关联任务信息（如果有）
        # 4. 计算效率评分和状态信息
        # 5. 返回格式化的会话详情

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话详情查询功能正在开发中"
        )

    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SESSION_NOT_FOUND",
                "message": e.user_message or "专注会话不存在",
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.delete(
    "/sessions/{session_id}",
    response_model=BaseResponse,
    summary="删除专注会话",
    description="删除指定的专注会话"
)
async def delete_focus_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    删除专注会话API端点

    删除指定的专注会话，只能删除未开始的或已完成的会话。

    Args:
        session_id: 专注会话ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        BaseResponse: 删除操作结果
    """
    try:
        # TODO: 实现专注会话删除逻辑
        # 1. 验证会话存在且属于当前用户
        # 2. 检查会话状态是否允许删除
        # 3. 执行软删除操作
        # 4. 返回删除结果

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注会话删除功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


# ================================
# 专注统计API端点
# ================================

@router.get(
    "/statistics",
    response_model=FocusStatisticsResponse,
    summary="获取专注统计数据",
    description="获取用户的专注时间统计信息"
)
async def get_focus_statistics(
    start_date: Optional[datetime] = Query(None, description="统计开始日期"),
    end_date: Optional[datetime] = Query(None, description="统计结束日期"),
    task_id: Optional[str] = Query(None, description="任务ID筛选"),
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    获取专注统计数据API端点

    返回用户在指定时间范围内的专注时间统计信息，
    包括总会话数、总时长、完成率、趋势数据等。

    Args:
        start_date: 统计开始日期
        end_date: 统计结束日期
        task_id: 任务ID筛选
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusStatisticsResponse: 专注统计数据
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注统计数据查询逻辑
        # 1. 设置默认时间范围（如果未提供）
        # 2. 查询会话统计数据
        # 3. 计算各种指标（总时长、完成率等）
        # 4. 生成趋势数据
        # 5. 返回统计结果

        # 临时实现：返回模拟统计数据
        return FocusStatisticsResponse(
            total_sessions=0,
            total_minutes=0,
            average_session_minutes=0.0,
            completion_rate=0.0,
            daily_average_minutes=0.0,
            mood_distribution={},
            session_type_distribution={},
            trend_data=[],
            best_day=None,
            current_streak=0
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


# ================================
# 专注模板管理API端点
# ================================

@router.post(
    "/templates",
    response_model=FocusTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建专注模板",
    description="创建自定义的专注会话模板"
)
async def create_focus_template(
    request: FocusTemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    创建专注模板API端点

    创建用户自定义的专注会话模板，支持不同的时间配置。

    Args:
        request: 专注模板创建请求
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusTemplateResponse: 创建的专注模板信息
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注模板创建逻辑
        # 1. 验证请求数据
        # 2. 检查用户是否已有默认模板（如果要设为默认）
        # 3. 创建模板记录
        # 4. 返回创建的模板信息

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注模板创建功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/templates",
    response_model=PaginatedResponse,
    summary="获取专注模板列表",
    description="分页获取用户的专注模板列表"
)
async def get_focus_templates(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    获取专注模板列表API端点

    分页返回当前用户的专注模板列表。

    Args:
        page: 页码，从1开始
        limit: 每页数量，最大100
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        PaginatedResponse: 分页的专注模板列表
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现专注模板列表查询逻辑

        return PaginatedResponse(
            items=[],
            total=0,
            page=page,
            limit=limit,
            has_more=False,
            pages=0
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/templates/{template_id}",
    response_model=FocusTemplateResponse,
    summary="获取专注模板详情",
    description="获取指定专注模板的详细信息"
)
async def get_focus_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    获取专注模板详情API端点

    返回指定专注模板的完整信息。

    Args:
        template_id: 专注模板ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusTemplateResponse: 专注模板详细信息
    """
    try:
        # TODO: 实现专注模板详情查询逻辑

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注模板详情查询功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.put(
    "/templates/{template_id}",
    response_model=FocusTemplateResponse,
    summary="更新专注模板",
    description="更新指定的专注模板信息"
)
async def update_focus_template(
    template_id: str,
    request: FocusTemplateUpdateRequest,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    更新专注模板API端点

    更新指定的专注模板配置信息。

    Args:
        template_id: 专注模板ID
        request: 专注模板更新请求
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        FocusTemplateResponse: 更新后的专注模板信息
    """
    try:
        # TODO: 实现专注模板更新逻辑

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注模板更新功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.delete(
    "/templates/{template_id}",
    response_model=BaseResponse,
    summary="删除专注模板",
    description="删除指定的专注模板"
)
async def delete_focus_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    删除专注模板API端点

    删除指定的专注模板。

    Args:
        template_id: 专注模板ID
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        BaseResponse: 删除操作结果
    """
    try:
        # TODO: 实现专注模板删除逻辑

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="专注模板删除功能正在开发中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/tasks/{task_id}/sessions",
    response_model=PaginatedResponse,
    summary="获取任务的专注会话记录",
    description="获取指定任务的所有专注会话记录，按时间倒序排列"
)
async def get_task_focus_sessions(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user),
    focus_repo: FocusRepository = Depends(get_focus_repository)
):
    """
    获取任务的专注会话记录API端点

    获取指定任务的所有专注会话记录，支持分页查询。

    Args:
        task_id: 任务ID
        page: 页码，从1开始
        page_size: 每页记录数
        current_user: 当前认证用户信息
        focus_repo: 专注系统Repository实例

    Returns:
        PaginatedResponse: 分页的专注会话记录列表

    Raises:
        ResourceNotFoundException: 任务不存在
        BusinessException: 查询失败
    """
    try:
        user_id = current_user["user_id"]

        # TODO: 实现任务专注会话查询逻辑
        # 1. 验证任务存在且属于当前用户
        # 2. 查询任务的所有专注会话记录
        # 3. 按时间倒序排列并分页
        # 4. 返回分页结果

        # 临时返回空结果
        return PaginatedResponse(
            success=True,
            message="获取任务专注会话记录成功",
            data={
                "items": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": 0,
                    "total_pages": 0
                }
            }
        )

    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "TASK_NOT_FOUND",
                "message": e.user_message or "任务不存在",
                "details": e.details
            }
        )
    except BusinessException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "BUSINESS_ERROR",
                "message": e.user_message or "业务逻辑错误",
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {"original_error": str(e)}
            }
        )