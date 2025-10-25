"""
简化的聊天状态

基于Context7最佳实践：
1. 使用MessagesState避免复杂状态
2. 最小化状态定义
3. 类型安全
4. KISS原则

作者：TaKeKe团队
版本：1.0.0 - 简化状态管理
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from langgraph.graph import MessagesState

from langchain_core.messages import BaseMessage


class SimpleChatState(MessagesState):
    """
    简化的聊天状态

    继承自MessagesState，避免复杂的状态管理
    只包含必要的消息字段，其他元数据由数据库管理
    """
    # MessagesState已经包含了messages字段，无需额外定义
    # 遵循KISS原则，保持简单
    pass


class MessageMetadata:
    """
    消息元数据

    用于数据库存储的消息信息
    """

    def __init__(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        message_id: Optional[str] = None
    ):
        """
        初始化消息元数据

        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 消息内容
            timestamp: 时间戳（可选）
            message_id: 消息ID（可选）
        """
        self.session_id = session_id
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.message_id = message_id or str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageMetadata":
        """从字典创建实例"""
        return cls(
            session_id=data["session_id"],
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            message_id=data.get("message_id")
        )


class SessionInfo:
    """
    会话信息

    用于数据库存储的会话元数据
    """

    def __init__(
        self,
        session_id: str,
        user_id: str,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_message_at: Optional[datetime] = None
    ):
        """
        初始化会话信息

        Args:
            session_id: 会话ID
            user_id: 用户ID
            title: 会话标题
            created_at: 创建时间
            last_message_at: 最后消息时间
        """
        self.session_id = session_id
        self.user_id = user_id
        self.title = title or "新会话"
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_message_at = last_message_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        """从字典创建实例"""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            title=data.get("title"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_message_at=datetime.fromisoformat(data["last_message_at"]) if data.get("last_message_at") else None
        )

    def update_last_message_time(self) -> None:
        """更新最后消息时间"""
        self.last_message_at = datetime.now(timezone.utc)