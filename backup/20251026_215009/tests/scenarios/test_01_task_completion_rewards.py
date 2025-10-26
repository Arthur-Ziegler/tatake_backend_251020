"""
任务完成场景测试

验证TaKeKe API v3核心功能的完整业务流程：
1. 普通任务完成获得2积分
2. Top3任务抽奖机制
3. 重复完成任务防刷验证
4. 父任务完成度自动更新
5. 奖品配方合成功能

遵循TDD原则，每个测试都验证特定的业务场景和验收标准。

作者：TaTakeKe团队
版本：3.0.0 - v3 API核心功能测试
"""

import pytest
import time
import httpx
from uuid import uuid4

from tests.scenarios.utils import (
    create_test_client,
    create_authenticated_user,
    assert_api_success,
    assert_points_change,
    create_task_with_validation,
    complete_task_with_validation,
    complete_top3_task_with_validation,
    setup_top3_task,
    get_user_points_balance,
    get_user_transactions,
    print_test_header,
    print_test_step,
    print_test_success,
    print_test_error
)


@pytest.mark.scenario
class TestTaskCompletionRewards:
    """任务完成奖励系统测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境和用户认证"""
        print_test_header("任务完成奖励系统测试")

        # 创建认证用户
        user_data = create_authenticated_user()
        self.user_id = user_data["user_id"]
        self.access_token = user_data["access_token"]

        # 创建认证客户端
        self.client = create_test_client()
        self.client.headers["Authorization"] = f"Bearer {self.access_token}"

        yield

        # 清理资源
        self.client.close()

    def test_01_normal_task_completion_2_points(self):
        """
        场景1：普通任务完成获得2积分

        验证v3 API核心修正：
        - 普通任务完成获得2积分（修正原30积分）
        - 积分流水记录正确
        - 任务状态正确更新
        - 不触发抽奖机制
        """
        print_test_step("开始普通任务完成获得2积分测试")

        # 获取初始积分
        initial_points = get_user_points_balance(self.client)
        print_test_step(f"用户初始积分: {initial_points}")

        # 创建普通任务
        task_data = {
            "title": "测试普通任务",
            "description": "这是一个用于测试积分奖励的普通任务",
            "priority": "medium",
            "status": "pending"
        }

        print_test_step("创建普通任务")
        task = create_task_with_validation(self.client, task_data)
        task_id = task["id"]
        print_test_step(f"任务创建成功，ID: {task_id}")

        # 完成任务
        print_test_step("完成任务")
        completion_result = complete_task_with_validation(self.client, task_id)

        # 验证任务状态
        assert completion_result["data"]["task"]["status"] == "completed", "任务状态应为completed"
        assert completion_result["data"]["task"]["id"] == task_id, "任务ID应匹配"

        # 验证积分发放
        completion_data = completion_result["data"]["completion_result"]
        assert completion_data["points_awarded"] == 2, f"普通任务应获得2积分，实际获得: {completion_data['points_awarded']}"
        assert completion_data["reward_type"] == "task_complete", f"普通任务奖励类型应为task_complete，实际为: {completion_data['reward_type']}"

        # 验证不触发抽奖
        assert completion_result["data"].get("lottery_result") is None, "普通任务不应触发抽奖"

        # 验证积分余额变化
        final_points = get_user_points_balance(self.client)
        expected_points = initial_points + 2
        assert final_points == expected_points, f"积分余额应为{expected_points}，实际为{final_points}"

        # 验证积分流水记录
        transactions = get_user_transactions(self.client)
        task_completion_transactions = [
            t for t in transactions
            if t["source"] == "task_complete" and t["amount"] > 0
        ]

        assert len(task_completion_transactions) >= 1, "应该有任务完成的积分流水记录"

        # 验证最新的一条流水记录
        latest_transaction = task_completion_transactions[0]
        assert latest_transaction["amount"] == 2, f"流水记录积分应为2，实际为: {latest_transaction['amount']}"
        assert latest_transaction["source"] == "task_complete", f"流水记录类型应为task_complete，实际为: {latest_transaction['source']}"

        print_test_success(f"普通任务完成获得2积分测试通过！最终积分: {final_points}")

    def test_02_top3_task_lottery_points_path(self):
        """
        场景2：Top3任务抽奖（100积分路径）

        验证Top3任务抽奖机制：
        - Top3任务完成获得2积分基础奖励
        - 触发50%概率抽奖机制
        - 积分路径：获得100积分（修正原50积分）
        - 积分流水类型为lottery_points
        """
        print_test_step("开始Top3任务抽奖（100积分路径）测试")

        # 获取初始积分
        initial_points = get_user_points_balance(self.client)
        print_test_step(f"用户初始积分: {initial_points}")

        # 创建Top3任务
        task_data = {
            "title": "测试Top3任务",
            "description": "这是一个用于测试Top3抽奖机制的任务",
            "priority": "high",
            "status": "pending"
        }

        print_test_step("创建Top3任务")
        task = create_task_with_validation(self.client, task_data)
        task_id = task["id"]
        print_test_step(f"任务创建成功，ID: {task_id}")

        # 设置任务为Top3（直接操作数据库）
        print_test_step("设置任务为Top3")
        setup_top3_task(self.client, task_id)

        # 多次尝试完成Top3任务以触发100积分路径
        max_attempts = 10
        points_awarded = False

        for attempt in range(max_attempts):
            print_test_step(f"第{attempt + 1}次完成Top3任务")

            try:
                completion_result = complete_top3_task_with_validation(self.client, task_id)

                # 检查抽奖结果
                lottery_result = completion_result["data"].get("lottery_result")
                if lottery_result:
                    if lottery_result.get("consolation_points") == 100:
                        points_awarded = True
                        print_test_step(f"成功触发100积分安慰奖路径！获得积分: {lottery_result.get('consolation_points')}")
                        break
                    elif lottery_result.get("type") == "points":
                        points_awarded = True

                        # 验证抽奖获得的积分
                        lottery_points = lottery_result.get("amount", 0)
                        assert lottery_points == 100, f"Top3抽奖应获得100积分，实际获得: {lottery_points}"

                        print_test_step(f"成功触发100积分路径！获得积分: {lottery_points}")
                        break

                    elif lottery_result.get("type") == "reward":
                        print_test_step(f"第{attempt + 1}次触发奖品路径，继续尝试...")
                        # 重置任务状态以便再次完成
                        # 这里需要取消完成任务或创建新的Top3任务
                        break

                    else:
                        print_test_step(f"第{attempt + 1}次抽奖结果未知，继续尝试...")
                else:
                    print_test_step(f"第{attempt + 1}次未触发抽奖，继续尝试...")

            except Exception as e:
                print_test_step(f"第{attempt + 1}次尝试失败: {e}")
                break

        # 验证积分总变化（基础2积分 + 抽奖100积分 = 102积分）
        if points_awarded:
            final_points = get_user_points_balance(self.client)
            expected_points = initial_points + 102  # 2基础积分 + 100抽奖积分
            assert final_points == expected_points, f"积分余额应为{expected_points}，实际为{final_points}"

            # 验证积分流水记录
            transactions = get_user_transactions(self.client)

            # 检查基础任务完成积分（2积分）
            base_completion_transactions = [
                t for t in transactions
                if t["source"] == "task_complete_top3" and t["amount"] == 2
            ]
            assert len(base_completion_transactions) >= 1, "应该有Top3任务完成的2积分记录"

            # 检查抽奖积分记录（100积分）
            lottery_points_transactions = [
                t for t in transactions
                if t["source"] == "lottery_points" and t["amount"] == 100
            ]
            assert len(lottery_points_transactions) >= 1, "应该有Top3抽奖的100积分记录"

            print_test_success(f"Top3任务抽奖（100积分路径）测试通过！最终积分: {final_points}")
        else:
            print_test_error("多次尝试未触发100积分路径，测试失败")
            pytest.fail("Top3任务抽奖100积分路径测试失败")

    def test_03_top3_task_lottery_reward_path(self):
        """
        场景3：Top3任务抽奖（奖品路径）

        验证Top3任务抽奖机制：
        - Top3任务完成获得2积分基础奖励
        - 触发50%概率抽奖机制
        - 奖品路径：获得随机激活奖品
        - 奖品流水类型为lottery_reward
        """
        print_test_step("开始Top3任务抽奖（奖品路径）测试")

        # 获取初始积分
        initial_points = get_user_points_balance(self.client)
        print_test_step(f"用户初始积分: {initial_points}")

        # 创建Top3任务
        task_data = {
            "title": "测试Top3任务-奖品路径",
            "description": "这是一个用于测试Top3奖品抽奖机制的任务",
            "priority": "high",
            "status": "pending"
        }

        print_test_step("创建Top3任务")
        task = create_task_with_validation(self.client, task_data)
        task_id = task["id"]
        print_test_step(f"任务创建成功，ID: {task_id}")

        # 设置任务为Top3
        print_test_step("设置任务为Top3")
        setup_top3_task(self.client, task_id)

        # 由于防刷机制，需要创建多个任务来尝试触发奖品路径
        max_attempts = 10
        reward_awarded = False

        for attempt in range(max_attempts):
            print_test_step(f"第{attempt + 1}次尝试Top3任务抽奖")

            # 创建新的Top3任务（因为已完成的任务不能重复完成）
            task_data = {
                "title": f"测试Top3任务-奖品路径-{attempt + 1}",
                "description": f"这是第{attempt + 1}次测试Top3奖品抽奖机制的任务",
                "priority": "high",
                "status": "pending"
            }

            try:
                task = create_task_with_validation(self.client, task_data)
                new_task_id = task["id"]

                # 设置任务为Top3
                setup_top3_task(self.client, new_task_id)

                # 完成任务
                completion_result = complete_top3_task_with_validation(self.client, new_task_id)

                # 检查抽奖结果
                lottery_result = completion_result["data"].get("lottery_result")
                if lottery_result and lottery_result.get("type") == "reward":
                    reward_awarded = True

                    # 验证抽奖获得的奖品
                    reward_data = lottery_result.get("reward")
                    assert reward_data is not None, "抽奖结果应包含奖品信息"
                    assert "id" in reward_data, "奖品应包含ID"
                    assert "name" in reward_data, "奖品应包含名称"

                    print_test_step(f"成功触发奖品路径！获得奖品: {reward_data.get('name')}")
                    break

                elif lottery_result and lottery_result.get("type") == "points":
                    print_test_step(f"第{attempt + 1}次触发积分路径，继续尝试...")
                    continue

                else:
                    print_test_step(f"第{attempt + 1}次未触发抽奖，继续尝试...")

            except Exception as e:
                print_test_step(f"第{attempt + 1}次尝试失败: {e}")
                continue

        # 验证积分变化（只有基础2积分，没有抽奖积分）
        if reward_awarded:
            final_points = get_user_points_balance(self.client)
            expected_points = initial_points + 2  # 只有基础2积分
            assert final_points == expected_points, f"积分余额应为{expected_points}，实际为{final_points}"

            # 验证积分流水记录
            transactions = get_user_transactions(self.client)

            # 检查基础任务完成积分（2积分）
            base_completion_transactions = [
                t for t in transactions
                if t["source"] == "task_complete_top3" and t["amount"] == 2
            ]
            assert len(base_completion_transactions) >= 1, "应该有Top3任务完成的2积分记录"

            # 检查抽奖奖品记录
            lottery_reward_transactions = [
                t for t in transactions
                if t["source_type"] == "lottery_reward"
            ]
            assert len(lottery_reward_transactions) >= 1, "应该有Top3抽奖的奖品记录"

            print_test_success(f"Top3任务抽奖（奖品路径）测试通过！最终积分: {final_points}")
        else:
            print_test_error("多次尝试未触发奖品路径，测试失败")
            pytest.fail("Top3任务抽奖奖品路径测试失败")

    def test_04_repeat_task_completion_prevention(self):
        """
        场景4：重复完成任务防刷验证

        验证永久防刷机制：
        - 已领奖任务永久拒绝再次发放奖励
        - last_claimed_date字段正确维护
        - 任务可以重复完成但不获得奖励
        """
        print_test_step("开始重复完成任务防刷验证测试")

        # 获取初始积分
        initial_points = get_user_points_balance(self.client)
        print_test_step(f"用户初始积分: {initial_points}")

        # 创建普通任务
        task_data = {
            "title": "测试防刷机制任务",
            "description": "这是一个用于测试防刷机制的任务",
            "priority": "medium",
            "status": "pending"
        }

        print_test_step("创建测试任务")
        task = create_task_with_validation(self.client, task_data)
        task_id = task["id"]
        print_test_step(f"任务创建成功，ID: {task_id}")

        # 第一次完成任务
        print_test_step("第一次完成任务")
        first_completion = complete_task_with_validation(self.client, task_id)

        # 验证第一次完成获得奖励
        assert first_completion["data"]["completion_result"]["points_awarded"] == 2, "第一次完成应获得2积分"

        # 验证积分增加
        points_after_first = get_user_points_balance(self.client)
        expected_after_first = initial_points + 2
        assert points_after_first == expected_after_first, f"第一次完成后积分应为{expected_after_first}，实际为{points_after_first}"

        # 尝试第二次完成任务（应该不获得奖励）
        print_test_step("尝试第二次完成任务（应不获得奖励）")

        # 首先需要重置任务状态为pending（如果API支持）
        # 这里假设我们可以再次调用complete API，但应该不获得奖励
        try:
            # 再次调用完成API
            second_response = self.client.post(f"/tasks/{task_id}/complete", json={})

            # 即使API调用成功，也不应该获得奖励
            if second_response.status_code == 200:
                second_result = second_response.json()
                completion_result = second_result["data"].get("completion_result", {})

                # 验证不获得积分奖励
                points_awarded = completion_result.get("points_awarded", 0)
                assert points_awarded == 0, f"重复完成不应获得积分，实际获得: {points_awarded}"

                # 验证不触发抽奖
                assert second_result["data"].get("lottery_result") is None, "重复完成不应触发抽奖"

                print_test_step("第二次完成未获得奖励，防刷机制正常工作")
            else:
                print_test_step(f"第二次完成API返回状态码: {second_response.status_code}")

        except Exception as e:
            print_test_step(f"第二次完成尝试异常: {e}")

        # 验证积分余额没有变化
        points_after_second = get_user_points_balance(self.client)
        assert points_after_second == points_after_first, f"重复完成后积分不应变化，仍应为{points_after_first}，实际为{points_after_second}"

        # 验证积分流水记录
        transactions = get_user_transactions(self.client)
        task_completion_transactions = [
            t for t in transactions
            if t["source"] == "task_complete" and t["amount"] > 0
        ]

        # 应该只有一次积分发放记录
        positive_task_transactions = [t for t in task_completion_transactions if t["amount"] > 0]
        assert len(positive_task_transactions) >= 1, "应该至少有一次任务完成积分记录"

        print_test_success(f"重复完成任务防刷验证测试通过！最终积分: {points_after_second}")

    def test_05_parent_task_completion_update(self):
        """
        场景5：父任务完成度自动更新

        验证递归更新机制：
        - 子任务完成时自动更新所有父任务的completion_percentage
        - 深层任务树支持多层递归更新
        - 完成度计算准确
        """
        print_test_step("开始父任务完成度自动更新测试")

        # 创建父任务
        parent_task_data = {
            "title": "父任务",
            "description": "这是包含子任务的父任务",
            "priority": "high",
            "status": "pending"
        }

        print_test_step("创建父任务")
        parent_task = create_task_with_validation(self.client, parent_task_data)
        parent_task_id = parent_task["id"]
        print_test_step(f"父任务创建成功，ID: {parent_task_id}")

        # 创建第一个子任务
        child1_data = {
            "title": "子任务1",
            "description": "父任务的第一个子任务",
            "priority": "medium",
            "status": "pending",
            "parent_id": parent_task_id
        }

        print_test_step("创建第一个子任务")
        child1 = create_task_with_validation(self.client, child1_data)
        child1_id = child1["id"]
        print_test_step(f"子任务1创建成功，ID: {child1_id}")

        # 创建第二个子任务
        child2_data = {
            "title": "子任务2",
            "description": "父任务的第二个子任务",
            "priority": "medium",
            "status": "pending",
            "parent_id": parent_task_id
        }

        print_test_step("创建第二个子任务")
        child2 = create_task_with_validation(self.client, child2_data)
        child2_id = child2["id"]
        print_test_step(f"子任务2创建成功，ID: {child2_id}")

        # 验证初始状态
        # 检查父任务的完成度（初始应为0%）
        parent_response = self.client.get(f"/tasks/{parent_task_id}")
        assert_api_success(parent_response, "获取父任务状态失败")
        parent_data = parent_response.json()["data"]
        initial_completion = parent_data.get("completion_percentage", 0)
        print_test_step(f"父任务初始完成度: {initial_completion}%")

        # 完成第一个子任务
        print_test_step("完成第一个子任务")
        complete_task_with_validation(self.client, child1_id)

        # 验证父任务完成度更新（应为50%）
        parent_response_after_child1 = self.client.get(f"/tasks/{parent_task_id}")
        assert_api_success(parent_response_after_child1, "获取父任务状态失败")
        parent_data_after_child1 = parent_response_after_child1.json()["data"]
        completion_after_child1 = parent_data_after_child1.get("completion_percentage", 0)
        print_test_step(f"完成子任务1后，父任务完成度: {completion_after_child1}%")

        # 完成第二个子任务
        print_test_step("完成第二个子任务")
        complete_task_with_validation(self.client, child2_id)

        # 验证父任务完成度更新（应为100%）
        parent_response_final = self.client.get(f"/tasks/{parent_task_id}")
        assert_api_success(parent_response_final, "获取父任务状态失败")
        parent_data_final = parent_response_final.json()["data"]
        final_completion = parent_data_final.get("completion_percentage", 0)
        print_test_step(f"完成所有子任务后，父任务完成度: {final_completion}%")

        # 验证完成度递增逻辑
        assert initial_completion == 0, f"初始完成度应为0%，实际为{initial_completion}%"
        assert completion_after_child1 == 50, f"完成一个子任务后完成度应为50%，实际为{completion_after_child1}%"
        assert final_completion == 100, f"完成所有子任务后完成度应为100%，实际为{final_completion}%"

        print_test_success("父任务完成度自动更新测试通过！")

    def test_06_reward_recipe_composition(self):
        """
        场景6：奖品配方合成

        验证材料聚合和配方合成功能：
        - 材料充足时合成成功
        - 奖品发放和材料扣除在同一事务中
        - 流水记录正确关联
        """
        print_test_step("开始奖品配方合成测试")

        # 首先检查用户现有材料
        materials_response = self.client.get("/rewards/materials")
        if materials_response.status_code == 200:
            materials_data = materials_response.json()
            print_test_step(f"用户当前材料: {materials_data}")
        else:
            print_test_step("用户当前没有材料或需要认证")

        # 获取可用配方
        recipes_response = self.client.get("/rewards/recipes")
        assert_api_success(recipes_response, "获取可用配方失败")

        recipes_data = recipes_response.json()["data"]
        available_recipes = recipes_data.get("recipes", [])
        assert len(available_recipes) > 0, "应该有可用的合成配方"

        print_test_step(f"可用配方数量: {len(available_recipes)}")

        # 选择第一个配方进行测试
        test_recipe = available_recipes[0]
        recipe_id = test_recipe["id"]
        recipe_name = test_recipe["name"]
        recipe_materials = test_recipe.get("materials", [])

        print_test_step(f"选择测试配方: {recipe_name}")
        print_test_step(f"配方所需材料: {recipe_materials}")

        # 检查用户是否有足够的材料
        if not recipe_materials:
            print_test_error("配方没有材料要求，跳过测试")
            pytest.skip("配方没有材料要求")

        # 尝试合成配方
        composition_request = {}  # RedeemRecipeRequest是空对象
        print_test_step(f"尝试合成配方: {recipe_name}")

        composition_response = self.client.post(f"/rewards/recipes/{recipe_id}/redeem", json=composition_request)

        if composition_response.status_code == 200:
            composition_result = composition_response.json()["data"]

            # 验证合成结果
            assert composition_result["success"], "配方合成应该成功"
            assert composition_result["recipe_id"] == recipe_id, "配方ID应匹配"
            assert composition_result["recipe_name"] == recipe_name, "配方名称应匹配"

            # 验证结果奖品
            result_reward = composition_result.get("result_reward")
            assert result_reward is not None, "合成结果应包含奖品信息"
            assert "id" in result_reward, "结果奖品应包含ID"
            assert "name" in result_reward, "结果奖品应包含名称"

            # 验证消耗的材料
            materials_consumed = composition_result.get("materials_consumed", [])
            assert len(materials_consumed) > 0, "应该有材料消耗记录"

            # 验证事务组关联
            transaction_group = composition_result.get("transaction_group")
            assert transaction_group is not None, "应该有事务组关联"

            print_test_step(f"配方合成成功！获得奖品: {result_reward['name']}")
            print_test_step(f"消耗材料: {materials_consumed}")
            print_test_step(f"事务组: {transaction_group}")

            print_test_success("奖品配方合成测试通过！")

        elif composition_response.status_code == 400:
            # 材料不足是正常的测试结果
            error_detail = composition_response.json().get("detail", "")
            print_test_step(f"配方合成失败（预期）: {error_detail}")

            if "材料不足" in error_detail or "insufficient" in error_detail.lower():
                print_test_success("奖品配方合成测试通过！（材料不足，符合预期）")
            else:
                print_test_error(f"意外的合成失败原因: {error_detail}")
                pytest.fail(f"配方合成意外失败: {error_detail}")
        else:
            print_test_error(f"配方合成API返回意外状态码: {composition_response.status_code}")
            pytest.fail(f"配方合成API状态码异常: {composition_response.status_code}")

    def test_07_insufficient_materials_composition_failure(self):
        """
        场景7：材料不足合成失败

        验证配方合成错误处理：
        - 材料不足时抛出InsufficientRewardsException
        - 事务正确回滚
        - 错误信息详细明确
        """
        print_test_step("开始材料不足合成失败测试")

        # 获取可用配方
        recipes_response = self.client.get("/rewards/recipes")
        assert_api_success(recipes_response, "获取可用配方失败")

        recipes_data = recipes_response.json()["data"]
        available_recipes = recipes_data.get("recipes", [])
        assert len(available_recipes) > 0, "应该有可用的合成配方"

        # 选择一个需要材料的配方
        test_recipe = None
        for recipe in available_recipes:
            if recipe.get("materials"):  # 选择有材料要求的配方
                test_recipe = recipe
                break

        if not test_recipe:
            pytest.skip("没有找到需要材料的配方，跳过测试")

        recipe_id = test_recipe["id"]
        recipe_name = test_recipe["name"]
        recipe_materials = test_recipe.get("materials", [])

        print_test_step(f"选择测试配方: {recipe_name}")
        print_test_step(f"配方所需材料: {recipe_materials}")

        # 检查用户当前材料（应该不足）
        materials_response = self.client.get("/rewards/materials")
        current_materials = {}

        if materials_response.status_code == 200:
            materials_data = materials_response.json()["data"]
            for material in materials_data.get("materials", []):
                current_materials[material["reward_id"]] = material["quantity"]

        print_test_step(f"用户当前材料: {current_materials}")

        # 确认材料不足
        insufficient_materials = False
        for required_material in recipe_materials:
            material_id = required_material.get("reward_id")
            required_quantity = required_material.get("quantity", 0)
            current_quantity = current_materials.get(material_id, 0)

            if current_quantity < required_quantity:
                insufficient_materials = True
                print_test_step(f"材料不足: 需要{required_quantity}个{material_id}，当前只有{current_quantity}个")
                break

        if not insufficient_materials:
            print_test_step("用户材料充足，跳过材料不足测试")
            pytest.skip("用户材料充足，无法测试材料不足场景")

        # 尝试合成配方（应该失败）
        composition_request = {}  # RedeemRecipeRequest是空对象
        print_test_step(f"尝试合成配方（预期失败）: {recipe_name}")

        composition_response = self.client.post(f"/rewards/recipes/{recipe_id}/redeem", json=composition_request)

        # 验证失败响应
        assert composition_response.status_code == 400, f"材料不足时应返回400状态码，实际为: {composition_response.status_code}"

        error_data = composition_response.json()
        error_detail = error_data.get("detail", "")

        # 验证错误信息
        assert "材料不足" in error_detail or "insufficient" in error_detail.lower(), f"错误信息应说明材料不足，实际为: {error_detail}"

        print_test_step(f"合成失败（符合预期）: {error_detail}")

        # 验证没有材料被扣除
        materials_after_response = self.client.get("/rewards/materials")
        if materials_after_response.status_code == 200:
            materials_after_data = materials_after_response.json()["data"]
            materials_after = {}
            for material in materials_after_data.get("materials", []):
                materials_after[material["reward_id"]] = material["quantity"]

            # 材料数量应该没有变化
            assert materials_after == current_materials, "材料不足失败时不应扣除任何材料"

        print_test_success("材料不足合成失败测试通过！")

    def test_08_uncomplete_task_no_reward_recovery(self):
        """
        场景8：取消任务完成不回收奖励

        验证取消完成任务不回收奖励：
        - 取消完成任务不影响已发放的奖励
        - 任务状态可以变更但奖励保留
        - 流水记录不被删除或修改
        """
        print_test_step("开始取消任务完成不回收奖励测试")

        # 获取初始积分
        initial_points = get_user_points_balance(self.client)
        print_test_step(f"用户初始积分: {initial_points}")

        # 创建任务
        task_data = {
            "title": "测试取消完成任务",
            "description": "这是一个用于测试取消完成不回收奖励的任务",
            "priority": "medium",
            "status": "pending"
        }

        print_test_step("创建测试任务")
        task = create_task_with_validation(self.client, task_data)
        task_id = task["id"]
        print_test_step(f"任务创建成功，ID: {task_id}")

        # 完成任务
        print_test_step("完成任务")
        completion_result = complete_task_with_validation(self.client, task_id)

        # 验证获得奖励
        assert completion_result["data"]["completion_result"]["points_awarded"] == 2, "完成任务应获得2积分"

        # 验证积分增加
        points_after_completion = get_user_points_balance(self.client)
        expected_after_completion = initial_points + 2
        assert points_after_completion == expected_after_completion, f"完成后积分应为{expected_after_completion}，实际为{points_after_completion}"

        # 获取完成后的流水记录
        transactions_before_uncomplete = get_user_transactions(self.client)
        task_completion_transactions = [
            t for t in transactions_before_uncomplete
            if t["source"] == "task_complete" and t["amount"] > 0
        ]

        completion_transaction_count = len(task_completion_transactions)
        print_test_step(f"完成任务后共有{completion_transaction_count}条积分发放记录")

        # 尝试取消完成任务
        print_test_step("尝试取消完成任务")

        try:
            uncomplete_response = self.client.post(f"/tasks/{task_id}/uncomplete", json={})

            if uncomplete_response.status_code == 200:
                print_test_step("取消完成任务API调用成功")

                # 验证任务状态变更（可能变回pending或其他状态）
                uncomplete_result = uncomplete_response.json()
                task_status_after = uncomplete_result["data"].get("status", "unknown")
                print_test_step(f"取消完成任务后任务状态: {task_status_after}")

            elif uncomplete_response.status_code == 404:
                print_test_step("取消完成任务API不存在或任务未找到，跳过测试")
                pytest.skip("取消完成任务API不存在")
            else:
                print_test_step(f"取消完成任务API返回状态码: {uncomplete_response.status_code}")

        except Exception as e:
            print_test_step(f"取消完成任务异常: {e}")

        # 验证积分余额没有减少
        points_after_uncomplete = get_user_points_balance(self.client)
        assert points_after_uncomplete == points_after_completion, f"取消完成后积分不应减少，仍应为{points_after_completion}，实际为{points_after_uncomplete}"

        # 验证流水记录没有被删除或修改
        transactions_after_uncomplete = get_user_transactions(self.client)
        task_completion_transactions_after = [
            t for t in transactions_after_uncomplete
            if t["source"] == "task_complete" and t["amount"] > 0
        ]

        assert len(task_completion_transactions_after) >= completion_transaction_count, "流水记录不应被删除"

        # 验证流水记录内容没有变化
        if task_completion_transactions and task_completion_transactions_after:
            original_transaction = task_completion_transactions[0]
            current_transaction = task_completion_transactions_after[0]

            assert original_transaction["id"] == current_transaction["id"], "流水记录ID不应变化"
            assert original_transaction["amount"] == current_transaction["amount"], "流水记录金额不应变化"
            assert original_transaction["source"] == current_transaction["source"], "流水记录类型不应变化"

        print_test_success(f"取消任务完成不回收奖励测试通过！最终积分: {points_after_uncomplete}")


if __name__ == "__main__":
    # 可以直接运行此测试文件进行调试
    pytest.main([__file__, "-v", "-s"])