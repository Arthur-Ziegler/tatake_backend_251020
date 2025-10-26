"""
枚举类型JSON Schema编码器

为Pydantic V2中的枚举类型提供model_json_schema属性支持。

解决TaskStatus、TaskPriority等枚举类型在Schema注册时的错误。
"""

import json
from enum import Enum
from typing import Any, Type, TypeVar, get_origin
from pydantic.json_schema import GenerateJsonSchema
from pydantic._internal._generate_schema import GenerateSchema


def encode_enum(enum_class: Type[Enum]) -> Any:
    """
    为枚举类型生成model_json_schema属性

    Args:
        enum_class: 枚举类型

    Returns:
        包含model_json_schema属性的枚举类
    """
    def model_json_schema(cls) -> Any:
        """Pydantic V2兼容的model_json_schema属性"""
        if not isinstance(enum_class, type) or not issubclass(enum_class, Enum):
            raise TypeError(f"{enum_class.__name__} is not an Enum")

        # 获取枚举成员及其值
        enum_values = {}
        enum_descriptions = {}

        for member in enum_class:
            enum_values[member.name] = member.value
            # 如果成员有描述，添加到schema中
            if hasattr(member, '__doc__') and member.__doc__:
                enum_descriptions[member.name] = member.__doc__

        # 生成符合JSON Schema的枚举定义
        schema = {
            "type": "string",
            "enum": list(enum_values.keys()),
            "title": enum_class.__name__,
            "description": enum_class.__doc__ or f"{enum_class.__name__} enumeration"
        }

        # 如果有成员描述，添加到schema中
        if enum_descriptions:
            descriptions = {}
            for name, desc in enum_descriptions.items():
                descriptions[name] = desc
                schema["descriptions"] = descriptions

        return schema

    @classmethod
    def __get_validators__(cls) -> Any:
        """获取枚举类验证器"""
        return [super().__get_validators__(cls)]

    @classmethod
    def __modify_schema__(cls) -> Any:
        """修改schema以支持枚举"""
        schema = cls.model_json_schema()
        return GenerateJsonSchema(
            schema=schema,
            ref=cls.__name__,
            title=cls.__name__,
            description=cls.__doc__,
        )


# 为现有枚举类型动态添加model_json_schema属性
def add_json_schema_to_enum(enum_class: Type[Enum]) -> None:
    """
    为已存在的枚举类添加model_json_schema属性

    Args:
        enum_class: 目标枚举类
    """
    setattr(enum_class, 'model_json_schema', classmethod(encode_enum(enum_class)))