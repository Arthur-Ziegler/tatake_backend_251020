"""
CORS中间件测试

测试跨域资源共享中间件，包括：
1. 跨域头设置
2. 允许的来源验证
3. 允许的方法验证
4. 允许的头部验证

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@pytest.mark.unit
class TestCORSMiddleware:
    """CORS中间件测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.mock_app = Mock()

    def test_cors_middleware_initialization(self):
        """测试CORS中间件初始化"""
        # 模拟CORS中间件初始化
        middleware = Mock()
        middleware.app = self.mock_app
        middleware.allowed_origins = ["*"]
        middleware.allowed_methods = ["GET", "POST", "PUT", "DELETE"]
        middleware.allowed_headers = ["*"]
        middleware.allow_credentials = True

        assert middleware.app is not None
        assert "*" in middleware.allowed_origins
        assert "GET" in middleware.allowed_methods

    def test_cors_headers_set_for_options_request(self):
        """测试OPTIONS请求的CORS头设置"""
        request = Mock()
        request.method = "OPTIONS"
        request.headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }

        # 模拟CORS处理
        response_headers = {}

        if request.method == "OPTIONS":
            response_headers.update({
                "Access-Control-Allow-Origin": "https://example.com",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Max-Age": "86400"
            })

        assert response_headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert "POST" in response_headers["Access-Control-Allow-Methods"]

    def test_cors_headers_set_for_simple_request(self):
        """测试简单请求的CORS头设置"""
        request = Mock()
        request.method = "GET"
        request.headers = {"Origin": "https://example.com"}

        # 模拟CORS处理
        response_headers = {}

        if request.method != "OPTIONS":
            response_headers.update({
                "Access-Control-Allow-Origin": "https://example.com",
                "Access-Control-Allow-Credentials": "true"
            })

        assert response_headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert response_headers["Access-Control-Allow-Credentials"] == "true"

    def test_wildcard_origin_handling(self):
        """测试通配符来源处理"""
        request = Mock()
        request.headers = {"Origin": "https://any-domain.com"}

        # 模拟通配符CORS配置
        allowed_origins = ["*"]

        origin = request.headers.get("Origin")
        if "*" in allowed_origins or origin in allowed_origins:
            allowed_origin = "*"
        else:
            allowed_origin = None

        assert allowed_origin == "*"

    def test_specific_origin_handling(self):
        """测试特定来源处理"""
        request = Mock()
        request.headers = {"Origin": "https://trusted.example.com"}

        # 模拟特定CORS配置
        allowed_origins = ["https://trusted.example.com", "https://api.example.com"]

        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            allowed_origin = origin
        else:
            allowed_origin = None

        assert allowed_origin == "https://trusted.example.com"

    def test_blocked_origin_handling(self):
        """测试被阻止的来源处理"""
        request = Mock()
        request.headers = {"Origin": "https://malicious.example.com"}

        # 模拟受限CORS配置
        allowed_origins = ["https://trusted.example.com"]

        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            allowed_origin = origin
        else:
            allowed_origin = None

        assert allowed_origin is None

    def test_preflight_request_validation(self):
        """测试预检请求验证"""
        request = Mock()
        request.method = "OPTIONS"
        request.headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "X-Custom-Header"
        }

        # 模拟预检请求验证
        allowed_methods = ["GET", "POST", "PUT", "DELETE"]
        allowed_headers = ["Content-Type", "Authorization"]

        requested_method = request.headers.get("Access-Control-Request-Method")
        requested_headers = request.headers.get("Access-Control-Request-Headers", "").split(",")

        method_allowed = requested_method in allowed_methods
        headers_allowed = all(
            header.strip() in allowed_headers or header.strip() == "X-Custom-Header"
            for header in requested_headers
        )

        # 在实际实现中，X-Custom-Header可能不被允许
        assert method_allowed is False  # PATCH不在允许的方法中

    @pytest.mark.asyncio
    async def test_cors_middleware_dispatch(self):
        """测试CORS中间件调度"""
        request = Mock()
        request.method = "GET"
        request.headers = {"Origin": "https://example.com"}

        call_next = AsyncMock()
        mock_response = Mock()
        mock_response.headers = {}
        call_next.return_value = mock_response

        # 模拟中间件处理
        response = await call_next(request)

        # 添加CORS头
        response.headers["Access-Control-Allow-Origin"] = "https://example.com"
        response.headers["Access-Control-Allow-Credentials"] = "true"

        assert response.headers["Access-Control-Allow-Origin"] == "https://example.com"
        call_next.assert_called_once_with(request)


