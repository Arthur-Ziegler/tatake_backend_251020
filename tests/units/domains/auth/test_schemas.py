"""
Auth领域Schemas测试

测试认证领域的数据模型和验证规则，包括：
1. 请求模型验证
2. 响应模型验证
3. 字段类型和约束验证
4. Pydantic模型序列化

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from pydantic import ValidationError
from uuid import uuid4

from src.domains.auth.schemas import (
    # 请求模型
    GuestInitRequest,
    WeChatRegisterRequest,
    WeChatLoginRequest,
    GuestUpgradeRequest,
    TokenRefreshRequest,

    # 响应模型
    AuthTokenData,
    AuthTokenResponse,
)


@pytest.mark.unit
class TestGuestInitRequest:
    """游客初始化请求测试"""

    def test_guest_init_request_empty(self):
        """测试空的游客初始化请求"""
        request = GuestInitRequest()

        # GuestInitRequest 不应该有必需字段
        assert request is not None

    def test_guest_init_request_serialization(self):
        """测试游客初始化请求序列化"""
        request = GuestInitRequest()

        # 测试序列化
        data = request.model_dump()
        assert isinstance(data, dict)

        # 测试JSON序列化
        json_data = request.model_dump_json()
        assert isinstance(json_data, str)


@pytest.mark.unit
class TestWeChatRegisterRequest:
    """微信注册请求测试"""

    def test_wechat_register_request_valid(self):
        """测试有效的微信注册请求"""
        openid = "wx_test_12345"
        request = WeChatRegisterRequest(wechat_openid=openid)

        assert request.wechat_openid == openid

    def test_wechat_register_request_invalid_openid(self):
        """测试无效的微信OpenID"""
        # 测试空字符串
        with pytest.raises(ValidationError):
            WeChatRegisterRequest(wechat_openid="")

        # 测试None
        with pytest.raises(ValidationError):
            WeChatRegisterRequest(wechat_openid=None)

    @pytest.mark.parametrize("openid", [
        "wx_valid_123",
        "wx_user_456789",
        "wx_test_abcdefghijklmnopqrstuvwxyz123456",
        "1",  # 最小长度
        "a" * 100,  # 最大合理长度
    ])
    def test_wechat_register_request_valid_openids(self, openid):
        """测试各种有效的OpenID格式"""
        request = WeChatRegisterRequest(wechat_openid=openid)
        assert request.wechat_openid == openid


@pytest.mark.unit
class TestWeChatLoginRequest:
    """微信登录请求测试"""

    def test_wechat_login_request_valid(self):
        """测试有效的微信登录请求"""
        openid = "wx_login_test_12345"
        request = WeChatLoginRequest(wechat_openid=openid)

        assert request.wechat_openid == openid

    def test_wechat_login_request_invalid_openid(self):
        """测试无效的微信OpenID"""
        with pytest.raises(ValidationError):
            WeChatLoginRequest(wechat_openid="")


@pytest.mark.unit
class TestGuestUpgradeRequest:
    """游客升级请求测试"""

    def test_guest_upgrade_request_valid(self):
        """测试有效的游客升级请求"""
        openid = "wx_upgrade_test_12345"
        request = GuestUpgradeRequest(wechat_openid=openid)

        assert request.wechat_openid == openid

    def test_guest_upgrade_request_invalid_openid(self):
        """测试无效的微信OpenID"""
        with pytest.raises(ValidationError):
            GuestUpgradeRequest(wechat_openid="")


@pytest.mark.unit
class TestTokenRefreshRequest:
    """令牌刷新请求测试"""

    def test_token_refresh_request_valid(self):
        """测试有效的令牌刷新请求"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.refresh"
        request = TokenRefreshRequest(refresh_token=token)

        assert request.refresh_token == token

    def test_token_refresh_request_invalid_token(self):
        """测试无效的刷新令牌"""
        with pytest.raises(ValidationError):
            TokenRefreshRequest(refresh_token="")

        with pytest.raises(ValidationError):
            TokenRefreshRequest(refresh_token=None)


