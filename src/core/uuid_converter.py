"""
UUID类型转换器

提供统一的UUID对象和字符串转换功能，确保整个系统的类型一致性。
这个转换器将在数据访问层使用，保证服务层可以统一使用UUID对象。

设计原则：
1. 类型安全：确保输入输出的类型正确性
2. 性能优化：避免重复的转换操作
3. 错误处理：提供详细的错误信息
4. 批量支持：支持批量转换操作
"""

import logging
from typing import Union, List, Optional, Any
from uuid import UUID, uuid4
import re

logger = logging.getLogger(__name__)


class UUIDConverter:
    """
    UUID类型转换器

    提供UUID对象和字符串之间的双向转换功能，
    确保数据层和服务层之间的类型一致性。
    """

    # UUID字符串格式的正则表达式
    UUID_PATTERN = re.compile(
        r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    )

    @classmethod
    def to_string(cls, uuid_obj: UUID) -> str:
        """
        将UUID对象转换为字符串

        Args:
            uuid_obj: UUID对象

        Returns:
            str: UUID字符串格式

        Raises:
            TypeError: 当输入不是UUID对象时
        """
        if not isinstance(uuid_obj, UUID):
            raise TypeError(f"Expected UUID object, got {type(uuid_obj)}")

        return str(uuid_obj)

    @classmethod
    def to_uuid(cls, uuid_str: str) -> UUID:
        """
        将字符串转换为UUID对象

        Args:
            uuid_str: UUID字符串格式

        Returns:
            UUID: UUID对象

        Raises:
            TypeError: 当输入不是字符串时
            ValueError: 当字符串格式不正确时
        """
        if not isinstance(uuid_str, str):
            raise TypeError(f"Expected string, got {type(uuid_str)}")

        if not cls.UUID_PATTERN.match(uuid_str):
            raise ValueError(f"Invalid UUID string format: {uuid_str}")

        try:
            return UUID(uuid_str)
        except Exception as e:
            raise ValueError(f"Failed to convert string to UUID: {uuid_str}, error: {e}")

    @classmethod
    def ensure_string(cls, value: Union[UUID, str, None]) -> Optional[str]:
        """
        确保值是字符串格式

        智能转换：如果是UUID对象则转换为字符串，如果是字符串则验证格式，如果是None则返回None。

        Args:
            value: UUID对象、字符串或None

        Returns:
            Optional[str]: UUID字符串格式或None

        Raises:
            TypeError: 当值类型无效时
            ValueError: 当字符串格式不正确时
        """
        if value is None:
            return None
        elif isinstance(value, UUID):
            return cls.to_string(value)
        elif isinstance(value, str):
            # 验证字符串格式是否正确
            if not cls.UUID_PATTERN.match(value):
                raise ValueError(f"Invalid UUID string format: {value}")
            return value
        else:
            raise TypeError(f"Expected UUID, string, or None, got {type(value)}")

    @classmethod
    def ensure_uuid(cls, value: Union[UUID, str, None]) -> Optional[UUID]:
        """
        确保值是UUID对象

        智能转换：如果是字符串则转换为UUID对象，如果是UUID对象则直接返回，如果是None则返回None。

        Args:
            value: UUID对象、字符串或None

        Returns:
            Optional[UUID]: UUID对象或None

        Raises:
            TypeError: 当值类型无效时
            ValueError: 当字符串格式不正确时
        """
        if value is None:
            return None
        elif isinstance(value, UUID):
            return value
        elif isinstance(value, str):
            return cls.to_uuid(value)
        else:
            raise TypeError(f"Expected UUID, string, or None, got {type(value)}")

    @classmethod
    def batch_to_string(cls, uuid_list: List[UUID]) -> List[str]:
        """
        批量将UUID对象转换为字符串

        Args:
            uuid_list: UUID对象列表

        Returns:
            List[str]: UUID字符串列表
        """
        if not isinstance(uuid_list, list):
            raise TypeError(f"Expected list, got {type(uuid_list)}")

        return [cls.to_string(uuid_obj) for uuid_obj in uuid_list]

    @classmethod
    def batch_to_uuid(cls, string_list: List[str]) -> List[UUID]:
        """
        批量将字符串转换为UUID对象

        Args:
            string_list: UUID字符串列表

        Returns:
            List[UUID]: UUID对象列表
        """
        if not isinstance(string_list, list):
            raise TypeError(f"Expected list, got {type(string_list)}")

        return [cls.to_uuid(uuid_str) for uuid_str in string_list]

    @classmethod
    def is_valid_uuid_string(cls, value: str) -> bool:
        """
        检查字符串是否是有效的UUID格式

        Args:
            value: 要检查的字符串

        Returns:
            bool: 是否是有效的UUID格式
        """
        if not isinstance(value, str):
            return False

        return bool(cls.UUID_PATTERN.match(value))

    @classmethod
    def generate_uuid_string(cls) -> str:
        """
        生成新的UUID字符串

        Returns:
            str: 新生成的UUID字符串
        """
        return cls.to_string(uuid4())

    @classmethod
    def safe_to_string(cls, value: Any, default: Optional[str] = None) -> Optional[str]:
        """
        安全转换为字符串，失败时返回默认值

        Args:
            value: 要转换的值
            default: 转换失败时的默认值

        Returns:
            Optional[str]: 转换结果或默认值
        """
        try:
            return cls.ensure_string(value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to convert {value} to UUID string: {e}")
            return default

    @classmethod
    def safe_to_uuid(cls, value: Any, default: Optional[UUID] = None) -> Optional[UUID]:
        """
        安全转换为UUID对象，失败时返回默认值

        Args:
            value: 要转换的值
            default: 转换失败时的默认值

        Returns:
            Optional[UUID]: 转换结果或默认值
        """
        try:
            return cls.ensure_uuid(value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to convert {value} to UUID object: {e}")
            return default

    @classmethod
    def is_valid_uuid_format(cls, value: str) -> bool:
        """
        检查UUID格式是否有效（兼容LangGraph特殊格式）

        Args:
            value: 要检查的UUID字符串

        Returns:
            bool: 是否是有效的UUID格式
        """
        if not isinstance(value, str):
            return False

        # 检查标准UUID格式
        if cls.UUID_PATTERN.match(value):
            return True

        # 检查LangGraph特殊版本号格式
        # 例如: "00000000000000000000000000000002.0.243798848838515"
        if '.' in value:
            parts = value.split('.')
            if len(parts) >= 2:
                # 检查第一部分是否是UUID格式
                if cls.UUID_PATTERN.match(parts[0]):
                    return True
                # 或者第一部分是32位十六进制数（可能没有连字符）
                if len(parts[0]) == 32 and all(c in '0123456789abcdefABCDEF' for c in parts[0]):
                    return True

        return False

    @classmethod
    def _extract_version_from_langgraph_format(cls, value: str) -> int:
        """
        从LangGraph特殊格式中提取版本号

        Args:
            value: LangGraph版本号字符串，例如 "00000000000000000000000000000002.0.243798848838515"

        Returns:
            int: 提取的版本号
        """
        if not isinstance(value, str):
            return 1

        # 如果是整数，直接返回
        try:
            return int(value)
        except ValueError:
            pass

        # 处理LangGraph特殊格式
        if '.' in value:
            parts = value.split('.')
            if len(parts) >= 2:
                # 尝试提取第一部分作为版本号
                first_part = parts[0]

                # 如果第一部分是UUID格式，提取数字部分
                if cls.UUID_PATTERN.match(first_part):
                    # 从UUID中提取数字部分生成版本号
                    hash_value = abs(hash(first_part)) % 1000000
                    return hash_value

                # 如果第一部分是32位十六进制数
                if len(first_part) == 32 and all(c in '0123456789abcdefABCDEF' for c in first_part):
                    # 转换为十进制并取模
                    try:
                        decimal_value = int(first_part, 16)
                        return decimal_value % 1000000
                    except ValueError:
                        pass

                # 如果第一部分本身是数字
                if first_part.isdigit():
                    return int(first_part) if len(first_part) > 0 else 1

        # 默认返回1
        return 1

    @classmethod
    def validate_and_normalize_uuid(cls, value: Union[str, UUID], field_name: str = "uuid") -> str:
        """
        验证并标准化UUID格式

        Args:
            value: UUID字符串或对象
            field_name: 字段名称（用于错误信息）

        Returns:
            str: 标准化的UUID字符串

        Raises:
            ValueError: 当UUID格式无效时
            TypeError: 当值类型无效时
        """
        if value is None:
            raise ValueError(f"{field_name} 不能为 None")

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, str):
            # 检查是否是标准UUID格式
            if cls.UUID_PATTERN.match(value):
                return value

            # 检查是否是常见的问题格式并提供建议
            if '-' not in value and len(value) == 32:
                raise ValueError(
                    f"{field_name} 格式错误: '{value}'。"
                    f"可能需要添加连字符，标准格式应为: "
                    f"'{value[:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:]}'"
                )

            if len(value) < 32:
                raise ValueError(
                    f"{field_name} 长度不足: '{value}'。"
                    f"标准UUID长度应为36个字符（包含连字符）。"
                )

            raise ValueError(
                f"{field_name} 格式无效: '{value}'。"
                f"请使用标准UUID格式，例如: '550e8400-e29b-41d4-a716-446655440000'"
            )

        raise TypeError(f"{field_name} 必须是字符串或UUID对象，收到类型: {type(value)}")


# 便捷函数，提供更简洁的调用方式
def to_uuid_string(uuid_obj: UUID) -> str:
    """将UUID对象转换为字符串（便捷函数）"""
    return UUIDConverter.to_string(uuid_obj)


def to_uuid_object(uuid_str: str) -> UUID:
    """将字符串转换为UUID对象（便捷函数）"""
    return UUIDConverter.to_uuid(uuid_str)


def ensure_uuid_string(value: Union[UUID, str]) -> str:
    """确保值是UUID字符串格式（便捷函数）"""
    return UUIDConverter.ensure_string(value)


def ensure_uuid_object(value: Union[UUID, str]) -> UUID:
    """确保值是UUID对象（便捷函数）"""
    return UUIDConverter.ensure_uuid(value)