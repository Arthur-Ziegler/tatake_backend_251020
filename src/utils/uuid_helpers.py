"""UUID类型处理工具集

提供统一的UUID和字符串类型转换功能，解决全系统UUID类型混用问题。
遵循1.4.2 OpenSpec设计的UUID类型系统规范。

作者：TaKeKe团队
版本：1.4.2
日期：2025-10-25
"""

from uuid import UUID
from typing import Union, Optional, List, Any


def ensure_uuid(value: Union[str, UUID, None]) -> Optional[UUID]:
    """
    确保返回UUID对象，兼容str和UUID输入

    Args:
        value: 可以是str、UUID或None的值

    Returns:
        Optional[UUID]: UUID对象或None

    Examples:
        >>> ensure_uuid("550e8400-e29b-41d4-a716-446655440000")
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> ensure_uuid(UUID('550e8400-e29b-41d4-a716-446655440000'))
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> ensure_uuid(None) is None
        True
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid UUID value: {value}") from e


def ensure_str(value: Union[str, UUID, None]) -> Optional[str]:
    """
    确保返回字符串，兼容str和UUID输入

    Args:
        value: 可以是str、UUID或None的值

    Returns:
        Optional[str]: 字符串或None

    Examples:
        >>> ensure_str("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'

        >>> ensure_str(UUID('550e8400-e29b-41d4-a716-446655440000'))
        '550e8400-e29b-41d4-a716-446655440000'

        >>> ensure_str(None) is None
        True
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def uuid_list_to_str(uuids: List[Union[str, UUID]]) -> List[str]:
    """
    UUID列表转字符串列表

    Args:
        uuids: UUID或字符串的列表

    Returns:
        List[str]: 字符串列表

    Examples:
        >>> uuid_list_to_str([
        ...     UUID('550e8400-e29b-41d4-a716-446655440000'),
        ...     "550e8400-e29b-41d4-a716-446655440001",
        ... ])
        ['550e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440001']
    """
    return [ensure_str(u) for u in uuids]


def str_list_to_uuid(strings: List[str]) -> List[UUID]:
    """
    字符串列表转UUID列表

    Args:
        strings: 字符串列表

    Returns:
        List[UUID]: UUID列表

    Examples:
        >>> str_list_to_uuid([
        ...     "550e8400-e29b-41d4-a716-446655440000",
        ...     "550e8400-e29b-41d4-a716-446655440001",
        ... ])
        [UUID('550e8400-e29b-41d4-a716-446655440000'), UUID('550e8400-e29b-41d4-a716-446655440001')]
    """
    return [ensure_uuid(s) for s in strings if s]  # 过滤None值


def safe_uuid_str(uuid_obj: UUID) -> str:
    """
    安全地将UUID对象转换为字符串，不会抛出异常

    Args:
        uuid_obj: UUID对象

    Returns:
        str: UUID字符串表示
    """
    return str(uuid_obj)


def normalize_uuid_for_db(value: Union[str, UUID, None]) -> Optional[str]:
    """
    为数据库存储规范化UUID（转为字符串）

    Args:
        value: 输入值

    Returns:
        Optional[str]: 适用于数据库存储的字符串
    """
    return ensure_str(value)


def normalize_uuid_for_api(value: Union[str, UUID, None]) -> Optional[UUID]:
    """
    为API处理规范化UUID（转为UUID对象）

    Args:
        value: 输入值

    Returns:
        Optional[UUID]: 适用于API处理的UUID对象
    """
    return ensure_uuid(value)


def validate_uuid_string(uuid_str: str) -> bool:
    """
    验证字符串是否为有效的UUID

    Args:
        uuid_str: UUID字符串

    Returns:
        bool: 是否为有效UUID

    Examples:
        >>> validate_uuid_string("550e8400-e29b-41d4-a716-446655440000")
        True

        >>> validate_uuid_string("invalid-uuid")
        False
    """
    try:
        UUID(uuid_str)
        return True
    except (ValueError, TypeError):
        return False


def extract_uuid_from_mixed(mixed_value: Any) -> Optional[UUID]:
    """
    从混合类型值中提取UUID，处理各种可能的输入格式

    Args:
        mixed_value: 可能包含UUID的任意类型

    Returns:
        Optional[UUID]: 提取的UUID对象

    Examples:
        >>> extract_uuid_from_mixed("550e8400-e29b-41d4-a716-446655440000")
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> extract_uuid_from_mixed({"user_id": "550e8400-e29b-41d4-a716-446655440000"})
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> extract_uuid_from_mixed(None) is None
        True
    """
    if mixed_value is None:
        return None
    if isinstance(mixed_value, UUID):
        return mixed_value
    if isinstance(mixed_value, str) and validate_uuid_string(mixed_value):
        return UUID(mixed_value)
    if isinstance(mixed_value, dict):
        # 常见模式：{"user_id": "uuid"} 或 {"id": "uuid"}
        for key in ["user_id", "id", "task_id", "parent_id"]:
            if key in mixed_value:
                uuid_val = mixed_value[key]
                if isinstance(uuid_val, UUID):
                    return uuid_val
                if isinstance(uuid_val, str) and validate_uuid_string(uuid_val):
                    return UUID(uuid_val)
    return None


class UUIDConverter:
    """
    UUID转换器类，提供面向对象的UUID处理接口
    """

    @staticmethod
    def to_db_format(value: Union[str, UUID, None]) -> Optional[str]:
        """转换为数据库格式（字符串）"""
        return normalize_uuid_for_db(value)

    @staticmethod
    def to_api_format(value: Union[str, UUID, None]) -> Optional[UUID]:
        """转换为API格式（UUID对象）"""
        return normalize_uuid_for_api(value)

    @staticmethod
    def to_str(value: Union[str, UUID, None]) -> Optional[str]:
        """转换为字符串格式"""
        return ensure_str(value)

    @staticmethod
    def to_uuid(value: Union[str, UUID, None]) -> Optional[UUID]:
        """转换为UUID对象格式"""
        return ensure_uuid(value)


# 便捷实例
uuid_converter = UUIDConverter()