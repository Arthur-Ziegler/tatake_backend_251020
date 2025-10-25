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

from .service import chat_service
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

        # 调用聊天服务创建会话（将UUID转换为字符串）
        result = chat_service.create_session(
            user_id=str(user_id),
            title=request.title
        )

        logger.info(f"聊天会话创建成功: user_id={user_id}, session_id={result['session_id']}")

        # 构造响应数据模型
        session_response = ChatSessionResponse(
            session_id=result["session_id"],
            title=result["title"],
            created_at=result["created_at"],
            welcome_message=result.get("welcome_message", ""),
            status=result.get("status", "created")
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
    session_id: str,
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
    session_id: str,
    limit: int = Query(default=50, ge=1, le=1000, description="返回消息数量限制"),
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[ChatHistoryResponse]:
    """
    获取聊天历史记录

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

        # 调用聊天服务获取历史（将UUID转换为字符串）
        result = chat_service.get_chat_history(
            user_id=str(user_id),
            session_id=session_id,
            limit=limit
        )

        logger.info(f"聊天历史获取成功: user_id={user_id}, session_id={session_id}, count={result['total_count']}")

        # 构造消息列表
        messages = []
        for msg in result["messages"]:
            messages.append(ChatMessageItem(
                type=msg["type"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            ))

        # 构造响应数据模型
        history_response = ChatHistoryResponse(
            session_id=result["session_id"],
            messages=messages,
            total_count=result["total_count"],
            limit=result.get("limit", limit),
            timestamp=result["timestamp"],
            status=result.get("status", "success")
        )

        return UnifiedResponse(
            code=200,
            data=history_response,
            message="聊天历史获取成功"
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
    session_id: str,
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

        # 调用聊天服务获取会话信息（将UUID转换为字符串）
        result = chat_service.get_session_info(
            user_id=str(user_id),
            session_id=session_id
        )

        logger.info(f"会话信息获取成功: user_id={user_id}, session_id={session_id}")

        # 构造响应数据模型
        session_info = SessionInfoResponse(
            session_id=result["session_id"],
            title=result["title"],
            message_count=result["message_count"],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
            status=result["status"]
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

        # 调用聊天服务获取会话列表（将UUID转换为字符串）
        result = chat_service.list_sessions(
            user_id=str(user_id),
            limit=limit
        )

        logger.info(f"会话列表获取成功: user_id={user_id}, count={result['total_count']}")

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

        # 构造响应数据模型
        session_list = SessionListResponse(
            user_id=result["user_id"],
            sessions=sessions,
            total_count=result["total_count"],
            limit=result["limit"],
            timestamp=result["timestamp"],
            status=result["status"],
            note=result.get("note", "")
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
    session_id: str,
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

        # 调用聊天服务删除会话（将UUID转换为字符串）
        result = chat_service.delete_session(
            user_id=str(user_id),
            session_id=session_id
        )

        logger.info(f"会话删除成功: user_id={user_id}, session_id={session_id}")

        # 构造响应数据模型
        delete_response = DeleteSessionResponse(
            session_id=result["session_id"],
            status=result["status"],
            timestamp=result["timestamp"],
            note=result.get("note", "")
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
        result = chat_service.health_check()

        # 构造响应数据模型
        health_response = ChatHealthResponse(
            status=result["status"],
            database=result["database"],
            graph_initialized=result.get("graph_initialized", False),
            timestamp=result["timestamp"]
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