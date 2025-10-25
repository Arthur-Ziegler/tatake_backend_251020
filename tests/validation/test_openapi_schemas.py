"""
OpenAPI Schema验证测试

验证OpenAPI JSON文档包含所有必要的schema定义，确保1.2变更的文档层面要求得到满足。

作者：TaKeKe团队
版本：1.0.0 - 1.2变更验证
"""

import pytest
import requests
import json
from typing import Dict, Any, List


class TestOpenAPISchemas:
    """OpenAPI Schema完整性验证"""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture(scope="class")
    def openapi_spec(self) -> Dict[str, Any]:
        """获取OpenAPI规范"""
        try:
            response = requests.get(f"{self.BASE_URL}/openapi.json")
            assert response.status_code == 200, f"无法获取OpenAPI JSON: {response.status_code}"
            return response.json()
        except requests.exceptions.ConnectionError:
            pytest.skip("API服务器未运行，跳过OpenAPI验证测试")

    def test_openapi_contains_required_schemas(self, openapi_spec: Dict[str, Any]):
        """验证OpenAPI包含所有必要的schema定义"""
        schemas = openapi_spec.get("components", {}).get("schemas", {})

        required_schemas = [
            # 核心响应格式
            "UnifiedResponse",

            # 认证相关
            "AuthTokenData",
            "GuestInitRequest",
            "WeChatRegisterRequest",
            "WeChatLoginRequest",

            # 任务相关
            "CreateTaskRequest",
            "UpdateTaskRequest",
            "TaskResponse",
            "TaskListResponse",
            "TaskDeleteResponse",
            "CompleteTaskRequest",
            "CompleteTaskResponse",

            # 专注相关
            "StartFocusRequest",
            "FocusSessionResponse",
            "FocusSessionListResponse",
            "FocusOperationResponse",

            # 聊天相关
            "SendMessageRequest",
            "MessageResponse",
            "ChatSessionResponse",
            "SessionListResponse",
            "SessionInfoResponse",
            "DeleteSessionResponse",
            "ChatHealthResponse",

            # 用户相关
            "UpdateProfileRequest",
            "UserProfileResponse",
            "FeedbackRequest",

            # 奖励相关
            "RewardResponse",
            "UserMaterialsResponse",
            "AvailableRecipesResponse",
            "RedeemRecipeResponse",

            # Top3相关
            "SetTop3Request",
            "Top3Response",
            "GetTop3Response",
        ]

        missing_schemas = []
        for schema_name in required_schemas:
            if schema_name not in schemas:
                missing_schemas.append(schema_name)

        assert len(missing_schemas) == 0, f"缺少必要的schema: {missing_schemas}"

    def test_unified_response_schema_structure(self, openapi_spec: Dict[str, Any]):
        """验证UnifiedResponse schema结构正确"""
        schemas = openapi_spec.get("components", {}).get("schemas", {})

        assert "UnifiedResponse" in schemas, "缺少UnifiedResponse schema"

        unified_schema = schemas["UnifiedResponse"]

        # 验证必要字段
        properties = unified_schema.get("properties", {})
        required = unified_schema.get("required", [])

        assert "code" in properties, "UnifiedResponse缺少code字段"
        assert "data" in properties, "UnifiedResponse缺少data字段"
        assert "message" in properties, "UnifiedResponse缺少message字段"

        assert "code" in required, "code字段应该是必需的"
        assert "message" in required, "message字段应该是必需的"

    def test_all_endpoints_have_response_models(self, openapi_spec: Dict[str, Any]):
        """验证所有端点都有明确的response_model定义"""
        paths = openapi_spec.get("paths", {})
        endpoints_without_schema = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                responses = operation.get("responses", {})
                success_response = responses.get("200") or responses.get("201")

                if not success_response:
                    endpoints_without_schema.append(f"{method.upper()} {path}")
                    continue

                content = success_response.get("content", {})
                json_content = content.get("application/json", {})
                schema = json_content.get("schema", {})

                # 检查是否有schema引用
                if not (schema.get("$ref") or schema.get("allOf")):
                    endpoints_without_schema.append(f"{method.upper()} {path}")

        assert len(endpoints_without_schema) == 0, \
            f"以下端点缺少schema定义: {endpoints_without_schema}"

    def test_no_wrapper_classes_in_schemas(self, openapi_spec: Dict[str, Any]):
        """验证OpenAPI中不包含已删除的Wrapper类"""
        schemas = openapi_spec.get("components", {}).get("schemas", {})

        forbidden_wrapper_classes = [
            "TaskCreateResponse",
            "TaskUpdateResponse",
            "TaskDeleteResponseWrapper",
            "TaskListResponseWrapper",
            "TaskCompleteResponseWrapper",
            "TaskUncompleteResponseWrapper",
            "UserMaterialsResponseWrapper",
            "AvailableRecipesResponseWrapper",
            "RedeemRecipeResponseWrapper"
        ]

        found_wrappers = []
        for wrapper_class in forbidden_wrapper_classes:
            if wrapper_class in schemas:
                found_wrappers.append(wrapper_class)

        assert len(found_wrappers) == 0, f"OpenAPI中仍包含已删除的Wrapper类: {found_wrappers}"

    def test_generic_response_schemas_present(self, openapi_spec: Dict[str, Any]):
        """验证泛型响应schema存在"""
        schemas = openapi_spec.get("components", {}).get("schemas", {})

        # FastAPI会为泛型生成独立的schema名称
        # 检查是否有类似UnifiedResponse_TaskResponse_的schema
        generic_schemas = [name for name in schemas.keys() if name.startswith("UnifiedResponse_")]

        assert len(generic_schemas) > 0, "未找到泛型响应schema"

        print(f"✅ 发现 {len(generic_schemas)} 个泛型响应schema")

    def test_endpoint_count_validation(self, openapi_spec: Dict[str, Any]):
        """验证端点数量符合预期"""
        paths = openapi_spec.get("paths", {})

        endpoint_count = 0
        for path, path_item in paths.items():
            for method in path_item.keys():
                if method in ["get", "post", "put", "delete", "patch"]:
                    endpoint_count += 1

        # 预期至少30个端点（6个领域 * 平均5个端点）
        assert endpoint_count >= 30, f"端点数量不足: {endpoint_count} < 30"

        print(f"✅ OpenAPI包含 {endpoint_count} 个API端点")


class TestSwaggerUIAccessibility:
    """Swagger UI可访问性验证"""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture(scope="class")
    def swagger_html(self):
        """获取Swagger UI HTML"""
        try:
            response = requests.get(f"{self.BASE_URL}/docs")
            assert response.status_code == 200, f"无法访问Swagger UI: {response.status_code}"
            return response.text
        except requests.exceptions.ConnectionError:
            pytest.skip("API服务器未运行，跳过Swagger UI验证测试")

    def test_swagger_ui_loads_properly(self, swagger_html: str):
        """验证Swagger UI正确加载"""
        assert "<title>Swagger UI</title>" in swagger_html
        assert "swagger-ui" in swagger_html.lower()
        assert "openapi.json" in swagger_html

    def test_swagger_ui_contains_api_endpoints(self, swagger_html: str):
        """验证Swagger UI包含API端点"""
        # 检查是否包含一些关键端点
        key_endpoints = [
            "/api/v1/tasks",
            "/api/v1/focus/sessions",
            "/api/v1/chat/sessions",
            "/api/v1/auth/guest/init"
        ]

        for endpoint in key_endpoints:
            assert endpoint in swagger_html, f"Swagger UI缺少端点: {endpoint}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])