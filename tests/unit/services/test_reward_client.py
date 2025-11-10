"""
Reward微服务客户端单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.reward_microservice_client import RewardMicroserviceClient, get_reward_client


@pytest.fixture
def reward_client():
    """创建测试客户端"""
    return RewardMicroserviceClient()


@pytest.mark.asyncio
async def test_get_prizes(reward_client):
    """测试获取奖品"""
    with patch.object(reward_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"prizes": [{"name": "gold_coin", "quantity": 10}]}
        mock_get.return_value = mock_response

        result = await reward_client.get_prizes("user_123")

        assert len(result["prizes"]) == 1
        assert result["prizes"][0]["name"] == "gold_coin"
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_get_points(reward_client):
    """测试获取积分"""
    with patch.object(reward_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"current_balance": 1250}
        mock_get.return_value = mock_response

        result = await reward_client.get_points("user_123")

        assert result["current_balance"] == 1250
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_redeem(reward_client):
    """测试兑换奖品"""
    with patch.object(reward_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "prize": "diamond"}
        mock_post.return_value = mock_response

        result = await reward_client.redeem("user_123", "GOLD10")

        assert result["success"] is True
        assert result["prize"] == "diamond"
        mock_post.assert_called_once()


def test_get_reward_client_singleton():
    """测试单例模式"""
    client1 = get_reward_client()
    client2 = get_reward_client()
    assert client1 is client2
