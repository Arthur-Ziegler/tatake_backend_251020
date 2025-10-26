"""
Focus领域API Schema - 简化番茄钟系统

定义API请求和响应的数据结构，采用极简设计：
- 只包含必要的字段，避免冗余信息
- 使用类型注解确保数据安全
- 统一的响应格式

Schema设计原则：
1. KISS：只包含必要的字段，避免过度设计
2. 一致性：与项目其他领域的Schema风格保持一致
3. 可扩展：预留扩展空间，但不添加当前不需要的字段
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.core.uuid_converter import UUIDConverter
from .models import SessionType, SessionTypeConst


class StartFocusRequest(BaseModel):
    """
    开始专注会话请求模型

    极简设计，只需要任务ID和会话类型：
    - task_id: 必须关联一个有效任务
    - session_type: 支持多种会话类型

    设计说明：
    - 不包含计划时长，由前端控制
    - 不包含备注等非必要字段
    - 所有会话（包括暂停）都使用同一个请求模型
    """
    task_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="任务ID")
    session_type: str = Field(default=SessionTypeConst.FOCUS,
        example="focus", description="会话类型: focus(专注)/break(短休息)/long_break(长休息)/pause(暂停)")

    @field_validator('task_id')
    def validate_task_id(cls, v):
        """验证任务ID格式"""
        if not v:
            raise ValueError('任务ID不能为空')

        # 验证UUID格式
        if not UUIDConverter.is_valid_uuid_string(v):
            raise ValueError(f'任务ID格式无效: {v}')

        return v


class FocusSessionResponse(BaseModel):
    """
    专注会话响应模型

    返回会话的基本信息，不包含复杂计算：
    - 包含所有6个核心字段
    - 时间格式化处理
    - 简单的状态指示

    设计说明：
    - 不计算duration，由前端根据时间差计算
    - 不包含复杂的status字段，通过end_time判断状态
    - 不包含created_at字段，只保留6个核心字段
    - 保持数据简洁，便于前端处理
    """
    id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="会话ID")
    user_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440001", description="用户ID")
    task_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440002", description="任务ID")
    session_type: str = Field(...,
        example="focus", description="会话类型")
    start_time: datetime = Field(...,
        example="2025-01-15T10:30:00Z", description="开始时间")
    end_time: Optional[datetime] = Field(None,
        example="2025-01-15T11:00:00Z", description="结束时间")

    @property
    def is_active(self) -> bool:
        """检查会话是否正在进行中"""
        return self.end_time is None

    model_config = ConfigDict(
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class FocusOperationResponse(BaseModel):
    """
    Focus操作响应模型 - 按照v3文档格式

    数据结构包含session对象，符合v3文档要求：
    - 不包含current_time字段（用户明确要求）
    - session对象包含完整的会话信息

    设计说明：
    - 与v3文档格式保持一致
    - 去掉current_time字段，用户明确要求不包含
    - 简洁的数据结构，便于前端处理
    """
    session: FocusSessionResponse = Field(...,
        description="专注会话信息")

    model_config = ConfigDict(
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class FocusSessionListResponse(BaseModel):
    """
    专注会话列表响应模型

    支持分页查询，返回会话列表：
    - 简单的分页结构
    - 基本的统计信息
    - 按时间倒序排列

    设计说明：
    - 不包含复杂的聚合数据
    - 提供基本的分页信息
    - 保持结构简单
    """
    sessions: List[FocusSessionResponse] = Field(default=[],
        description="专注会话列表")
    total: int = Field(...,
        example=50, description="总会话数")
    page: int = Field(...,
        example=1, description="当前页码")
    page_size: int = Field(...,
        example=20, description="每页大小")
    has_more: bool = Field(...,
        example=True, description="是否有更多页")

    model_config = ConfigDict(
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    )