"""
简化的AI聊天服务

为了快速实现可工作的AI聊天API，这个简化版本提供了基本的聊天功能，
包括会话管理、消息处理和简单的AI回复生成。

后续可以逐步替换为更复杂的LangGraph实现。
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import asyncio
import time

from .base_performance_optimized import PerformanceOptimizedBaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    AuthorizationException
)
from ..models.chat import ChatSession, ChatMessage
from ..models.enums import ChatMode, MessageRole, SessionStatus
from ..repositories.chat import ChatRepository
from .logging_config import get_logger


class SimpleChatService(PerformanceOptimizedBaseService):
    """
    简化的AI聊天服务

    提供基础的聊天会话管理功能，包括：
    - 会话创建、查询、更新、删除
    - 消息发送和历史记录
    - 简单的AI回复生成（模拟）
    - 会话统计和分析

    这是一个临时实现，后续将被完整的LangGraph版本替换。
    """

    def __init__(self, chat_repo=None, **kwargs):
        """
        初始化简化聊天服务

        Args:
            chat_repo: 聊天数据仓储
            **kwargs: 其他参数传递给父类
        """
        super().__init__(chat_repo=chat_repo, **kwargs)
        self._chat_repo = chat_repo

        # 简单的AI回复模板
        self._ai_responses = {
            "general": [
                "我理解您的问题。让我来为您详细解答。",
                "这是一个很好的问题！根据我的分析...",
                "感谢您的提问。我建议您可以考虑以下几个方面...",
                "我很乐意帮助您。让我来提供一些有用的信息...",
                "您提出的这个问题很有意思。让我来分享一下我的看法..."
            ],
            "task_assistant": [
                "作为您的任务助手，我来帮您分析这个问题。",
                "让我们来制定一个具体的行动计划来解决这个任务。",
                "根据任务管理的最佳实践，我建议您...",
                "我来帮您把这个任务分解成更小的步骤。",
                "为了更好地完成这个任务，您可以考虑以下方案..."
            ],
            "learning": [
                "这是一个很好的学习机会！让我来详细解释。",
                "为了帮助您更好地理解，我来打个比方。",
                "这个概念涉及到几个关键点，让我逐一说明。",
                "学习这个知识点时，建议您掌握以下核心概念。",
                "让我用更简单的方式来解释这个问题。"
            ],
            "creative": [
                "这是一个很有创意的想法！让我来提供一些灵感。",
                "从创意的角度来看，我们可以尝试多种可能性。",
                "让我来用一种创新的方式思考这个问题。",
                "这个话题很有趣！让我们探索一些创意的解决方案。",
                "为了让这个想法更加独特，我建议您..."
            ]
        }

    async def create_session(
        self,
        user_id: str,
        title: str,
        chat_mode: str = "general",
        initial_message: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        创建新的聊天会话

        Args:
            user_id: 用户ID
            title: 会话标题
            chat_mode: 聊天模式
            initial_message: 初始消息
            tags: 会话标签

        Returns:
            创建的会话信息

        Raises:
            ValidationException: 参数验证失败
            BusinessException: 会话创建失败
        """
        start_time = time.time()

        try:
            # 参数验证
            self._validate_create_session_params(user_id, title, chat_mode)

            # 转换枚举值
            chat_mode_enum = self._convert_chat_mode(chat_mode)

            # 创建会话记录
            session = await self._chat_repo.create_session(
                user_id=uuid.UUID(user_id),
                title=title or "新会话",
                chat_mode=chat_mode_enum,
                status=SessionStatus.ACTIVE,
                session_metadata={
                    "initial_message": initial_message,
                    "tags": tags or [],
                    "created_by": "api"
                }
            )

            # 如果有初始消息，自动添加系统消息和用户消息
            if initial_message:
                # 添加系统欢迎消息
                system_message = await self._chat_repo.create_message(
                    session_id=session.id,
                    role=MessageRole.SYSTEM,
                    content=self._generate_welcome_message(chat_mode),
                    message_metadata={
                        "auto_generated": True,
                        "message_type": "welcome"
                    }
                )

                # 添加用户初始消息
                user_message = await self._chat_repo.create_message(
                    session_id=session.id,
                    role=MessageRole.USER,
                    content=initial_message,
                    message_metadata={
                        "initial_message": True,
                        "tags": tags
                    }
                )

                # 生成AI回复
                ai_response = self._generate_ai_response(initial_message, chat_mode)
                ai_message = await self._chat_repo.create_message(
                    session_id=session.id,
                    role=MessageRole.ASSISTANT,
                    content=ai_response,
                    message_metadata={
                        "auto_generated": True,
                        "response_time_ms": (time.time() - start_time) * 1000
                    }
                )

                # 更新会话消息计数
                await self._chat_repo.update_session_message_count(session.id, 3)

            else:
                # 只添加系统欢迎消息
                system_message = await self._chat_repo.create_message(
                    session_id=session.id,
                    role=MessageRole.SYSTEM,
                    content=self._generate_welcome_message(chat_mode),
                    message_metadata={
                        "auto_generated": True,
                        "message_type": "welcome"
                    }
                )

                # 更新会话消息计数
                await self._chat_repo.update_session_message_count(session.id, 1)

            processing_time = (time.time() - start_time) * 1000

            self._log_operation_success("create_session",
                                      session_id=str(session.id),
                                      user_id=user_id,
                                      chat_mode=chat_mode,
                                      processing_time_ms=processing_time)

            return {
                "id": str(session.id),
                "user_id": user_id,
                "title": session.title,
                "chat_mode": session.chat_mode.value,
                "status": session.status.value,
                "message_count": session.message_count,
                "last_activity_at": session.last_activity_at.isoformat(),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.session_metadata
            }

        except (ValidationException, BusinessException):
            raise
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._log_operation_error("create_session", e,
                                    user_id=user_id,
                                    title=title,
                                    processing_time_ms=processing_time)
            raise BusinessException(
                error_code="SESSION_CREATION_FAILED",
                message=f"会话创建失败: {str(e)}",
                details={
                    "user_id": user_id,
                    "title": title,
                    "chat_mode": chat_mode,
                    "processing_time_ms": processing_time
                }
            )

    async def get_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取聊天会话详情

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            会话详细信息

        Raises:
            ValidationException: 参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限访问会话
        """
        try:
            # 参数验证
            self._validate_session_access_params(session_id, user_id)

            # 获取会话信息
            session = await self._chat_repo.get_session_by_id(uuid.UUID(session_id))
            if not session:
                raise self._fast_not_found_error("ChatSession", session_id)

            # 权限验证
            if str(session.user_id) != user_id:
                raise AuthorizationException(
                    required_permission="access_chat_session",
                    details={
                        "session_id": session_id,
                        "user_id": user_id,
                        "session_user_id": str(session.user_id)
                    }
                )

            self._log_operation_success("get_session",
                                      session_id=session_id,
                                      user_id=user_id)

            return {
                "id": str(session.id),
                "user_id": str(session.user_id),
                "title": session.title,
                "chat_mode": session.chat_mode.value,
                "status": session.status.value,
                "message_count": session.message_count,
                "last_activity_at": session.last_activity_at.isoformat(),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.session_metadata
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._log_operation_error("get_session", e,
                                    session_id=session_id,
                                    user_id=user_id)
            raise BusinessException(
                error_code="SESSION_FETCH_FAILED",
                message=f"获取会话失败: {str(e)}",
                details={"session_id": session_id, "user_id": user_id}
            )

    async def get_sessions(
        self,
        user_id: str,
        status: Optional[str] = None,
        chat_mode: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取用户聊天会话列表

        Args:
            user_id: 用户ID
            status: 状态筛选
            chat_mode: 聊天模式筛选
            keyword: 搜索关键词
            page: 页码
            limit: 每页数量

        Returns:
            分页的会话列表
        """
        try:
            # 参数验证
            if page < 1:
                raise ValidationException(
                    message="页码必须大于0",
                    field="page",
                    value=page
                )
            if limit < 1 or limit > 100:
                raise ValidationException(
                    message="每页数量必须在1-100之间",
                    field="limit",
                    value=limit
                )

            # 转换筛选参数
            status_enum = self._convert_status(status) if status else None
            chat_mode_enum = self._convert_chat_mode(chat_mode) if chat_mode else None

            # 获取会话列表
            sessions, total = await self._chat_repo.get_user_sessions(
                user_id=uuid.UUID(user_id),
                status=status_enum,
                chat_mode=chat_mode_enum,
                keyword=keyword,
                limit=limit,
                offset=(page - 1) * limit
            )

            # 转换为响应格式
            session_list = []
            for session in sessions:
                session_list.append({
                    "id": str(session.id),
                    "user_id": str(session.user_id),
                    "title": session.title,
                    "chat_mode": session.chat_mode.value,
                    "status": session.status.value,
                    "message_count": session.message_count,
                    "last_activity_at": session.last_activity_at.isoformat(),
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "metadata": session.session_metadata
                })

            has_more = page * limit < total
            pages = (total + limit - 1) // limit

            self._log_operation_success("get_sessions",
                                      user_id=user_id,
                                      page=page,
                                      limit=limit,
                                      total_found=total)

            return {
                "items": session_list,
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": has_more,
                "pages": pages
            }

        except ValidationException:
            raise
        except Exception as e:
            self._log_operation_error("get_sessions", e,
                                    user_id=user_id,
                                    page=page,
                                    limit=limit)
            raise BusinessException(
                error_code="SESSIONS_FETCH_FAILED",
                message=f"获取会话列表失败: {str(e)}",
                details={"user_id": user_id}
            )

    async def update_session(
        self,
        session_id: str,
        user_id: str,
        title: Optional[str] = None,
        chat_mode: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        更新聊天会话

        Args:
            session_id: 会话ID
            user_id: 用户ID
            title: 新标题
            chat_mode: 新聊天模式
            status: 新状态
            tags: 新标签

        Returns:
            更新后的会话信息

        Raises:
            ValidationException: 参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限更新会话
        """
        try:
            # 参数验证和权限检查
            await self._check_session_access_permission(session_id, user_id)

            # 准备更新数据
            update_data = {}
            if title is not None:
                update_data["title"] = title
            if chat_mode is not None:
                update_data["chat_mode"] = self._convert_chat_mode(chat_mode)
            if status is not None:
                update_data["status"] = self._convert_status(status)

            # 更新元数据中的标签
            if tags is not None:
                session = await self._chat_repo.get_session_by_id(uuid.UUID(session_id))
                if session:
                    metadata = session.session_metadata.copy()
                    metadata["tags"] = tags
                    update_data["session_metadata"] = metadata

            # 执行更新
            updated_session = await self._chat_repo.update_session(
                uuid.UUID(session_id),
                title=update_data.get("title"),
                status=update_data.get("status"),
                session_metadata=update_data.get("session_metadata")
            )

            if not updated_session:
                raise self._fast_not_found_error("ChatSession", session_id)

            self._log_operation_success("update_session",
                                      session_id=session_id,
                                      user_id=user_id,
                                      update_fields=list(update_data.keys()))

            return {
                "id": str(updated_session.id),
                "user_id": str(updated_session.user_id),
                "title": updated_session.title,
                "chat_mode": updated_session.chat_mode.value,
                "status": updated_session.status.value,
                "message_count": updated_session.message_count,
                "last_activity_at": updated_session.last_activity_at.isoformat(),
                "created_at": updated_session.created_at.isoformat(),
                "updated_at": updated_session.updated_at.isoformat(),
                "metadata": updated_session.session_metadata
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._log_operation_error("update_session", e,
                                    session_id=session_id,
                                    user_id=user_id)
            raise BusinessException(
                error_code="SESSION_UPDATE_FAILED",
                message=f"会话更新失败: {str(e)}",
                details={"session_id": session_id, "user_id": user_id}
            )

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """
        删除聊天会话

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            是否删除成功

        Raises:
            ValidationException: 参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限删除会话
        """
        try:
            # 参数验证和权限检查
            await self._check_session_access_permission(session_id, user_id)

            # 执行删除
            success = await self._chat_repo.delete_session(uuid.UUID(session_id))

            if success:
                self._log_operation_success("delete_session",
                                          session_id=session_id,
                                          user_id=user_id)
            else:
                self._log_warning("delete_session",
                                "删除操作返回False，可能会话已被删除",
                                session_id=session_id,
                                user_id=user_id)

            return success

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._log_operation_error("delete_session", e,
                                    session_id=session_id,
                                    user_id=user_id)
            raise BusinessException(
                error_code="SESSION_DELETION_FAILED",
                message=f"会话删除失败: {str(e)}",
                details={"session_id": session_id, "user_id": user_id}
            )

    async def send_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
        message_type: str = "text",
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        发送聊天消息

        Args:
            session_id: 会话ID
            user_id: 用户ID
            content: 消息内容
            message_type: 消息类型
            attachments: 附件列表

        Returns:
            AI回复消息信息

        Raises:
            ValidationException: 参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限访问会话
        """
        start_time = time.time()

        try:
            # 参数验证
            self._validate_send_message_params(session_id, user_id, content)

            # 权限检查
            session = await self._check_session_access_permission(session_id, user_id)

            # 保存用户消息
            user_message = await self._chat_repo.create_message(
                session_id=uuid.UUID(session_id),
                role=MessageRole.USER,
                content=content,
                message_metadata={
                    "message_type": message_type,
                    "attachments": attachments or [],
                    "processing_time_ms": 0
                }
            )

            # 生成AI回复
            ai_response = self._generate_ai_response(
                content,
                session.chat_mode.value,
                session.title
            )

            processing_time = (time.time() - start_time) * 1000

            # 保存AI回复
            ai_message = await self._chat_repo.create_message(
                session_id=uuid.UUID(session_id),
                role=MessageRole.ASSISTANT,
                content=ai_response,
                message_metadata={
                    "message_type": "text",
                    "model": "simple-chat-v1",
                    "processing_time_ms": processing_time,
                    "attachments": [],
                    "user_message_id": str(user_message.id)
                }
            )

            # 更新会话活动时间和消息计数
            await self._chat_repo.update_session_activity(
                uuid.UUID(session_id),
                datetime.now(timezone.utc)
            )
            current_count = await self._chat_repo.count_session_messages(uuid.UUID(session_id))
            await self._chat_repo.update_session_message_count(uuid.UUID(session_id), current_count)

            self._log_operation_success("send_message",
                                      session_id=session_id,
                                      user_id=user_id,
                                      processing_time_ms=processing_time)

            return {
                "id": str(ai_message.id),
                "session_id": session_id,
                "user_id": user_id,
                "content": ai_response,
                "message_type": "text",
                "model": "simple-chat-v1",
                "created_at": ai_message.created_at.isoformat(),
                "attachments": [],
                "metadata": {
                    "processing_time_ms": processing_time,
                    "user_message_id": str(user_message.id)
                }
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._log_operation_error("send_message", e,
                                    session_id=session_id,
                                    user_id=user_id,
                                    processing_time_ms=processing_time)
            raise BusinessException(
                error_code="MESSAGE_SEND_FAILED",
                message=f"消息发送失败: {str(e)}",
                details={
                    "session_id": session_id,
                    "user_id": user_id,
                    "processing_time_ms": processing_time
                }
            )

    async def get_message_history(
        self,
        session_id: str,
        user_id: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        获取聊天历史记录

        Args:
            session_id: 会话ID
            user_id: 用户ID
            before: 获取指定消息ID之前的消息
            after: 获取指定消息ID之后的消息
            limit: 消息数量限制

        Returns:
            消息历史记录

        Raises:
            ValidationException: 参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限访问会话
        """
        try:
            # 参数验证
            self._validate_message_history_params(session_id, user_id, limit)

            # 权限检查
            await self._check_session_access_permission(session_id, user_id)

            # 获取消息历史
            messages = await self._chat_repo.get_session_messages(
                session_id=uuid.UUID(session_id),
                limit=limit,
                before_message_id=uuid.UUID(before) if before else None,
                after_message_id=uuid.UUID(after) if after else None
            )

            # 转换为响应格式
            message_list = []
            for message in messages:
                message_list.append({
                    "id": str(message.id),
                    "session_id": str(message.session_id),
                    "user_id": user_id,
                    "role": message.role.value,
                    "content": message.content,
                    "message_type": message.message_metadata.get("message_type", "text"),
                    "model": message.message_metadata.get("model"),
                    "created_at": message.created_at.isoformat(),
                    "attachments": message.message_metadata.get("attachments", []),
                    "metadata": message.message_metadata
                })

            # 获取总数
            total = await self._chat_repo.count_session_messages(uuid.UUID(session_id))
            has_more = len(message_list) == limit and len(message_list) < total

            self._log_operation_success("get_message_history",
                                      session_id=session_id,
                                      user_id=user_id,
                                      message_count=len(message_list))

            return {
                "messages": message_list,
                "has_more": has_more,
                "total": total
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._log_operation_error("get_message_history", e,
                                    session_id=session_id,
                                    user_id=user_id)
            raise BusinessException(
                error_code="MESSAGE_HISTORY_FETCH_FAILED",
                message=f"获取消息历史失败: {str(e)}",
                details={"session_id": session_id, "user_id": user_id}
            )

    async def get_chat_statistics(self, user_id: str, period: str = "week") -> Dict[str, Any]:
        """
        获取聊天统计信息

        Args:
            user_id: 用户ID
            period: 统计周期

        Returns:
            聊天统计信息
        """
        try:
            # 参数验证
            if not user_id:
                raise ValidationException(
                    message="用户ID不能为空",
                    field="user_id",
                    value=user_id
                )

            if period not in ["day", "week", "month", "year"]:
                raise ValidationException(
                    message="无效的统计周期",
                    field="period",
                    value=period
                )

            # 获取统计数据
            stats = await self._chat_repo.get_user_chat_statistics(
                uuid.UUID(user_id),
                period
            )

            self._log_operation_success("get_chat_statistics",
                                      user_id=user_id,
                                      period=period)

            return {
                "period": period,
                **stats
            }

        except ValidationException:
            raise
        except Exception as e:
            self._log_operation_error("get_chat_statistics", e,
                                    user_id=user_id,
                                    period=period)
            raise BusinessException(
                error_code="CHAT_STATISTICS_FETCH_FAILED",
                message=f"获取聊天统计失败: {str(e)}",
                details={"user_id": user_id, "period": period}
            )

    async def summarize_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        生成会话摘要

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            会话摘要结果
        """
        try:
            # 权限检查
            session = await self._check_session_access_permission(session_id, user_id)

            # 获取最近的消息用于生成摘要
            messages = await self._chat_repo.get_session_messages(
                uuid.UUID(session_id),
                limit=20
            )

            # 生成简单摘要（基于消息内容分析）
            summary = self._generate_session_summary(messages, session)

            self._log_operation_success("summarize_session",
                                      session_id=session_id,
                                      user_id=user_id)

            return {
                "session_id": session_id,
                "summary": summary["summary"],
                "key_points": summary["key_points"],
                "action_items": summary["action_items"],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._log_operation_error("summarize_session", e,
                                    session_id=session_id,
                                    user_id=user_id)
            raise BusinessException(
                error_code="SESSION_SUMMARIZATION_FAILED",
                message=f"会话摘要生成失败: {str(e)}",
                details={"session_id": session_id, "user_id": user_id}
            )

    async def export_session(self, session_id: str, user_id: str, format: str = "markdown") -> Dict[str, Any]:
        """
        导出聊天会话

        Args:
            session_id: 会话ID
            user_id: 用户ID
            format: 导出格式

        Returns:
            导出结果
        """
        try:
            # 权限检查
            session = await self._check_session_access_permission(session_id, user_id)

            # 获取完整消息历史
            messages = await self._chat_repo.get_session_messages(
                uuid.UUID(session_id),
                limit=1000  # 设置一个较大的限制
            )

            # 生成导出内容
            export_content = self._generate_export_content(messages, session, format)

            self._log_operation_success("export_session",
                                      session_id=session_id,
                                      user_id=user_id,
                                      format=format)

            return {
                "session_id": session_id,
                "format": format,
                "export_url": f"/api/v1/chat/sessions/{session_id}/download?format={format}",
                "expires_at": (datetime.now(timezone.utc).timestamp() + 3600 * 24), # 24小时后过期
                "content_length": len(export_content),
                "message_count": len(messages)
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._log_operation_error("export_session", e,
                                    session_id=session_id,
                                    user_id=user_id,
                                    format=format)
            raise BusinessException(
                error_code="SESSION_EXPORT_FAILED",
                message=f"会话导出失败: {str(e)}",
                details={"session_id": session_id, "user_id": user_id, "format": format}
            )

    # ==================== 辅助方法 ====================

    def _validate_create_session_params(self, user_id: str, title: str, chat_mode: str) -> None:
        """验证创建会话参数"""
        if not user_id:
            raise self._fast_validation_error("user_id", user_id, "用户ID不能为空")

        if not title or not title.strip():
            raise self._fast_validation_error("title", title, "会话标题不能为空")

        if len(title) > 200:
            raise self._fast_validation_error("title", title, "会话标题长度不能超过200个字符")

        if chat_mode not in ["general", "task_assistant", "learning", "creative"]:
            raise self._fast_validation_error("chat_mode", chat_mode, "无效的聊天模式")

    def _validate_session_access_params(self, session_id: str, user_id: str) -> None:
        """验证会话访问参数"""
        if not session_id:
            raise self._fast_validation_error("session_id", session_id, "会话ID不能为空")

        if not user_id:
            raise self._fast_validation_error("user_id", user_id, "用户ID不能为空")

    def _validate_send_message_params(self, session_id: str, user_id: str, content: str) -> None:
        """验证发送消息参数"""
        self._validate_session_access_params(session_id, user_id)

        if not content or not content.strip():
            raise self._fast_validation_error("content", content, "消息内容不能为空")

        if len(content) > 4000:
            raise self._fast_validation_error("content", content, "消息内容长度不能超过4000个字符")

    def _validate_message_history_params(self, session_id: str, user_id: str, limit: int) -> None:
        """验证消息历史参数"""
        self._validate_session_access_params(session_id, user_id)

        if limit < 1 or limit > 100:
            raise self._fast_validation_error("limit", limit, "消息数量限制必须在1-100之间")

    async def _check_session_access_permission(self, session_id: str, user_id: str) -> ChatSession:
        """
        检查会话访问权限

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            会话对象

        Raises:
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 无权限访问
        """
        session = await self._chat_repo.get_session_by_id(uuid.UUID(session_id))
        if not session:
            raise self._fast_not_found_error("ChatSession", session_id)

        if str(session.user_id) != user_id:
            raise AuthorizationException(
                required_permission="access_chat_session",
                details={
                    "session_id": session_id,
                    "user_id": user_id,
                    "session_user_id": str(session.user_id)
                }
            )

        return session

    def _convert_chat_mode(self, chat_mode: str) -> ChatMode:
        """转换聊天模式字符串为枚举"""
        mode_mapping = {
            "general": ChatMode.GENERAL,
            "task_assistant": ChatMode.TASK_ASSISTANT,
            "learning": ChatMode.PRODUCTIVITY_COACH,  # 使用PRODUCTIVITY_COACH作为学习模式
            "creative": ChatMode.FOCUS_GUIDE  # 使用FOCUS_GUIDE作为创意模式
        }
        return mode_mapping.get(chat_mode, ChatMode.GENERAL)

    def _convert_status(self, status: str) -> SessionStatus:
        """转换状态字符串为枚举"""
        status_mapping = {
            "active": SessionStatus.ACTIVE,
            "paused": SessionStatus.PAUSED,
            "completed": SessionStatus.COMPLETED,
            "archived": SessionStatus.ARCHIVED
        }
        return status_mapping.get(status, SessionStatus.ACTIVE)

    def _generate_welcome_message(self, chat_mode: str) -> str:
        """生成欢迎消息"""
        welcome_messages = {
            "general": "您好！我是您的AI助手，很高兴为您服务。请问有什么我可以帮助您的吗？",
            "task_assistant": "您好！我是您的任务助手，可以帮助您规划和管理任务。让我们开始高效的工作吧！",
            "learning": "您好！我是您的学习伙伴，可以帮您解答问题和提供学习指导。让我们一起开始学习之旅！",
            "creative": "您好！我是您的创意伙伴，可以帮助您激发灵感和实现创意。让我们开始创意探索吧！"
        }
        return welcome_messages.get(chat_mode, welcome_messages["general"])

    def _generate_ai_response(self, user_message: str, chat_mode: str, context: str = "") -> str:
        """生成AI回复"""
        import random

        # 获取对应模式的回复模板
        templates = self._ai_responses.get(chat_mode, self._ai_responses["general"])

        # 随机选择一个模板
        base_response = random.choice(templates)

        # 根据用户消息内容添加一些个性化
        if "你好" in user_message or "hi" in user_message.lower():
            return f"{base_response} 我是您的AI助手，有什么可以帮助您的吗？"
        elif "谢谢" in user_message or "thank" in user_message.lower():
            return "不客气！很高兴能帮助到您。还有其他需要我协助的地方吗？"
        elif "再见" in user_message or "bye" in user_message.lower():
            return "再见！期待下次为您服务。祝您有美好的一天！"
        else:
            return f"{base_response}\n\n针对您提到的「{user_message[:50]}{'...' if len(user_message) > 50 else ''}」，我建议您可以从以下几个方面来考虑..."

    def _generate_session_summary(self, messages: List[ChatMessage], session: ChatSession) -> Dict[str, Any]:
        """生成会话摘要"""
        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        ai_messages = [msg for msg in messages if msg.role == MessageRole.ASSISTANT]

        # 简单的摘要逻辑
        summary = f"这是一个关于「{session.title}」的对话，包含{len(user_messages)}条用户消息和{len(ai_messages)}条AI回复。"

        # 提取关键词
        all_content = " ".join([msg.content for msg in messages])
        key_points = []
        if "任务" in all_content:
            key_points.append("讨论了任务相关内容")
        if "学习" in all_content:
            key_points.append("涉及学习话题")
        if "时间" in all_content:
            key_points.append("提到了时间管理")

        if not key_points:
            key_points.append("进行了多方面的交流")

        # 生成行动项
        action_items = []
        if "计划" in all_content or "规划" in all_content:
            action_items.append("制定具体计划")
        if "尝试" in all_content or "实践" in all_content:
            action_items.append("实践讨论的方法")

        if not action_items:
            action_items.append("回顾和总结对话内容")

        return {
            "summary": summary,
            "key_points": key_points,
            "action_items": action_items
        }

    def _generate_export_content(self, messages: List[ChatMessage], session: ChatSession, format: str) -> str:
        """生成导出内容"""
        if format == "markdown":
            content = f"# {session.title}\n\n"
            content += f"**会话ID**: {session.id}\n"
            content += f"**聊天模式**: {session.chat_mode.value}\n"
            content += f"**创建时间**: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"**消息数量**: {len(messages)}\n\n"
            content += "---\n\n"

            for message in messages:
                role_name = "用户" if message.role == MessageRole.USER else "助手"
                content += f"## {role_name}\n\n"
                content += f"{message.content}\n\n"
                content += f"*{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                content += "---\n\n"

        elif format == "txt":
            content = f"会话标题: {session.title}\n"
            content += f"会话ID: {session.id}\n"
            content += f"聊天模式: {session.chat_mode.value}\n"
            content += f"创建时间: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"消息数量: {len(messages)}\n"
            content += "=" * 50 + "\n\n"

            for message in messages:
                role_name = "用户" if message.role == MessageRole.USER else "助手"
                content += f"[{role_name}] {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                content += f"{message.content}\n\n"

        else:  # json
            import json
            messages_data = []
            for message in messages:
                messages_data.append({
                    "role": message.role.value,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "metadata": message.message_metadata
                })

            session_data = {
                "session": {
                    "id": str(session.id),
                    "title": session.title,
                    "chat_mode": session.chat_mode.value,
                    "created_at": session.created_at.isoformat(),
                    "metadata": session.session_metadata
                },
                "messages": messages_data
            }
            content = json.dumps(session_data, ensure_ascii=False, indent=2)

        return content