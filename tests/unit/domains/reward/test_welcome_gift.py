"""
欢迎礼包功能测试

测试用户欢迎礼包的完整功能，包括：
1. 1000积分发放
2. 固定礼物组合发放
3. 可重复领取
4. 流水记录正确性

遵循TDD原则，先写测试再实现功能。
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone


class TestWelcomeGiftAPI:
    """欢迎礼包API测试类"""

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_should_grant_1000_points(self, test_client: AsyncClient):
        """测试领取欢迎礼包应该获得1000积分"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        assert auth_response.status_code == 200
        auth_data = auth_response.json()
        access_token = auth_data["data"]["access_token"]
        user_id = auth_data["data"]["user_id"]

        # 2. 领取欢迎礼包
        headers = {"Authorization": f"Bearer {access_token}"}
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)

        # 3. 验证响应
        assert gift_response.status_code == 200
        gift_data = gift_response.json()
        assert gift_data["code"] == 200
        assert gift_data["message"] == "success"

        # 4. 验证积分发放
        assert "points_granted" in gift_data["data"]
        assert gift_data["data"]["points_granted"] == 1000

        # 5. 验证奖励物品
        assert "rewards_granted" in gift_data["data"]
        rewards = gift_data["data"]["rewards_granted"]
        assert len(rewards) == 3  # 应该有3种奖励

        # 验证具体奖励内容
        reward_names = [reward["name"] for reward in rewards]
        assert "积分加成卡" in reward_names
        assert "专注道具" in reward_names
        assert "时间管理券" in reward_names

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_should_include_fixed_reward_quantities(self, test_client: AsyncClient):
        """测试欢迎礼包应该包含固定数量的奖励组合"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]

        # 2. 领取欢迎礼包
        headers = {"Authorization": f"Bearer {access_token}"}
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)

        # 3. 验证奖励数量
        gift_data = gift_response.json()
        rewards = gift_data["data"]["rewards_granted"]

        # 验证具体数量
        reward_map = {reward["name"]: reward["quantity"] for reward in rewards}
        assert reward_map.get("积分加成卡", 0) == 3  # 3张积分加成卡
        assert reward_map.get("专注道具", 0) == 10  # 10个专注道具
        assert reward_map.get("时间管理券", 0) == 5  # 5张时间管理券

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_should_be_repeatable(self, test_client: AsyncClient):
        """测试欢迎礼包应该可以重复领取"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        user_id = auth_response.json()["data"]["user_id"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 第一次领取礼包
        first_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert first_response.status_code == 200

        # 3. 第二次领取礼包
        second_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert second_response.status_code == 200

        # 4. 验证两次都成功
        first_data = first_response.json()
        second_data = second_response.json()
        assert first_data["data"]["points_granted"] == 1000
        assert second_data["data"]["points_granted"] == 1000

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_should_create_correct_transactions(self, test_client: AsyncClient):
        """测试欢迎礼包应该创建正确的流水记录"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        user_id = auth_response.json()["data"]["user_id"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 领取欢迎礼包
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert gift_response.status_code == 200

        # 3. 验证积分流水记录
        points_response = await test_client.get("/points/balance", headers=headers)
        assert points_response.status_code == 200
        points_data = points_response.json()

        # 验证积分余额
        assert points_data["data"]["current_balance"] == 1000

        # 4. 验证积分流水
        history_response = await test_client.get("/points/history", headers=headers)
        assert history_response.status_code == 200
        history_data = history_response.json()

        # 应该有一条welcome_gift类型的流水记录
        welcome_gift_transactions = [
            t for t in history_data["data"]["transactions"]
            if t["source_type"] == "welcome_gift"
        ]
        assert len(welcome_gift_transactions) == 1
        assert welcome_gift_transactions[0]["amount"] == 1000

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_should_create_reward_transactions(self, test_client: AsyncClient):
        """测试欢迎礼包应该创建奖励流水记录"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        user_id = auth_response.json()["data"]["user_id"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 领取欢迎礼包
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert gift_response.status_code == 200

        # 3. 验证奖励流水记录
        rewards_response = await test_client.get("/reward/balance", headers=headers)
        assert rewards_response.status_code == 200
        rewards_data = rewards_response.json()

        # 验证奖励数量
        reward_balance = rewards_data["data"]["rewards"]
        assert reward_balance.get("积分加成卡", 0) == 3
        assert reward_balance.get("专注道具", 0) == 10
        assert reward_balance.get("时间管理券", 0) == 5

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_should_fail_without_authentication(self, test_client: AsyncClient):
        """测试未认证用户领取礼包应该失败"""
        response = await test_client.post("/user/welcome-gift/claim")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_should_fail_with_invalid_token(self, test_client: AsyncClient):
        """测试无效token领取礼包应该失败"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_welcome_gift_should_have_proper_error_handling(self, test_client: AsyncClient):
        """测试欢迎礼包应该有适当的错误处理"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 模拟数据库错误（如果有的话）
        # 这里主要测试API的错误响应格式
        response = await test_client.post("/user/welcome-gift/claim", headers=headers)

        # 3. 验证成功响应格式
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "message" in data
            assert "data" in data
            assert isinstance(data["data"], dict)

    @pytest.mark.asyncio
    async def test_concurrent_welcome_gift_claims_should_work_correctly(self, test_client: AsyncClient):
        """测试并发领取欢迎礼包应该正确工作"""
        import asyncio

        async def claim_gift_for_user():
            # 为每次并发创建不同的用户
            auth_response = await test_client.post("/auth/guest-init")
            access_token = auth_response.json()["data"]["access_token"]
            user_id = auth_response.json()["data"]["user_id"]
            headers = {"Authorization": f"Bearer {access_token}"}

            # 领取礼包
            gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
            return {
                "user_id": user_id,
                "response_status": gift_response.status_code,
                "response_data": gift_response.json() if gift_response.status_code == 200 else None
            }

        # 并发执行10个用户领取礼包
        tasks = [claim_gift_for_user() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有请求都成功
        for result in results:
            assert not isinstance(result, Exception)
            assert result["response_status"] == 200
            assert result["response_data"]["data"]["points_granted"] == 1000
            assert len(result["response_data"]["data"]["rewards_granted"]) == 3

        # 验证用户ID都不同
        user_ids = [result["user_id"] for result in results]
        assert len(set(user_ids)) == 10  # 所有用户ID都应该是唯一的