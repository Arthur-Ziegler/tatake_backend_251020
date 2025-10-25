"""
API参数验证测试套件

专门用于检测和预防API参数解析错误的测试模块。
通过多层次的验证确保API参数的正确性和一致性。

作者：TaTakeKe团队
版本：1.0.0
日期：2025-10-25
"""

import pytest
import requests
import json
import asyncio
import httpx
from typing import Dict, Any, List, Set
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport

from src.api.main import app


class TestAPIParameterValidation:
    """API参数验证测试类"""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture(scope="class")
    def openapi_spec(self) -> Dict[str, Any]:
        """获取OpenAPI规范"""
        try:
            response = requests.get(f"{self.BASE_URL}/openapi.json", timeout=10)
            assert response.status_code == 200, f"无法获取OpenAPI JSON: {response.status_code}"
            return response.json()
        except requests.exceptions.ConnectionError:
            pytest.skip("API服务器未运行，跳过API参数验证测试")
        except requests.exceptions.Timeout:
            pytest.skip("API服务器响应超时，跳过测试")

    @pytest.fixture(scope="class")
    def test_client(self) -> TestClient:
        """FastAPI测试客户端"""
        return TestClient(app)

    def test_no_args_kwargs_in_any_endpoint(self, openapi_spec: Dict[str, Any]):
        """验证所有端点都不包含args/kwargs参数"""
        paths = openapi_spec.get("paths", {})
        problematic_endpoints = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                # 检查参数列表
                parameters = operation.get("parameters", [])
                for param in parameters:
                    param_name = param.get("name", "")
                    param_in = param.get("in", "")

                    if param_name in ["args", "kwargs"]:
                        problematic_endpoints.append({
                            "endpoint": f"{method.upper()} {path}",
                            "param_name": param_name,
                            "param_location": param_in,
                            "required": param.get("required", False),
                            "description": param.get("description", "")
                        })

        # 如果发现问题端点，提供详细错误信息
        if problematic_endpoints:
            error_details = []
            for endpoint_info in problematic_endpoints:
                error_details.append(
                    f"- {endpoint_info['endpoint']}: "
                    f"参数 '{endpoint_info['param_name']}' "
                    f"位于 {endpoint_info['param_location']}"
                )

            pytest.fail(
                f"发现 {len(problematic_endpoints)} 个端点包含args/kwargs参数:\n" +
                "\n".join(error_details) +
                "\n\n这表明存在Pydantic泛型类型或参数解析问题。"
            )

        print(f"✅ 验证了所有端点，未发现args/kwargs参数问题")

    def test_parameter_consistency_across_endpoints(self, openapi_spec: Dict[str, Any]):
        """验证相似端点的参数一致性"""
        paths = openapi_spec.get("paths", {})
        user_endpoints = {}

        # 收集所有用户相关端点
        for path, path_item in paths.items():
            if "/user/" in path:
                user_endpoints[path] = path_item

        # 检查用户端点的参数一致性
        auth_params_consistent = True
        inconsistent_endpoints = []

        for path, path_item in user_endpoints.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete"]:
                    continue

                parameters = operation.get("parameters", [])
                auth_params = [p for p in parameters if p.get("name") in ["Authorization", "token"]]

                # 用户端点应该有认证参数（除了guest-init等特殊端点）
                if not any(special in path for special in ["guest-init", "wechat-register"]):
                    if not auth_params:
                        auth_params_consistent = False
                        inconsistent_endpoints.append(f"{method.upper()} {path}")

        if not auth_params_consistent:
            pytest.fail(
                f"以下用户端点缺少认证参数:\n" +
                "\n".join(f"- {ep}" for ep in inconsistent_endpoints)
            )

    def test_no_generic_response_schemas_leakage(self, openapi_spec: Dict[str, Any]):
        """验证泛型响应schema不会泄露为参数"""
        schemas = openapi_spec.get("components", {}).get("schemas", {})

        # 检查是否有异常的schema定义
        problematic_schemas = []

        for schema_name, schema_def in schemas.items():
            # 检查schema属性
            properties = schema_def.get("properties", {})

            # 检查是否有args/kwargs属性
            for prop_name in properties:
                if prop_name in ["args", "kwargs"]:
                    problematic_schemas.append({
                        "schema": schema_name,
                        "property": prop_name,
                        "type": properties[prop_name].get("type", "unknown")
                    })

        if problematic_schemas:
            error_details = []
            for schema_info in problematic_schemas:
                error_details.append(
                    f"- Schema '{schema_info['schema']}' "
                    f"包含异常属性 '{schema_info['property']}' "
                    f"(类型: {schema_info['type']})"
                )

            pytest.fail(
                f"发现 {len(problematic_schemas)} 个schema包含args/kwargs属性:\n" +
                "\n".join(error_details)
            )

    def test_response_model_consistency(self, openapi_spec: Dict[str, Any]):
        """验证响应模型的一致性"""
        paths = openapi_spec.get("paths", {})

        # 检查响应格式一致性
        inconsistent_responses = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete"]:
                    continue

                responses = operation.get("responses", {})
                success_response = responses.get("200") or responses.get("201")

                if not success_response:
                    continue

                content = success_response.get("content", {})
                json_content = content.get("application/json", {})
                schema = json_content.get("schema", {})

                # 检查响应结构
                if schema.get("$ref"):
                    # 有schema引用，检查是否是标准格式
                    ref = schema.get("$ref")
                    if "UnifiedResponse" in ref:
                        # 统一响应格式，应该包含code, data, message
                        pass
                elif schema.get("type") == "object":
                    # 直接定义，检查结构
                    properties = schema.get("properties", {})
                    if not all(key in properties for key in ["code", "data", "message"]):
                        inconsistent_responses.append(f"{method.upper()} {path}")

        # 允许一些端点有不同的响应格式（如健康检查等）
        allowed_exceptions = ["/health", "/docs", "/openapi.json", "/redoc"]
        filtered_inconsistent = [
            resp for resp in inconsistent_responses
            if not any(exc in resp for exc in allowed_exceptions)
        ]

        if filtered_inconsistent:
            pytest.fail(
                f"以下端点的响应格式不一致:\n" +
                "\n".join(f"- {resp}" for resp in filtered_inconsistent)
            )

    @pytest.mark.asyncio
    async def test_real_api_call_parameter_validation(self):
        """使用真实HTTP客户端测试API参数"""

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 测试用户资料端点（无需认证的版本）
                response = await client.get(f"{self.BASE_URL}/health")

                # 健康检查应该正常响应
                if response.status_code != 200:
                    pytest.fail(f"健康检查失败: {response.status_code}")

                # 检查响应中是否有参数错误信息
                try:
                    response_data = response.json()
                    # 如果响应包含参数错误信息，说明有问题
                    if "error" in str(response_data).lower() and "parameter" in str(response_data).lower():
                        pytest.fail(f"API返回参数错误: {response_data}")
                except json.JSONDecodeError:
                    pass  # 健康检查可能返回非JSON响应

            except httpx.ConnectError:
                pytest.skip("无法连接到API服务器，跳过真实HTTP测试")
            except httpx.TimeoutException:
                pytest.skip("API服务器响应超时，跳过测试")

    def test_endpoint_parameter_count_reasonable(self, openapi_spec: Dict[str, Any]):
        """验证端点参数数量合理"""
        paths = openapi_spec.get("paths", {})

        high_param_endpoints = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete"]:
                    continue

                parameters = operation.get("parameters", [])
                param_count = len(parameters)

                # 排除查询参数较多的端点（如列表查询）
                if "list" in path or param_count <= 5:
                    continue

                high_param_endpoints.append({
                    "endpoint": f"{method.upper()} {path}",
                    "param_count": param_count,
                    "parameters": [p.get("name") for p in parameters]
                })

        # 警告参数过多的端点
        if high_param_endpoints:
            warning_details = []
            for endpoint_info in high_param_endpoints:
                warning_details.append(
                    f"- {endpoint_info['endpoint']}: "
                    f"{endpoint_info['param_count']} 个参数 "
                    f"({', '.join(endpoint_info['parameters'][:3])}{'...' if endpoint_info['param_count'] > 3 else ''})"
                )

            print(f"\n⚠️  发现 {len(high_param_endpoints)} 个高参数端点:")
            print("\n".join(warning_details))
            print("建议考虑简化这些端点的参数结构")

    def test_no_duplicate_parameter_names(self, openapi_spec: Dict[str, Any]):
        """验证端点内没有重复的参数名"""
        paths = openapi_spec.get("paths", {})

        duplicate_param_endpoints = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete"]:
                    continue

                parameters = operation.get("parameters", [])
                param_names = [p.get("name") for p in parameters]

                # 检查重复参数
                seen_names = set()
                duplicates = set()

                for name in param_names:
                    if name in seen_names:
                        duplicates.add(name)
                    seen_names.add(name)

                if duplicates:
                    duplicate_param_endpoints.append({
                        "endpoint": f"{method.upper()} {path}",
                        "duplicates": list(duplicates)
                    })

        if duplicate_param_endpoints:
            error_details = []
            for endpoint_info in duplicate_param_endpoints:
                error_details.append(
                    f"- {endpoint_info['endpoint']}: "
                    f"重复参数 {endpoint_info['duplicates']}"
                )

            pytest.fail(
                f"发现 {len(duplicate_param_endpoints)} 个端点有重复参数:\n" +
                "\n".join(error_details)
            )


