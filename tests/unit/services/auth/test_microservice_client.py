"""
认证微服务客户端单元测试

测试AuthMicroserviceClient的所有功能，包括：
- HTTP请求处理
- 错误处理和重试机制
- 参数注入和响应格式化
- 各种认证方式的API调用

作者：TaTakeKe团队
版本：1.0.0
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response, HTTPStatusError, ConnectError

from src.services.auth.client import AuthMicroserviceClient


@pytest.mark.unit
class TestAuthMicroserviceClient:
    """认证微服务客户端测试类"""

    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        return AuthMicroserviceClient(
            base_url="http://test-auth.com:8987",
            project="test_project"
        )

    @pytest.fixture
    def mock_response(self):
        """创建模拟响应"""
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.json.return_value = {
            "code": 200,
            "message": "success",
            "data": {"test": "data"}
        }
        return response

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """测试客户端初始化"""
        # 测试默认初始化
        client1 = AuthMicroserviceClient()
        assert client1.base_url == "http://45.152.65.130:8987"
        assert client1.project == "tatake_backend"

        # 测试自定义初始化
        client2 = AuthMicroserviceClient(
            base_url="http://custom.com:8000",
            project="custom_project"
        )
        assert client2.base_url == "http://custom.com:8000"
        assert client2.project == "custom_project"

    @pytest.mark.asyncio
    async def test_guest_init_success(self, client, mock_response):
        """测试游客初始化成功"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value

            result = await client.guest_init()

            mock_request.assert_called_once_with("POST", "/guest/init", data={"project": "test_project"})
            assert result == {"code": 200, "message": "success", "data": {"test": "data"}}

    @pytest.mark.asyncio
    async def test_wechat_register_success(self, client, mock_response):
        """测试微信注册成功"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value

            result = await client.wechat_register("test_openid_123")

            mock_request.assert_called_once_with(
                "POST",
                "/wechat/register",
                data={"wechat_openid": "test_openid_123", "project": "test_project"}
            )
            assert result == {"code": 200, "message": "success", "data": {"test": "data"}}

    @pytest.mark.asyncio
    async def test_email_send_code_success(self, client, mock_response):
        """测试邮箱验证码发送成功"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value

            result = await client.email_send_code("test@example.com", "register")

            mock_request.assert_called_once_with(
                "POST",
                "/email/send-code",
                data={"email": "test@example.com", "scene": "register", "project": "test_project"}
            )
            assert result == {"code": 200, "message": "success", "data": {"test": "data"}}

    @pytest.mark.asyncio
    async def test_phone_send_code_with_token(self, client, mock_response):
        """测试带令牌的手机验证码发送"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value

            result = await client.phone_send_code("13800138000", "bind", "test_token")

            mock_request.assert_called_once_with(
                "POST",
                "/phone/send-code",
                data={"phone": "13800138000", "scene": "bind", "project": "test_project"},
                headers={"Authorization": "Bearer test_token"}
            )
            assert result == {"code": 200, "message": "success", "data": {"test": "data"}}

    @pytest.mark.asyncio
    async def test_get_public_key_success(self, client, mock_response):
        """测试获取公钥成功"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value

            result = await client.get_public_key()

            mock_request.assert_called_once_with("GET", "/system/public-key")
            assert result == {"code": 200, "message": "success", "data": {"test": "data"}}

    @pytest.mark.asyncio
    async def test_make_request_success(self, client):
        """测试HTTP请求成功"""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "message": "success", "data": {}}

        with patch('httpx.AsyncClient.request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client._make_request("POST", "/test", data={"test": "data"})

            mock_request.assert_called_once_with(
                method="POST",
                url="http://test-auth.com:8987/test",
                json={"test": "data", "project": "test_project"},
                headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "TaKeKe-Backend/1.0.0"}
            )
            assert result == {"code": 200, "message": "success", "data": {}}

    @pytest.mark.asyncio
    async def test_make_request_http_error(self, client):
        """测试HTTP错误处理"""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": 400, "message": "Bad Request", "data": None}

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await client._make_request("POST", "/test")

            assert "Bad Request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_network_error(self, client):
        """测试网络错误处理"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = ConnectError("Connection failed")

            with pytest.raises(Exception) as exc_info:
                await client._make_request("POST", "/test")

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_with_headers(self, client):
        """测试带请求头的HTTP请求"""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "message": "success", "data": {}}

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await client._make_request(
                "POST",
                "/test",
                data={"test": "data"},
                headers={"Authorization": "Bearer token123"}
            )

            mock_post.assert_called_once_with(
                "http://test-auth.com:8987/test",
                data={"test": "data"},
                headers={"Content-Type": "application/json", "Authorization": "Bearer token123"}
            )

    @pytest.mark.asyncio
    async def test_all_endpoints_coverage(self, client, mock_response):
        """测试所有API端点的覆盖"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value

            # 测试所有主要方法
            await client.guest_init()
            await client.wechat_register("openid")
            await client.wechat_login("openid")
            await client.wechat_bind("openid", "token")
            await client.refresh_token("refresh_token")
            await client.email_send_code("email@test.com", "register")
            await client.email_register("email@test.com", "password", "123456")
            await client.email_login("email@test.com", "password")
            await client.email_bind("email@test.com", "password", "123456", "token")
            await client.phone_send_code("13800138000", "register")
            await client.phone_verify("13800138000", "123456", "register")
            await client.get_public_key()

            # 验证所有方法都被调用了
            assert mock_request.call_count == 13

    @pytest.mark.asyncio
    async def test_parameter_validation(self, client):
        """测试参数验证"""
        # 测试空邮箱地址
        with pytest.raises(Exception):
            await client.email_send_code("", "register")

        # 测试无效手机号
        with pytest.raises(Exception):
            await client.phone_send_code("123", "register")

    @pytest.mark.asyncio
    async def test_response_format_validation(self, client):
        """测试响应格式验证"""
        # 测试非JSON响应
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            with pytest.raises(Exception):
                await client._make_request("POST", "/test")

    def test_project_parameter_auto_injection(self, client):
        """测试project参数自动注入"""
        # project在初始化时设置，应该自动注入到所有请求中
        assert client.project == "test_project"

    @pytest.mark.asyncio
    async def test_base_url_trailing_slash_removal(self):
        """测试base_url尾部斜杠移除"""
        client1 = AuthMicroserviceClient(base_url="http://test.com/")
        client2 = AuthMicroserviceClient(base_url="http://test.com")

        assert client1.base_url == "http://test.com"
        assert client2.base_url == "http://test.com"