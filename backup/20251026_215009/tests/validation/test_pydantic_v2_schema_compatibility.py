"""
Pydantic V2 Schema兼容性测试

测试自定义枚举类型的Pydantic V2兼容性，确保所有Schema都能正确注册到OpenAPI。

测试范围:
- TaskStatus枚举类型
- TaskPriority枚举类型
- SessionType枚举类型
- Schema Registry注册功能
- OpenAPI文档生成

作者：TaKeKe团队
版本：1.0.0 - UUID架构Batch 1测试
"""

import pytest
import json
from pydantic import ValidationError
from pydantic_core import core_schema

# 导入需要测试的自定义类型
from src.core.types import TaskStatus, TaskPriority
from src.domains.focus.models import SessionType


class TestTaskStatusSchemaCompatibility:
    """TaskStatus Pydantic V2兼容性测试"""

    def test_task_status_model_json_schema(self):
        """测试TaskStatus.model_json_schema()方法正常工作"""
        schema = TaskStatus.model_json_schema()

        # 验证基本结构
        assert "title" in schema
        assert "type" in schema
        assert "enum" in schema
        assert "description" in schema

        # 验证枚举值
        assert schema["enum"] == ["pending", "in_progress", "completed"]

        # 验证标题和描述
        assert schema["title"] == "TaskStatus"
        assert "任务状态枚举" in schema["description"]

    def test_task_status_pydantic_core_schema(self):
        """测试TaskStatus.__get_pydantic_core_schema__方法"""
        schema = TaskStatus.__get_pydantic_core_schema__(TaskStatus, None)

        # 验证返回的是Pydantic core schema
        assert 'type' in schema
        assert schema['type'] == 'union'
        assert 'choices' in schema
        assert len(schema['choices']) == 2  # is_instance_schema 和 no_info_plain_validator_function

    def test_task_status_validation(self):
        """测试TaskStatus字段验证功能"""
        # 测试有效值
        for valid_value in ["pending", "in_progress", "completed"]:
            status = TaskStatus(valid_value)
            assert str(status) == valid_value

        # 测试无效值
        with pytest.raises(ValueError):
            TaskStatus("invalid_status")

    def test_task_status_json_serialization(self):
        """测试TaskStatus JSON序列化"""
        status = TaskStatus("pending")

        # 测试model_dump
        data = status.model_dump()
        assert data == "pending"

        # 测试model_dump_json
        json_str = status.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed == "pending"


class TestTaskPrioritySchemaCompatibility:
    """TaskPriority Pydantic V2兼容性测试"""

    def test_task_priority_model_json_schema(self):
        """测试TaskPriority.model_json_schema()方法正常工作"""
        schema = TaskPriority.model_json_schema()

        # 验证基本结构
        assert "title" in schema
        assert "type" in schema
        assert "enum" in schema
        assert "description" in schema

        # 验证枚举值
        assert schema["enum"] == ["low", "medium", "high"]

        # 验证标题和描述
        assert schema["title"] == "TaskPriority"
        assert "任务优先级枚举" in schema["description"]

    def test_task_priority_pydantic_core_schema(self):
        """测试TaskPriority.__get_pydantic_core_schema__方法"""
        schema = TaskPriority.__get_pydantic_core_schema__(TaskPriority, None)

        # 验证返回的是Pydantic core schema
        assert isinstance(schema, dict)
        assert 'type' in schema
        assert schema['type'] == 'union'
        assert 'choices' in schema
        assert len(schema['choices']) == 2  # is_instance_schema 和 no_info_plain_validator_function

    def test_task_priority_validation(self):
        """测试TaskPriority字段验证功能"""
        # 测试有效值
        for valid_value in ["low", "medium", "high"]:
            priority = TaskPriority(valid_value)
            assert str(priority) == valid_value

        # 测试无效值
        with pytest.raises(ValueError):
            TaskPriority("invalid_priority")

    def test_task_priority_json_serialization(self):
        """测试TaskPriority JSON序列化"""
        priority = TaskPriority("medium")

        # 测试model_dump
        data = priority.model_dump()
        assert data == "medium"

        # 测试model_dump_json
        json_str = priority.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed == "medium"


