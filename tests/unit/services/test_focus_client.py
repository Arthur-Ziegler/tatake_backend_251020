"""
Focus微服务客户端单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.focus_microservice_client import FocusMicroserviceClient, get_focus_client


@pytest.fixture
def focus_client():
    """创建测试客户端"""
    return FocusMicroserviceClient()


@pytest.mark.asyncio
async def test_create_session(focus_client):
    """测试创建专注会话"""
    with patch.object(focus_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"session_id": "session_123"}
        mock_post.return_value = mock_response

        result = await focus_client.create_session("user_123", "task_456")

        assert result["session_id"] == "session_123"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_get_sessions(focus_client):
    """测试获取专注会话列表"""
    with patch.object(focus_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"sessions": [{"id": "s1"}, {"id": "s2"}]}
        mock_get.return_value = mock_response

        result = await focus_client.get_sessions("user_123")

        assert len(result["sessions"]) == 2
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_pause_session(focus_client):
    """测试暂停会话"""
    with patch.object(focus_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "paused"}
        mock_post.return_value = mock_response

        result = await focus_client.pause_session("session_123", "user_123")

        assert result["status"] == "paused"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_complete_session(focus_client):
    """测试完成会话"""
    with patch.object(focus_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "completed"}
        mock_post.return_value = mock_response

        result = await focus_client.complete_session("session_123", "user_123")

        assert result["status"] == "completed"
        mock_post.assert_called_once()


def test_get_focus_client_singleton():
    """测试单例模式"""
    client1 = get_focus_client()
    client2 = get_focus_client()
    assert client1 is client2
