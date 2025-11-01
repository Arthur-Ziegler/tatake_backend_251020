"""
任务本地操作数据库模型

存储微服务不支持的任务操作，如删除、更新、完成等。
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel, Column, DateTime
from sqlalchemy import text


class TaskOperationBase(SQLModel):
    """任务操作基础模型"""
    user_id: UUID = Field(description="用户ID（UUID字符串）")
    task_id: str = Field(description="任务ID（来自微服务）")
    operation_type: str = Field(description="操作类型：delete, update, complete")
    operation_data: Optional[str] = Field(default=None, description="操作数据（JSON格式）")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=text("CURRENT_TIMESTAMP")),
        description="创建时间"
    )


class TaskOperation(TaskOperationBase, table=True):
    """任务操作表"""
    __tablename__ = "task_operations"

    id: Optional[int] = Field(default=None, primary_key=True)


class TaskCompletionBase(SQLModel):
    """任务完成基础模型"""
    user_id: UUID = Field(description="用户ID（UUID字符串）")
    task_id: str = Field(description="任务ID（来自微服务）")
    completion_type: str = Field(description="完成类型：full, partial")
    points_earned: int = Field(default=0, description="获得的积分")
    reward_given: Optional[str] = Field(default=None, description="奖励描述")
    completion_data: Optional[str] = Field(default=None, description="完成数据（JSON格式）")
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=text("CURRENT_TIMESTAMP")),
        description="完成时间"
    )


class TaskCompletion(TaskCompletionBase, table=True):
    """任务完成记录表"""
    __tablename__ = "task_completions"

    id: Optional[int] = Field(default=None, primary_key=True)


class FocusStatusBase(SQLModel):
    """专注状态基础模型"""
    user_id: UUID = Field(description="用户ID（UUID字符串）")
    task_id: Optional[str] = Field(default=None, description="相关任务ID")
    focus_status: str = Field(description="专注状态：start, break, complete, pause")
    duration_minutes: Optional[int] = Field(default=None, description="专注时长（分钟）")
    status_data: Optional[str] = Field(default=None, description="状态数据（JSON格式）")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=text("CURRENT_TIMESTAMP")),
        description="创建时间"
    )


class FocusStatus(FocusStatusBase, table=True):
    """专注状态记录表"""
    __tablename__ = "focus_status_records"

    id: Optional[int] = Field(default=None, primary_key=True)


class PomodoroCountBase(SQLModel):
    """番茄钟计数基础模型"""
    user_id: UUID = Field(description="用户ID（UUID字符串）")
    date_filter: str = Field(description="日期过滤类型：today, week, month")
    count: int = Field(default=0, description="番茄钟数量")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, server_default=text("CURRENT_TIMESTAMP")),
        description="最后更新时间"
    )


class PomodoroCount(PomodoroCountBase, table=True):
    """番茄钟计数表"""
    __tablename__ = "pomodoro_counts"

    id: Optional[int] = Field(default=None, primary_key=True)