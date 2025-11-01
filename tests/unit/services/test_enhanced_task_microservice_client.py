"""
增强版Task微服务客户端单元测试

测试路径映射、UUID验证、错误处理和响应透传等核心功能。
遵循TDD原则，每个测试用例独立且覆盖完整的业务场景。

测试覆盖：
- 路径映射逻辑
- UUID格式验证
- 错误处理策略
- 连接池管理
- 重试机制

作者：TaTakeKe团队
版本：1.0.0
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from typing import Dict, Any
import httpx

from src.services.enhanced_task_microservice_client import (
    EnhancedTaskMicroserviceClient,
    UUIDValidator,
    TaskMicroserviceError,
    ConnectionPoolManager,
    ErrorHandlingStrategy
)


class TestUUIDValidator:
    """UUID验证器测试"""

    def test_validate_valid_user_id(self):
        """测试有效用户ID验证"""
        valid_uuid = str(uuid4())
        result = UUIDValidator.validate_user_id(valid_uuid)
        assert result == valid_uuid

    def test_validate_valid_task_id(self):
        """测试有效任务ID验证"""
        valid_uuid = str(uuid4())
        result = UUIDValidator.validate_task_id(valid_uuid)
        assert result == valid_uuid

    def test_validate_invalid_uuid_format(self):
        """测试无效UUID格式"""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            UUIDValidator.validate_user_id("invalid-uuid")

        with pytest.raises(ValueError, match="Invalid UUID format"):
            UUIDValidator.validate_task_id("test-user-123")

    def test_validate_empty_user_id(self):
        """测试空用户ID"""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            UUIDValidator.validate_user_id("")

        with pytest.raises(ValueError, match="user_id cannot be empty"):
            UUIDValidator.validate_user_id(None)

    def test_validate_empty_task_id(self):
        """测试空任务ID"""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            UUIDValidator.validate_task_id("")

        with pytest.raises(ValueError, match="task_id cannot be empty"):
            UUIDValidator.validate_task_id(None)


class TestEnhancedTaskMicroserviceClient:
    """增强版Task微服务客户端测试"""

    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        return EnhancedTaskMicroserviceClient()

    @pytest.fixture
    def sample_user_id(self):
        """示例用户ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_task_id(self):
        """示例任务ID"""
        return str(uuid4())

    def test_build_path_mappings(self, client):
        """测试路径映射表构建"""
        mappings = client._build_path_mappings()

        # 验证关键路径映射存在
        assert ("POST", "tasks/query") in mappings
        assert ("PUT", "tasks/{task_id}") in mappings
        assert ("DELETE", "tasks/{task_id}") in mappings
        assert ("POST", "tasks/{task_id}/complete") in mappings
        assert ("POST", "tasks/top3/query") in mappings
        assert ("POST", "tasks/focus-status") in mappings
        assert ("GET", "tasks/pomodoro-count") in mappings

    def test_rewrite_path_query_tasks(self, client, sample_user_id):
        """测试查询任务路径重写"""
        new_path = client.rewrite_path("POST", "tasks/query", sample_user_id)
        assert new_path == f"tasks/{sample_user_id}"

    def test_rewrite_path_single_task_with_task_id(self, client, sample_user_id, sample_task_id):
        """测试单个任务操作路径重写（带task_id）"""
        new_path = client.rewrite_path(
            "PUT", "tasks/{task_id}", sample_user_id, task_id=sample_task_id
        )
        assert new_path == f"tasks/{sample_user_id}/{sample_task_id}"

    def test_rewrite_path_single_task_without_task_id(self, client, sample_user_id):
        """测试单个任务操作路径重写（缺少task_id）"""
        with pytest.raises(ValueError, match="task_id is required"):
            client.rewrite_path("PUT", "tasks/{task_id}", sample_user_id)

    def test_rewrite_path_complete_task(self, client, sample_user_id, sample_task_id):
        """测试任务完成路径重写"""
        new_path = client.rewrite_path(
            "POST", "tasks/{task_id}/complete", sample_user_id, task_id=sample_task_id
        )
        assert new_path == f"tasks/{sample_user_id}/{sample_task_id}/complete"

    def test_rewrite_path_top3_query(self, client, sample_user_id):
        """测试Top3查询路径重写"""
        test_date = "2025-11-01"
        new_path = client.rewrite_path(
            "POST", "tasks/top3/query", sample_user_id, date=test_date
        )
        assert new_path == f"tasks/top3/{sample_user_id}/{test_date}"

    def test_rewrite_path_top3_query_without_date(self, client, sample_user_id):
        """测试Top3查询路径重写（缺少date）"""
        with pytest.raises(ValueError, match="date is required"):
            client.rewrite_path("POST", "tasks/top3/query", sample_user_id)

    def test_rewrite_path_unmapped(self, client, sample_user_id):
        """测试未映射路径"""
        original_path = "tasks/some/other/path"
        new_path = client.rewrite_path("GET", original_path, sample_user_id)
        assert new_path == original_path

    def test_rewrite_path_focus_status(self, client, sample_user_id):
        """测试专注状态路径重写"""
        new_path = client.rewrite_path("POST", "tasks/focus-status", sample_user_id)
        assert new_path == "focus/sessions"

    def test_rewrite_path_pomodoro_count(self, client, sample_user_id):
        """测试番茄钟计数路径重写"""
        new_path = client.rewrite_path("GET", "tasks/pomodoro-count", sample_user_id)
        assert new_path == "pomodoros/count"

    @pytest.mark.asyncio
    async def test_call_microservice_success(self, client, sample_user_id):
        """测试微服务调用成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "success": True,
            "message": "success",
            "data": {"id": str(uuid4())}
        }
        mock_response.status_code = 200

        with patch.object(client.connection_pool, 'get_client') as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response

            result = await client.call_microservice(
                "POST", "tasks", sample_user_id, {"title": "Test Task"}
            )

            assert result["code"] == 200
            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_call_microservice_with_uuid_validation(self, client):
        """测试微服务调用UUID验证"""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            await client.call_microservice(
                "POST", "tasks", "invalid-uuid", {"title": "Test Task"}
            )

    @pytest.mark.asyncio
    async def test_call_microservice_connection_error(self, client, sample_user_id):
        """测试微服务连接错误"""
        with patch.object(client.connection_pool, 'get_client') as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.request.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(TaskMicroserviceError) as exc_info:
                await client.call_microservice(
                    "POST", "tasks", sample_user_id, {"title": "Test Task"}
                )

            assert exc_info.value.status_code == 503
            assert "连接失败" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_call_microservice_timeout_error(self, client, sample_user_id):
        """测试微服务超时错误"""
        with patch.object(client.connection_pool, 'get_client') as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.request.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(TaskMicroserviceError) as exc_info:
                await client.call_microservice(
                    "POST", "tasks", sample_user_id, {"title": "Test Task"}
                )

            assert exc_info.value.status_code == 504
            assert "超时" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_call_microservice_http_error(self, client, sample_user_id):
        """测试微服务HTTP错误"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 404,
            "success": False,
            "message": "Task not found",
            "data": None
        }
        mock_response.status_code = 404

        with patch.object(client.connection_pool, 'get_client') as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.request.return_value = mock_response

            result = await client.call_microservice(
                "GET", "tasks/invalid-id", sample_user_id
            )

            assert result["code"] == 404
            assert result["success"] is False

    def test_get_headers(self, client):
        """测试获取请求头"""
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers

    def test_base_url_configuration(self):
        """测试基础URL配置"""
        # 测试默认配置
        client = EnhancedTaskMicroserviceClient()
        # 使用config中的默认值或环境变量值
        expected_urls = ["http://45.152.65.130:20253", "http://127.0.0.1:20252/api/v1"]
        assert any(url in client.base_url for url in expected_urls)

        # 测试自定义配置
        custom_url = "http://custom.example.com/api/v1"
        custom_client = EnhancedTaskMicroserviceClient(base_url=custom_url)
        assert custom_client.base_url == custom_url


