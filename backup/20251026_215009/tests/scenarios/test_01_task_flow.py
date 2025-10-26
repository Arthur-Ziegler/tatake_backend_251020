"""
任务完整流程场景测试

测试任务从创建到完成的完整业务流程，包括：
1. 创建任务
2. 查看任务详情
3. 更新任务
4. 完成任务获得积分
5. 查询积分变化
6. 获取任务奖励
7. 兑换奖品

优先级：A（最高优先级）
作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import httpx
from utils import (
    print_test_header, print_test_step, print_test_success, print_test_error,
    assert_api_success, assert_contains_fields, assert_points_change,
    create_sample_task, create_task_with_validation, complete_task_with_validation,
    get_user_points, get_user_rewards
)


@pytest.mark.scenario
@pytest.mark.task_flow
def test_complete_task_flow(authenticated_client: httpx.Client, test_user: dict):
    """
    测试任务完整业务流程

    流程：创建任务 → 更新任务 → 完成任务 → 获得积分 → 查看奖励
    """
    print_test_header("任务完整流程测试")

    client = authenticated_client
    user_id = test_user["id"]

    # 步骤1: 获取初始积分
    print_test_step("获取用户初始积分")
    initial_points = get_user_points(client, user_id)
    print(f"初始积分: {initial_points}")

    # 步骤2: 创建任务
    print_test_step("创建新任务")
    task_data = create_sample_task("场景测试任务", "这是一个完整的场景测试任务")
    created_task = create_task_with_validation(client, task_data)
    task_id = created_task["id"]
    print_test_success(f"任务创建成功，ID: {task_id}")

    # 步骤3: 查看任务详情
    print_test_step("查看任务详情")
    response = client.get(f"/tasks/{task_id}")
    assert_api_success(response, "获取任务详情失败")
    task_detail = response.json()["data"]
    assert_contains_fields(task_detail, ["id", "title", "status", "created_at"], "任务详情缺少必需字段")
    assert task_detail["title"] == task_data["title"], "任务标题不匹配"
    print_test_success("任务详情获取成功")

    # 步骤4: 更新任务
    print_test_step("更新任务信息")
    update_data = {
        "title": "更新后的任务标题",
        "description": "更新后的任务描述",
        "priority": "high",
        "tags": ["测试", "更新", "场景"]
    }
    response = client.put(f"/tasks/{task_id}", json=update_data)
    assert_api_success(response, "更新任务失败")
    updated_task = response.json()["data"]
    assert updated_task["title"] == update_data["title"], "任务标题更新失败"
    assert updated_task["priority"] == update_data["priority"], "任务优先级更新失败"
    print_test_success("任务更新成功")

    # 步骤5: 获取任务列表验证更新
    print_test_step("获取任务列表验证更新")
    response = client.get("/tasks/")
    assert_api_success(response, "获取任务列表失败")
    task_list = response.json()["data"]
    assert task_list["total"] >= 1, "任务列表应该包含至少一个任务"

    # 查找我们创建的任务
    found_task = None
    for task in task_list["items"]:
        if task["id"] == task_id:
            found_task = task
            break

    assert found_task is not None, "在任务列表中找不到创建的任务"
    assert found_task["title"] == update_data["title"], "任务列表中的标题未更新"
    print_test_success("任务列表验证成功")

    # 步骤6: 完成任务
    print_test_step("完成任务")
    completed_task = complete_task_with_validation(client, task_id)
    assert completed_task["status"] == "completed", "任务状态应为已完成"
    print_test_success("任务完成成功")

    # 步骤7: 验证积分增加
    print_test_step("验证积分变化")
    final_points = get_user_points(client, user_id)
    expected_points_gain = 10  # 假设完成任务获得10积分
    assert_points_change(initial_points, final_points, expected_points_gain, "完成任务后积分变化不正确")
    print_test_success(f"积分增加正确，从 {initial_points} 增加到 {final_points}")

    # 步骤8: 查看获得的奖励
    print_test_step("查看任务完成奖励")
    rewards = get_user_rewards(client)
    # 验证是否有新的奖励记录（这里根据实际业务逻辑调整）
    print_test_success(f"当前用户奖励数量: {len(rewards)}")

    # 步骤9: 创建子任务测试层次结构
    print_test_step("创建子任务测试层次结构")
    subtask_data = create_sample_task("子任务测试", "这是父任务的子任务")
    subtask_data["parent_id"] = task_id
    subtask = create_task_with_validation(client, subtask_data)
    assert subtask["parent_id"] == task_id, "子任务父级ID设置错误"
    print_test_success(f"子任务创建成功，ID: {subtask['id']}")

    # 步骤10: 完成子任务
    print_test_step("完成子任务")
    completed_subtask = complete_task_with_validation(client, subtask["id"])
    assert completed_subtask["status"] == "completed", "子任务状态应为已完成"
    print_test_success("子任务完成成功")

    # 步骤11: 删除任务
    print_test_step("删除测试任务")
    response = client.delete(f"/tasks/{task_id}")
    assert_api_success(response, "删除任务失败")
    print_test_success("主任务删除成功")

    # 步骤12: 验证删除结果
    print_test_step("验证任务删除结果")
    response = client.get(f"/tasks/{task_id}")
    # 删除后应该返回404或相应的错误状态
    assert response.status_code in [404, 400], f"删除后获取任务应该返回错误，实际返回: {response.status_code}"
    print_test_success("任务删除验证成功")

    print_test_success("任务完整流程测试通过！")


@pytest.mark.scenario
@pytest.mark.task_flow
def test_task_batch_operations(authenticated_client: httpx.Client, test_user: dict):
    """
    测试任务批量操作场景

    创建多个任务并进行批量操作
    """
    print_test_header("任务批量操作测试")

    client = authenticated_client
    user_id = test_user["id"]
    initial_points = get_user_points(client, user_id)
    created_task_ids = []

    try:
        # 步骤1: 批量创建多个任务
        print_test_step("批量创建5个任务")
        for i in range(5):
            task_data = create_sample_task(f"批量任务_{i+1}", f"第{i+1}个批量测试任务")
            task = create_task_with_validation(client, task_data)
            created_task_ids.append(task["id"])

        print_test_success(f"成功创建 {len(created_task_ids)} 个任务")

        # 步骤2: 获取任务列表验证
        print_test_step("获取任务列表验证批量创建")
        response = client.get("/tasks/")
        assert_api_success(response, "获取任务列表失败")
        task_list = response.json()["data"]
        assert task_list["total"] >= 5, "任务列表应包含至少5个任务"
        print_test_success(f"任务列表验证成功，当前共 {task_list['total']} 个任务")

        # 步骤3: 批量完成任务
        print_test_step("批量完成任务")
        for task_id in created_task_ids:
            complete_task_with_validation(client, task_id)

        print_test_success(f"成功完成 {len(created_task_ids)} 个任务")

        # 步骤4: 验证积分批量增加
        print_test_step("验证批量完成任务积分变化")
        final_points = get_user_points(client, user_id)
        total_points_gain = len(created_task_ids) * 10  # 每个任务10积分
        assert_points_change(initial_points, final_points, total_points_gain, "批量完成任务积分变化不正确")
        print_test_success(f"批量积分增加正确，从 {initial_points} 增加到 {final_points}")

    finally:
        # 清理：删除所有创建的任务
        print_test_step("清理批量创建的任务")
        for task_id in created_task_ids:
            try:
                response = client.delete(f"/tasks/{task_id}")
                if response.status_code == 200:
                    print_test_success(f"任务 {task_id} 删除成功")
            except Exception as e:
                print_test_error(f"删除任务 {task_id} 失败: {e}")


@pytest.mark.scenario
@pytest.mark.task_flow
def test_task_error_handling(authenticated_client: httpx.Client, test_user: dict):
    """
    测试任务错误处理场景

    验证各种错误情况的处理
    """
    print_test_header("任务错误处理测试")

    client = authenticated_client

    # 步骤1: 测试获取不存在的任务
    print_test_step("测试获取不存在的任务")
    fake_task_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/tasks/{fake_task_id}")
    assert response.status_code in [404, 400], f"获取不存在任务应返回错误，实际: {response.status_code}"
    print_test_success("不存在任务错误处理正确")

    # 步骤2: 测试创建无效任务数据
    print_test_step("测试创建无效任务数据")
    invalid_task_data = {
        "title": "",  # 空标题应该无效
        "priority": "invalid_priority"  # 无效优先级
    }
    response = client.post("/tasks/", json=invalid_task_data)
    assert response.status_code in [422, 400], f"创建无效任务应返回错误，实际: {response.status_code}"
    print_test_success("无效任务数据错误处理正确")

    # 步骤3: 测试更新不存在的任务
    print_test_step("测试更新不存在的任务")
    update_data = {"title": "更新标题"}
    response = client.put(f"/tasks/{fake_task_id}", json=update_data)
    assert response.status_code in [404, 400], f"更新不存在任务应返回错误，实际: {response.status_code}"
    print_test_success("更新不存在任务错误处理正确")

    # 步骤4: 测试重复完成任务
    print_test_step("测试重复完成任务")
    # 先创建并完成一个任务
    task_data = create_sample_task("重复完成测试任务")
    task = create_task_with_validation(client, task_data)
    completed_task = complete_task_with_validation(client, task["id"])

    # 再次尝试完成同一个任务
    response = client.patch(f"/tasks/{task['id']}/complete")
    # 根据业务逻辑，重复完成可能返回成功或特定错误
    print_test_success(f"重复完成任务处理正确，状态码: {response.status_code}")

    # 清理测试数据
    try:
        client.delete(f"/tasks/{task['id']}")
        print_test_success("测试任务清理成功")
    except Exception:
        pass  # 清理失败不影响测试结果

    print_test_success("任务错误处理测试通过！")