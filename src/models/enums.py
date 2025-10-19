"""
数据模型枚举类型定义模块

本模块定义了TaKeKe应用中使用的所有枚举类型，包括：
- 任务状态相关的枚举
- 优先级相关的枚举
- 会话类型相关的枚举

设计原则：
1. 字符串枚举：所有枚举都继承自str和Enum，确保数据库兼容性
2. 语义化值：枚举值使用小写下划线格式，便于理解和维护
3. 类型安全：提供强类型检查，避免无效值
4. 序列化友好：支持JSON序列化和反序列化

使用示例：
    >>> task = Task(status=TaskStatus.IN_PROGRESS)
    >>> if task.status == TaskStatus.COMPLETED:
    ...     print("任务已完成")

    >>> priority = PriorityLevel.HIGH
    >>> print(f"优先级: {priority}")  # 输出: 优先级: high
"""

from enum import Enum


class TaskStatus(str, Enum):
    """
    任务状态枚举

    定义任务在生命周期中的各种状态，用于跟踪任务的进展情况。
    所有状态都是互斥的，任务在任何时刻只能处于一种状态。

    状态流转规则：
    - PENDING -> IN_PROGRESS -> COMPLETED
    - PENDING/IN_PROGRESS -> CANCELLED
    - 任何状态 -> DELETED (软删除)

    Attributes:
        PENDING (str): 待处理状态，任务已创建但尚未开始
        IN_PROGRESS (str): 进行中状态，任务正在执行
        COMPLETED (str): 已完成状态，任务已成功完成
        CANCELLED (str): 已取消状态，任务被手动取消
        DELETED (str): 已删除状态，任务被软删除（逻辑删除）
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELETED = "deleted"

    def __str__(self) -> str:
        """
        返回枚举的字符串值

        Returns:
            str: 枚举的字符串值

        Example:
            >>> str(TaskStatus.PENDING)
            'pending'
        """
        return self.value

    @classmethod
    def get_active_statuses(cls) -> set["TaskStatus"]:
        """
        获取所有活跃状态（不包括已删除和已取消）

        Returns:
            set[TaskStatus]: 活跃状态集合

        Example:
            >>> active_statuses = TaskStatus.get_active_statuses()
            >>> TaskStatus.PENDING in active_statuses
            True
            >>> TaskStatus.DELETED in active_statuses
            False
        """
        return {cls.PENDING, cls.IN_PROGRESS, cls.COMPLETED}

    @classmethod
    def get_completed_statuses(cls) -> set["TaskStatus"]:
        """
        获取所有完成状态

        Returns:
            set[TaskStatus]: 完成状态集合

        Example:
            >>> completed_statuses = TaskStatus.get_completed_statuses()
            >>> TaskStatus.COMPLETED in completed_statuses
            True
            >>> TaskStatus.CANCELLED in completed_statuses
            True
        """
        return {cls.COMPLETED, cls.CANCELLED}

    def is_active(self) -> bool:
        """
        判断当前状态是否为活跃状态

        Returns:
            bool: 如果是活跃状态返回True，否则返回False

        Example:
            >>> TaskStatus.PENDING.is_active()
            True
            >>> TaskStatus.DELETED.is_active()
            False
        """
        return self in self.get_active_statuses()

    def is_completed(self) -> bool:
        """
        判断当前状态是否为完成状态

        Returns:
            bool: 如果是完成状态返回True，否则返回False

        Example:
            >>> TaskStatus.COMPLETED.is_completed()
            True
            >>> TaskStatus.IN_PROGRESS.is_completed()
            False
        """
        return self in self.get_completed_statuses()


class PriorityLevel(str, Enum):
    """
    优先级枚举

    定义任务的优先级级别，用于任务排序和重要性标识。
    采用三级优先级制度，简洁明了。

    优先级使用建议：
    - HIGH: 紧急重要任务，需要立即处理
    - MEDIUM: 重要但不紧急的任务，正常处理
    - LOW: 不重要或不紧急的任务，空闲时处理

    Attributes:
        LOW (str): 低优先级，次要任务
        MEDIUM (str): 中优先级，常规任务
        HIGH (str): 高优先级，重要任务
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __str__(self) -> str:
        """
        返回枚举的字符串值

        Returns:
            str: 枚举的字符串值

        Example:
            >>> str(PriorityLevel.HIGH)
            'high'
        """
        return self.value

    @classmethod
    def get_numeric_value(cls, priority: "PriorityLevel") -> int:
        """
        获取优先级的数值表示，用于排序比较

        Args:
            priority (PriorityLevel): 优先级枚举值

        Returns:
            int: 数值表示，数值越大优先级越高

        Raises:
            ValueError: 当传入无效的优先级时

        Example:
            >>> PriorityLevel.get_numeric_value(PriorityLevel.HIGH)
            3
            >>> PriorityLevel.get_numeric_value(PriorityLevel.LOW)
            1
        """
        priority_map = {
            cls.LOW: 1,
            cls.MEDIUM: 2,
            cls.HIGH: 3
        }

        if priority not in priority_map:
            raise ValueError(
                f"无效的优先级: {priority}. "
                f"有效的优先级包括: {list(cls)}"
            )

        return priority_map[priority]

    def is_higher_than(self, other: "PriorityLevel") -> bool:
        """
        比较当前优先级是否高于另一个优先级

        Args:
            other (PriorityLevel): 要比较的另一个优先级

        Returns:
            bool: 如果当前优先级更高返回True，否则返回False

        Example:
            >>> PriorityLevel.HIGH.is_higher_than(PriorityLevel.LOW)
            True
            >>> PriorityLevel.LOW.is_higher_than(PriorityLevel.HIGH)
            False
        """
        return self.get_numeric_value(self) > self.get_numeric_value(other)


