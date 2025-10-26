"""
API端点响应格式集成测试

验证所有API端点都正确返回UnifiedResponse[T]格式，确保1.2变更的API层面要求得到满足。

作者：TaKeKe团队
版本：1.0.0 - 1.2变更验证
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from typing import Dict, Any

# 导入主应用
from src.api.main import app


class TestUnifiedResponseFormat:
    """统一响应格式验证"""

    def setup_method(self):
        """设置测试客户端"""
        self.client = TestClient(app)

    def assert_unified_response_format(self, response_data: Dict[str, Any], expected_code: int = 200):
        """验证统一响应格式"""
        assert "code" in response_data, "响应缺少code字段"
        assert "data" in response_data, "响应缺少data字段"
        assert "message" in response_data, "响应缺少message字段"
        assert response_data["code"] == expected_code, f"期望code={expected_code}, 实际={response_data['code']}"

        if expected_code == 200:
            assert response_data["data"] is not None, "成功响应的data不应为null"
        else:
            assert response_data["data"] is None, "错误响应的data应为null"

    def test_health_endpoint_response_format(self):
        """测试健康检查端点响应格式"""
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200

        json_data = response.json()
        self.assert_unified_response_format(json_data, 200)

    def test_auth_guest_init_response_format(self):
        """测试游客初始化端点响应格式"""
        response = self.client.post("/api/v1/auth/guest/init")
        assert response.status_code == 200

        json_data = response.json()
        self.assert_unified_response_format(json_data, 200)

        # 验证data字段包含必要信息
        assert "access_token" in json_data["data"]
        assert "user_id" in json_data["data"]
        assert "is_guest" in json_data["data"]

    def test_task_create_response_format(self):
        """测试创建任务端点响应格式"""
        # 首先创建用户获取token
        auth_response = self.client.post("/api/v1/auth/guest/init")
        token = auth_response.json()["data"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        task_data = {
            "title": "测试任务",
            "description": "测试描述"
        }

        response = self.client.post("/api/v1/tasks", json=task_data, headers=headers)
        assert response.status_code == 200

        json_data = response.json()
        self.assert_unified_response_format(json_data, 201)

        # 验证data字段包含任务信息
        task = json_data["data"]
        assert "id" in task
        assert "title" in task
        assert task["title"] == "测试任务"

    def test_task_list_response_format(self):
        """测试任务列表端点响应格式"""
        # 首先创建用户获取token
        auth_response = self.client.post("/api/v1/auth/guest/init")
        token = auth_response.json()["data"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        response = self.client.get("/api/v1/tasks", headers=headers)
        assert response.status_code == 200

        json_data = response.json()
        self.assert_unified_response_format(json_data, 200)

        # 验证data字段包含任务列表
        task_list = json_data["data"]
        assert "tasks" in task_list
        assert "pagination" in task_list
        assert isinstance(task_list["tasks"], list)

    def test_focus_sessions_response_format(self):
        """测试专注会话端点响应格式"""
        # 首先创建用户获取token
        auth_response = self.client.post("/api/v1/auth/guest/init")
        token = auth_response.json()["data"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        response = self.client.get("/api/v1/focus/sessions", headers=headers)
        assert response.status_code == 200

        json_data = response.json()
        self.assert_unified_response_format(json_data, 200)

        # 验证data字段包含会话列表
        sessions_data = json_data["data"]
        assert "sessions" in sessions_data
        assert "total" in sessions_data

    def test_chat_health_response_format(self):
        """测试聊天健康检查端点响应格式"""
        response = self.client.get("/api/v1/chat/health")
        assert response.status_code == 200

        json_data = response.json()
        self.assert_unified_response_format(json_data, 200)

    def test_error_response_format(self):
        """测试错误响应格式"""
        # 测试无效token的错误响应
        headers = {"Authorization": "Bearer invalid_token"}

        response = self.client.get("/api/v1/tasks", headers=headers)
        assert response.status_code == 401

        json_data = response.json()
        self.assert_unified_response_format(json_data, 401)

    def test_task_not_found_response_format(self):
        """测试任务不存在的错误响应格式"""
        # 首先创建用户获取token
        auth_response = self.client.post("/api/v1/auth/guest/init")
        token = auth_response.json()["data"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        fake_task_id = str(uuid4())

        response = self.client.get(f"/api/v1/tasks/{fake_task_id}", headers=headers)
        # 可能返回404或其他错误码

        if response.status_code != 200:
            json_data = response.json()
            # 验证错误响应也遵循统一格式
            assert "code" in json_data
            assert "message" in json_data


class TestSpecificDomainResponses:
    """特定领域响应验证"""

    def setup_method(self):
        """设置测试客户端"""
        self.client = TestClient(app)

    def test_reward_catalog_response_format(self):
        """测试奖励目录端点响应格式"""
        response = self.client.get("/api/v1/rewards/catalog")
        assert response.status_code == 200

        json_data = response.json()
        assert "code" in json_data
        assert "data" in json_data
        assert "message" in json_data

    def test_top3_get_response_format(self):
        """测试获取Top3端点响应格式"""
        # 首先创建用户获取token
        auth_response = self.client.post("/api/v1/auth/guest/init")
        token = auth_response.json()["data"]["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        today = "2023-10-25"

        response = self.client.get(f"/api/v1/tasks/special/top3/{today}", headers=headers)
        # 可能返回200（如果存在Top3）或其他状态码

        json_data = response.json()
        assert "code" in json_data
        assert "data" in json_data
        assert "message" in json_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])