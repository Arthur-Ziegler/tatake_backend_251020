"""
UUID通用处理组件

统一处理UUID类型与字符串的转换，解决数据库存取时的类型绑定问题。

设计原则：
1. 业务层使用原生UUID对象
2. 数据库层使用字符串存储
3. 在Repository层自动处理转换
4. 提供装饰器和工具函数简化使用

使用方式：
- 在Repository的get_by_id等方法中使用convert_uuid_params装饰器
- 在构建查询参数时使用uuid_to_str
- 在处理查询结果时使用str_to_uuid

作者：TaTakeKe团队
版本：1.0.0
"""

import logging
from typing import Any, Dict, List, Union, Optional
from functools import wraps
from uuid import UUID, uuid4
import inspect

logger = logging.getLogger(__name__)


def uuid_to_str(value: Union[str, UUID, None]) -> Optional[str]:
    """
    将UUID转换为字符串

    Args:
        value: UUID对象、字符串或None

    Returns:
        Optional[str]: 转换后的字符串或None

    Examples:
        >>> uuid_to_str(UUID('12345678-1234-5678-9abc-123456789abc'))
        '12345678-1234-5678-9abc-123456789abc'
        >>> uuid_to_str('12345678-1234-5678-9abc-123456789abc')
        '12345678-1234-5678-9abc-123456789abc'
        >>> uuid_to_str(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        # 验证字符串是否为有效的UUID格式
        try:
            UUID(value)
            return value
        except ValueError:
            logger.warning(f"Invalid UUID string: {value}")
            return value  # 保持原样，让下游处理错误
    return str(value)


def str_to_uuid(value: Union[str, UUID, None]) -> Optional[UUID]:
    """
    将字符串转换为UUID

    Args:
        value: 字符串、UUID对象或None

    Returns:
        Optional[UUID]: 转换后的UUID对象或None

    Examples:
        >>> str_to_uuid('12345678-1234-5678-9abc-123456789abc')
        UUID('12345678-1234-5678-9abc-123456789abc')
        >>> str_to_uuid(UUID('12345678-1234-5678-9abc-123456789abc'))
        UUID('12345678-1234-5678-9abc-123456789abc')
        >>> str_to_uuid(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            logger.warning(f"Invalid UUID string: {value}")
            return None
    return None


def convert_uuid_dict(data: Dict[str, Any], uuid_fields: List[str]) -> Dict[str, Any]:
    """
    转换字典中的UUID字段为字符串

    Args:
        data: 原始字典
        uuid_fields: 需要转换的UUID字段名列表

    Returns:
        Dict[str, Any]: 转换后的字典

    Examples:
        >>> data = {"id": UUID('123...'), "name": "test"}
        >>> convert_uuid_dict(data, ["id"])
        {"id": "123...", "name": "test"}
    """
    if not data:
        return data

    result = data.copy()
    for field in uuid_fields:
        if field in result:
            result[field] = uuid_to_str(result[field])

    return result


def convert_str_dict(data: Dict[str, Any], uuid_fields: List[str]) -> Dict[str, Any]:
    """
    转换字典中的字符串字段为UUID

    Args:
        data: 原始字典
        uuid_fields: 需要转换的UUID字段名列表

    Returns:
        Dict[str, Any]: 转换后的字典
    """
    if not data:
        return data

    result = data.copy()
    for field in uuid_fields:
        if field in result:
            result[field] = str_to_uuid(result[field])

    return result


def convert_uuid_params_decorator(uuid_fields: List[str] = None):
    """
    装饰器：自动转换Repository方法中的UUID参数为字符串

    Args:
        uuid_fields: 需要转换的UUID字段名列表，如果为None则尝试自动检测

    Usage:
        @convert_uuid_params_decorator(['user_id', 'task_id'])
        def get_by_id(self, task_id, user_id):
            # task_id 和 user_id 会自动转换为字符串
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取函数签名
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()

            # 转换参数
            if uuid_fields:
                # 使用指定的字段列表
                for field in uuid_fields:
                    if field in bound_args.arguments:
                        bound_args.arguments[field] = uuid_to_str(bound_args.arguments[field])
            else:
                # 自动检测UUID参数
                for param_name, param_value in bound_args.arguments.items():
                    if param_name != 'self':  # 跳过self参数
                        if isinstance(param_value, UUID):
                            bound_args.arguments[param_name] = uuid_to_str(param_value)

            # 调用原函数
            return func(self, **bound_args.arguments)
        return wrapper
    return decorator


class UUIDModelMixin:
    """
    UUID模型混入类

    为SQLModel提供UUID处理的便利方法
    """

    @classmethod
    def get_uuid_fields(cls) -> List[str]:
        """
        获取模型中的UUID字段列表

        子类应该重写此方法来指定UUID字段
        """
        return ['id', 'user_id', 'parent_id', 'task_id']  # 默认常见UUID字段

    def to_dict_with_uuid_str(self) -> Dict[str, Any]:
        """
        转换为字典，将UUID字段转换为字符串
        """
        data = self.model_dump(mode='python')
        return convert_uuid_dict(data, self.get_uuid_fields())

    @classmethod
    def from_dict_with_uuid(cls, data: Dict[str, Any]):
        """
        从字典创建实例，将字符串UUID字段转换为UUID对象
        """
        converted_data = convert_str_dict(data, cls.get_uuid_fields())
        return cls(**converted_data)


class UUIDRepositoryMixin:
    """
    UUID仓储混入类

    为Repository提供UUID处理的便利方法
    """

    def __init__(self, session):
        self.session = session
        # 子类应该定义model_class和uuid_fields
        self.model_class = None
        self.uuid_fields = []

    def _convert_query_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换查询参数中的UUID为字符串
        """
        return convert_uuid_dict(params, self.uuid_fields)

    def _convert_model_result(self, model_instance) -> Any:
        """
        转换模型结果，将字符串UUID转换为UUID对象
        """
        if model_instance is None:
            return None

        # 如果模型有UUIDModelMixin，使用其方法
        if hasattr(model_instance, 'to_dict_with_uuid_str'):
            return model_instance

        return model_instance


# 便捷函数
def generate_uuid() -> UUID:
    """生成新的UUID"""
    return uuid4()


def is_valid_uuid(value: Union[str, UUID]) -> bool:
    """
    检查值是否为有效的UUID

    Args:
        value: 要检查的值

    Returns:
        bool: 是否为有效UUID
    """
    if value is None:
        return False
    if isinstance(value, UUID):
        return True
    if isinstance(value, str):
        try:
            UUID(value)
            return True
        except ValueError:
            return False
    return False


def ensure_uuid(value: Union[str, UUID, None]) -> Optional[UUID]:
    """
    确保值是UUID类型，如果不是则尝试转换

    Args:
        value: 输入值

    Returns:
        Optional[UUID]: UUID对象或None
    """
    return str_to_uuid(value)


def ensure_uuid_str(value: Union[str, UUID, None]) -> Optional[str]:
    """
    确保值是UUID字符串，如果不是则尝试转换

    Args:
        value: 输入值

    Returns:
        Optional[str]: UUID字符串或None
    """
    return uuid_to_str(value)