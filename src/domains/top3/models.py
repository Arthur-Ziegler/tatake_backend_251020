"""Top3领域数据模型"""

from datetime import date
from typing import List, Dict, Any, Optional

from sqlmodel import SQLModel, Field, Column, Index, Date, String
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON


class TaskTop3(SQLModel, table=True):
    """
    任务Top3模型

    记录用户每日设置的Top3重要任务。
    每天只能设置一次，消耗300积分。
    """
    __tablename__ = "task_top3"

    id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}, description="主键ID")
    user_id: str = Field(
        ...,
        sa_column=Column(String(36), index=True),
        description="用户ID（字符串格式）"
    )
    top_date: date = Field(
        ...,
        sa_column=Column(Date),
        description="日期（YYYY-MM-DD）"
    )
    task_ids: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(SQLiteJSON),
        description="任务ID列表，包含位置信息，格式：[{'task_id': 'uuid', 'position': 1}]"
    )
    points_consumed: int = Field(
        default=300,
        description="消耗积分数"
    )
    created_at: date = Field(
        default_factory=date.today,
        description="创建时间"
    )

    __table_args__ = (
        Index('idx_user_date', 'user_id', 'top_date', unique=True),
        Index('idx_date', 'top_date'),
    )
