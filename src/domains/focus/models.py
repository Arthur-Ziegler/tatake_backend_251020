"""
Focus领域数据模型 - 简化番茄钟系统

根据v3文档设计理念，采用极简设计：
- 仅记录时间段，不计算duration/管理status
- 6个核心字段：id, user_id, task_id, session_type, start_time, end_time
- 支持4种会话类型：focus, break, long_break, pause
- 自动关闭机制：新会话开始时自动关闭未完成会话

设计原则：
1. KISS：极简字段定义，避免复杂状态管理
2. YAGNI：只记录当前需要的数据，统计由其他服务处理
3. 时区安全：所有时间字段使用timezone-aware的datetime
4. 无继承：直接继承SQLModel，避免BaseModel的created_at/updated_at字段
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column, DateTime, Index
from sqlalchemy import text


# 定义会话类型
SessionType = str

# 会话类型常量
class SessionTypeConst:
    FOCUS = "focus"
    BREAK = "break"
    LONG_BREAK = "long_break"
    PAUSE = "pause"


class FocusSession(SQLModel, table=True):
    """
    专注会话模型 - 极简设计

    仅记录核心会话信息，不包含复杂的状态管理和时长计算。
    所有会话时长和统计数据由前端或统计服务根据时间段计算得出。

    核心字段（6个，符合提案要求）：
    - id: 主键
    - user_id: 用户ID
    - task_id: 关联任务ID（必填）
    - session_type: 会话类型（focus/break/long_break/pause）
    - start_time: 开始时间（必填）
    - end_time: 结束时间（NULL表示进行中）

    业务逻辑：
    1. end_time为NULL表示会话正在进行中
    2. 每个用户同时只能有一个进行中的会话
    3. 新会话开始时自动关闭未完成的会话
    4. 暂停会话也是独立的会话记录
    """
    __tablename__ = "focus_sessions"

    # 主键ID
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        description="主键ID"
    )

    # 用户ID（必填，建立索引）
    user_id: str = Field(
        ...,
        index=True,
        description="用户ID，关联认证表"
    )

    # 关联任务ID（必填，建立索引）
    task_id: str = Field(
        ...,
        index=True,
        description="关联的任务ID，必填字段"
    )

    # 会话类型
    session_type: str = Field(
        ...,
        description="会话类型：focus(专注)/break(短休息)/long_break(长休息)/pause(暂停)"
    )

    # 开始时间（必填，建立索引）
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), index=True),
        description="会话开始时间"
    )

    # 结束时间（可选，NULL表示进行中）
    end_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="会话结束时间，NULL表示会话正在进行中"
    )

    # 数据库索引优化
    __table_args__ = (
        Index('idx_user_time', 'user_id', 'start_time'),
        Index('idx_task_session', 'task_id', 'session_type'),
        Index('idx_session_type', 'session_type'),  # 会话类型索引
        Index('idx_active_session', 'user_id', 'end_time'),  # 用于查询进行中的会话
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )

    def __repr__(self) -> str:
        """会话模型的字符串表示"""
        status = "进行中" if self.end_time is None else "已完成"
        return f"FocusSession(id={self.id}, type={self.session_type}, status={status})"

    @property
    def is_active(self) -> bool:
        """检查会话是否正在进行中"""
        return self.end_time is None

    @property
    def duration_minutes(self) -> Optional[int]:
        """计算会话时长（分钟）"""
        if self.end_time is None:
            return None
        return int((self.end_time - self.start_time).total_seconds() / 60)