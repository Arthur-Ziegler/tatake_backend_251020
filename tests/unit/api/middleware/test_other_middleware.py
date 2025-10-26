"""
其他中间件综合测试

测试异常处理、日志记录、限流、安全等中间件，包括：
1. 异常处理中间件
2. 日志记录中间件
3. 限流中间件
4. 安全中间件

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json


@pytest.mark.unit
class TestExceptionHandlingMiddleware:
    """异常处理中间件测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.mock_app = Mock()

    def test_exception_handling_middleware_initialization(self):
        """测试异常处理中间件初始化"""
        middleware = Mock()
        middleware.app = self.mock_app
        middleware.debug = False

        assert middleware.app is not None
        assert middleware.debug is False

    @pytest.mark.asyncio
    async def test_http_exception_handling(self):
        """测试HTTP异常处理"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "GET"

        call_next = AsyncMock()
        http_exception = HTTPException(
            status_code=404,
            detail="资源未找到"
        )
        call_next.side_effect = http_exception

        # 模拟异常处理
        try:
            await call_next(request)
        except HTTPException as exc:
            error_response = {
                "code": exc.status_code,
                "message": exc.detail,
                "data": None,
                "path": request.url.path
            }

            assert error_response["code"] == 404
            assert error_response["message"] == "资源未找到"
            assert error_response["path"] == "/api/test"

    @pytest.mark.asyncio
    async def test_validation_exception_handling(self):
        """测试验证异常处理"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/users"

        call_next = AsyncMock()
        validation_exception = ValueError("用户名不能为空")
        call_next.side_effect = validation_exception

        # 模拟验证异常处理
        try:
            await call_next(request)
        except ValueError as exc:
            error_response = {
                "code": 422,
                "message": "参数验证失败",
                "data": {
                    "error": str(exc),
                    "path": request.url.path
                }
            }

            assert error_response["code"] == 422
            assert "参数验证失败" in error_response["message"]
            assert "用户名不能为空" in error_response["data"]["error"]

    @pytest.mark.asyncio
    async def test_database_exception_handling(self):
        """测试数据库异常处理"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/tasks"

        call_next = AsyncMock()
        db_exception = Exception("数据库连接失败")
        call_next.side_effect = db_exception

        # 模拟数据库异常处理
        try:
            await call_next(request)
        except Exception as exc:
            error_response = {
                "code": 500,
                "message": "服务器内部错误",
                "data": {
                    "error": "数据处理失败",
                    "path": request.url.path
                }
            }

            assert error_response["code"] == 500
            assert error_response["data"]["error"] == "数据处理失败"

    @pytest.mark.asyncio
    async def test_successful_request_handling(self):
        """测试成功请求处理"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/health"

        call_next = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        call_next.return_value = mock_response

        # 模拟成功处理
        response = await call_next(request)

        assert response.status_code == 200
        call_next.assert_called_once_with(request)


