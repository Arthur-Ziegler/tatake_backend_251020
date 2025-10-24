"""Top3领域Schema定义"""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SetTop3Request(BaseModel):
    """设置Top3请求"""
    date: str = Field(..., description="日期（YYYY-MM-DD）")
    task_ids: List[str] = Field(..., description="任务ID列表，1-3个")

    @field_validator("task_ids")
    @classmethod
    def validate_task_ids(cls, v):
        if not v or len(v) < 1 or len(v) > 3:
            raise ValueError("task_ids必须包含1-3个任务")
        return v


class Top3Response(BaseModel):
    """Top3响应"""
    date: str
    task_ids: List[str]
    points_consumed: int
    remaining_balance: Optional[int] = Field(None, description="设置Top3后的剩余积分余额")


class GetTop3Response(BaseModel):
    """获取Top3响应"""
    date: str
    task_ids: List[str]
    points_consumed: int
    created_at: Optional[str] = None
