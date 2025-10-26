"""
Auth领域路由测试

测试认证API路由功能，包括：
1. API端点响应验证
2. 请求参数验证
3. 错误处理和异常
4. 统一响应格式

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.domains.auth.router import auth_router
from src.domains.auth.service import AuthService
from src.domains.auth.exceptions import (
    AuthenticationException,
    ValidationError,
    TokenException,
)


@pytest.mark.unit
class TestAuthRouter:
    """认证路由测试类"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(auth_router, prefix="/auth")
        return TestClient(app)

    @pytest.fixture
    def mock_auth_service(self):
        """模拟认证服务"""
        with patch('src.domains.auth.router.AuthService') as mock:
            yield mock

    def test_guest_init_success(self, app, mock_auth_service):
        """测试游客初始化成功"""
        # 模拟服务返回
        expected_response = {
            "code": 200,
            "data": {
                "user_id": "test-user-123",
                "is_guest": True,
                "access_token": "guest-access-token",
                "refresh_token": "guest-refresh-token",
                "token_type": "bearer",
                "expires_in": 3600
            },
            "message": "游客账号初始化成功"
        }

        mock_service_instance = Mock()
        mock_service_instance.init_guest_account.return_value = expected_response
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/guest/init")

        # 验证响应
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["message"] == "游客账号初始化成功"
        assert "data" in response.json()

    def test_wechat_register_success(self, app, mock_auth_service):
        """测试微信注册成功"""
        request_data = {"wechat_openid": "wx_test_12345"}

        expected_response = {
            "code": 200,
            "data": {
                "user_id": "new-user-123",
                "is_guest": False,
                "access_token": "user-access-token",
                "refresh_token": "user-refresh-token",
                "token_type": "bearer",
                "expires_in": 7200
            },
            "message": "微信注册成功"
        }

        mock_service_instance = Mock()
        mock_service_instance.wechat_register.return_value = expected_response
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/register", json=request_data)

        # 验证响应
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["message"] == "微信注册成功"

    def test_wechat_register_validation_error(self, app):
        """测试微信注册参数验证错误"""
        # 缺少必需的 wechat_openid
        response = app.post("/auth/register", json={})

        assert response.status_code == 422  # Validation Error

    def test_wechat_login_success(self, app, mock_auth_service):
        """测试微信登录成功"""
        request_data = {"wechat_openid": "wx_login_12345"}

        expected_response = {
            "code": 200,
            "data": {
                "user_id": "existing-user-123",
                "is_guest": False,
                "access_token": "login-access-token",
                "refresh_token": "login-refresh-token",
                "token_type": "bearer",
                "expires_in": 7200
            },
            "message": "微信登录成功"
        }

        mock_service_instance = Mock()
        mock_service_instance.wechat_login.return_value = expected_response
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/login", json=request_data)

        # 验证响应
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["message"] == "微信登录成功"

    def test_guest_upgrade_success(self, app, mock_auth_service):
        """测试游客账号升级成功"""
        request_data = {"wechat_openid": "wx_upgrade_12345"}

        expected_response = {
            "code": 200,
            "data": {
                "user_id": "upgraded-user-123",
                "is_guest": False,
                "access_token": "upgraded-access-token",
                "refresh_token": "upgraded-refresh-token",
                "token_type": "bearer",
                "expires_in": 7200
            },
            "message": "游客账号升级成功"
        }

        mock_service_instance = Mock()
        mock_service_instance.upgrade_guest_account.return_value = expected_response
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/guest/upgrade", json=request_data)

        # 验证响应
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["message"] == "游客账号升级成功"

    def test_token_refresh_success(self, app, mock_auth_service):
        """测试令牌刷新成功"""
        request_data = {"refresh_token": "refresh-token-12345"}

        expected_response = {
            "code": 200,
            "data": {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "token_type": "bearer",
                "expires_in": 7200
            },
            "message": "令牌刷新成功"
        }

        mock_service_instance = Mock()
        mock_service_instance.refresh_token.return_value = expected_response
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/refresh", json=request_data)

        # 验证响应
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["message"] == "令牌刷新成功"

    def test_service_exception_handling(self, app, mock_auth_service):
        """测试服务异常处理"""
        mock_service_instance = Mock()
        mock_service_instance.wechat_register.side_effect = AuthenticationException("认证失败")
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/register", json={"wechat_openid": "wx_test"})

        # 验证异常处理
        assert response.status_code in [400, 401, 422]  # 根据具体异常类型

    def test_validation_exception_handling(self, app, mock_auth_service):
        """测试验证异常处理"""
        mock_service_instance = Mock()
        mock_service_instance.wechat_register.side_effect = ValidationError("参数验证失败", "wechat_openid")
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/register", json={"wechat_openid": "invalid_format"})

        # 验证验证异常处理
        assert response.status_code == 400

    def test_token_exception_handling(self, app, mock_auth_service):
        """测试令牌异常处理"""
        mock_service_instance = Mock()
        mock_service_instance.refresh_token.side_effect = TokenException("令牌无效", "TOKEN_INVALID")
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/refresh", json={"refresh_token": "invalid_token"})

        # 验证令牌异常处理
        assert response.status_code == 401

    def test_unexpected_exception_handling(self, app, mock_auth_service):
        """测试意外异常处理"""
        mock_service_instance = Mock()
        mock_service_instance.wechat_register.side_effect = Exception("意外错误")
        mock_auth_service.return_value = mock_service_instance

        # 发送请求
        response = app.post("/auth/register", json={"wechat_openid": "wx_test"})

        # 验证意外异常处理
        assert response.status_code == 500

    def test_response_format_consistency(self, app, mock_auth_service):
        """测试响应格式一致性"""
        # 测试所有端点都返回统一格式
        endpoints_scenarios = [
            ("POST", "/auth/guest/init", {}),
            ("POST", "/auth/register", {"wechat_openid": "wx_test"}),
            ("POST", "/auth/login", {"wechat_openid": "wx_test"}),
            ("POST", "/auth/guest/upgrade", {"wechat_openid": "wx_test"}),
            ("POST", "/auth/refresh", {"refresh_token": "token123"}),
        ]

        mock_service_instance = Mock()
        mock_service_instance.init_guest_account.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.wechat_register.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.wechat_login.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.upgrade_guest_account.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.refresh_token.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_auth_service.return_value = mock_service_instance

        for method, endpoint, data in endpoints_scenarios:
            if method == "POST":
                response = app.post(endpoint, json=data)

            # 验证响应格式
            assert response.status_code == 200
            json_response = response.json()
            assert "code" in json_response
            assert "data" in json_response
            assert "message" in json_response
            assert json_response["code"] == 200

    @pytest.mark.parametrize("endpoint,method,data", [
        ("/auth/guest/init", "POST", {}),
        ("/auth/register", "POST", {"wechat_openid": "wx_test"}),
        ("/auth/login", "POST", {"wechat_openid": "wx_test"}),
        ("/auth/guest/upgrade", "POST", {"wechat_openid": "wx_test"}),
        ("/auth/refresh", "POST", {"refresh_token": "token123"}),
    ])
    def test_all_endpoints_basic_functionality(self, app, mock_auth_service, endpoint, method, data):
        """测试所有端点基本功能"""
        mock_service_instance = Mock()
        mock_service_instance.init_guest_account.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.wechat_register.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.wechat_login.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.upgrade_guest_account.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_service_instance.refresh_token.return_value = {"code": 200, "data": {}, "message": "成功"}
        mock_auth_service.return_value = mock_service_instance

        if method == "POST":
            response = app.post(endpoint, json=data)

        # 基本验证
        assert response.status_code == 200
        assert "code" in response.json()
        assert "data" in response.json()
        assert "message" in response.json()


