"""
认证领域Router层测试

测试API路由层的功能，包括：
- 7个认证API端点
- 请求参数验证
- 响应格式验证
- 错误处理
- 认证中间件
"""

import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import status

from ...api.main import app
from src.domains.auth.schemas import (
    GuestInitRequest, GuestUpgradeRequest, LoginRequest,
    SMSCodeRequest, TokenRefreshRequest
)


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


class TestGuestInitAPI:
    """游客初始化API测试"""

    def test_guest_init_success(self, client: TestClient):
        """测试成功初始化游客账号"""
        request_data = {
            "device_id": "test-device-123",
            "device_type": "ios",
            "app_version": "1.0.0"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.init_guest_account.return_value = {
                "user_id": str(uuid4()),
                "access_token": "mock_access_token",
                "refresh_token": "mock_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": True
            }
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/guest/init", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["is_guest"] is True
            assert "access_token" in data["data"]

    def test_guest_init_minimal_data(self, client: TestClient):
        """测试最少数据初始化游客账号"""
        request_data = {}  # 所有字段都是可选的

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.init_guest_account.return_value = {
                "user_id": str(uuid4()),
                "access_token": "mock_access_token",
                "refresh_token": "mock_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": True
            }
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/guest/init", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    def test_guest_init_invalid_data_fails(self, client: TestClient):
        """测试无效数据初始化游客账号失败"""
        request_data = {
            "device_type": 123,  # 应该是字符串
            "app_version": ""  # 空字符串
        }

        response = client.post("/api/v1/auth/guest/init", json=request_data)

        # 应该返回验证错误
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_guest_init_service_error(self, client: TestClient):
        """测试服务层错误处理"""
        request_data = {
            "device_id": "test-device-123"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.init_guest_account.side_effect = Exception("服务错误")
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/guest/init", json=request_data)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "detail" in data


class TestGuestUpgradeAPI:
    """游客升级API测试"""

    def test_guest_upgrade_success(self, client: TestClient):
        """测试成功升级游客账号"""
        request_data = {
            "phone": "13800138000",
            "sms_code": "123456",
            "password": "new_password_123",
            "nickname": "正式用户"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

            mock_user_id.return_value = uuid4()
            mock_auth_service = AsyncMock()
            mock_auth_service.upgrade_guest_account.return_value = {
                "user_id": str(uuid4()),
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": False
            }
            mock_service.return_value = mock_auth_service

            response = client.post(
                "/api/v1/auth/guest/upgrade",
                json=request_data,
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["is_guest"] is False

    def test_guest_upgrade_unauthorized_fails(self, client: TestClient):
        """测试未授权升级游客账号失败"""
        request_data = {
            "phone": "13800138000",
            "sms_code": "123456"
        }

        response = client.post("/api/v1/auth/guest/upgrade", json=request_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_guest_upgrade_invalid_data_fails(self, client: TestClient):
        """测试无效数据升级游客账号失败"""
        request_data = {
            "phone": "invalid_phone",  # 无效手机号
            "sms_code": "12",  # 验证码太短
            "password": "123"  # 密码太短
        }

        response = client.post(
            "/api/v1/auth/guest/upgrade",
            json=request_data,
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSMSCodeAPI:
    """短信验证码API测试"""

    def test_send_sms_code_success(self, client: TestClient):
        """测试成功发送短信验证码"""
        request_data = {
            "phone": "13800138000",
            "verification_type": "login"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

            mock_user_id.return_value = uuid4()
            mock_auth_service = AsyncMock()
            mock_auth_service.send_sms_code.return_value = "123456"
            mock_service.return_value = mock_auth_service

            response = client.post(
                "/api/v1/auth/sms/send",
                json=request_data,
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["phone"] == "13800138000"

    def test_send_sms_code_rate_limit(self, client: TestClient):
        """测试发送短信验证码频率限制"""
        request_data = {
            "phone": "13800138000",
            "verification_type": "login"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

            mock_user_id.return_value = uuid4()
            mock_auth_service = AsyncMock()
            mock_auth_service.send_sms_code.side_effect = Exception("发送过于频繁")
            mock_service.return_value = mock_auth_service

            response = client.post(
                "/api/v1/auth/sms/send",
                json=request_data,
                headers={"Authorization": "Bearer mock_token"}
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_sms_code_invalid_phone_fails(self, client: TestClient):
        """测试无效手机号发送短信失败"""
        request_data = {
            "phone": "invalid_phone",
            "verification_type": "login"
        }

        response = client.post(
            "/api/v1/auth/sms/send",
            json=request_data,
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginAPI:
    """登录API测试"""

    def test_login_sms_success(self, client: TestClient):
        """测试短信验证码登录成功"""
        request_data = {
            "identifier": "13800138000",
            "login_type": "sms",
            "sms_code": "123456"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.login.return_value = {
                "user_id": str(uuid4()),
                "access_token": "access_token",
                "refresh_token": "refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": False
            }
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/login", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "access_token" in data["data"]

    def test_login_password_success(self, client: TestClient):
        """测试密码登录成功"""
        request_data = {
            "identifier": "testuser",
            "login_type": "password",
            "password": "test_password_123"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.login.return_value = {
                "user_id": str(uuid4()),
                "access_token": "access_token",
                "refresh_token": "refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": False
            }
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/login", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    def test_login_invalid_credentials_fails(self, client: TestClient):
        """测试无效凭据登录失败"""
        request_data = {
            "identifier": "testuser",
            "login_type": "password",
            "password": "wrong_password"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.login.side_effect = Exception("用户名或密码错误")
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/login", json=request_data)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_unsupported_type_fails(self, client: TestClient):
        """测试不支持的登录类型失败"""
        request_data = {
            "identifier": "testuser",
            "login_type": "unsupported",
            "password": "password"
        }

        response = client.post("/api/v1/auth/login", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTokenRefreshAPI:
    """令牌刷新API测试"""

    def test_refresh_token_success(self, client: TestClient):
        """测试成功刷新令牌"""
        request_data = {
            "refresh_token": "valid_refresh_token"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.refresh_token.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800
            }
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/refresh", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "access_token" in data["data"]
            assert "refresh_token" in data["data"]

    def test_refresh_token_invalid_fails(self, client: TestClient):
        """测试无效令牌刷新失败"""
        request_data = {
            "refresh_token": "invalid_token"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.refresh_token.side_effect = Exception("令牌无效")
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/refresh", json=request_data)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_missing_fails(self, client: TestClient):
        """测试缺少刷新令牌失败"""
        request_data = {}  # 缺少refresh_token

        response = client.post("/api/v1/auth/refresh", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogoutAPI:
    """登出API测试"""

    def test_logout_success(self, client: TestClient):
        """测试成功登出"""
        valid_token = "valid_bearer_token"

        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('jwt.decode', return_value={
                 "sub": str(uuid4()),
                 "jti": str(uuid4()),
                 "exp": (datetime.now().timestamp() + 3600)
             }):

            mock_auth_service = AsyncMock()
            mock_service.return_value = mock_auth_service

            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "登出成功"

    def test_logout_unauthorized_fails(self, client: TestClient):
        """测试未授权登出失败"""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_invalid_token_fails(self, client: TestClient):
        """测试无效令牌登出失败"""
        invalid_token = "invalid_token"

        with patch('jwt.decode', side_effect=Exception("令牌无效")):
            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {invalid_token}"}
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserInfoAPI:
    """用户信息API测试"""

    def test_get_user_info_success(self, client: TestClient):
        """测试成功获取用户信息"""
        user_id = uuid4()
        valid_token = "valid_bearer_token"

        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id', return_value=user_id):

            mock_auth_service = AsyncMock()
            mock_auth_service.get_user_info.return_value = {
                "user_id": str(user_id),
                "username": "testuser",
                "nickname": "测试用户",
                "email": "test@example.com",
                "phone": "13800138000",
                "is_guest": False,
                "is_verified": True,
                "level": 1,
                "total_points": 100
            }
            mock_service.return_value = mock_auth_service

            response = client.get(
                "/api/v1/auth/user-info",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["user_id"] == str(user_id)
            assert data["data"]["username"] == "testuser"

    def test_get_user_info_unauthorized_fails(self, client: TestClient):
        """测试未授权获取用户信息失败"""
        response = client.get("/api/v1/auth/user-info")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_info_not_found_fails(self, client: TestClient):
        """测试用户不存在获取信息失败"""
        valid_token = "valid_bearer_token"

        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id', return_value=uuid4()):

            mock_auth_service = AsyncMock()
            mock_auth_service.get_user_info.side_effect = Exception("用户不存在")
            mock_service.return_value = mock_auth_service

            response = client.get(
                "/api/v1/auth/user-info",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST


# 集成测试
@pytest.mark.integration
class TestAuthAPIIntegration:
    """认证API集成测试"""

    def test_complete_auth_flow(self, client: TestClient):
        """测试完整的认证流程"""
        device_id = "test-device-integration"
        phone = "13800138000"
        sms_code = "123456"
        password = "integration_password"

        # 1. 游客初始化
        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            guest_user_id = uuid4()
            mock_auth_service.init_guest_account.return_value = {
                "user_id": str(guest_user_id),
                "access_token": "guest_access_token",
                "refresh_token": "guest_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": True
            }
            mock_service.return_value = mock_auth_service

            init_response = client.post("/api/v1/auth/guest/init", json={
                "device_id": device_id,
                "device_type": "ios"
            })
            assert init_response.status_code == 200
            guest_token = init_response.json()["data"]["access_token"]

        # 2. 发送短信验证码
        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

            mock_user_id.return_value = guest_user_id
            mock_auth_service = AsyncMock()
            mock_auth_service.send_sms_code.return_value = sms_code
            mock_service.return_value = mock_auth_service

            sms_response = client.post("/api/v1/auth/sms/send", json={
                "phone": phone,
                "verification_type": "upgrade"
            }, headers={"Authorization": f"Bearer {guest_token}"})
            assert sms_response.status_code == 200

        # 3. 游客升级
        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

            mock_user_id.return_value = guest_user_id
            mock_auth_service = AsyncMock()
            registered_user_id = uuid4()
            mock_auth_service.upgrade_guest_account.return_value = {
                "user_id": str(registered_user_id),
                "access_token": "user_access_token",
                "refresh_token": "user_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": False
            }
            mock_service.return_value = mock_auth_service

            upgrade_response = client.post("/api/v1/auth/guest/upgrade", json={
                "phone": phone,
                "sms_code": sms_code,
                "password": password,
                "nickname": "正式用户"
            }, headers={"Authorization": f"Bearer {guest_token}"})
            assert upgrade_response.status_code == 200
            user_token = upgrade_response.json()["data"]["access_token"]

        # 4. 获取用户信息
        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('src.domains.auth.router.get_current_user_id') as mock_user_id:

            mock_user_id.return_value = registered_user_id
            mock_auth_service = AsyncMock()
            mock_auth_service.get_user_info.return_value = {
                "user_id": str(registered_user_id),
                "username": None,
                "nickname": "正式用户",
                "phone": phone,
                "is_guest": False,
                "is_verified": True
            }
            mock_service.return_value = mock_auth_service

            user_info_response = client.get("/api/v1/auth/user-info",
                headers={"Authorization": f"Bearer {user_token}"})
            assert user_info_response.status_code == 200
            user_data = user_info_response.json()["data"]
            assert user_data["is_guest"] is False
            assert user_data["phone"] == phone

        # 5. 刷新令牌
        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.refresh_token.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer",
                "expires_in": 1800
            }
            mock_service.return_value = mock_auth_service

            refresh_response = client.post("/api/v1/auth/refresh", json={
                "refresh_token": "user_refresh_token"
            })
            assert refresh_response.status_code == 200
            new_token = refresh_response.json()["data"]["access_token"]

        # 6. 登出
        with patch('src.domains.auth.router.create_auth_service') as mock_service, \
             patch('jwt.decode', return_value={
                 "sub": str(registered_user_id),
                 "jti": str(uuid4()),
                 "exp": (datetime.now().timestamp() + 3600)
             }):
            mock_auth_service = AsyncMock()
            mock_service.return_value = mock_auth_service

            logout_response = client.post("/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {new_token}"})
            assert logout_response.status_code == 200


# 错误处理测试
@pytest.mark.edge_case
class TestAuthAPIErrorHandling:
    """认证API错误处理测试"""

    def test_malformed_json_request(self, client: TestClient):
        """测试格式错误的JSON请求"""
        malformed_json = '{"device_id": "test", invalid}'

        response = client.post(
            "/api/v1/auth/guest/init",
            data=malformed_json,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_content_type(self, client: TestClient):
        """测试缺少Content-Type头"""
        response = client.post(
            "/api/v1/auth/guest/init",
            data='{"device_id": "test"}'
        )

        # FastAPI通常能处理这种情况，但应该验证
        assert response.status_code in [200, 422]

    def test_very_large_request_data(self, client: TestClient):
        """测试非常大的请求数据"""
        large_string = "a" * 10000  # 10KB的字符串

        request_data = {
            "device_id": large_string,
            "device_type": large_string,
            "app_version": large_string
        }

        response = client.post("/api/v1/auth/guest/init", json=request_data)

        # 应该被验证器拒绝或处理
        assert response.status_code != 500  # 不应该导致服务器错误

    def test_unicode_characters(self, client: TestClient):
        """测试Unicode字符处理"""
        request_data = {
            "device_id": "测试设备-🎉-设备",
            "device_type": "iOS-中文",
            "app_version": "1.0.0-版本"
        }

        with patch('src.domains.auth.router.create_auth_service') as mock_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.init_guest_account.return_value = {
                "user_id": str(uuid4()),
                "access_token": "mock_token",
                "refresh_token": "mock_refresh",
                "token_type": "bearer",
                "expires_in": 1800,
                "is_guest": True
            }
            mock_service.return_value = mock_auth_service

            response = client.post("/api/v1/auth/guest/init", json=request_data)

            assert response.status_code == status.HTTP_200_OK

    def test_concurrent_requests(self, client: TestClient):
        """测试并发请求处理"""
        import threading
        import time

        results = []

        def make_request():
            with patch('src.domains.auth.router.create_auth_service') as mock_service:
                mock_auth_service = AsyncMock()
                mock_auth_service.init_guest_account.return_value = {
                    "user_id": str(uuid4()),
                    "access_token": "mock_token",
                    "refresh_token": "mock_refresh",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "is_guest": True
                }
                mock_service.return_value = mock_auth_service

                response = client.post("/api/v1/auth/guest/init", json={
                    "device_id": f"device-{threading.current_thread().ident}"
                })
                results.append(response.status_code)

        # 创建10个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有请求都成功
        assert all(status == 200 for status in results)
        assert len(results) == 10