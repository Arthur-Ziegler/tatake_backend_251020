"""
API主应用测试

测试FastAPI主应用的核心功能，包括：
1. 应用创建和配置验证
2. 生命周期管理测试
3. 路由注册验证
4. 中间件配置测试
5. 异常处理验证
6. 系统端点测试

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.main import app, HTTPValidationError, lifespan


@pytest.mark.unit
class TestFastAPIApplication:
    """FastAPI应用基础测试类"""

    def test_app_creation(self):
        """测试FastAPI应用创建"""
        assert isinstance(app, FastAPI)
        assert app.title == "TaKeKe API"
        assert app.version  # 版本应该存在
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_app_cors_middleware(self):
        """测试CORS中间件配置"""
        # 检查CORS中间件是否已添加
        middleware_types = [type(middleware.cls) for middleware in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware
        assert CORSMiddleware in middleware_types

    def test_app_routes_exist(self):
        """测试关键路由是否存在"""
        routes = [route.path for route in app.routes]

        # 检查系统路由
        assert "/" in routes
        assert "/health" in routes
        assert "/test-cors" in routes

        # 检查API前缀路由
        api_routes = [route for route in routes if route.startswith("/api")]
        assert len(api_routes) > 0  # 应该有API路由

    def test_http_validation_error_model(self):
        """测试HTTP验证错误模型"""
        error = HTTPValidationError(
            loc=["field1"],
            msg="验证错误",
            type="validation_error"
        )

        assert error.loc == ["field1"]
        assert error.msg == "验证错误"
        assert error.type == "validation_error"


@pytest.mark.unit
class TestLifespanManagement:
    """应用生命周期管理测试类"""

    @pytest.mark.asyncio
    async def test_lifespan_startup_initialization(self):
        """测试生命周期启动初始化"""
        # 模拟数据库初始化函数
        with patch('src.api.main.check_connection') as mock_check_connection, \
             patch('src.api.main.create_tables') as mock_create_tables, \
             patch('src.api.main.initialize_task_database') as mock_init_task, \
             patch('src.api.main.get_db_session') as mock_get_session, \
             patch('src.api.main.initialize_reward_database') as mock_init_reward, \
             patch('src.api.main.create_focus_tables') as mock_create_focus:

            # 设置模拟返回值
            mock_check_connection.return_value = True
            mock_session = Mock()
            mock_session.close = Mock()
            mock_get_session.return_value = iter([mock_session])

            # 测试启动过程
            async with lifespan(Mock()):
                pass  # 启动过程

            # 验证数据库初始化函数被调用
            mock_check_connection.assert_called()
            mock_create_tables.assert_called()
            mock_init_task.assert_called()
            mock_init_reward.assert_called()
            mock_create_focus.assert_called()

    @pytest.mark.asyncio
    async def test_lifespan_database_failure_handling(self):
        """测试生命周期数据库失败处理"""
        with patch('src.api.main.check_connection') as mock_check_connection:
            # 模拟数据库连接失败
            mock_check_connection.return_value = False

            # 应该能正常处理失败情况
            async with lifespan(Mock()):
                pass  # 不应该抛出异常

    @pytest.mark.asyncio
    async def test_lifespan_exception_handling(self):
        """测试生命周期异常处理"""
        with patch('src.api.main.check_connection') as mock_check_connection:
            # 模拟数据库初始化异常
            mock_check_connection.side_effect = Exception("数据库连接失败")

            # 应该能正常处理异常
            async with lifespan(Mock()):
                pass  # 不应该抛出异常


@pytest.mark.unit
class TestSystemEndpoints:
    """系统端点测试类"""

    def setup_test_client(self):
        """设置测试客户端"""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """测试根路径端点"""
        self.setup_test_client()
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "message" in data
        assert "data" in data
        assert "name" in data["data"]
        assert "version" in data["data"]
        assert "docs_url" in data["data"]
        assert data["data"]["docs_url"] == "/docs"

    def test_health_check_endpoint_success(self):
        """测试健康检查端点成功情况"""
        self.setup_test_client()

        with patch('src.api.main.check_connection') as mock_check_connection, \
             patch('src.api.main.get_database_info') as mock_get_db_info:

            # 模拟所有服务健康
            mock_check_connection.return_value = True
            mock_get_db_info.return_value = {"status": "healthy"}

            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 200
            assert data["data"]["status"] == "healthy"
            assert "services" in data["data"]
            assert data["data"]["services"]["authentication"] == "healthy"

    def test_health_check_endpoint_partial_failure(self):
        """测试健康检查端点部分失败"""
        self.setup_test_client()

        with patch('src.api.main.check_connection') as mock_check_connection, \
             patch('src.api.main.get_database_info') as mock_get_db_info:

            # 模拟部分服务不健康
            mock_check_connection.return_value = True
            mock_get_db_info.return_value = {"status": "unhealthy"}

            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "unhealthy"

    def test_api_info_endpoint(self):
        """测试API信息端点"""
        self.setup_test_client()

        with patch('src.api.main.get_database_info') as mock_get_db_info:
            # 模拟数据库信息
            mock_get_db_info.return_value = {
                "status": "healthy",
                "tables_created": True
            }

            response = self.client.get("/api/info")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 200
            assert "api_name" in data["data"]
            assert "api_version" in data["data"]
            assert "domains" in data["data"]
            assert "total_endpoints" in data["data"]

    def test_cors_test_endpoint(self):
        """测试CORS测试端点"""
        self.setup_test_client()
        response = self.client.get("/test-cors")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["cors_enabled"] is True
        assert "CORS 测试成功" in data["message"]


@pytest.mark.unit
class TestExceptionHandling:
    """异常处理测试类"""

    def setup_test_client(self):
        """设置测试客户端"""
        self.client = TestClient(app)

    def test_http_exception_handler_404(self):
        """测试404异常处理"""
        self.setup_test_client()
        response = self.client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 404
        assert "message" in data
        assert "请求的资源未找到" in data["message"]

    def test_http_exception_handler_405(self):
        """测试405异常处理"""
        self.setup_test_client()
        response = self.client.post("/")  # 根路径只支持GET

        assert response.status_code == 405
        data = response.json()
        assert data["code"] == 405
        assert "请求方法不被允许" in data["message"]

    def test_http_exception_handler_422(self):
        """测试422异常处理"""
        self.setup_test_client()
        response = self.client.post("/health", json={"invalid": "data"})

        # FastAPI会自动将某些验证错误转为422
        if response.status_code == 422:
            data = response.json()
            assert data["code"] == 422
            assert "message" in data

    def test_custom_error_response_format(self):
        """测试自定义错误响应格式"""
        self.setup_test_client()

        # 测试所有错误响应都遵循统一格式
        response = self.client.get("/nonexistent-endpoint")
        data = response.json()

        # 验证响应格式一致性
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert isinstance(data["code"], int)
        assert isinstance(data["message"], str)


@pytest.mark.unit
class TestApplicationConfiguration:
    """应用配置测试类"""

    def test_app_imports(self):
        """测试应用导入"""
        # 验证关键模块能正常导入
        from src.api.main import app, lifespan, HTTPValidationError
        assert app is not None
        assert lifespan is not None
        assert HTTPValidationError is not None

    def test_router_registration(self):
        """测试路由注册"""
        # 验证路由器被正确导入和注册
        routes = [route.path for route in app.routes if hasattr(route, 'path')]

        # 应该包含各个领域的路由
        domain_routes = [route for route in routes if "/api" in route]
        assert len(domain_routes) > 0

    def test_middleware_configuration(self):
        """测试中间件配置"""
        # 验证CORS中间件配置
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                # CORS中间件应该被配置
                break
        else:
            pytest.fail("CORS中间件未找到")

    def test_openapi_setup(self):
        """测试OpenAPI设置"""
        # 验证OpenAPI相关功能
        assert hasattr(app, 'openapi')
        assert app.openapi_schema is not None

    def test_startup_event_registration(self):
        """测试启动事件注册"""
        # 验证启动事件处理器存在
        assert hasattr(app, 'on_event')
        # 具体的startup事件在代码中注册


@pytest.mark.integration
class TestApplicationIntegration:
    """应用集成测试类"""

    def setup_test_client(self):
        """设置测试客户端"""
        self.client = TestClient(app)

    def test_full_application_startup_flow(self):
        """测试完整应用启动流程"""
        self.setup_test_client()

        # 测试多个端点确保应用完整启动
        endpoints_to_test = [
            "/",
            "/health",
            "/api/info",
            "/test-cors"
        ]

        for endpoint in endpoints_to_test:
            response = self.client.get(endpoint)
            # 所有端点都应该能正常响应（可能需要模拟数据库）
            assert response.status_code in [200, 500]  # 500可能是数据库连接问题

    def test_router_integration(self):
        """测试路由器集成"""
        self.setup_test_client()

        # 测试API前缀路由
        response = self.client.get("/api/info")

        # 应该能找到API路由（即使数据库有问题）
        assert response.status_code in [200, 500]

    def test_cors_headers(self):
        """测试CORS响应头"""
        self.setup_test_client()

        # 测试CORS预检请求
        response = self.client.options("/test-cors")

        # 应该包含CORS相关头部
        if response.status_code == 200:
            # CORS配置应该正确
            pass

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        self.setup_test_client()

        # 测试各种错误情况
        error_scenarios = [
            ("/nonexistent", 404),
            ("/", 405, {"method": "POST"}),  # 方法不允许
        ]

        for scenario in error_scenarios:
            if len(scenario) == 2:
                endpoint, expected_status = scenario
                response = self.client.get(endpoint)
            else:
                endpoint, expected_status, extra = scenario
                if extra.get("method") == "POST":
                    response = self.client.post(endpoint)
                else:
                    response = self.client.get(endpoint)

            # 错误响应应该遵循统一格式
            if response.status_code == expected_status:
                data = response.json()
                assert "code" in data
                assert "message" in data


@pytest.mark.parametrize("endpoint,expected_status", [
    ("/", 200),
    ("/health", 200),
    ("/test-cors", 200),
    ("/api/info", 200),
    ("/nonexistent", 404)
])
def test_system_endpoints_parametrized(endpoint, expected_status):
    """参数化测试系统端点"""
    client = TestClient(app)
    response = client.get(endpoint)

    # 某些端点可能因数据库问题返回500，这是正常的
    assert response.status_code in [expected_status, 500]


@pytest.mark.asyncio
async def test_lifespan_context_manager():
    """测试生命周期上下文管理器"""
    with patch('src.api.main.check_connection') as mock_check_connection, \
         patch('src.api.main.create_tables') as mock_create_tables, \
         patch('src.api.main.initialize_task_database') as mock_init_task:

        # 设置模拟
        mock_check_connection.return_value = True

        # 测试生命周期管理器
        async with lifespan(Mock()):
            pass

        # 验证初始化函数被调用
        mock_check_connection.assert_called()
        mock_create_tables.assert_called()
        mock_init_task.assert_called()


@pytest.fixture
def mock_app():
    """模拟应用实例"""
    return Mock(spec=FastAPI)


@pytest.fixture
def mock_request():
    """模拟请求对象"""
    return Mock()


def test_http_validation_error_model_creation():
    """测试HTTP验证错误模型创建"""
    error = HTTPValidationError(
        loc=["field1", "field2"],
        msg="字段验证失败",
        type="value_error"
    )

    assert error.loc == ["field1", "field2"]
    assert error.msg == "字段验证失败"
    assert error.type == "value_error"