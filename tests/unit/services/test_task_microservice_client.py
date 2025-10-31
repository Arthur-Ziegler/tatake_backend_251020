"""
Task微服务客户端单元测试

测试Task微服务客户端的各项功能，包括：
1. HTTP调用封装
2. 响应格式转换
3. 错误处理机制
4. 超时配置

测试策略：
1. Mock微服务HTTP调用
2. 验证响应格式转换
3. 测试各种错误场景
4. 确保异常处理正确

作者：TaKeKe团队
版本：1.0.0（Task微服务迁移）
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

import httpx
from pydantic import BaseModel

from src.services.task_microservice_client import (
    TaskMicroserviceClient,
    TaskMicroserviceError,
    call_task_service,
    get_task_microservice_client
)


class TestTaskMicroserviceClient:
    """Task微服务客户端测试类"""

    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        return TaskMicroserviceClient("http://test-microservice:20252/api/v1")

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient"""
        mock_client = AsyncMock()
        return mock_client

    @pytest.fixture
    def sample_success_response(self):
        """示例成功响应"""
        return {
            "success": True,
            "data": {
                "id": str(uuid4()),
                "title": "测试任务",
                "status": "pending",
                "priority": "medium",
                "created_at": datetime.now().isoformat()
            }
        }

    @pytest.fixture
    def sample_error_response(self):
        """示例错误响应"""
        return {
            "success": False,
            "message": "任务不存在",
            "code": 404
        }

    @pytest.mark.asyncio
    async def test_transform_response_success(self, client, sample_success_response):
        """测试成功响应格式转换"""
        result = client.transform_response(sample_success_response)

        assert result["code"] == 200
        assert result["data"] == sample_success_response["data"]
        assert result["message"] == "success"

    @pytest.mark.asyncio
    async def test_transform_response_error(self, client, sample_error_response):
        """测试错误响应格式转换"""
        result = client.transform_response(sample_error_response)

        assert result["code"] == 404
        assert result["data"] is None
        assert result["message"] == "任务不存在"

    @pytest.mark.asyncio
    async def test_transform_response_invalid_format(self, client):
        """测试无效响应格式"""
        invalid_response = "invalid response"

        with pytest.raises(TaskMicroserviceError) as exc_info:
            client.transform_response(invalid_response)

        assert "响应格式转换失败" in str(exc_info.value)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_map_error_status(self, client):
        """测试HTTP状态码映射"""
        # 测试各种HTTP状态码
        test_cases = [
            (400, {}, 400),
            (401, {}, 401),
            (403, {}, 403),
            (404, {}, 404),
            (409, {}, 409),
            (422, {}, 422),
            (500, {}, 500),
            (502, {}, 500),
            (503, {}, 500),
        ]

        for http_status, error_content, expected_code in test_cases:
            result = client.map_error_status(http_status, error_content)
            assert result == expected_code

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.httpx.AsyncClient')
    async def test_call_task_service_success(self, mock_client_class, client, sample_success_response):
        """测试成功调用微服务"""
        # 设置Mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_success_response

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 执行调用
        result = await client.call_task_service(
            method="POST",
            path="tasks",
            user_id=str(uuid4()),
            data={"title": "测试任务"}
        )

        # 验证结果
        assert result["code"] == 200
        assert result["data"] == sample_success_response["data"]
        assert result["message"] == "success"

        # 验证HTTP调用参数
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "tasks" in call_args[1]["url"]
        assert call_args[1]["json"]["title"] == "测试任务"

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.httpx.AsyncClient')
    async def test_call_task_service_microservice_error(self, mock_client_class, client, sample_error_response):
        """测试微服务返回错误"""
        # 设置Mock
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = sample_error_response

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 执行调用
        result = await client.call_task_service(
            method="GET",
            path="tasks/invalid-id",
            user_id=str(uuid4())
        )

        # 验证结果
        assert result["code"] == 404
        assert result["data"] is None
        assert result["message"] == "任务不存在"

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.httpx.AsyncClient')
    async def test_call_task_service_timeout_error(self, mock_client_class, client):
        """测试微服务调用超时"""
        # 设置Mock
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 执行调用并验证异常
        with pytest.raises(TaskMicroserviceError) as exc_info:
            await client.call_task_service(
                method="GET",
                path="tasks",
                user_id=str(uuid4())
            )

        assert exc_info.value.status_code == 504
        assert "超时" in exc_info.value.message

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.httpx.AsyncClient')
    async def test_call_task_service_connection_error(self, mock_client_class, client):
        """测试微服务连接失败"""
        # 设置Mock
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 执行调用并验证异常
        with pytest.raises(TaskMicroserviceError) as exc_info:
            await client.call_task_service(
                method="GET",
                path="tasks",
                user_id=str(uuid4())
            )

        assert exc_info.value.status_code == 503
        assert "不可用" in exc_info.value.message

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.httpx.AsyncClient')
    async def test_call_task_service_with_params(self, mock_client_class, client, sample_success_response):
        """测试带查询参数的微服务调用"""
        # 设置Mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_success_response

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 执行调用
        user_id = str(uuid4())
        result = await client.call_task_service(
            method="GET",
            path="tasks",
            user_id=user_id,
            params={"page": 1, "page_size": 20}
        )

        # 验证结果
        assert result["code"] == 200

        # 验证查询参数包含user_id
        call_args = mock_client.request.call_args
        params = call_args[1]["params"]
        assert params["user_id"] == user_id
        assert params["page"] == 1
        assert params["page_size"] == 20

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.httpx.AsyncClient')
    async def test_health_check_success(self, mock_client_class, client):
        """测试健康检查成功"""
        # 设置Mock
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 执行健康检查
        result = await client.health_check()

        # 验证结果
        assert result is True
        mock_client.get.assert_called_once_with(f"{client.base_url}/health", headers=client._get_headers())

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.httpx.AsyncClient')
    async def test_health_check_failure(self, mock_client_class, client):
        """测试健康检查失败"""
        # 设置Mock
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # 执行健康检查
        result = await client.health_check()

        # 验证结果
        assert result is False

    def test_get_headers(self, client):
        """测试获取请求头"""
        headers = client._get_headers()

        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Accept" in headers
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers
        assert "TaKeKe-Backend" in headers["User-Agent"]


