"""
FastAPI HTTP响应序列化测试

这个测试文件专门测试FastAPI在实际HTTP请求/响应中的序列化行为，
确保自定义类型在真实的API场景中能正确序列化。

测试重点：
1. HTTP响应序列化
2. 自定义类型在FastAPI中的表现
3. OpenAPI schema生成
4. 错误处理

作者：TaTakeKe团队
版本：1.0.0 - FastAPI序列化测试
"""

import pytest
import json
from typing import Any
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.api.main import app
from src.core.types import TaskStatus, TaskPriority


class TestFastAPISerialization:
    """FastAPI HTTP响应序列化测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.client = TestClient(app)

    def test_task_list_response_serialization(self):
        """测试任务列表API响应序列化"""
        # 使用有效的token进行测试
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ZjNiMTcyNS0yMjAzLTRkMDQtODZiNy1mZTAxOTk1OTc5NWQiLCJpc19ndWVzdCI6dHJ1ZSwiand0X3ZlcnNpb24iOjEsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3NjE0MjMxNDgsImV4cCI6MTc2MTQyNDk0OCwianRpIjoiOWQ0NDBiMjUtYmE5OC00ZGM2LThiOGYtYzE1ZWYyMzdlYzkzIn0.3y3SYwmn9kNHKwEb2_f9SrQRJseyMxsAMBQlas1h1sk"

        response = self.client.get(
            "/tasks/?page=1&page_size=20&include_deleted=false",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "tasks" in data["data"]

        # 验证TaskStatus正确序列化为字符串
        if data["data"]["tasks"]:
            task = data["data"]["tasks"][0]
            assert isinstance(task["status"], str)
            assert task["status"] in ["pending", "in_progress", "completed"]
            assert isinstance(task["priority"], str)
            assert task["priority"] in ["low", "medium", "high"]

    def test_task_creation_response_serialization(self):
        """测试任务创建API响应序列化"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ZjNiMTcyNS0yMjAzLTRkMDQtODZiNy1mZTAxOTk1OTc5NWQiLCJpc19ndWVzdCI6dHJ1ZSwiand0X3ZlcnNpb24iOjEsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3NjE0MjMxNDgsImV4cCI6MTc2MTQyNDk0OCwianRpIjoiOWQ0NDBiMjUtYmE5OC00ZGM2LThiOGYtYzE1ZWYyMzdlYzkzIn0.3y3SYwmn9kNHKwEb2_f9SrQRJseyMxsAMBQlas1h1sk"

        task_data = {
            "title": "测试任务",
            "description": "测试任务描述",
            "status": "pending",
            "priority": "high"
        }

        response = self.client.post(
            "/tasks/",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

        data = response.json()
        assert "data" in data

        # 验证响应中的TaskStatus和TaskPriority是字符串
        if "task" in data["data"]:
            task = data["data"]["task"]
            assert isinstance(task["status"], str)
            assert task["status"] == "pending"
            assert isinstance(task["priority"], str)
            assert task["priority"] == "high"

    def test_invalid_status_in_request(self):
        """测试无效状态值在请求中的处理"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ZjNiMTcyNS0yMjAzLTRkMDQtODZiNy1mZTAxOTk1OTc5NWQiLCJpc19ndWVzdCI6dHJ1ZSwiand0X3ZlcnNpb24iOjEsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3NjE0MjMxNDgsImV4cCI6MTc2MTQyNDk0OCwianRpIjoiOWQ0NDBiMjUtYmE5OC00ZGM2LThiOGYtYzE1ZWYyMzdlYzkzIn0.3y3SYwmn9kNHKwEb2_f9SrQRJseyMxsAMBQlas1h1sk"

        task_data = {
            "title": "测试任务",
            "status": "invalid_status",  # 无效状态
            "priority": "medium"
        }

        response = self.client.post(
            "/tasks/",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # 应该返回验证错误
        assert response.status_code == 422 or response.status_code == 400

        error_data = response.json()
        assert "detail" in error_data or "error" in error_data

    def test_openapi_schema_generation(self):
        """测试OpenAPI schema生成"""
        response = self.client.get("/openapi.json")

        assert response.status_code == 200

        openapi_schema = response.json()

        # 验证components/schemas中包含TaskStatus和TaskPriority
        if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
            schemas = openapi_schema["components"]["schemas"]

            # 检查是否有包含TaskStatus或TaskPriority的schema
            task_schemas = [name for name in schemas.keys() if "Task" in name]
            assert len(task_schemas) > 0

    def test_api_docs_response(self):
        """测试API文档响应"""
        response = self.client.get("/docs")

        # Swagger UI应该能正常加载
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestPydanticModelIntegration:
    """Pydantic模型与API集成测试"""

    def test_task_status_in_model_field(self):
        """测试TaskStatus在Pydantic模型字段中的表现"""
        class TestModel(BaseModel):
            title: str
            status: TaskStatus
            priority: TaskPriority

        # 测试直接创建
        model = TestModel(
            title="测试",
            status=TaskStatus("pending"),
            priority=TaskPriority("high")
        )

        # 测试model_dump用于API响应
        data = model.model_dump()
        assert isinstance(data["status"], str)
        assert data["status"] == "pending"
        assert isinstance(data["priority"], str)
        assert data["priority"] == "high"

        # 测试JSON序列化
        json_str = model.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed["status"], str)
        assert parsed["status"] == "pending"

    def test_model_validation_from_strings(self):
        """测试模型从字符串验证"""
        class TestModel(BaseModel):
            title: str
            status: TaskStatus
            priority: TaskPriority

        # 从字符串创建模型
        model = TestModel(
            title="测试",
            status="completed",  # 字符串应该自动转换为TaskStatus
            priority="low"      # 字符串应该自动转换为TaskPriority
        )

        assert isinstance(model.status, TaskStatus)
        assert model.status.value == "completed"
        assert isinstance(model.priority, TaskPriority)
        assert model.priority.value == "low"

    def test_model_validation_invalid_values(self):
        """测试模型验证无效值"""
        class TestModel(BaseModel):
            title: str
            status: TaskStatus
            priority: TaskPriority

        # 测试无效状态
        with pytest.raises(ValueError):
            TestModel(
                title="测试",
                status="invalid_status",
                priority="medium"
            )

        # 测试无效优先级
        with pytest.raises(ValueError):
            TestModel(
                title="测试",
                status="pending",
                priority="invalid_priority"
            )


class TestSerializationEdgeCases:
    """序列化边界情况测试"""

    def test_all_status_values_serialization(self):
        """测试所有状态值的序列化"""
        all_statuses = ["pending", "in_progress", "completed"]

        for status_value in all_statuses:
            status = TaskStatus(status_value)
            # 继承自str的类本身就是字符串
            assert isinstance(status, str)
            assert str(status) == status_value

            # JSON序列化测试
            json_str = json.dumps(str(status))
            parsed = json.loads(json_str)
            assert parsed == status_value

    def test_all_priority_values_serialization(self):
        """测试所有优先级值的序列化"""
        all_priorities = ["low", "medium", "high"]

        for priority_value in all_priorities:
            priority = TaskPriority(priority_value)
            # 继承自str的类本身就是字符串
            assert isinstance(priority, str)
            assert str(priority) == priority_value

            # JSON序列化测试
            json_str = json.dumps(str(priority))
            parsed = json.loads(json_str)
            assert parsed == priority_value

    def test_complex_model_with_nested_types(self):
        """测试包含嵌套类型的复杂模型序列化"""
        class ComplexModel(BaseModel):
            tasks: list[dict[str, Any]]
            default_status: TaskStatus = TaskStatus.PENDING

        model = ComplexModel(
            tasks=[],
            default_status=TaskStatus("completed")
        )

        data = model.model_dump()
        assert isinstance(data["default_status"], str)
        assert data["default_status"] == "completed"
        assert isinstance(data["tasks"], list)


if __name__ == "__main__":
    pytest.main([__file__])