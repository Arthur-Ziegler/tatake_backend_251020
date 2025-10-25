"""
共享模块

提供跨域使用的通用组件和工具。

模块内容：
- uuid_handler: UUID类型转换和处理
- response_utils: 响应格式化工具
- validation_utils: 验证工具
- database_utils: 数据库工具

作者：TaTakeKe团队
版本：1.0.0
"""

from .uuid_handler import (
    uuid_to_str,
    str_to_uuid,
    convert_uuid_dict,
    convert_str_dict,
    convert_uuid_params_decorator,
    UUIDModelMixin,
    UUIDRepositoryMixin,
    generate_uuid,
    is_valid_uuid,
    ensure_uuid,
    ensure_uuid_str,
)

__all__ = [
    'uuid_to_str',
    'str_to_uuid',
    'convert_uuid_dict',
    'convert_str_dict',
    'convert_uuid_params_decorator',
    'UUIDModelMixin',
    'UUIDRepositoryMixin',
    'generate_uuid',
    'is_valid_uuid',
    'ensure_uuid',
    'ensure_uuid_str',
]