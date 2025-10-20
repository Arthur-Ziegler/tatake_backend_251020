"""
游客升级API测试

测试游客账号升级功能，验证与AuthService的集成。
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from fastapi.testclient import TestClient
from fastapi import FastAPI


def test_guest_upgrade_api_validation():
    """测试游客升级API请求验证"""
    try:
        from src.api.schemas import GuestUpgradeRequest
        from src.api.schemas import LoginType
        from pydantic import ValidationError

        # 测试有效的手机号升级请求
        valid_phone_request = GuestUpgradeRequest(
            upgrade_type=LoginType.PHONE,
            phone="13812345678",
            verification_code="123456",
            device_id="test_device_123"
        )
        assert valid_phone_request.upgrade_type == LoginType.PHONE
        assert valid_phone_request.phone == "13812345678"
        assert valid_phone_request.verification_code == "123456"

        # 测试有效的邮箱升级请求
        valid_email_request = GuestUpgradeRequest(
            upgrade_type=LoginType.EMAIL,
            email="test@example.com",
            verification_code="654321",
            device_id="test_device_123"
        )
        assert valid_email_request.upgrade_type == LoginType.EMAIL
        assert valid_email_request.email == "test@example.com"
        assert valid_email_request.verification_code == "654321"

        # 测试有效的微信升级请求
        valid_wechat_request = GuestUpgradeRequest(
            upgrade_type=LoginType.WECHAT,
            wechat_code="wx_auth_code_123",
            verification_code="wx_verify_123",
            device_id="test_device_123"
        )
        assert valid_wechat_request.upgrade_type == LoginType.WECHAT
        assert valid_wechat_request.wechat_code == "wx_auth_code_123"
        assert valid_wechat_request.verification_code == "wx_verify_123"

        # 测试无效请求（缺少必需字段）
        try:
            invalid_request = GuestUpgradeRequest(
                upgrade_type=LoginType.PHONE,
                # 缺少phone和sms_code
                device_id="test_device_123"
            )
            pytest.fail("应该抛出ValidationError")
        except ValidationError:
            pass  # 预期的错误

        print("✓ 游客升级API请求验证测试通过")

    except Exception as e:
        pytest.fail(f"游客升级API请求验证测试失败: {e}")


def test_guest_upgrade_api_with_mock_service():
    """测试游客升级API与模拟AuthService集成"""
    try:
        from src.api.routers.auth import router
        from src.api.schemas import GuestUpgradeRequest, AuthResponse
        from src.services.auth_service import AuthService
        from src.services.jwt_service import JWTService
        from unittest.mock import patch, AsyncMock
        from src.api.schemas import LoginType

        # 创建FastAPI应用
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        # 创建测试客户端
        client = TestClient(app)

        # 模拟AuthService
        mock_auth_service = AsyncMock()
        mock_upgraded_user = {
            "user_id": f"upgraded_{uuid4().hex[:16]}",
            "phone": "13812345678",
            "email": None,
            "is_registered": True,
            "created_at": datetime.now(timezone.utc)
        }
        mock_auth_service.upgrade_guest_account.return_value = mock_upgraded_user

        # 模拟JWT服务
        mock_jwt_service = AsyncMock()
        mock_access_token = "mock_new_access_token"
        mock_refresh_token = "mock_new_refresh_token"
        mock_jwt_service.generate_token_pair.return_value = (mock_access_token, mock_refresh_token)

        # 准备测试数据
        request_data = {
            "upgrade_type": "phone",
            "phone": "13812345678",
            "verification_code": "123456",
            "device_id": "test_device_123"
        }

        # 模拟当前用户（必须是游客）
        mock_current_user = {
            "user_id": f"guest_{uuid4().hex[:16]}",
            "user_type": "guest",
            "is_guest": True
        }

        # 使用patch来模拟依赖
        with patch('src.api.routers.auth.get_current_user') as mock_get_user, \
             patch('src.api.routers.auth.get_auth_service') as mock_get_auth_service, \
             patch('src.api.routers.auth.get_jwt_service') as mock_get_jwt_service:

            mock_get_user.return_value = mock_current_user
            mock_get_auth_service.return_value = mock_auth_service
            mock_get_jwt_service.return_value = mock_jwt_service

            # 发送请求
            response = client.post("/api/v1/auth/guest/upgrade", json=request_data)

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "账号升级成功"

            # 验证认证响应数据
            auth_data = data["data"]
            assert auth_data["user_type"] == "registered"
            assert auth_data["is_guest"] == False
            assert auth_data["access_token"] == mock_access_token
            assert auth_data["refresh_token"] == mock_refresh_token

            # 验证AuthService方法被调用
            mock_auth_service.upgrade_guest_account.assert_called_once()
            call_args = mock_auth_service.upgrade_guest_account.call_args[1]
            assert call_args["user_id"] == mock_current_user["user_id"]
            assert call_args["upgrade_type"] == "phone"
            assert call_args["phone"] == "13812345678"
            assert call_args["verification_code"] == "123456"

            # 验证JWT服务方法被调用
            mock_jwt_service.generate_token_pair.assert_called_once()

        print("✓ 游客升级API与模拟AuthService集成测试通过")

    except Exception as e:
        pytest.fail(f"游客升级API与模拟AuthService集成测试失败: {e}")


def test_guest_upgrade_non_guest_user():
    """测试非游客用户升级失败"""
    try:
        from src.api.routers.auth import router
        from src.api.schemas import GuestUpgradeRequest
        from unittest.mock import patch

        # 创建FastAPI应用
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        # 创建测试客户端
        client = TestClient(app)

        # 准备测试数据
        request_data = {
            "upgrade_type": "phone",
            "phone": "13812345678",
            "verification_code": "123456",
            "device_id": "test_device_123"
        }

        # 模拟当前用户（不是游客）
        mock_current_user = {
            "user_id": f"registered_{uuid4().hex[:16]}",
            "user_type": "registered",
            "is_guest": False
        }

        # 使用patch来模拟依赖
        with patch('src.api.routers.auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_current_user

            # 发送请求，应该返回400错误
            response = client.post("/api/v1/auth/guest/upgrade", json=request_data)

            # 验证错误响应
            assert response.status_code == 400
            error_data = response.json()
            assert "detail" in error_data
            assert "只有游客账号可以升级" in error_data["detail"]

        print("✓ 非游客用户升级失败测试通过")

    except Exception as e:
        pytest.fail(f"非游客用户升级失败测试失败: {e}")


def test_guest_upgrade_validation_error():
    """测试游客升级验证错误处理"""
    try:
        from src.api.routers.auth import router
        from src.api.schemas import GuestUpgradeRequest
        from src.services.auth_service import BusinessException
        from unittest.mock import patch, AsyncMock

        # 创建FastAPI应用
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        # 创建测试客户端
        client = TestClient(app)

        # 模拟AuthService抛出验证异常
        mock_auth_service = AsyncMock()
        mock_auth_service.upgrade_guest_account.side_effect = BusinessException(
            "验证码错误或已过期",
            error_code="VERIFICATION_CODE_INVALID"
        )

        # 准备测试数据
        request_data = {
            "upgrade_type": "phone",
            "phone": "13812345678",
            "verification_code": "wrong_code",
            "device_id": "test_device_123"
        }

        # 模拟当前用户（是游客）
        mock_current_user = {
            "user_id": f"guest_{uuid4().hex[:16]}",
            "user_type": "guest",
            "is_guest": True
        }

        # 使用patch来模拟依赖
        with patch('src.api.routers.auth.get_current_user') as mock_get_user, \
             patch('src.api.routers.auth.get_auth_service') as mock_get_service, \
             patch('src.api.routers.auth.get_jwt_service') as mock_get_jwt:

            mock_get_user.return_value = mock_current_user
            mock_get_service.return_value = mock_auth_service
            mock_jwt = AsyncMock()
            mock_get_jwt.return_value = mock_jwt

            # 发送请求，应该返回400错误
            response = client.post("/api/v1/auth/guest/upgrade", json=request_data)

            # 验证错误响应
            assert response.status_code == 400
            error_data = response.json()
            assert "detail" in error_data
            assert "验证码" in error_data["detail"]

        print("✓ 游客升级验证错误处理测试通过")

    except Exception as e:
        pytest.fail(f"游客升级验证错误处理测试失败: {e}")


def test_guest_upgrade_different_types():
    """测试不同类型的游客升级"""
    try:
        from src.api.schemas import GuestUpgradeRequest
        from src.api.schemas import LoginType

        # 测试手机号升级
        phone_upgrade = GuestUpgradeRequest(
            upgrade_type=LoginType.PHONE,
            phone="13812345678",
            verification_code="123456",
            device_id="device_123"
        )
        assert phone_upgrade.upgrade_type == LoginType.PHONE
        assert phone_upgrade.phone == "13812345678"

        # 测试邮箱升级
        email_upgrade = GuestUpgradeRequest(
            upgrade_type=LoginType.EMAIL,
            email="user@example.com",
            verification_code="654321",
            device_id="device_123"
        )
        assert email_upgrade.upgrade_type == LoginType.EMAIL
        assert email_upgrade.email == "user@example.com"

        # 测试微信升级
        wechat_upgrade = GuestUpgradeRequest(
            upgrade_type=LoginType.WECHAT,
            wechat_code="wx_auth_12345",
            verification_code="wx_verify_123",
            device_id="device_123"
        )
        assert wechat_upgrade.upgrade_type == LoginType.WECHAT
        assert wechat_upgrade.wechat_code == "wx_auth_12345"

        print("✓ 不同类型的游客升级测试通过")

    except Exception as e:
        pytest.fail(f"不同类型的游客升级测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])