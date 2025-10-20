"""
OpenAPI文档系统测试

测试API文档生成、配置、元数据等功能是否正常工作。
"""

import pytest
import json
from fastapi.testclient import TestClient

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.main import app


class TestOpenAPIDocumentation:
    """OpenAPI文档系统测试类"""

    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)

    def test_openapi_schema_generation(self):
        """测试OpenAPI规范生成"""
        response = self.client.get("/openapi.json")

        # 验证响应状态
        assert response.status_code == 200

        # 解析JSON响应
        schema = response.json()

        # 验证必需字段
        required_fields = ["openapi", "info", "paths", "servers", "components"]
        for field in required_fields:
            assert field in schema, f"OpenAPI规范缺少必需字段: {field}"

        # 验证基本信息
        assert schema["openapi"].startswith("3.")
        assert schema["info"]["title"] == "TaKeKe API"
        assert "version" in schema["info"]
        assert len(schema["info"]["description"]) > 100

        # 验证服务器配置
        assert isinstance(schema["servers"], list)
        assert len(schema["servers"]) > 0

        # 验证安全方案
        assert "securitySchemes" in schema["components"]
        assert "BearerAuth" in schema["components"]["securitySchemes"]

        # 验证示例
        assert "examples" in schema["components"]

    def test_swagger_ui_accessibility(self):
        """测试Swagger UI文档可访问性"""
        response = self.client.get("/docs")

        # 验证响应状态
        assert response.status_code == 200

        # 验证响应是HTML
        assert "text/html" in response.headers["content-type"]

        # 验证包含Swagger相关内容
        html_content = response.text
        assert "swagger" in html_content.lower()
        assert "swagger-ui" in html_content.lower()

    def test_redoc_accessibility(self):
        """测试ReDoc文档可访问性"""
        response = self.client.get("/redoc")

        # 验证响应状态
        assert response.status_code == 200

        # 验证响应是HTML
        assert "text/html" in response.headers["content-type"]

        # 验证包含ReDoc相关内容
        html_content = response.text
        assert "redoc" in html_content.lower()

    def test_api_info_endpoint(self):
        """测试API信息端点"""
        response = self.client.get("/api-info")

        # 验证响应状态
        assert response.status_code == 200

        # 解析响应数据
        data = response.json()

        # 验证响应格式
        assert data["code"] == 200
        assert "data" in data
        assert "message" in data
        assert "timestamp" in data
        assert "traceId" in data

        # 验证API信息
        api_data = data["data"]
        assert "title" in api_data
        assert "version" in api_data
        assert "description" in api_data
        assert "contact" in api_data
        assert "license" in api_data

        # 验证统计信息
        assert "statistics" in api_data
        statistics = api_data["statistics"]
        assert "total_routes" in statistics
        assert "routes_by_tag" in statistics
        assert "documentation_urls" in statistics

        # 验证配置信息
        assert "configuration" in api_data
        configuration = api_data["configuration"]
        assert "api_prefix" in configuration
        assert "debug_mode" in configuration

    def test_docs_health_endpoint(self):
        """测试文档健康检查端点"""
        response = self.client.get("/docs-health")

        # 验证响应状态
        assert response.status_code == 200

        # 解析响应数据
        data = response.json()

        # 验证响应格式
        assert data["code"] == 200
        assert data["message"] == "文档服务健康"

        # 验证健康状态
        health_data = data["data"]
        assert health_data["status"] == "healthy"
        assert "services" in health_data
        assert "endpoints" in health_data

        # 验证服务状态
        services = health_data["services"]
        assert services["swagger_ui"] == "available"
        assert services["redoc"] == "available"
        assert services["openapi_json"] == "available"

        # 验证端点信息
        endpoints = health_data["endpoints"]
        assert endpoints["swagger_ui"] == "/docs"
        assert endpoints["redoc"] == "/redoc"
        assert endpoints["openapi_json"] == "/openapi.json"

    def test_openapi_tags_metadata(self):
        """测试OpenAPI标签元数据"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证标签存在
        assert "tags" in schema
        tags = schema["tags"]
        assert len(tags) > 0

        # 验证必需标签
        tag_names = [tag["name"] for tag in tags]
        assert "系统" in tag_names

        # 验证标签结构
        for tag in tags:
            assert "name" in tag
            assert "description" in tag

    def test_security_schemes(self):
        """测试安全认证方案"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证安全方案
        security_schemes = schema["components"]["securitySchemes"]
        assert "BearerAuth" in security_schemes

        # 验证Bearer认证方案
        bearer_auth = security_schemes["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"

        # 验证全局安全要求
        assert "security" in schema
        security = schema["security"]
        assert isinstance(security, list)
        assert len(security) > 0
        assert {"BearerAuth": []} in security

    def test_examples_in_schema(self):
        """测试响应示例"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证示例存在
        examples = schema["components"]["examples"]
        assert "success_response" in examples
        assert "error_response" in examples

        # 验证成功响应示例
        success_example = examples["success_response"]
        assert "summary" in success_example
        assert "value" in success_example
        example_data = success_example["value"]
        assert example_data["code"] == 200
        assert "data" in example_data
        assert "timestamp" in example_data
        assert "traceId" in example_data

        # 验证错误响应示例
        error_example = examples["error_response"]
        assert "summary" in error_example
        assert "value" in error_example
        example_data = error_example["value"]
        assert example_data["code"] >= 400
        assert "data" in example_data
        assert example_data["data"] is None

    def test_external_docs(self):
        """测试外部文档链接"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证外部文档
        assert "externalDocs" in schema
        external_docs = schema["externalDocs"]
        assert "description" in external_docs
        assert "url" in external_docs

    def test_contact_and_license_info(self):
        """测试联系人和许可证信息"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证联系人信息
        contact = schema["info"]["contact"]
        assert "name" in contact
        assert "url" in contact
        assert "email" in contact

        # 验证许可证信息
        license_info = schema["info"]["license"]
        assert "name" in license_info
        assert "url" in license_info

    def test_terms_of_service(self):
        """测试服务条款"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证服务条款
        assert "termsOfService" in schema["info"]
        terms_url = schema["info"]["termsOfService"]
        assert terms_url.startswith("http")

    def test_server_configuration(self):
        """测试服务器配置"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证服务器列表
        servers = schema["servers"]
        assert isinstance(servers, list)
        assert len(servers) > 0

        # 验证每个服务器配置
        for server in servers:
            assert "url" in server
            assert "description" in server
            assert server["url"].startswith("http")

    def test_extension_fields(self):
        """测试扩展字段"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证扩展字段
        assert "x-tag-groups" in schema
        tag_groups = schema["x-tag-groups"]
        assert isinstance(tag_groups, list)
        assert len(tag_groups) > 0

        # 验证标签分组
        for group in tag_groups:
            assert "name" in group
            assert "tags" in group
            assert isinstance(group["tags"], list)

    def test_api_schema_completeness(self):
        """测试API模式完整性"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 验证OpenAPI版本
        assert schema["openapi"].startswith("3.")

        # 验证必须字段
        required_top_level_fields = ["openapi", "info", "paths"]
        for field in required_top_level_fields:
            assert field in schema, f"缺少顶级字段: {field}"

        # 验证info字段完整性
        info_fields = ["title", "version", "description"]
        for field in info_fields:
            assert field in schema["info"], f"info缺少字段: {field}"

        # 验证components字段
        components = schema["components"]
        assert "securitySchemes" in components
        assert "examples" in components

        # 验证路径字段存在
        assert isinstance(schema["paths"], dict)


class TestOpenAPIIntegration:
    """OpenAPI集成测试类"""

    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)

    def test_docs_endpoints_with_trailing_slash(self):
        """测试带尾部斜杠的文档端点"""
        # 测试Swagger UI
        response = self.client.get("/docs/")
        assert response.status_code == 200

        # 测试ReDoc
        response = self.client.get("/redoc/")
        # FastAPI可能会重定向，所以检查200或3xx状态码
        assert response.status_code in [200, 307, 308]

    def test_openapi_content_type(self):
        """测试OpenAPI响应内容类型"""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_docs_cors_headers(self):
        """测试文档端点的CORS头"""
        response = self.client.get("/docs", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        # 检查是否有CORS相关的头
        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers

    def test_api_info_trace_id(self):
        """测试API信息端点的TraceID"""
        response = self.client.get("/api-info")
        data = response.json()

        # 验证TraceID存在且不为空
        assert "traceId" in data
        assert len(data["traceId"]) > 0

        # 验证响应头中的TraceID
        assert "x-request-id" in response.headers
        header_trace_id = response.headers["x-request-id"]
        assert header_trace_id == data["traceId"]

    def test_openapi_schema_validity(self):
        """测试OpenAPI模式有效性"""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # 基本结构验证
        assert isinstance(schema, dict)
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # 验证版本格式
        openapi_version = schema["openapi"]
        assert isinstance(openapi_version, str)
        assert openapi_version.startswith("3.")

        # 验证info结构
        info = schema["info"]
        assert isinstance(info, dict)
        assert "title" in info
        assert "version" in info
        assert isinstance(info["title"], str)
        assert isinstance(info["version"], str)

        # 验证paths结构
        paths = schema["paths"]
        assert isinstance(paths, dict)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])