@pytest.mark.integration
class TestAuthRouterIntegration:
    """认证路由集成测试类"""

    def test_complete_auth_flow_simulation(self, app, mock_auth_service):
        """测试完整认证流程模拟"""
        mock_service_instance = Mock()

        # 模拟各个阶段的响应
        mock_service_instance.init_guest_account.return_value = {
            "code": 200,
            "data": {"user_id": "guest_123", "is_guest": True},
            "message": "游客账号初始化成功"
        }

        mock_service_instance.upgrade_guest_account.return_value = {
            "code": 200,
            "data": {"user_id": "user_123", "is_guest": False},
            "message": "游客账号升级成功"
        }

        mock_service_instance.refresh_token.return_value = {
            "code": 200,
            "data": {"access_token": "new_token"},
            "message": "令牌刷新成功"
        }

        mock_auth_service.return_value = mock_service_instance

        # 1. 游客初始化
        response1 = app.post("/auth/guest/init", json={})
        assert response1.status_code == 200
        guest_data = response1.json()

        # 2. 游客升级
        response2 = app.post("/auth/guest/upgrade", json={"wechat_openid": "wx_test"})
        assert response2.status_code == 200
        upgrade_data = response2.json()

        # 3. 令牌刷新
        response3 = app.post("/auth/refresh", json={"refresh_token": "token123"})
        assert response3.status_code == 200
        refresh_data = response3.json()

        # 验证流程一致性
        assert guest_data["data"]["user_id"] == upgrade_data["data"]["user_id"]
        assert guest_data["data"]["is_guest"] is True
        assert upgrade_data["data"]["is_guest"] is False