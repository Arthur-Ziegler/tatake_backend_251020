"""
奖励系统集成服务

提供与奖励系统的集成功能，包括积分余额查询、缓存管理和错误处理。

设计原则：
1. 缓存优化：减少对奖励服务的重复调用
2. 错误处理：优雅处理服务不可用的情况
3. 性能优先：快速响应，支持异步操作
4. 降级策略：服务异常时返回合理默认值

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RewardsServiceClient(ABC):
    """奖励服务客户端抽象接口"""

    @abstractmethod
    async def get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户积分余额

        Args:
            user_id: 用户ID

        Returns:
            Dict: 包含积分余额的响应数据
        """
        pass


class RewardsIntegrationService:
    """
    奖励系统集成服务

    负责与奖励系统的集成，提供积分余额查询、缓存和错误处理功能。
    支持异步操作，提供高性能的用户积分查询服务。

    Attributes:
        _client: 奖励服务客户端
        _cache: 积分余额缓存
        _cache_ttl_minutes: 缓存过期时间（分钟）
    """

    def __init__(self, client: Optional[RewardsServiceClient] = None, cache_ttl_minutes: int = 5):
        """
        初始化奖励系统集成服务

        Args:
            client: 奖励服务客户端实例
            cache_ttl_minutes: 缓存过期时间，默认5分钟
        """
        self._client = client
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_minutes = cache_ttl_minutes

    async def get_user_balance(self, user_id: str) -> int:
        """
        获取用户积分余额

        先检查缓存，如果缓存有效则返回缓存值；
        否则调用奖励服务获取最新数据并缓存。

        Args:
            user_id: 用户ID

        Returns:
            int: 用户积分余额，服务异常时返回0
        """
        # 检查缓存
        if self._is_cache_valid(user_id):
            logger.debug(f"使用缓存积分余额: user_id={user_id}")
            cached_balance = self._cache[user_id]["balance"]
            return cached_balance

        # 缓存无效或不存在，调用奖励服务
        try:
            if not self._client:
                logger.warning("奖励服务客户端未配置，返回默认积分余额")
                return 0

            logger.debug(f"查询奖励服务积分余额: user_id={user_id}")
            response = await self._client.get_user_balance(user_id)

            # 解析响应
            balance = self._parse_balance_response(response)

            # 更新缓存
            self._update_cache(user_id, balance)

            logger.info(f"获取积分余额成功: user_id={user_id}, balance={balance}")
            return balance

        except asyncio.TimeoutError:
            logger.error(f"奖励服务超时: user_id={user_id}")
            return 0

        except Exception as e:
            logger.error(f"获取积分余额失败: user_id={user_id}, error={str(e)}")
            return 0

    def _parse_balance_response(self, response: Dict[str, Any]) -> int:
        """
        解析奖励服务响应

        Args:
            response: 奖励服务响应数据

        Returns:
            int: 积分余额，解析失败时返回0
        """
        try:
            if response.get("code") == 200 and response.get("data"):
                balance = response["data"].get("balance", 0)
                return int(balance) if balance is not None else 0
            else:
                logger.warning(f"奖励服务返回错误响应: {response}")
                return 0

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"解析积分余额响应失败: response={response}, error={str(e)}")
            return 0

    def _is_cache_valid(self, user_id: str, ttl_minutes: Optional[int] = None) -> bool:
        """
        检查缓存是否有效

        Args:
            user_id: 用户ID
            ttl_minutes: 缓存过期时间，默认使用实例配置

        Returns:
            bool: 缓存是否有效
        """
        if user_id not in self._cache:
            return False

        ttl = ttl_minutes or self._cache_ttl_minutes
        cache_entry = self._cache[user_id]
        cache_time = cache_entry["timestamp"]

        # 检查缓存是否过期
        expiry_time = cache_time + timedelta(minutes=ttl)
        return datetime.utcnow() < expiry_time

    def _update_cache(self, user_id: str, balance: int) -> None:
        """
        更新缓存

        Args:
            user_id: 用户ID
            balance: 积分余额
        """
        self._cache[user_id] = {
            "balance": balance,
            "timestamp": datetime.utcnow()
        }

    def clear_cache(self, user_id: str) -> None:
        """
        清理指定用户的缓存

        Args:
            user_id: 用户ID
        """
        if user_id in self._cache:
            del self._cache[user_id]
            logger.debug(f"清理用户缓存: user_id={user_id}")

    def clear_all_cache(self) -> None:
        """清理所有缓存"""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.debug(f"清理所有缓存，共清理 {cache_size} 个条目")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            Dict: 缓存统计数据
        """
        current_time = datetime.utcnow()
        valid_cache_count = 0
        expired_cache_count = 0

        for user_id, cache_entry in self._cache.items():
            cache_time = cache_entry["timestamp"]
            expiry_time = cache_time + timedelta(minutes=self._cache_ttl_minutes)

            if current_time < expiry_time:
                valid_cache_count += 1
            else:
                expired_cache_count += 1

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_cache_count,
            "expired_entries": expired_cache_count,
            "cache_ttl_minutes": self._cache_ttl_minutes
        }


class MockRewardsServiceClient(RewardsServiceClient):
    """
    模拟奖励服务客户端

    用于测试和开发环境，提供模拟的奖励服务响应。
    """

    def __init__(self):
        """初始化模拟客户端"""
        self._user_balances: Dict[str, int] = {}

    def set_user_balance(self, user_id: str, balance: int) -> None:
        """
        设置用户积分余额（用于测试）

        Args:
            user_id: 用户ID
            balance: 积分余额
        """
        self._user_balances[user_id] = balance

    async def get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户积分余额（模拟实现）

        Args:
            user_id: 用户ID

        Returns:
            Dict: 模拟的响应数据
        """
        # 模拟网络延迟
        await asyncio.sleep(0.01)

        balance = self._user_balances.get(user_id, 1000)  # 默认1000积分

        return {
            "code": 200,
            "data": {"balance": balance},
            "message": "success"
        }


# 全局奖励服务实例
_global_rewards_service: Optional[RewardsIntegrationService] = None


def get_rewards_service() -> RewardsIntegrationService:
    """
    获取全局奖励服务实例

    Returns:
        RewardsIntegrationService: 全局奖励服务实例
    """
    global _global_rewards_service
    if _global_rewards_service is None:
        # TODO: 根据配置创建实际的奖励服务客户端
        mock_client = MockRewardsServiceClient()
        _global_rewards_service = RewardsIntegrationService(client=mock_client)
    return _global_rewards_service


def reset_rewards_service():
    """重置全局奖励服务实例（用于测试）"""
    global _global_rewards_service
    _global_rewards_service = None