class SessionType(str, Enum):
    """
    会话类型枚举

    定义专注会话的不同类型，基于番茄工作法设计。
    不同类型的会话有不同的默认时长和用途。

    会话类型说明：
    - FOCUS: 专注工作时段，通常25分钟
    - BREAK: 短休息时段，通常5分钟
    - LONG_BREAK: 长休息时段，通常15-30分钟

    Attributes:
        FOCUS (str): 专注工作会话
        BREAK (str): 短休息会话
        LONG_BREAK (str): 长休息会话
    """

    FOCUS = "focus"
    BREAK = "break"
    LONG_BREAK = "long_break"

    def __str__(self) -> str:
        """
        返回枚举的字符串值

        Returns:
            str: 枚举的字符串值

        Example:
            >>> str(SessionType.FOCUS)
            'focus'
        """
        return self.value

    @classmethod
    def get_default_duration(cls, session_type: "SessionType") -> int:
        """
        获取会话类型的默认时长（分钟）

        Args:
            session_type (SessionType): 会话类型

        Returns:
            int: 默认时长（分钟）

        Raises:
            ValueError: 当传入无效的会话类型时

        Example:
            >>> SessionType.get_default_duration(SessionType.FOCUS)
            25
            >>> SessionType.get_default_duration(SessionType.BREAK)
            5
        """
        duration_map = {
            cls.FOCUS: 25,        # 专注时段：25分钟
            cls.BREAK: 5,         # 短休息：5分钟
            cls.LONG_BREAK: 15    # 长休息：15分钟
        }

        if session_type not in duration_map:
            raise ValueError(
                f"无效的会话类型: {session_type}. "
                f"有效的会话类型包括: {list(cls)}"
            )

        return duration_map[session_type]

    def is_break_session(self) -> bool:
        """
        判断是否为休息类型的会话

        Returns:
            bool: 如果是休息会话返回True，否则返回False

        Example:
            >>> SessionType.BREAK.is_break_session()
            True
            >>> SessionType.LONG_BREAK.is_break_session()
            True
            >>> SessionType.FOCUS.is_break_session()
            False
        """
        return self in {self.BREAK, self.LONG_BREAK}

    def is_work_session(self) -> bool:
        """
        判断是否为工作类型的会话

        Returns:
            bool: 如果是工作会话返回True，否则返回False

        Example:
            >>> SessionType.FOCUS.is_work_session()
            True
            >>> SessionType.BREAK.is_work_session()
            False
        """
        return self == self.FOCUS


class RewardType(str, Enum):
    """
    奖励类型枚举

    定义应用中不同类型的奖励，用于激励用户完成专注任务和达成目标。
    每种奖励类型都有不同的获取条件和展示方式。

    Attributes:
        BADGE (str): 徽章奖励，用户成就的视觉标识
        AVATAR_FRAME (str): 头像框奖励，个性化用户头像展示
        TITLE (str): 称号奖励，用户在社区中的荣誉称号
        THEME (str): 主题奖励，应用界面主题定制
        ACHIEVEMENT (str): 成就奖励，特殊里程碑的记录
        CUSTOM (str): 自定义奖励，用户个性化配置
    """

    BADGE = "badge"
    AVATAR_FRAME = "avatar_frame"
    TITLE = "title"
    THEME = "theme"
    ACHIEVEMENT = "achievement"
    CUSTOM = "custom"


