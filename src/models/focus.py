"""
专注系统相关数据模型

本模块定义了专注系统相关的数据模型，包括：
- FocusSession: 专注会话信息模型，记录用户的专注时段
- FocusSessionBreak: 专注会话休息模型，记录专注期间的休息信息
- FocusSessionTemplate: 专注会话模板模型，用户自定义的专注配置

设计原则：
1. 时间精确：所有时间字段都使用UTC时区，确保时间计算准确
2. 状态管理：完整的会话状态流转，从开始到结束的生命周期管理
3. 灵活配置：支持不同类型的专注模式（番茄钟、自定义等）
4. 关联完整：与用户和任务建立完整的关系，支持数据分析和统计

使用示例：
    >>> session = FocusSession(
    ...     session_type=SessionType.FOCUS,
    ...     user_id="user123",
    ...     duration_minutes=25
    ... )
    >>> session.complete_session()
    >>> print(f"专注时长: {session.duration_minutes}分钟")
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

# 导入基础模型类和枚举
from src.models.base_model import BaseSQLModel
from src.models.enums import SessionType

# 避免循环导入的类型检查
if TYPE_CHECKING:
    from src.models.user import User
    from src.models.task import Task


class FocusSession(BaseSQLModel, table=True):
    """
    专注会话信息模型

    记录用户的专注时段信息，包括专注类型、持续时间、关联任务等。
    支持番茄钟工作法和其他专注时间管理方法。

    Attributes:
        session_type (SessionType): 会话类型，区分专注、休息、长休息等
        started_at (Optional[datetime]): 会话开始时间，UTC时区
        ended_at (Optional[datetime]): 会话结束时间，UTC时区
        duration_minutes (Optional[int]): 持续时间（分钟），自动计算或手动设置
        is_completed (bool): 会话是否已完成，默认False
        user_id (str): 用户ID，外键关联到User表
        task_id (Optional[str]): 关联任务ID，外键关联到Task表，可选
        user (User): 关联的用户，多对一关系
        task (Optional[Task]): 关联的任务，多对一关系
        breaks (List[FocusSessionBreak]): 休息记录，一对多关系
    """

    __tablename__ = "focus_sessions"

    # 会话基本信息
    session_type: SessionType = Field(
        description="会话类型，区分专注、休息、长休息等"
    )

    # 时间相关字段
    started_at: Optional[datetime] = Field(
        default=None,
        description="会话开始时间，UTC时区"
    )

    ended_at: Optional[datetime] = Field(
        default=None,
        description="会话结束时间，UTC时区"
    )

    duration_minutes: Optional[int] = Field(
        default=None,
        ge=0,
        le=480,  # 最长8小时
        description="持续时间（分钟），自动计算或手动设置"
    )

    # 状态字段
    is_completed: bool = Field(
        default=False,
        description="会话是否已完成"
    )

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表，标识会话归属"
    )

    task_id: Optional[str] = Field(
        default=None,
        foreign_key="tasks.id",
        index=True,
        description="关联任务ID，外键关联到Task表，可选字段"
    )

    # 排序和优先级
    sort_order: int = Field(
        default=0,
        description="排序顺序，用于自定义会话排序"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    task: Optional["Task"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    # breaks: List["FocusSessionBreak"] = Relationship(
    #     back_populates="focus_session",
    #     sa_relationship_kwargs={
    #         "cascade": "all, delete-orphan",
    #         "lazy": "select"
    #     }
    # )

    def __repr__(self) -> str:
        """
        返回专注会话的字符串表示

        Returns:
            str: 专注会话的基本信息表示

        Example:
            >>> session = FocusSession(session_type=SessionType.FOCUS, user_id="user123")
            >>> print(repr(session))
            FocusSession(id=uuid-string)
        """
        return f"FocusSession(id={self.id})"

    def __str__(self) -> str:
        """
        返回专注会话友好的字符串表示

        Returns:
            str: 专注会话的类型和状态表示

        Example:
            >>> session = FocusSession(session_type=SessionType.FOCUS, user_id="user123")
            >>> print(str(session))
            Focus Session (focus)
        """
        return f"{self.session_type.value.title()} Session ({self.session_type.value})"

    def start_session(self) -> None:
        """
        开始专注会话

        设置开始时间为当前UTC时间，标记会话为进行中状态。

        Example:
            >>> session = FocusSession(session_type=SessionType.FOCUS, user_id="user123")
            >>> session.start_session()
            >>> print(session.started_at)
            2023-12-01 10:30:00+00:00
        """
        self.started_at = datetime.now(timezone.utc)

    def complete_session(self) -> None:
        """
        完成专注会话

        设置结束时间为当前UTC时间，计算持续时间，标记会话为已完成。

        Example:
            >>> session = FocusSession(session_type=SessionType.FOCUS, user_id="user123")
            >>> session.start_session()
            >>> # 经过25分钟后
            >>> session.complete_session()
            >>> print(session.is_completed)
            True
        """
        self.ended_at = datetime.now(timezone.utc)
        self.is_completed = True

        # 如果有开始时间，自动计算持续时间
        if self.started_at and self.ended_at:
            # 确保时间对象都有时区信息
            started = self.started_at
            ended = self.ended_at

            # 如果开始时间没有时区，添加UTC时区
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if ended.tzinfo is None:
                ended = ended.replace(tzinfo=timezone.utc)

            duration = ended - started
            self.duration_minutes = int(duration.total_seconds() / 60)

    def get_actual_duration(self) -> Optional[int]:
        """
        获取实际持续时间

        基于开始和结束时间计算实际持续时间，优先于手动设置的duration_minutes。

        Returns:
            Optional[int]: 实际持续时间（分钟），如果缺少时间信息则返回None

        Example:
            >>> session = FocusSession(session_type=SessionType.FOCUS, user_id="user123")
            >>> session.start_session()
            >>> # 经过25分钟后
            >>> session.complete_session()
            >>> print(session.get_actual_duration())
            25
        """
        if self.started_at and self.ended_at:
            duration = self.ended_at - self.started_at
            return int(duration.total_seconds() / 60)
        return None

    def is_active(self) -> bool:
        """
        判断会话是否为活跃状态

        Returns:
            bool: 如果会话已开始但未结束返回True，否则返回False

        Example:
            >>> session = FocusSession(session_type=SessionType.FOCUS, user_id="user123")
            >>> session.start_session()
            >>> print(session.is_active())
            True
            >>> session.complete_session()
            >>> print(session.is_active())
            False
        """
        return self.started_at is not None and self.ended_at is None

    def is_focus_session(self) -> bool:
        """
        判断是否为专注会话

        Returns:
            bool: 如果会话类型为FOCUS返回True，否则返回False

        Example:
            >>> session = FocusSession(session_type=SessionType.FOCUS, user_id="user123")
            >>> print(session.is_focus_session())
            True
        """
        return self.session_type == SessionType.FOCUS

    def is_break_session(self) -> bool:
        """
        判断是否为休息会话

        Returns:
            bool: 如果会话类型为BREAK或LONG_BREAK返回True，否则返回False

        Example:
            >>> break_session = FocusSession(session_type=SessionType.BREAK, user_id="user123")
            >>> print(break_session.is_break_session())
            True
        """
        return self.session_type in [SessionType.BREAK, SessionType.LONG_BREAK]

    def get_efficiency_score(self) -> float:
        """
        计算专注效率评分

        基于计划时长和实际时长的比值计算效率评分，
        完美执行得1.0分，超时或提前结束会相应扣分。

        Returns:
            float: 效率评分，范围0.0-1.0

        Example:
            >>> session = FocusSession(
            ...     session_type=SessionType.FOCUS,
            ...     user_id="user123",
            ...     duration_minutes=25
            ... )
            >>> session.start_session()
            >>> # 经过25分钟后
            >>> session.complete_session()
            >>> print(session.get_efficiency_score())
            1.0
        """
        if not self.is_completed or not self.duration_minutes:
            return 0.0

        # 获取标准时长（硬编码，因为SessionType.get_default_duration方法不存在）
        standard_durations = {
            SessionType.FOCUS: 25,
            SessionType.BREAK: 5,
            SessionType.LONG_BREAK: 15
        }

        standard_duration = standard_durations.get(self.session_type, 25)
        if standard_duration == 0:
            return 1.0

        # 计算效率评分：实际时长与标准时长的比值
        efficiency = min(1.0, self.duration_minutes / standard_duration)
        return max(0.0, efficiency)


class FocusSessionBreak(BaseSQLModel, table=True):
    """
    专注会话休息模型

    记录专注会话期间的休息信息，包括休息类型、持续时间等。
    用于分析用户的休息模式和专注效果。

    Attributes:
        focus_session_id (str): 关联的专注会话ID，外键
        break_type (SessionType): 休息类型，区分短休息和长休息
        started_at (Optional[datetime]): 休息开始时间
        ended_at (Optional[datetime]): 休息结束时间
        duration_minutes (Optional[int]): 休息持续时间（分钟）
        is_skipped (bool): 是否跳过休息，默认False
        focus_session (FocusSession): 关联的专注会话，多对一关系
    """

    __tablename__ = "focus_session_breaks"

    # 关联字段
    focus_session_id: str = Field(
        foreign_key="focus_sessions.id",
        index=True,
        description="关联的专注会话ID，外键"
    )

    # 休息信息
    break_type: SessionType = Field(
        description="休息类型，区分短休息和长休息"
    )

    # 时间字段
    started_at: Optional[datetime] = Field(
        default=None,
        description="休息开始时间，UTC时区"
    )

    ended_at: Optional[datetime] = Field(
        default=None,
        description="休息结束时间，UTC时区"
    )

    duration_minutes: Optional[int] = Field(
        default=None,
        ge=0,
        le=60,  # 最长1小时休息
        description="休息持续时间（分钟）"
    )

    # 状态字段
    is_skipped: bool = Field(
        default=False,
        description="是否跳过休息"
    )

    def __repr__(self) -> str:
        """
        返回休息记录的字符串表示

        Returns:
            str: 休息记录的基本信息表示
        """
        return f"FocusSessionBreak(id={self.id})"

    def start_break(self) -> None:
        """开始休息"""
        self.started_at = datetime.now(timezone.utc)

    def end_break(self) -> None:
        """结束休息并计算持续时间"""
        self.ended_at = datetime.now(timezone.utc)
        if self.started_at and self.ended_at:
            # 确保时间对象都有时区信息
            started = self.started_at
            ended = self.ended_at

            # 如果开始时间没有时区，添加UTC时区
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if ended.tzinfo is None:
                ended = ended.replace(tzinfo=timezone.utc)

            duration = ended - started
            self.duration_minutes = int(duration.total_seconds() / 60)

    def skip_break(self) -> None:
        """跳过休息"""
        self.is_skipped = True
        self.ended_at = datetime.now(timezone.utc)


class FocusSessionTemplate(BaseSQLModel, table=True):
    """
    专注会话模板模型

    用户自定义的专注配置模板，支持不同的专注模式，
    如番茄钟、自定义专注方案等。

    Attributes:
        name (str): 模板名称，用户自定义
        description (Optional[str]): 模板描述，详细说明模板用途
        focus_duration (int): 专注时长（分钟）
        break_duration (int): 休息时长（分钟）
        long_break_duration (int): 长休息时长（分钟）
        sessions_until_long_break (int): 长休息前的专注次数
        is_default (bool): 是否为默认模板，默认False
        user_id (str): 用户ID，外键关联到User表
        user (User): 关联的用户，多对一关系
    """

    __tablename__ = "focus_session_templates"

    # 模板基本信息
    name: str = Field(
        max_length=100,
        description="模板名称，用户自定义"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="模板描述，详细说明模板用途"
    )

    # 时间配置
    focus_duration: int = Field(
        default=25,
        ge=1,
        le=180,
        description="专注时长（分钟），范围1-180分钟"
    )

    break_duration: int = Field(
        default=5,
        ge=1,
        le=30,
        description="休息时长（分钟），范围1-30分钟"
    )

    long_break_duration: int = Field(
        default=15,
        ge=1,
        le=60,
        description="长休息时长（分钟），范围1-60分钟"
    )

    # 配置参数
    sessions_until_long_break: int = Field(
        default=4,
        ge=2,
        le=10,
        description="长休息前的专注次数，范围2-10次"
    )

    # 状态字段
    is_default: bool = Field(
        default=False,
        description="是否为默认模板"
    )

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表，标识模板归属"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回模板的字符串表示

        Returns:
            str: 模板的基本信息表示
        """
        return f"FocusSessionTemplate(id={self.id})"

    def __str__(self) -> str:
        """
        返回模板友好的字符串表示

        Returns:
            str: 模板的名称表示
        """
        return self.name

    def is_pomodoro_template(self) -> bool:
        """
        判断是否为标准番茄钟模板

        Returns:
            bool: 如果符合标准番茄钟配置返回True，否则返回False

        Example:
            >>> template = FocusSessionTemplate(
            ...     name="番茄钟",
            ...     focus_duration=25,
            ...     break_duration=5,
            ...     long_break_duration=15,
            ...     sessions_until_long_break=4,
            ...     user_id="user123"
            ... )
            >>> print(template.is_pomodoro_template())
            True
        """
        return (
            self.focus_duration == 25 and
            self.break_duration == 5 and
            self.long_break_duration == 15 and
            self.sessions_until_long_break == 4
        )

    def get_total_cycle_time(self) -> int:
        """
        获取完整番茄钟周期的总时间

        计算一个完整番茄钟周期（专注+休息）的总时间。

        Returns:
            int: 总时间（分钟）

        Example:
            >>> template = FocusSessionTemplate(
            ...     name="番茄钟",
            ...     focus_duration=25,
            ...     break_duration=5,
            ...     user_id="user123"
            ... )
            >>> print(template.get_total_cycle_time())
            30  # 25分钟专注 + 5分钟休息
        """
        return self.focus_duration + self.break_duration

    def get_daily_focus_time(self, sessions: int = 8) -> int:
        """
        计算指定专注次数下的总专注时间

        Args:
            sessions (int): 专注次数，默认8次

        Returns:
            int: 总专注时间（分钟）

        Example:
            >>> template = FocusSessionTemplate(
            ...     name="番茄钟",
            ...     focus_duration=25,
            ...     user_id="user123"
            ... )
            >>> print(template.get_daily_focus_time(8))
            200  # 8次 * 25分钟
        """
        return sessions * self.focus_duration

    def reset_to_pomodoro_defaults(self) -> None:
        """
        重置为标准番茄钟配置

        将模板设置重置为标准的番茄钟时间配置。

        Example:
            >>> template = FocusSessionTemplate(name="自定义模板", user_id="user123")
            >>> template.reset_to_pomodoro_defaults()
            >>> print(template.focus_duration)
            25
        """
        self.focus_duration = 25
        self.break_duration = 5
        self.long_break_duration = 15
        self.sessions_until_long_break = 4


# 导出所有专注系统模型
__all__ = [
    "FocusSession",
    "FocusSessionBreak",
    "FocusSessionTemplate"
]