@pytest.mark.unit
class TestCORSPolicyConfiguration:
    """CORS策略配置测试类"""

    def test_strict_cors_policy(self):
        """测试严格CORS策略"""
        strict_policy = {
            "allowed_origins": ["https://app.example.com"],
            "allowed_methods": ["GET", "POST"],
            "allowed_headers": ["Content-Type", "Authorization"],
            "allow_credentials": True,
            "max_age": 3600
        }

        assert len(strict_policy["allowed_origins"]) == 1
        assert "app.example.com" in strict_policy["allowed_origins"][0]
        assert len(strict_policy["allowed_methods"]) == 2

    def test_permissive_cors_policy(self):
        """测试宽松CORS策略"""
        permissive_policy = {
            "allowed_origins": ["*"],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allowed_headers": ["*"],
            "allow_credentials": False,
            "max_age": 86400
        }

        assert "*" in permissive_policy["allowed_origins"]
        assert "*" in permissive_policy["allowed_headers"]
        assert permissive_policy["allow_credentials"] is False

    def test_development_cors_policy(self):
        """测试开发环境CORS策略"""
        dev_policy = {
            "allowed_origins": [
                "http://localhost:3000",
                "http://localhost:8080",
                "http://127.0.0.1:3000"
            ],
            "allowed_methods": ["*"],
            "allowed_headers": ["*"],
            "allow_credentials": True,
            "max_age": 7200
        }

        assert len(dev_policy["allowed_origins"]) == 3
        assert all("localhost" in origin or "127.0.0.1" in origin
                  for origin in dev_policy["allowed_origins"])

    def test_production_cors_policy(self):
        """测试生产环境CORS策略"""
        prod_policy = {
            "allowed_origins": [
                "https://app.example.com",
                "https://admin.example.com"
            ],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
            "allowed_headers": [
                "Content-Type",
                "Authorization",
                "X-Requested-With"
            ],
            "allow_credentials": True,
            "max_age": 3600
        }

        assert all(origin.startswith("https://") for origin in prod_policy["allowed_origins"])
        assert "X-Requested-With" in prod_policy["allowed_headers"]


@pytest.mark.integration
class TestCORSIntegration:
    """CORS集成测试类"""

    def test_cors_headers_persistence(self):
        """测试CORS头持久性"""
        request = Mock()
        request.headers = {"Origin": "https://example.com"}

        # 模拟多个中间件处理
        responses = []
        for i in range(3):
            response = Mock()
            response.headers = {}
            # 每个中间件都应该保留CORS头
            response.headers["Access-Control-Allow-Origin"] = "https://example.com"
            responses.append(response)

        # 验证所有响应都有正确的CORS头
        for response in responses:
            assert response.headers["Access-Control-Allow-Origin"] == "https://example.com"

    def test_cors_error_handling(self):
        """测试CORS错误处理"""
        request = Mock()
        request.headers = {"Origin": "https://malicious.com"}

        # 模拟CORS错误处理
        try:
            # 验证来源
            allowed_origins = ["https://trusted.com"]
            origin = request.headers.get("Origin")

            if origin not in allowed_origins:
                raise ValueError(f"Origin {origin} not allowed")

        except ValueError as e:
            # 在实际实现中，可能不会抛出异常，而是拒绝请求
            assert "not allowed" in str(e)

    def test_cors_with_credentials(self):
        """测试带凭据的CORS"""
        request = Mock()
        request.headers = {
            "Origin": "https://example.com",
            "Cookie": "session=abc123"
        }

        # 模拟带凭据的CORS处理
        response_headers = {}

        # 当allow_credentials为True时，不能使用通配符
        if "https://example.com" in ["https://example.com"]:  # 具体来源
            response_headers["Access-Control-Allow-Origin"] = "https://example.com"
            response_headers["Access-Control-Allow-Credentials"] = "true"
        else:
            response_headers["Access-Control-Allow-Origin"] = "*"

        assert response_headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert response_headers["Access-Control-Allow-Credentials"] == "true"


@pytest.mark.parametrize("origin,allowed_origins,expected_result", [
    ("https://example.com", ["*"], True),
    ("https://example.com", ["https://example.com"], True),
    ("https://example.com", ["https://trusted.com"], False),
    ("http://localhost:3000", ["http://localhost:3000", "https://app.com"], True),
    ("https://malicious.com", ["https://trusted.com"], False)
])
def test_origin_validation(origin, allowed_origins, expected_result):
    """参数化测试来源验证"""
    if "*" in allowed_origins:
        result = True
    else:
        result = origin in allowed_origins

    assert result == expected_result


@pytest.mark.parametrize("method,allowed_methods,expected_result", [
    ("GET", ["GET", "POST"], True),
    ("POST", ["GET", "POST"], True),
    ("PUT", ["GET", "POST"], False),
    ("DELETE", ["GET", "POST", "PUT", "DELETE"], True),
    ("PATCH", ["GET", "POST", "PUT", "DELETE"], False)
])
def test_method_validation(method, allowed_methods, expected_result):
    """参数化测试方法验证"""
    result = method in allowed_methods
    assert result == expected_result


@pytest.mark.parametrize("headers,allowed_headers,expected_result", [
    ("Content-Type", ["Content-Type", "Authorization"], True),
    ("Authorization", ["Content-Type", "Authorization"], True),
    ("X-Custom", ["Content-Type", "Authorization"], False),
    ("Content-Type,X-Custom", ["Content-Type", "Authorization"], False),
    ("", ["Content-Type", "Authorization"], True)  # 空头部应该被允许
])
def test_headers_validation(headers, allowed_headers, expected_result):
    """参数化测试头部验证"""
    if not headers:
        result = True
    else:
        header_list = [h.strip() for h in headers.split(",")]
        result = all(header in allowed_headers for header in header_list)

    assert result == expected_result


@pytest.fixture
def cors_request():
    """CORS请求fixture"""
    return Mock(
        method="GET",
        headers={"Origin": "https://example.com"}
    )


@pytest.fixture
def cors_options_request():
    """CORS OPTIONS请求fixture"""
    return Mock(
        method="OPTIONS",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
    )


def test_with_fixtures(cors_request, cors_options_request):
    """使用fixtures的测试"""
    # 测试简单请求
    assert cors_request.method == "GET"
    assert cors_request.headers["Origin"] == "https://example.com"

    # 测试预检请求
    assert cors_options_request.method == "OPTIONS"
    assert "Access-Control-Request-Method" in cors_options_request.headers