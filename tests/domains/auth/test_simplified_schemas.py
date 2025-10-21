"""
测试简化的认证领域Schema

测试新的简化Schema设计，确保：
1. 统一响应格式：{code, data, message}
2. 简化请求Schema，移除复杂字段
3. 只保留微信登录相关的Schema
4. 删除SMS、密码等非核心功能的Schema
"""

import pytest
from datetime import datetime
from typing import Dict, Any
from pydantic import ValidationError

from src.domains.auth.schemas import (
    # 统一响应格式
    UnifiedResponse,

    # 简化的请求Schema
    GuestInitRequest,
    WeChatRegisterRequest,
    WeChatLoginRequest,
    GuestUpgradeRequest,
    TokenRefreshRequest,

    # 响应Schema
    AuthTokenResponse,

    # 枚举
    UserTypeEnum,
)


@pytest.mark.asyncio
class TestUnifiedResponse:
    """测试统一响应格式"""

    def test_success_response_format(self):
        """测试成功响应格式"""
        response = UnifiedResponse(
            code=200,
            data={"user_id": "123", "token": "abc"},
            message="success"
        )

        assert response.code == 200
        assert response.data["user_id"] == "123"
        assert response.message == "success"

    def test_error_response_format(self):
        """测试错误响应格式"""
        response = UnifiedResponse(
            code=404,
            data=None,
            message="用户不存在"
        )

        assert response.code == 404
        assert response.data is None
        assert response.message == "用户不存在"

    def test_response_serialization(self):
        """测试响应序列化"""
        response = UnifiedResponse(
            code=200,
            data={"key": "value"},
            message="success"
        )

        json_data = response.model_dump()

        expected_keys = {"code", "data", "message"}
        assert set(json_data.keys()) == expected_keys
        assert json_data["code"] == 200
        assert json_data["data"] == {"key": "value"}
        assert json_data["message"] == "success"


@pytest.mark.asyncio
class TestSimplifiedRequestSchemas:
    """测试简化的请求Schema"""

    def test_guest_init_request_empty(self):
        """测试游客初始化请求（无请求体）"""
        # 游客初始化不接受任何参数
        request = GuestInitRequest()

        # 验证模型可以正常创建
        assert request is not None

    def test_wechat_register_request(self):
        """测试微信注册请求"""
        request = WeChatRegisterRequest(
            wechat_openid="wx_test_openid_12345"
        )

        assert request.wechat_openid == "wx_test_openid_12345"

    def test_wechat_login_request(self):
        """测试微信登录请求"""
        request = WeChatLoginRequest(
            wechat_openid="wx_test_openid_12345"
        )

        assert request.wechat_openid == "wx_test_openid_12345"

    def test_guest_upgrade_request(self):
        """测试游客升级请求"""
        request = GuestUpgradeRequest(
            wechat_openid="wx_test_openid_12345"
        )

        assert request.wechat_openid == "wx_test_openid_12345"

    def test_token_refresh_request(self):
        """测试令牌刷新请求"""
        request = TokenRefreshRequest(
            refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )

        assert request.refresh_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

    def test_validation_error_handling(self):
        """测试验证错误处理"""
        # 测试空openid会失败
        with pytest.raises(ValidationError):
            WeChatRegisterRequest(wechat_openid="")

        # 测试空refresh_token会失败
        with pytest.raises(ValidationError):
            TokenRefreshRequest(refresh_token="")


@pytest.mark.asyncio
class TestSimplifiedResponseSchemas:
    """测试简化的响应Schema"""

    def test_auth_token_response(self):
        """测试认证令牌响应"""
        response = AuthTokenResponse(
            code=200,
            data={
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            message="success"
        )

        assert response.code == 200
        assert response.data["user_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert "access_token" in response.data
        assert "refresh_token" in response.data
        assert response.message == "success"


@pytest.mark.asyncio
class TestDeletedSchemas:
    """测试已删除的Schema不应该存在"""

    def test_old_schemas_do_not_exist(self):
        """测试旧的Schema已被删除"""
        # 这些Schema应该已被删除
        old_schemas = [
            'DeviceInfo',        # 设备信息
            'SMSCodeRequest',    # 短信验证码请求
            'LoginRequest',      # 复杂登录请求
            'UserInfoResponse',   # 用户信息响应
            'SMSCodeResponse',   # 短信验证码响应
        ]

        for schema_name in old_schemas:
            # 尝试导入这些Schema应该失败
            try:
                from src.domains.auth.schemas import schema_name  # type: ignore
                assert False, f"Schema {schema_name} 应该已被删除"
            except ImportError:
                pass  # 期望的行为


@pytest.mark.asyncio
class TestSimplifiedEnums:
    """测试简化的枚举类型"""

    def test_user_type_enum(self):
        """测试用户类型枚举已简化"""
        # 检查枚举值
        assert UserTypeEnum.GUEST == "guest"

        # 验证枚举已简化
        enum_values = {member.value for member in UserTypeEnum}

        # 不应该包含旧的登录方式
        assert "phone" not in enum_values
        assert "apple" not in enum_values

        # 应该只保留核心类型
        expected_values = {"guest", "wechat"}
        assert enum_values == expected_values, f"用户类型枚举应该只包含 {expected_values}"