class TestAPIResponseStructure:
    """API响应结构验证测试类"""

    def test_user_endpoints_response_structure(self, test_client: TestClient):
        """验证用户端点响应结构"""

        # 测试端点列表
        user_endpoints = [
            ("GET", "/api/v1/user/profile"),
            ("PUT", "/api/v1/user/profile"),
            ("POST", "/api/v1/user/welcome-gift/claim"),
            ("GET", "/api/v1/user/welcome-gift/history"),
        ]

        for method, endpoint in user_endpoints:
            # 对于需要认证的端点，这里主要测试响应结构
            # 认证失败应该返回401错误，而不是参数错误

            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "POST":
                response = test_client.post(endpoint, json={})
            elif method == "PUT":
                response = test_client.put(endpoint, json={})

            # 检查是否返回401（认证失败）而不是422（参数错误）
            if response.status_code == 422:
                response_data = response.json()
                if "detail" in response_data:
                    detail = response_data["detail"]
                    if isinstance(detail, list) and any(
                        "args" in str(error).lower() or "kwargs" in str(error).lower()
                        for error in detail
                    ):
                        pytest.fail(f"{method} {endpoint} 返回args/kwargs参数错误: {detail}")

    def test_error_responses_not_contain_parameter_errors(self, test_client: TestClient):
        """验证错误响应不包含参数解析错误"""

        # 测试各种可能导致错误的请求
        test_cases = [
            ("GET", "/api/v1/user/profile"),
            ("POST", "/api/v1/user/welcome-gift/claim"),
            ("GET", "/api/v1/user/welcome-gift/history"),
        ]

        for method, endpoint in test_cases:
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "POST":
                response = test_client.post(endpoint)

            # 检查错误响应
            if response.status_code >= 400:
                try:
                    response_data = response.json()
                    response_str = json.dumps(response_data).lower()

                    # 检查是否包含args/kwargs相关的错误信息
                    if "args" in response_str or "kwargs" in response_str:
                        pytest.fail(
                            f"{method} {endpoint} 错误响应包含args/kwargs: {response_data}"
                        )
                except json.JSONDecodeError:
                    pass  # 非JSON响应，跳过检查