class TestSessionTypeSchemaCompatibility:
    """SessionType Pydantic V2兼容性测试"""

    def test_session_type_model_json_schema(self):
        """测试SessionType.model_json_schema()方法正常工作"""
        schema = SessionType.model_json_schema()

        # 验证基本结构
        assert "title" in schema
        assert "type" in schema
        assert "enum" in schema
        assert "description" in schema

        # 验证枚举值
        assert schema["enum"] == ["focus", "break", "long_break", "pause"]

        # 验证标题和描述
        assert schema["title"] == "SessionType"
        assert "会话类型枚举" in schema["description"]

    def test_session_type_pydantic_core_schema(self):
        """测试SessionType.__get_pydantic_core_schema__方法"""
        schema = SessionType.__get_pydantic_core_schema__(SessionType, None)

        # 验证返回的是Pydantic core schema
        assert isinstance(schema, dict)
        assert 'type' in schema
        assert schema['type'] == 'union'
        assert 'choices' in schema
        assert len(schema['choices']) == 2  # is_instance_schema 和 no_info_plain_validator_function

    def test_session_type_validation(self):
        """测试SessionType字段验证功能"""
        # 测试有效值
        for valid_value in ["focus", "break", "long_break", "pause"]:
            session_type = SessionType(valid_value)
            assert str(session_type) == valid_value

        # 测试无效值
        with pytest.raises(ValueError):
            SessionType("invalid_session_type")

    def test_session_type_json_serialization(self):
        """测试SessionType JSON序列化"""
        session_type = SessionType("focus")

        # 测试model_dump
        data = session_type.model_dump()
        assert data == "focus"

        # 测试model_dump_json
        json_str = session_type.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed == "focus"


class TestSchemaRegistryIntegration:
    """Schema Registry集成测试"""

    def test_schema_registry_contains_custom_types(self, client):
        """测试Schema Registry包含自定义类型"""
        # 获取OpenAPI文档
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()
        schemas = openapi_spec.get("components", {}).get("schemas", {})

        # 验证自定义类型存在
        assert "TaskStatus" in schemas
        assert "TaskPriority" in schemas
        assert "SessionType" in schemas

        # 验证Schema结构正确
        task_status_schema = schemas["TaskStatus"]
        assert task_status_schema["type"] == "string"
        assert "enum" in task_status_schema
        assert task_status_schema["enum"] == ["pending", "in_progress", "completed"]

        task_priority_schema = schemas["TaskPriority"]
        assert task_priority_schema["type"] == "string"
        assert "enum" in task_priority_schema
        assert task_priority_schema["enum"] == ["low", "medium", "high"]

        session_type_schema = schemas["SessionType"]
        assert session_type_schema["type"] == "string"
        assert "enum" in session_type_schema
        assert session_type_schema["enum"] == ["focus", "break", "long_break", "pause"]

    def test_openapi_docs_render_successfully(self, client):
        """测试OpenAPI文档渲染成功"""
        # 测试Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # 测试ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_schema_validation_in_api_context(self, client):
        """测试API上下文中的Schema验证"""
        # 这里可以添加具体的API测试来验证Schema在实际API调用中的表现
        # 暂时跳过，因为需要具体的API端点
        pass


@pytest.mark.integration
class TestCrossSchemaCompatibility:
    """跨Schema兼容性测试"""

    def test_all_custom_schemas_generate_valid_json(self):
        """测试所有自定义Schema都能生成有效的JSON"""
        schemas_to_test = [
            (TaskStatus, ["pending", "in_progress", "completed"]),
            (TaskPriority, ["low", "medium", "high"]),
            (SessionType, ["focus", "break", "long_break", "pause"])
        ]

        for schema_class, valid_values in schemas_to_test:
            for value in valid_values:
                # 创建实例
                instance = schema_class(value)

                # 测试JSON schema生成
                json_schema = schema_class.model_json_schema()
                assert isinstance(json_schema, dict)
                assert "enum" in json_schema

                # 测试实例序列化
                serialized = instance.model_dump()
                assert serialized == value

                # 测试JSON序列化
                json_str = instance.model_dump_json()
                parsed = json.loads(json_str)
                assert parsed == value