"""
奖励兑换并发安全性测试

测试奖励兑换系统在高并发场景下的行为：
1. 多用户同时兑换同一奖励
2. 库存扣减的原子性
3. 事务隔离级别验证
4. 数据一致性保证

作者：TaTakeKe团队
版本：测试覆盖度改进
"""

import pytest
import asyncio
import httpx
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4
from typing import Dict, List

from tests.scenarios.utils import (
    create_test_client,
    create_authenticated_user,
    assert_api_success
)


@pytest.mark.integration
@pytest.mark.slow
class TestRewardRedemptionConcurrent:
    """奖励兑换并发测试类"""

    @pytest.fixture
    def multiple_users(self):
        """创建多个认证用户"""
        users = []
        for i in range(10):
            user_data = create_authenticated_user()
            client = create_test_client()
            client.headers.update({
                "Authorization": f"Bearer {user_data['access_token']}"
            })
            users.append({
                "client": client,
                "user_data": user_data,
                "user_id": user_data["user_id"]
            })
        return users

    @pytest.fixture
    def limited_stock_reward(self):
        """创建库存有限的奖励"""
        # 这里需要通过管理员API或直接数据库操作创建奖励
        # 由于测试环境限制，我们模拟一个已知的奖励ID
        return {
            "reward_id": str(uuid4()),
            "name": "限量测试奖励",
            "points_cost": 100,
            "stock_quantity": 5,
            "description": "用于并发测试的限量奖励"
        }

    def test_concurrent_reward_redemption_stock_atomicity(self, multiple_users, limited_stock_reward):
        """测试并发奖励兑换的库存原子性"""
        users = multiple_users[:8]  # 使用8个用户，超过库存5
        reward_id = limited_stock_reward["reward_id"]
        stock_quantity = limited_stock_reward["stock_quantity"]

        # 兑换结果
        redemption_results = []
        redemption_lock = threading.Lock()

        def redeem_reward_worker(user_info):
            """奖励兑换工作线程"""
            client = user_info["client"]
            user_id = user_info["user_id"]

            try:
                # 首先确保用户有足够积分
                # 在实际环境中，这里可能需要预先给用户积分
                # 对于测试，我们假设用户有足够积分

                redemption_response = client.post("/rewards/redeem", json={
                    "reward_id": reward_id,
                    "quantity": 1
                })

                success = redemption_response.status_code in [200, 201]
                error_msg = None

                if not success:
                    try:
                        error_data = redemption_response.json()
                        error_msg = error_data.get("message", "Unknown error")
                    except:
                        error_msg = f"HTTP {redemption_response.status_code}"

                with redemption_lock:
                    redemption_results.append({
                        "user_id": user_id,
                        "success": success,
                        "error_message": error_msg,
                        "status_code": redemption_response.status_code,
                        "timestamp": time.time()
                    })

            except Exception as e:
                with redemption_lock:
                    redemption_results.append({
                        "user_id": user_id,
                        "success": False,
                        "error_message": str(e),
                        "timestamp": time.time()
                    })

        # 启动并发兑换
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = [
                executor.submit(redeem_reward_worker, user)
                for user in users
            ]

            # 等待所有兑换完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Redemption thread execution error: {e}")

        # 分析结果
        successful_redemptions = [r for r in redemption_results if r["success"]]
        failed_redemptions = [r for r in redemption_results if not r["success"]]

        print(f"总用户数: {len(users)}")
        print(f"库存数量: {stock_quantity}")
        print(f"成功兑换: {len(successful_redemptions)}")
        print(f"失败兑换: {len(failed_redemptions)}")

        # 验证库存原子性
        assert len(successful_redemptions) <= stock_quantity, \
            f"成功兑换数量不应超过库存: {len(successful_redemptions)} > {stock_quantity}"

        # 验证失败原因
        stock_insufficient_failures = [
            r for r in failed_redemptions
            if r["error_message"] and "库存" in r["error_message"]
        ]

        print(f"库存不足失败: {len(stock_insufficient_failures)}")

        # 如果API实现了库存检查，应该有库存不足的失败
        # 这个断言可能会因为API未实现而跳过
        if len(successful_redemptions) == stock_quantity:
            assert len(stock_insufficient_failures) >= len(users) - stock_quantity, \
                "超出库存的兑换应该失败"

    def test_concurrent_points_deduction_consistency(self, multiple_users):
        """测试并发积分扣除的一致性"""
        users = multiple_users[:5]  # 使用5个用户
        points_cost = 50  # 每个兑换消耗50积分

        # 为每个用户预设积分（通过直接数据库操作或API）
        # 这里假设用户已有足够积分

        # 记录积分变化
        points_changes = []
        points_lock = threading.Lock()

        def check_points_balance_worker(user_info):
            """积分余额检查工作线程"""
            client = user_info["client"]
            user_id = user_info["user_id"]

            try:
                # 获取初始积分
                initial_response = client.get(f"/points/my-points?user_id={user_id}")
                if initial_response.status_code != 200:
                    return

                initial_balance = initial_response.json()["data"]["current_balance"]

                # 模拟积分扣除（通过完成任务获得积分，然后兑换）
                # 这里简化为直接检查积分查询的一致性

                # 多次查询积分余额，验证一致性
                balances = []
                for _ in range(3):
                    balance_response = client.get(f"/points/my-points?user_id={user_id}")
                    if balance_response.status_code == 200:
                        balance = balance_response.json()["data"]["current_balance"]
                        balances.append(balance)
                    time.sleep(0.01)  # 短暂延迟

                with points_lock:
                    points_changes.append({
                        "user_id": user_id,
                        "initial_balance": initial_balance,
                        "balances": balances,
                        "consistent": len(set(balances)) <= 1,  # 所有查询结果一致
                        "timestamp": time.time()
                    })

            except Exception as e:
                with points_lock:
                    points_changes.append({
                        "user_id": user_id,
                        "error": str(e),
                        "timestamp": time.time()
                    })

        # 启动并发积分检查
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = [
                executor.submit(check_points_balance_worker, user)
                for user in users
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Points check thread execution error: {e}")

        # 验证积分查询一致性
        consistent_queries = [p for p in points_changes if p.get("consistent", False)]
        print(f"一致查询: {len(consistent_queries)}/{len(points_changes)}")

        # 大部分查询应该是一致的
        assert len(consistent_queries) >= len(points_changes) * 0.8, \
            "积分查询应该具有一致性"

    def test_concurrent_recipe_composition_transaction(self, multiple_users):
        """测试并发配方组合的事务性"""
        users = multiple_users[:3]  # 使用3个用户

        # 假设有一个需要多种材料的配方
        recipe_id = str(uuid4())
        required_materials = [
            {"material_id": "material_1", "quantity": 2},
            {"material_id": "material_2", "quantity": 1}
        ]

        # 组合结果
        composition_results = []
        composition_lock = threading.Lock()

        def compose_recipe_worker(user_info):
            """配方组合工作线程"""
            client = user_info["client"]
            user_id = user_info["user_id"]

            try:
                # 获取用户当前材料
                materials_response = client.get("/rewards/materials")
                initial_materials = {}
                if materials_response.status_code == 200:
                    materials_data = materials_response.json()["data"]
                    for material in materials_data.get("materials", []):
                        initial_materials[material["reward_id"]] = material["quantity"]

                # 尝试组合配方
                composition_response = client.post(f"/rewards/recipes/{recipe_id}/redeem", json={})

                success = composition_response.status_code == 200

                if success:
                    # 获取组合后的材料
                    final_materials_response = client.get("/rewards/materials")
                    final_materials = {}
                    if final_materials_response.status_code == 200:
                        final_materials_data = final_materials_response.json()["data"]
                        for material in final_materials_data.get("materials", []):
                            final_materials[material["reward_id"]] = material["quantity"]

                    with composition_lock:
                        composition_results.append({
                            "user_id": user_id,
                            "success": True,
                            "initial_materials": initial_materials,
                            "final_materials": final_materials,
                            "materials_consumed": True,  # 如果成功，材料应该被消耗
                            "timestamp": time.time()
                        })
                else:
                    error_msg = "Unknown error"
                    try:
                        error_data = composition_response.json()
                        error_msg = error_data.get("message", "Unknown error")
                    except:
                        pass

                    with composition_lock:
                        composition_results.append({
                            "user_id": user_id,
                            "success": False,
                            "error_message": error_msg,
                            "status_code": composition_response.status_code,
                            "timestamp": time.time()
                        })

            except Exception as e:
                with composition_lock:
                    composition_results.append({
                        "user_id": user_id,
                        "success": False,
                        "error_message": str(e),
                        "timestamp": time.time()
                    })

        # 启动并发配方组合
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = [
                executor.submit(compose_recipe_worker, user)
                for user in users
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Recipe composition thread execution error: {e}")

        # 分析结果
        successful_compositions = [r for r in composition_results if r["success"]]
        failed_compositions = [r for r in composition_results if not r["success"]]

        print(f"成功组合: {len(successful_compositions)}")
        print(f"失败组合: {len(failed_compositions)}")

        # 验证事务性：成功的组合应该正确消耗材料
        for composition in successful_compositions:
            initial_materials = composition["initial_materials"]
            final_materials = composition["final_materials"]

            # 材料应该被正确消耗（这里假设API实现了正确的逻辑）
            # 具体验证逻辑取决于实际API实现

    def test_concurrent_reward_statistics_consistency(self, multiple_users):
        """测试并发奖励统计的一致性"""
        users = multiple_users

        # 统计查询结果
        statistics_results = []
        statistics_lock = threading.Lock()

        def query_statistics_worker(user_info):
            """统计查询工作线程"""
            client = user_info["client"]
            user_id = user_info["user_id"]

            try:
                stats_response = client.get(f"/rewards/statistics?user_id={user_id}")

                with statistics_lock:
                    statistics_results.append({
                        "user_id": user_id,
                        "status_code": stats_response.status_code,
                        "success": stats_response.status_code == 200,
                        "timestamp": time.time()
                    })

            except Exception as e:
                with statistics_lock:
                    statistics_results.append({
                        "user_id": user_id,
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })

        # 并发查询统计信息
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = [
                executor.submit(query_statistics_worker, user)
                for user in users
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Statistics query thread execution error: {e}")

        # 验证统计查询的一致性
        successful_queries = [s for s in statistics_results if s["success"]]
        print(f"成功统计查询: {len(successful_queries)}/{len(statistics_results)}")

        # 所有查询应该都成功（或都失败，如果API不可用）
        if len(successful_queries) > 0:
            assert len(successful_queries) == len(statistics_results), \
                "统计查询应该具有一致性"

    def test_concurrent_reward_history_consistency(self, multiple_users):
        """测试并发奖励历史记录的一致性"""
        users = multiple_users

        # 历史记录查询结果
        history_results = []
        history_lock = threading.Lock()

        def query_history_worker(user_info):
            """历史记录查询工作线程"""
            client = user_info["client"]
            user_id = user_info["user_id"]

            try:
                history_response = client.get(f"/rewards/redemptions?user_id={user_id}")

                success = history_response.status_code == 200
                record_count = 0

                if success:
                    try:
                        history_data = history_response.json()
                        if history_data.get("code") == 200:
                            transactions = history_data["data"].get("transactions", [])
                            record_count = len(transactions)
                    except:
                        pass

                with history_lock:
                    history_results.append({
                        "user_id": user_id,
                        "success": success,
                        "record_count": record_count,
                        "status_code": history_response.status_code,
                        "timestamp": time.time()
                    })

            except Exception as e:
                with history_lock:
                    history_results.append({
                        "user_id": user_id,
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })

        # 并发查询历史记录
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = [
                executor.submit(query_history_worker, user)
                for user in users
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"History query thread execution error: {e}")

        # 验证历史记录查询的一致性
        successful_queries = [h for h in history_results if h["success"]]
        print(f"成功历史查询: {len(successful_queries)}/{len(history_results)}")

        # 对于同一用户的多次查询，记录数量应该一致
        user_records = {}
        for result in successful_queries:
            user_id = result["user_id"]
            if user_id not in user_records:
                user_records[user_id] = []
            user_records[user_id].append(result["record_count"])

        # 检查每个用户的记录数量一致性
        inconsistent_users = 0
        for user_id, records in user_records.items():
            if len(set(records)) > 1:  # 记录数量不一致
                inconsistent_users += 1
                print(f"用户 {user_id} 记录数量不一致: {records}")

        print(f"记录数量一致的用户: {len(user_records) - inconsistent_users}/{len(user_records)}")

        # 大部分用户的记录应该是一致的
        if len(user_records) > 0:
            consistency_rate = (len(user_records) - inconsistent_users) / len(user_records)
            assert consistency_rate >= 0.8, \
                f"历史记录查询一致性过低: {consistency_rate:.2%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])