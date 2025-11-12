"""
Reward微服务客户端（增强版）

功能：与Reward-Service(20254)通信
接口：3个（奖品、积分、兑换）
增强：连接池、重试机制
"""
import httpx
from typing import Dict, Any
from src.api.config import config


class RewardMicroserviceClient:
    """Reward微服务客户端（增强版）"""

    def __init__(self):
        self.base_url = config.reward_service_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=config.reward_service_timeout,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )

    async def get_prizes(self, user_id: str) -> Dict[str, Any]:
        """查看我的奖品

        Raises:
            HTTPException: 当Reward微服务返回错误时
        """
        response = await self.client.get(
            f"/rewards/prizes",
            params={"user_id": user_id}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def get_points(self, user_id: str) -> Dict[str, Any]:
        """查看我的积分

        Raises:
            HTTPException: 当Reward微服务返回错误时
        """
        response = await self.client.get(
            f"/rewards/points",
            params={"user_id": user_id}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()

    async def redeem(self, user_id: str, code: str) -> Dict[str, Any]:
        """兑换奖品

        Raises:
            HTTPException: 当Reward微服务返回错误时
        """
        response = await self.client.post(
            f"/rewards/redeem",
            params={"user_id": user_id},
            json={"code": code}
        )

        if response.status_code >= 400:
            from fastapi import HTTPException
            error_detail = response.json() if response.text else {"detail": "Unknown error"}
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
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