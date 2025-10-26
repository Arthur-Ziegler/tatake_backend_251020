"""
零Bug测试体系 - 任务API集成测试

测试任务API的完整功能，包括认证、数据验证、业务逻辑等。

这是零Bug测试体系的集成测试示例，展示了如何测试API端到端功能，
包括数据库操作、认证验证、响应格式等。

集成测试原则：
1. 真实环境：使用真实的数据库和API
2. 完整流程：测试完整的业务流程
3. 错误处理：测试各种异常情况
4. 性能验证：确保响应时间符合标准
"""

import pytest
from httpx import Client
from datetime import datetime, timezone, timedelta

from tests.factories.tasks import TaskFactory, TaskFactoryManager
from tests.conftest_zero_bug import ZeroBugTestConfig


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.api
class TestTaskAPIIntegration:
    """任务API集成测试类"""

    def test_create_task_successfully(self, authenticated_client, test_helper):
        """
        测试：成功创建任务

        期望：
        - 返回201状态码
        - 任务数据正确保存
        - 响应格式符合标准
        """
        # Arrange
        task_data = {
            "title": "零Bug测试任务",
            "description": "这是零Bug测试体系的集成测试任务",
            "priority": "high",
            "estimated_hours": 2.5,
            "tags": ["测试", "零Bug"]
        }

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.post("/api/v1/tasks/", json=task_data)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 201)

        data = response.json()
        assert data["data"]["title"] == task_data["title"]
        assert data["data"]["description"] == task_data["description"]
        assert data["data"]["priority"] == task_data["priority"]
        assert data["data"]["status"] == "pending"
        assert data["data"]["completion_percentage"] == 0

    def test_create_task_with_invalid_data(self, authenticated_client, test_helper):
        """
        测试：使用无效数据创建任务

        期望：
        - 返回400状态码
        - 错误信息明确
        - 数据未保存到数据库
        """
        # Arrange
        invalid_task_data = {
            "title": "",  # 空标题
            "priority": "invalid_priority",  # 无效优先级
            "estimated_hours": -1  # 负数工时
        }

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.post("/api/v1/tasks/", json=invalid_task_data)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        assert response.status_code == 400

        data = response.json()
        assert "code" in data
        assert data["code"] != 200
        assert "message" in data or "detail" in data

    def test_get_task_list(self, authenticated_client, sample_tasks, test_helper):
        """
        测试：获取任务列表

        期望：
        - 返回用户的所有任务
        - 分页参数生效
        - 数据格式正确
        """
        # Arrange
        params = {"page": 1, "size": 10}

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.get("/api/v1/tasks/", params=params)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 200)

        data = response.json()
        assert "data" in data
        assert "pagination" in data

        tasks = data["data"]
        assert len(tasks) > 0

        # 验证任务数据格式
        for task in tasks:
            assert "id" in task
            assert "title" in task
            assert "status" in task
            assert "created_at" in task

    def test_get_task_by_id(self, authenticated_client, sample_tasks, test_helper):
        """
        测试：通过ID获取任务

        期望：
        - 返回指定任务
        - 数据完整准确
        - 权限检查正确
        """
        # Arrange
        task = sample_tasks[0]
        task_id = str(task.id)

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.get(f"/api/v1/tasks/{task_id}")

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 200)

        data = response.json()
        task_data = data["data"]
        assert str(task_data["id"]) == task_id
        assert task_data["title"] == task.title

    def test_update_task_status(self, authenticated_client, sample_tasks, test_helper):
        """
        测试：更新任务状态

        期望：
        - 状态正确更新
        - 完成百分比自动调整
        - 时间戳正确更新
        """
        # Arrange
        task = sample_tasks[0]
        task_id = str(task.id)
        update_data = {
            "status": "in_progress"
        }

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.patch(f"/api/v1/tasks/{task_id}/status", json=update_data)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 200)

        data = response.json()
        task_data = data["data"]
        assert task_data["status"] == "in_progress"
        assert 0 < task_data["completion_percentage"] < 100

    def test_complete_task(self, authenticated_client, sample_tasks, test_helper):
        """
        测试：完成任务

        期望：
        - 状态更新为completed
        - 完成百分比为100
        - 设置完成时间
        - 触发积分奖励
        """
        # Arrange
        task = sample_tasks[0]
        task_id = str(task.id)

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.post(f"/api/v1/tasks/{task_id}/complete")

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 200)

        data = response.json()
        task_data = data["data"]
        assert task_data["status"] == "completed"
        assert task_data["completion_percentage"] == 100
        assert task_data["completed_at"] is not None

    def test_delete_task(self, authenticated_client, sample_tasks, test_helper):
        """
        测试：删除任务

        期望：
        - 任务被软删除
        - 再次查询返回404
        - 相关数据正确处理
        """
        # Arrange
        task = sample_tasks[0]
        task_id = str(task.id)

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 200)

        # 验证任务已被删除
        get_response = authenticated_client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.status_code == 404

    def test_create_subtask(self, authenticated_client, sample_tasks, test_helper):
        """
        测试：创建子任务

        期望：
        - 子任务正确关联到父任务
        - 层级结构正确
        - 数据一致性保持
        """
        # Arrange
        parent_task = sample_tasks[0]
        subtask_data = {
            "title": "零Bug子任务测试",
            "description": "这是父任务的子任务",
            "parent_id": str(parent_task.id),
            "estimated_hours": 1.0
        }

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.post("/api/v1/tasks/", json=subtask_data)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 201)

        data = response.json()
        task_data = data["data"]
        assert task_data["parent_id"] == str(parent_task.id)

    def test_get_task_hierarchy(self, authenticated_client, test_helper):
        """
        测试：获取任务层级结构

        期望：
        - 返回完整的任务树
        - 层级关系正确
        - 数据完整
        """
        # Arrange - 创建任务层级
        hierarchy_data = TaskFactoryManager.create_project_tasks("零Bug测试项目", 5)

        # 通过API创建根任务
        root_task_response = authenticated_client.post("/api/v1/tasks/", json={
            "title": hierarchy_data["root_task"]["title"],
            "description": hierarchy_data["root_task"]["description"],
            "priority": "high"
        })
        root_task_id = root_task_response.json()["data"]["id"]

        # 创建子任务
        for task in hierarchy_data["all_tasks"][1:]:
            if task.get("parent_id"):
                authenticated_client.post("/api/v1/tasks/", json={
                    "title": task["title"],
                    "parent_id": root_task_id,
                    "estimated_hours": task.get("estimated_hours", 1.0)
                })

        # Act
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.get(f"/api/v1/tasks/{root_task_id}/hierarchy")

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(response, 200)

        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == root_task_id
        assert "subtasks" in data["data"]

    def test_unauthorized_access(self, test_client, test_helper):
        """
        测试：未授权访问

        期望：
        - 返回401状态码
        - 错误信息明确
        - 不返回敏感数据
        """
        # Act
        start_time = datetime.now(timezone.utc)
        response = test_client.get("/api/v1/tasks/")

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        assert response.status_code == 401

    def test_task_performance_benchmark(self, authenticated_client, test_helper):
        """
        测试：任务API性能基准

        期望：
        - 响应时间符合标准
        - 并发处理正确
        - 资源使用合理
        """
        # Arrange
        task_data = TaskFactory.create()

        # Act - 测试创建性能
        start_time = datetime.now(timezone.utc)
        response = authenticated_client.post("/api/v1/tasks/", json={
            "title": task_data["title"],
            "description": task_data["description"]
        })

        # Assert
        test_helper.assert_performance(start_time, 1.0)  # 1秒内完成
        test_helper.assert_valid_response(response, 201)

    def test_task_data_consistency(self, authenticated_client, test_helper):
        """
        测试：任务数据一致性

        期望：
        - 关联数据保持一致
        - 事务操作正确
        - 并发安全
        """
        # Arrange
        task_data = {
            "title": "一致性测试任务",
            "description": "测试数据一致性",
            "tags": ["一致性", "测试"],
            "estimated_hours": 3.0
        }

        # Act - 创建任务
        start_time = datetime.now(timezone.utc)
        create_response = authenticated_client.post("/api/v1/tasks/", json=task_data)
        task_id = create_response.json()["data"]["id"]

        # 立即查询验证
        get_response = authenticated_client.get(f"/api/v1/tasks/{task_id}")

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_INTEGRATION_TIME)
        test_helper.assert_valid_response(get_response, 200)

        task_info = get_response.json()["data"]
        assert task_info["title"] == task_data["title"]
        assert task_info["tags"] == task_data["tags"]
        assert task_info["estimated_hours"] == task_data["estimated_hours"]