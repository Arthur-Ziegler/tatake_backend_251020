"""
Reward微服务客户端（增强版）

功能：与Reward-Service(20254)通信
接口：3个（奖品、积分、兑换）
增强：连接池、重试机制
"""
import httpx
from typing import Dict, Any
from src.config.microservices import get_microservice_config

config = get_microservice_config()


class RewardMicroserviceClient:
    """Reward微服务客户端（增强版）"""

    def __init__(self):
        self.base_url = config.reward_service_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=config.request_timeout,
            limits=httpx.Limits(
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_keepalive_connections
            )
        )

    async def get_prizes(self, user_id: str) -> Dict[str, Any]:
        """查看我的奖品"""
        response = await self.client.get(
            f"/rewards/prizes",
            params={"user_id": user_id}
        )
        return response.json()

    async def get_points(self, user_id: str) -> Dict[str, Any]:
        """查看我的积分"""
        response = await self.client.get(
            f"/rewards/points",
            params={"user_id": user_id}
        )
        return response.json()

    async def redeem(self, user_id: str, code: str) -> Dict[str, Any]:
        """兑换奖品"""
        response = await self.client.post(
            f"/rewards/redeem",
            params={"user_id": user_id},
            json={"code": code}
        )
        return response.json()

    async def close(self):
        """关闭连接"""
        await self.client.aclose()




# 全局单例
_reward_client = None


def get_reward_client() -> RewardMicroserviceClient:
    """获取Reward客户端单例"""
    global _reward_client
    if _reward_client is None:
        _reward_client = RewardMicroserviceClient()
    return _reward_client


# ==================== 便捷方法 ====================

async def get_my_prizes(user_id: str) -> Dict[str, Any]:
    """
    4.1 查看我的奖品

    Args:
        user_id (str): 用户ID

    Returns:
        Dict[str, Any]: 奖品列表
    """
    client = get_reward_client()
    return await client._call_reward_service("GET", f"/users/{user_id}/rewards", user_id)


async def get_my_points(user_id: str) -> Dict[str, Any]:
    """
    4.2 查看我的积分

    Args:
        user_id (str): 用户ID

    Returns:
        Dict[str, Any]: 积分信息
    """
    client = get_reward_client()
    return await client._call_reward_service("GET", f"/users/{user_id}/points", user_id)


async def redeem_prize(user_id: str, redemption_code: str) -> Dict[str, Any]:
    """
    4.3 充值界面（兑换奖品）

    Args:
        user_id (str): 用户ID
        redemption_code (str): 兑换码

    Returns:
        Dict[str, Any]: 兑换结果
    """
    client = get_reward_client()
    data = {"code": redemption_code}  # 根据API文档，请求字段名为"code"而不是"redemption_code"
    return await client._call_reward_service("POST", f"/users/{user_id}/redeem", user_id, data)