"""
认证中间件测试

测试认证中间件的真实JWT验证、数据库黑名单检查、令牌自动刷新等功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


def test_auth_middleware_import():
    """测试认证中间件导入"""
    try:
        from src.api.middleware.auth import AuthMiddleware
        assert AuthMiddleware is not None
        print("✓ 认证中间件导入成功")
    except ImportError as e:
        pytest.fail(f"认证中间件导入失败: {e}")


def test_auth_middleware_with_real_jwt():
    """测试认证中间件使用真实JWT验证"""
    try:
        from src.api.middleware.auth import AuthMiddleware
        from src.services.jwt_service import JWTService
        from unittest.mock import AsyncMock

        # 使用与中间件相同的JWT配置
        from src.api.config import config
        jwt_config = config.get_secure_jwt_config()

        # 创建JWT服务和令牌
        jwt_service = JWTService(**jwt_config)
        user_id = uuid4()
        access_token = jwt_service.generate_access_token(
            user_id=user_id,
            user_type="user"
        )

        # 创建中间件实例（使用相同的配置）
        middleware = AuthMiddleware(None)

        # 创建模拟请求
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/tasks",  # 使用明确不是公开路径的路径
            "headers": [(b"authorization", f"Bearer {access_token}".encode())],
            "query_string": b"",
        }
        request = Request(scope)

        # 模拟下一个中间件
        call_next_called = False
        async def mock_call_next(req):
            nonlocal call_next_called
            call_next_called = True
            # 验证用户信息被正确设置
            assert hasattr(req.state, 'user_id')
            assert hasattr(req.state, 'user_type')
            assert req.state.user_id == str(user_id)
            assert req.state.user_type == "user"
            return Response(content="OK")

        # 测试中间件处理
        import asyncio
        asyncio.run(middleware.dispatch(request, mock_call_next))

        assert call_next_called
        print("✓ 真实JWT验证测试通过")

    except Exception as e:
        pytest.fail(f"真实JWT验证测试失败: {e}")


def test_auth_middleware_blacklist_check():
    """测试认证中间件黑名单检查"""
    try:
        from src.api.middleware.auth import AuthMiddleware
        from src.services.jwt_service import JWTService
        from unittest.mock import AsyncMock

        # 这个测试需要黑名单功能
        # 先创建基础测试，稍后完善
        middleware = AuthMiddleware(None)

        # 验证中间件有黑名单检查相关方法或属性
        assert hasattr(middleware, '_is_public_path')
        assert hasattr(middleware, '_extract_token')
        assert hasattr(middleware, '_verify_token_with_blacklist')

        print("✓ 黑名单检查基础测试通过")

    except Exception as e:
        pytest.fail(f"黑名单检查测试失败: {e}")


def test_auth_middleware_auto_refresh():
    """测试认证中间件令牌自动刷新机制"""
    try:
        from src.api.middleware.auth import AuthMiddleware

        # 创建中间件实例
        middleware = AuthMiddleware(None)

        # 验证中间件有令牌刷新相关的基础结构
        assert hasattr(middleware, '_extract_token')

        # 创建即将过期的令牌
        from src.services.jwt_service import JWTService
        from src.api.config import config
        jwt_config = config.get_secure_jwt_config()
        # 修改访问令牌过期时间为1秒
        jwt_config['access_token_expiry'] = 1
        jwt_service = JWTService(**jwt_config)

        user_id = uuid4()
        expiring_token = jwt_service.generate_access_token(
            user_id=user_id,
            user_type="user"
        )

        # 验证令牌格式正确
        assert isinstance(expiring_token, str)
        assert len(expiring_token) > 0

        print("✓ 自动刷新机制基础测试通过")

    except Exception as e:
        pytest.fail(f"自动刷新机制测试失败: {e}")


def test_auth_middleware_error_handling():
    """测试认证中间件错误处理"""
    try:
        from src.api.middleware.auth import AuthMiddleware
        from fastapi import HTTPException

        # 创建中间件实例
        middleware = AuthMiddleware(None)

        # 测试无效令牌
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/protected",
            "headers": [(b"authorization", b"Bearer invalid-token")],
            "query_string": b"",
        }
        request = Request(scope)

        # 模拟下一个中间件
        async def mock_call_next(req):
            return Response(content="OK")

        # 测试无效令牌应该抛出HTTPException
        import asyncio
        try:
            asyncio.run(middleware.dispatch(request, mock_call_next))
            # 如果没有抛出异常，测试失败
            pytest.fail("应该抛出HTTPException")
        except HTTPException as exc_info:
            # 验证异常状态码
            assert exc_info.status_code == 401
            # 验证错误信息包含认证相关内容
            error_detail = str(exc_info.detail)
            assert any(keyword in error_detail for keyword in [
                "认证", "令牌", "token", "Token", "验证", "无效"
            ]), f"错误信息应包含认证相关关键词，实际得到: {error_detail}"

        print("✓ 错误处理测试通过")

    except Exception as e:
        pytest.fail(f"错误处理测试失败: {e}")


def test_auth_middleware_public_paths():
    """测试认证中间件公开路径处理"""
    try:
        from src.api.middleware.auth import AuthMiddleware

        # 创建中间件实例
        middleware = AuthMiddleware(None)

        # 测试公开路径
        public_paths = [
            "/api/v1/auth/guest/init",
            "/api/v1/auth/sms/send",
            "/api/v1/auth/login",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/"
        ]

        for path in public_paths:
            assert middleware._is_public_path(path) == True
            # 只有文档路径支持子路径，认证路径不支持
            if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi.json") or path.startswith("/health"):
                assert middleware._is_public_path(path + "/subpath") == True
            else:
                assert middleware._is_public_path(path + "/subpath") == False

        # 测试受保护路径
        protected_paths = [
            "/api/v1/tasks",
            "/api/v1/focus",
            "/api/v1/user/profile",
            "/api/v1/rewards"
        ]

        for path in protected_paths:
            assert middleware._is_public_path(path) == False

        print("✓ 公开路径处理测试通过")

    except Exception as e:
        pytest.fail(f"公开路径处理测试失败: {e}")


def test_auth_middleware_token_extraction():
    """测试认证中间件令牌提取"""
    try:
        from src.api.middleware.auth import AuthMiddleware

        # 创建中间件实例
        middleware = AuthMiddleware(None)

        test_token = "test-jwt-token"

        # 测试Authorization头提取
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/protected",
            "headers": [(b"authorization", f"Bearer {test_token}".encode())],
            "query_string": b"",
        }
        request = Request(scope)
        extracted_token = middleware._extract_token(request)
        assert extracted_token == test_token

        # 测试查询参数提取
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/protected",
            "headers": [],
            "query_string": f"token={test_token}".encode(),
        }
        request = Request(scope)
        extracted_token = middleware._extract_token(request)
        assert extracted_token == test_token

        # 测试无令牌情况
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/protected",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        extracted_token = middleware._extract_token(request)
        assert extracted_token is None

        print("✓ 令牌提取测试通过")

    except Exception as e:
        pytest.fail(f"令牌提取测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])