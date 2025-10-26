"""
跨模块组合流程场景测试

测试跨模块的业务流程，包括：
1. 任务+Focus组合流程
2. Focus+奖励组合流程
3. 任务树完成度验证
4. 综合业务场景

优先级：D（低优先级，但重要）
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
    get_user_points, get_user_rewards, create_sample_top3,
    start_focus_session_with_validation
)


@pytest.mark.scenario
@pytest.mark.combined_flow
def test_task_focus_combined_flow(authenticated_client: httpx.Client):
    """
    测试任务+Focus组合流程

    流程：创建任务 → Focus专注 → 完成任务 → 验证双重奖励
    """
    print_test_header("任务+Focus组合流程测试")

    client = authenticated_client

    # 步骤1: 获取初始状态
    print_test_step("获取用户初始状态")
    initial_points = get_user_points(client)
    initial_rewards_count = len(get_user_rewards(client))
    print(f"初始积分: {initial_points}, 初始奖励数量: {initial_rewards_count}")

    # 步骤2: 创建一个复杂任务
    print_test_step("创建复杂任务")
    task_data = create_sample_task("专注学习任务", "需要专注完成的学习任务", priority="high")
    task = create_task_with_validation(client, task_data)
    task_id = task["id"]
    print_test_success(f"任务创建成功，ID: {task_id}")

    # 步骤3: 开始Focus会话专注这个任务
    print_test_step("开始Focus会话专注任务")
    focus_data = {
        "duration_minutes": 30,
        "task_type": "study",
        # 如果API支持，可以关联任务ID
        # "task_id": task_id
    }

    response = client.post("/focus/sessions", json=focus_data)
    if response.status_code == 200:
        session = response.json()["data"]
        session_id = session["id"]
        print_test_success(f"Focus会话开始成功，ID: {session_id}")

        # 步骤4: 完成Focus会话
        print_test_step("完成Focus会话")
        response = client.post(f"/focus/sessions/{session_id}/complete")
        assert_api_success(response, "完成Focus会话失败")
        completed_session = response.json()["data"]
        print_test_success("Focus会话完成成功")

        # 验证Focus完成获得的积分
        points_after_focus = get_user_points(client)
        focus_points_gain = points_after_focus - initial_points
        print_test_success(f"Focus完成获得积分: {focus_points_gain}")

        # 步骤5: 完成关联的任务
        print_test_step("完成关联任务")
        completed_task = complete_task_with_validation(client, task_id)
        print_test_success("任务完成成功")

        # 步骤6: 验证任务完成获得的额外积分
        final_points = get_user_points(client)
        task_points_gain = final_points - points_after_focus
        print_test_success(f"任务完成获得积分: {task_points_gain}")

        # 步骤7: 验证总积分增长
        total_points_gain = final_points - initial_points
        expected_min_gain = 15 + 10  # Focus(15) + 任务(10)
        assert total_points_gain >= expected_min_gain, f"组合流程积分增长不足，期望至少{expected_min_gain}，实际{total_points_gain}"
        print_test_success(f"组合流程总积分增长: {total_points_gain}")

    else:
        print_test_success("Focus会话创建失败，跳过组合测试")
        # 仍然完成任务
        complete_task_with_validation(client, task_id)

    # 步骤8: 验证奖励记录
    print_test_step("验证奖励记录")
    final_rewards = get_user_rewards(client)
    rewards_gain = len(final_rewards) - initial_rewards_count
    print_test_success(f"获得新奖励数量: {rewards_gain}")

    # 清理
    try:
        client.delete(f"/tasks/{task_id}")
    except Exception:
        pass

    print_test_success("任务+Focus组合流程测试通过！")


@pytest.mark.scenario
@pytest.mark.combined_flow
def test_top3_focus_task_tree_flow(authenticated_client: httpx.Client):
    """
    测试Top3 + Focus + 任务树组合流程

    流程：积累积分 → 设置Top3 → Focus专注 → 完成Top3任务树 → 验证综合奖励
    """
    print_test_header("Top3 + Focus + 任务树组合流程测试")

    client = authenticated_client

    # 步骤1: 积累足够积分
    print_test_step("积累足够的积分用于Top3")
    initial_points = get_user_points(client)
    needed_points = 300
    current_points = initial_points

    if current_points < needed_points:
        # 通过完成任务获得积分
        tasks_to_complete = (needed_points - current_points + 9) // 10  # 每个任务10积分
        print(f"需要完成 {tasks_to_complete} 个任务来获得足够积分")

        temp_task_ids = []
        try:
            for i in range(tasks_to_complete):
                task_data = create_sample_task(f"积分任务_{i+1}")
                task = create_task_with_validation(client, task_data)
                temp_task_ids.append(task["id"])
                complete_task_with_validation(client, task["id"])

            current_points = get_user_points(client)
            print_test_success(f"完成 {tasks_to_complete} 个任务，当前积分: {current_points}")

        finally:
            # 清理临时任务
            for task_id in temp_task_ids:
                try:
                    client.delete(f"/tasks/{task_id}")
                except Exception:
                    pass

    # 步骤2: 创建任务层次结构
    print_test_step("创建任务层次结构")
    main_task_ids = []
    subtask_ids = []

    try:
        # 创建3个主要任务
        for i in range(3):
            main_task_data = create_sample_task(f"主任务_{i+1}", f"Top3主任务第{i+1}个")
            main_task = create_task_with_validation(client, main_task_data)
            main_task_ids.append(main_task["id"])

            # 每个主任务创建2个子任务
            for j in range(2):
                subtask_data = create_sample_task(
                    f"子任务_{i+1}-{j+1}",
                    f"主任务{i+1}的子任务{j+1}",
                    priority="medium"
                )
                subtask_data["parent_id"] = main_task["id"]
                subtask = create_task_with_validation(client, subtask_data)
                subtask_ids.append(subtask["id"])

        print_test_success(f"创建了 {len(main_task_ids)} 个主任务和 {len(subtask_ids)} 个子任务")

        # 步骤3: 设置Top3
        print_test_step("设置今日Top3")
        today = date.today().strftime("%Y-%m-%d")
        top3_data = {
            "date": today,
            "task_ids": [
                {"position": 1, "task_id": main_task_ids[0]},
                {"position": 2, "task_id": main_task_ids[1]},
                {"position": 3, "task_id": main_task_ids[2]}
            ]
        }

        response = client.post("/tasks/special/top3", json=top3_data)
        assert_api_success(response, "设置Top3失败")
        top3_result = response.json()["data"]
        print_test_success("Top3设置成功")

        points_after_top3 = get_user_points(client)

        # 步骤4: 为每个Top3任务进行Focus专注
        print_test_step("为Top3任务进行Focus专注")
        focus_session_ids = []

        for i, task_id in enumerate(main_task_ids):
            print(f"为任务 {i+1} 进行Focus专注")
            focus_data = {
                "duration_minutes": 25,
                "task_type": "work"
            }

            response = client.post("/focus/sessions", json=focus_data)
            if response.status_code == 200:
                session = response.json()["data"]
                focus_session_ids.append(session["id"])

                # 立即完成Focus会话
                response = client.post(f"/focus/sessions/{session['id']}/complete")
                assert_api_success(response, f"完成Focus会话 {session['id']} 失败")
                print_test_success(f"任务 {i+1} 的Focus专注完成")

        points_after_focus = get_user_points(client)
        print_test_success(f"所有Focus专注完成，当前积分: {points_after_focus}")

        # 步骤5: 完成所有子任务
        print_test_step("完成所有子任务")
        for subtask_id in subtask_ids:
            complete_task_with_validation(client, subtask_id)

        points_after_subtasks = get_user_points(client)
        print_test_success(f"所有子任务完成，当前积分: {points_after_subtasks}")

        # 步骤6: 完成所有Top3主任务
        print_test_step("完成所有Top3主任务")
        for main_task_id in main_task_ids:
            complete_task_with_validation(client, main_task_id)

        final_points = get_user_points(client)
        print_test_success(f"所有Top3主任务完成，最终积分: {final_points}")

        # 步骤7: 验证任务树完成度
        print_test_step("验证任务树完成度")
        response = client.get("/tasks/")
        assert_api_success(response, "获取任务列表失败")
        task_list = response.json()["data"]

        # 验证所有任务都已完成
        completed_tasks = [t for t in task_list["items"] if t["id"] in main_task_ids + subtask_ids]
        assert len(completed_tasks) == len(main_task_ids) + len(subtask_ids), "不是所有任务都已完成"
        assert all(t["status"] == "completed" for t in completed_tasks), "有任务状态不是completed"
        print_test_success("任务树完成度验证成功")

        # 步骤8: 验证综合奖励
        print_test_step("验证综合奖励")
        final_rewards = get_user_rewards(client)
        print_test_success(f"最终获得奖励数量: {len(final_rewards)}")

        # 验证积分大幅增长
        total_points_change = final_points - initial_points
        print_test_success(f"整个流程积分变化: {total_points_change}")

    finally:
        # 清理所有任务
        print_test_step("清理所有任务")
        all_task_ids = main_task_ids + subtask_ids
        for task_id in all_task_ids:
            try:
                client.delete(f"/tasks/{task_id}")
            except Exception:
                pass

    print_test_success("Top3 + Focus + 任务树组合流程测试通过！")


@pytest.mark.scenario
@pytest.mark.combined_flow
def test_cross_module_error_scenarios(authenticated_client: httpx.Client):
    """
    测试跨模块错误场景

    验证跨模块操作时的错误处理和一致性
    """
    print_test_header("跨模块错误场景测试")

    client = authenticated_client

    # 步骤1: 测试Top3任务与Focus会话冲突
    print_test_step("测试Top3任务与Focus会话冲突处理")

    # 创建任务并设置为Top3
    task_data = create_sample_task("冲突测试任务")
    task = create_task_with_validation(client, task_data)
    task_id = task["id"]

    try:
        # 尝试设置Top3（积分可能不足）
        today = date.today().strftime("%Y-%m-%d")
        top3_data = {
            "date": today,
            "task_ids": [
                {"position": 1, "task_id": task_id}
            ]
        }

        response = client.post("/tasks/special/top3", json=top3_data)
        if response.status_code == 200:
            # Top3设置成功，测试删除正在Top3中的任务
            print_test_step("测试删除正在Top3中的任务")
            response = client.delete(f"/tasks/{task_id}")
            # 应该允许删除或返回相应错误
            print_test_success(f"删除Top3任务处理，状态码: {response.status_code}")
        else:
            print_test_success("积分不足，跳过冲突测试")

    finally:
        # 清理任务
        try:
            client.delete(f"/tasks/{task_id}")
        except Exception:
            pass

    # 步骤2: 测试Focus会话与任务状态一致性
    print_test_step("测试Focus会话与任务状态一致性")

    # 创建任务和Focus会话
    task_data = create_sample_task("一致性测试任务")
    task = create_task_with_validation(client, task_data)
    task_id = task["id"]

    try:
        # 开始Focus会话
        session = start_focus_session_with_validation(client, duration=25)
        session_id = session["id"]

        # 删除关联的任务
        response = client.delete(f"/tasks/{task_id}")
        if response.status_code == 200:
            # 验证Focus会话是否仍然有效
            response = client.post(f"/focus/sessions/{session_id}/complete")
            print_test_success(f"任务删除后Focus会话处理，状态码: {response.status_code}")
        else:
            print_test_success("任务删除失败，跳过一致性测试")

        # 清理Focus会话
        try:
            client.post(f"/focus/sessions/{session_id}/complete")
        except Exception:
            pass

    finally:
        # 清理任务
        try:
            client.delete(f"/tasks/{task_id}")
        except Exception:
            pass

    # 步骤3: 测试并发操作冲突
    print_test_step("测试并发操作冲突")

    # 创建任务
    task_data = create_sample_task("并发测试任务")
    task = create_task_with_validation(client, task_data)
    task_id = task["id"]

    try:
        # 快速连续操作
        # 1. 开始Focus会话
        session = start_focus_session_with_validation(client, duration=25)
        session_id = session["id"]

        # 2. 立即暂停
        response = client.post(f"/focus/sessions/{session_id}/pause")
        pause_success = response.status_code == 200

        # 3. 立即恢复
        response = client.post(f"/focus/sessions/{session_id}/resume")
        resume_success = response.status_code == 200

        # 4. 立即完成
        response = client.post(f"/focus/sessions/{session_id}/complete")
        complete_success = response.status_code == 200

        print_test_success(f"并发操作处理: 暂停{pause_success}, 恢复{resume_success}, 完成{complete_success}")

        # 验证任务完成
        complete_task_with_validation(client, task_id)

    finally:
        # 清理任务
        try:
            client.delete(f"/tasks/{task_id}")
        except Exception:
            pass

    print_test_success("跨模块错误场景测试通过！")


@pytest.mark.scenario
@pytest.mark.combined_flow
def test_comprehensive_business_flow(authenticated_client: httpx.Client):
    """
    测试综合业务流程

    模拟真实用户的完整使用场景
    """
    print_test_header("综合业务流程测试")

    client = authenticated_client

    # 记录初始状态
    initial_state = {
        "points": get_user_points(client),
        "rewards": len(get_user_rewards(client)),
        "tasks": 0
    }

    try:
        # 阶段1: 用户日常任务管理
        print_test_step("阶段1: 日常任务管理")
        daily_tasks = []

        # 创建今日任务
        task_titles = ["完成项目报告", "学习新技术", "锻炼身体", "阅读书籍", "整理笔记"]
        for title in task_titles:
            task_data = create_sample_task(title, f"今日需要完成的{title}")
            task = create_task_with_validation(client, task_data)
            daily_tasks.append(task["id"])

        print_test_success(f"创建 {len(daily_tasks)} 个日常任务")

        # 阶段2: 专注工作时间
        print_test_step("阶段2: 专注工作时间")
        focus_sessions = []

        # 为重要任务进行专注
        important_tasks = daily_tasks[:3]  # 前3个重要任务
        for i, task_id in enumerate(important_tasks):
            session = start_focus_session_with_validation(client, duration=25)
            focus_sessions.append(session["id"])

            # 完成Focus会话
            response = client.post(f"/focus/sessions/{session['id']}/complete")
            assert_api_success(response, f"完成Focus会话 {session['id']} 失败")

            # 完成任务
            complete_task_with_validation(client, task_id)

        print_test_success(f"完成 {len(focus_sessions)} 个Focus会话和相关任务")

        # 阶段3: 设置明日Top3（模拟）
        print_test_step("阶段3: Top3目标设置")
        current_points = get_user_points(client)

        if current_points >= 300:
            # 如果积分足够，设置Top3
            remaining_tasks = daily_tasks[3:]  # 剩余任务
            if len(remaining_tasks) >= 3:
                today = date.today().strftime("%Y-%m-%d")
                top3_data = {
                    "date": today,
                    "task_ids": [
                        {"position": 1, "task_id": remaining_tasks[0]},
                        {"position": 2, "task_id": remaining_tasks[1]},
                        {"position": 3, "task_id": remaining_tasks[2]}
                    ]
                }

                response = client.post("/tasks/special/top3", json=top3_data)
                if response.status_code == 200:
                    print_test_success("Top3设置成功")

                    # 完成Top3任务
                    for task_id in remaining_tasks[:3]:
                        complete_task_with_validation(client, task_id)

                    print_test_success("Top3任务全部完成")
                else:
                    print_test_success("Top3设置失败，跳过Top3流程")
            else:
                print_test_success("剩余任务不足3个，跳过Top3流程")
        else:
            print_test_success(f"积分不足({current_points} < 300)，跳过Top3流程")

        # 阶段4: 查看成果和奖励
        print_test_step("阶段4: 查看成果和奖励")

        final_points = get_user_points(client)
        final_rewards = get_user_rewards(client)

        # 计算成果
        points_gained = final_points - initial_state["points"]
        rewards_gained = len(final_rewards) - initial_state["rewards"]
        tasks_completed = len(daily_tasks)

        print_test_success(f"📊 今日成果统计:")
        print_test_success(f"   ✅ 完成任务: {tasks_completed} 个")
        print_test_success(f"   💰 积分增长: {points_gained} 分")
        print_test_success(f"   🎁 获得奖励: {rewards_gained} 个")
        print_test_success(f"   💎 当前积分: {final_points} 分")

        # 阶段5: 奖励兑换（如果积分足够）
        print_test_step("阶段5: 奖励兑换")
        if final_points >= 50:  # 假设50积分可以兑换小奖品
            response = client.get("/rewards/catalog")
            if response.status_code == 200:
                catalog = response.json()["data"]
                affordable_rewards = [r for r in catalog.get("items", []) if r.get("points_value", 0) <= final_points]

                if affordable_rewards:
                    reward = affordable_rewards[0]  # 选择第一个可兑换的奖品
                    redeem_data = {"reward_id": reward["id"]}
                    response = client.post("/rewards/redeem", json=redeem_data)

                    if response.status_code == 200:
                        print_test_success(f"成功兑换奖品: {reward['name']}")
                    else:
                        print_test_success(f"兑换奖品失败，状态码: {response.status_code}")
                else:
                    print_test_success("没有可兑换的奖品")
            else:
                print_test_success("获取奖品目录失败")
        else:
            print_test_success("积分不足，无法兑换奖品")

    finally:
        # 清理所有创建的任务
        print_test_step("清理所有任务")
        for task_id in daily_tasks:
            try:
                client.delete(f"/tasks/{task_id}")
            except Exception:
                pass

    print_test_success("综合业务流程测试通过！")
    print_test_success("🎉 模拟真实用户使用场景完成")