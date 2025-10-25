"""Top3领域Schema定义"""

from datetime import date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from src.core.uuid_converter import UUIDConverter


class SetTop3Request(BaseModel):
    """设置Top3请求"""
    date: str = Field(...,
        example="2025-01-15", description="日期，格式：YYYY-MM-DD")
    task_ids: List[str] = Field(...,
        min_items=1, max_items=3,
        example=["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"],
        description="任务ID列表，必须是有效的UUID格式")

    @field_validator("task_ids")
    @classmethod
    def validate_task_ids(cls, v):
        """验证任务ID列表"""
        if not v or len(v) < 1 or len(v) > 3:
            raise ValueError("task_ids必须包含1-3个任务")

        # 验证每个task_id都是有效的UUID格式
        for task_id in v:
            if not UUIDConverter.is_valid_uuid_string(task_id):
                raise ValueError(f"无效的UUID格式: {task_id}")

        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        """验证日期格式"""
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("日期格式无效，请使用YYYY-MM-DD格式")


class Top3Response(BaseModel):
    """Top3响应"""
    date: str = Field(..., example="2025-01-15", description="日期")
    task_ids: List[str] = Field(..., example=["550e8400-e29b-41d4-a716-446655440000"], description="任务ID列表")
    points_consumed: int = Field(..., example=5, description="消耗积分")
    remaining_balance: Optional[int] = Field(None, example=100, description="剩余积分")


class GetTop3Response(BaseModel):
    """获取Top3响应"""
    date: str = Field(..., example="2025-01-15", description="日期")
    task_ids: List[str] = Field(..., example=["550e8400-e29b-41d4-a716-446655440000"], description="任务ID列表")
    points_consumed: int = Field(..., example=5, description="消耗积分")
    created_at: Optional[str] = Field(None, example="2025-01-15T10:30:00Z", description="创建时间")