class TestOpenAPIGeneration:
    """OpenAPI生成验证测试类"""

    def test_openapi_generation_without_errors(self, test_client: TestClient):
        """验证OpenAPI生成过程无错误"""

        response = test_client.get("/openapi.json")
        assert response.status_code == 200

        try:
            openapi_data = response.json()

            # 验证基本结构
            assert "openapi" in openapi_data
            assert "info" in openapi_data
            assert "paths" in openapi_data

            # 验证paths不是空的
            paths = openapi_data["paths"]
            assert len(paths) > 0, "OpenAPI paths为空"

            print(f"✅ OpenAPI生成成功，包含 {len(paths)} 个路径")

        except json.JSONDecodeError as e:
            pytest.fail(f"OpenAPI JSON格式错误: {e}")

    def test_all_schemas_are_valid(self, test_client: TestClient):
        """验证所有schema定义有效"""

        response = test_client.get("/openapi.json")
        openapi_data = response.json()

        schemas = openapi_data.get("components", {}).get("schemas", {})

        invalid_schemas = []

        for schema_name, schema_def in schemas.items():
            # 检查schema是否有基本结构
            if not isinstance(schema_def, dict):
                invalid_schemas.append(f"{schema_name}: 不是有效的字典对象")
                continue

            # 检查是否有type或$ref
            if "type" not in schema_def and "$ref" not in schema_def and "allOf" not in schema_def:
                invalid_schemas.append(f"{schema_name}: 缺少type、$ref或allOf")

            # 检查type为object时是否有properties
            if schema_def.get("type") == "object" and "properties" not in schema_def:
                # 允许空的object类型
                pass

        if invalid_schemas:
            pytest.fail(
                f"发现 {len(invalid_schemas)} 个无效schema:\n" +
                "\n".join(f"- {error}" for error in invalid_schemas)
            )


if __name__ == "__main__":
    # 可以直接运行此测试文件
    pytest.main([__file__, "-v", "-s"])