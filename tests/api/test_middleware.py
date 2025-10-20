"""
核心中间件测试

测试CORS、认证、日志、限流、安全等核心中间件的配置和功能是否正常工作。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.main import app

# 创建测试客户端
client = TestClient(app)


class TestCORSMiddleware:
    """CORS中间件测试类"""

    def test_cors_preflight_request(self):
        """测试CORS预检请求"""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type"
        })

        # 验证CORS响应头
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
        assert "access-control-max-age" in response.headers

    def test_cors_simple_request(self):
        """测试CORS简单请求"""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        # 验证CORS响应头
        assert "access-control-allow-origin" in response.headers

    def test_cors_wildcard_origin(self):
        """测试CORS通配符源"""
        response = client.get("/", headers={"Origin": "http://test.example.com"})

        # 验证响应存在
        assert response.status_code == 200

    def test_cors_multiple_origins(self):
        """测试多个CORS源"""
        origins = ["http://localhost:3000", "https://tatake.app"]
        for origin in origins:
            response = client.get("/", headers={"Origin": origin})
            assert "access-control-allow-origin" in response.headers


class TestSecurityHeadersMiddleware:
    """安全头中间件测试类"""

    def test_security_headers_present(self):
        """测试安全头是否存在"""
        response = client.get("/")

        # 验证基本安全头
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "x-xss-protection" in response.headers
        assert "referrer-policy" in response.headers
        assert "content-security-policy" in response.headers

    def test_security_headers_values(self):
        """测试安全头的值"""
        response = client.get("/")

        # 验证具体的安全头值
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-xss-protection"] == "1; mode=block"

    def test_content_security_policy(self):
        """测试内容安全策略"""
        response = client.get("/")
        csp = response.headers["content-security-policy"]

        # 验证CSP包含基本指令
        assert "default-src 'self'" in csp
        assert "script-src" in csp
        assert "style-src" in csp
        assert "img-src" in csp
        assert "connect-src" in csp

    def test_permissions_policy(self):
        """测试权限策略"""
        response = client.get("/")
        permissions = response.headers["permissions-policy"]

        # 验证权限策略限制敏感功能
        assert "geolocation=()" in permissions
        assert "microphone=()" in permissions
        assert "camera=()" in permissions


class TestLoggingMiddleware:
    """日志中间件测试类"""

    def test_request_logging(self):
        """测试请求日志记录"""
        # 使用mock来验证日志调用
        with patch('builtins.print') as mock_print:
            response = client.get("/")

            # 验证日志被调用
            assert mock_print.called

            # 验证响应正常
            assert response.status_code == 200

    def test_request_id_generation(self):
        """测试请求ID生成"""
        response1 = client.get("/")
        response2 = client.get("/")

        # 验证每个请求都有唯一的ID
        request_id_1 = response1.headers.get("x-request-id")
        request_id_2 = response2.headers.get("x-request-id")

        assert request_id_1 is not None
        assert request_id_2 is not None
        assert request_id_1 != request_id_2

    def test_process_time_header(self):
        """测试处理时间头"""
        response = client.get("/")

        # 验证处理时间头存在且为数值
        assert "x-process-time" in response.headers
        process_time = response.headers["x-process-time"]
        assert float(process_time) >= 0

    def test_error_logging(self):
        """测试错误日志记录"""
        with patch('builtins.print') as mock_print:
            response = client.get("/nonexistent-endpoint")

            # 验证错误日志被调用
            assert mock_print.called

            # 验证错误响应
            assert response.status_code == 404


class TestRateLimitMiddleware:
    """限流中间件测试类"""

    def test_rate_limit_headers(self):
        """测试限流响应头"""
        response = client.get("/")

        # 验证限流相关头存在
        assert "x-rate-limit-limit" in response.headers
        assert "x-rate-limit-remaining" in response.headers
        assert "x-rate-limit-reset" in response.headers

    def test_rate_limit_values(self):
        """测试限流头的值"""
        response = client.get("/")

        # 验证限流头的值是合理的
        limit = int(response.headers["x-rate-limit-limit"])
        remaining = int(response.headers["x-rate-limit-remaining"])
        reset_time = int(response.headers["x-rate-limit-reset"])

        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit
        assert reset_time > 0

    def test_concurrent_requests(self):
        """测试并发请求"""
        # 发送多个请求测试限流
        responses = []
        for _ in range(5):
            response = client.get("/")
            responses.append(response)

        # 验证所有请求都成功（在测试环境下限流应该很宽松）
        for response in responses:
            assert response.status_code in [200, 429]  # 可能触发限流


class TestAuthenticationMiddleware:
    """认证中间件测试类"""

    def test_public_endpoint_access(self):
        """测试公开端点访问"""
        # 这些端点不需要认证
        public_endpoints = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

        for endpoint in public_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404]  # 有些可能不存在

    def test_protected_endpoint_no_auth(self):
        """测试需要认证的端点无认证访问"""
        # 这些端点需要认证（如果存在的话）
        protected_endpoints = [
            "/api/v1/auth/user-info",
            "/api/v1/tasks",
            "/api/v1/focus/sessions"
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # 应该返回401或404（端点可能还不存在）
            assert response.status_code in [401, 404]

    def test_auth_header_parsing(self):
        """测试认证头解析"""
        # 测试无效的认证头
        response = client.get(
            "/api/v1/auth/user-info",
            headers={"Authorization": "invalid token"}
        )
        # 应该返回401或404
        assert response.status_code in [401, 404]


class TestMiddlewareIntegration:
    """中间件集成测试类"""

    def test_all_middleware_work_together(self):
        """测试所有中间件协同工作"""
        response = client.get("/", headers={
            "Origin": "http://localhost:3000",
            "User-Agent": "Test Client",
            "Accept": "application/json"
        })

        # 验证响应正常
        assert response.status_code == 200

        # 验证所有中间件都添加了相应的头
        expected_headers = [
            "x-request-id",           # 日志中间件
            "x-process-time",        # 日志中间件
            "x-rate-limit-limit",     # 限流中间件
            "x-rate-limit-remaining",  # 限流中间件
            "x-rate-limit-reset",      # 限流中间件
            "x-content-type-options", # 安全中间件
            "x-frame-options",       # 安全中间件
            "x-xss-protection",      # 安全中间件
            "referrer-policy",       # 安全中间件
            "content-security-policy", # 安全中间件
            "permissions-policy",    # 安全中间件
        ]

        for header in expected_headers:
            assert header in response.headers, f"缺少响应头: {header}"

    def test_middleware_order(self):
        """测试中间件执行顺序"""
        response = client.get("/")

        # 验证响应包含所有预期的信息
        data = response.json()

        # 验证响应格式统一
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert "timestamp" in data
        assert "traceId" in data

        # 验证TraceID在响应头中
        assert "x-request-id" in response.headers

    def test_middleware_error_handling(self):
        """测试中间件错误处理"""
        # 测试404错误处理
        response = client.get("/nonexistent-endpoint")

        # 验证错误响应格式统一
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "traceId" in data

        # 验证错误状态码
        assert response.status_code == 404

    def test_middleware_performance_impact(self):
        """测试中间件对性能的影响"""
        import time

        # 测试多个请求的响应时间
        start_time = time.time()
        for _ in range(10):
            client.get("/")
        end_time = time.time()

        average_time = (end_time - start_time) / 10

        # 验证平均响应时间在合理范围内（1秒以内）
        assert average_time < 1.0, f"平均响应时间过长: {average_time:.3f}秒"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])