class TestConnectionPoolManager:
    """连接池管理器测试"""

    def test_connection_pool_initialization(self):
        """测试连接池初始化"""
        pool_manager = ConnectionPoolManager()
        assert pool_manager.client is not None
        assert hasattr(pool_manager.client, 'request')

    @pytest.mark.asyncio
    async def test_connection_pool_close(self):
        """测试连接池关闭"""
        pool_manager = ConnectionPoolManager()

        # 模拟aclose方法
        pool_manager.client.aclose = AsyncMock()

        await pool_manager.close()
        pool_manager.client.aclose.assert_called_once()


class TestErrorHandlingStrategy:
    """错误处理策略测试"""

    def test_handle_connect_error(self):
        """测试连接错误处理"""
        error = httpx.ConnectError("Connection failed")
        result = ErrorHandlingStrategy.handle_network_error(error)

        assert isinstance(result, TaskMicroserviceError)
        assert result.status_code == 503
        assert result.is_recoverable is True
        assert "连接失败" in result.message

    def test_handle_timeout_error(self):
        """测试超时错误处理"""
        error = httpx.TimeoutException("Request timeout")
        result = ErrorHandlingStrategy.handle_network_error(error)

        assert isinstance(result, TaskMicroserviceError)
        assert result.status_code == 504
        assert result.is_recoverable is True
        assert "超时" in result.message

    def test_handle_generic_network_error(self):
        """测试通用网络错误处理"""
        error = Exception("Generic network error")
        result = ErrorHandlingStrategy.handle_network_error(error)

        assert isinstance(result, TaskMicroserviceError)
        assert result.status_code == 500
        assert result.is_recoverable is True
        assert "网络异常" in result.message


