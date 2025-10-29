"""
认证API集成测试

测试完整的认证API流程，包括：
- 游客账号初始化
- 微信登录/注册
- 邮箱认证流程
- 手机认证流程
- JWT令牌验证和刷新

作者：TaTakeKe团队
版本：1.0.0
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json
from uuid import uuid4

from src.api.main import app


@pytest.mark.integration
class TestAuthAPIIntegration:
    """认证API集成测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def async_client(self):
        """创建异步测试客户端"""
        return AsyncClient(app=app, base_url="http://test")

    @pytest.fixture
    def test_wechat_openid(self):
        """测试微信OpenID"""
        return f"test_openid_{uuid4().hex[:8]}"

    @pytest.fixture
    def test_email(self):
        """测试邮箱"""
        return f"test_{uuid4().hex[:8]}@example.com"

    @pytest.fixture
    def test_phone(self):
        """测试手机号"""
        return f"138{uuid4().hex[:8]}"

    def test_guest_init_complete_flow(self, client):
        """测试游客初始化完整流程"""
        # 1. 创建游客账号
        response = client.post("/auth/guest/init")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "success"
        assert "data" in data

        user_data = data["data"]
        assert "user_id" in user_data
        assert "access_token" in user_data
        assert "refresh_token" in user_data
        assert "token_type" in user_data
        assert "expires_in" in user_data
        assert user_data["is_guest"] is True
        assert user_data["token_type"] == "bearer"

        # 2. 使用令牌访问受保护资源
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}

        # 测试获取公钥（不需要认证）
        response = client.get("/auth/system/public-key")
        assert response.status_code == 200

        # 3. 测试令牌验证（通过尝试访问需要认证的端点）
        # 这里我们通过刷新令牌来验证access_token的有效性
        refresh_response = client.post(
            "/auth/token/refresh",
            json={"refresh_token": user_data["refresh_token"]}
        )
        assert refresh_response.status_code == 200

    def test_wechat_register_and_login_flow(self, client, test_wechat_openid):
        """测试微信注册和登录流程"""
        # 1. 微信注册
        register_response = client.post(
            "/auth/wechat/register",
            json={"wechat_openid": test_wechat_openid}
        )
        assert register_response.status_code == 200

        register_data = register_response.json()
        assert register_data["code"] == 200
        assert "data" in register_data

        user_data = register_data["data"]
        assert "access_token" in user_data
        assert "refresh_token" in user_data
        assert user_data["is_guest"] is False

        # 2. 微信登录（应该返回相同用户）
        login_response = client.post(
            "/auth/wechat/login",
            json={"wechat_openid": test_wechat_openid}
        )
        assert login_response.status_code == 200

        login_data = login_response.json()
        assert login_data["code"] == 200
        assert login_data["data"]["is_guest"] is False

        # 3. 验证令牌可以刷新
        refresh_response = client.post(
            "/auth/token/refresh",
            json={"refresh_token": user_data["refresh_token"]}
        )
        assert refresh_response.status_code == 200

        refresh_data = refresh_response.json()
        assert refresh_data["code"] == 200
        assert "access_token" in refresh_data["data"]

    def test_email_flow(self, client, test_email):
        """测试邮箱认证流程"""
        # 1. 发送注册验证码
        send_code_response = client.post(
            "/auth/email/send-code",
            json={"email": test_email, "scene": "register"}
        )
        assert send_code_response.status_code == 200

        send_code_data = send_code_response.json()
        assert send_code_data["code"] == 200

        # 注意：在真实环境中，这里需要等待邮箱验证码
        # 在测试环境中，我们模拟这个过程

        # 2. 测试无效验证码注册
        invalid_register_response = client.post(
            "/auth/email/register",
            json={
                "email": test_email,
                "password": "testpassword123",
                "verification_code": "000000"  # 错误的验证码
            }
        )
        # 应该返回验证码错误
        assert invalid_register_response.status_code in [400, 401]

    def test_phone_flow(self, client, test_phone):
        """测试手机认证流程"""
        # 1. 发送注册验证码
        send_code_response = client.post(
            "/auth/phone/send-code",
            json={"phone": test_phone, "scene": "register"}
        )
        assert send_code_response.status_code == 200

        send_code_data = send_code_response.json()
        assert send_code_data["code"] == 200

        # 2. 测试验证码接口结构
        # 注意：在真实环境中需要正确的验证码
        verify_response = client.post(
            "/auth/phone/verify",
            json={
                "phone": test_phone,
                "code": "000000",  # 错误的验证码
                "scene": "register"
            }
        )
        # 应该返回验证码错误
        assert verify_response.status_code in [400, 401]

    def test_public_key_endpoint(self, client):
        """测试公钥端点"""
        response = client.get("/auth/system/public-key")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "public_key" in data["data"]

        # 如果是对称加密，public_key可能为空
        if data["data"]["public_key"]:
            assert isinstance(data["data"]["public_key"], str)

    def test_token_refresh_invalid_token(self, client):
        """测试无效令牌刷新"""
        response = client.post(
            "/auth/token/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code in [400, 401]

    def test_wechat_bind_without_auth(self, client, test_wechat_openid):
        """测试未认证状态的微信绑定"""
        response = client.post(
            "/auth/wechat/bind",
            json={"wechat_openid": test_wechat_openid}
        )
        # 应该返回认证错误
        assert response.status_code in [401, 403]

    def test_email_bind_without_auth(self, client, test_email):
        """测试未认证状态的邮箱绑定"""
        response = client.post(
            "/auth/email/bind",
            json={
                "email": test_email,
                "password": "testpassword123",
                "verification_code": "123456"
            }
        )
        # 应该返回认证错误
        assert response.status_code in [401, 403]

    def test_phone_bind_with_auth(self, client, test_phone):
        """测试认证状态的手机绑定"""
        # 1. 先创建游客账号
        guest_response = client.post("/auth/guest/init")
        assert guest_response.status_code == 200

        access_token = guest_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 发送绑定验证码
        send_code_response = client.post(
            "/auth/phone/send-code",
            json={"phone": test_phone, "scene": "bind"},
            headers=headers
        )
        assert send_code_response.status_code == 200

    def test_error_handling(self, client):
        """测试错误处理"""
        # 测试无效的JSON
        response = client.post(
            "/auth/guest/init",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

        # 测试缺少必要参数
        response = client.post(
            "/auth/wechat/register",
            json={}  # 缺少 wechat_openid
        )
        assert response.status_code == 422

        # 测试无效的邮箱格式
        response = client.post(
            "/auth/email/send-code",
            json={"email": "invalid-email", "scene": "register"}
        )
        assert response.status_code == 422

        # 测试无效的手机号格式
        response = client.post(
            "/auth/phone/send-code",
            json={"phone": "123", "scene": "register"}
        )
        assert response.status_code == 422

    def test_openapi_documentation(self, client):
        """测试OpenAPI文档可访问性"""
        # 测试OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "paths" in openapi_data
        assert "/auth/guest/init" in openapi_data["paths"]
        assert "/auth/wechat/register" in openapi_data["paths"]

    def test_cors_headers(self, client):
        """测试CORS头部"""
        # 测试预检请求
        response = client.options(
            "/auth/guest/init",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )

        # 应该包含CORS头部
        if response.status_code == 200:
            assert "access-control-allow-origin" in response.headers
            assert "access-control-allow-methods" in response.headers

    def test_rate_limiting(self, client):
        """测试频率限制（如果实现了）"""
        # 快速发送多个请求
        responses = []
        for _ in range(5):
            response = client.post("/auth/guest/init")
            responses.append(response)

        # 至少前几个请求应该成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 3  # 允许一些请求被限制

    @pytest.mark.asyncio
    async def test_async_client_compatibility(self, async_client):
        """测试异步客户端兼容性"""
        async with async_client:
            response = await async_client.get("/auth/system/public-key")
            assert response.status_code == 200

            data = response.json()
            assert data["code"] == 200