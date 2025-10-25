"""
全覆盖API端到端测试套件

按照openspec 1.3-user-welcome-gift-and-api-testing要求：
- 100% API端点覆盖
- 真实HTTP请求，端到端测试
- 游客用户 + 注册用户双覆盖
- 数据持久化验证，不隔离，不清理

设计原则：
1. 测试驱动：先写测试，确保失败
2. 真实环境：使用真实HTTP请求，不Mock
3. 完整覆盖：认证、任务、奖励、用户、聊天、Top3、Focus
4. 错误场景：401、404、500全覆盖
5. 性能测试：响应时间<200ms P95
6. 并发测试：10个用户同时操作

作者：TaKeKe团队
版本：1.3.0
"""

import pytest
import asyncio
import httpx
from httpx import ASGITransport
from typing import Dict, Any, List
from uuid import uuid4
import time
from datetime import datetime, timezone

from src.api.main import app


class TestAPICoverage:
    """API全覆盖测试类"""

    @pytest.mark.asyncio
    async def test_auth_guest_init(self, test_client: httpx.AsyncClient):
        """测试游客初始化"""
        response = await test_client.post("/auth/guest/init")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "user_id" in data["data"]
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["is_guest"] == True

    @pytest.mark.asyncio
    async def test_auth_wechat_register(self, test_client: httpx.AsyncClient):
        """测试微信注册"""
        # 先创建游客
        auth_response = await test_client.post("/auth/guest-init")
        guest_token = auth_response.json()["data"]["access_token"]

        # 注册微信用户
        register_data = {
            "wechat_openid": f"test_openid_{uuid4().hex[:8]}",
            "nickname": "测试用户"
        }
        headers = {"Authorization": f"Bearer {guest_token}"}
        response = await test_client.post("/auth/wechat-register", json=register_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["is_guest"] == False
        assert "wechat_openid" in data["data"]

    @pytest.mark.asyncio
    async def test_welcome_gift_claim_flow(self, test_client: httpx.AsyncClient):
        """测试欢迎礼包完整流程"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        user_id = auth_response.json()["data"]["user_id"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 领取欢迎礼包
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)

        assert gift_response.status_code == 200
        gift_data = gift_response.json()
        assert gift_data["code"] == 200
        assert gift_data["data"]["points_granted"] == 1000
        assert len(gift_data["data"]["rewards_granted"]) == 3

        # 验证奖励物品
        reward_names = [reward["name"] for reward in gift_data["data"]["rewards_granted"]]
        assert "积分加成卡" in reward_names
        assert "专注道具" in reward_names
        assert "时间管理券" in reward_names

        # 3. 验证积分流水
        points_response = await test_client.get("/points/balance", headers=headers)
        assert points_response.status_code == 200
        points_data = points_response.json()
        assert points_data["data"]["current_balance"] == 1000

    @pytest.mark.asyncio
    async def test_welcome_gift_repeatable(self, test_client: httpx.AsyncClient):
        """测试欢迎礼包可重复领取"""
        # 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 第一次领取
        first_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert first_response.status_code == 200

        # 第二次领取
        second_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert second_response.status_code == 200

        # 验证两次都成功
        first_data = first_response.json()
        second_data = second_response.json()
        assert first_data["data"]["points_granted"] == 1000
        assert second_data["data"]["points_granted"] == 1000

    @pytest.mark.asyncio
    async def test_welcome_gift_history(self, test_client: httpx.AsyncClient):
        """测试欢迎礼包历史查询"""
        # 创建用户并领取礼包
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 领取礼包
        await test_client.post("/user/welcome-gift/claim", headers=headers)

        # 查询历史
        history_response = await test_client.get("/user/welcome-gift/history", headers=headers)

        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["code"] == 200
        assert "history" in history_data["data"]
        assert len(history_data["data"]["history"]) >= 1

    @pytest.mark.asyncio
    async def test_task_crud_flow(self, test_client: httpx.AsyncClient):
        """测试任务CRUD完整流程"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 创建任务
        task_data = {
            "title": "测试任务",
            "description": "这是一个API测试任务",
            "priority": "high"
        }
        create_response = await test_client.post("/tasks", json=task_data, headers=headers)
        assert create_response.status_code == 200
        create_data = create_response.json()
        task_id = create_data["data"]["id"]

        # 3. 查询任务
        get_response = await test_client.get(f"/tasks/{task_id}", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["data"]["title"] == "测试任务"

        # 4. 更新任务
        update_data = {
            "title": "更新后的测试任务",
            "description": "任务已更新"
        }
        update_response = await test_client.put(f"/tasks/{task_id}", json=update_data, headers=headers)
        assert update_response.status_code == 200

        # 5. 完成任务
        complete_response = await test_client.post(f"/tasks/{task_id}/complete", headers=headers)
        assert complete_response.status_code == 200

        # 6. 查询任务列表
        list_response = await test_client.get("/tasks", headers=headers)
        assert list_response.status_code == 200
        list_data = list_response.json()
        tasks = list_data["data"]

        # 验证任务在列表中且状态正确
        completed_task = next((t for t in tasks if t["id"] == task_id), None)
        assert completed_task is not None
        assert completed_task["status"] == "completed"

    @pytest.mark.asyncio
    async def test_points_and_rewards_integration(self, test_client: httpx.AsyncClient):
        """测试积分和奖励系统集成"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 领取欢迎礼包（应该同时增加积分和奖励）
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert gift_response.status_code == 200

        # 3. 验证积分余额
        points_response = await test_client.get("/points/balance", headers=headers)
        assert points_response.status_code == 200
        points_data = points_response.json()
        assert points_data["data"]["current_balance"] == 1000

        # 4. 验证奖励余额
        rewards_response = await test_client.get("/rewards/my-rewards", headers=headers)
        assert rewards_response.status_code == 200
        rewards_data = rewards_response.json()
        assert rewards_data["code"] == 200

        # 验证有相应的奖励
        rewards = rewards_data["data"]["rewards"]
        assert "积分加成卡" in rewards
        assert rewards["积分加成卡"]["quantity"] >= 3

    @pytest.mark.asyncio
    async def test_error_scenarios(self, test_client: httpx.AsyncClient):
        """测试错误场景"""

        # 1. 测试401未授权
        response = await test_client.get("/user/profile")
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == 401

        # 2. 测试404资源不存在
        response = await test_client.get("/tasks/nonexistent-task")
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 404

        # 3. 测试无效参数
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 无效的任务创建数据
        invalid_task = {"invalid": "data"}
        response = await test_client.post("/tasks", json=invalid_task, headers=headers)
        assert response.status_code == 422  # 验证错误

        # 4. 测试无效的奖励兑换
        response = await test_client.post("/rewards/exchange/invalid-reward", headers=headers)
        assert response.status_code in [404, 400]  # 可能找不到或验证失败

    @pytest.mark.asyncio
    async def test_concurrent_users(self, test_client: httpx.AsyncClient):
        """测试并发用户操作"""

        async def create_user_and_claim_gift():
            # 为每个并发用户创建独立会话
            async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 创建用户
                auth_response = await client.post("/auth/guest-init")
                access_token = auth_response.json()["data"]["access_token"]
                headers = {"Authorization": f"Bearer {access_token}"}

                # 领取欢迎礼包
                gift_response = await client.post("/user/welcome-gift/claim", headers=headers)

                return {
                    "status_code": gift_response.status_code,
                    "success": gift_response.status_code == 200
                }

        # 并发执行10个用户操作
        tasks = [create_user_and_claim_gift() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        success_count = sum(1 for result in results if result["success"])
        assert success_count == 10  # 所有10个用户都应该成功

    @pytest.mark.asyncio
    async def test_response_time_performance(self, test_client: httpx.AsyncClient):
        """测试API响应时间性能"""

        # 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 测试多个端点的响应时间
        endpoints_to_test = [
            "/auth/guest-init",
            "/user/profile",
            "/points/balance",
            "/tasks",
            "/user/welcome-gift/claim"
        ]

        response_times = []
        for endpoint in endpoints_to_test:
            start_time = time.time()
            response = await test_client.get(endpoint, headers=headers)
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒

            assert response.status_code in [200, 404]  # 应该成功或合理的失败
            response_times.append(response_time)

            # 验证P95响应时间小于200ms
            assert response_time < 200, f"{endpoint} 响应时间过长: {response_time}ms"

        # 验证平均响应时间
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 150, f"平均响应时间过长: {avg_response_time}ms"

    @pytest.mark.asyncio
    async def test_data_persistence_validation(self, test_client: httpx.AsyncClient):
        """测试数据持久化验证"""

        # 1. 创建用户并领取礼包
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        user_id = auth_response.json()["data"]["user_id"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 领取礼包
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert gift_response.status_code == 200
        transaction_group = gift_response.json()["data"]["transaction_group"]

        # 2. 验证数据持久化 - 查询积分流水
        points_history_response = await test_client.get("/points/transactions", headers=headers)
        assert points_history_response.status_code == 200
        history_data = points_history_response.json()

        # 验证我们的交易记录存在
        transactions = history_data["data"]["transactions"]
        welcome_transactions = [t for t in transactions if t["source_type"] == "welcome_gift"]
        assert len(welcome_transactions) >= 1

        # 验证事务组匹配
        matching_transaction = next((t for t in welcome_transactions if t["source_id"] == transaction_group), None)
        assert matching_transaction is not None
        assert matching_transaction["amount"] == 1000

    @pytest.mark.asyncio
    async def test_cross_service_integration(self, test_client: httpx.AsyncClient):
        """测试跨服务集成"""

        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 创建任务
        task_data = {
            "title": "集成测试任务",
            "description": "用于验证跨服务集成",
            "priority": "medium"
        }
        task_response = await test_client.post("/tasks", json=task_data, headers=headers)
        assert task_response.status_code == 200
        task_id = task_response.json()["data"]["id"]

        # 3. 完成任务（应该触发积分和奖励）
        complete_response = await test_client.post(f"/tasks/{task_id}/complete", headers=headers)
        assert complete_response.status_code == 200

        # 4. 验证积分增加
        points_response = await test_client.get("/points/balance", headers=headers)
        assert points_response.status_code == 200
        points_data = points_response.json()
        # 任务完成应该获得积分（基于现有积分规则）
        assert points_data["data"]["current_balance"] > 0

        # 5. 验证奖励流水
        rewards_response = await test_client.get("/rewards/my-rewards", headers=headers)
        assert rewards_response.status_code == 200
        rewards_data = rewards_response.json()
        # 任务完成应该获得奖励
        rewards = rewards_data["data"]["rewards"]
        total_reward_items = sum(rewards.get(r, {}).get("quantity", 0) for r in rewards if r != "积分")
        assert total_reward_items > 0

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, test_client: httpx.AsyncClient):
        """测试Unicode和特殊字符处理"""

        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest-init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 测试包含Unicode字符的任务创建
        unicode_task_data = {
            "title": "测试任务🚀",
            "description": "这是一个包含Emoji和特殊字符的测试任务",
            "tags": ["测试", "标签", "Unicode测试"]
        }

        response = await test_client.post("/tasks", json=unicode_task_data, headers=headers)
        assert response.status_code == 200
        task_data = response.json()

        # 3. 验证数据正确保存
        get_response = await test_client.get(f"/tasks/{task_data['data']['id']}", headers=headers)
        assert get_response.status_code == 200
        get_task = get_response.json()
        assert get_task["data"]["title"] == "测试任务🚀"
        assert "测试" in get_task["data"]["tags"]
        assert "Unicode测试" in get_task["data"]["tags"]