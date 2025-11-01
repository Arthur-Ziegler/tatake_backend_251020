"""
奖励微服务客户端

提供与奖励微服务(http://45.152.65.130:20254)通信的HTTP客户端功能。
实现3个核心接口：
1. 查看我的奖品
2. 查看我的积分
3. 充值界面

作者：TaTake团队
版本：1.0.0
"""

import logging
import asyncio
from typing import Dict, Any, Optional

import httpx
from pydantic import BaseModel

from src.api.config import config


class RewardMicroserviceError(Exception):
    """奖励微服务调用异常"""

    def __init__(self, message: str, status_code: int = 500, original_error: Optional[Exception] = None):
        self.message = message
        self.status_code = status_code
        self.original_error = original_error
        super().__init__(message)


class RewardMicroserviceClient:
    """奖励微服务客户端"""

    def __init__(self):
        self.base_url = "http://45.152.65.130:20254"
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.logger = logging.getLogger(__name__)

    async def _call_reward_service(
        self,
        method: str,
        path: str,
        user_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用奖励微服务

        Args:
            method: HTTP方法
            path: API路径
            user_id: 用户ID
            data: 请求数据

        Returns:
            Dict[str, Any]: 微服务响应数据
        """
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "X-User-ID": user_id  # 微服务要求在头部传递用户ID
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            error_msg = f"奖励微服务HTTP错误: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg)
            raise RewardMicroserviceError(error_msg, e.response.status_code)
        except httpx.TimeoutException:
            error_msg = "奖励微服务调用超时"
            self.logger.error(error_msg)
            raise RewardMicroserviceError(error_msg, 504)
        except Exception as e:
            error_msg = f"奖励微服务调用异常: {str(e)}"
            self.logger.error(error_msg)
            raise RewardMicroserviceError(error_msg, 500, e)


# 全局客户端实例
_reward_client: Optional[RewardMicroserviceClient] = None


def get_reward_client() -> RewardMicroserviceClient:
    """获取奖励微服务客户端单例"""
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