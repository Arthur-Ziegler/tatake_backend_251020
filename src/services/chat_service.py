"""
聊天服务模块

该模块提供聊天会话的管理功能，采用面向对象设计和LangGraph状态机。
支持多种聊天模式、AI对话生成、上下文管理等高级功能。

核心组件：
- ChatService: 聊天服务主类
- ConversationCreationRequest: 对话创建请求
- ChatMessageRequest: 聊天消息请求
- ChatResponse: 聊天响应

设计原则：
- 服务层模式：封装业务逻辑和数据访问
- 依赖注入：通过构造函数注入依赖
- 异常处理：统一的异常处理和错误传播
- 状态管理：使用LangGraph状态机管理对话流程
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from uuid import UUID
import logging

# 导入服务层基类和异常
from .base import BaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    AuthorizationException
)

# 导入数据模型
from src.models.chat import (
    ChatSession as ChatSessionModel,
    ChatMessage as ChatMessageModel,
    ChatMode,
    MessageRole,
    SessionStatus
)

# 导入用户模型
from src.models.user import User

# 导入聊天组件
from src.services.chat.conversation import (
    ConversationManager,
    Conversation,
    Message,
    ConversationStatus,
    ChatMode as ConversationChatMode,
    MessageType,
    MessagePriority
)
from src.services.chat.ai_client import (
    AIConfig,
    AIClientFactory,
    LangGraphOrchestrator,
    ChatState,
    MessageHandler
)

# 导入仓储层
from src.repositories.chat import ChatRepository

logger = logging.getLogger(__name__)


@dataclass
class ConversationCreationRequest:
    """对话创建请求"""
    user_id: UUID
    title: str
    chat_mode: ChatMode = ChatMode.GENERAL
    initial_context: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


@dataclass
class ChatMessageRequest:
    """聊天消息请求"""
    session_id: UUID
    user_id: UUID
    content: str
    message_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    session_id: UUID
    message_id: UUID
    content: str
    message_type: str
    processing_time_ms: int
    timestamp: datetime
    metadata: Dict[str, Any]


class ChatService(BaseService):
    """
    聊天服务类

    提供完整的聊天会话管理功能，包括对话创建、消息处理、
    AI回复生成、上下文管理等。使用LangGraph状态机进行对话流程管理。

    Attributes:
        chat_repository: 聊天数据仓储
        conversation_manager: 对话管理器
        ai_orchestrator: LangGraph编排器
        ai_config: AI配置
    """

    def __init__(
        self,
        chat_repository: ChatRepository,
        conversation_manager: Optional[ConversationManager] = None,
        ai_orchestrator: Optional[LangGraphOrchestrator] = None,
        ai_config: Optional[AIConfig] = None
    ):
        """
        初始化聊天服务

        Args:
            chat_repository: 聊天数据仓储
            conversation_manager: 对话管理器（可选，用于测试）
            ai_orchestrator: AI编排器（可选，用于测试）
            ai_config: AI配置（可选，用于测试）
        """
        super().__init__()
        self._chat_repository = chat_repository

        # 初始化对话管理器
        self._conversation_manager = conversation_manager or ConversationManager()

        # 初始化AI配置和编排器
        self._ai_config = ai_config or AIConfig()
        self._ai_orchestrator = ai_orchestrator or self._create_ai_orchestrator()

    def _create_ai_orchestrator(self) -> LangGraphOrchestrator:
        """
        创建AI编排器

        Returns:
            AI编排器实例
        """
        try:
            # 创建AI提供商
            provider = AIClientFactory.create_provider(
                AIClientFactory.get_default_provider(),
                self._ai_config
            )

            # 创建编排器
            orchestrator = LangGraphOrchestrator(provider)

            self._logger.info(f"AI编排器创建成功，提供商: {AIClientFactory.get_default_provider()}")
            return orchestrator

        except Exception as e:
            self._logger.error(f"AI编排器创建失败: {str(e)}")
            raise BusinessException(
                error_code="AI_ORCHESTRATOR_CREATION_FAILED",
                message=f"AI编排器创建失败: {str(e)}",
                details={
                    "provider_type": AIClientFactory.get_default_provider(),
                    "model": self._ai_config.model
                }
            )

    async def create_conversation(self, request: ConversationCreationRequest) -> Dict[str, Any]:
        """
        创建新对话会话

        Args:
            request: 对话创建请求

        Returns:
            创建的对话信息

        Raises:
            ValidationException: 请求参数验证失败
            BusinessException: 对话创建失败
        """
        start_time = datetime.now(timezone.utc)

        try:
            # 参数验证
            self._validate_conversation_creation_request(request)

            # 验证用户存在性
            user = await self._chat_repository.get_user_by_id(request.user_id)
            if not user:
                raise ResourceNotFoundException(
                    resource_type="User",
                    resource_id=str(request.user_id)
                )

            # 转换聊天模式
            chat_mode = self._convert_chat_mode(request.chat_mode)

            # 创建对话对象
            conversation = self._conversation_manager.create_conversation(
                user_id=str(request.user_id),
                title=request.title,
                chat_mode=chat_mode,
                initial_context=request.initial_context,
                tags=request.tags
            )

            # 创建数据库记录
            session = await self._chat_repository.create_session(
                user_id=request.user_id,
                title=request.title,
                chat_mode=request.chat_mode,
                status=SessionStatus.ACTIVE,
                session_metadata={
                    "conversation_id": conversation.id,
                    "initial_context": request.initial_context,
                    "tags": request.tags
                }
            )

            # 添加系统消息
            system_content = MessageHandler.create_system_message(
                request.chat_mode.value,
                self._create_user_context(user)
            )

            system_message = Message(
                conversation_id=conversation.id,
                message_type=MessageType.SYSTEM,
                content=system_content,
                priority=MessagePriority.HIGH
            )

            self._conversation_manager.add_message(system_message)

            # 保存系统消息到数据库
            await self._chat_repository.create_message(
                session_id=session.id,
                role=MessageRole.SYSTEM,
                content=system_content,
                message_metadata={
                    "conversation_id": conversation.id,
                    "message_type": MessageType.SYSTEM.value,
                    "priority": MessagePriority.HIGH.value
                }
            )

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            self._logger.info(
                f"对话创建成功",
                extra={
                    "session_id": str(session.id),
                    "conversation_id": conversation.id,
                    "user_id": str(request.user_id),
                    "chat_mode": request.chat_mode.value,
                    "processing_time_ms": processing_time
                }
            )

            return {
                "session_id": session.id,
                "conversation_id": conversation.id,
                "title": conversation.title,
                "chat_mode": conversation.chat_mode.value,
                "status": conversation.status.value,
                "created_at": conversation.created_at.isoformat(),
                "system_message_id": system_message.id,
                "processing_time_ms": processing_time
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._logger.error(
                f"对话创建失败: {str(e)}",
                extra={
                    "user_id": str(request.user_id),
                    "title": request.title,
                    "processing_time_ms": processing_time
                }
            )
            raise BusinessException(
                error_code="CONVERSATION_CREATION_FAILED",
                message=f"对话创建失败: {str(e)}",
                details={
                    "user_id": str(request.user_id),
                    "title": request.title,
                    "chat_mode": request.chat_mode.value,
                    "processing_time_ms": processing_time
                }
            )

    async def send_message(self, request: ChatMessageRequest) -> ChatResponse:
        """
        发送聊天消息

        Args:
            request: 聊天消息请求

        Returns:
            聊天响应

        Raises:
            ValidationException: 请求参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限访问会话
            BusinessException: 消息发送失败
        """
        start_time = datetime.now(timezone.utc)

        try:
            # 参数验证
            self._validate_message_request(request)

            # 获取会话信息
            session = await self._chat_repository.get_session_by_id(request.session_id)
            if not session:
                raise ResourceNotFoundException(
                    resource_type="ChatSession",
                    resource_id=str(request.session_id)
                )

            # 权限验证
            if session.user_id != request.user_id:
                raise AuthorizationException(
                    required_permission="access_chat_session",
                    details={
                        "session_id": str(request.session_id),
                        "user_id": str(request.user_id),
                        "session_user_id": str(session.user_id)
                    }
                )

            # 获取对话对象
            conversation = self._get_conversation_by_session_id(str(request.session_id))
            if not conversation:
                # 如果对话不存在，重新创建
                conversation = self._recreate_conversation_from_session(session)

            # 创建用户消息
            user_message = Message(
                conversation_id=conversation.id,
                message_type=MessageType.USER,
                content=request.content,
                metadata=request.metadata or {}
            )

            # 保存用户消息到数据库
            user_message_record = await self._chat_repository.create_message(
                session_id=request.session_id,
                role=MessageRole.USER,
                content=request.content,
                message_metadata={
                    "conversation_id": conversation.id,
                    "message_type": MessageType.USER.value,
                    **(request.metadata or {})
                }
            )

            # 添加到对话管理器
            self._conversation_manager.add_message(user_message)

            # 获取消息历史
            messages = self._conversation_manager.get_messages(conversation.id, include_deleted=False)

            # 准备LangGraph状态
            chat_state = ChatState(
                messages=self._convert_to_langchain_messages(messages),
                user_context=self._create_user_context_from_session(session),
                conversation_metadata={
                    "session_id": str(request.session_id),
                    "conversation_id": conversation.id,
                    "chat_mode": conversation.chat_mode.value,
                    "title": conversation.title
                },
                processing_state="starting"
            )

            # 使用LangGraph编排器处理对话
            processed_state = await self._ai_orchestrator.process_conversation(chat_state)

            # 提取AI回复
            ai_response_content = self._extract_ai_response(processed_state)

            # 创建AI回复消息
            ai_message = Message(
                conversation_id=conversation.id,
                message_type=MessageType.ASSISTANT,
                content=ai_response_content,
                processing_time_ms=int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )
            )

            # 保存AI回复到数据库
            ai_message_record = await self._chat_repository.create_message(
                session_id=request.session_id,
                role=MessageRole.ASSISTANT,
                content=ai_response_content,
                metadata={
                    "conversation_id": conversation.id,
                    "message_type": MessageType.ASSISTANT.value,
                    "processing_time_ms": ai_message.processing_time_ms,
                    "langgraph_state": processed_state.get("processing_state", "unknown"),
                    "required_actions": processed_state.get("required_actions", [])
                }
            )

            # 添加到对话管理器
            self._conversation_manager.add_message(ai_message)

            # 更新对话活动
            conversation.update_activity()
            self._conversation_manager.update_conversation(conversation)

            # 更新会话状态
            await self._chat_repository.update_session_activity(
                session_id=request.session_id,
                last_activity_at=datetime.now(timezone.utc)
            )

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            self._logger.info(
                f"消息处理成功",
                extra={
                    "session_id": str(request.session_id),
                    "conversation_id": conversation.id,
                    "user_message_id": str(user_message_record.id),
                    "ai_message_id": str(ai_message_record.id),
                    "processing_time_ms": processing_time,
                    "langgraph_state": processed_state.processing_state
                }
            )

            return ChatResponse(
                session_id=request.session_id,
                message_id=ai_message_record.id,
                content=ai_response_content,
                message_type=MessageType.ASSISTANT.value,
                processing_time_ms=int(processing_time),
                timestamp=ai_message_record.created_at,
                metadata={
                    "conversation_id": conversation.id,
                    "langgraph_state": processed_state.processing_state,
                    "required_actions": processed_state.required_actions,
                    "user_message_id": str(user_message_record.id)
                }
            )

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._logger.error(
                f"消息处理失败: {str(e)}",
                extra={
                    "session_id": str(request.session_id),
                    "user_id": str(request.user_id),
                    "processing_time_ms": processing_time
                }
            )
            raise BusinessException(
                error_code="MESSAGE_PROCESSING_FAILED",
                message=f"消息处理失败: {str(e)}",
                details={
                    "session_id": str(request.session_id),
                    "user_id": str(request.user_id),
                    "processing_time_ms": processing_time
                }
            )

    async def get_conversation_history(
        self,
        session_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取对话历史

        Args:
            session_id: 会话ID
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            对话历史信息

        Raises:
            ValidationException: 请求参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限访问会话
        """
        try:
            # 参数验证
            if not session_id:
                raise ValidationException(
                    message="会话ID不能为空",
                    field="session_id",
                    value=session_id
                )
            if not user_id:
                raise ValidationException(
                    message="用户ID不能为空",
                    field="user_id",
                    value=user_id
                )
            if limit <= 0 or limit > 100:
                raise ValidationException(
                    message="返回数量限制必须在1-100之间",
                    field="limit",
                    value=limit
                )
            if offset < 0:
                raise ValidationException(
                    message="偏移量不能为负数",
                    field="offset",
                    value=offset
                )

            # 获取会话信息
            session = await self._chat_repository.get_session_by_id(session_id)
            if not session:
                raise ResourceNotFoundException(
                    resource_type="ChatSession",
                    resource_id=str(session_id)
                )

            # 权限验证
            if session.user_id != user_id:
                raise AuthorizationException(
                    required_permission="access_chat_session",
                    details={
                        "session_id": str(session_id),
                        "user_id": str(user_id),
                        "session_user_id": str(session.user_id)
                    }
                )

            # 获取消息历史
            messages = await self._chat_repository.get_session_messages(
                session_id=session_id,
                limit=limit,
                offset=offset
            )

            # 获取对话统计信息
            conversation = self._get_conversation_by_session_id(str(session_id))
            stats = None
            if conversation:
                stats = self._conversation_manager.get_conversation_stats(conversation.id)

            total_messages = await self._chat_repository.count_session_messages(session_id)

            return {
                "session_id": session_id,
                "title": session.title,
                "chat_mode": session.chat_mode.value,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "last_activity_at": session.last_activity_at.isoformat(),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role.value,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "metadata": msg.message_metadata
                    }
                    for msg in messages
                ],
                "conversation_stats": stats,
                "pagination": {
                    "total": total_messages,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_messages
                }
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._logger.error(
                f"获取对话历史失败: {str(e)}",
                extra={
                    "session_id": str(session_id),
                    "user_id": str(user_id)
                }
            )
            raise BusinessException(
                error_code="CONVERSATION_HISTORY_FETCH_FAILED",
                message=f"获取对话历史失败: {str(e)}",
                details={
                    "session_id": str(session_id),
                    "user_id": str(user_id)
                }
            )

    async def delete_conversation(self, session_id: UUID, user_id: UUID) -> bool:
        """
        删除对话

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            是否删除成功

        Raises:
            ValidationException: 请求参数验证失败
            ResourceNotFoundException: 会话不存在
            AuthorizationException: 用户无权限删除会话
        """
        try:
            # 参数验证
            if not session_id:
                raise ValidationException(
                    message="会话ID不能为空",
                    field="session_id",
                    value=session_id
                )
            if not user_id:
                raise ValidationException(
                    message="用户ID不能为空",
                    field="user_id",
                    value=user_id
                )

            # 获取会话信息
            session = await self._chat_repository.get_session_by_id(session_id)
            if not session:
                raise ResourceNotFoundException(
                    resource_type="ChatSession",
                    resource_id=str(session_id)
                )

            # 权限验证
            if session.user_id != user_id:
                raise AuthorizationException(
                    required_permission="delete_chat_session",
                    details={
                        "session_id": str(session_id),
                        "user_id": str(user_id),
                        "session_user_id": str(session.user_id)
                    }
                )

            # 获取对话对象并删除
            conversation = self._get_conversation_by_session_id(str(session_id))
            if conversation:
                self._conversation_manager.delete_conversation(conversation.id)

            # 删除数据库记录
            success = await self._chat_repository.delete_session(session_id)

            if success:
                self._logger.info(
                    f"对话删除成功",
                    extra={
                        "session_id": str(session_id),
                        "user_id": str(user_id)
                    }
                )

            return success

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            self._logger.error(
                f"对话删除失败: {str(e)}",
                extra={
                    "session_id": str(session_id),
                    "user_id": str(user_id)
                }
            )
            raise BusinessException(
                error_code="CONVERSATION_DELETION_FAILED",
                message=f"对话删除失败: {str(e)}",
                details={
                    "session_id": str(session_id),
                    "user_id": str(user_id)
                }
            )

    def _validate_conversation_creation_request(self, request: ConversationCreationRequest) -> None:
        """
        验证对话创建请求

        Args:
            request: 对话创建请求

        Raises:
            ValidationException: 验证失败
        """
        if not request.user_id:
            raise ValidationException(
                message="用户ID不能为空",
                field="user_id",
                value=request.user_id
            )

        if not request.title or not request.title.strip():
            raise ValidationException(
                message="对话标题不能为空",
                field="title",
                value=request.title
            )

        if len(request.title) > 200:
            raise ValidationException(
                message="对话标题长度不能超过200个字符",
                field="title",
                value=request.title
            )

        if not isinstance(request.chat_mode, ChatMode):
            raise ValidationException(
                message="无效的聊天模式",
                field="chat_mode",
                value=request.chat_mode
            )

        if request.tags and len(request.tags) > 20:
            raise ValidationException(
                message="标签数量不能超过20个",
                field="tags",
                value=len(request.tags)
            )

    def _validate_message_request(self, request: ChatMessageRequest) -> None:
        """
        验证消息请求

        Args:
            request: 消息请求

        Raises:
            ValidationException: 验证失败
        """
        if not request.session_id:
            raise ValidationException(
                message="会话ID不能为空",
                field="session_id",
                value=request.session_id
            )

        if not request.user_id:
            raise ValidationException(
                message="用户ID不能为空",
                field="user_id",
                value=request.user_id
            )

        if not request.content or not request.content.strip():
            raise ValidationException(
                message="消息内容不能为空",
                field="content",
                value=request.content
            )

        if len(request.content) > 10000:
            raise ValidationException(
                message="消息内容长度不能超过10000个字符",
                field="content",
                value=len(request.content)
            )

    def _convert_chat_mode(self, chat_mode: ChatMode) -> ConversationChatMode:
        """
        转换聊天模式

        Args:
            chat_mode: API层聊天模式

        Returns:
            服务层聊天模式
        """
        mode_mapping = {
            ChatMode.GENERAL: ConversationChatMode.GENERAL,
            ChatMode.TASK_ASSISTANT: ConversationChatMode.TASK_ASSISTANT,
            ChatMode.PRODUCTIVITY_COACH: ConversationChatMode.PRODUCTIVITY_COACH,
            ChatMode.FOCUS_GUIDE: ConversationChatMode.FOCUS_GUIDE
        }
        return mode_mapping.get(chat_mode, ConversationChatMode.GENERAL)

    def _create_user_context(self, user: User) -> Dict[str, Any]:
        """
        创建用户上下文

        Args:
            user: 用户对象

        Returns:
            用户上下文信息
        """
        return {
            "user_id": str(user.id),
            "username": getattr(user, 'nickname', 'Unknown User'),  # 使用nickname作为username
            "level": getattr(user, 'level', 1),
            "experience_points": getattr(user, 'experience_points', 0),
            "current_streak": getattr(user, 'current_streak', 0),
            "max_streak": getattr(user, 'max_streak', 0)
        }

    def _create_user_context_from_session(self, session: ChatSessionModel) -> Dict[str, Any]:
        """
        从会话创建用户上下文

        Args:
            session: 会话对象

        Returns:
            用户上下文信息
        """
        return {
            "session_id": str(session.id),
            "user_id": str(session.user_id),
            "chat_mode": session.chat_mode.value,
            "title": session.title
        }

    def _get_conversation_by_session_id(self, session_id: str) -> Optional[Conversation]:
        """
        根据会话ID获取对话

        Args:
            session_id: 会话ID

        Returns:
            对话对象或None
        """
        # 遍历所有对话，查找匹配的会话ID
        for conversation in self._conversation_manager._conversations.values():
            if conversation.metadata.get("session_id") == session_id:
                return conversation
        return None

    def _recreate_conversation_from_session(self, session: ChatSessionModel) -> Conversation:
        """
        从会话重新创建对话

        Args:
            session: 会话对象

        Returns:
            重新创建的对话对象
        """
        conversation = self._conversation_manager.create_conversation(
            user_id=str(session.user_id),
            title=session.title,
            chat_mode=self._convert_chat_mode(session.chat_mode),
            initial_context=session.session_metadata.get("initial_context", {}),
            tags=session.session_metadata.get("tags", [])
        )

        # 更新对话元数据
        conversation.update_context("session_id", str(session.id))
        conversation.metadata["session_id"] = str(session.id)

        return conversation

    def _convert_to_langchain_messages(self, messages: List[Message]) -> List[Any]:
        """
        转换为LangChain消息格式

        Args:
            messages: 消息列表

        Returns:
            LangChain消息列表
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        langchain_messages = []
        for msg in messages:
            if msg.message_type == MessageType.USER:
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.message_type == MessageType.ASSISTANT:
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.message_type == MessageType.SYSTEM:
                langchain_messages.append(SystemMessage(content=msg.content))

        return langchain_messages

    def _extract_ai_response(self, processed_state) -> str:
        """
        提取AI回复内容

        Args:
            processed_state: 处理后的状态（可能是ChatState对象或字典）

        Returns:
            AI回复内容
        """
        # 处理字典格式的状态
        if isinstance(processed_state, dict):
            if "messages" in processed_state and processed_state["messages"]:
                last_message = processed_state["messages"][-1]
                if hasattr(last_message, 'content'):
                    return last_message.content
                elif isinstance(last_message, str):
                    return last_message
                else:
                    return str(last_message)
            return "抱歉，我现在无法回复您的消息。"

        # 处理ChatState对象
        if hasattr(processed_state, 'messages') and processed_state.messages:
            last_message = processed_state.messages[-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            elif isinstance(last_message, str):
                return last_message
            else:
                return str(last_message)

        return "抱歉，我现在无法回复您的消息。"