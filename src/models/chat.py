"""
聊天相关数据模型

本模块定义了聊天系统相关的数据模型，包括：
- ChatSession: 聊天会话模型
- ChatMessage: 聊天消息模型

设计原则：
- 使用SQLModel作为ORM框架
- 支持UUID主键
- 包含时间戳字段
- 使用枚举类型确保数据一致性
- 支持JSON字段存储元数据
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import DateTime, func

from .base_model import BaseSQLModel as BaseModel
from .enums import ChatMode, MessageRole, SessionStatus
from .user import User


class ChatSession(BaseModel, table=True):
    """
    聊天会话模型

    表示一个完整的聊天会话，包含会话的基本信息、状态和配置。
    每个会话属于一个用户，包含多条消息。

    Attributes:
        id: 会话唯一标识符
        user_id: 用户ID
        title: 会话标题
        chat_mode: 聊天模式
        status: 会话状态
        metadata: 会话元数据（JSON格式）
        last_activity_at: 最后活动时间
        message_count: 消息总数
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "chat_sessions"

    # 会话基本信息
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="会话唯一标识符"
    )
    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        description="所属用户ID"
    )
    title: str = Field(
        max_length=200,
        nullable=False,
        description="会话标题"
    )
    chat_mode: ChatMode = Field(
        default=ChatMode.GENERAL,
        nullable=False,
        description="聊天模式"
    )
    status: SessionStatus = Field(
        default=SessionStatus.ACTIVE,
        nullable=False,
        description="会话状态"
    )

    # 会话元数据
    session_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="会话元数据（JSON格式）"
    )

    # 时间和统计信息
    last_activity_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="最后活动时间"
    )
    message_count: int = Field(
        default=0,
        nullable=False,
        description="消息总数"
    )

    # 关联关系
    user: User = Relationship(
        back_populates="chat_sessions",
        sa_relationship_kwargs={"lazy": "select"}
    )
    messages: list["ChatMessage"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "lazy": "select",
            "cascade": "all, delete-orphan",
            "order_by": "ChatMessage.created_at"
        }
    )

    def update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def increment_message_count(self) -> None:
        """增加消息计数"""
        self.message_count += 1
        self.update_activity()

    def update_status(self, new_status: SessionStatus) -> None:
        """
        更新会话状态

        Args:
            new_status: 新状态
        """
        self.status = new_status
        self.update_activity()

    def is_active(self) -> bool:
        """检查会话是否活跃"""
        return self.status.is_active()

    def is_ended(self) -> bool:
        """检查会话是否已结束"""
        return self.status.is_ended()

    def get_duration_minutes(self) -> float:
        """
        获取会话持续时间（分钟）

        Returns:
            持续时间（分钟）
        """
        duration = datetime.now(timezone.utc) - self.created_at
        return duration.total_seconds() / 60

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            会话字典表示
        """
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "chat_mode": self.chat_mode.value,
            "status": self.status.value,
            "metadata": self.session_metadata,
            "last_activity_at": self.last_activity_at.isoformat(),
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "duration_minutes": self.get_duration_minutes()
        }


class ChatMessage(BaseModel, table=True):
    """
    聊天消息模型

    表示聊天会话中的单条消息，包含消息内容、角色、元数据等信息。
    支持多种消息类型和优先级。

    Attributes:
        id: 消息唯一标识符
        session_id: 会话ID
        role: 消息角色
        content: 消息内容
        metadata: 消息元数据（JSON格式）
        token_count: Token数量估算
        processing_time_ms: 处理耗时（毫秒）
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "chat_messages"

    # 消息基本信息
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="消息唯一标识符"
    )
    session_id: UUID = Field(
        foreign_key="chat_sessions.id",
        nullable=False,
        description="所属会话ID"
    )
    role: MessageRole = Field(
        nullable=False,
        description="消息角色"
    )
    content: str = Field(
        nullable=False,
        description="消息内容"
    )

    # 消息元数据
    message_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="消息元数据（JSON格式）"
    )

    # 性能和统计信息
    token_count: int = Field(
        default=0,
        nullable=False,
        description="Token数量估算"
    )
    processing_time_ms: int = Field(
        default=0,
        nullable=False,
        description="处理耗时（毫秒）"
    )

    # 关联关系
    session: ChatSession = Relationship(
        back_populates="messages",
        sa_relationship_kwargs={"lazy": "select"}
    )

    def __post_init__(self):
        """初始化后处理"""
        # 估算Token数量（简单实现：按字符数/4估算）
        if self.content and not self.token_count:
            self.token_count = max(1, len(self.content) // 4)

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
        self.message_metadata[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def set_processing_time(self, processing_time_ms: int) -> None:
        """
        设置处理时间

        Args:
            processing_time_ms: 处理时间（毫秒）
        """
        self.processing_time_ms = processing_time_ms
        self.updated_at = datetime.now(timezone.utc)

    def is_user_message(self) -> bool:
        """检查是否为用户消息"""
        return self.role == MessageRole.USER

    def is_assistant_message(self) -> bool:
        """检查是否为AI助手消息"""
        return self.role == MessageRole.ASSISTANT

    def is_system_message(self) -> bool:
        """检查是否为系统消息"""
        return self.role == MessageRole.SYSTEM

    def is_tool_message(self) -> bool:
        """检查是否为工具调用消息"""
        return self.role == MessageRole.TOOL

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            消息字典表示
        """
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role.value,
            "content": self.content,
            "metadata": self.message_metadata,
            "token_count": self.token_count,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# 导出所有模型，便于外部导入
__all__ = [
    "ChatSession",
    "ChatMessage"
]