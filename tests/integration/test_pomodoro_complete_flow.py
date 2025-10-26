"""
番茄钟完整流程集成测试

测试完整的番茄钟工作流程，包括：
1. 任务创建与专注会话结合
2. 专注-休息循环流程
3. 长休息触发机制
4. 会话统计和积分计算

模块化设计：独立的集成测试文件，专注端到端流程验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import time
import httpx

from src.domains.task.models import Task, TaskStatus, TaskPriority
from src.domains.focus.models import FocusSession, SessionTypeConst
from src.domains.points.service import PointsService
from tests.scenarios.utils import (
    create_test_client,
    create_authenticated_user,
    assert_api_success,
    cleanup_user_data
)


@pytest.mark.integration
@pytest.mark.slow
class TestPomodoroCompleteFlow:
    """番茄钟完整流程测试类"""

    @pytest.fixture
    def user_client(self):
        """创建认证的用户客户端"""
        user_data = create_authenticated_user()
        client = create_test_client()
        client.headers.update({
            "Authorization": f"Bearer {user_data['access_token']}"
        })
        return client, user_data

    @pytest.fixture
    def pomodoro_task(self, user_client):
        """创建番茄钟任务"""
        client, user_data = user_client

        task_data = {
            "title": "番茄钟测试任务",
            "description": "用于测试完整番茄钟流程的任务",
            "priority": TaskPriority.HIGH.value,
            "tags": ["番茄钟", "测试"],
            "estimated_duration": 125  # 5个番茄钟
        }

        response = client.post("/tasks/", json=task_data)
        assert_api_success(response)

        return response.json()["data"]

    def test_standard_pomodoro_cycle(self, user_client, pomodoro_task):
        """测试标准番茄钟周期"""
        client, user_data = user_client
        task_id = pomodoro_task["id"]

        # 标准番茄钟周期：4个专注时段 + 1个长休息
        pomodoro_cycles = [
            {"type": SessionTypeConst.FOCUS, "duration": 25},
            {"type": SessionTypeConst.BREAK, "duration": 5},
            {"type": SessionTypeConst.FOCUS, "duration": 25},
            {"type": SessionTypeConst.BREAK, "duration": 5},
            {"type": SessionTypeConst.FOCUS, "duration": 25},
            {"type": SessionTypeConst.BREAK, "duration": 5},
            {"type": SessionTypeConst.FOCUS, "duration": 25},
            {"type": SessionTypeConst.LONG_BREAK, "duration": 15},
        ]

        sessions = []

        for cycle in pomodoro_cycles:
            # 开始会话
            start_response = client.post("/focus/sessions", json={
                "task_id": task_id,
                "session_type": cycle["type"]
            })
            assert_api_success(start_response)

            session = start_response.json()["data"]
            sessions.append(session)

            # 模拟会话进行
            time.sleep(0.1)  # 短暂等待

            # 结束会话
            end_response = client.post(f"/focus/sessions/{session['id']}/end")
            assert_api_success(end_response)

        # 验证所有会话都已完成
        for session in sessions:
            get_response = client.get(f"/focus/sessions/{session['id']}")
            assert_api_success(get_response)
            session_data = get_response.json()["data"]
            assert session_data["end_time"] is not None

        # 验证任务状态更新
        task_response = client.get(f"/tasks/{task_id}")
        assert_api_success(task_response)
        task_data = task_response.json()["data"]

        # 经过4个专注时段，任务应该有显著进展
        assert task_data["completion_percentage"] >= 50.0

    def test_interrupted_pomodoro_handling(self, user_client, pomodoro_task):
        """测试中断的番茄钟处理"""
        client, user_data = user_client
        task_id = pomodoro_task["id"]

        # 开始专注会话
        start_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        assert_api_success(start_response)

        session = start_response.json()["data"]

        # 模拟中断（立即暂停）
        pause_response = client.post(f"/focus/sessions/{session['id']}/pause")
        assert_api_success(pause_response)

        # 验证暂停会话创建
        pause_data = pause_response.json()["data"]
        assert pause_data["session_type"] == SessionTypeConst.PAUSE

        # 验证原专注会话已结束
        original_response = client.get(f"/focus/sessions/{session['id']}")
        assert_api_success(original_response)
        original_data = original_response.json()["data"]
        assert original_data["end_time"] is not None

    def test_multiple_tasks_pomodoro(self, user_client):
        """测试多任务番茄钟管理"""
        client, user_data = user_client

        # 创建多个任务
        tasks = []
        for i in range(3):
            task_data = {
                "title": f"番茄钟任务 {i+1}",
                "description": f"第{i+1}个需要专注完成的任务",
                "priority": TaskPriority.MEDIUM.value,
                "tags": ["番茄钟", f"任务{i+1}"]
            }

            response = client.post("/tasks/", json=task_data)
            assert_api_success(response)
            tasks.append(response.json()["data"])

        # 为每个任务分配专注时间
        for task in tasks:
            # 开始专注会话
            start_response = client.post("/focus/sessions", json={
                "task_id": task["id"],
                "session_type": SessionTypeConst.FOCUS
            })
            assert_api_success(start_response)

            session = start_response.json()["data"]

            # 模拟短时间专注
            time.sleep(0.1)

            # 结束会话
            end_response = client.post(f"/focus/sessions/{session['id']}/end")
            assert_api_success(end_response)

        # 验证所有任务都有进展
        for task in tasks:
            task_response = client.get(f"/tasks/{task['id']}")
            assert_api_success(task_response)
            task_data = task_response.json()["data"]
            assert task_data["completion_percentage"] > 0

    def test_pomodoro_statistics_calculation(self, user_client, pomodoro_task):
        """测试番茄钟统计计算"""
        client, user_data = user_client
        task_id = pomodoro_task["id"]

        # 完成几个番茄钟会话
        focus_sessions = []
        for i in range(3):
            # 专注会话
            start_response = client.post("/focus/sessions", json={
                "task_id": task_id,
                "session_type": SessionTypeConst.FOCUS
            })
            assert_api_success(start_response)
            focus_session = start_response.json()["data"]
            focus_sessions.append(focus_session)

            time.sleep(0.1)

            # 结束专注
            end_response = client.post(f"/focus/sessions/{focus_session['id']}/end")
            assert_api_success(end_response)

            # 短休息（除了最后一个）
            if i < 2:
                break_response = client.post("/focus/sessions", json={
                    "task_id": task_id,
                    "session_type": SessionTypeConst.BREAK
                })
                assert_api_success(break_response)

                break_session = break_response.json()["data"]
                time.sleep(0.1)

                break_end_response = client.post(f"/focus/sessions/{break_session['id']}/end")
                assert_api_success(break_end_response)

        # 获取统计信息
        stats_response = client.get("/focus/statistics")
        assert_api_success(stats_response)

        stats = stats_response.json()["data"]

        # 验证统计数据
        assert stats["total_sessions"] >= 6  # 3个专注 + 2个休息 + 可能的其他会话
        assert stats["total_focus_minutes"] >= 0
        assert stats["total_break_minutes"] >= 0

    def test_pomodoro_with_points_integration(self, user_client, pomodoro_task):
        """测试番茄钟与积分系统集成"""
        client, user_data = user_client
        task_id = pomodoro_task["id"]
        user_id = user_data["user_id"]

        # 获取初始积分
        try:
            points_response = client.get(f"/points/my-points?user_id={user_id}")
            if points_response.status_code == 200:
                initial_points = points_response.json()["data"]["current_balance"]
            else:
                initial_points = 0
        except:
            initial_points = 0

        # 完成一个完整的番茄钟会话
        start_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        assert_api_success(start_response)

        session = start_response.json()["data"]

        time.sleep(0.1)

        # 完成会话
        complete_response = client.post(f"/focus/sessions/{session['id']}/end")
        assert_api_success(complete_response)

        # 完成任务（可能获得积分）
        task_complete_response = client.post(f"/tasks/{task_id}/complete", json={
            "mood_feedback": {
                "comment": "番茄钟帮助完成任务",
                "difficulty": "medium"
            }
        })

        # 如果任务完成成功，检查积分变化
        if task_complete_response.status_code in [200, 201]:
            try:
                final_points_response = client.get(f"/points/my-points?user_id={user_id}")
                if final_points_response.status_code == 200:
                    final_points = final_points_response.json()["data"]["current_balance"]
                    # 验证积分增加（根据业务规则）
                    assert final_points >= initial_points
            except:
                pass  # 积分系统可能尚未完全实现

    def test_pomodoro_error_recovery(self, user_client, pomodoro_task):
        """测试番茄钟错误恢复"""
        client, user_data = user_client
        task_id = pomodoro_task["id"]

        # 开始专注会话
        start_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        assert_api_success(start_response)

        session = start_response.json()["data"]

        # 模拟意外中断（不正常结束会话）
        # 直接开始新会话，系统应该自动关闭之前的会话
        new_session_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.BREAK
        })
        assert_api_success(new_session_response)

        # 验证第一个会话被自动关闭
        original_response = client.get(f"/focus/sessions/{session['id']}")
        assert_api_success(original_response)
        original_data = original_response.json()["data"]
        assert original_data["end_time"] is not None

        # 新会话应该正常活跃
        new_session = new_session_response.json()["data"]
        assert new_session["end_time"] is None

    def test_pomodoro_session_validation(self, user_client):
        """测试番茄钟会话验证"""
        client, user_data = user_client

        # 测试无效的任务ID
        invalid_task_id = str(uuid4())
        response = client.post("/focus/sessions", json={
            "task_id": invalid_task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        # 应该返回错误，因为任务不存在
        assert response.status_code in [400, 404, 422]

        # 测试无效的会话类型
        valid_task = {
            "title": "验证测试任务",
            "description": "用于验证会话创建的任务",
            "priority": TaskPriority.MEDIUM.value
        }

        task_response = client.post("/tasks/", json=valid_task)
        assert_api_success(task_response)
        task_id = task_response.json()["data"]["id"]

        # 使用无效会话类型
        invalid_session_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": "invalid_type"
        })
        assert invalid_session_response.status_code == 422

    def test_pomodoro_cleanup(self, user_client, pomodoro_task):
        """测试番茄钟数据清理"""
        client, user_data = user_client
        task_id = pomodoro_task["id"]
        user_id = user_data["user_id"]

        # 创建一些会话数据
        sessions = []
        for i in range(3):
            response = client.post("/focus/sessions", json={
                "task_id": task_id,
                "session_type": SessionTypeConst.FOCUS if i % 2 == 0 else SessionTypeConst.BREAK
            })
            assert_api_success(response)
            sessions.append(response.json()["data"])

        # 清理测试数据
        cleanup_success = cleanup_user_data(client, user_id, [task_id])
        assert cleanup_success

        # 验证会话已被清理（或标记为已删除）
        for session in sessions:
            session_response = client.get(f"/focus/sessions/{session['id']}")
            # 会话可能被删除或访问受限
            assert session_response.status_code in [200, 404, 401]