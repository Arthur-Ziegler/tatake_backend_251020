"""
聊天域API数据模型

定义聊天功能相关的请求和响应数据模型，使用Pydantic进行数据验证。

设计原则：
1. 明确的字段定义和类型注解
2. 详细的字段描述和验证规则
3. 清晰的响应模型结构
4. 完整的错误处理支持
5. 自动API文档生成支持

功能特性：
- 会话创建请求模型
- 消息发送请求模型
- 会话响应模型
- 消息响应模型
- 历史查询模型
- 列表查询模型

作者：TaKeKe团队
版本：1.0.0
"""

from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, validator


# ========== 请求模型 ==========

class CreateSessionRequest(BaseModel):
    """创建聊天会话请求"""

    title: Optional[str] = Field(
        default=None,
        description="会话标题，如果不提供则使用默认标题",
        example="日常对话",
        max_length=100
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "日常对话"
            }
        }
    }


class SendMessageRequest(BaseModel):
    """发送消息请求"""

    message: str = Field(
        ...,
        description="用户消息内容",
        min_length=1,
        max_length=4000,
        example="你好，请帮我计算1+2等于多少？"
    )

    @validator('message')
    def validate_message(cls, v):
        """验证消息内容"""
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "你好，请帮我计算1+2等于多少？"
            }
        }
    }


# ========== 响应模型 ==========

class ChatSessionResponse(BaseModel):
    """创建聊天会话响应"""

    session_id: str = Field(
        ...,
        description="会话ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )

    title: str = Field(
        ...,
        description="会话标题",
        example="日常对话"
    )

    created_at: str = Field(
        ...,
        description="创建时间（ISO格式）",
        example="2024-01-01T12:00:00Z"
    )

    welcome_message: str = Field(
        ...,
        description="欢迎消息",
        example="你好！我是你的AI助手，很高兴为你服务。"
    )

    status: str = Field(
        ...,
        description="会话状态",
        example="created"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "日常对话",
                "created_at": "2024-01-01T12:00:00Z",
                "welcome_message": "你好！我是你的AI助手，很高兴为你服务。",
                "status": "created"
            }
        }
    }


class MessageResponse(BaseModel):
    """发送消息响应"""

    session_id: str = Field(
        ...,
        description="会话ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )

    user_message: str = Field(
        ...,
        description="用户消息",
        example="你好，请帮我计算1+2等于多少？"
    )

    ai_response: str = Field(
        ...,
        description="AI回复",
        example="1+2 = 3"
    )

    timestamp: str = Field(
        ...,
        description="消息时间戳（ISO格式）",
        example="2024-01-01T12:01:00Z"
    )

    status: str = Field(
        ...,
        description="处理状态",
        example="success"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_message": "你好，请帮我计算1+2等于多少？",
                "ai_response": "1+2 = 3",
                "timestamp": "2024-01-01T12:01:00Z",
                "status": "success"
            }
        }
    }


class ChatMessageItem(BaseModel):
    """聊天消息项"""

    type: str = Field(
        ...,
        description="消息类型",
        example="human"
    )

    content: str = Field(
        ...,
        description="消息内容",
        example="你好，请帮我计算1+2等于多少？"
    )

    timestamp: str = Field(
        ...,
        description="消息时间戳（ISO格式）",
        example="2024-01-01T12:01:00Z"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "human",
                "content": "你好，请帮我计算1+2等于多少？",
                "timestamp": "2024-01-01T12:01:00Z"
            }
        }
    }


class ChatHistoryResponse(BaseModel):
    """聊天历史响应"""

    session_id: str = Field(
        ...,
        description="会话ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )

    messages: List[ChatMessageItem] = Field(
        ...,
        description="消息列表"
    )

    total_count: int = Field(
        ...,
        description="消息总数",
        example=10
    )

    limit: int = Field(
        ...,
        description="返回数量限制",
        example=50
    )

    timestamp: str = Field(
        ...,
        description="查询时间戳（ISO格式）",
        example="2024-01-01T12:02:00Z"
    )

    status: str = Field(
        ...,
        description="查询状态",
        example="success"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "messages": [
                    {
                        "type": "human",
                        "content": "你好，请帮我计算1+2等于多少？",
                        "timestamp": "2024-01-01T12:01:00Z"
                    },
                    {
                        "type": "ai",
                        "content": "1+2 = 3",
                        "timestamp": "2024-01-01T12:01:05Z"
                    }
                ],
                "total_count": 2,
                "limit": 50,
                "timestamp": "2024-01-01T12:02:00Z",
                "status": "success"
            }
        }
    }


