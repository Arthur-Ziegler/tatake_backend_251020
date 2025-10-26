"""
聊天域数据模型

定义聊天系统相关的数据模型，使用LangGraph内置的MessagesState
作为状态管理的基础，避免过度抽象。

设计原则：
1. 直接使用LangGraph内置的MessagesState
2. 最小化自定义字段，保持简洁
3. 符合LangGraph最佳实践
4. 支持消息序列化和存储

功能特性：
- 聊天消息状态管理
- 用户ID和会话ID跟踪
- 消息格式定义
- 状态序列化支持

作者：TaKeKe团队
版本：1.0.0
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import MessagesState


class ChatMessage(BaseModel):
    """
    聊天消息模型

    定义单个聊天消息的结构，包含消息内容和元数据。
    使用Pydantic进行数据验证和序列化。
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="消息唯一标识")
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    role: str = Field(..., pattern="^(user|assistant|tool|system)$", description="消息角色")
    content: str = Field(..., description="消息内容")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")

    # 工具调用相关字段
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="工具调用列表")
    tool_response: Optional[str] = Field(default=None, description="工具响应内容")

    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")

    model_config = ConfigDict(
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    )


class ChatSession(BaseModel):
    """
    聊天会话模型

    定义聊天会话的基本信息和状态。
    注意：根据提案设计，此模型仅用于数据传输，实际会话状态由LangGraph管理。
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="会话唯一标识")
    user_id: str = Field(..., description="用户ID")
    title: Optional[str] = Field(default=None, description="会话标题")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="更新时间")

    # 会话状态
    message_count: int = Field(default=0, description="消息数量")
    is_active: bool = Field(default=True, description="是否活跃")

    model_config = ConfigDict(
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    )


class ChatState(MessagesState):
    """
    简化的聊天状态模型

    只使用MessagesState的标准功能，不添加任何自定义字段。
    用户和会话信息通过config传递，而不是在state中。

    这是解决LangGraph版本号类型错误的根本方案：
    - 移除所有自定义字段，避免干扰LangGraph的内部机制
    - 保持MessagesState的纯粹性
    - 通过config而不是state传递元数据
    """

    # 不添加任何自定义字段！完全依赖MessagesState的messages字段

    def add_human_message(self, content: str) -> None:
        """
        添加用户消息

        Args:
            content: 用户消息内容
        """
        message = HumanMessage(content=content)
        self.messages.append(message)

    def add_ai_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        添加AI消息

        Args:
            content: AI回复内容
            tool_calls: 工具调用列表（可选）
        """
        message = AIMessage(content=content)
        if tool_calls:
            # AIMessage支持工具调用，但这里简化处理
            message.additional_kwargs["tool_calls"] = tool_calls
        self.messages.append(message)

    def add_tool_message(self, content: str, tool_call_id: str) -> None:
        """
        添加工具消息

        Args:
            content: 工具执行结果
            tool_call_id: 工具调用ID
        """
        message = ToolMessage(content=content, tool_call_id=tool_call_id)
        self.messages.append(message)

    def get_last_message(self) -> Optional[BaseMessage]:
        """
        获取最后一条消息

        Returns:
            最后一条消息，如果没有则返回None
        """
        return self.messages[-1] if self.messages else None

    def get_message_count(self) -> int:
        """
        获取消息数量

        Returns:
            消息总数
        """
        return len(self.messages)


class ToolCallResult(BaseModel):
    """
    工具调用结果模型

    定义工具调用的结果格式，用于AI和工具之间的数据交换。
    """

    tool_name: str = Field(..., description="工具名称")
    tool_args: Dict[str, Any] = Field(..., description="工具参数")
    result: Any = Field(..., description="工具执行结果")
    success: bool = Field(..., description="执行是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
    execution_time: Optional[float] = Field(default=None, description="执行时间（秒）")

    model_config = ConfigDict(
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    )


# 便捷函数
def create_chat_state() -> ChatState:
    """
    创建新的聊天状态

    简化版本：不包含任何自定义字段，只使用MessagesState的标准功能。
    用户和会话信息通过config传递，而不是在state中。

    Returns:
        新的ChatState实例
    """
    return ChatState(
        messages=[]  # 只包含messages字段，不添加任何自定义字段
    )


def message_to_chat_message(message: BaseMessage, session_id: str, user_id: str) -> ChatMessage:
    """
    将LangGraph消息转换为聊天消息模型

    Args:
        message: LangGraph消息
        session_id: 会话ID
        user_id: 用户ID

    Returns:
        ChatMessage实例
    """
    # 确定消息角色
    if isinstance(message, HumanMessage):
        role = "user"
    elif isinstance(message, AIMessage):
        role = "assistant"
    elif isinstance(message, ToolMessage):
        role = "tool"
    else:
        role = "system"

    # 提取工具调用信息
    tool_calls = None
    tool_response = None

    if isinstance(message, AIMessage):
        tool_calls = message.additional_kwargs.get("tool_calls")
    elif isinstance(message, ToolMessage):
        tool_response = message.content

    return ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role=role,
        content=message.content,
        tool_calls=tool_calls,
        tool_response=tool_response
    )