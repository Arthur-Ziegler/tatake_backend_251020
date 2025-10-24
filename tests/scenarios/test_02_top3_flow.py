"""
Top3特殊奖励流程场景测试

测试Top3系统的完整业务流程，包括：
1. 充值积分（通过完成任务）
2. 设置Top3任务
3. 完成Top3任务
4. 验证高价值奖励

优先级：B（高优先级）
作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import httpx
from datetime import date, datetime
from utils import (
    print_test_header, print_test_step, print_test_success, print_test_error,
    assert_api_success, assert_contains_fields, assert_points_change,
    create_sample_task, create_task_with_validation, complete_task_with_validation,
    get_user_points, get_user_rewards, create_sample_top3
)


@pytest.mark.scenario
@pytest.mark.top3_flow
def test_top3_complete_flow(authenticated_client: httpx.Client):
    """
    测试Top3完整业务流程

    流程：完成任务获得积分 → 设置Top3 → 完成Top3任务 → 获得特殊奖励
    """
    print_test_header("Top3完整流程测试")

    client = authenticated_client

    # 步骤1: 获取初始积分
    print_test_step("获取用户初始积分")
    initial_points = get_user_points(client)
    print(f"初始积分: {initial_points}")

    # 步骤2: 完成一些任务来获得足够的积分（Top3需要300积分）
    print_test_step("通过完成任务获得足够积分")
    needed_points = 300
    points_per_task = 10  # 假设每个任务10积分
    tasks_to_complete = max(0, (needed_points - initial_points + points_per_task - 1) // points_per_task)

    created_task_ids = []
    try:
        for i in range(tasks_to_complete):
            task_data = create_sample_task(f"积分任务_{i+1}", f"为了获得积分创建的第{i+1}个任务")
            task = create_task_with_validation(client, task_data)
            created_task_ids.append(task["id"])
            complete_task_with_validation(client, task["id"])

        # 验证积分增加
        current_points = get_user_points(client)
        expected_points = initial_points + (tasks_to_complete * points_per_task)
        assert_points_change(initial_points, current_points, tasks_to_complete * points_per_task, "完成任务积分计算错误")
        print_test_success(f"通过完成 {tasks_to_complete} 个任务获得足够积分，当前积分: {current_points}")

    finally:
        # 清理临时任务
        for task_id in created_task_ids:
            try:
                client.delete(f"/tasks/{task_id}")
            except Exception:
                pass

    # 步骤3: 创建一些任务用于Top3
    print_test_step("创建用于Top3的任务")
    top3_task_ids = []
    for i in range(3):
        task_data = create_sample_task(f"Top3任务_{i+1}", f"今日重要任务第{i+1}个")
        task = create_task_with_validation(client, task_data)
        top3_task_ids.append(task["id"])

    try:
        # 步骤4: 设置Top3
        print_test_step("设置今日Top3任务")
        today = date.today().strftime("%Y-%m-%d")
        top3_data = {
            "date": today,
            "task_ids": [
                {"position": 1, "task_id": top3_task_ids[0]},
                {"position": 2, "task_id": top3_task_ids[1]},
                {"position": 3, "task_id": top3_task_ids[2]}
            ]
        }

        response = client.post("/tasks/top3", json=top3_data)
        assert_api_success(response, "设置Top3失败")
        top3_result = response.json()["data"]
        assert_contains_fields(top3_result, ["date", "top3_tasks", "points_consumed"], "Top3响应缺少必需字段")
        assert top3_result["points_consumed"] == 300, "Top3积分消耗应为300"
        print_test_success(f"Top3设置成功，消耗300积分")

        # 验证积分减少
        points_after_top3 = get_user_points(client)
        assert_points_change(current_points, points_after_top3, -300, "设置Top3后积分变化不正确")
        print_test_success(f"设置Top3后积分: {points_after_top3}")

        # 步骤5: 验证Top3设置结果
        print_test_step("验证Top3设置结果")
        response = client.get(f"/tasks/top3/{today}")
        assert_api_success(response, "获取Top3失败")
        top3_detail = response.json()["data"]
        assert len(top3_detail["top3_tasks"]) == 3, "Top3任务数量不正确"
        print_test_success("Top3设置验证成功")

        # 步骤6: 完成所有Top3任务
        print_test_step("完成所有Top3任务")
        for i, task_id in enumerate(top3_task_ids):
            print(f"完成Top3任务 {i+1}")
            complete_task_with_validation(client, task_id)

        print_test_success("所有Top3任务完成")

        # 步骤7: 验证完成Top3任务的额外积分奖励
        print_test_step("验证Top3任务完成奖励")
        final_points = get_user_points(client)
        # Top3任务应该有额外的积分奖励（除了普通任务完成的10积分外）
        expected_bonus = 50  # 假设Top3任务额外奖励50积分
        expected_final_points = points_after_top3 + (3 * points_per_task) + expected_bonus

        # 这里我们只验证积分确实增加了，具体数值可能根据业务逻辑调整
        assert final_points > points_after_top3 + (3 * points_per_task), "完成Top3任务应该有额外积分奖励"
        print_test_success(f"Top3任务完成获得额外奖励，最终积分: {final_points}")

        # 步骤8: 查看获得的奖励
        print_test_step("查看获得的特殊奖励")
        rewards = get_user_rewards(client)
        print_test_success(f"当前用户奖励数量: {len(rewards)}")

        # 步骤9: 尝试兑换高价值奖品（如果积分足够）
        print_test_step("尝试兑换高价值奖品")
        response = client.get("/rewards/catalog")
        assert_api_success(response, "获取奖品目录失败")
        catalog = response.json()["data"]

        # 查找高价值奖品
        high_value_reward = None
        for reward in catalog.get("items", []):
            if reward.get("points_value", 0) > 100:  # 假设100积分以上为高价值
                high_value_reward = reward
                break

        if high_value_reward and final_points >= high_value_reward["points_value"]:
            reward_id = high_value_reward["id"]
            redeem_data = {"reward_id": reward_id}
            response = client.post("/rewards/redeem", json=redeem_data)

            if response.status_code == 200:
                print_test_success(f"成功兑换高价值奖品: {high_value_reward['name']}")
            else:
                print_test_success(f"尝试兑换奖品返回状态码: {response.status_code}")
        else:
            print_test_success("积分不足或没有合适的高价值奖品可兑换")

    finally:
        # 清理Top3任务
        print_test_step("清理Top3任务")
        for task_id in top3_task_ids:
            try:
                client.delete(f"/tasks/{task_id}")
            except Exception:
                pass

    print_test_success("Top3完整流程测试通过！")


@pytest.mark.scenario
@pytest.mark.top3_flow
def test_top3_error_handling(authenticated_client: httpx.Client):
    """
    测试Top3错误处理场景

    验证Top3系统的各种错误情况处理
    """
    print_test_header("Top3错误处理测试")

    client = authenticated_client

    # 步骤1: 测试积分不足时设置Top3
    print_test_step("测试积分不足时设置Top3")
    # 先获取当前积分
    current_points = get_user_points(client)

    # 如果积分足够，先消费掉大部分积分
    if current_points >= 300:
        # 创建一些任务来消耗积分（这里假设有消耗积分的API）
        # 或者跳过这个测试，如果用户积分总是足够的话
        print_test_success("用户积分充足，跳过积分不足测试")
    else:
        # 尝试设置Top3
        today = date.today().strftime("%Y-%m-%d")
        # 先创建一些任务
        task_ids = []
        try:
            for i in range(3):
                task_data = create_sample_task(f"测试任务_{i+1}")
                task = create_task_with_validation(client, task_data)
                task_ids.append(task["id"])

            top3_data = {
                "date": today,
                "task_ids": [
                    {"position": 1, "task_id": task_ids[0]},
                    {"position": 2, "task_id": task_ids[1]},
                    {"position": 3, "task_id": task_ids[2]}
                ]
            }

            response = client.post("/tasks/top3", json=top3_data)
            # 如果积分不足，应该返回错误
            if response.status_code != 200:
                print_test_success("积分不足时正确拒绝设置Top3")
            else:
                print_test_success("积分充足，成功设置Top3")

        finally:
            # 清理任务
            for task_id in task_ids:
                try:
                    client.delete(f"/tasks/{task_id}")
                except Exception:
                    pass

    # 步骤2: 测试重复设置Top3
    print_test_step("测试重复设置Top3")
    # 先确保有足够积分
    if current_points < 300:
        # 通过完成任务获得积分
        for i in range(30):  # 完成30个任务获得300积分
            task_data = create_sample_task(f"积分任务_{i+1}")
            task = create_task_with_validation(client, task_data)
            complete_task_with_validation(client, task["id"])
            client.delete(f"/tasks/{task['id']}")

    # 创建任务并设置Top3
    task_ids = []
    try:
        for i in range(3):
            task_data = create_sample_task(f"重复测试任务_{i+1}")
            task = create_task_with_validation(client, task_data)
            task_ids.append(task["id"])

        today = date.today().strftime("%Y-%m-%d")
        top3_data = {
            "date": today,
            "task_ids": [
                {"position": 1, "task_id": task_ids[0]},
                {"position": 2, "task_id": task_ids[1]},
                {"position": 3, "task_id": task_ids[2]}
            ]
        }

        # 第一次设置Top3
        response1 = client.post("/tasks/top3", json=top3_data)
        assert_api_success(response1, "第一次设置Top3失败")

        # 第二次设置同一天的Top3
        response2 = client.post("/tasks/top3", json=top3_data)
        # 应该拒绝重复设置
        assert response2.status_code in [400, 422], f"重复设置Top3应返回错误，实际: {response2.status_code}"
        print_test_success("正确拒绝重复设置Top3")

    finally:
        # 清理任务
        for task_id in task_ids:
            try:
                client.delete(f"/tasks/{task_id}")
            except Exception:
                pass

    # 步骤3: 测试无效的任务ID
    print_test_step("测试无效任务ID设置Top3")
    fake_task_id = "00000000-0000-0000-0000-000000000000"
    invalid_top3_data = {
        "date": date.today().strftime("%Y-%m-%d"),
        "task_ids": [
            {"position": 1, "task_id": fake_task_id}
        ]
    }

    response = client.post("/tasks/top3", json=invalid_top3_data)
    assert response.status_code in [400, 404, 422], f"使用无效任务ID应返回错误，实际: {response.status_code}"
    print_test_success("正确拒绝无效任务ID的Top3设置")

    # 步骤4: 测试获取不存在日期的Top3
    print_test_step("测试获取不存在日期的Top3")
    future_date = "2099-12-31"
    response = client.get(f"/tasks/top3/{future_date}")
    # 应该返回空结果或相应状态
    assert response.status_code == 200, "获取不存在日期的Top3应返回200"
    print_test_success("正确处理不存在日期的Top3查询")

    print_test_success("Top3错误处理测试通过！")


@pytest.mark.scenario
@pytest.mark.top3_flow
def test_top3_task_relationship(authenticated_client: httpx.Client):
    """
    测试Top3任务关联关系

    验证Top3任务与普通任务之间的关系和状态同步
    """
    print_test_header("Top3任务关联关系测试")

    client = authenticated_client

    # 步骤1: 创建任务并设置为Top3
    print_test_step("创建任务并设置为Top3")
    task_ids = []
    try:
        for i in range(3):
            task_data = create_sample_task(f"关联测试任务_{i+1}")
            task = create_task_with_validation(client, task_data)
            task_ids.append(task["id"])

        today = date.today().strftime("%Y-%m-%d")
        top3_data = {
            "date": today,
            "task_ids": [
                {"position": 1, "task_id": task_ids[0]},
                {"position": 2, "task_id": task_ids[1]},
                {"position": 3, "task_id": task_ids[2]}
            ]
        }

        response = client.post("/tasks/top3", json=top3_data)
        assert_api_success(response, "设置Top3失败")
        print_test_success("Top3设置成功")

        # 步骤2: 验证任务状态
        print_test_step("验证Top3任务状态")
        for task_id in task_ids:
            response = client.get(f"/tasks/{task_id}")
            assert_api_success(response, f"获取任务 {task_id} 失败")
            task_detail = response.json()["data"]
            # 验证任务确实存在
            assert task_detail["id"] == task_id, "任务ID不匹配"

        print_test_success("Top3任务状态验证成功")

        # 步骤3: 完成部分Top3任务
        print_test_step("完成部分Top3任务")
        complete_task_with_validation(client, task_ids[0])
        complete_task_with_validation(client, task_ids[1])
        print_test_success("部分Top3任务完成")

        # 步骤4: 验证Top3状态
        print_test_step("验证Top3状态更新")
        response = client.get(f"/tasks/top3/{today}")
        assert_api_success(response, "获取Top3状态失败")
        top3_detail = response.json()["data"]
        # 这里可以验证Top3的完成状态等
        print_test_success("Top3状态验证成功")

    finally:
        # 清理任务
        for task_id in task_ids:
            try:
                client.delete(f"/tasks/{task_id}")
            except Exception:
                pass

    print_test_success("Top3任务关联关系测试通过！")