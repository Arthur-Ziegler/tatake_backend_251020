"""
奖励系统集成服务单元测试

测试与奖励系统的集成，包括积分余额查询、缓存和错误处理。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import UUID
from datetime import datetime, timedelta

from src.services.rewards_integration_service import RewardsIntegrationService


class TestRewardsIntegrationService:
    """奖励系统集成服务测试类"""

    @pytest.fixture
    def mock_rewards_client(self):
        """模拟奖励服务客户端fixture"""
        client = Mock()
        client.get_user_balance = AsyncMock()
        return client

    @pytest.fixture
    def rewards_service(self, mock_rewards_client):
        """奖励服务实例fixture"""
        return RewardsIntegrationService(client=mock_rewards_client)

    @pytest.mark.asyncio
    async def test_get_user_balance_success(self, rewards_service: RewardsIntegrationService, mock_rewards_client):
        """
        测试成功获取用户积分余额

        Given: 有效的用户ID和奖励服务响应
        When: 调用get_user_balance方法
        Then: 应该返回正确的积分余额
        """
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        expected_balance = 1500

        # 模拟奖励服务响应
        mock_rewards_client.get_user_balance.return_value = {
            "code": 200,
            "data": {"balance": expected_balance},
            "message": "success"
        }

        balance = await rewards_service.get_user_balance(str(user_id))

        assert balance == expected_balance
        mock_rewards_client.get_user_balance.assert_called_once_with(str(user_id))

    @pytest.mark.asyncio
    async def test_get_user_balance_with_cache(self, rewards_service: RewardsIntegrationService, mock_rewards_client):
        """
        测试积分余额缓存功能

        Given: 用户积分余额已缓存
        When: 多次调用get_user_balance方法
        Then: 应该使用缓存值，减少服务调用
        """
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        expected_balance = 1500

        # 模拟奖励服务响应
        mock_rewards_client.get_user_balance.return_value = {
            "code": 200,
            "data": {"balance": expected_balance},
            "message": "success"
        }

        # 第一次调用
        balance1 = await rewards_service.get_user_balance(str(user_id))
        # 第二次调用（应该使用缓存）
        balance2 = await rewards_service.get_user_balance(str(user_id))

        assert balance1 == expected_balance
        assert balance2 == expected_balance
        # 应该只调用一次奖励服务
        assert mock_rewards_client.get_user_balance.call_count == 1

    @pytest.mark.asyncio
    async def test_get_user_balance_service_error(self, rewards_service: RewardsIntegrationService, mock_rewards_client):
        """
        测试奖励服务错误处理

        Given: 奖励服务返回错误
        When: 调用get_user_balance方法
        Then: 应该返回默认值并记录错误
        """
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        # 模拟奖励服务错误
        mock_rewards_client.get_user_balance.side_effect = Exception("Service unavailable")

        balance = await rewards_service.get_user_balance(str(user_id))

        assert balance == 0  # 默认值
        mock_rewards_client.get_user_balance.assert_called_once_with(str(user_id))

    @pytest.mark.asyncio
    async def test_get_user_balance_service_timeout(self, rewards_service: RewardsIntegrationService, mock_rewards_client):
        """
        测试奖励服务超时处理

        Given: 奖励服务响应超时
        When: 调用get_user_balance方法
        Then: 应该返回默认值
        """
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        # 模拟服务超时
        mock_rewards_client.get_user_balance.side_effect = TimeoutError("Service timeout")

        balance = await rewards_service.get_user_balance(str(user_id))

        assert balance == 0  # 默认值

    @pytest.mark.asyncio
    async def test_get_user_balance_invalid_response(self, rewards_service: RewardsIntegrationService, mock_rewards_client):
        """
        测试奖励服务无效响应处理

        Given: 奖励服务返回无效响应
        When: 调用get_user_balance方法
        Then: 应该返回默认值
        """
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        # 模拟无效响应
        mock_rewards_client.get_user_balance.return_value = {
            "code": 500,
            "data": None,
            "message": "Internal server error"
        }

        balance = await rewards_service.get_user_balance(str(user_id))

        assert balance == 0  # 默认值

    @pytest.mark.asyncio
    async def test_cache_expiration(self, rewards_service: RewardsIntegrationService, mock_rewards_client):
        """
        测试缓存过期机制

        Given: 缓存的积分余额已过期
        When: 再次调用get_user_balance方法
        Then: 应该重新调用奖励服务
        """
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        expected_balance = 1500

        # 模拟奖励服务响应
        mock_rewards_client.get_user_balance.return_value = {
            "code": 200,
            "data": {"balance": expected_balance},
            "message": "success"
        }

        # 第一次调用
        balance1 = await rewards_service.get_user_balance(str(user_id))

        # 模拟缓存过期（需要手动清理缓存或等待过期）
        rewards_service.clear_cache(str(user_id))

        # 第二次调用（缓存已过期）
        balance2 = await rewards_service.get_user_balance(str(user_id))

        assert balance1 == expected_balance
        assert balance2 == expected_balance
        # 应该调用两次奖励服务
        assert mock_rewards_client.get_user_balance.call_count == 2

    def test_is_cache_valid(self, rewards_service: RewardsIntegrationService):
        """
        测试缓存有效性检查

        Given: 不同时间的缓存条目
        When: 检查缓存是否有效
        Then: 应该正确判断缓存有效性
        """
        user_id = "test-user"
        current_time = datetime.utcnow()

        # 有效缓存（未过期）
        valid_cache_time = current_time - timedelta(minutes=3)  # 3分钟前
        rewards_service._cache[user_id] = {
            "balance": 1000,
            "timestamp": valid_cache_time
        }
        assert rewards_service._is_cache_valid(user_id, ttl_minutes=5) is True

        # 过期缓存
        invalid_cache_time = current_time - timedelta(minutes=10)  # 10分钟前
        rewards_service._cache[user_id] = {
            "balance": 1000,
            "timestamp": invalid_cache_time
        }
        assert rewards_service._is_cache_valid(user_id, ttl_minutes=5) is False

        # 不存在的缓存
        assert rewards_service._is_cache_valid("non-existent-user") is False

    def test_clear_cache(self, rewards_service: RewardsIntegrationService):
        """
        测试清理缓存功能

        Given: 存在缓存数据
        When: 调用clear_cache方法
        Then: 应该清理指定用户的缓存
        """
        user_id = "test-user"
        rewards_service._cache[user_id] = {
            "balance": 1000,
            "timestamp": datetime.utcnow()
        }

        # 验证缓存存在
        assert user_id in rewards_service._cache

        # 清理缓存
        rewards_service.clear_cache(user_id)

        # 验证缓存已清理
        assert user_id not in rewards_service._cache

    def test_clear_all_cache(self, rewards_service: RewardsIntegrationService):
        """
        测试清理所有缓存功能

        Given: 存在多个用户的缓存数据
        When: 调用clear_all_cache方法
        Then: 应该清理所有缓存
        """
        # 添加多个用户的缓存
        for i in range(3):
            user_id = f"user-{i}"
            rewards_service._cache[user_id] = {
                "balance": 1000 + i,
                "timestamp": datetime.utcnow()
            }

        # 验证缓存存在
        assert len(rewards_service._cache) == 3

        # 清理所有缓存
        rewards_service.clear_all_cache()

        # 验证所有缓存已清理
        assert len(rewards_service._cache) == 0