class RewardStatus(str, Enum):
    """
    奖励状态枚举

    定义奖励在用户账户中的状态，用于跟踪奖励的获取和使用情况。

    Attributes:
        LOCKED (str): 未解锁，奖励不可用
        AVAILABLE (str): 可用，奖励已解锁但未使用
        EQUIPPED (str): 已装备，奖励正在使用中
        EXPIRED (str): 已过期，奖励有效期已过
    """

    LOCKED = "locked"
    AVAILABLE = "available"
    EQUIPPED = "equipped"
    EXPIRED = "expired"


class TransactionType(str, Enum):
    """
    交易类型枚举

    定义用户碎片和积分的各种交易类型，用于记录和分析用户行为。

    Attributes:
        EARN (str): 赚得，通过完成任务获得
        SPEND (str): 消费，用于兑换奖励
        REFUND (str): 退款，奖励退还返还
        BONUS (str): 奖励，额外赠送
        PENALTY (str): 扣除，违规操作扣除
    """

    EARN = "earn"
    SPEND = "spend"
    REFUND = "refund"
    BONUS = "bonus"
    PENALTY = "penalty"


class ChatMode(str, Enum):
    """
    聊天模式枚举

    定义不同的AI聊天助手模式，每种模式都有特定的行为和回应风格。

    Attributes:
        GENERAL (str): 通用对话模式，提供一般性帮助和对话
        TASK_ASSISTANT (str): 任务助手模式，专注于任务管理和执行建议
        PRODUCTIVITY_COACH (str): 生产力教练模式，提供效率提升指导
        FOCUS_GUIDE (str): 专注指导模式，帮助用户保持专注和避免分心
    """

    GENERAL = "general"
    TASK_ASSISTANT = "task_assistant"
    PRODUCTIVITY_COACH = "productivity_coach"
    FOCUS_GUIDE = "focus_guide"

    def __str__(self) -> str:
        """返回枚举的字符串值"""
        return self.value

    @classmethod
    def get_description(cls, mode: "ChatMode") -> str:
        """
        获取聊天模式的描述

        Args:
            mode: 聊天模式

        Returns:
            str: 模式描述
        """
        descriptions = {
            cls.GENERAL: "通用AI助手，可以帮助处理各种问题和任务",
            cls.TASK_ASSISTANT: "任务管理助手，专注于任务创建、管理和完成建议",
            cls.PRODUCTIVITY_COACH: "生产力教练，提供工作效率提升和习惯养成建议",
            cls.FOCUS_GUIDE: "专注指导师，帮助提高专注力和管理干扰因素"
        }
        return descriptions.get(mode, "未知模式")


class MessageRole(str, Enum):
    """
    消息角色枚举

    定义聊天消息中的不同角色类型。

    Attributes:
        USER (str): 用户消息
        ASSISTANT (str): AI助手消息
        SYSTEM (str): 系统消息
        TOOL (str): 工具调用消息
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

    def __str__(self) -> str:
        """返回枚举的字符串值"""
        return self.value


class SessionStatus(str, Enum):
    """
    会话状态枚举

    定义聊天会话的生命周期状态。

    Attributes:
        ACTIVE (str): 活跃状态，会话正在进行中
        PAUSED (str): 暂停状态，会话暂时停止
        COMPLETED (str): 已完成状态，会话正常结束
        ARCHIVED (str): 已归档状态，会话被归档保存
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        """返回枚举的字符串值"""
        return self.value

    def is_active(self) -> bool:
        """判断会话是否为活跃状态"""
        return self == self.ACTIVE

    def is_ended(self) -> bool:
        """判断会话是否已结束"""
        return self in {self.COMPLETED, self.ARCHIVED}


# 导出所有枚举类型，便于外部导入
__all__ = [
    "TaskStatus",
    "PriorityLevel",
    "SessionType",
    "RewardType",
    "RewardStatus",
    "TransactionType",
    "ChatMode",
    "MessageRole",
    "SessionStatus"
]