class TestTaskMicroserviceClientGlobal:
    """测试全局客户端实例和便捷函数"""

    @patch('src.services.task_microservice_client.TaskMicroserviceClient')
    def test_get_task_microservice_client(self, mock_client_class):
        """测试获取全局客户端实例"""
        # 首次调用
        client1 = get_task_microservice_client()
        # 第二次调用
        client2 = get_task_microservice_client()

        # 验证只创建一次实例
        mock_client_class.assert_called_once()
        assert client1 is client2

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.get_task_microservice_client')
    async def test_call_task_service_convenience_function(self, mock_get_client):
        """测试便捷函数"""
        # 设置Mock
        mock_client = MagicMock()
        mock_client.call_task_service = AsyncMock(return_value={"code": 200, "data": {}, "message": "success"})
        mock_get_client.return_value = mock_client

        # 调用便捷函数
        user_id = str(uuid4())
        result = await call_task_service(
            method="POST",
            path="tasks",
            user_id=user_id,
            data={"title": "测试"}
        )

        # 验证结果
        assert result["code"] == 200
        mock_client.call_task_service.assert_called_once_with(
            "POST",
            "tasks",
            user_id,
            {"title": "测试"},
            None
        )

    @pytest.mark.asyncio
    @patch('src.services.task_microservice_client.get_task_microservice_client')
    async def test_call_task_service_convenience_function_with_params(self, mock_get_client):
        """测试带参数的便捷函数"""
        # 设置Mock
        mock_client = MagicMock()
        mock_client.call_task_service = AsyncMock(return_value={"code": 200, "data": {}, "message": "success"})
        mock_get_client.return_value = mock_client

        # 调用便捷函数
        user_id = str(uuid4())
        result = await call_task_service(
            method="GET",
            path="tasks",
            user_id=user_id,
            params={"page": 1}
        )

        # 验证结果
        assert result["code"] == 200
        mock_client.call_task_service.assert_called_once_with(
            "GET",
            "tasks",
            user_id,
            None,
            {"page": 1}
        )


class TestTaskMicroserviceClientIntegration:
    """集成测试类"""

    @pytest.mark.asyncio
    async def test_client_initialization_with_config(self):
        """测试客户端从配置初始化"""
        # 这里可以测试从环境配置文件读取URL的初始化
        client = TaskMicroserviceClient()
        assert client.base_url is not None
        assert "20252" in client.base_url  # 确保包含微服务端口

    @pytest.mark.asyncio
    async def test_client_timeout_configuration(self):
        """测试客户端超时配置"""
        client = TaskMicroserviceClient()
        timeout = client.timeout

        assert timeout.connect == 5.0
        assert timeout.read == 30.0
        assert timeout.write == 10.0
        assert timeout.pool == 60.0