class TestIntegrationScenarios:
    """集成场景测试"""

    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        return EnhancedTaskMicroserviceClient()

    @pytest.fixture
    def sample_user_id(self):
        """示例用户ID"""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_complete_task_crud_flow(self, client, sample_user_id):
        """测试完整任务CRUD流程"""
        # 模拟创建任务响应
        create_response = MagicMock()
        create_response.json.return_value = {
            "code": 201,
            "success": True,
            "message": "任务创建成功",
            "data": {"id": str(uuid4()), "title": "Test Task", "status": "pending"}
        }
        create_response.status_code = 201

        # 模拟查询任务响应
        query_response = MagicMock()
        query_response.json.return_value = {
            "code": 200,
            "success": True,
            "message": "查询成功",
            "data": [{"id": str(uuid4()), "title": "Test Task", "status": "pending"}]
        }
        query_response.status_code = 200

        with patch.object(client.connection_pool, 'get_client') as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_get_client.return_value = mock_client_instance

            # 模拟不同请求的不同响应
            mock_client_instance.request.side_effect = [create_response, query_response]

            # 创建任务
            create_result = await client.call_microservice(
                "POST", "tasks", sample_user_id, {"title": "Test Task"}
            )
            assert create_result["code"] == 201
            assert create_result["success"] is True

            # 查询任务
            query_result = await client.call_microservice(
                "POST", "tasks/query", sample_user_id
            )
            assert query_result["code"] == 200
            assert query_result["success"] is True
            assert len(query_result["data"]) == 1

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, client, sample_user_id):
        """测试错误恢复流程"""
        # 第一次请求失败，第二次成功
        failing_response = MagicMock()
        failing_response.status_code = 503

        success_response = MagicMock()
        success_response.json.return_value = {
            "code": 200,
            "success": True,
            "message": "success",
            "data": {"id": str(uuid4())}
        }
        success_response.status_code = 200

        with patch.object(client.connection_pool, 'get_client') as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.request.side_effect = [failing_response, success_response]

            # 第一次调用失败
            with pytest.raises(TaskMicroserviceError):
                await client.call_microservice(
                    "POST", "tasks", sample_user_id, {"title": "Test Task"}
                )

            # 第二次调用成功
            result = await client.call_microservice(
                "POST", "tasks", sample_user_id, {"title": "Test Task"}
            )
            assert result["code"] == 200