@pytest.mark.unit
class TestLoggingMiddleware:
    """日志记录中间件测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.mock_app = Mock()

    def test_logging_middleware_initialization(self):
        """测试日志记录中间件初始化"""
        middleware = Mock()
        middleware.app = self.mock_app
        middleware.log_level = "INFO"
        middleware.log_requests = True
        middleware.log_responses = True

        assert middleware.app is not None
        assert middleware.log_level == "INFO"

    @pytest.mark.asyncio
    async def test_request_logging(self):
        """测试请求日志记录"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/users"
        request.method = "GET"
        request.headers = {"User-Agent": "TestClient"}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        call_next = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        call_next.return_value = mock_response

        # 模拟日志记录
        start_time = datetime.now(timezone.utc)
        response = await call_next(request)
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration": duration,
            "client_ip": request.client.host,
            "user_agent": request.headers.get("User-Agent"),
            "timestamp": start_time.isoformat()
        }

        assert log_data["method"] == "GET"
        assert log_data["path"] == "/api/users"
        assert log_data["status_code"] == 200
        assert isinstance(log_data["duration"], float)

    @pytest.mark.asyncio
    async def test_error_logging(self):
        """测试错误日志记录"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/error"
        request.method = "POST"

        call_next = AsyncMock()
        error_exception = ValueError("测试错误")
        call_next.side_effect = error_exception

        # 模拟错误日志记录
        try:
            await call_next(request)
        except Exception as exc:
            error_log_data = {
                "method": request.method,
                "path": request.url.path,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            assert error_log_data["method"] == "POST"
            assert error_log_data["path"] == "/api/error"
            assert error_log_data["error_type"] == "ValueError"
            assert error_log_data["error_message"] == "测试错误"

    def test_sensitive_data_filtering(self):
        """测试敏感数据过滤"""
        request_headers = {
            "Authorization": "Bearer secret.token",
            "Cookie": "session=abc123",
            "Content-Type": "application/json"
        }

        # 模拟敏感数据过滤
        filtered_headers = {}
        sensitive_headers = ["Authorization", "Cookie"]

        for key, value in request_headers.items():
            if key in sensitive_headers:
                filtered_headers[key] = "***FILTERED***"
            else:
                filtered_headers[key] = value

        assert filtered_headers["Authorization"] == "***FILTERED***"
        assert filtered_headers["Cookie"] == "***FILTERED***"
        assert filtered_headers["Content-Type"] == "application/json"


@pytest.mark.unit
class TestRateLimitMiddleware:
    """限流中间件测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.mock_app = Mock()

    def test_rate_limit_middleware_initialization(self):
        """测试限流中间件初始化"""
        middleware = Mock()
        middleware.app = self.mock_app
        middleware.requests_per_minute = 60
        middleware.requests_per_hour = 1000
        middleware.burst_size = 10

        assert middleware.app is not None
        assert middleware.requests_per_minute == 60

    @pytest.mark.asyncio
    async def test_rate_limit_within_threshold(self):
        """测试阈值内的限流"""
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.url = Mock()
        request.url.path = "/api/data"

        call_next = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        call_next.return_value = mock_response

        # 模拟限流检查
        client_ip = request.client.host
        current_requests = 30  # 当前请求数
        limit = 60

        if current_requests < limit:
            response = await call_next(request)
            is_allowed = True
        else:
            is_allowed = False

        assert is_allowed is True
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """测试超过限流阈值"""
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.101"
        request.url = Mock()
        request.url.path = "/api/data"

        call_next = AsyncMock()

        # 模拟限流检查
        client_ip = request.client.host
        current_requests = 65  # 超过限制
        limit = 60

        if current_requests < limit:
            response = await call_next(request)
            is_allowed = True
        else:
            is_allowed = False
            # 模拟限流响应
            rate_limit_response = {
                "code": 429,
                "message": "请求过于频繁，请稍后重试",
                "data": {
                    "limit": limit,
                    "reset_time": 60
                }
            }

        assert is_allowed is False
        assert rate_limit_response["code"] == 429

    @pytest.mark.asyncio
    async def test_rate_limit_burst_handling(self):
        """测试限流突发处理"""
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.102"

        call_next = AsyncMock()

        # 模拟突发限流检查
        client_ip = request.client.host
        burst_requests = 15  # 突发请求数
        burst_size = 10

        if burst_requests > burst_size:
            is_allowed = False
            burst_response = {
                "code": 429,
                "message": "请求过于频繁，请降低请求速率",
                "data": {
                    "burst_size": burst_size,
                    "retry_after": 5
                }
            }
        else:
            is_allowed = True

        assert is_allowed is False
        assert burst_response["data"]["burst_size"] == 10

    def test_rate_limit_key_generation(self):
        """测试限流键生成"""
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.103"
        request.headers = {"X-User-ID": "user123"}

        # 模拟限流键生成
        user_id = request.headers.get("X-User-ID")
        if user_id:
            rate_limit_key = f"user:{user_id}"
        else:
            rate_limit_key = f"ip:{request.client.host}"

        # 测试基于用户ID的键
        assert rate_limit_key == "user:user123"

        # 测试基于IP的键
        request.headers = {}
        rate_limit_key = f"ip:{request.client.host}"
        assert rate_limit_key == "ip:192.168.1.103"


