"""
聊天域API数据模型

定义简化版聊天功能的请求和响应数据模型。

设计原则：
1. 极简化：只包含必要字段
2. 统一格式：所有响应都符合UnifiedResponse包装
3. 用户友好：清晰的字段描述和示例
4. 类型安全：严格的类型验证

核心接口：
1. 查询所有会话列表
2. 查询聊天记录
3. 删除会话
4. 聊天接口（流式）

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.api.schemas import UnifiedResponse


# ========== 请求模型 ==========

class ChatMessageRequest(BaseModel):
    """聊天消息请求"""

    message: str = Field(..., description="消息内容", example="你好，请帮我介绍一下Python")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "你好，请帮我介绍一下Python"
            }
        }


# ========== 响应模型 ==========

class SessionListItem(BaseModel):
    """会话列表项"""

    session_id: str = Field(..., description="会话ID", example="20251101051704_4a42")
    title: str = Field(..., description="会话标题", example="会话20251101051704")


class ChatHistoryMessage(BaseModel):
    """聊天历史消息"""

    role: str = Field(..., description="消息角色", example="human")
    content: str = Field(..., description="消息内容", example="你好")
    time: str = Field(..., description="UTC时间", example="2025-11-01T05:17:04Z")


class ChatHistoryResponse(BaseModel):
    """聊天记录响应"""

    session_id: str = Field(..., description="会话ID", example="20251101051704_4a42")
    title: str = Field(..., description="会话标题", example="会话20251101051704")
    messages: List[ChatHistoryMessage] = Field(..., description="聊天记录列表")


class DeleteSessionResponse(BaseModel):
    """删除会话响应"""

    success: bool = Field(..., description="删除是否成功", example=True)