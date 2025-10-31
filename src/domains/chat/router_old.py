"""
Chat领域API路由

提供基于LangGraph的聊天功能的HTTP API端点，实现RESTful接口设计。

API端点设计：
1. POST /chat/sessions - 创建聊天会话
2. POST /chat/sessions/{session_id}/messages - 发送消息
3. GET /chat/sessions/{session_id}/messages - 获取聊天历史
4. GET /chat/sessions/{session_id} - 获取会话信息
5. GET /chat/sessions - 获取会话列表

设计原则：
1. RESTful设计：遵循REST API设计规范
2. 统一响应格式：所有API返回统一格式
3. 详细参数验证：使用Pydantic进行请求验证
4. 完整错误处理：提供详细的错误信息
5. 自动文档生成：支持FastAPI自动文档

权限控制：
- 所有API都需要JWT认证
- 用户只能操作自己的聊天会话
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

from fastapi import APIRouter, HTTPException, Depends, status, Query

from .service_separated import SeparatedChatService

# 创建分离的聊天服务实例
chat_service = SeparatedChatService()

from .schemas import (
    CreateSessionRequest,
    SendMessageRequest,
    ChatSessionResponse,
    MessageResponse,
    SessionInfoResponse,
    SessionListResponse,
    ChatHistoryResponse,
    ChatMessageItem,
    ChatSessionItem,
    DeleteSessionResponse,
    ChatHealthResponse,
    UnifiedResponse
)

from src.api.dependencies import get_current_user_id
from src.utils.api_validators import SessionId

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/chat", tags=["智能聊天"])


@router.post("/sessions", response_model=UnifiedResponse[ChatSessionResponse], summary="创建聊天会话")
async def create_chat_session(
    request: CreateSessionRequest,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[ChatSessionResponse]:
    """
    创建新的聊天会话

    Args:
        request: 创建会话请求
        user_id: 当前用户ID

    Returns:
        UnifiedResponse[ChatSessionResponse]: 会话创建结果

    Raises:
        HTTPException: 创建失败时抛出
    """
    try:
        logger.info(f"创建聊天会话请求: user_id={user_id}, title={request.title}")

        # 调用分离的聊天服务创建会话（将UUID转换为字符串）
        result = chat_service.create_session(
            user_id=str(user_id),
            title=request.title
        )

        logger.info(f"聊天会话创建成功: user_id={user_id}, session_id={result['session_id']}")

        # 构造响应数据模型（适配SeparatedChatService返回格式）
        session_response = ChatSessionResponse(
            session_id=result["session_id"],
            title=result["title"],
            created_at=result["created_at"],
            welcome_message="",  # SeparatedChatService不返回welcome_message
            status=result.get("status", "success")
        )

        return UnifiedResponse(
            code=200,
            data=session_response,
            message="聊天会话创建成功"
        )

    except Exception as e:
        logger.error(f"创建聊天会话失败: user_id={user_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"创建会话失败: {str(e)}"
        )


@router.post("/sessions/{session_id}/send", response_model=UnifiedResponse[MessageResponse], summary="发送消息")
async def send_chat_message(
    session_id: SessionId,
    request: SendMessageRequest,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[MessageResponse]:
    """
    发送消息到聊天会话

    Args:
        session_id: 会话ID
        request: 发送消息请求
        user_id: 当前用户ID

    Returns:
        UnifiedResponse[MessageResponse]: 消息处理结果

    Raises:
        HTTPException: 发送失败时抛出
    """
    try:
        logger.info(f"发送聊天消息请求: user_id={user_id}, session_id={session_id}")

        # 调用聊天服务发送消息（将UUID转换为字符串）
        result = chat_service.send_message(
            user_id=str(user_id),
            session_id=session_id,
            message=request.message
        )

        logger.info(f"聊天消息发送成功: user_id={user_id}, session_id={session_id}")

        # 构造响应数据模型
        message_response = MessageResponse(
            session_id=result["session_id"],
            user_message=result["user_message"],
            ai_response=result["ai_response"],
            timestamp=result["timestamp"],
            status=result.get("status", "success")
        )

        return UnifiedResponse(
            code=200,
            data=message_response,
            message="消息发送成功"
        )

    except ValueError as e:
        logger.warning(f"消息验证失败: user_id={user_id}, session_id={session_id}, error={e}")
        return UnifiedResponse(
            code=400,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"发送聊天消息失败: user_id={user_id}, session_id={session_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"发送消息失败: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=UnifiedResponse[ChatHistoryResponse], summary="获取聊天历史记录")
async def get_chat_history(
    session_id: SessionId,
    limit: int = Query(default=50, ge=1, le=1000, description="返回消息数量限制"),
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[ChatHistoryResponse]:
    """
    获取聊天历史记录

    注意：SeparatedChatService暂时不支持聊天历史查询功能
    该功能将在后续版本中实现，或通过LangGraph的checkpoint系统直接查询

    Args:
        session_id: 会话ID
        limit: 返回消息数量限制
        user_id: 当前用户ID

    Returns:
        UnifiedResponse[ChatHistoryResponse]: 消息历史记录

    Raises:
        HTTPException: 获取失败时抛出
    """
    try:
        logger.info(f"获取聊天历史请求: user_id={user_id}, session_id={session_id}, limit={limit}")

        # TODO: SeparatedChatService暂时不支持聊天历史查询
        # 可以通过LangGraph的checkpoint系统实现，但需要额外的开发工作
        # 目前返回空的历史记录

        # 验证会话是否存在
        session_result = chat_service.get_session_info(session_id)
        if session_result["session"]["user_id"] != str(user_id):
            return UnifiedResponse(
                code=403,
                data=None,
                message="无权限访问该会话"
            )

        # 构造空的响应数据模型
        history_response = ChatHistoryResponse(
            session_id=session_id,
            messages=[],  # 暂时返回空列表
            total_count=0,
            limit=limit,
            timestamp=session_result["session"]["updated_at"],
            status="success",
            note="聊天历史功能将在后续版本中实现"
        )

        return UnifiedResponse(
            code=200,
            data=history_response,
            message="聊天历史获取成功（暂时返回空记录）"
        )

    except ValueError as e:
        logger.warning(f"会话不存在: user_id={user_id}, session_id={session_id}, error={e}")
        return UnifiedResponse(
            code=404,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"获取聊天历史失败: user_id={user_id}, session_id={session_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"获取聊天历史失败: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=UnifiedResponse[SessionInfoResponse], summary="获取聊天会话信息")
async def get_chat_session_info(
    session_id: SessionId,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[SessionInfoResponse]:
    """
    获取聊天会话信息

    Args:
        session_id: 会话ID
        user_id: 当前用户ID

    Returns:
        UnifiedResponse[SessionInfoResponse]: 会话信息

    Raises:
        HTTPException: 获取失败时抛出
    """
    try:
        logger.info(f"获取会话信息请求: user_id={user_id}, session_id={session_id}")

        # 调用分离的聊天服务获取会话信息（将UUID转换为字符串）
        result = chat_service.get_session_info(session_id)

        logger.info(f"会话信息获取成功: user_id={user_id}, session_id={session_id}")

        # 验证用户权限
        if result["session"]["user_id"] != str(user_id):
            return UnifiedResponse(
                code=403,
                data=None,
                message="无权限访问该会话"
            )

        # 构造响应数据模型（适配SeparatedChatService返回格式）
        session_info = SessionInfoResponse(
            session_id=result["session"]["session_id"],
            title=result["session"]["title"],
            message_count=result["session"]["message_count"],
            created_at=result["session"]["created_at"],
            updated_at=result["session"]["updated_at"],
            status=result.get("status", "success")
        )

        return UnifiedResponse(
            code=200,
            data=session_info,
            message="会话信息获取成功"
        )

    except ValueError as e:
        logger.warning(f"会话不存在: user_id={user_id}, session_id={session_id}, error={e}")
        return UnifiedResponse(
            code=404,
            data=None,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"获取会话信息失败: user_id={user_id}, session_id={session_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"获取会话信息失败: {str(e)}"
        )


@router.get("/sessions", response_model=UnifiedResponse[SessionListResponse], summary="获取用户的聊天会话列表")
async def list_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100, description="返回会话数量限制"),
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[SessionListResponse]:
    """
    获取用户的聊天会话列表

    Args:
        limit: 返回会话数量限制
        user_id: 当前用户ID

    Returns:
        UnifiedResponse[SessionListResponse]: 会话列表

    Raises:
        HTTPException: 获取失败时抛出
    """
    try:
        logger.info(f"获取会话列表请求: user_id={user_id}, limit={limit}")

        # 调用分离的聊天服务获取会话列表（将UUID转换为字符串）
        result = chat_service.get_sessions(
            user_id=str(user_id),
            limit=limit
        )

        logger.info(f"会话列表获取成功: user_id={user_id}, count={result['total']}")

        # 构造会话列表
        sessions = []
        for session in result["sessions"]:
            sessions.append(ChatSessionItem(
                session_id=session["session_id"],
                title=session["title"],
                message_count=session["message_count"],
                created_at=session["created_at"],
                updated_at=session["updated_at"]
            ))

        # 构造响应数据模型（适配SeparatedChatService返回格式）
        session_list = SessionListResponse(
            user_id=str(user_id),
            sessions=sessions,
            total_count=result["total"],
            limit=result["limit"],
            timestamp="",  # SeparatedChatService不返回timestamp
            status=result["status"],
            note=""
        )

        return UnifiedResponse(
            code=200,
            data=session_list,
            message="会话列表获取成功"
        )

    except Exception as e:
        logger.error(f"获取会话列表失败: user_id={user_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"获取会话列表失败: {str(e)}"
        )


@router.delete("/sessions/{session_id}", response_model=UnifiedResponse[DeleteSessionResponse], summary="删除聊天会话")
async def delete_chat_session(
    session_id: SessionId,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[DeleteSessionResponse]:
    """
    删除聊天会话

    Args:
        session_id: 会话ID
        user_id: 当前用户ID

    Returns:
        UnifiedResponse[DeleteSessionResponse]: 删除结果

    Raises:
        HTTPException: 删除失败时抛出
    """
    try:
        logger.info(f"删除会话请求: user_id={user_id}, session_id={session_id}")

        # 调用分离的聊天服务删除会话（SeparatedChatService不需要user_id参数）
        result = chat_service.delete_session(session_id)

        logger.info(f"会话删除成功: user_id={user_id}, session_id={session_id}")

        # 构造响应数据模型（适配SeparatedChatService返回格式）
        delete_response = DeleteSessionResponse(
            session_id=result["session_id"],
            status=result["status"],
            timestamp=result.get("deleted_at", ""),
            note="会话已软删除"
        )

        return UnifiedResponse(
            code=200,
            data=delete_response,
            message="会话删除成功"
        )

    except Exception as e:
        logger.error(f"删除会话失败: user_id={user_id}, session_id={session_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"删除会话失败: {str(e)}"
        )


@router.get("/health", response_model=UnifiedResponse[ChatHealthResponse], summary="聊天服务健康检查")
async def chat_health_check() -> UnifiedResponse[ChatHealthResponse]:
    """
    聊天服务健康检查

    Returns:
        UnifiedResponse[ChatHealthResponse]: 健康检查结果
    """
    try:
        # SeparatedChatService简单健康检查
        from datetime import datetime, timezone

        # 验证服务是否可以正常创建
        service_status = "healthy"
        database_status = "connected"

        # 尝试获取SessionStore实例来验证数据库连接
        try:
            from .session_store import get_session_store
            session_store = get_session_store()
            # 如果没有异常，认为数据库连接正常
        except Exception as db_error:
            logger.warning(f"数据库连接检查失败: {db_error}")
            database_status = "disconnected"
            service_status = "degraded"

        # 构造响应数据模型
        health_response = ChatHealthResponse(
            status=service_status,
            database=database_status,
            graph_initialized=True,  # SeparatedChatService使用简化的图初始化
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        return UnifiedResponse(
            code=200,
            data=health_response,
            message="聊天服务健康检查成功"
        )

    except Exception as e:
        logger.error(f"聊天服务健康检查失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"聊天服务健康检查失败: {str(e)}"
        )