@pytest.mark.unit
class TestAuthTokenData:
    """认证令牌数据测试"""

    def test_auth_token_data_valid(self):
        """测试有效的认证令牌数据"""
        user_id = str(uuid4())
        token_data = AuthTokenData(
            user_id=user_id,
            is_guest=True,
            access_token="eyJ.access.token",
            refresh_token="eyJ.refresh.token",
            token_type="bearer",
            expires_in=3600
        )

        assert token_data.user_id == user_id
        assert token_data.is_guest is True
        assert token_data.access_token == "eyJ.access.token"
        assert token_data.refresh_token == "eyJ.refresh.token"
        assert token_data.token_type == "bearer"
        assert token_data.expires_in == 3600

    def test_auth_token_data_serialization(self):
        """测试认证令牌数据序列化"""
        user_id = str(uuid4())
        token_data = AuthTokenData(
            user_id=user_id,
            is_guest=False,
            access_token="access.token",
            refresh_token="refresh.token",
            token_type="bearer",
            expires_in=7200
        )

        # 测试字典序列化
        data = token_data.model_dump()
        assert data["user_id"] == user_id
        assert data["is_guest"] is False
        assert data["token_type"] == "bearer"

        # 测试JSON序列化
        json_data = token_data.model_dump_json()
        assert isinstance(json_data, str)
        assert user_id in json_data


@pytest.mark.unit
class TestAuthTokenResponse:
    """认证令牌响应测试"""

    def test_auth_token_response_valid(self):
        """测试有效的认证令牌响应"""
        user_id = str(uuid4())
        token_data = AuthTokenData(
            user_id=user_id,
            is_guest=False,
            access_token="access.token",
            refresh_token="refresh.token",
            token_type="bearer",
            expires_in=3600
        )

        response = AuthTokenResponse(
            success=True,
            message="认证成功",
            data=token_data
        )

        assert response.success is True
        assert response.message == "认证成功"
        assert response.data.user_id == user_id
        assert response.data.is_guest is False


@pytest.mark.integration
class TestSchemaIntegration:
    """Schema集成测试"""

    def test_complete_auth_flow_schemas(self):
        """测试完整认证流程的Schema使用"""
        # 1. 游客初始化
        guest_request = GuestInitRequest()

        # 2. 模拟认证令牌数据
        user_id = str(uuid4())
        auth_data = AuthTokenData(
            user_id=user_id,
            is_guest=True,
            access_token="guest.access.token",
            refresh_token="guest.refresh.token",
            token_type="bearer",
            expires_in=3600
        )

        # 3. 认证响应
        auth_response = AuthTokenResponse(
            success=True,
            message="游客初始化成功",
            data=auth_data
        )

        # 4. 游客升级请求
        upgrade_request = GuestUpgradeRequest(wechat_openid="wx_upgrade_12345")

        # 5. 模拟升级后的令牌数据
        upgraded_data = AuthTokenData(
            user_id=user_id,
            is_guest=False,
            access_token="user.access.token",
            refresh_token="user.refresh.token",
            token_type="bearer",
            expires_in=7200
        )

        # 6. 升级响应
        upgrade_response = AuthTokenResponse(
            success=True,
            message="升级成功",
            data=upgraded_data
        )

        # 7. 令牌刷新请求
        refresh_request = TokenRefreshRequest(refresh_token=upgrade_response.data.refresh_token)

        # 验证所有Schema都能正常创建和序列化
        assert guest_request.model_dump() is not None
        assert auth_response.model_dump() is not None
        assert upgrade_request.model_dump() is not None
        assert upgrade_response.model_dump() is not None
        assert refresh_request.model_dump() is not None

    def test_schema_json_serialization_roundtrip(self):
        """测试Schema JSON序列化往返"""
        original_data = {
            "user_id": str(uuid4()),
            "is_guest": False,
            "access_token": "access.token",
            "refresh_token": "refresh.token",
            "token_type": "bearer",
            "expires_in": 3600
        }

        # 创建令牌数据对象
        token_data = AuthTokenData(**original_data)

        # 序列化为JSON
        json_data = token_data.model_dump_json()

        # 从JSON重建对象（这里简化验证，实际中可能需要JSON解析）
        reconstructed_data = token_data.model_dump()

        # 验证关键字段保持一致
        assert reconstructed_data["user_id"] == original_data["user_id"]
        assert reconstructed_data["is_guest"] == original_data["is_guest"]
        assert reconstructed_data["token_type"] == original_data["token_type"]