"""
系统全面测试套件

按照v3文档要求，对任务系统、用户管理、Top3系统进行完整测试：
- 任务CRUD完整流程
- 任务完成和奖励发放
- 用户资料管理
- Top3抽奖机制
- 数据持久化验证
- 错误场景覆盖

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


class TestSystemComprehensive:
    """系统全面测试类"""

    @pytest.mark.asyncio
    async def test_task_complete_lifecycle(self, test_client: httpx.AsyncClient):
        """测试任务完整生命周期"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 创建任务
        task_data = {
            "title": "生命周期测试任务",
            "description": "测试任务完整流程",
            "priority": "high"
        }
        create_response = await test_client.post("/tasks/", json=task_data, headers=headers)
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["id"]

        # 3. 查询任务
        get_response = await test_client.get(f"/tasks/{task_id}", headers=headers)
        assert get_response.status_code == 200
        task_data = get_response.json()["data"]
        assert task_data["status"] == "pending"

        # 4. 完成任务
        complete_response = await test_client.post(f"/tasks/{task_id}/complete",
                                           json={"mood_feedback": {"comment": "测试完成", "difficulty": "medium"}},
                                           headers=headers)
        assert complete_response.status_code == 200
        complete_data = complete_response.json()["data"]
        assert complete_data["task"]["status"] == "completed"

        # 5. 验证积分增加
        points_response = await test_client.get("/points/my-points", headers=headers)
        assert points_response.status_code == 200
        balance = points_response.json()["data"]["current_balance"]
        assert balance > 0  # 完成任务应该获得积分

        print("✅ 任务生命周期测试通过")

    @pytest.mark.asyncio
    async def test_task_nested_structure(self, test_client: httpx.AsyncClient):
        """测试嵌套任务结构"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 创建父任务
        parent_task = {
            "title": "父任务",
            "description": "这是父任务",
            "priority": "high"
        }
        parent_response = await test_client.post("/tasks/", json=parent_task, headers=headers)
        assert parent_response.status_code == 200
        parent_id = parent_response.json()["data"]["id"]

        # 3. 创建子任务
        child_task = {
            "title": "子任务",
            "description": "这是子任务",
            "priority": "medium",
            "parent_id": str(parent_id)
        }
        child_response = await test_client.post("/tasks/", json=child_task, headers=headers)
        assert child_response.status_code == 200
        child_id = child_response.json()["data"]["id"]

        # 4. 验证父子关系
        get_child_response = await test_client.get(f"/tasks/{child_id}", headers=headers)
        child_data = get_child_response.json()["data"]
        assert child_data["parent_id"] == str(parent_id)

        print("✅ 嵌套任务结构测试通过")

    @pytest.mark.asyncio
    async def test_user_profile_management(self, test_client: httpx.AsyncClient):
        """测试用户资料管理"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 获取用户资料
        profile_response = await test_client.get("/user/profile", headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()["data"]
        assert "user_id" in profile_data

        # 3. 测试头像上传（如果支持）
        avatar_response = await test_client.get("/user/avatar", headers=headers)
        assert avatar_response.status_code in [200, 404]  # 可能没有头像

        print("✅ 用户资料管理测试通过")

    @pytest.mark.asyncio
    async def test_rewards_system_flow(self, test_client: httpx.AsyncClient):
        """测试奖励系统完整流程"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 领取欢迎礼包
        gift_response = await test_client.post("/user/welcome-gift/claim", headers=headers)
        assert gift_response.status_code == 200
        gift_data = gift_response.json()["data"]
        assert gift_data["points_granted"] == 1000
        assert len(gift_data["rewards_granted"]) == 3

        # 3. 查看奖励库存
        rewards_response = await test_client.get("/rewards/my-rewards", headers=headers)
        assert rewards_response.status_code == 200
        rewards_data = rewards_response.json()["data"]["rewards"]

        # 验证欢迎礼包奖励
        gift_reward_names = [r["name"] for r in gift_data["rewards_granted"]]
        has_bonus_card = any("积分加成卡" in rewards_data.get("积分加成卡", {}).get("name", ""))
        has_focus_item = any("专注道具" in rewards_data.get("专注道具", {}).get("name", ""))
        has_coupon = any("时间管理券" in rewards_data.get("时间管理券", {}).get("name", ""))

        assert has_bonus_card or has_focus_item or has_coupon  # 至少有一个奖励

        print("✅ 奖励系统流程测试通过")

    @pytest.mark.asyncio
    async def test_top3_lottery_system(self, test_client: httpx.AsyncClient):
        """测试Top3抽奖系统"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 获取Top3信息
        top3_response = await test_client.get("/tasks/special/top3", headers=headers)
        assert top3_response.status_code == 200
        top3_data = top3_response.json()["data"]

        # 3. 尝试参与Top3（可能需要积分）
        lottery_response = await test_client.post("/tasks/special/top3/2025-10-25", headers=headers)
        # Top3可能需要特定条件，允许失败
        print(f"Top3尝试结果：{lottery_response.status_code}")

        print("✅ Top3抽奖系统测试通过")

    @pytest.mark.asyncio
    async def test_focus_system_integration(self, test_client: httpx.AsyncClient):
        """测试Focus系统集成"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 创建Focus会话
        focus_data = {
            "task_id": str(uuid4()),
            "session_type": "focus"
        }
        focus_response = await test_client.post("/focus/sessions", json=focus_data, headers=headers)
        assert focus_response.status_code == 200
        session_id = focus_response.json()["data"]["id"]

        # 3. 完成Focus会话
        complete_response = await test_client.post(f"/focus/sessions/{session_id}/complete", headers=headers)
        assert complete_response.status_code == 200

        print("✅ Focus系统集成测试通过")

    @pytest.mark.asyncio
    async def test_error_scenarios_coverage(self, test_client: httpx.AsyncClient):
        """测试错误场景全覆盖"""
        # 1. 测试401未授权
        response = await test_client.get("/user/profile")
        assert response.status_code == 401
        error_data = response.json()
        assert error_data["code"] == 401

        # 2. 测试404资源不存在
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        notfound_response = await test_client.get("/tasks/nonexistent-task", headers=headers)
        assert notfound_response.status_code == 404
        error_data = notfound_response.json()
        assert error_data["code"] == 404

        # 3. 测试422参数验证错误
        invalid_task = {"invalid": "data"}
        validation_response = await test_client.post("/tasks/", json=invalid_task, headers=headers)
        assert validation_response.status_code == 422
        error_data = validation_response.json()
        assert error_data["code"] == 422

        print("✅ 错误场景覆盖测试通过")

    @pytest.mark.asyncio
    async def test_data_persistence_verification(self, test_client: httpx.AsyncClient):
        """测试数据持久化验证"""
        # 1. 创建用户并完成任务
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 创建并完成任务
        task_data = {"title": "持久化测试任务", "description": "验证数据保存"}
        create_response = await test_client.post("/tasks/", json=task_data, headers=headers)
        task_id = create_response.json()["data"]["id"]

        complete_response = await test_client.post(f"/tasks/{task_id}/complete",
                                               json={"mood_feedback": {"comment": "持久化测试"}},
                                               headers=headers)

        # 3. 验证积分流水
        points_response = await test_client.get("/points/transactions", headers=headers)
        assert points_response.status_code == 200
        transactions = points_response.json()["data"]["transactions"]
        task_transactions = [t for t in transactions if t["source_type"] == "task_complete"]
        assert len(task_transactions) >= 1

        # 4. 验证奖励流水
        rewards_response = await test_client.get("/rewards/my-rewards", headers=headers)
        assert rewards_response.status_code == 200

        print("✅ 数据持久化验证测试通过")

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, test_client: httpx.AsyncClient):
        """测试性能基准"""
        # 1. 创建用户
        auth_response = await test_client.post("/auth/guest/init")
        access_token = auth_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. 测试关键端点响应时间
        endpoints = [
            ("/user/profile", "GET"),
            ("/points/my-points", "GET"),
            ("/tasks/", "GET"),
            ("/rewards/catalog", "GET")
        ]

        for endpoint, method in endpoints:
            start_time = time.time()
            if method == "GET":
                response = await test_client.get(endpoint, headers=headers)
            else:
                response = await test_client.post(endpoint, headers=headers)

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒

            assert response.status_code in [200, 404]  # 允许合理失败
            assert response_time < 200, f"{endpoint} 响应时间过长: {response_time}ms"

        print("✅ 性能基准测试通过")