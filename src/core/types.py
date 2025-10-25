"""
零Bug测试体系 - 绝对类型安全系统

提供严格的数据类型定义，确保运行时类型安全。

设计原则：
1. 类型即约束：类型本身包含了业务规则
2. 零容忍：任何类型错误立即失败
3. 明确性：类型名称即是业务含义
4. 不可变性：一经创建，不可修改
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import NewType, Optional, Literal, Final, Union, Any
from enum import Enum
import re
import uuid
from datetime import datetime, timezone

# =============================================================================
# 基础严格类型
# =============================================================================

# 原子类型 - 不可修改的基础类型
UserId = NewType('UserId', str)
TaskId = NewType('TaskId', str)
RewardId = NewType('RewardId', str)
Token = NewType('Token', str)

# 验证过的字符串类型
@dataclass(frozen=True)
class ValidatedString:
    """经过验证的字符串基类"""
    value: str
    min_length: int
    max_length: int
    pattern: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.value, str):
            raise TypeError(f"{self.__class__.__name__} 必须是字符串")

        if len(self.value) < self.min_length:
            raise ValueError(f"{self.__class__.__name__} 长度不能少于 {self.min_length} 字符")

        if len(self.value) > self.max_length:
            raise ValueError(f"{self.__class__.__name__} 长度不能超过 {self.max_length} 字符")

        if self.pattern and not re.match(self.pattern, self.value):
            raise ValueError(f"{self.__class__.__name__} 格式不正确")

    def __str__(self) -> str:
        return self.value

# 具体的业务类型
@dataclass(frozen=True)
class TaskTitle(ValidatedString):
    """任务标题 - 1-100字符，不能为空"""
    def __init__(self, value: str):
        object.__setattr__(self, 'value', value.strip())
        object.__setattr__(self, 'min_length', 1)
        object.__setattr__(self, 'max_length', 100)
        object.__setattr__(self, 'pattern', None)
        super().__post_init__()

@dataclass(frozen=True)
class TaskDescription(ValidatedString):
    """任务描述 - 可选，最大1000字符"""
    def __init__(self, value: Optional[str] = None):
        if value is None:
            value = ""
        object.__setattr__(self, 'value', value.strip())
        object.__setattr__(self, 'min_length', 0)
        object.__setattr__(self, 'max_length', 1000)
        object.__setattr__(self, 'pattern', None)
        super().__post_init__()

@dataclass(frozen=True)
class WeChatOpenId(ValidatedString):
    """微信OpenID - 严格格式验证"""
    def __init__(self, value: str):
        object.__setattr__(self, 'value', value)
        object.__setattr__(self, 'min_length', 1)
        object.__setattr__(self, 'max_length', 100)
        object.__setattr__(self, 'pattern', r'^[a-zA-Z0-9_-]+$')
        super().__post_init__()

@dataclass(frozen=True)
class EmailAddress(ValidatedString):
    """邮箱地址 - 标准邮箱格式"""
    def __init__(self, value: str):
        object.__setattr__(self, 'value', value.lower().strip())
        object.__setattr__(self, 'min_length', 5)
        object.__setattr__(self, 'max_length', 255)
        object.__setattr__(self, 'pattern', r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        super().__post_init__()

# =============================================================================
# 严格枚举类型
# =============================================================================

class TaskStatus(str):
    """任务状态 - 继承自str的枚举，确保FastAPI序列化兼容性"""
    PENDING: Final = "pending"
    IN_PROGRESS: Final = "in_progress"
    COMPLETED: Final = "completed"

    # 允许的值集合
    _ALLOWED_VALUES: Final = frozenset([PENDING, IN_PROGRESS, COMPLETED])

    def __new__(cls, value: str):
        if value not in cls._ALLOWED_VALUES:
            raise ValueError(f"无效的任务状态: {value}. 允许的值: {cls._ALLOWED_VALUES}")
        # 返回str实例，但保持TaskStatus类型
        instance = super().__new__(cls, value)
        return instance

    def __init__(self, value: str):
        # str.__new__已经设置了值，这里不需要额外操作
        pass

    def __str__(self) -> str:
        return self

    @classmethod
    def from_string(cls, value: str) -> 'TaskStatus':
        """从字符串创建状态"""
        return cls(value)

    def can_transition_to(self, target_status: 'TaskStatus') -> bool:
        """检查状态转换是否合法"""
        valid_transitions = {
            self.PENDING: {self.IN_PROGRESS, self.COMPLETED},
            self.IN_PROGRESS: {self.COMPLETED, self.PENDING},
            self.COMPLETED: {self.PENDING}  # 可以重新开启
        }
        return target_status in valid_transitions.get(self, set())

    @property
    def value(self) -> str:
        """获取字符串值"""
        return str(self)

    # 确保JSON序列化时返回字符串
    def __repr__(self) -> str:
        return f"TaskStatus('{self}')"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        """Pydantic V2核心Schema生成方法"""
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(cls)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """Pydantic V2 JSON Schema生成方法"""
        return {
            "title": "TaskStatus",
            "type": "string",
            "enum": [cls.PENDING, cls.IN_PROGRESS, cls.COMPLETED],
            "description": "任务状态枚举：pending(待处理), in_progress(进行中), completed(已完成)"
        }

class TaskPriority(str):
    """任务优先级 - 继承自str的枚举，确保FastAPI序列化兼容性"""
    LOW: Final = "low"
    MEDIUM: Final = "medium"
    HIGH: Final = "high"

    _ALLOWED_VALUES: Final = frozenset([LOW, MEDIUM, HIGH])
    _LEVEL_MAP: Final = {
        LOW: 1,
        MEDIUM: 2,
        HIGH: 3
    }

    def __new__(cls, value: str):
        if value not in cls._ALLOWED_VALUES:
            raise ValueError(f"无效的任务优先级: {value}. 允许的值: {cls._ALLOWED_VALUES}")
        # 返回str实例，但保持TaskPriority类型
        instance = super().__new__(cls, value)
        return instance

    def __init__(self, value: str):
        # str.__new__已经设置了值，这里不需要额外操作
        pass

    def __str__(self) -> str:
        return self

    @classmethod
    def from_string(cls, value: str) -> 'TaskPriority':
        """从字符串创建优先级"""
        return cls(value)

    @property
    def level(self) -> int:
        """获取优先级数值"""
        return self._LEVEL_MAP[self]

    def is_higher_than(self, other: 'TaskPriority') -> bool:
        """检查是否比其他优先级更高"""
        return self.level > other.level

    @property
    def value(self) -> str:
        """获取字符串值"""
        return str(self)

    # 确保JSON序列化时返回字符串
    def __repr__(self) -> str:
        return f"TaskPriority('{self}')"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        """Pydantic V2核心Schema生成方法"""
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(cls)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """Pydantic V2 JSON Schema生成方法"""
        return {
            "title": "TaskPriority",
            "type": "string",
            "enum": [cls.LOW, cls.MEDIUM, cls.HIGH],
            "description": "任务优先级枚举：low(低), medium(中), high(高)"
        }

# =============================================================================
# 严格数值类型
# =============================================================================

@dataclass(frozen=True)
class Percentage:
    """百分比 - 0.0-100.0之间的数值"""
    value: float

    def __post_init__(self):
        if not isinstance(self.value, (int, float)):
            raise TypeError("百分比必须是数字")

        if not 0.0 <= self.value <= 100.0:
            raise ValueError(f"百分比必须在 0.0-100.0 之间，当前值: {self.value}")

        # 标准化为两位小数
        object.__setattr__(self, 'value', round(float(self.value), 2))

    def __str__(self) -> str:
        return f"{self.value}%"

    def is_complete(self) -> bool:
        """是否为100%完成"""
        return abs(self.value - 100.0) < 0.01

    @classmethod
    def from_float(cls, value: float) -> 'Percentage':
        """从浮点数创建百分比"""
        return cls(value)

    @classmethod
    def zero(cls) -> 'Percentage':
        """创建0%"""
        return cls(0.0)

    @classmethod
    def complete(cls) -> 'Percentage':
        """创建100%"""
        return cls(100.0)

@dataclass(frozen=True)
class PositiveInteger:
    """正整数 - 大于0的整数"""
    value: int

    def __post_init__(self):
        if not isinstance(self.value, int):
            raise TypeError("必须是整数")

        if self.value <= 0:
            raise ValueError(f"必须是正整数，当前值: {self.value}")

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value

# =============================================================================
# ID生成器
# =============================================================================

class IdGenerator:
    """严格的ID生成器 - 确保ID的唯一性和格式"""

    @staticmethod
    def generate_user_id() -> UserId:
        """生成用户ID"""
        return UserId(f"user_{uuid.uuid4().hex}")

    @staticmethod
    def generate_task_id() -> TaskId:
        """生成任务ID"""
        return TaskId(f"task_{uuid.uuid4().hex}")

    @staticmethod
    def generate_reward_id() -> RewardId:
        """生成奖励ID"""
        return RewardId(f"reward_{uuid.uuid4().hex}")

    @staticmethod
    def parse_id(id_string: str, prefix: str) -> str:
        """解析并验证ID格式"""
        if not isinstance(id_string, str):
            raise TypeError("ID必须是字符串")

        if not id_string.startswith(f"{prefix}_"):
            raise ValueError(f"ID格式错误，应以 {prefix}_ 开头: {id_string}")

        # 提取UUID部分
        uuid_part = id_string[len(f"{prefix}_"):]
        try:
            uuid.UUID(uuid_part)
            return id_string
        except ValueError:
            raise ValueError(f"ID包含无效的UUID: {id_string}")

# =============================================================================
# 时间类型
# =============================================================================

@dataclass(frozen=True)
class UTCDateTime:
    """UTC时间 - 统一使用UTC时间避免时区问题"""
    value: datetime

    def __post_init__(self):
        if not isinstance(self.value, datetime):
            raise TypeError("时间必须是datetime对象")

        if self.value.tzinfo is None:
            raise TypeError("时间必须包含时区信息")

        if self.value.tzinfo != timezone.utc:
            # 转换为UTC
            utc_time = self.value.astimezone(timezone.utc)
            object.__setattr__(self, 'value', utc_time)

    def __str__(self) -> str:
        return self.value.isoformat()

    @classmethod
    def now(cls) -> 'UTCDateTime':
        """获取当前UTC时间"""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_string(cls, iso_string: str) -> 'UTCDateTime':
        """从ISO字符串创建时间"""
        try:
            dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            return cls(dt)
        except ValueError as e:
            raise ValueError(f"时间格式错误: {iso_string}") from e

    def is_future(self) -> bool:
        """是否为未来时间"""
        return self.value > datetime.now(timezone.utc)

    def is_past(self) -> bool:
        """是否为过去时间"""
        return self.value < datetime.now(timezone.utc)

# =============================================================================
# 类型验证器
# =============================================================================

class TypeValidator:
    """类型验证器 - 提供严格的类型验证"""

    @staticmethod
    def validate_task_title(value: str) -> TaskTitle:
        """验证任务标题"""
        return TaskTitle(value)

    @staticmethod
    def validate_task_description(value: Optional[str]) -> TaskDescription:
        """验证任务描述"""
        return TaskDescription(value)

    @staticmethod
    def validate_task_status(value: str) -> TaskStatus:
        """验证任务状态"""
        return TaskStatus(value)

    @staticmethod
    def validate_task_priority(value: str) -> TaskPriority:
        """验证任务优先级"""
        return TaskPriority(value)

    @staticmethod
    def validate_percentage(value: Union[int, float]) -> Percentage:
        """验证百分比"""
        return Percentage(float(value))

    @staticmethod
    def validate_user_id(value: str) -> UserId:
        """验证用户ID"""
        return IdGenerator.parse_id(value, "user")

    @staticmethod
    def validate_task_id(value: str) -> TaskId:
        """验证任务ID"""
        return IdGenerator.parse_id(value, "task")

# =============================================================================
# 导出的类型
# =============================================================================

__all__ = [
    # 基础类型
    'UserId', 'TaskId', 'RewardId', 'Token',

    # 字符串类型
    'TaskTitle', 'TaskDescription', 'WeChatOpenId', 'EmailAddress',

    # 枚举类型
    'TaskStatus', 'TaskPriority',

    # 数值类型
    'Percentage', 'PositiveInteger',

    # 时间类型
    'UTCDateTime',

    # 工具类
    'IdGenerator', 'TypeValidator',
]