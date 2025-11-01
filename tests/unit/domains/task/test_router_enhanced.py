"""
增强版Task路由单元测试

测试纯微服务代理模式的Task路由实现。
验证所有9个核心接口的路径重写、错误处理和响应适配功能。

测试覆盖：
- 任务CRUD操作（创建、查询、更新、删除）
- 任务完成功能
- Top3管理（设置、查询）
- 专注状态记录
- 番茄钟计数查询
- 路径重写逻辑
- 错误处理和响应适配
- UUID格式验证

作者：TaTakeKe团队
版本：1.0.0
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import date, datetime
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from unittest.mock import Mock

from src.domains.task.router import router
from src.services.enhanced_task_microservice_client import (
    EnhancedTaskMicroserviceClient,
    TaskMicroserviceError
)


class TestEnhancedTaskRouter:
    """增强版Task路由测试"""

    @pytest.fixture
    def app(self):
        """创建FastAPI应用"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def sample_user_id(self):
        """示例用户ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_task_id(self):
        """示例任务ID"""
        return str(uuid4())

    @pytest.fixture
    def mock_microservice_client(self):
        """模拟微服务客户端"""
        mock_client = AsyncMock(spec=EnhancedTaskMicroserviceClient)
        return mock_client

    def test_create_task_success(self, client, sample_user_id, mock_microservice_client):
        """测试成功创建任务"""
        # 准备请求数据
        request_data = {
            "title": "Test Task",
            "description": "Test Description",
            "priority": "high",
            "due_date": "2025-12-01T10:00:00"
        }

        # 准备微服务响应
        microservice_response = {
            "code": 201,
            "success": True,
            "message": "任务创建成功",
            "data": {
                "id": str(uuid4()),
                "title": "Test Task",
                "description": "Test Description",
                "priority": "High",
                "status": "pending",
                "due_date": "2025-12-01T10:00:00"
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.post("/tasks/", json=request_data)

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 201
                assert response_data["data"]["title"] == "Test Task"
                assert response_data["message"] == "任务创建成功"

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="POST",
                    path="tasks",
                    user_id=sample_user_id,
                    data={
                        "title": "Test Task",
                        "description": "Test Description",
                        "priority": "High",  # 验证优先级被转换为首字母大写
                        "due_date": "2025-12-01T10:00:00",
                        "user_id": sample_user_id
                    }
                )

    def test_query_tasks_success(self, client, sample_user_id, mock_microservice_client):
        """测试成功查询任务列表"""
        # 准备请求数据
        request_data = {
            "page": 1,
            "page_size": 20,
            "status": "pending"
        }

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "查询成功",
            "data": [
                {
                    "id": str(uuid4()),
                    "title": "Task 1",
                    "status": "pending",
                    "priority": "Medium"
                },
                {
                    "id": str(uuid4()),
                    "title": "Task 2",
                    "status": "completed",
                    "priority": "High"
                }
            ]
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.post("/tasks/query", json=request_data)

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200
                assert len(response_data["data"]["tasks"]) == 2
                assert "pagination" in response_data["data"]

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="POST",
                    path="tasks/query",
                    user_id=sample_user_id,
                    data={
                        "page": 1,
                        "page_size": 20,
                        "status": "pending"
                    }
                )

    def test_update_task_success(self, client, sample_user_id, sample_task_id, mock_microservice_client):
        """测试成功更新任务"""
        # 准备请求数据
        request_data = {
            "title": "Updated Task",
            "description": "Updated Description",
            "priority": "low",
            "due_date": "2025-12-02T15:00:00"
        }

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "任务更新成功",
            "data": {
                "id": sample_task_id,
                "title": "Updated Task",
                "description": "Updated Description",
                "priority": "Low",
                "status": "pending"
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.put(f"/tasks/{sample_task_id}", json=request_data)

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200
                assert response_data["data"]["title"] == "Updated Task"

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="PUT",
                    path="tasks/{task_id}",
                    user_id=sample_user_id,
                    data={
                        "title": "Updated Task",
                        "description": "Updated Description",
                        "priority": "Low",  # 验证优先级被转换为首字母大写
                        "due_date": "2025-12-02T15:00:00",
                        "user_id": sample_user_id
                    },
                    task_id=sample_task_id
                )

    def test_delete_task_success(self, client, sample_user_id, sample_task_id, mock_microservice_client):
        """测试成功删除任务"""
        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "任务删除成功",
            "data": None
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.delete(f"/tasks/{sample_task_id}")

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200
                assert response_data["data"]["task_id"] == sample_task_id
                assert response_data["data"]["deleted"] is True

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="DELETE",
                    path="tasks/{task_id}",
                    user_id=sample_user_id,
                    task_id=sample_task_id
                )

    def test_complete_task_success(self, client, sample_user_id, sample_task_id, mock_microservice_client):
        """测试成功完成任务"""
        # 准备请求数据
        request_data = {
            "completion_notes": "任务完成备注",
            "actual_duration": 120
        }

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "任务完成成功",
            "data": {
                "task_id": sample_task_id,
                "rewards": {
                    "points_earned": 10,
                    "badge_earned": "Task Complete"
                }
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.post(f"/tasks/{sample_task_id}/complete", json=request_data)

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200
                assert "rewards" in response_data["data"]

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="POST",
                    path="tasks/{task_id}/complete",
                    user_id=sample_user_id,
                    data={
                        "completion_notes": "任务完成备注",
                        "actual_duration": 120,
                        "user_id": sample_user_id,
                        "task_id": sample_task_id
                    },
                    task_id=sample_task_id
                )

    def test_set_top3_success(self, client, sample_user_id, mock_microservice_client):
        """测试成功设置Top3"""
        # 准备请求数据
        task_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        request_data = {
            "date": "2025-11-01",
            "task_ids": task_ids
        }

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "Top3设置成功",
            "data": {
                "date": "2025-11-01",
                "top3_tasks": task_ids
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.post("/tasks/special/top3", json=request_data)

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200
                assert response_data["data"]["date"] == "2025-11-01"

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="POST",
                    path="tasks/special/top3",
                    user_id=sample_user_id,
                    data={
                        "user_id": sample_user_id,
                        "date": "2025-11-01",
                        "task_ids": task_ids
                    }
                )

    def test_get_top3_success(self, client, sample_user_id, mock_microservice_client):
        """测试成功获取Top3"""
        query_date = "2025-11-01"
        task_ids = [str(uuid4()), str(uuid4())]

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "Top3查询成功",
            "data": {
                "date": query_date,
                "top3_tasks": [
                    {"id": task_ids[0], "title": "Task 1"},
                    {"id": task_ids[1], "title": "Task 2"}
                ]
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.get(f"/tasks/special/top3/{query_date}")

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200
                assert response_data["data"]["date"] == query_date

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="POST",
                    path="tasks/top3/query",
                    user_id=sample_user_id,
                    date=query_date
                )

    def test_record_focus_status_success(self, client, sample_user_id, mock_microservice_client):
        """测试成功记录专注状态"""
        # 准备请求数据
        request_data = {
            "focus_status": "focused",
            "duration_minutes": 45,
            "task_id": str(uuid4())
        }

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "专注状态记录成功",
            "data": {
                "focus_session_id": str(uuid4()),
                "status": "recorded"
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.post("/tasks/focus-status", json=request_data)

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="POST",
                    path="tasks/focus-status",
                    user_id=sample_user_id,
                    data={
                        "user_id": sample_user_id,
                        "focus_status": "focused",
                        "duration_minutes": 45,
                        "task_id": request_data["task_id"]
                    }
                )

    def test_get_pomodoro_count_success(self, client, sample_user_id, mock_microservice_client):
        """测试成功获取番茄钟计数"""
        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "番茄钟计数查询成功",
            "data": {
                "date_filter": "today",
                "count": 5,
                "total_duration_minutes": 225
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.get("/tasks/pomodoro-count?date_filter=today")

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 200
                assert response_data["data"]["count"] == 5

                # 验证微服务调用参数
                mock_microservice_client.call_microservice.assert_called_once_with(
                    method="GET",
                    path="tasks/pomodoro-count",
                    user_id=sample_user_id,
                    params={
                        "date_filter": "today",
                        "user_id": sample_user_id
                    }
                )

    def test_microservice_error_handling(self, client, sample_user_id, mock_microservice_client):
        """测试微服务错误处理"""
        # 模拟微服务错误
        mock_microservice_client.call_microservice.side_effect = TaskMicroserviceError(
            message="微服务连接失败",
            status_code=503
        )

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.post("/tasks/", json={
                    "title": "Test Task",
                    "description": "Test Description"
                })

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["code"] == 503
                assert response_data["message"] == "微服务连接失败"
                assert response_data["data"] is None

    def test_health_check_success(self, client, mock_microservice_client):
        """测试健康检查成功"""
        mock_microservice_client.health_check.return_value = True

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            response = client.get("/tasks/health")

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["code"] == 200
            assert response_data["data"]["healthy"] is True
            assert "timestamp" in response_data["data"]

    def test_health_check_failure(self, client, mock_microservice_client):
        """测试健康检查失败"""
        mock_microservice_client.health_check.return_value = False

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            response = client.get("/tasks/health")

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["code"] == 200
            assert response_data["data"]["healthy"] is False
            assert response_data["message"] == "不健康"

    def test_invalid_task_id_format(self, client, sample_user_id):
        """测试无效任务ID格式"""
        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = AsyncMock()
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                # 使用无效的UUID格式
                response = client.get("/tasks/invalid-task-id")

                # 应该返回UUID验证错误
                assert response.status_code == 422  # FastAPI的验证错误

    def test_invalid_date_format(self, client, sample_user_id):
        """测试无效日期格式"""
        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = AsyncMock()
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                # 使用无效的日期格式
                response = client.get("/tasks/special/top3/invalid-date")

                # 应该返回日期验证错误
                assert response.status_code == 422  # FastAPI的验证错误

    def test_top3_task_limit(self, client, sample_user_id, mock_microservice_client):
        """测试Top3任务数量限制"""
        # 准备超过3个任务的请求
        task_ids = [str(uuid4()) for _ in range(5)]
        request_data = {
            "date": "2025-11-01",
            "task_ids": task_ids
        }

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "Top3设置成功",
            "data": {}
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        with patch('src.domains.task.router_enhanced.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client
            with patch('src.domains.task.router_enhanced.get_current_user_id') as mock_auth:
                mock_auth.return_value = UUID(sample_user_id)

                response = client.post("/tasks/special/top3", json=request_data)

                assert response.status_code == 200

                # 验证只传递了前3个任务ID
                call_args = mock_microservice_client.call_microservice.call_args
                sent_task_ids = call_args[1]["data"]["task_ids"]
                assert len(sent_task_ids) == 3
                assert sent_task_ids == task_ids[:3]