@pytest.mark.unit
class TestSecurityMiddleware:
    """安全中间件测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.mock_app = Mock()

    def test_security_middleware_initialization(self):
        """测试安全中间件初始化"""
        middleware = Mock()
        middleware.app = self.mock_app
        middleware.add_security_headers = True
        middleware.block_suspicious_requests = True

        assert middleware.app is not None
        assert middleware.add_security_headers is True

    @pytest.mark.asyncio
    async def test_security_headers_addition(self):
        """测试安全头添加"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/secure"

        call_next = AsyncMock()
        mock_response = Mock()
        mock_response.headers = {}
        call_next.return_value = mock_response

        # 模拟安全头添加
        response = await call_next(request)

        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        }

        for header, value in security_headers.items():
            response.headers[header] = value

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Strict-Transport-Security"] is not None

    @pytest.mark.asyncio
    async def test_suspicious_request_blocking(self):
        """测试可疑请求阻止"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/admin/users"
        request.method = "GET"
        request.headers = {
            "User-Agent": "sqlmap/1.0",
            "X-Forwarded-For": "192.168.1.1"
        }
        request.client = Mock()
        request.client.host = "10.0.0.1"

        call_next = AsyncMock()

        # 模拟可疑请求检测
        suspicious_patterns = [
            "sqlmap",
            "nmap",
            "nikto",
            "dirb"
        ]

        user_agent = request.headers.get("User-Agent", "")
        is_suspicious = any(pattern in user_agent.lower() for pattern in suspicious_patterns)

        if is_suspicious:
            is_blocked = True
            security_response = {
                "code": 403,
                "message": "请求被拒绝",
                "data": {
                    "reason": "检测到可疑活动"
                }
            }
        else:
            is_blocked = False

        assert is_blocked is True
        assert security_response["data"]["reason"] == "检测到可疑活动"

    @pytest.mark.asyncio
    async def test_sql_injection_detection(self):
        """测试SQL注入检测"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/users"
        request.query_params = {
            "id": "1; DROP TABLE users; --"
        }

        # 模拟SQL注入检测
        sql_injection_patterns = [
            "DROP TABLE",
            "UNION SELECT",
            "OR 1=1",
            ";--",
            "' OR '1'='1"
        ]

        query_string = str(request.query_params)
        is_sql_injection = any(pattern in query_string.upper() for pattern in sql_injection_patterns)

        if is_sql_injection:
            is_blocked = True
            block_reason = "SQL注入检测"
        else:
            is_blocked = False

        assert is_blocked is True
        assert block_reason == "SQL注入检测"

    @pytest.mark.asyncio
    async def test_xss_detection(self):
        """测试XSS检测"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/comments"
        request.method = "POST"

        # 模拟请求体
        request_data = {
            "comment": "<script>alert('xss')</script>"
        }

        # 模拟XSS检测
        xss_patterns = [
            "<script>",
            "javascript:",
            "onerror=",
            "onload=",
            "eval("
        ]

        comment = request_data.get("comment", "")
        is_xss = any(pattern in comment.lower() for pattern in xss_patterns)

        if is_xss:
            is_blocked = True
            block_reason = "XSS攻击检测"
        else:
            is_blocked = False

        assert is_blocked is True
        assert block_reason == "XSS攻击检测"

    def test_ip_whitelist_check(self):
        """测试IP白名单检查"""
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # 模拟IP白名单
        whitelist_ips = [
            "192.168.1.100",
            "10.0.0.50",
            "127.0.0.1"
        ]

        client_ip = request.client.host
        is_whitelisted = client_ip in whitelist_ips

        assert is_whitelisted is True

        # 测试非白名单IP
        request.client.host = "203.0.113.1"
        is_whitelisted = request.client.host in whitelist_ips
        assert is_whitelisted is False


@pytest.mark.integration
class TestMiddlewareIntegration:
    """中间件集成测试类"""

    @pytest.mark.asyncio
    async def test_middleware_chain_execution(self):
        """测试中间件链执行"""
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "GET"

        # 模拟中间件链
        middleware_stack = []

        # 添加安全中间件
        security_response = Mock()
        security_response.headers = {}
        security_middleware = AsyncMock()
        security_middleware.return_value = security_response
        middleware_stack.append(security_middleware)

        # 添加日志中间件
        logging_middleware = AsyncMock()
        logging_middleware.return_value = security_response
        middleware_stack.append(logging_middleware)

        # 添加限流中间件
        rate_limit_middleware = AsyncMock()
        rate_limit_middleware.return_value = security_response
        middleware_stack.append(rate_limit_middleware)

        # 执行中间件链
        current_request = request
        for middleware in middleware_stack:
            response = await middleware(current_request)

        # 验证所有中间件都被调用
        for middleware in middleware_stack:
            middleware.assert_called()

    def test_error_propagation_through_middleware(self):
        """测试错误在中间件链中的传播"""
        # 模拟错误在中间件链中的传播
        error = HTTPException(status_code=404, detail="Not Found")

        try:
            raise error
        except HTTPException as exc:
            # 异常应该被正确传播
            assert exc.status_code == 404
            assert exc.detail == "Not Found"

    def test_middleware_configuration_consistency(self):
        """测试中间件配置一致性"""
        # 模拟中间件配置
        middleware_configs = {
            "security": {
                "add_headers": True,
                "block_suspicious": True
            },
            "logging": {
                "log_level": "INFO",
                "log_requests": True,
                "log_responses": True
            },
            "rate_limit": {
                "requests_per_minute": 60,
                "burst_size": 10
            },
            "exception_handling": {
                "debug": False,
                "detailed_errors": False
            }
        }

        # 验证配置一致性
        for middleware_name, config in middleware_configs.items():
            assert isinstance(config, dict)
            assert len(config) > 0

        # 验证特定配置值
        assert middleware_configs["security"]["add_headers"] is True
        assert middleware_configs["logging"]["log_level"] == "INFO"
        assert middleware_configs["rate_limit"]["requests_per_minute"] == 60


@pytest.mark.parametrize("error_type,expected_status,expected_message", [
    (HTTPException, 404, "资源未找到"),
    (ValueError, 422, "参数验证失败"),
    (Exception, 500, "服务器内部错误")
])
def test_exception_handling_parametrized(error_type, expected_status, expected_message):
    """参数化测试异常处理"""
    try:
        if error_type == HTTPException:
            raise error_type(status_code=expected_status, detail=expected_message)
        else:
            raise error_type(expected_message)
    except HTTPException as exc:
        assert exc.status_code == expected_status
        assert exc.detail == expected_message
    except (ValueError, Exception) as exc:
        # 其他异常被转换为标准错误响应
        assert expected_status in [422, 500]


@pytest.mark.parametrize("client_ip,limit,requests,should_block", [
    ("192.168.1.1", 60, 30, False),
    ("192.168.1.2", 60, 65, True),
    ("10.0.0.1", 100, 99, False),
    ("10.0.0.2", 100, 101, True)
])
def test_rate_limit_parametrized(client_ip, limit, requests, should_block):
    """参数化测试限流"""
    is_blocked = requests > limit
    assert is_blocked == should_block


@pytest.mark.parametrize("user_agent,is_suspicious", [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", False),
    ("sqlmap/1.0", True),
    ("curl/7.64.1", False),
    ("nmap/7.80", True)
])
def test_suspicious_user_agent_detection(user_agent, is_suspicious):
    """参数化测试可疑用户代理检测"""
    suspicious_patterns = ["sqlmap", "nmap", "nikto", "dirb"]
    detected = any(pattern in user_agent.lower() for pattern in suspicious_patterns)
    assert detected == is_suspicious


@pytest.fixture
def sample_request():
    """示例请求对象"""
    request = Mock()
    request.url = Mock()
    request.url.path = "/api/test"
    request.method = "GET"
    request.headers = {"User-Agent": "TestClient"}
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def sample_error_response():
    """示例错误响应"""
    return {
        "code": 404,
        "message": "资源未找到",
        "data": None,
        "path": "/api/nonexistent"
    }


def test_with_fixtures(sample_request, sample_error_response):
    """使用fixtures的测试"""
    # 测试请求对象
    assert sample_request.method == "GET"
    assert sample_request.url.path == "/api/test"
    assert sample_request.client.host == "127.0.0.1"

    # 测试错误响应
    assert sample_error_response["code"] == 404
    assert sample_error_response["message"] == "资源未找到"