class SessionInfoResponse(BaseModel):
    """会话信息响应"""

    session_id: str = Field(
        ...,
        description="会话ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )

    title: str = Field(
        ...,
        description="会话标题",
        example="日常对话"
    )

    message_count: int = Field(
        ...,
        description="消息数量",
        example=5
    )

    created_at: str = Field(
        ...,
        description="创建时间（ISO格式）",
        example="2024-01-01T12:00:00Z"
    )

    updated_at: str = Field(
        ...,
        description="更新时间（ISO格式）",
        example="2024-01-01T12:05:00Z"
    )

    status: str = Field(
        ...,
        description="会话状态",
        example="active"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "日常对话",
                "message_count": 5,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:05:00Z",
                "status": "active"
            }
        }
    }


class ChatSessionItem(BaseModel):
    """聊天会话项"""

    session_id: str = Field(
        ...,
        description="会话ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )

    title: str = Field(
        ...,
        description="会话标题",
        example="日常对话"
    )

    message_count: int = Field(
        ...,
        description="消息数量",
        example=5
    )

    created_at: str = Field(
        ...,
        description="创建时间（ISO格式）",
        example="2024-01-01T12:00:00Z"
    )

    updated_at: str = Field(
        ...,
        description="更新时间（ISO格式）",
        example="2024-01-01T12:05:00Z"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "日常对话",
                "message_count": 5,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:05:00Z"
            }
        }
    }


class SessionListResponse(BaseModel):
    """会话列表响应"""

    user_id: str = Field(
        ...,
        description="用户ID",
        example="test-user-123"
    )

    sessions: List[ChatSessionItem] = Field(
        ...,
        description="会话列表"
    )

    total_count: int = Field(
        ...,
        description="会话总数",
        example=3
    )

    limit: int = Field(
        ...,
        description="返回数量限制",
        example=20
    )

    timestamp: str = Field(
        ...,
        description="查询时间戳（ISO格式）",
        example="2024-01-01T12:10:00Z"
    )

    status: str = Field(
        ...,
        description="查询状态",
        example="success"
    )

    note: str = Field(
        ...,
        description="备注信息",
        example=""
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "test-user-123",
                "sessions": [
                    {
                        "session_id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "日常对话",
                        "message_count": 5,
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:05:00Z"
                    }
                ],
                "total_count": 1,
                "limit": 20,
                "timestamp": "2024-01-01T12:10:00Z",
                "status": "success",
                "note": ""
            }
        }
    }


class DeleteSessionResponse(BaseModel):
    """删除会话响应"""

    session_id: str = Field(
        ...,
        description="会话ID",
        example="123e4567-e89b-12d3-a456-426614174000"
    )

    status: str = Field(
        ...,
        description="删除状态",
        example="deleted"
    )

    timestamp: str = Field(
        ...,
        description="删除时间戳（ISO格式）",
        example="2024-01-01T12:15:00Z"
    )

    note: str = Field(
        ...,
        description="备注信息",
        example=""
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "deleted",
                "timestamp": "2024-01-01T12:15:00Z",
                "note": ""
            }
        }
    }


class ChatHealthResponse(BaseModel):
    """聊天服务健康检查响应"""

    status: str = Field(
        ...,
        description="服务状态",
        example="healthy"
    )

    database: dict = Field(
        ...,
        description="数据库状态"
    )

    graph_initialized: bool = Field(
        ...,
        description="图是否已初始化",
        example=True
    )

    timestamp: str = Field(
        ...,
        description="检查时间戳（ISO格式）",
        example="2024-01-01T12:20:00Z"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "database": {
                    "status": "healthy",
                    "file_exists": True,
                    "connected": True,
                    "checkpointer_ok": True,
                    "store_ok": True
                },
                "graph_initialized": True,
                "timestamp": "2024-01-01T12:20:00Z"
            }
        }
    }