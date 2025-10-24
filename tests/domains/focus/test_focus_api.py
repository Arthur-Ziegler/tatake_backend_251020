"""
Focus领域API层测试

测试Focus相关的HTTP API端点，包括：
1. 创建会话
2. 结束会话
3. 查询会话
4. 统计信息

模块化设计：独立的API测试文件，专注于HTTP层验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import httpx

from src.domains.focus.models import FocusSession, SessionTypeConst
from tests.scenarios.utils import (
    create_test_client,
    create_authenticated_user,
    assert_api_success,
    assert_api_error
)


@pytest.mark.integration
class TestFocusSessionAPI:
    """Focus会话API测试类"""

    @pytest.fixture
    def authenticated_client(self):
        """创建认证的测试客户端"""
        user_data = create_authenticated_user()
        client = create_test_client()
        client.headers.update({
            "Authorization": f"Bearer {user_data['access_token']}"
        })
        return client, user_data

    def test_create_focus_session_api(self, authenticated_client):
        """测试创建Focus会话API"""
        client, user_data = authenticated_client
        task_id = str(uuid4())

        session_data = {
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        }

        response = client.post("/focus/sessions", json=session_data)
        assert_api_success(response, "创建Focus会话失败")

        data = response.json()["data"]
        assert "id" in data
        assert data["user_id"] == user_data["user_id"]
        assert data["task_id"] == task_id
        assert data["session_type"] == SessionTypeConst.FOCUS
        assert data["end_time"] is None

    def test_end_active_session_api(self, authenticated_client):
        """测试结束活跃会话API"""
        client, user_data = authenticated_client
        task_id = str(uuid4())

        # 先创建会话
        create_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        assert_api_success(create_response)
        session_id = create_response.json()["data"]["id"]

        # 结束会话
        end_response = client.post(f"/focus/sessions/{session_id}/end")
        assert_api_success(end_response)

        data = end_response.json()["data"]
        assert data["id"] == session_id
        assert data["end_time"] is not None
        assert data["duration_minutes"] is not None

    def test_get_user_sessions_api(self, authenticated_client):
        """测试获取用户会话列表API"""
        client, user_data = authenticated_client
        task_id = str(uuid4())

        # 创建多个会话
        for i in range(3):
            client.post("/focus/sessions", json={
                "task_id": task_id,
                "session_type": SessionTypeConst.FOCUS if i % 2 == 0 else SessionTypeConst.BREAK
            })

        # 获取会话列表
        response = client.get("/focus/sessions")
        assert_api_success(response)

        sessions = response.json()["data"]["items"]
        assert len(sessions) >= 3

        # 验证所有会话都属于当前用户
        for session in sessions:
            assert session["user_id"] == user_data["user_id"]

    def test_get_session_statistics_api(self, authenticated_client):
        """测试获取会话统计API"""
        client, user_data = authenticated_client

        response = client.get("/focus/statistics")
        assert_api_success(response)

        stats = response.json()["data"]
        assert "total_sessions" in stats
        assert "total_focus_minutes" in stats
        assert "total_break_minutes" in stats
        assert "completion_rate" in stats

    def test_pause_session_api(self, authenticated_client):
        """测试暂停会话API"""
        client, user_data = authenticated_client
        task_id = str(uuid4())

        # 创建专注会话
        create_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        session_id = create_response.json()["data"]["id"]

        # 暂停会话
        pause_response = client.post(f"/focus/sessions/{session_id}/pause")
        assert_api_success(pause_response)

        data = pause_response.json()["data"]
        assert data["session_type"] == SessionTypeConst.PAUSE
        assert data["end_time"] is None  # 暂停会话应该是活跃的

    def test_get_active_session_api(self, authenticated_client):
        """测试获取活跃会话API"""
        client, user_data = authenticated_client
        task_id = str(uuid4())

        # 无活跃会话时
        response = client.get("/focus/active-session")
        assert response.status_code == 404

        # 创建活跃会话
        client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })

        # 获取活跃会话
        response = client.get("/focus/active-session")
        assert_api_success(response)

        data = response.json()["data"]
        assert data["end_time"] is None
        assert data["session_type"] == SessionTypeConst.FOCUS

    def test_session_validation_errors(self, authenticated_client):
        """测试会话验证错误"""
        client, user_data = authenticated_client

        # 缺少必需字段
        response = client.post("/focus/sessions", json={})
        assert_api_error(response, 400)

        # 无效的会话类型
        response = client.post("/focus/sessions", json={
            "task_id": str(uuid4()),
            "session_type": "invalid_type"
        })
        assert_api_error(response, 422)

        # 无效的UUID
        response = client.post("/focus/sessions", json={
            "task_id": "invalid_uuid",
            "session_type": SessionTypeConst.FOCUS
        })
        assert_api_error(response, 422)

    def test_unauthorized_access(self):
        """测试未授权访问"""
        client = create_test_client()

        # 无认证头的请求
        response = client.get("/focus/sessions")
        assert response.status_code == 401

        response = client.post("/focus/sessions", json={
            "task_id": str(uuid4()),
            "session_type": SessionTypeConst.FOCUS
        })
        assert response.status_code == 401

    def test_get_sessions_by_type_api(self, authenticated_client):
        """测试根据类型获取会话API"""
        client, user_data = authenticated_client
        task_id = str(uuid4())

        # 创建不同类型的会话
        client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.BREAK
        })

        # 获取Focus类型的会话
        response = client.get(f"/focus/sessions?type={SessionTypeConst.FOCUS}")
        assert_api_success(response)

        sessions = response.json()["data"]["items"]
        for session in sessions:
            assert session["session_type"] == SessionTypeConst.FOCUS

    def test_delete_session_api(self, authenticated_client):
        """测试删除会话API"""
        client, user_data = authenticated_client
        task_id = str(uuid4())

        # 创建会话
        create_response = client.post("/focus/sessions", json={
            "task_id": task_id,
            "session_type": SessionTypeConst.FOCUS
        })
        session_id = create_response.json()["data"]["id"]

        # 删除会话
        response = client.delete(f"/focus/sessions/{session_id}")
        assert response.status_code == 204

        # 验证会话已删除
        get_response = client.get(f"/focus/sessions/{session_id}")
        assert get_response.status_code == 404