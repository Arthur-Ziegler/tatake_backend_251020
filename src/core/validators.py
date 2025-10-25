"""
零Bug测试体系 - 业务规则验证器

提供严格的业务规则验证，确保所有业务逻辑都有明确的约束。

设计原则：
1. 规则即代码：每个业务规则都有对应的验证器
2. 快速失败：验证失败立即抛出明确异常
3. 规则组合：支持复杂规则的组合验证
4. 规则文档：每个验证器都是业务规则的文档
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable, Type
from datetime import datetime, timezone, timedelta

from .types import (
    TaskTitle, TaskDescription, TaskStatus, TaskPriority, Percentage,
    UserId, TaskId, UTCDateTime, WeChatOpenId
)

# =============================================================================
# 异常定义
# =============================================================================

class ValidationError(Exception):
    """验证错误基类"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.message = message

    def __str__(self) -> str:
        if self.field:
            return f"{self.field}: {self.message}"
        return self.message

class BusinessRuleViolationError(ValidationError):
    """业务规则违反错误"""
    pass

class DataConsistencyError(ValidationError):
    """数据一致性错误"""
    pass

class PermissionError(ValidationError):
    """权限错误"""
    pass

# =============================================================================
# 验证器基类
# =============================================================================

class BaseValidator:
    """验证器基类"""

    def __init__(self, field_name: str = None):
        self.field_name = field_name

    def validate(self, value: Any) -> Any:
        """验证方法 - 子类必须实现"""
        raise NotImplementedError("子类必须实现validate方法")

    def _raise_error(self, message: str, value: Any = None) -> None:
        """抛出验证错误"""
        raise ValidationError(message, self.field_name, value)

    def __call__(self, value: Any) -> Any:
        """使验证器可调用"""
        return self.validate(value)

# =============================================================================
# 基础验证器
# =============================================================================

class RequiredValidator(BaseValidator):
    """必填字段验证器"""

    def __init__(self, field_name: str = None):
        super().__init__(field_name)
        self.field_name = field_name or "字段"

    def validate(self, value: Any) -> Any:
        if value is None:
            self._raise_error(f"{self.field_name}是必填的")

        if isinstance(value, str) and not value.strip():
            self._raise_error(f"{self.field_name}不能为空字符串")

        return value

class TypeValidator(BaseValidator):
    """类型验证器"""

    def __init__(self, expected_type: Type, field_name: str = None):
        super().__init__(field_name)
        self.expected_type = expected_type

    def validate(self, value: Any) -> Any:
        if not isinstance(value, self.expected_type):
            type_name = self.expected_type.__name__
            self._raise_error(f"期望类型 {type_name}，实际类型 {type(value).__name__}", value)
        return value

class RangeValidator(BaseValidator):
    """范围验证器"""

    def __init__(self, min_value: Any = None, max_value: Any = None, field_name: str = None):
        super().__init__(field_name)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> Any:
        if self.min_value is not None and value < self.min_value:
            self._raise_error(f"值不能小于 {self.min_value}，当前值: {value}", value)

        if self.max_value is not None and value > self.max_value:
            self._raise_error(f"值不能大于 {self.max_value}，当前值: {value}", value)

        return value

class RegexValidator(BaseValidator):
    """正则表达式验证器"""

    def __init__(self, pattern: str, message: str = None, field_name: str = None):
        super().__init__(field_name)
        self.pattern = pattern
        self.message = message or f"格式不正确，应符合: {pattern}"

    def validate(self, value: str) -> str:
        import re
        if not re.match(self.pattern, value):
            self._raise_error(self.message, value)
        return value

# =============================================================================
# 任务相关验证器
# =============================================================================

class TaskTitleValidator(BaseValidator):
    """任务标题验证器"""

    def __init__(self):
        super().__init__("任务标题")

    def validate(self, value: str) -> TaskTitle:
        try:
            return TaskTitle(value)
        except (TypeError, ValueError) as e:
            self._raise_error(str(e), value)

class TaskDescriptionValidator(BaseValidator):
    """任务描述验证器"""

    def __init__(self):
        super().__init__("任务描述")

    def validate(self, value: Optional[str]) -> TaskDescription:
        try:
            return TaskDescription(value)
        except (TypeError, ValueError) as e:
            self._raise_error(str(e), value)

class TaskStatusValidator(BaseValidator):
    """任务状态验证器"""

    def __init__(self):
        super().__init__("任务状态")

    def validate(self, value: str) -> TaskStatus:
        try:
            return TaskStatus(value)
        except (TypeError, ValueError) as e:
            self._raise_error(str(e), value)

class TaskStatusTransitionValidator(BaseValidator):
    """任务状态转换验证器"""

    def __init__(self, current_status: TaskStatus):
        super().__init__("任务状态转换")
        self.current_status = current_status

    def validate(self, target_status: TaskStatus) -> TaskStatus:
        if not self.current_status.can_transition_to(target_status):
            self._raise_error(
                f"不能从状态 {self.current_status} 转换到 {target_status}",
                target_status.value
            )
        return target_status

class TaskPriorityValidator(BaseValidator):
    """任务优先级验证器"""

    def __init__(self):
        super().__init__("任务优先级")

    def validate(self, value: str) -> TaskPriority:
        try:
            return TaskPriority(value)
        except (TypeError, ValueError) as e:
            self._raise_error(str(e), value)

class TaskCompletionValidator(BaseValidator):
    """任务完成百分比验证器"""

    def __init__(self):
        super().__init__("任务完成百分比")

    def validate(self, value: Union[int, float]) -> Percentage:
        try:
            return Percentage(float(value))
        except (TypeError, ValueError) as e:
            self._raise_error(str(e), value)

# =============================================================================
# 用户相关验证器
# =============================================================================

class UserIdValidator(BaseValidator):
    """用户ID验证器"""

    def __init__(self):
        super().__init__("用户ID")

    def validate(self, value: str) -> UserId:
        try:
            return UserId(value)
        except (TypeError, ValueError) as e:
            self._raise_error(str(e), value)

class WeChatOpenIdValidator(BaseValidator):
    """微信OpenID验证器"""

    def __init__(self):
        super().__init__("微信OpenID")

    def validate(self, value: str) -> WeChatOpenId:
        try:
            return WeChatOpenId(value)
        except (TypeError, ValueError) as e:
            self._raise_error(str(e), value)

# =============================================================================
# 业务规则验证器
# =============================================================================

class TaskBusinessRuleValidator(BaseValidator):
    """任务业务规则验证器"""

    def __init__(self):
        super().__init__("任务业务规则")

    def validate_task_creation(self, user_id: UserId, title: TaskTitle) -> None:
        """验证任务创建规则"""
        # 规则1: 用户必须有有效的身份
        if not user_id:
            self._raise_error("用户ID不能为空")

        # 规则2: 任务标题不能重复（同用户下）
        # 这里需要查询数据库，暂时跳过实际查询
        pass

    def validate_task_deletion(self, task: Any, user_id: UserId) -> None:
        """验证任务删除规则"""
        # 规则1: 只能删除自己的任务
        if task.user_id != user_id:
            self._raise_error("只能删除自己的任务")

        # 规则2: 已完成的任务不能删除（只能归档）
        if task.status == TaskStatus.COMPLETED:
            self._raise_error("已完成的任务不能删除，请使用归档功能")

        # 规则3: 有子任务的父任务不能删除
        # 这里需要查询数据库，暂时跳过
        pass

    def validate_task_completion(self, task: Any) -> None:
        """验证任务完成规则"""
        # 规则1: 只有进行中的任务才能标记为完成
        if task.status != TaskStatus.IN_PROGRESS:
            self._raise_error(f"只有进行中的任务才能完成，当前状态: {task.status}")

        # 规则2: 完成时间必须在创建时间之后
        now = UTCDateTime.now()
        if now.value < task.created_at:
            self._raise_error("完成时间不能早于创建时间")

# =============================================================================
# 复合验证器
# =============================================================================

class CompositeValidator(BaseValidator):
    """复合验证器 - 支持多个验证器组合"""

    def __init__(self, validators: List[BaseValidator], field_name: str = None):
        super().__init__(field_name)
        self.validators = validators

    def validate(self, value: Any) -> Any:
        """依次执行所有验证器"""
        result = value
        for validator in self.validators:
            result = validator.validate(result)
        return result

class ConditionalValidator(BaseValidator):
    """条件验证器 - 根据条件执行不同验证"""

    def __init__(self, condition: Callable[[Any], bool],
                 true_validator: BaseValidator,
                 false_validator: BaseValidator = None):
        super().__init__()
        self.condition = condition
        self.true_validator = true_validator
        self.false_validator = false_validator

    def validate(self, value: Any) -> Any:
        if self.condition(value):
            return self.true_validator.validate(value)
        elif self.false_validator:
            return self.false_validator.validate(value)
        return value

# =============================================================================
# 验证器工厂
# =============================================================================

class ValidatorFactory:
    """验证器工厂 - 提供常用验证器的快速创建"""

    @staticmethod
    def task_title() -> TaskTitleValidator:
        """创建任务标题验证器"""
        return TaskTitleValidator()

    @staticmethod
    def task_description() -> TaskDescriptionValidator:
        """创建任务描述验证器"""
        return TaskDescriptionValidator()

    @staticmethod
    def task_status(current_status: TaskStatus = None) -> BaseValidator:
        """创建任务状态验证器"""
        if current_status:
            return TaskStatusTransitionValidator(current_status)
        return TaskStatusValidator()

    @staticmethod
    def task_priority() -> TaskPriorityValidator:
        """创建任务优先级验证器"""
        return TaskPriorityValidator()

    @staticmethod
    def task_completion() -> TaskCompletionValidator:
        """创建任务完成百分比验证器"""
        return TaskCompletionValidator()

    @staticmethod
    def user_id() -> UserIdValidator:
        """创建用户ID验证器"""
        return UserIdValidator()

    @staticmethod
    def wechat_openid() -> WeChatOpenIdValidator:
        """创建微信OpenID验证器"""
        return WeChatOpenIdValidator()

    @staticmethod
    def required_string(min_length: int = 1, max_length: int = 255,
                        field_name: str = "字符串") -> CompositeValidator:
        """创建必填字符串验证器"""
        return CompositeValidator([
            RequiredValidator(field_name),
            TypeValidator(str, field_name),
            RangeValidator(min_length, max_length, field_name)
        ], field_name)

# =============================================================================
# 导出的验证器
# =============================================================================

__all__ = [
    # 异常
    'ValidationError', 'BusinessRuleViolationError',
    'DataConsistencyError', 'PermissionError',

    # 基础验证器
    'BaseValidator', 'RequiredValidator', 'TypeValidator',
    'RangeValidator', 'RegexValidator',

    # 任务验证器
    'TaskTitleValidator', 'TaskDescriptionValidator',
    'TaskStatusValidator', 'TaskStatusTransitionValidator',
    'TaskPriorityValidator', 'TaskCompletionValidator',

    # 用户验证器
    'UserIdValidator', 'WeChatOpenIdValidator',

    # 业务验证器
    'TaskBusinessRuleValidator',

    # 复合验证器
    'CompositeValidator', 'ConditionalValidator',

    # 工厂类
    'ValidatorFactory',
]