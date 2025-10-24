"""Top3领域数据模型"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlmodel import Field, Column, Index, Date
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

try:
    from src.domains.auth.models import BaseModel
except ImportError:
    from ...auth.models import BaseModel


class TaskTop3(BaseModel, table=True):
    """
    任务Top3模型

    记录用户每日设置的Top3重要任务。
    每天只能设置一次，消耗300积分。
    """
    __tablename__ = "task_top3"

    user_id: str = Field(
        ...,
        index=True,
        description="用户ID"
    )
    top_date: date = Field(
        ...,
        sa_column=Column(Date),
        description="日期（YYYY-MM-DD）"
    )
    task_ids: Optional[List[Dict[str, Any]]] = Field(
        ...,
        sa_column=Column(SQLiteJSON),
        description="任务ID列表，包含位置信息，格式：[{'task_id': 'uuid', 'position': 1}]"
    )
    points_consumed: int = Field(
        default=300,
        description="消耗积分数"
    )

    __table_args__ = (
        Index('idx_user_date', 'user_id', 'top_date', unique=True),
        Index('idx_date', 'top_date'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )
