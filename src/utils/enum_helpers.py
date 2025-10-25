"""枚举类型处理工具集

提供统一的枚举和字符串类型转换功能，解决SQLite不支持Python枚举的问题。
遵循与UUID helpers相同的设计模式。

作者：TaKeKe团队
版本：1.0.0
日期：2025-10-26
"""

from typing import Union, Optional, Any, Type
from enum import Enum


def ensure_enum_value(value: Union[str, Enum, None], enum_class: Type) -> Optional[Union[Enum, str]]:
    """
    确保返回枚举对象，兼容str和Enum输入
    支持真正的Enum类和简单的常量类

    Args:
        value: 可以是str、Enum或None的值
        enum_class: 目标枚举类或常量类

    Returns:
        Optional[Union[Enum, str]]: 枚举对象或字符串常量

    Examples:
        >>> from src.domains.task.models_schema import TaskStatusConst
        >>> ensure_enum_value("pending", TaskStatusConst)
        'pending'

        >>> ensure_enum_value(TaskStatusConst.PENDING, TaskStatusConst)
        'pending'
    """
    if value is None:
        return None

    # 如果已经是enum_class的实例，直接返回
    if hasattr(value, '__class__') and value.__class__ == enum_class:
        return value

    if isinstance(value, str):
        # 检查是否是真正的Enum类
        if hasattr(enum_class, '__members__'):  # 真正的Enum类
            try:
                # 将字符串转换为对应的枚举值
                return enum_class(value.upper())
            except ValueError:
                # 如果直接转换失败，尝试遍历枚举值
                for enum_val in enum_class:
                    if hasattr(enum_val, 'value') and enum_val.value == value:
                        return enum_val
                raise ValueError(f"Invalid {enum_class.__name__} value: {value}")
        else:
            # 简单的常量类，直接验证值是否有效
            if hasattr(enum_class, '__dict__'):
                valid_values = [v for k, v in enum_class.__dict__.items()
                             if not k.startswith('_') and isinstance(v, str)]
                if value in valid_values:
                    return value
                raise ValueError(f"Invalid {enum_class.__name__} value: {value}. Valid values: {valid_values}")
            else:
                # 如果无法验证，直接返回字符串
                return value

    raise ValueError(f"Invalid {enum_class.__name__} value type: {type(value)}")


def ensure_enum_str(value: Union[str, Enum, None]) -> Optional[str]:
    """
    确保返回字符串，兼容str和Enum输入

    Args:
        value: 可以是str、Enum或None的值

    Returns:
        Optional[str]: 字符串或None

    Examples:
        >>> from src.domains.task.models import TaskStatusConst
        >>> ensure_enum_str(TaskStatusConst.PENDING)
        'pending'

        >>> ensure_enum_str("pending")
        'pending'
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Enum):
        return value.value
    raise ValueError(f"Invalid enum value type: {type(value)}")


def normalize_enum_for_db(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[str]:
    """
    为数据库存储规范化枚举（转为字符串）

    Args:
        value: 输入值
        enum_class: 目标枚举类

    Returns:
        Optional[str]: 适用于数据库存储的字符串
    """
    if value is None:
        return None
    if isinstance(value, str):
        # 验证字符串是否为有效的枚举值
        ensure_enum_value(value, enum_class)
        return value
    if isinstance(value, enum_class):
        return value.value
    raise ValueError(f"Invalid {enum_class.__name__} value: {value}")


def normalize_enum_for_api(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[Enum]:
    """
    为API处理规范化枚举（转为Enum对象）

    Args:
        value: 输入值
        enum_class: 目标枚举类

    Returns:
        Optional[Enum]: 适用于API处理的枚举对象
    """
    return ensure_enum_value(value, enum_class)


def validate_enum_string(enum_str: str, enum_class: Type[Enum]) -> bool:
    """
    验证字符串是否为有效的枚举值

    Args:
        enum_str: 枚举字符串
        enum_class: 枚举类

    Returns:
        bool: 是否为有效枚举值

    Examples:
        >>> from src.domains.task.models import TaskStatusConst
        >>> validate_enum_string("pending", TaskStatusConst)
        True

        >>> validate_enum_string("invalid", TaskStatusConst)
        False
    """
    try:
        ensure_enum_value(enum_str, enum_class)
        return True
    except ValueError:
        return False


class EnumConverter:
    """
    枚举转换器类，提供面向对象的枚举处理接口
    """

    @staticmethod
    def to_db_format(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[str]:
        """转换为数据库格式（字符串）"""
        return normalize_enum_for_db(value, enum_class)

    @staticmethod
    def to_api_format(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[Enum]:
        """转换为API格式（枚举对象）"""
        return normalize_enum_for_api(value, enum_class)

    @staticmethod
    def to_str(value: Union[str, Enum, None]) -> Optional[str]:
        """转换为字符串格式"""
        return ensure_enum_str(value)

    @staticmethod
    def to_enum(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[Enum]:
        """转换为枚举对象格式"""
        return ensure_enum_value(value, enum_class)


# 便捷实例
enum_converter = EnumConverter()