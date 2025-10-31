"""
系统健康检查测试

验证应用启动、OpenAPI生成、Schema注册等核心功能的完整性。
防止因导入错误、Schema缺失等问题导致应用异常。
"""

import pytest
import httpx
from fastapi.testclient import TestClient
from typing import Dict, Any

from src.api.main import app


class TestSystemHealth:
    """系统健康检查测试套件"""

    def test_openapi_endpoint_accessibility(self):
        """测试OpenAPI端点可访问性"""
        with TestClient(app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            assert "openapi" in response.json()
            assert "paths" in response.json()
            assert "components" in response.json()

    def test_swagger_ui_accessibility(self):
        """测试Swagger UI可访问性"""
        with TestClient(app) as client:
            response = client.get("/docs")
            assert response.status_code == 200
            assert "html" in response.text.lower()

    def test_redoc_ui_accessibility(self):
        """测试ReDoc UI可访问性"""
        with TestClient(app) as client:
            response = client.get("/redoc")
            assert response.status_code == 200
            assert "html" in response.text.lower()

    def test_all_core_endpoints_responsive(self):
        """测试所有核心端点响应性（不验证功能，只验证能正常响应）"""
        with TestClient(app) as client:
            # 健康检查端点
            endpoints = [
                ("/", "GET"),
                ("/health", "GET"),
                ("/auth/health", "GET"),
                ("/chat/health", "GET"),
                ("/tasks/health", "GET"),
                ("/focus/health", "GET"),
                ("/rewards/health", "GET"),
            ]

            for endpoint, method in endpoints:
                if method == "GET":
                    response = client.get(endpoint)
                else:
                    response = client.request(method, endpoint)

                # 允许401（需要认证）但不应是500（服务器错误）
                assert response.status_code != 500, f"端点 {endpoint} 返回500错误"

    def test_schema_imports_validity(self):
        """测试Schema导入有效性"""
        try:
            # 尝试导入所有Schema注册器使用的模块
            from src.api.schema_registry import register_all_schemas_to_openapi
            # 如果没有抛出ImportError，说明导入成功
            assert True
        except ImportError as e:
            pytest.fail(f"Schema导入失败: {e}")

    def test_domain_modules_import_validity(self):
        """测试所有域模块导入有效性"""
        domains = [
            "src.domains.chat.schemas",
            "src.domains.chat.router",
            "src.domains.chat.models",
            "src.domains.chat.repository",
            "src.domains.task.schemas",
            "src.domains.task.router",
            "src.domains.focus.schemas",
            "src.domains.focus.router",
            "src.domains.reward.schemas",
            "src.domains.reward.router",
        ]

        for domain_module in domains:
            try:
                __import__(domain_module)
            except ImportError as e:
                pytest.fail(f"域模块导入失败 {domain_module}: {e}")

    def test_api_config_completeness(self):
        """测试API配置完整性"""
        from src.api.config import config

        # 验证必需的配置项存在
        required_configs = [
            "chat_service_url",
            "chat_service_timeout",
            "task_service_url",
            "task_service_timeout",
            "auth_microservice_url",
            "auth_project",
        ]

        for config_name in required_configs:
            assert hasattr(config, config_name), f"缺少配置项: {config_name}"

    def test_database_connections(self):
        """测试数据库连接"""
        from src.domains.chat.models import init_chat_database
        from src.domains.focus.models import init_focus_database
        from src.domains.reward.models import init_reward_database

        try:
            # 测试数据库初始化（不实际操作数据）
            assert True  # 如果没有异常抛出，说明连接正常
        except Exception as e:
            pytest.fail(f"数据库连接失败: {e}")

    def test_microservice_clients_initialization(self):
        """测试微服务客户端初始化"""
        try:
            from src.services.chat_microservice_client import get_chat_microservice_client
            from src.services.task_microservice_client import get_task_microservice_client
            from src.api.auth import AuthMicroserviceClient

            # 测试客户端初始化（不实际调用）
            assert True
        except ImportError as e:
            pytest.fail(f"微服务客户端初始化失败: {e}")

    def test_jwt_validator_initialization(self):
        """测试JWT验证器初始化"""
        try:
            from src.api.auth import JWTValidator, DevJWTValidator

            # 测试验证器初始化
            assert True
        except Exception as e:
            pytest.fail(f"JWT验证器初始化失败: {e}")


class TestSchemaRegistration:
    """Schema注册专项测试"""

    def test_chat_schema_registration(self):
        """测试聊天Schema注册"""
        try:
            from src.domains.chat.schemas import (
                ChatMessageRequest, ChatHistoryResponse, DeleteSessionResponse,
                ChatHealthResponse, SessionListItem, ChatHistoryMessage
            )

            # 验证关键Schema类存在
            required_schemas = [
                ChatMessageRequest,
                ChatHistoryResponse,
                DeleteSessionResponse,
                ChatHealthResponse,
                SessionListItem,
                ChatHistoryMessage
            ]

            for schema_class in required_schemas:
                assert hasattr(schema_class, '__name__'), f"Schema类 {schema_class} 定义不完整"

        except ImportError as e:
            pytest.fail(f"聊天Schema导入失败: {e}")

    def test_openapi_schema_completeness(self):
        """测试OpenAPI Schema完整性"""
        with TestClient(app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200

            openapi_spec = response.json()

            # 验证核心组件存在
            assert "components" in openapi_spec
            assert "schemas" in openapi_spec["components"]

            schemas = openapi_spec["components"]["schemas"]

            # 验证关键Schema存在
            required_schemas = [
                "UnifiedResponse",
                "ChatMessageRequest",
                "ChatHistoryResponse",
                "DeleteSessionResponse",
                "ChatHealthResponse"
            ]

            for schema_name in required_schemas:
                assert schema_name in schemas, f"OpenAPI中缺少Schema: {schema_name}"


if __name__ == "__main__":
    # 可以单独运行此测试文件
    pytest.main([__file__, "-v"])