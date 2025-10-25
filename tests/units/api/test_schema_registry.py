"""
Schema Registry严格单元测试

测试Schema Registry的所有功能，包括：
1. Schema注册逻辑
2. Pydantic V2兼容性检查
3. OpenAPI生成
4. 错误处理
5. 类型验证
6. 示例数据验证

作者：TaTakeKe团队
版本：1.0.0 - Schema Registry严格测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Type
from pydantic import BaseModel

from src.api.schema_registry import (
    register_all_schemas_to_openapi,
    _convert_pydantic_schema_to_openapi,
    validate_schema_examples,
    ALL_SCHEMAS
)


class MockSchema(BaseModel):
    """Mock Schema用于测试"""
    name: str
    value: int = 42

    class Config:
        json_schema_extra = {
            "example": {
                "name": "test",
                "value": 123
            }
        }


class TestConvertPydanticSchemaToOpenapi:
    """Pydantic Schema到OpenAPI转换测试"""

    def test_convert_basic_schema(self):
        """测试基本Schema转换"""
        pydantic_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "integer"}
            },
            "required": ["name"],
            "title": "MockSchema"
        }

        result = _convert_pydantic_schema_to_openapi(pydantic_schema)

        assert result["type"] == "object"
        assert "properties" in result
        assert "name" in result["properties"]
        assert "value" in result["properties"]
        assert result["required"] == ["name"]
        assert result["title"] == "MockSchema"

    def test_convert_schema_with_enum(self):
        """测试带枚举的Schema转换"""
        pydantic_schema = {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "title": "TaskPriority"
        }

        result = _convert_pydantic_schema_to_openapi(pydantic_schema)

        assert result["type"] == "string"
        assert result["enum"] == ["low", "medium", "high"]
        assert result["title"] == "TaskPriority"

    def test_convert_schema_with_array(self):
        """测试带数组的Schema转换"""
        pydantic_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}}
            },
            "title": "TaskList"
        }

        result = _convert_pydantic_schema_to_openapi(pydantic_schema)

        assert result["type"] == "array"
        assert "items" in result
        assert result["items"]["type"] == "object"

    def test_convert_schema_with_description(self):
        """测试带描述的Schema转换"""
        pydantic_schema = {
            "type": "object",
            "description": "A test schema",
            "properties": {
                "name": {"type": "string", "description": "The name field"}
            }
        }

        result = _convert_pydantic_schema_to_openapi(pydantic_schema)

        assert result["description"] == "A test schema"
        assert result["properties"]["name"]["description"] == "The name field"

    def test_convert_schema_with_all_of(self):
        """测试带allOf的Schema转换"""
        pydantic_schema = {
            "type": "object",
            "allOf": [
                {"type": "object", "properties": {"base": {"type": "string"}}},
                {"type": "object", "properties": {"derived": {"type": "integer"}}}
            ]
        }

        result = _convert_pydantic_schema_to_openapi(pydantic_schema)

        assert result["type"] == "object"
        assert "allOf" in result
        assert len(result["allOf"]) == 2

    def test_convert_schema_with_defs(self):
        """测试带$defs的Schema转换"""
        pydantic_schema = {
            "type": "object",
            "properties": {
                "ref_field": {"$ref": "#/$defs/RefType"}
            },
            "$defs": {
                "RefType": {
                    "type": "string"
                }
            }
        }

        result = _convert_pydantic_schema_to_openapi(pydantic_schema)

        assert result["type"] == "object"
        assert "$defs" in result
        assert "RefType" in result["$defs"]


class TestRegisterAllSchemasToOpenapi:
    """Schema注册到OpenAPI测试"""

    def test_register_to_empty_app(self):
        """测试注册到空应用"""
        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {
                "schemas": {}
            }
        }

        # 创建测试Schema映射
        test_schemas = {
            "MockSchema": MockSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            register_all_schemas_to_openapi(mock_app)

        # 验证Schema被添加
        assert "MockSchema" in mock_app.openapi_schema["components"]["schemas"]

    def test_register_to_app_with_existing_schemas(self):
        """测试注册到已有Schema的应用"""
        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {
                "schemas": {
                    "ExistingSchema": {"type": "string"}
                }
            }
        }

        test_schemas = {
            "MockSchema": MockSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            register_all_schemas_to_openapi(mock_app)

        # 验证原有Schema保持，新Schema被添加
        assert "ExistingSchema" in mock_app.openapi_schema["components"]["schemas"]
        assert "MockSchema" in mock_app.openapi_schema["components"]["schemas"]

    def test_register_with_missing_openapi_schema(self):
        """测试缺少openapi_schema的应用"""
        mock_app = Mock()
        mock_app.openapi_schema = None

        # 应该不会崩溃
        register_all_schemas_to_openapi(mock_app)

    def test_register_with_missing_components(self):
        """测试缺少components的Schema"""
        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"}
        }

        register_all_schemas_to_openapi(mock_app)

        # 验证components和schemas被创建
        assert "components" in mock_app.openapi_schema
        assert "schemas" in mock_app.openapi_schema["components"]

    def test_register_schema_generation_failure(self):
        """测试Schema生成失败的处理"""
        class FailingSchema:
            @classmethod
            def model_json_schema(cls):
                raise Exception("Schema generation failed")

        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        test_schemas = {
            "FailingSchema": FailingSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            # 应该不会崩溃，只是跳过失败的Schema
            register_all_schemas_to_openapi(mock_app)

        # 验证失败的Schema没有被注册
        assert "FailingSchema" not in mock_app.openapi_schema["components"]["schemas"]

    def test_register_with_ref_template_support(self):
        """测试支持ref_template的Schema"""
        class RefTemplateSchema(BaseModel):
            name: str

            @classmethod
            def model_json_schema(cls, ref_template=None):
                if ref_template:
                    return {"type": "object", "ref_template_used": True}
                return {"type": "object", "ref_template_used": False}

        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        test_schemas = {
            "RefTemplateSchema": RefTemplateSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            register_all_schemas_to_openapi(mock_app)

        # 验证Schema被正确注册
        assert "RefTemplateSchema" in mock_app.openapi_schema["components"]["schemas"]


class TestValidateSchemaExamples:
    """Schema示例验证测试"""

    def test_validate_all_schemas_with_examples(self):
        """测试验证所有带示例的Schema"""
        # 创建带示例的Mock Schema
        class ExampleSchema(BaseModel):
            name: str = "default_name"
            value: int = 42

            @classmethod
            def model_json_schema(cls):
                return {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "example": "test_name"
                        },
                        "value": {
                            "type": "integer",
                            "example": 123
                        }
                    }
                }

        test_schemas = {
            "ExampleSchema": ExampleSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            result = validate_schema_examples()

        # 所有字段都有示例，应该返回True
        assert result is True

    def test_validate_schemas_missing_examples(self):
        """测试缺少示例的Schema"""
        class NoExampleSchema(BaseModel):
            name: str
            value: int

            @classmethod
            def model_json_schema(cls):
                return {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},  # 缺少example
                        "value": {"type": "integer"}  # 缺少example
                    }
                }

        test_schemas = {
            "NoExampleSchema": NoExampleSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            result = validate_schema_examples()

        # 有字段缺少示例，应该返回False
        assert result is False

    def test_validate_schema_generation_failure(self):
        """测试Schema生成失败"""
        class FailingSchema:
            @classmethod
            def model_json_schema(cls):
                raise Exception("Generation failed")

        test_schemas = {
            "FailingSchema": FailingSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            result = validate_schema_examples()

        # 应该处理失败并返回False
        assert result is False

    def test_validate_nested_schema_examples(self):
        """测试嵌套Schema示例验证"""
        class NestedSchema(BaseModel):
            @classmethod
            def model_json_schema(cls):
                return {
                    "type": "object",
                    "properties": {
                        "nested": {
                            "type": "object",
                            "properties": {
                                "inner": {
                                    "type": "string",
                                    "example": "inner_value"
                                },
                                "missing_example": {
                                    "type": "integer"
                                    # 缺少example
                                }
                            }
                        }
                    }
                }

        test_schemas = {
            "NestedSchema": NestedSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            result = validate_schema_examples()

        # 嵌套字段缺少示例，应该返回False
        assert result is False

    def test_validate_array_schema_examples(self):
        """测试数组Schema示例验证"""
        class ArraySchema(BaseModel):
            @classmethod
            def model_json_schema(cls):
                return {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "example": "item_name"
                                    },
                                    "missing_example": {
                                        "type": "integer"
                                        # 缺少example
                                    }
                                }
                            }
                        }
                    }
                }

        test_schemas = {
            "ArraySchema": ArraySchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            result = validate_schema_examples()

        # 数组项字段缺少示例，应该返回False
        assert result is False


class TestAllSchemasConstant:
    """ALL_SCHEMAS常量测试"""

    def test_all_schemas_structure(self):
        """测试ALL_SCHEMAS的结构"""
        assert isinstance(ALL_SCHEMAS, dict)
        assert len(ALL_SCHEMAS) > 0

        # 验证所有值都是类型
        for schema_name, schema_class in ALL_SCHEMAS.items():
            assert isinstance(schema_name, str)
            assert isinstance(schema_class, type)

    def test_all_schemas_contains_expected_domains(self):
        """测试ALL_SCHEMAS包含预期的域"""
        expected_domains = [
            "UnifiedResponse",  # 认证
            "CreateTaskRequest",  # 任务
            "SendMessageRequest",  # 聊天
            "StartFocusRequest",  # 番茄钟
            "RewardResponse",  # 奖励
            "UserProfileResponse",  # 用户
        ]

        for expected_schema in expected_domains:
            assert expected_schema in ALL_SCHEMAS, f"缺少Schema: {expected_schema}"

    def test_all_schemas_pydantic_compatibility(self):
        """测试ALL_SCHEMAS中Schema的Pydantic兼容性"""
        incompatible_schemas = []

        for schema_name, schema_class in ALL_SCHEMAS.items():
            try:
                # 尝试获取model_json_schema方法
                if hasattr(schema_class, 'model_json_schema'):
                    schema = schema_class.model_json_schema()
                    assert isinstance(schema, dict), f"{schema_name}的model_json_schema应返回字典"
                # 对于自定义类（如枚举），跳过检查
            except Exception as e:
                incompatible_schemas.append(f"{schema_name}: {e}")

        # 报告不兼容的Schema
        if incompatible_schemas:
            pytest.fail(f"发现不兼容的Schema:\n" + "\n".join(incompatible_schemas))


class TestSchemaRegistryEdgeCases:
    """Schema Registry边界情况测试"""

    def test_register_schema_with_circular_references(self):
        """测试循环引用的Schema"""
        class CircularA(BaseModel):
            b_ref: "CircularB"

        class CircularB(BaseModel):
            a_ref: CircularA

        # 更新forward references
        CircularA.model_rebuild()

        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        test_schemas = {
            "CircularA": CircularA,
            "CircularB": CircularB
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            # 应该能处理循环引用
            register_all_schemas_to_openapi(mock_app)

        # 验证Schema被注册
        assert "CircularA" in mock_app.openapi_schema["components"]["schemas"]
        assert "CircularB" in mock_app.openapi_schema["components"]["schemas"]

    def test_register_schema_with_large_schema(self):
        """测试大型Schema"""
        class LargeSchema(BaseModel):
            field_1: str
            field_2: int
            field_3: float
            field_4: bool
            field_5: str

        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        test_schemas = {
            "LargeSchema": LargeSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            register_all_schemas_to_openapi(mock_app)

        # 验证大型Schema被正确注册
        assert "LargeSchema" in mock_app.openapi_schema["components"]["schemas"]
        schema = mock_app.openapi_schema["components"]["schemas"]["LargeSchema"]
        assert len(schema["properties"]) == 5

    def test_register_schema_with_special_characters(self):
        """测试包含特殊字符的Schema"""
        class SpecialCharSchema(BaseModel):
            special_field: str  # 包含下划线
            "field-with-dashes": str  # 包含连字符（通过Field别名）
            "field.with.dots": str  # 包含点（通过Field别名）

            class Config:
                allow_population_by_field_name = True
                fields = {
                    "field-with-dashes": "field_with_dashes",
                    "field.with.dots": "field_with_dots"
                }

        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        test_schemas = {
            "SpecialCharSchema": SpecialCharSchema
        }

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            register_all_schemas_to_openapi(mock_app)

        # 验证特殊字符字段名被正确处理
        assert "SpecialCharSchema" in mock_app.openapi_schema["components"]["schemas"]


@pytest.mark.performance
class TestSchemaRegistryPerformance:
    """Schema Registry性能测试"""

    def test_register_many_schemas_performance(self):
        """测试注册大量Schema的性能"""
        # 创建大量测试Schema
        many_schemas = {}
        for i in range(50):
            class_name = f"PerfSchema{i}"
            schema_class = type(class_name, (BaseModel,), {
                "field_" + str(i): str,
                "__module__": __name__
            })
            many_schemas[class_name] = schema_class

        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        import time
        start_time = time.time()

        with patch.dict(ALL_SCHEMAS, many_schemas, clear=False):
            register_all_schemas_to_openapi(mock_app)

        duration = time.time() - start_time
        assert duration < 5.0, f"注册大量Schema性能测试失败: {duration:.3f}s"

        # 验证所有Schema都被注册
        assert len(mock_app.openapi_schema["components"]["schemas"]) >= 50

    def test_validate_examples_performance(self):
        """测试示例验证性能"""
        # 创建带大量字段的Schema
        class LargeExampleSchema(BaseModel):
            @classmethod
            def model_json_schema(cls):
                properties = {}
                for i in range(100):
                    if i % 2 == 0:
                        properties[f"field_{i}"] = {
                            "type": "string",
                            "example": f"example_{i}"
                        }
                    else:
                        properties[f"field_{i}"] = {
                            "type": "string"
                            # 缺少example
                        }

                return {
                    "type": "object",
                    "properties": properties
                }

        test_schemas = {
            "LargeExampleSchema": LargeExampleSchema
        }

        import time
        start_time = time.time()

        with patch.dict(ALL_SCHEMAS, test_schemas, clear=False):
            validate_schema_examples()

        duration = time.time() - start_time
        assert duration < 2.0, f"示例验证性能测试失败: {duration:.3f}s"


class TestSchemaRegistryIntegration:
    """Schema Registry集成测试"""

    def test_full_registration_workflow(self):
        """测试完整的注册工作流"""
        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        # 注册Schema
        register_all_schemas_to_openapi(mock_app)

        # 验证Schema被注册
        assert len(mock_app.openapi_schema["components"]["schemas"]) > 0

        # 验证示例（如果有Schema缺少示例会返回False）
        example_validation = validate_schema_examples()
        # 结果取决于ALL_SCHEMAS中的实际Schema

    def test_registration_idempotency(self):
        """测试注册的幂等性"""
        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        # 第一次注册
        register_all_schemas_to_openapi(mock_app)
        first_count = len(mock_app.openapi_schema["components"]["schemas"])

        # 第二次注册
        register_all_schemas_to_openapi(mock_app)
        second_count = len(mock_app.openapi_schema["components"]["schemas"])

        # Schema数量应该相同（幂等性）
        assert first_count == second_count

    def test_schema_order_consistency(self):
        """测试Schema顺序一致性"""
        mock_app = Mock()
        mock_app.openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
            "components": {"schemas": {}}
        }

        # 多次注册
        register_all_schemas_to_openapi(mock_app)
        first_order = list(mock_app.openapi_schema["components"]["schemas"].keys())

        register_all_schemas_to_openapi(mock_app)
        second_order = list(mock_app.openapi_schema["components"]["schemas"].keys())

        # Schema顺序应该一致
        assert first_order == second_order