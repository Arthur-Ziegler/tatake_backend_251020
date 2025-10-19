"""
对话管理模块

该模块提供对话会话的数据模型和管理功能，采用面向对象设计。
支持多种聊天模式、状态管理和消息历史。

核心组件：
- Conversation: 对话会话数据模型
- Message: 消息数据模型
- ConversationManager: 对话管理器
- ConversationStatus: 对话状态枚举
- ChatMode: 聊天模式枚举

设计原则：
- 数据类设计：使用dataclass定义数据模型
- 状态机模式：对话状态转换管理
- 策略模式：不同聊天模式的处理策略
- 单一职责：每个类专注于特定功能
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class ConversationStatus(Enum):
    """对话状态枚举"""
    ACTIVE = "active"        # 活跃状态
    PAUSED = "paused"        # 暂停状态
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"    # 已归档


class ChatMode(Enum):
    """聊天模式枚举"""
    GENERAL = "general"                    # 通用对话
    TASK_ASSISTANT = "task_assistant"      # 任务助手
    PRODUCTIVITY_COACH = "productivity_coach"  # 生产力教练
    FOCUS_GUIDE = "focus_guide"            # 专注指导


class MessageType(Enum):
    """消息类型枚举"""
    USER = "user"        # 用户消息
    ASSISTANT = "assistant"  # AI回复
    SYSTEM = "system"      # 系统消息
    TOOL = "tool"        # 工具调用消息


class MessagePriority(Enum):
    """消息优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Message:
    """
    消息数据类

    表示对话中的单条消息，包含内容、类型、元数据等信息。
    支持消息优先级、处理状态、关联数据等高级功能。

    Attributes:
        id: 消息唯一标识符
        conversation_id: 所属对话ID
        message_type: 消息类型
        content: 消息内容
        metadata: 消息元数据
        created_at: 创建时间
        updated_at: 更新时间
        token_count: Token数量估算
        processing_time_ms: 处理耗时（毫秒）
        priority: 消息优先级
        is_deleted: 是否已删除
        parent_id: 父消息ID（用于消息回复关系）
        related_data: 关联的业务数据
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    message_type: MessageType = MessageType.USER
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_count: int = 0
    processing_time_ms: int = 0
    priority: MessagePriority = MessagePriority.NORMAL
    is_deleted: bool = False
    parent_id: Optional[str] = None
    related_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())

        # 估算Token数量（简单实现：按字符数/4估算）
        if self.content:
            self.token_count = max(1, len(self.content) // 4)

    def mark_as_deleted(self) -> None:
        """标记消息为已删除"""
        self.is_deleted = True
        self.updated_at = datetime.now(timezone.utc)

    def update_content(self, new_content: str) -> None:
        """
        更新消息内容

        Args:
            new_content: 新内容
        """
        self.content = new_content
        self.token_count = max(1, len(new_content) // 4)
        self.updated_at = datetime.now(timezone.utc)

    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据

        Args:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def set_related_data(self, data: Dict[str, Any]) -> None:
        """
        设置关联数据

        Args:
            data: 关联数据
        """
        self.related_data.update(data)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            消息字典表示
        """
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "token_count": self.token_count,
            "processing_time_ms": self.processing_time_ms,
            "priority": self.priority.value,
            "is_deleted": self.is_deleted,
            "parent_id": self.parent_id,
            "related_data": self.related_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """
        从字典创建消息对象

        Args:
            data: 消息字典数据

        Returns:
            消息对象
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            conversation_id=data.get("conversation_id", ""),
            message_type=MessageType(data.get("message_type", "user")),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(timezone.utc).isoformat())),
            token_count=data.get("token_count", 0),
            processing_time_ms=data.get("processing_time_ms", 0),
            priority=MessagePriority(data.get("priority", 2)),
            is_deleted=data.get("is_deleted", False),
            parent_id=data.get("parent_id"),
            related_data=data.get("related_data", {})
        )


@dataclass
class Conversation:
    """
    对话会话数据类

    表示一个完整的对话会话，包含消息历史、上下文信息、
    状态管理等。支持复杂的对话模式和状态转换。

    Attributes:
        id: 对话唯一标识符
        user_id: 用户ID
        title: 对话标题
        status: 对话状态
        chat_mode: 聊天模式
        context: 对话上下文
        metadata: 对话元数据
        created_at: 创建时间
        updated_at: 更新时间
        message_count: 消息总数
        last_activity_at: 最后活动时间
        tags: 对话标签
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = ""
    status: ConversationStatus = ConversationStatus.ACTIVE
    chat_mode: ChatMode = ChatMode.GENERAL
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())

    def update_status(self, new_status: ConversationStatus) -> None:
        """
        更新对话状态

        Args:
            new_status: 新状态
        """
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

        logger.info(
            f"对话状态变更: {self.id} ({self.title}) {old_status.value} -> {new_status.value}",
            extra={
                "conversation_id": self.id,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "user_id": self.user_id
            }
        )

    def update_title(self, new_title: str) -> None:
        """
        更新对话标题

        Args:
            new_title: 新标题
        """
        self.title = new_title
        self.updated_at = datetime.now(timezone.utc)

    def update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def add_tag(self, tag: str) -> None:
        """
        添加标签

        Args:
            tag: 标签名称
        """
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now(timezone.utc)

    def remove_tag(self, tag: str) -> None:
        """
        移除标签

        Args:
            tag: 标签名称
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now(timezone.utc)

    def update_context(self, key: str, value: Any) -> None:
        """
        更新上下文信息

        Args:
            key: 上下文键
            value: 上下文值
        """
        self.context[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据

        Args:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def increment_message_count(self) -> None:
        """增加消息计数"""
        self.message_count += 1
        self.update_activity()

    def is_active(self) -> bool:
        """检查对话是否活跃"""
        return self.status == ConversationStatus.ACTIVE

    def is_paused(self) -> bool:
        """检查对话是否暂停"""
        return self.status == ConversationStatus.PAUSED

    def is_completed(self) -> bool:
        """检查对话是否已完成"""
        return self.status == ConversationStatus.COMPLETED

    def is_archived(self) -> bool:
        """检查对话是否已归档"""
        return self.status == ConversationStatus.ARCHIVED

    def get_duration_minutes(self) -> float:
        """
        获取对话持续时间（分钟）

        Returns:
            持续时间（分钟）
        """
        duration = datetime.now(timezone.utc) - self.created_at
        return duration.total_seconds() / 60

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            对话字典表示
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status.value,
            "chat_mode": self.chat_mode.value,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.message_count,
            "last_activity_at": self.last_activity_at.isoformat(),
            "tags": self.tags,
            "duration_minutes": self.get_duration_minutes()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """
        从字典创建对话对象

        Args:
            data: 对话字典数据

        Returns:
            对话对象
        """
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            title=data.get("title", ""),
            status=ConversationStatus(data.get("status", "active")),
            chat_mode=ChatMode(data.get("chat_mode", "general")),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(timezone.utc).isoformat())),
            message_count=data.get("message_count", 0),
            last_activity_at=datetime.fromisoformat(data.get("last_activity_at", datetime.now(timezone.utc).isoformat())),
            tags=data.get("tags", [])
        )


class ConversationManager:
    """
    对话管理器

    提供对话会话的管理功能，包括创建、查询、状态管理、
    消息处理等。采用内存存储，可以轻松扩展为数据库存储。

    设计原则：
        - 单例模式：确保全局唯一的对话管理器
        - 仓储模式：抽象数据存储接口
        - 观察者模式：支持对话状态变更通知
        - 缓存策略：提高访问性能
    """

    def __init__(self):
        """初始化对话管理器"""
        self._conversations: Dict[str, Conversation] = {}
        self._messages: Dict[str, List[Message]] = {}
        self._observers: List[callable] = []

    def create_conversation(
        self,
        user_id: str,
        title: str,
        chat_mode: ChatMode = ChatMode.GENERAL,
        initial_context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Conversation:
        """
        创建新对话

        Args:
            user_id: 用户ID
            title: 对话标题
            chat_mode: 聊天模式
            initial_context: 初始上下文
            tags: 对话标签

        Returns:
            创建的对话对象
        """
        conversation = Conversation(
            user_id=user_id,
            title=title,
            chat_mode=chat_mode,
            context=initial_context or {},
            tags=tags or []
        )

        # 添加到存储
        self._conversations[conversation.id] = conversation
        self._messages[conversation.id] = []

        # 通知观察者
        self._notify_observers("conversation_created", conversation)

        logger.info(
            f"创建新对话: {conversation.id} ({conversation.title})",
            extra={
                "conversation_id": conversation.id,
                "user_id": user_id,
                "chat_mode": chat_mode.value,
                "title": title
            }
        )

        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        获取对话

        Args:
            conversation_id: 对话ID

        Returns:
            对话对象或None
        """
        return self._conversations.get(conversation_id)

    def get_user_conversations(
        self,
        user_id: str,
        status: Optional[ConversationStatus] = None,
        limit: int = 20,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> List[Conversation]:
        """
        获取用户对话列表

        Args:
            user_id: 用户ID
            status: 状态过滤
            limit: 返回数量限制
            offset: 偏移量
            tags: 标签过滤

        Returns:
            对话列表
        """
        conversations = [
            conv for conv in self._conversations.values()
            if conv.user_id == user_id
        ]

        # 状态过滤
        if status:
            conversations = [conv for conv in conversations if conv.status == status]

        # 标签过滤
        if tags:
            conversations = [
                conv for conv in conversations
                if any(tag in conv.tags for tag in tags)
            ]

        # 按更新时间排序
        conversations.sort(key=lambda x: x.updated_at, reverse=True)

        # 分页
        return conversations[offset:offset + limit]

    def update_conversation(self, conversation: Conversation) -> None:
        """
        更新对话

        Args:
            conversation: 对话对象
        """
        if conversation.id in self._conversations:
            self._conversations[conversation.id] = conversation
            conversation.updated_at = datetime.now(timezone.utc)

            # 通知观察者
            self._notify_observers("conversation_updated", conversation)

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话

        Args:
            conversation_id: 对话ID

        Returns:
            是否删除成功
        """
        if conversation_id in self._conversations:
            conversation = self._conversations[conversation_id]

            # 删除消息
            if conversation_id in self._messages:
                del self._messages[conversation_id]

            # 删除对话
            del self._conversations[conversation_id]

            # 通知观察者
            self._notify_observers("conversation_deleted", conversation)

            logger.info(f"删除对话: {conversation_id}")
            return True

        return False

    def add_message(self, message: Message) -> None:
        """
        添加消息

        Args:
            message: 消息对象
        """
        if message.conversation_id not in self._messages:
            self._messages[message.conversation_id] = []

        self._messages[message.conversation_id].append(message)

        # 更新对话信息
        conversation = self.get_conversation(message.conversation_id)
        if conversation:
            conversation.increment_message_count()

        # 通知观察者
        self._notify_observers("message_added", message)

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Message]:
        """
        获取对话消息

        Args:
            conversation_id: 对话ID
            limit: 返回数量限制
            offset: 偏移量
            include_deleted: 是否包含已删除消息

        Returns:
            消息列表
        """
        if conversation_id not in self._messages:
            return []

        messages = self._messages[conversation_id]

        # 过滤已删除消息
        if not include_deleted:
            messages = [msg for msg in messages if not msg.is_deleted]

        # 按创建时间排序
        messages.sort(key=lambda x: x.created_at)

        return messages[offset:offset + limit]

    def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """
        获取对话统计信息

        Args:
            conversation_id: 对话ID

        Returns:
            统计信息字典
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return {}

        messages = self.get_messages(conversation_id, include_deleted=False)

        # 计算统计信息
        user_messages = [msg for msg in messages if msg.message_type == MessageType.USER]
        assistant_messages = [msg for msg in messages if msg.message_type == MessageType.ASSISTANT]
        system_messages = [msg for msg in messages if msg.message_type == MessageType.SYSTEM]

        total_tokens = sum(msg.token_count for msg in messages)
        total_processing_time = sum(msg.processing_time_ms for msg in messages)

        avg_processing_time = (
            total_processing_time / len(messages) if messages else 0
        )

        return {
            "conversation_id": conversation_id,
            "title": conversation.title,
            "status": conversation.status.value,
            "chat_mode": conversation.chat_mode.value,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "system_messages": len(system_messages),
            "total_tokens": total_tokens,
            "average_processing_time_ms": round(avg_processing_time, 2),
            "duration_minutes": conversation.get_duration_minutes(),
            "message_count": conversation.message_count,
            "last_activity_at": conversation.last_activity_at.isoformat(),
            "tags": conversation.tags
        }

    def add_observer(self, observer: callable) -> None:
        """
        添加观察者

        Args:
            observer: 观察者函数
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: callable) -> None:
        """
        移除观察者

        Args:
            observer: 观察者函数
        """
        if observer in self._observers:
            self.observers.remove(observer)

    def _notify_observers(self, event_type: str, data: Any) -> None:
        """
        通知观察者

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        for observer in self._observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logger.error(f"观察者通知失败: {str(e)}")

    def get_conversation_count(self, user_id: str) -> int:
        """
        获取用户对话数量

        Args:
            user_id: 用户ID

        Returns:
            对话数量
        """
        return len([
            conv for conv in self._conversations.values()
            if conv.user_id == user_id
        ])

    def cleanup_inactive_conversations(self, inactive_days: int = 30) -> int:
        """
        清理不活跃对话

        Args:
            inactive_days: 不活跃天数阈值

        Returns:
            清理的对话数量
        """
        threshold_date = datetime.now(timezone.utc) - timedelta(days=inactive_days)
        inactive_conversations = [
            conv for conv in self._conversations.values()
            if conv.last_activity_at < threshold_date
        ]

        for conversation in inactive_conversations:
            self.delete_conversation(conversation.id)

        logger.info(f"清理了 {len(inactive_conversations)} 个不活跃对话")
        return len(inactive_conversations)