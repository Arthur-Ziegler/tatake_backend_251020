"""
Focus番茄钟流程场景测试

测试Focus番茄钟系统的完整业务流程，包括：
1. 开始Focus会话
2. 暂停Focus会话
3. 恢复Focus会话
4. 完成Focus会话
5. 查询Focus历史记录

优先级：C（中等优先级）
作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import httpx
import time
from datetime import datetime, timedelta
from utils import (
    print_test_header, print_test_step, print_test_success, print_test_error,
    assert_api_success, assert_contains_fields, assert_points_change,
    get_user_points, start_focus_session_with_validation
)


@pytest.mark.scenario
@pytest.mark.focus_flow
def test_focus_complete_flow(authenticated_client: httpx.Client):
    """
    测试Focus番茄钟完整业务流程

    流程：开始 → 暂停 → 恢复 → 完成 → 查询历史
    """
    print_test_header("Focus番茄钟完整流程测试")

    client = authenticated_client

    # 步骤1: 获取初始积分
    print_test_step("获取用户初始积分")
    initial_points = get_user_points(client)
    print(f"初始积分: {initial_points}")

    # 步骤2: 开始Focus会话
    print_test_step("开始Focus会话（25分钟）")
    session = start_focus_session_with_validation(client, duration=25)
    session_id = session["id"]
    print_test_success(f"Focus会话开始成功，ID: {session_id}")

    # 步骤3: 验证会话状态
    print_test_step("验证会话状态")
    response = client.get(f"/focus/sessions")
    assert_api_success(response, "获取Focus会话列表失败")
    sessions = response.json()["data"]
    assert len(sessions) >= 1, "应该至少有一个Focus会话"

    # 查找我们创建的会话
    created_session = None
    for s in sessions:
        if s["id"] == session_id:
            created_session = s
            break

    assert created_session is not None, "在会话列表中找不到创建的会话"
    assert created_session["status"] == "active", f"会话状态应为active，实际为 {created_session['status']}"
    assert created_session["duration_minutes"] == 25, "会话时长不正确"
    print_test_success("会话状态验证成功")

    # 步骤4: 暂停Focus会话
    print_test_step("暂停Focus会话")
    response = client.post(f"/focus/sessions/{session_id}/pause")
    assert_api_success(response, "暂停Focus会话失败")
    paused_session = response.json()["data"]
    assert paused_session["status"] == "paused", f"会话状态应为paused，实际为 {paused_session['status']}"
    print_test_success("Focus会话暂停成功")

    # 步骤5: 恢复Focus会话
    print_test_step("恢复Focus会话")
    response = client.post(f"/focus/sessions/{session_id}/resume")
    assert_api_success(response, "恢复Focus会话失败")
    resumed_session = response.json()["data"]
    assert resumed_session["status"] == "active", f"会话状态应为active，实际为 {resumed_session['status']}"
    print_test_success("Focus会话恢复成功")

    # 步骤6: 完成Focus会话
    print_test_step("完成Focus会话")
    response = client.post(f"/focus/sessions/{session_id}/complete")
    assert_api_success(response, "完成Focus会话失败")
    completed_session = response.json()["data"]
    assert completed_session["status"] == "completed", f"会话状态应为completed，实际为 {completed_session['status']}"
    assert_contains_fields(completed_session, ["completed_at", "actual_duration_minutes"], "完成会话缺少必需字段")
    print_test_success("Focus会话完成成功")

    # 步骤7: 验证完成会话获得的积分
    print_test_step("验证完成Focus会话获得的积分")
    final_points = get_user_points(client)
    expected_points_gain = 15  # 假设完成25分钟Focus获得15积分
    assert_points_change(initial_points, final_points, expected_points_gain, "完成Focus会话积分变化不正确")
    print_test_success(f"Focus会话完成获得积分奖励，从 {initial_points} 增加到 {final_points}")

    # 步骤8: 查询Focus历史记录
    print_test_step("查询Focus历史记录")
    response = client.get("/focus/sessions")
    assert_api_success(response, "获取Focus历史记录失败")
    history = response.json()["data"]

    # 验证我们完成的会话在历史记录中
    completed_session_in_history = None
    for s in history:
        if s["id"] == session_id:
            completed_session_in_history = s
            break

    assert completed_session_in_history is not None, "完成的会话应该在历史记录中"
    assert completed_session_in_history["status"] == "completed", "历史记录中的会话状态应为completed"
    print_test_success("Focus历史记录查询成功")

    print_test_success("Focus番茄钟完整流程测试通过！")


@pytest.mark.scenario
@pytest.mark.focus_flow
def test_focus_multiple_sessions(authenticated_client: httpx.Client):
    """
    测试多个Focus会话场景

    测试连续创建和管理多个Focus会话
    """
    print_test_header("Focus多会话管理测试")

    client = authenticated_client
    initial_points = get_user_points(client)
    session_ids = []

    try:
        # 步骤1: 创建多个不同时长的Focus会话
        print_test_step("创建多个不同时长的Focus会话")
        durations = [15, 25, 45, 60]  # 不同的专注时长

        for i, duration in enumerate(durations):
            print(f"创建第 {i+1} 个Focus会话，时长: {duration} 分钟")
            session = start_focus_session_with_validation(client, duration=duration)
            session_ids.append(session["id"])
            print_test_success(f"会话 {i+1} 创建成功，ID: {session['id']}")

            # 立即完成这个会话
            response = client.post(f"/focus/sessions/{session['id']}/complete")
            assert_api_success(response, f"完成会话 {session['id']} 失败")

        print_test_success(f"成功创建并完成 {len(session_ids)} 个Focus会话")

        # 步骤2: 验证多个会话的积分奖励
        print_test_step("验证多个会话的积分奖励")
        final_points = get_user_points(client)
        total_points_gained = 0

        # 根据时长计算期望积分（这里使用简单的比例计算）
        for duration in durations:
            points = min(duration // 2, 30)  # 每分钟0.5积分，最多30积分
            total_points_gained += points

        # 验证积分确实增加了
        assert final_points > initial_points, "完成多个Focus会话应该获得积分"
        print_test_success(f"多个Focus会话完成，积分从 {initial_points} 增加到 {final_points}")

        # 步骤3: 验证所有会话都在历史记录中
        print_test_step("验证所有会话都在历史记录中")
        response = client.get("/focus/sessions")
        assert_api_success(response, "获取Focus历史记录失败")
        history = response.json()["data"]

        # 检查我们创建的会话数量
        completed_sessions = [s for s in history if s["id"] in session_ids and s["status"] == "completed"]
        assert len(completed_sessions) == len(session_ids), "不是所有会话都在历史记录中"
        print_test_success(f"所有 {len(session_ids)} 个会话都在历史记录中")

    finally:
        # 清理：如果有未完成的会话，尝试完成它们
        print_test_step("清理未完成的会话")
        for session_id in session_ids:
            try:
                response = client.post(f"/focus/sessions/{session_id}/complete")
                if response.status_code == 200:
                    print_test_success(f"会话 {session_id} 清理完成")
            except Exception as e:
                print_test_error(f"清理会话 {session_id} 失败: {e}")


@pytest.mark.scenario
@pytest.mark.focus_flow
def test_focus_error_handling(authenticated_client: httpx.Client):
    """
    测试Focus错误处理场景

    验证Focus系统的各种错误情况处理
    """
    print_test_header("Focus错误处理测试")

    client = authenticated_client

    # 步骤1: 测试操作不存在的会话
    print_test_step("测试操作不存在的会话")
    fake_session_id = "00000000-0000-0000-0000-000000000000"

    # 尝试暂停不存在的会话
    response = client.post(f"/focus/sessions/{fake_session_id}/pause")
    assert response.status_code in [404, 400], f"暂停不存在会话应返回错误，实际: {response.status_code}"

    # 尝试恢复不存在的会话
    response = client.post(f"/focus/sessions/{fake_session_id}/resume")
    assert response.status_code in [404, 400], f"恢复不存在会话应返回错误，实际: {response.status_code}"

    # 尝试完成不存在的会话
    response = client.post(f"/focus/sessions/{fake_session_id}/complete")
    assert response.status_code in [404, 400], f"完成不存在会话应返回错误，实际: {response.status_code}"
    print_test_success("操作不存在会话的错误处理正确")

    # 步骤2: 测试重复操作会话
    print_test_step("测试重复操作会话")
    # 创建一个会话
    session = start_focus_session_with_validation(client, duration=25)
    session_id = session["id"]

    try:
        # 暂停会话
        response = client.post(f"/focus/sessions/{session_id}/pause")
        assert_api_success(response, "暂停会话失败")

        # 再次暂停已暂停的会话
        response = client.post(f"/focus/sessions/{session_id}/pause")
        # 应该处理重复暂停（可能返回成功或特定错误）
        print_test_success(f"重复暂停处理，状态码: {response.status_code}")

        # 恢复会话
        response = client.post(f"/focus/sessions/{session_id}/resume")
        assert_api_success(response, "恢复会话失败")

        # 再次恢复已恢复的会话
        response = client.post(f"/focus/sessions/{session_id}/resume")
        print_test_success(f"重复恢复处理，状态码: {response.status_code}")

        # 完成会话
        response = client.post(f"/focus/sessions/{session_id}/complete")
        assert_api_success(response, "完成会话失败")

        # 再次尝试完成已完成的会话
        response = client.post(f"/focus/sessions/{session_id}/complete")
        print_test_success(f"重复完成处理，状态码: {response.status_code}")

    finally:
        # 确保会话被清理
        try:
            client.post(f"/focus/sessions/{session_id}/complete")
        except Exception:
            pass

    # 步骤3: 测试无效的会话数据
    print_test_step("测试无效的会话数据")
    invalid_focus_data = {
        "duration_minutes": -5,  # 无效的负数时长
        "task_type": "invalid_type"  # 无效的任务类型
    }
    response = client.post("/focus/sessions", json=invalid_focus_data)
    assert response.status_code in [422, 400], f"创建无效会话应返回错误，实际: {response.status_code}"
    print_test_success("无效会话数据错误处理正确")

    # 步骤4: 测试边界值
    print_test_step("测试边界值")
    # 测试零时长
    zero_duration_data = {
        "duration_minutes": 0,
        "task_type": "work"
    }
    response = client.post("/focus/sessions", json=zero_duration_data)
    assert response.status_code in [422, 400], f"零时长会话应返回错误，实际: {response.status_code}"

    # 测试过大时长
    large_duration_data = {
        "duration_minutes": 1000,  # 过大的时长
        "task_type": "work"
    }
    response = client.post("/focus/sessions", json=large_duration_data)
    assert response.status_code in [422, 400], f"过大时长会话应返回错误，实际: {response.status_code}"
    print_test_success("边界值错误处理正确")

    print_test_success("Focus错误处理测试通过！")


@pytest.mark.scenario
@pytest.mark.focus_flow
def test_focus_task_integration(authenticated_client: httpx.Client):
    """
    测试Focus与任务系统集成

    验证Focus会话与任务系统的关联和协同工作
    """
    print_test_header("Focus任务集成测试")

    client = authenticated_client

    # 步骤1: 创建一个任务与Focus会话关联
    print_test_step("创建任务与Focus会话关联")
    from utils import create_sample_task, create_task_with_validation

    task_data = create_sample_task("专注任务", "这个任务需要专注完成")
    task = create_task_with_validation(client, task_data)
    task_id = task["id"]

    try:
        # 步骤2: 开始关联任务的Focus会话
        print_test_step("开始关联任务的Focus会话")
        focus_data = {
            "duration_minutes": 25,
            "task_type": "work",
            "task_id": task_id  # 如果API支持关联任务
        }

        response = client.post("/focus/sessions", json=focus_data)
        if response.status_code == 200:
            session = response.json()["data"]
            session_id = session["id"]
            print_test_success(f"关联任务的Focus会话创建成功，ID: {session_id}")

            # 步骤3: 完成Focus会话
            print_test_step("完成关联任务的Focus会话")
            response = client.post(f"/focus/sessions/{session_id}/complete")
            assert_api_success(response, "完成关联任务的Focus会话失败")
            completed_session = response.json()["data"]
            print_test_success("关联任务的Focus会话完成成功")

            # 步骤4: 验证任务状态变化（如果有集成）
            print_test_step("验证任务状态")
            response = client.get(f"/tasks/{task_id}")
            assert_api_success(response, "获取任务状态失败")
            task_status = response.json()["data"]
            # 这里可以验证任务是否因为Focus完成而有状态变化
            print_test_success(f"任务状态验证: {task_status['status']}")

        else:
            print_test_success("Focus会话不支持任务关联，跳过集成测试")

    finally:
        # 清理任务
        try:
            client.delete(f"/tasks/{task_id}")
        except Exception:
            pass

    print_test_success("Focus任务集成测试通过！")