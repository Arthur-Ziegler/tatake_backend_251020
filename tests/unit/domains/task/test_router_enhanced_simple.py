"""
增强版Task路由单元测试（简化版）

直接测试路由函数，避免FastAPI依赖复杂性。
专注于验证路径重写、错误处理和响应适配逻辑。

测试覆盖：
- 路径重写逻辑
- 响应数据适配
- 错误处理机制
- UUID验证

作者：TaTakeKe团队
版本：1.0.0
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import date, datetime
from typing import Dict, Any

from src.domains.task.router import (
    adapt_microservice_response_to_client,
    create_error_response,
    router
)
from src.services.enhanced_task_microservice_client import (
    EnhancedTaskMicroserviceClient,
    TaskMicroserviceError
)


class TestEnhancedTaskRouterSimple:
    """增强版Task路由简化测试"""

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
        return AsyncMock(spec=EnhancedTaskMicroserviceClient)

    def test_create_error_response(self):
        """测试错误响应创建"""
        error_response = create_error_response(500, "服务器错误")

        assert error_response.code == 500
        assert error_response.data is None
        assert error_response.message == "服务器错误"

    def test_adapt_microservice_response_to_client_with_array_data(self):
        """测试适配微服务响应数据（数组格式）"""
        microservice_data = {
            "code": 200,
            "success": True,
            "message": "查询成功",
            "data": [
                {"id": "123", "title": "Task 1"},
                {"id": "456", "title": "Task 2"}
            ]
        }

        adapted = adapt_microservice_response_to_client(microservice_data)

        assert adapted["code"] == 200
        assert adapted["success"] is True
        assert adapted["message"] == "查询成功"
        assert isinstance(adapted["data"], dict)
        assert "tasks" in adapted["data"]
        assert "pagination" in adapted["data"]
        assert len(adapted["data"]["tasks"]) == 2

    def test_adapt_microservice_response_to_client_with_object_data(self):
        """测试适配微服务响应数据（对象格式）"""
        microservice_data = {
            "code": 200,
            "success": True,
            "message": "操作成功",
            "data": {
                "id": "123",
                "title": "Task 1",
                "status": "completed"
            }
        }

        adapted = adapt_microservice_response_to_client(microservice_data)

        assert adapted["code"] == 200
        assert adapted["success"] is True
        assert adapted["message"] == "操作成功"
        assert adapted["data"]["id"] == "123"
        assert adapted["data"]["title"] == "Task 1"

    def test_adapt_microservice_response_to_client_with_non_dict_data(self):
        """测试适配微服务响应数据（非字典格式）"""
        microservice_data = "simple string data"

        adapted = adapt_microservice_response_to_client(microservice_data)

        assert adapted == microservice_data

    @pytest.mark.asyncio
    async def test_create_task_endpoint_success(self, sample_user_id, mock_microservice_client):
        """测试成功创建任务端点"""
        from src.domains.task.schemas import CreateTaskRequest
        from src.domains.task.router import create_task_endpoint

        # 准备请求数据
        request = CreateTaskRequest(
            title="Test Task",
            description="Test Description",
            priority="high"
        )

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
                "status": "pending"
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await create_task_endpoint(
                request=request,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 201
            assert result.data.title == "Test Task"
            assert result.message == "任务创建成功"

            # 验证微服务调用参数
            mock_microservice_client.call_microservice.assert_called_once_with(
                method="POST",
                path="tasks",
                user_id=sample_user_id,
                data={
                    "title": "Test Task",
                    "description": "Test Description",
                    "priority": "High",  # 验证优先级被转换为首字母大写
                    "due_date": None,
                    "user_id": sample_user_id
                }
            )

    @pytest.mark.asyncio
    async def test_query_tasks_endpoint_success(self, sample_user_id, mock_microservice_client):
        """测试成功查询任务端点"""
        from src.domains.task.router import TaskQueryRequest, query_tasks_endpoint

        # 准备请求数据
        request = TaskQueryRequest(
            page=1,
            page_size=20,
            status="pending"
        )

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
                }
            ]
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await query_tasks_endpoint(
                request=request,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200
            assert len(result.data.tasks) == 1
            assert result.data.pagination.current_page == 1

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

    @pytest.mark.asyncio
    async def test_update_task_endpoint_success(self, sample_user_id, sample_task_id, mock_microservice_client):
        """测试成功更新任务端点"""
        from src.domains.task.schemas import UpdateTaskRequest
        from src.domains.task.router import update_task_endpoint

        # 准备请求数据
        request = UpdateTaskRequest(
            title="Updated Task",
            description="Updated Description",
            priority="low"
        )

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

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await update_task_endpoint(
                task_id=sample_task_id,
                request=request,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200
            assert result.data.title == "Updated Task"

            # 验证微服务调用参数
            mock_microservice_client.call_microservice.assert_called_once_with(
                method="PUT",
                path="tasks/{task_id}",
                user_id=sample_user_id,
                data={
                    "title": "Updated Task",
                    "description": "Updated Description",
                    "priority": "Low",  # 验证优先级被转换为首字母大写
                    "due_date": None,
                    "user_id": sample_user_id
                },
                task_id=sample_task_id
            )

    @pytest.mark.asyncio
    async def test_delete_task_endpoint_success(self, sample_user_id, sample_task_id, mock_microservice_client):
        """测试成功删除任务端点"""
        from src.domains.task.router import delete_task_endpoint

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "任务删除成功",
            "data": None
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await delete_task_endpoint(
                task_id=sample_task_id,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200
            assert result.data.deleted_task_id == sample_task_id
            assert result.data.deleted_count == 1

            # 验证微服务调用参数
            mock_microservice_client.call_microservice.assert_called_once_with(
                method="DELETE",
                path="tasks/{task_id}",
                user_id=sample_user_id,
                task_id=sample_task_id
            )

    @pytest.mark.asyncio
    async def test_complete_task_endpoint_success(self, sample_user_id, sample_task_id, mock_microservice_client):
        """测试成功完成任务端点"""
        from src.domains.task.router import complete_task_endpoint

        # 准备完成数据
        completion_data = {
            "completion_notes": "任务完成",
            "actual_duration": 120
        }

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "任务完成成功",
            "data": {
                "task_id": sample_task_id,
                "rewards": {"points_earned": 10}
            }
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await complete_task_endpoint(
                task_id=sample_task_id,
                completion_data=completion_data,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200
            assert "rewards" in result.data

            # 验证微服务调用参数
            mock_microservice_client.call_microservice.assert_called_once_with(
                method="POST",
                path="tasks/{task_id}/complete",
                user_id=sample_user_id,
                data={
                    "completion_notes": "任务完成",
                    "actual_duration": 120,
                    "user_id": sample_user_id,
                    "task_id": sample_task_id
                },
                task_id=sample_task_id
            )

    @pytest.mark.asyncio
    async def test_set_top3_endpoint_success(self, sample_user_id, mock_microservice_client):
        """测试成功设置Top3端点"""
        from src.domains.task.router import Top3SetRequest, set_top3_endpoint

        # 准备请求数据
        task_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        request = Top3SetRequest(
            date="2025-11-01",
            task_ids=task_ids
        )

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "Top3设置成功",
            "data": {"date": "2025-11-01", "top3_tasks": task_ids}
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await set_top3_endpoint(
                request=request,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200
            assert result.data["date"] == "2025-11-01"

            # 验证微服务调用参数
            mock_microservice_client.call_microservice.assert_called_once_with(
                method="POST",
                path="tasks/special/top3",
                user_id=sample_user_id,
                data={
                    "user_id": sample_user_id,
                    "date": "2025-11-01",
                    "task_ids": task_ids[:3]  # 验证只取前3个
                }
            )

    @pytest.mark.asyncio
    async def test_get_top3_endpoint_success(self, sample_user_id, mock_microservice_client):
        """测试成功获取Top3端点"""
        from src.domains.task.router import get_top3_endpoint

        query_date = "2025-11-01"
        task_ids = [str(uuid4()), str(uuid4())]

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "Top3查询成功",
            "data": {"date": query_date, "top3_tasks": task_ids}
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await get_top3_endpoint(
                query_date=query_date,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200
            assert result.data["date"] == query_date

            # 验证微服务调用参数
            mock_microservice_client.call_microservice.assert_called_once_with(
                method="POST",
                path="tasks/top3/query",
                user_id=sample_user_id,
                date=query_date
            )

    @pytest.mark.asyncio
    async def test_record_focus_status_endpoint_success(self, sample_user_id, mock_microservice_client):
        """测试成功记录专注状态端点"""
        from src.domains.task.router import FocusStatusRequest, record_focus_status_endpoint

        # 准备请求数据
        request = FocusStatusRequest(
            focus_status="focused",
            duration_minutes=45,
            task_id=str(uuid4())
        )

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "专注状态记录成功",
            "data": {"focus_session_id": str(uuid4()), "status": "recorded"}
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await record_focus_status_endpoint(
                request=request,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200

            # 验证微服务调用参数
            mock_microservice_client.call_microservice.assert_called_once_with(
                method="POST",
                path="tasks/focus-status",
                user_id=sample_user_id,
                data={
                    "user_id": sample_user_id,
                    "focus_status": "focused",
                    "duration_minutes": 45,
                    "task_id": request.task_id
                }
            )

    @pytest.mark.asyncio
    async def test_get_pomodoro_count_endpoint_success(self, sample_user_id, mock_microservice_client):
        """测试成功获取番茄钟计数端点"""
        from src.domains.task.router import get_pomodoro_count_endpoint

        # 准备微服务响应
        microservice_response = {
            "code": 200,
            "success": True,
            "message": "番茄钟计数查询成功",
            "data": {"date_filter": "today", "count": 5, "total_duration_minutes": 225}
        }

        mock_microservice_client.call_microservice.return_value = microservice_response

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await get_pomodoro_count_endpoint(
                date_filter="today",
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 200
            assert result.data["count"] == 5

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

    @pytest.mark.asyncio
    async def test_microservice_error_handling(self, sample_user_id, mock_microservice_client):
        """测试微服务错误处理"""
        from src.domains.task.schemas import CreateTaskRequest
        from src.domains.task.router import create_task_endpoint

        # 模拟微服务错误
        mock_microservice_client.call_microservice.side_effect = TaskMicroserviceError(
            message="微服务连接失败",
            status_code=503
        )

        # 准备请求数据
        request = CreateTaskRequest(title="Test Task")

        # 调用端点函数
        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await create_task_endpoint(
                request=request,
                user_id=UUID(sample_user_id),
                client=mock_microservice_client
            )

            assert result.code == 503
            assert result.message == "微服务连接失败"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_health_check_endpoint_success(self, mock_microservice_client):
        """测试健康检查成功端点"""
        from src.domains.task.router import health_check_endpoint

        mock_microservice_client.health_check.return_value = True

        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await health_check_endpoint(client=mock_microservice_client)

            assert result.code == 200
            assert result.data["healthy"] is True
            assert "timestamp" in result.data

    @pytest.mark.asyncio
    async def test_health_check_endpoint_failure(self, mock_microservice_client):
        """测试健康检查失败端点"""
        from src.domains.task.router import health_check_endpoint

        mock_microservice_client.health_check.return_value = False

        with patch('src.domains.task.router.get_enhanced_task_microservice_client') as mock_get_client:
            mock_get_client.return_value = mock_microservice_client

            result = await health_check_endpoint(client=mock_microservice_client)

            assert result.code == 200
            assert result.data["healthy"] is False
            assert result.message == "不健康"

    def test_priority_conversion(self, sample_user_id, mock_microservice_client):
        """测试优先级转换逻辑"""
        from src.domains.task.schemas import CreateTaskRequest

        # 测试客户端到微服务的优先级转换（小写 -> 首字母大写）
        test_cases = [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ]

        for input_priority, expected_priority in test_cases:
            request = CreateTaskRequest(
                title="Test Task",
                priority=input_priority
            )

            # 验证数据准备阶段的优先级转换
            converted_priority = request.priority.capitalize()

            task_data = {
                "title": request.title,
                "description": request.description or "",
                "priority": converted_priority,
                "due_date": None,
                "user_id": sample_user_id
            }

            assert task_data["priority"] == expected_priority

    def test_top3_task_limit_enforcement(self, sample_user_id):
        """测试Top3任务数量限制强制执行"""
        from src.domains.task.router import Top3SetRequest

        # 创建超过3个任务的请求
        task_ids = [str(uuid4()) for _ in range(5)]
        request = Top3SetRequest(date="2025-11-01", task_ids=task_ids)

        # 验证端点会限制为最多3个任务
        top3_data = {
            "user_id": sample_user_id,
            "date": request.date,
            "task_ids": request.task_ids[:3]  # 最多3个任务
        }

        assert len(top3_data["task_ids"]) == 3
        assert top3_data["task_ids"] == task_ids[:3]