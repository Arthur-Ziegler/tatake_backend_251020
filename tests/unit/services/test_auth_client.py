"""
Auth微服务客户端单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.auth_microservice_client import AuthMicroserviceClient, get_auth_client


@pytest.fixture
def auth_client():
    """创建测试客户端"""
    return AuthMicroserviceClient()


@pytest.mark.asyncio
async def test_wechat_login(auth_client):
    """测试微信登录"""
    with patch.object(auth_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_post.return_value = mock_response

        result = await auth_client.wechat_login("test_openid")

        assert result["access_token"] == "test_token"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_phone_send_code(auth_client):
    """测试发送验证码"""
    with patch.object(auth_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": "123456"}
        mock_post.return_value = mock_response

        result = await auth_client.phone_send_code("13800138000")

        assert result["code"] == "123456"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_phone_verify(auth_client):
    """测试验证手机验证码"""
    with patch.object(auth_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "verified_token"}
        mock_post.return_value = mock_response

        result = await auth_client.phone_verify("13800138000", "123456")

        assert result["access_token"] == "verified_token"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token(auth_client):
    """测试刷新token"""
    with patch.object(auth_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "new_token"}
        mock_post.return_value = mock_response

        result = await auth_client.refresh_token("old_refresh_token")

        assert result["access_token"] == "new_token"
        mock_post.assert_called_once()


def test_get_auth_client_singleton():
    """测试单例模式"""
    client1 = get_auth_client()
    client2 = get_auth_client()
    assert client1 is client2
