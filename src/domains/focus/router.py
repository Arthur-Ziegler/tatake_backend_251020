"""
Focus领域API路由

提供番茄钟系统的5个核心API端点：
1. POST /focus/sessions - 开始专注会话
2. POST /focus/sessions/{id}/pause - 暂停会话
3. POST /focus/sessions/{id}/resume - 恢复会话
4. POST /focus/sessions/{id}/complete - 完成会话
5. GET /focus/sessions - 获取会话列表

API设计原则：
1. RESTful风格：使用标准的HTTP方法和路径
2. 统一响应格式：所有API返回统一的JSON格式
3. 详细错误信息：提供清晰的错误描述
4. 权限验证：确保用户只能操作自己的会话

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from .service import FocusService
from .schemas import StartFocusRequest, FocusSessionResponse, FocusSessionListResponse, FocusOperationResponse
from .exceptions import FocusException
from .database import get_focus_session
from src.api.dependencies import get_current_user_id
from src.api.schemas import UnifiedResponse

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/focus", tags=["番茄钟系统"])


@router.post("/sessions", response_model=UnifiedResponse[FocusOperationResponse], summary="开始专注会话")
async def start_focus(
    request: StartFocusRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_focus_session)
) -> UnifiedResponse[FocusOperationResponse]:
    """
    开始专注会话

    业务逻辑：
    1. 验证任务是否存在且属于当前用户
    2. 自动关闭用户当前未完成的会话
    3. 创建新的专注会话

    请求参数：
    - task_id: 关联的任务ID（必填）
    - session_type: 会话类型，默认为"focus"

    权限要求：需要登录
    """
    try:
        service = FocusService(session)
        result = service.start_focus(user_id, request)  # 直接传入UUID对象
        response_data = FocusOperationResponse(session=result)
        return UnifiedResponse(
            code=200,
            data=response_data,
            message="专注会话开始"
        )
    except FocusException as e:
        logger.error(f"开始专注失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"开始专注失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="开始专注失败"
        )


@router.post("/sessions/{session_id}/pause", response_model=UnifiedResponse[FocusOperationResponse], summary="暂停专注会话")
async def pause_focus(
    session_id: str,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_focus_session)
) -> UnifiedResponse[FocusOperationResponse]:
    """
    暂停专注会话

    业务逻辑：
    1. 完成当前的专注会话
    2. 创建一个新的暂停会话
    3. 返回暂停会话信息

    权限要求：需要登录且只能暂停自己的会话
    """
    try:
        service = FocusService(session)
        result = service.pause_focus(session_id, user_id)
        response_data = FocusOperationResponse(session=result)
        return UnifiedResponse(
            code=200,
            data=response_data,
            message="专注会话已暂停"
        )
    except FocusException as e:
        logger.error(f"暂停专注失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"暂停专注失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="暂停专注失败"
        )


@router.post("/sessions/{session_id}/resume", response_model=UnifiedResponse[FocusOperationResponse], summary="恢复专注会话")
async def resume_focus(
    session_id: str,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_focus_session)
) -> UnifiedResponse[FocusOperationResponse]:
    """
    恢复专注会话

    业务逻辑：
    1. 完成当前的暂停会话
    2. 创建一个新的专注会话
    3. 返回新的专注会话信息

    权限要求：需要登录且只能恢复自己的暂停会话
    """
    try:
        service = FocusService(session)
        result = service.resume_focus(session_id, user_id)
        response_data = FocusOperationResponse(session=result)
        return UnifiedResponse(
            code=200,
            data=response_data,
            message="专注会话已恢复"
        )
    except FocusException as e:
        logger.error(f"恢复专注失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"恢复专注失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="恢复专注失败"
        )


@router.post("/sessions/{session_id}/complete", response_model=UnifiedResponse[FocusOperationResponse], summary="完成专注会话")
async def complete_focus(
    session_id: str,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_focus_session)
) -> UnifiedResponse[FocusOperationResponse]:
    """
    完成专注会话

    业务逻辑：
    1. 设置会话的结束时间为当前时间
    2. 返回完成的会话信息

    权限要求：需要登录且只能完成自己的会话
    """
    try:
        service = FocusService(session)
        result = service.complete_focus(session_id, user_id)
        response_data = FocusOperationResponse(session=result)
        return UnifiedResponse(
            code=200,
            data=response_data,
            message="专注会话已完成"
        )
    except FocusException as e:
        logger.error(f"完成专注失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"完成专注失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="完成专注失败"
        )


@router.get("/sessions", response_model=UnifiedResponse[FocusSessionListResponse], summary="获取专注会话列表")
async def get_focus_sessions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_focus_session)
) -> UnifiedResponse[FocusSessionListResponse]:
    """
    获取用户专注会话列表

    返回当前用户的所有会话记录，按时间倒序排列。
    支持分页查询。

    权限要求：需要登录
    """
    try:
        service = FocusService(session)
        result = service.get_user_sessions(user_id, page, page_size)
        # service返回的是dict，构造对应的Pydantic数据模型
        response_data = FocusSessionListResponse(**result)
        return UnifiedResponse(
            code=200,
            data=response_data,
            message="获取成功"
        )
    except Exception as e:
        logger.error(f"获取专注会话失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="获取专注会话失败"
        )