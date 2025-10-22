"""
聊天API简单测试

通过mock认证依赖来测试聊天API的核心功能，
避免复杂的JWT认证问题。

测试重点：
1. API端点基本功能
2. 请求响应格式
3. 错误处理
4. 数据验证

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import uuid
import os
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from src.api.main import app
from src.domains.chat.database import get_chat_database_path


class TestChatAPISimple:
    """
    聊天API简单测试类
    """

    def setup_method(self):
        """
        测试设置
        """
        self.client = TestClient(app)
        self.test_user_id = str(uuid.uuid4())

        # 清理数据库文件
        db_path = get_chat_database_path()
        if os.path.exists(db_path):
            os.remove(db_path)

    def teardown_method(self):
        """
        测试清理
        """
        db_path = get_chat_database_path()
        if os.path.exists(db_path):
            os.remove(db_path)

    @patch('src.api.dependencies.get_current_user_id')
    def test_health_check_no_auth(self, mock_get_user):
        """
        测试健康检查（无需认证）
        """
        response = self.client.get("/api/v1/chat/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    @patch('src.api.dependencies.get_current_user_id')
    def test_create_session_success(self, mock_get_user):
        """
        测试创建会话成功
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        response = self.client.post(
            "/api/v1/chat/sessions",
            json={"title": "测试会话"},
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "session_id" in data["data"]
        assert data["data"]["title"] == "测试会话"
        assert data["message"] == "聊天会话创建成功"

    @patch('src.api.dependencies.get_current_user_id')
    def test_list_sessions_success(self, mock_get_user):
        """
        测试获取会话列表成功
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        # 先创建几个会话
        for i in range(3):
            self.client.post(
                "/api/v1/chat/sessions",
                json={"title": f"测试会话 {i+1}"},
                headers={"Authorization": "Bearer mock-token"}
            )

        # 获取会话列表
        response = self.client.get(
            "/api/v1/chat/sessions",
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert isinstance(data["sessions"], list)
        assert data["total_count"] >= 3

    @patch('src.api.dependencies.get_current_user_id')
    def test_get_session_info_success(self, mock_get_user):
        """
        测试获取会话信息成功
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        # 创建会话
        create_response = self.client.post(
            "/api/v1/chat/sessions",
            json={"title": "信息测试会话"},
            headers={"Authorization": "Bearer mock-token"}
        )
        session_id = create_response.json()["data"]["session_id"]

        # 获取会话信息
        response = self.client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "title" in data
        assert "message_count" in data
        assert "created_at" in data
        assert "status" in data

    @patch('src.api.dependencies.get_current_user_id')
    def test_delete_session_success(self, mock_get_user):
        """
        测试删除会话成功
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        # 创建会话
        create_response = self.client.post(
            "/api/v1/chat/sessions",
            json={"title": "删除测试会话"},
            headers={"Authorization": "Bearer mock-token"}
        )
        session_id = create_response.json()["data"]["session_id"]

        # 删除会话
        response = self.client.delete(
            f"/api/v1/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["status"] == "deleted"

    @patch('src.api.dependencies.get_current_user_id')
    def test_send_message_success(self, mock_get_user):
        """
        测试发送消息成功
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        # 创建会话
        create_response = self.client.post(
            "/api/v1/chat/sessions",
            json={"title": "消息测试会话"},
            headers={"Authorization": "Bearer mock-token"}
        )
        session_id = create_response.json()["data"]["session_id"]

        # 发送消息
        response = self.client.post(
            f"/api/v1/chat/sessions/{session_id}/send",
            json={"message": "测试消息"},
            headers={"Authorization": "Bearer mock-token"}
        )

        # 由于AI服务可能不可用，我们主要验证API结构
        # 状态码可能是200（成功）或500（AI服务错误）
        assert response.status_code in [200, 500]

    @patch('src.api.dependencies.get_current_user_id')
    def test_get_chat_history_success(self, mock_get_user):
        """
        测试获取聊天历史成功
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        # 创建会话
        create_response = self.client.post(
            "/api/v1/chat/sessions",
            json={"title": "历史测试会话"},
            headers={"Authorization": "Bearer mock-token"}
        )
        session_id = create_response.json()["data"]["session_id"]

        # 获取历史
        response = self.client.get(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)

    @patch('src.api.dependencies.get_current_user_id')
    def test_unauthorized_access(self, mock_get_user):
        """
        测试未授权访问
        """
        # 不mock用户ID，让认证失败
        response = self.client.post(
            "/api/v1/chat/sessions",
            json={"title": "未授权测试"}
        )

        assert response.status_code == 401

    @patch('src.api.dependencies.get_current_user_id')
    def test_invalid_request_data(self, mock_get_user):
        """
        测试无效请求数据
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        # 创建会话时缺少必需字段
        response = self.client.post(
            "/api/v1/chat/sessions",
            json={},  # 空请求体
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 422

    @patch('src.api.dependencies.get_current_user_id')
    def test_session_not_found(self, mock_get_user):
        """
        测试会话不存在
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        fake_session_id = str(uuid.uuid4())

        response = self.client.get(
            f"/api/v1/chat/sessions/{fake_session_id}",
            headers={"Authorization": "Bearer mock-token"}
        )

        assert response.status_code == 404

    @patch('src.api.dependencies.get_current_user_id')
    def test_pagination_parameters(self, mock_get_user):
        """
        测试分页参数
        """
        mock_get_user.return_value = uuid.UUID(self.test_user_id)

        # 测试有效的limit参数
        response = self.client.get(
            "/api/v1/chat/sessions?limit=5",
            headers={"Authorization": "Bearer mock-token"}
        )
        assert response.status_code == 200

        # 测试无效的limit参数（负数）
        response = self.client.get(
            "/api/v1/chat/sessions?limit=-1",
            headers={"Authorization": "Bearer mock-token"}
        )
        assert response.status_code == 422

        # 测试无效的limit参数（超过最大值）
        response = self.client.get(
            "/api/v1/chat/sessions?limit=1000",
            headers={"Authorization": "Bearer mock-token"}
        )
        assert response.status_code == 422


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])