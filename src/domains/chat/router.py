"""
Chat领域API路由

提供简化版聊天功能的4个核心HTTP API端点。

核心接口设计：
1. GET /chat/sessions - 查询所有会话列表
2. GET /chat/sessions/{session_id}/messages - 查询聊天记录
3. DELETE /chat/sessions/{session_id} - 删除会话
4. POST /chat/sessions/{session_id}/chat - 聊天接口（流式）

设计原则：
1. 极简化：只包含必要的功能
2. 统一响应：UnifiedResponse包装（除流式外）
3. 本地存储：SQLite存储会话信息
4. 流式响应：长连接保持5分钟
5. 自动创建session：聊天时自动创建会话

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""

import logging
import os
import json
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from starlette.responses import Response

from .models import init_chat_database, ChatSession
from .repository import ChatRepository
from .schemas import (
    SessionListItem,
    ChatHistoryResponse,
    ChatHistoryMessage,
    ChatMessageRequest,
    DeleteSessionResponse,
    ChatHealthResponse
)
from src.api.dependencies import get_current_user_id
from src.api.schemas import UnifiedResponse

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/chat", tags=["聊天系统"])

# 初始化聊天数据库
try:
    init_chat_database()
    logger.info("聊天数据库初始化成功")
except Exception as e:
    logger.error(f"聊天数据库初始化失败: {e}")


@router.get("/sessions", response_model=UnifiedResponse[List[SessionListItem]], summary="查询所有会话列表")
async def get_sessions(
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[List[SessionListItem]]:
    """
    查询所有会话列表

    - 输入：token（带有userid信息）
    - 过程：从token解析出userid，查询这个用户的所有会话session
    - 输出：一个列表，包含会话id，会话标题，只有两个东西
    """
    try:
        repository = ChatRepository()
        sessions = repository.get_user_sessions(str(user_id))

        # 转换为简化的响应格式
        session_list = [
            SessionListItem(
                session_id=session.session_id,
                title=session.title
            )
            for session in sessions
        ]

        logger.info(f"获取用户会话列表成功: user_id={user_id}, count={len(session_list)}")
        return UnifiedResponse(
            code=200,
            data=session_list,
            message="获取会话列表成功"
        )

    except Exception as e:
        logger.error(f"获取会话列表失败: user_id={user_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=[],
            message="获取会话列表失败"
        )


@router.get("/sessions/{session_id}/messages", response_model=UnifiedResponse[ChatHistoryResponse], summary="查询聊天记录")
async def get_chat_history(
    session_id: str,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[ChatHistoryResponse]:
    """
    查询聊天记录

    - 输入：token，sessionid
    - 过程：先验证userid是不是这个session的主人，如果是，就返回这个session的消息列表
    - 输出：一个json，包含：sessionid，session标题，session所有聊天记录；聊天记录是一个列表，分别是role，content和time。其中role只有assistant和human，time是UTC标准时间，context就是字符串。
    """
    try:
        repository = ChatRepository()

        # 验证会话是否存在且属于该用户
        session = repository.get_session_by_id(session_id, str(user_id))
        if not session:
            logger.warning(f"访问不存在的会话: session_id={session_id}, user_id={user_id}")
            return UnifiedResponse(
                code=404,
                data=None,
                message="会话不存在或无权限访问"
            )

        # 从微服务获取聊天记录
        from src.services.chat_microservice_client import get_chat_microservice_client
        client = get_chat_microservice_client()

        try:
            # 调用微服务获取消息历史
            response = await client.get_session_messages(session_id=session_id)

            # 转换微服务响应格式为本地格式
            if response.get("code") == 200 and "data" in response:
                microservice_data = response["data"]

                # 转换消息格式
                messages = []
                for msg in microservice_data.get("messages", []):
                    messages.append(ChatHistoryMessage(
                        role=msg["role"],  # human/assistant
                        content=msg["content"],
                        time=msg["created_at"]  # UTC时间
                    ))

                chat_history = ChatHistoryResponse(
                    session_id=session_id,
                    title=session.title,
                    messages=messages
                )

                logger.info(f"获取聊天记录成功: session_id={session_id}, user_id={user_id}, 消息数量={len(messages)}")
                return UnifiedResponse(
                    code=200,
                    data=chat_history,
                    message="获取聊天记录成功"
                )
            else:
                error_msg = response.get("message", "未知错误")
                logger.error(f"微服务获取聊天记录失败: {error_msg}")
                return UnifiedResponse(
                    code=response.get("code", 500),
                    data=None,
                    message=f"获取聊天记录失败: {error_msg}"
                )

        except Exception as e:
            logger.error(f"调用聊天微服务失败: session_id={session_id}, error={e}")
            return UnifiedResponse(
                code=500,
                data=None,
                message="聊天微服务暂时不可用"
            )

    except Exception as e:
        logger.error(f"获取聊天记录失败: session_id={session_id}, user_id={user_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="获取聊天记录失败"
        )


@router.delete("/sessions/{session_id}", response_model=UnifiedResponse[DeleteSessionResponse], summary="删除会话")
async def delete_session(
    session_id: str,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[DeleteSessionResponse]:
    """
    删除会话

    - 输入：token，session id
    - 过程：把这个session对应的session表信息与message信息全删掉
    - 结果：删除成功返回
    """
    try:
        repository = ChatRepository()

        # 删除本地会话记录
        success = repository.delete_session(session_id, str(user_id))

        if success:
            logger.info(f"删除会话成功: session_id={session_id}, user_id={user_id}")
            return UnifiedResponse(
                code=200,
                data=DeleteSessionResponse(success=True),
                message="删除会话成功"
            )
        else:
            logger.warning(f"删除会话失败，会话不存在: session_id={session_id}, user_id={user_id}")
            return UnifiedResponse(
                code=404,
                data=DeleteSessionResponse(success=False),
                message="会话不存在或无权限删除"
            )

    except Exception as e:
        logger.error(f"删除会话失败: session_id={session_id}, user_id={user_id}, error={e}")
        return UnifiedResponse(
            code=500,
            data=DeleteSessionResponse(success=False),
            message="删除会话失败"
        )


@router.post("/sessions/{session_id}/chat", summary="聊天接口（流式）")
async def chat_stream(
    session_id: str,
    request: ChatMessageRequest,
    user_id: UUID = Depends(get_current_user_id)
) -> StreamingResponse:
    """
    聊天接口（流式）

    - 输入：token，session id，message（字符串）
    - 过程：如果session不存在，就先创建一个session，标题用会话+时间占位。如果存在，就接着这个session开始聊天。
    - 输出：流式输出AI的返回结果，每一次就只有单纯的字符串，没有任何其他内容
    """
    try:
        repository = ChatRepository()

        # 检查会话是否存在
        session = repository.get_session_by_id(session_id, str(user_id))

        # 如果会话不存在，创建新会话
        if not session:
            from .utils import generate_default_title
            default_title = generate_default_title()
            session = repository.create_session(str(user_id), default_title)
            logger.info(f"自动创建新会话: session_id={session_id}, user_id={user_id}, title={default_title}")
        else:
            # 更新会话时间戳
            repository.update_session_timestamp(session_id, str(user_id))

        # 调用微服务的聊天功能
        from src.services.chat_microservice_client import get_chat_microservice_client
        client = get_chat_microservice_client()

        async def generate_stream():
            """生成流式响应"""
            try:
                # 调用微服务流式聊天
                async for token in client.stream_chat(
                    session_id=session_id,
                    message=request.message
                ):
                    # 直接返回微服务的token
                    yield token

            except Exception as e:
                logger.error(f"流式聊天微服务调用失败: {e}")
                yield "抱歉，聊天服务暂时不可用。"

        logger.info(f"开始流式聊天: session_id={session_id}, user_id={user_id}, message={request.message[:50]}...")

        # 返回流式响应，保持5分钟连接
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用nginx缓冲
            }
        )

    except Exception as e:
        logger.error(f"聊天接口失败: session_id={session_id}, user_id={user_id}, error={e}")

        # 返回错误响应
        async def error_stream():
            yield "抱歉，聊天服务暂时不可用。"

        return StreamingResponse(
            error_stream(),
            media_type="text/plain; charset=utf-8"
        )


@router.get("/health", response_model=UnifiedResponse[ChatHealthResponse], summary="聊天服务健康检查")
async def chat_health_check() -> UnifiedResponse[ChatHealthResponse]:
    """聊天服务健康检查"""
    try:
        from datetime import datetime, timezone

        # 检查数据库连接
        database_status = {"status": "connected"}
        try:
            repository = ChatRepository()
            # 尝试执行一个简单查询来验证数据库连接
            sessions = repository.get_user_sessions("health_check_test")
            database_status["connected"] = True
        except Exception as db_error:
            logger.warning(f"数据库连接检查失败: {db_error}")
            database_status = {"status": "disconnected", "error": str(db_error)}

        # 构造健康检查响应
        health_response = ChatHealthResponse(
            status="healthy",
            database=database_status,
            graph_initialized=True,  # 简化版本，总是返回True
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        return UnifiedResponse(
            code=200,
            data=health_response,
            message="聊天服务健康"
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="健康检查失败"
        )