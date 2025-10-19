"""
聊天服务模块

该模块提供基于LangGraph框架的AI对话服务，支持复杂的对话流程管理、
多轮对话上下文维护、以及智能的任务辅助功能。

核心功能：
- 对话会话创建和管理
- 多轮对话上下文维护
- 基于LangGraph的对话流程编排
- 智能任务辅助和建议
- 对话历史存储和检索
- 实时流式响应支持
- 对话质量评估和优化

技术特性：
- 基于LangGraph的状态机管理对话流程
- 支持复杂的多步骤任务处理
- 上下文感知的智能回复生成
- 可扩展的对话策略配置
- 异步消息处理支持
- 完整的错误处理和恢复机制

业务规则：
- 每个用户可以有多个独立的对话会话
- 对话上下文会在会话期间持续维护
- 支持任务相关的智能建议和提醒
- 对话内容需要适当的隐私保护
- 支持对话历史的导出和分析

异常处理：
- 对话参数验证失败时抛出ValidationException
- 会话不存在时抛出ResourceNotFoundException
- AI服务异常时抛出BusinessException
- 权限不足时抛出AuthorizationException
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass, field
from enum import Enum

# LangGraph相关导入（实际使用时需要安装）
try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.runnables import RunnableConfig
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # 模拟LangGraph类以便开发和测试
    LANGGRAPH_AVAILABLE = False
    print("Warning: LangGraph not available, using mock implementations")

from ..models.user import User
from ..models.task import Task, TaskStatus, PriorityLevel
from ..models.focus import FocusSession
from ..repositories import UserRepository, TaskRepository, FocusRepository
from .base import BaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    AuthorizationException,
    wrap_repository_error
)


class MessageType(Enum):
    """消息类型枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationStatus(Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ChatMode(Enum):
    """聊天模式枚举"""
    GENERAL = "general"          # 通用对话
    TASK_ASSISTANT = "task_assistant"  # 任务助手
    PRODUCTIVITY_COACH = "productivity_coach"  # 生产力教练
    FOCUS_GUIDE = "focus_guide"  # 专注指导


@dataclass
class ChatMessage:
    """聊天消息数据类"""
    id: str
    conversation_id: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_count: int = 0
    processing_time_ms: int = 0


@dataclass
class Conversation:
    """对话会话数据类"""
    id: str
    user_id: str
    title: str
    status: ConversationStatus
    chat_mode: ChatMode
    messages: List[ChatMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatState:
    """聊天状态类（用于LangGraph状态管理）"""
    """LangGraph状态定义，包含对话的所有状态信息"""
    messages: List[Any] = field(default_factory=list)  # 对话消息历史
    user_context: Dict[str, Any] = field(default_factory=dict)  # 用户上下文信息
    task_context: Dict[str, Any] = field(default_factory=dict)  # 任务相关上下文
    conversation_metadata: Dict[str, Any] = field(default_factory=dict)  # 对话元数据
    current_intent: Optional[str] = None  # 当前对话意图
    required_actions: List[str] = field(default_factory=list)  # 需要执行的动作
    processing_state: str = "idle"  # 处理状态


class ChatService(BaseService):
    """
    聊天服务类

    基于LangGraph框架提供智能对话服务，支持多轮对话、任务辅助、
    生产力指导等功能。服务采用状态机模式管理对话流程，确保
    对话的连贯性和上下文感知能力。

    Attributes:
        user_repo: 用户数据访问对象
        task_repo: 任务数据访问对象
        focus_repo: 专注数据访问对象
        conversations: 内存中的对话存储（生产环境应使用数据库）
        langgraph_app: LangGraph应用实例
    """

    def __init__(
        self,
        user_repo: UserRepository,
        task_repo: TaskRepository,
        focus_repo: FocusRepository
    ):
        """
        初始化聊天服务

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
        """
        super().__init__("ChatService")
        self.user_repo = user_repo
        self.task_repo = task_repo
        self.focus_repo = focus_repo

        # 内存存储（生产环境应使用数据库）
        self.conversations: Dict[str, Conversation] = {}
        self.messages: Dict[str, List[ChatMessage]] = {}

        # 初始化LangGraph应用
        self.langgraph_app = self._initialize_langgraph_app()

        # AI配置（从环境变量获取）
        self.ai_config = self._load_ai_config()

    # ==================== 对话会话管理 ====================

    def create_conversation(
        self,
        user_id: str,
        title: str,
        chat_mode: ChatMode = ChatMode.GENERAL,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建新的对话会话

        创建一个新的对话会话，并根据聊天模式初始化相应的上下文信息。
        支持多种聊天模式，每种模式有不同的对话策略和上下文需求。

        Args:
            user_id: 用户ID
            title: 对话标题
            chat_mode: 聊天模式，默认为通用对话
            initial_context: 初始上下文信息

        Returns:
            Dict[str, Any]: 创建的对话会话信息，包含：
                - conversation_id: 对话ID
                - title: 对话标题
                - status: 对话状态
                - chat_mode: 聊天模式
                - created_at: 创建时间
                - initial_message: 初始系统消息（如果有）

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 对话创建失败时
        """
        try:
            # 参数验证
            self._validate_conversation_creation_params(user_id, title, chat_mode)

            # 验证用户存在
            user = self._get_user_or_404(user_id)

            # 生成对话ID
            conversation_id = self._generate_conversation_id()

            # 创建对话实例
            conversation = Conversation(
                id=conversation_id,
                user_id=user_id,
                title=title,
                status=ConversationStatus.ACTIVE,
                chat_mode=chat_mode,
                context=initial_context or {},
                metadata={
                    "user_level": 1,  # 默认等级
                    "user_preferences": self._get_user_preferences(user_id),
                    "creation_mode": chat_mode.value
                }
            )

            # 根据聊天模式添加初始系统消息
            initial_message = self._create_initial_system_message(conversation)
            if initial_message:
                self.messages[conversation_id] = [initial_message]

            # 存储对话
            self.conversations[conversation_id] = conversation

            # 记录创建日志
            self._logger.info(
                f"创建新对话会话",
                extra={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "chat_mode": chat_mode.value,
                    "title": title
                }
            )

            return {
                "conversation_id": conversation_id,
                "title": title,
                "status": conversation.status.value,
                "chat_mode": chat_mode.value,
                "created_at": conversation.created_at.isoformat(),
                "initial_message": {
                    "content": initial_message.content,
                    "created_at": initial_message.created_at.isoformat()
                } if initial_message else None,
                "context": conversation.context,
                "capabilities": self._get_chat_mode_capabilities(chat_mode)
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                error_code="CHAT_CREATE_CONVERSATION_FAILED",
                message=f"创建对话会话失败: {str(e)}",
                details={
                    "user_id": user_id,
                    "title": title,
                    "chat_mode": chat_mode.value,
                    "error_type": type(e).__name__
                }
            )

    def get_conversation(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取对话会话信息

        获取指定对话会话的详细信息，包括对话历史、上下文信息等。
        验证用户权限确保只能访问自己的对话。

        Args:
            conversation_id: 对话ID
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 对话会话详细信息

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 对话不存在时
            AuthorizationException: 用户无权限访问时
        """
        try:
            # 参数验证
            self._validate_conversation_access_params(conversation_id, user_id)

            # 获取对话
            conversation = self._get_conversation_or_404(conversation_id)

            # 验证权限
            self._verify_conversation_access(conversation, user_id)

            # 获取消息历史
            messages = self.messages.get(conversation_id, [])

            # 计算对话统计
            conversation_stats = self._calculate_conversation_stats(conversation, messages)

            return {
                "conversation_info": {
                    "id": conversation.id,
                    "title": conversation.title,
                    "status": conversation.status.value,
                    "chat_mode": conversation.chat_mode.value,
                    "created_at": conversation.created_at.isoformat(),
                    "updated_at": conversation.updated_at.isoformat()
                },
                "messages": [
                    {
                        "id": msg.id,
                        "type": msg.message_type.value,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "token_count": msg.token_count,
                        "processing_time_ms": msg.processing_time_ms,
                        "metadata": msg.metadata
                    }
                    for msg in messages
                ],
                "context": conversation.context,
                "metadata": conversation.metadata,
                "statistics": conversation_stats
            }

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            raise BusinessException(
                error_code="CHAT_GET_CONVERSATION_FAILED",
                message=f"获取对话会话失败: {str(e)}",
                details={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )

    def list_user_conversations(
        self,
        user_id: str,
        status: Optional[ConversationStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取用户的对话列表

        获取指定用户的所有对话会话列表，支持按状态过滤和分页。

        Args:
            user_id: 用户ID
            status: 对话状态过滤（可选）
            limit: 返回数量限制，默认20
            offset: 偏移量，默认0

        Returns:
            Dict[str, Any]: 对话列表和分页信息

        Raises:
            ValidationException: 参数验证失败时
            BusinessException: 查询失败时
        """
        try:
            # 参数验证
            self._validate_list_conversations_params(user_id, limit, offset)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 过滤用户的对话
            user_conversations = [
                conv for conv in self.conversations.values()
                if conv.user_id == user_id
            ]

            # 按状态过滤
            if status:
                user_conversations = [
                    conv for conv in user_conversations
                    if conv.status == status
                ]

            # 按更新时间排序（最新的在前）
            user_conversations.sort(key=lambda x: x.updated_at, reverse=True)

            # 分页
            total_count = len(user_conversations)
            conversations_page = user_conversations[offset:offset + limit]

            # 构建返回数据
            conversation_list = []
            for conv in conversations_page:
                messages = self.messages.get(conv.id, [])
                last_message = messages[-1] if messages else None

                conversation_list.append({
                    "conversation_id": conv.id,
                    "title": conv.title,
                    "status": conv.status.value,
                    "chat_mode": conv.chat_mode.value,
                    "message_count": len(messages),
                    "last_message_preview": last_message.content[:100] if last_message else None,
                    "last_message_time": last_message.created_at.isoformat() if last_message else None,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                })

            return {
                "conversations": conversation_list,
                "pagination": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < total_count,
                    "has_prev": offset > 0
                },
                "filter_info": {
                    "status_filter": status.value if status else "all",
                    "filtered_count": len(user_conversations)
                }
            }

        except ValidationException:
            raise
        except Exception as e:
            raise BusinessException(
                error_code="CHAT_LIST_CONVERSATIONS_FAILED",
                message=f"获取对话列表失败: {str(e)}",
                details={
                    "user_id": user_id,
                    "status": status.value if status else None,
                    "limit": limit,
                    "offset": offset,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 消息处理 ====================

    async def send_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        stream: bool = False,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        发送消息并获取AI回复

        处理用户消息，通过LangGraph状态机生成AI回复，支持流式输出。
        根据对话模式采用不同的处理策略和上下文管理。

        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            content: 消息内容
            stream: 是否使用流式输出，默认False
            additional_context: 额外的上下文信息

        Returns:
            Union[Dict[str, Any], AsyncGenerator]: AI回复信息或流式数据生成器

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 对话不存在时
            AuthorizationException: 用户无权限访问时
            BusinessException: 消息处理失败时
        """
        try:
            # 参数验证
            self._validate_send_message_params(conversation_id, user_id, content)

            # 获取对话
            conversation = self._get_conversation_or_404(conversation_id)

            # 验证权限和状态
            self._verify_conversation_access(conversation, user_id)
            self._verify_conversation_active(conversation)

            # 创建用户消息
            user_message = self._create_message(
                conversation_id=conversation_id,
                message_type=MessageType.USER,
                content=content,
                metadata=additional_context or {}
            )

            # 添加到消息历史
            if conversation_id not in self.messages:
                self.messages[conversation_id] = []
            self.messages[conversation_id].append(user_message)

            # 更新对话时间
            conversation.updated_at = datetime.now(timezone.utc)

            # 更新对话上下文
            if additional_context:
                conversation.context.update(additional_context)

            # 获取用户和任务上下文
            enhanced_context = await self._build_enhanced_context(
                conversation, user_id, content
            )

            # 处理消息并生成回复
            if stream:
                return self._process_message_stream(
                    conversation, user_message, enhanced_context
                )
            else:
                return await self._process_message_sync(
                    conversation, user_message, enhanced_context
                )

        except (ValidationException, ResourceNotFoundException, AuthorizationException):
            raise
        except Exception as e:
            raise BusinessException(
                error_code="CHAT_SEND_MESSAGE_FAILED",
                message=f"消息处理失败: {str(e)}",
                details={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "content_length": len(content),
                    "error_type": type(e).__name__
                }
            )

    async def _process_message_sync(
        self,
        conversation: Conversation,
        user_message: ChatMessage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        同步处理消息

        Args:
            conversation: 对话实例
            user_message: 用户消息
            context: 增强上下文

        Returns:
            Dict[str, Any]: 完整的回复信息
        """
        start_time = datetime.now(timezone.utc)

        try:
            # 使用LangGraph处理消息
            if LANGGRAPH_AVAILABLE and self.langgraph_app:
                # 构建状态
                state = ChatState(
                    messages=self._convert_to_langchain_messages(
                        self.messages[conversation.id]
                    ),
                    user_context=context.get("user_context", {}),
                    task_context=context.get("task_context", {}),
                    conversation_metadata=conversation.metadata,
                    current_intent=self._analyze_intent(user_message.content),
                    processing_state="analyzing"
                )

                # 执行LangGraph流程
                result = await self.langgraph_app.ainvoke(state)

                # 提取AI回复
                ai_response = result["messages"][-1].content if result["messages"] else "抱歉，我无法处理您的请求。"

                # 更新处理状态
                processing_state = result.get("processing_state", "completed")
                required_actions = result.get("required_actions", [])
            else:
                # 模拟AI回复（用于开发测试）
                ai_response = self._generate_mock_response(
                    conversation.chat_mode, user_message.content, context
                )
                processing_state = "completed"
                required_actions = []

            # 计算处理时间
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # 创建AI回复消息
            ai_message = self._create_message(
                conversation_id=conversation.id,
                message_type=MessageType.ASSISTANT,
                content=ai_response,
                metadata={
                    "processing_state": processing_state,
                    "required_actions": required_actions,
                    "intent": context.get("intent", "general"),
                    "context_used": list(context.keys())
                },
                processing_time_ms=int(processing_time)
            )

            # 添加到消息历史
            self.messages[conversation.id].append(ai_message)

            # 更新对话时间
            conversation.updated_at = datetime.now(timezone.utc)

            # 执行后处理动作
            if required_actions:
                await self._execute_required_actions(
                    conversation, required_actions, context
                )

            return {
                "message_id": ai_message.id,
                "content": ai_response,
                "conversation_id": conversation.id,
                "created_at": ai_message.created_at.isoformat(),
                "processing_time_ms": int(processing_time),
                "metadata": ai_message.metadata,
                "conversation_context": {
                    "message_count": len(self.messages[conversation.id]),
                    "last_updated": conversation.updated_at.isoformat()
                }
            }

        except Exception as e:
            # 创建错误回复消息
            error_response = "抱歉，处理您的消息时出现了问题。请稍后再试。"
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            error_message = self._create_message(
                conversation_id=conversation.id,
                message_type=MessageType.ASSISTANT,
                content=error_response,
                metadata={
                    "error": True,
                    "error_type": type(e).__name__,
                    "processing_state": "error"
                },
                processing_time_ms=int(processing_time)
            )

            self.messages[conversation.id].append(error_message)

            # 记录错误日志
            self._logger.error(
                f"消息处理异常: {str(e)}",
                extra={
                    "conversation_id": conversation.id,
                    "user_id": conversation.user_id,
                    "error_type": type(e).__name__,
                    "processing_time_ms": int(processing_time)
                }
            )

            return {
                "message_id": error_message.id,
                "content": error_response,
                "conversation_id": conversation.id,
                "created_at": error_message.created_at.isoformat(),
                "processing_time_ms": int(processing_time),
                "metadata": error_message.metadata,
                "error_info": {
                    "error_code": "CHAT_PROCESSING_ERROR",
                    "error_message": str(e)
                }
            }

    async def _process_message_stream(
        self,
        conversation: Conversation,
        user_message: ChatMessage,
        context: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式处理消息

        Args:
            conversation: 对话实例
            user_message: 用户消息
            context: 增强上下文

        Yields:
            Dict[str, Any]: 流式回复数据块
        """
        start_time = datetime.now(timezone.utc)
        message_id = self._generate_message_id()
        accumulated_content = ""

        try:
            # 模拟流式输出（实际实现需要与LangGraph的流式API集成）
            mock_chunks = [
                "我正在分析您的请求...",
                "基于您的问题，我建议...",
                "让我为您提供详细的回答。",
                "首先，考虑到您当前的任务状态...",
                "我建议您可以考虑以下几个选项：",
                "1. 优先处理高优先级任务",
                "2. 使用番茄工作法提高专注度",
                "3. 设置合理的休息间隔",
                "希望这些建议对您有帮助！"
            ]

            for i, chunk in enumerate(mock_chunks):
                await asyncio.sleep(0.1)  # 模拟网络延迟

                accumulated_content += chunk

                yield {
                    "message_id": message_id,
                    "content": accumulated_content,
                    "chunk": chunk,
                    "chunk_index": i,
                    "conversation_id": conversation.id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_complete": i == len(mock_chunks) - 1,
                    "metadata": {
                        "streaming": True,
                        "chunk_count": i + 1,
                        "total_chunks": len(mock_chunks)
                    }
                }

            # 创建完整的AI回复消息
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            ai_message = self._create_message(
                conversation_id=conversation.id,
                message_type=MessageType.ASSISTANT,
                content=accumulated_content,
                metadata={
                    "streaming": True,
                    "processing_state": "completed",
                    "intent": context.get("intent", "general")
                },
                processing_time_ms=int(processing_time)
            )

            self.messages[conversation.id].append(ai_message)
            conversation.updated_at = datetime.now(timezone.utc)

        except Exception as e:
            # 流式错误处理
            error_chunk = f"\n\n抱歉，处理过程中出现了错误: {str(e)}"
            accumulated_content += error_chunk

            yield {
                "message_id": message_id,
                "content": accumulated_content,
                "chunk": error_chunk,
                "chunk_index": -1,
                "conversation_id": conversation.id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_complete": True,
                "error": True,
                "error_info": {
                    "error_code": "CHAT_STREAM_ERROR",
                    "error_message": str(e)
                }
            }

    # ==================== 智能功能 ====================

    async def get_task_suggestions(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        获取智能任务建议

        基于用户的历史数据、当前任务状态和专注情况，生成个性化的任务建议。
        支持在对话上下文中提供建议。

        Args:
            user_id: 用户ID
            conversation_id: 对话ID（可选）
            context: 额外上下文信息（可选）

        Returns:
            Dict[str, Any]: 任务建议信息

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)

            # 验证用户存在
            user = self._get_user_or_404(user_id)

            # 如果提供了对话ID，验证对话存在
            conversation = None
            if conversation_id:
                conversation = self._get_conversation_or_404(conversation_id)
                self._verify_conversation_access(conversation, user_id)

            # 获取用户数据
            user_tasks = self._get_user_tasks(user_id)
            user_stats = self._get_user_statistics(user_id)
            recent_focus_sessions = self._get_recent_focus_sessions(user_id, days=7)

            # 生成任务建议
            suggestions = await self._generate_task_suggestions(
                user, user_tasks, user_stats, recent_focus_sessions, context
            )

            # 构建返回数据
            result = {
                "suggestions": suggestions,
                "context_info": {
                    "user_level": 1,  # 默认等级
                    "active_tasks": len([t for t in user_tasks if t.status == TaskStatus.IN_PROGRESS]),
                    "completed_today": len([t for t in user_tasks if self._is_completed_today(t)]),
                    "focus_hours_today": sum([s.duration_minutes for s in recent_focus_sessions if self._is_today(s.ended_at)]) / 60
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

            # 如果在对话上下文中，添加建议到对话
            if conversation:
                suggestion_message = self._format_suggestions_as_message(suggestions)
                await self._add_context_message_to_conversation(
                    conversation, suggestion_message
                )
                result["conversation_context"] = {
                    "conversation_id": conversation.id,
                    "message_added": True
                }

            return result

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                error_code="CHAT_TASK_SUGGESTIONS_FAILED",
                message=f"获取任务建议失败: {str(e)}",
                details={
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "error_type": type(e).__name__
                }
            )

    async def analyze_productivity_patterns(
        self,
        user_id: str,
        days: int = 30,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析用户生产力模式

        深度分析用户的生产力模式，包括最佳工作时间、任务完成模式、
        专注习惯等，并提供改进建议。

        Args:
            user_id: 用户ID
            days: 分析天数，默认30天
            conversation_id: 对话ID（可选）

        Returns:
            Dict[str, Any]: 生产力模式分析结果

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            user = self._get_user_or_404(user_id)

            # 获取分析数据
            analysis_data = await self._collect_productivity_data(user_id, days)

            # 执行模式分析
            patterns = self._analyze_productivity_patterns(analysis_data)

            # 生成洞察和建议
            insights = self._generate_productivity_insights(patterns)
            recommendations = self._generate_productivity_recommendations(patterns, 1)  # 默认等级

            # 构建结果
            result = {
                "analysis_period": {
                    "start_date": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
                    "end_date": datetime.now(timezone.utc).isoformat(),
                    "days_analyzed": days
                },
                "patterns": patterns,
                "insights": insights,
                "recommendations": recommendations,
                "data_summary": {
                    "tasks_analyzed": len(analysis_data.get("tasks", [])),
                    "focus_sessions_analyzed": len(analysis_data.get("focus_sessions", [])),
                    "data_completeness": self._calculate_data_completeness(analysis_data)
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

            # 如果在对话上下文中，添加分析摘要到对话
            if conversation_id:
                conversation = self._get_conversation_or_404(conversation_id)
                self._verify_conversation_access(conversation, user_id)

                analysis_summary = self._format_analysis_summary(insights, recommendations)
                await self._add_context_message_to_conversation(
                    conversation, analysis_summary
                )
                result["conversation_context"] = {
                    "conversation_id": conversation_id,
                    "summary_added": True
                }

            return result

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                error_code="CHAT_PRODUCTIVITY_ANALYSIS_FAILED",
                message=f"生产力模式分析失败: {str(e)}",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    # ==================== LangGraph集成 ====================

    def _initialize_langgraph_app(self):
        """
        初始化LangGraph应用

        构建基于状态机的对话处理流程，包括消息分析、上下文管理、
        意图识别、回复生成等节点。

        Returns:
            LangGraph应用实例或mock应用实例
        """
        if not LANGGRAPH_AVAILABLE:
            self._logger.warning("LangGraph不可用，使用模拟实现")
            return self._create_mock_langgraph_app()

        try:
            # 构建状态图
            workflow = StateGraph(ChatState)

            # 添加节点
            workflow.add_node("analyze_intent", self._analyze_intent_node)
            workflow.add_node("gather_context", self._gather_context_node)
            workflow.add_node("generate_response", self._generate_response_node)
            workflow.add_node("post_process", self._post_process_node)

            # 设置入口点
            workflow.set_entry_point("analyze_intent")

            # 添加边
            workflow.add_edge("analyze_intent", "gather_context")
            workflow.add_edge("gather_context", "generate_response")
            workflow.add_edge("generate_response", "post_process")
            workflow.add_edge("post_process", END)

            # 编译应用
            app = workflow.compile()

            self._logger.info("LangGraph应用初始化成功")
            return app

        except Exception as e:
            self._logger.error(f"LangGraph应用初始化失败: {str(e)}")
            return self._create_mock_langgraph_app()

    def _create_mock_langgraph_app(self):
        """
        创建模拟LangGraph应用

        当LangGraph不可用时，创建一个mock应用来模拟基本功能。
        确保服务可以正常运行和测试。

        Returns:
            Mock应用实例
        """
        class MockLangGraphApp:
            """模拟LangGraph应用类"""

            async def ainvoke(self, state: ChatState, config: dict = None) -> ChatState:
                """模拟异步调用"""
                # 模拟处理流程
                if not state.messages:
                    state.messages = []

                # 模拟意图分析
                if not state.current_intent and state.messages:
                    last_message = state.messages[-1]
                    if hasattr(last_message, 'content'):
                        state.current_intent = self._analyze_intent_mock(last_message.content)

                # 模拟生成回复
                response_content = self._generate_response_mock(state)

                # 创建模拟AI回复消息
                mock_ai_message = type('MockMessage', (), {
                    'content': response_content
                })()

                if LANGGRAPH_AVAILABLE:
                    from langchain_core.messages import AIMessage
                    mock_ai_message = AIMessage(content=response_content)

                state.messages.append(mock_ai_message)
                state.processing_state = "completed"
                state.required_actions = []

                return state

            def _analyze_intent_mock(self, content: str) -> str:
                """模拟意图分析"""
                content_lower = content.lower()
                if any(word in content_lower for word in ["任务", "task", "todo"]):
                    return "task_help"
                elif any(word in content_lower for word in ["效率", "生产力", "productivity"]):
                    return "productivity_advice"
                elif any(word in content_lower for word in ["专注", "focus", "集中"]):
                    return "focus_help"
                else:
                    return "general"

            def _generate_response_mock(self, state: ChatState) -> str:
                """模拟回复生成"""
                intent = state.current_intent or "general"

                responses = {
                    "task_help": "我来帮您分析任务情况。建议您优先处理重要且紧急的任务，可以使用四象限法则来分类。",
                    "productivity_advice": "关于提升生产力，我建议您：1）使用番茄工作法 2）设定明确的目标 3）减少干扰源。",
                    "focus_help": "关于提高专注力，推荐您尝试：1）番茄工作法（25分钟专注+5分钟休息）2）创造无干扰环境 3）正念冥想练习。",
                    "general": "我理解您的需求。让我为您提供一些个性化的建议来帮助您提高效率。"
                }

                return responses.get(intent, responses["general"])

        return MockLangGraphApp()

    async def _analyze_intent_node(self, state: ChatState) -> ChatState:
        """分析用户意图节点"""
        if not state.messages:
            state.current_intent = "unknown"
            return state

        last_message = state.messages[-1]
        if isinstance(last_message, HumanMessage):
            state.current_intent = self._analyze_intent(last_message.content)
        else:
            state.current_intent = "unknown"

        state.processing_state = "intent_analyzed"
        return state

    async def _gather_context_node(self, state: ChatState) -> ChatState:
        """收集上下文节点"""
        # 这里可以根据意图收集相关的上下文信息
        state.processing_state = "context_gathered"
        return state

    async def _generate_response_node(self, state: ChatState) -> ChatState:
        """生成回复节点"""
        # 基于状态生成AI回复
        response_content = self._generate_response_content(state)

        ai_message = AIMessage(content=response_content)
        state.messages = add_messages(state.messages, [ai_message])

        state.processing_state = "response_generated"
        return state

    async def _post_process_node(self, state: ChatState) -> ChatState:
        """后处理节点"""
        # 执行后处理逻辑，如提取需要执行的动作
        state.required_actions = self._extract_required_actions(state)
        state.processing_state = "completed"
        return state

    # ==================== 私有辅助方法 ====================

    def _validate_conversation_creation_params(
        self, user_id: str, title: str, chat_mode: ChatMode
    ) -> None:
        """验证对话创建参数"""
        if not user_id or not isinstance(user_id, str):
            raise ValidationException(
                "用户ID不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_USER_ID", "user_id": user_id}
            )

        if not title or not isinstance(title, str):
            raise ValidationException(
                "对话标题不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_TITLE", "title": title}
            )

        if len(title) > 100:
            raise ValidationException(
                "对话标题长度不能超过100个字符",
                field="unknown",
                details={"error_code": "CHAT_TITLE_TOO_LONG", "title": title, "length": len(title)}
            )

        if not isinstance(chat_mode, ChatMode):
            raise ValidationException(
                f"聊天模式必须是ChatMode枚举值",
                field="chat_mode",
                value=chat_mode,
                details={"error_code": "CHAT_INVALID_CHAT_MODE"}
            )

    def _validate_conversation_access_params(
        self, conversation_id: str, user_id: str
    ) -> None:
        """验证对话访问参数"""
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValidationException(
                "对话ID不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_CONVERSATION_ID", "conversation_id": conversation_id}
            )

        if not user_id or not isinstance(user_id, str):
            raise ValidationException(
                "用户ID不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_USER_ID", "user_id": user_id}
            )

    def _validate_list_conversations_params(
        self, user_id: str, limit: int, offset: int
    ) -> None:
        """验证获取对话列表参数"""
        if not user_id or not isinstance(user_id, str):
            raise ValidationException(
                "用户ID不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_USER_ID", "user_id": user_id}
            )

        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            raise ValidationException(
                "limit必须是1-100之间的正整数",
                field="unknown",
                details={"error_code": "CHAT_INVALID_LIMIT", "limit": limit}
            )

        if not isinstance(offset, int) or offset < 0:
            raise ValidationException(
                "offset必须是非负整数",
                field="unknown",
                details={"error_code": "CHAT_INVALID_OFFSET", "offset": offset}
            )

    def _validate_send_message_params(
        self, conversation_id: str, user_id: str, content: str
    ) -> None:
        """验证发送消息参数"""
        if not conversation_id or not isinstance(conversation_id, str):
            raise ValidationException(
                "对话ID不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_CONVERSATION_ID", "conversation_id": conversation_id}
            )

        if not user_id or not isinstance(user_id, str):
            raise ValidationException(
                "用户ID不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_USER_ID", "user_id": user_id}
            )

        if not content or not isinstance(content, str):
            raise ValidationException(
                "消息内容不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_CONTENT", "content_length": len(content) if content else 0}
            )

        if len(content) > 10000:
            raise ValidationException(
                "消息内容长度不能超过10000个字符",
                field="unknown",
                details={"error_code": "CHAT_CONTENT_TOO_LONG", "content_length": len(content)}
            )

    def _validate_user_id(self, user_id: str) -> None:
        """验证用户ID"""
        if not user_id or not isinstance(user_id, str):
            raise ValidationException(
                "用户ID不能为空且必须是字符串类型",
                field="unknown",
                details={"error_code": "CHAT_INVALID_USER_ID", "user_id": user_id}
            )

    def _validate_days(self, days: int) -> None:
        """验证天数参数"""
        if not isinstance(days, int) or days <= 0 or days > 365:
            raise ValidationException(
                "天数必须是1-365之间的正整数",
                field="unknown",
                details={"error_code": "CHAT_INVALID_DAYS", "days": days}
            )

    def _get_user_or_404(self, user_id: str) -> User:
        """获取用户或抛出异常"""
        try:
            user = self.user_repo.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundException(
                    "User",
                    resource_id=user_id,
                    details={"error_code": "CHAT_USER_NOT_FOUND"}
                )
            return user
        except Exception as e:
            if isinstance(e, ResourceNotFoundException):
                raise
            raise wrap_repository_error(e, "get_user_by_id")

    def _get_conversation_or_404(self, conversation_id: str) -> Conversation:
        """获取对话或抛出异常"""
        if conversation_id not in self.conversations:
            raise ResourceNotFoundException(
                f"对话不存在: {conversation_id}",
                error_code="CHAT_CONVERSATION_NOT_FOUND",
                details={"conversation_id": conversation_id}
            )
        return self.conversations[conversation_id]

    def _verify_conversation_access(self, conversation: Conversation, user_id: str) -> None:
        """验证对话访问权限"""
        if conversation.user_id != user_id:
            raise AuthorizationException(
                "conversation_access",
                user_id=user_id,
                resource_id=conversation.id,
                details={"error_code": "CHAT_ACCESS_DENIED", "conversation_owner": conversation.user_id}
            )

    def _verify_conversation_active(self, conversation: Conversation) -> None:
        """验证对话是否活跃"""
        if conversation.status != ConversationStatus.ACTIVE:
            raise BusinessException(
                error_code="CHAT_CONVERSATION_NOT_ACTIVE",
                message=f"对话状态不允许发送消息: {conversation.status.value}",
                details={
                    "conversation_id": conversation.id,
                    "current_status": conversation.status.value
                }
            )

    def _generate_conversation_id(self) -> str:
        """生成对话ID"""
        import uuid
        return f"conv_{uuid.uuid4().hex[:12]}"

    def _generate_message_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"msg_{uuid.uuid4().hex[:12]}"

    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好设置"""
        # 实际实现需要从数据库获取
        return {
            "language": "zh-CN",
            "response_style": "friendly",
            "detail_level": "medium"
        }

    def _get_chat_mode_capabilities(self, chat_mode: ChatMode) -> List[str]:
        """获取聊天模式的能力列表"""
        capabilities = {
            ChatMode.GENERAL: ["通用对话", "基础问答", "闲聊"],
            ChatMode.TASK_ASSISTANT: ["任务管理", "任务建议", "进度跟踪", "任务分解"],
            ChatMode.PRODUCTIVITY_COACH: ["生产力分析", "习惯建议", "效率优化", "目标制定"],
            ChatMode.FOCUS_GUIDE: ["专注指导", "番茄工作法", "专注技巧", "干扰管理"]
        }
        return capabilities.get(chat_mode, [])

    def _create_initial_system_message(self, conversation: Conversation) -> Optional[ChatMessage]:
        """创建初始系统消息"""
        system_prompts = {
            ChatMode.GENERAL: "您好！我是您的AI助手，有什么可以帮助您的吗？",
            ChatMode.TASK_ASSISTANT: "您好！我是您的任务助手，可以帮您管理任务、提供建议。让我看看您当前的任务情况。",
            ChatMode.PRODUCTIVITY_COACH: "您好！我是您的生产力教练，可以帮助您分析工作模式、提升效率。让我们一起改善您的工作方式！",
            ChatMode.FOCUS_GUIDE: "您好！我是您的专注指导，可以帮助您提高专注力、管理干扰。准备好开始专注工作了吗？"
        }

        prompt = system_prompts.get(conversation.chat_mode)
        if not prompt:
            return None

        return self._create_message(
            conversation_id=conversation.id,
            message_type=MessageType.SYSTEM,
            content=prompt,
            metadata={"initial_message": True, "chat_mode": conversation.chat_mode.value}
        )

    def _create_message(
        self,
        conversation_id: str,
        message_type: MessageType,
        content: str,
        metadata: Dict[str, Any],
        processing_time_ms: int = 0
    ) -> ChatMessage:
        """创建消息对象"""
        return ChatMessage(
            id=self._generate_message_id(),
            conversation_id=conversation_id,
            message_type=message_type,
            content=content,
            metadata=metadata,
            processing_time_ms=processing_time_ms,
            token_count=len(content) // 4  # 简单估算token数量
        )

    def _calculate_conversation_stats(
        self, conversation: Conversation, messages: List[ChatMessage]
    ) -> Dict[str, Any]:
        """计算对话统计信息"""
        if not messages:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "total_tokens": 0,
                "average_response_time_ms": 0,
                "conversation_duration_minutes": 0
            }

        user_messages = [msg for msg in messages if msg.message_type == MessageType.USER]
        assistant_messages = [msg for msg in messages if msg.message_type == MessageType.ASSISTANT]

        total_tokens = sum(msg.token_count for msg in messages)
        avg_response_time = (
            sum(msg.processing_time_ms for msg in assistant_messages) / len(assistant_messages)
            if assistant_messages else 0
        )

        duration_minutes = (
            (messages[-1].created_at - messages[0].created_at).total_seconds() / 60
            if len(messages) > 1 else 0
        )

        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_tokens": total_tokens,
            "average_response_time_ms": round(avg_response_time, 2),
            "conversation_duration_minutes": round(duration_minutes, 2)
        }

    async def _build_enhanced_context(
        self, conversation: Conversation, user_id: str, user_content: str
    ) -> Dict[str, Any]:
        """构建增强上下文"""
        try:
            # 获取用户相关数据
            user = self._get_user_or_404(user_id)
            user_tasks = self._get_user_tasks(user_id)
            recent_focus = self._get_recent_focus_sessions(user_id, days=7)

            # 分析用户意图
            intent = self._analyze_intent(user_content)

            # 构建上下文
            context = {
                "user_context": {
                    "id": user.id,
                    "level": 1,  # 默认等级
                    "current_streak": 0,  # 默认连续记录
                    "preferences": self._get_user_preferences(user_id)
                },
                "task_context": {
                    "active_tasks": len([t for t in user_tasks if t.status == TaskStatus.IN_PROGRESS]),
                    "completed_today": len([t for t in user_tasks if self._is_completed_today(t)]),
                    "overdue_tasks": len([t for t in user_tasks if self._is_overdue(t)])
                },
                "focus_context": {
                    "focus_minutes_today": sum([
                        s.duration_minutes for s in recent_focus
                        if self._is_today(s.ended_at)
                    ]),
                    "sessions_this_week": len(recent_focus),
                    "average_session_length": (
                        sum(s.duration_minutes for s in recent_focus) / len(recent_focus)
                        if recent_focus else 0
                    )
                },
                "conversation_context": {
                    "chat_mode": conversation.chat_mode.value,
                    "message_count": len(self.messages.get(conversation.id, [])),
                    "previous_topics": self._extract_previous_topics(conversation.id)
                },
                "intent": intent,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return context

        except Exception as e:
            self._logger.warning(f"构建增强上下文失败: {str(e)}")
            return {
                "user_context": {"id": user_id},
                "intent": self._analyze_intent(user_content),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _analyze_intent(self, content: str) -> str:
        """分析用户意图"""
        content_lower = content.lower()

        # 简单的意图识别逻辑
        intent_patterns = {
            "task_help": ["任务", "待办", "todo", "任务管理", "task"],
            "productivity_advice": ["效率", "生产力", "如何提高", "怎么提升", "效率建议"],
            "focus_help": ["专注", "集中注意力", "分心", "干扰", "专注力"],
            "time_management": ["时间管理", "安排", "计划", "时间分配"],
            "goal_setting": ["目标", "计划", "目标设定", "制定目标"],
            "habit_development": ["习惯", "养成", "坚持", "习惯培养"],
            "general_question": ["什么", "为什么", "如何", "怎么", "?", "？"],
            "greeting": ["你好", "hello", "hi", "嗨", "您好"],
            "thanks": ["谢谢", "感谢", "thank", "谢了"]
        }

        for intent, patterns in intent_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                return intent

        return "general"

    def _convert_to_langchain_messages(self, messages: List[ChatMessage]) -> List[Any]:
        """转换为LangChain消息格式"""
        if not LANGGRAPH_AVAILABLE:
            return []

        langchain_messages = []
        for msg in messages:
            if msg.message_type == MessageType.USER:
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.message_type == MessageType.ASSISTANT:
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.message_type == MessageType.SYSTEM:
                langchain_messages.append(SystemMessage(content=msg.content))

        return langchain_messages

    def _generate_mock_response(
        self, chat_mode: ChatMode, user_content: str, context: Dict[str, Any]
    ) -> str:
        """生成模拟AI回复（用于开发测试）"""
        intent = self._analyze_intent(user_content)

        responses = {
            ChatMode.GENERAL: {
                "general_question": "这是一个很好的问题。让我为您详细解答...",
                "greeting": "您好！很高兴为您服务。请问有什么可以帮助您的吗？",
                "thanks": "不客气！如果您还有其他问题，随时可以问我。",
                "general": "我理解您的问题。基于当前的信息，我建议..."
            },
            ChatMode.TASK_ASSISTANT: {
                "task_help": "我来帮您分析任务情况。让我查看您当前的任务列表...",
                "general": "关于任务管理，我建议您可以尝试以下方法..."
            },
            ChatMode.PRODUCTIVITY_COACH: {
                "productivity_advice": "关于提升生产力，我建议您从以下几个方面入手...",
                "general": "作为您的生产力教练，我建议..."
            },
            ChatMode.FOCUS_GUIDE: {
                "focus_help": "关于提高专注力，我推荐您尝试番茄工作法...",
                "general": "专注力训练需要循序渐进，让我们从基础开始..."
            }
        }

        mode_responses = responses.get(chat_mode, {})
        return mode_responses.get(intent, "我理解您的需求，让我为您提供一些建议...")

    def _generate_response_content(self, state: ChatState) -> str:
        """基于状态生成回复内容"""
        intent = state.current_intent or "general"
        chat_mode = state.conversation_metadata.get("chat_mode", "general")

        # 这里可以集成更复杂的回复生成逻辑
        if intent == "task_help":
            return "我来帮您分析任务情况。根据您当前的状态，我建议您优先处理重要且紧急的任务。"
        elif intent == "productivity_advice":
            return "关于提升生产力，建议您：1）使用时间块管理法 2）设置明确的工作边界 3）定期休息恢复精力。"
        else:
            return "我理解您的需求。让我为您提供一些个性化的建议。"

    def _extract_required_actions(self, state: ChatState) -> List[str]:
        """提取需要执行的动作"""
        actions = []

        # 基于意图确定需要的动作
        if state.current_intent == "task_help":
            actions.append("analyze_tasks")
            actions.append("provide_task_suggestions")
        elif state.current_intent == "productivity_advice":
            actions.append("analyze_productivity")
            actions.append("generate_recommendations")

        return actions

    async def _execute_required_actions(
        self, conversation: Conversation, actions: List[str], context: Dict[str, Any]
    ) -> None:
        """执行需要的动作"""
        for action in actions:
            try:
                if action == "analyze_tasks":
                    await self._analyze_and_suggest_tasks(conversation, context)
                elif action == "provide_task_suggestions":
                    await self._provide_task_suggestions(conversation, context)
                elif action == "analyze_productivity":
                    await self._analyze_productivity(conversation, context)
                elif action == "generate_recommendations":
                    await self._generate_recommendations(conversation, context)
            except Exception as e:
                self._logger.error(f"执行动作失败 {action}: {str(e)}")

    # 占位符方法（实际实现需要根据具体需求）
    def _get_user_tasks(self, user_id: str) -> List[Task]:
        """获取用户任务列表"""
        # 实际实现需要从Repository获取
        return []

    def _get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计数据"""
        # 实际实现需要从StatisticsService获取
        return {}

    def _get_recent_focus_sessions(self, user_id: str, days: int) -> List[FocusSession]:
        """获取最近的专注会话"""
        # 实际实现需要从Repository获取
        return []

    def _is_completed_today(self, task: Task) -> bool:
        """检查任务是否今天完成"""
        return False  # 占位符实现

    def _is_today(self, timestamp: datetime) -> bool:
        """检查时间戳是否为今天"""
        return False  # 占位符实现

    def _is_overdue(self, task: Task) -> bool:
        """检查任务是否过期"""
        return False  # 占位符实现

    async def _generate_task_suggestions(
        self, user: User, tasks: List[Task], stats: Dict, focus_sessions: List, context: Optional[Dict]
    ) -> List[Dict]:
        """生成任务建议"""
        return [
            {
                "type": "prioritization",
                "title": "任务优先级建议",
                "description": "建议优先处理高优先级且即将到期的任务",
                "action_items": ["查看任务列表", "按优先级排序", "设定截止时间"]
            }
        ]

    async def _collect_productivity_data(self, user_id: str, days: int) -> Dict[str, Any]:
        """收集生产力数据"""
        return {
            "tasks": [],
            "focus_sessions": [],
            "user_activity": []
        }

    def _analyze_productivity_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析生产力模式"""
        return {
            "peak_hours": [9, 10, 14, 15],
            "productivity_trend": "stable",
            "focus_patterns": "consistent"
        }

    def _generate_productivity_insights(self, patterns: Dict[str, Any]) -> List[str]:
        """生成生产力洞察"""
        return [
            "您的工作效率在上午9-11点达到峰值",
            "保持规律的工作时间有助于提高生产力"
        ]

    def _generate_productivity_recommendations(
        self, patterns: Dict[str, Any], user_level: int
    ) -> List[Dict]:
        """生成生产力建议"""
        return [
            {
                "category": "time_management",
                "title": "优化工作时间分配",
                "description": "建议在高效时段处理重要任务",
                "priority": "high"
            }
        ]

    def _calculate_data_completeness(self, data: Dict[str, Any]) -> float:
        """计算数据完整性"""
        total_fields = 3
        available_fields = sum(1 for key in ["tasks", "focus_sessions", "user_activity"] if data.get(key))
        return (available_fields / total_fields) * 100

    def _format_suggestions_as_message(self, suggestions: List[Dict]) -> str:
        """将建议格式化为消息"""
        if not suggestions:
            return "暂时没有特别的建议，继续保持良好的工作习惯！"

        message = "基于您的情况，我为您生成以下建议：\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            message += f"{i}. {suggestion['title']}\n"
            message += f"   {suggestion['description']}\n\n"

        return message

    def _format_analysis_summary(self, insights: List[str], recommendations: List[Dict]) -> str:
        """格式化分析摘要"""
        summary = "## 生产力分析摘要\n\n### 主要发现：\n"
        for insight in insights:
            summary += f"- {insight}\n"

        summary += "\n### 改进建议：\n"
        for rec in recommendations[:3]:  # 只显示前3个建议
            summary += f"- {rec['title']}: {rec['description']}\n"

        return summary

    async def _add_context_message_to_conversation(
        self, conversation: Conversation, content: str
    ) -> None:
        """添加上下文消息到对话"""
        context_message = self._create_message(
            conversation_id=conversation.id,
            message_type=MessageType.SYSTEM,
            content=content,
            metadata={"auto_generated": True, "context_update": True}
        )

        if conversation.id not in self.messages:
            self.messages[conversation.id] = []
        self.messages[conversation.id].append(context_message)
        conversation.updated_at = datetime.now(timezone.utc)

    def _extract_previous_topics(self, conversation_id: str) -> List[str]:
        """提取之前的对话主题"""
        messages = self.messages.get(conversation_id, [])
        topics = []

        # 简单的主题提取逻辑
        for msg in messages[-5:]:  # 只看最近5条消息
            if msg.message_type == MessageType.USER:
                intent = self._analyze_intent(msg.content)
                if intent != "general" and intent not in topics:
                    topics.append(intent)

        return topics

    def _load_ai_config(self) -> Dict[str, Any]:
        """加载AI配置"""
        return {
            "model": os.getenv("AI_MODEL", "gpt-3.5-turbo"),
            "api_key": os.getenv("AI_API_KEY", ""),
            "base_url": os.getenv("AI_BASE_URL", ""),
            "temperature": float(os.getenv("AI_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("AI_MAX_TOKENS", "1000"))
        }

    # 占位符动作方法
    async def _analyze_and_suggest_tasks(self, conversation: Conversation, context: Dict) -> None:
        """分析并建议任务"""
        pass

    async def _provide_task_suggestions(self, conversation: Conversation, context: Dict) -> None:
        """提供任务建议"""
        pass

    async def _analyze_productivity(self, conversation: Conversation, context: Dict) -> None:
        """分析生产力"""
        pass

    async def _generate_recommendations(self, conversation: Conversation, context: Dict) -> None:
        """生成建议"""
        pass