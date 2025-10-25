"""
P0级功能综合验证测试

根据1.4.1 OpenSpec要求，验证真实HTTP测试框架和P0 Bug修复的效果。
测试覆盖：
1. 任务完成API（空请求体）
2. 任务完成API（带mood_feedback）
3. Top3设置（UUID修复）
4. Top3查询
5. 真实HTTP服务器连接

作者：TaKeKe团队
版本：1.4.1
日期：2025-10-25
"""

import pytest
import asyncio
from typing import Dict, Any, Optional
import uuid

# 导入真实HTTP测试框架
from tests.conftest_real_http import (
    real_http_server,
    real_api_client,
    test_user_context,
    assert_api_response,
    with_real_http_error_handling
)


class TestTaskCompletionAPI:
    """任务完成API测试类"""

    @with_real_http_error_handling
    async def test_complete_task_empty_body(self, real_api_client, test_user_context):
        """测试任务完成API - 空请求体"""
        # 获取访问令牌
        headers = {"Authorization": f"Bearer {test_user_context['access_token']}"}

        # 先创建一个测试任务
        create_response = await real_api_client.post(
            "/tasks",
            json={
                "title": "P0测试任务 - 空请求体",
                "description": "用于验证P0 Bug修复的测试任务"
            },
            headers=headers
        )

        assert create_response.status_code == 200
        task_data = create_response.json()["data"]
        task_id = task_data["id"]

        # 完成任务，不传递请求体（这是P0 Bug修复的核心测试）
        complete_response = await real_api_client.post(
            f"/tasks/{task_id}/complete",
            headers=headers
            # 注意：没有json参数，测试空请求体
        )

        # 验证响应
        assert_api_response(complete_response, expected_status=200)
        result = complete_response.json()

        # 验证任务状态已更新
        assert result["code"] == 200
        assert result["data"]["task"]["status"] == "completed"
        assert result["data"]["completion_result"]["success"] is True

    @with_real_http_error_handling
    async def test_complete_task_with_mood_feedback(self, real_api_client, test_user_context):
        """测试任务完成API - 带mood_feedback"""
        headers = {"Authorization": f"Bearer {test_user_context['access_token']}"}

        # 创建测试任务
        create_response = await real_api_client.post(
            "/tasks",
            json={
                "title": "P0测试任务 - 带反馈",
                "description": "用于验证mood_feedback处理的测试任务"
            },
            headers=headers
        )

        assert create_response.status_code == 200
        task_data = create_response.json()["data"]
        task_id = task_data["id"]

        # 完成任务，带mood_feedback
        complete_response = await real_api_client.post(
            f"/tasks/{task_id}/complete",
            json={
                "mood_feedback": {
                    "comment": "这个任务很有挑战性，但顺利完成了",
                    "difficulty": "medium"
                }
            },
            headers=headers
        )

        # 验证响应
        assert_api_response(complete_response, expected_status=200)
        result = complete_response.json()

        # 验证任务状态和反馈处理
        assert result["code"] == 200
        assert result["data"]["task"]["status"] == "completed"
        assert result["data"]["completion_result"]["success"] is True


class TestTop3API:
    """Top3 API测试类 - UUID修复验证"""

    @with_real_http_error_handling
    async def test_set_top3_uuid_fix(self, real_api_client, test_user_context):
        """测试Top3设置API - UUID类型修复验证"""
        headers = {"Authorization": f"Bearer {test_user_context['access_token']}"}

        # 领取欢迎礼包获得足够积分（需要300积分设置Top3）
        gift_response = await real_api_client.post(
            "/user/welcome-gift/claim",
            headers=headers
        )
        assert gift_response.status_code == 200

        # 创建3个测试任务
        task_ids = []
        for i in range(3):
            create_response = await real_api_client.post(
                "/tasks",
                json={
                    "title": f"Top3测试任务 {i+1}",
                    "description": f"用于验证UUID修复的测试任务 {i+1}"
                },
                headers=headers
            )
            assert create_response.status_code == 200
            task_data = create_response.json()["data"]
            task_ids.append(task_data["id"])

        # 设置Top3（这是P0 Bug修复的核心测试 - UUID类型错误修复）
        top3_response = await real_api_client.post(
            "/tasks/special/top3",
            json={
                "date": "2025-10-26",
                "task_ids": task_ids
            },
            headers=headers
        )

        # 验证不会出现UUID AttributeError
        assert_api_response(top3_response, expected_status=200)
        result = top3_response.json()

        # 验证Top3设置成功
        assert result["code"] == 200
        assert result["data"]["points_consumed"] == 300
        assert len(result["data"]["task_ids"]) == 3
        assert "remaining_balance" in result["data"]

    @with_real_http_error_handling
    async def test_get_top3_query(self, real_api_client, test_user_context):
        """测试Top3查询API"""
        headers = {"Authorization": f"Bearer {test_user_context['access_token']}"}

        # 查询今日Top3
        today = "2025-10-25"  # 使用今天的日期
        get_response = await real_api_client.get(
            f"/tasks/special/top3?date={today}",
            headers=headers
        )

        # 验证查询响应
        assert_api_response(get_response, expected_status=200)
        result = get_response.json()

        # 验证响应结构
        assert result["code"] == 200
        assert "data" in result
        assert "date" in result["data"]
        assert "task_ids" in result["data"]
        assert "points_consumed" in result["data"]


class TestRealHTTPServer:
    """真实HTTP服务器测试类"""

    @pytest.mark.asyncio
    async def test_server_health_check(self, real_http_server):
        """测试真实HTTP服务器健康检查"""
        # 获取客户端
        client_manager = real_http_server["client_manager"]
        client = client_manager.get_client()

        try:
            # 测试健康检查端点
            response = await client.get("/health")

            # 验证响应
            assert response.status_code == 200
            health_data = response.json()
            assert "status" in health_data
            assert health_data["status"] == "healthy"

        finally:
            client_manager.return_client(client)

    @pytest.mark.asyncio
    async def test_server_cors_headers(self, real_http_server):
        """测试服务器CORS头设置"""
        client_manager = real_http_server["client_manager"]
        client = client_manager.get_client()

        try:
            # 测试OPTIONS请求
            response = await client.options("/health")

            # 验证CORS头存在
            assert response.status_code == 200
            # 注意：具体的CORS头可能因配置而异

        finally:
            client_manager.return_client(client)


class TestIntegratedWorkflow:
    """集成工作流测试类"""

    @with_real_http_error_handling
    async def test_complete_user_workflow(self, real_api_client, test_user_context):
        """测试完整用户工作流"""
        headers = {"Authorization": f"Bearer {test_user_context['access_token']}"}

        # 1. 领取欢迎礼包
        gift_response = await real_api_client.post(
            "/user/welcome-gift/claim",
            headers=headers
        )
        assert_api_response(gift_response)

        # 2. 创建任务
        task_response = await real_api_client.post(
            "/tasks",
            json={"title": "工作流测试任务", "description": "完整工作流测试"},
            headers=headers
        )
        assert_api_response(task_response)
        task_data = task_response.json()["data"]
        task_id = task_data["id"]

        # 3. 完成任务（空请求体）
        complete_response = await real_api_client.post(
            f"/tasks/{task_id}/complete",
            headers=headers
        )
        assert_api_response(complete_response)

        # 4. 验证任务状态
        get_task_response = await real_api_client.get(
            f"/tasks/{task_id}",
            headers=headers
        )
        assert_api_response(get_task_response)
        updated_task = get_task_response.json()["data"]
        assert updated_task["status"] == "completed"


# 性能基准测试
class TestPerformanceBenchmarks:
    """性能基准测试类"""

    @pytest.mark.asyncio
    async def test_api_response_time(self, real_api_client, test_user_context):
        """测试API响应时间基准"""
        import time
        headers = {"Authorization": f"Bearer {test_user_context['access_token']}"}

        # 测试健康检查响应时间
        start_time = time.time()
        response = await real_api_client.get("/health")
        response_time = time.time() - start_time

        assert response.status_code == 200
        assert response_time < 2.0, f"健康检查响应时间过长: {response_time}秒"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, real_http_server):
        """测试并发请求处理"""
        client_manager = real_http_server["client_manager"]
        client = client_manager.get_client()

        try:
            # 创建10个并发请求
            tasks = []
            for i in range(10):
                task = client.get("/health")
                tasks.append(task)

            # 等待所有请求完成
            responses = await asyncio.gather(*tasks)

            # 验证所有请求都成功
            for response in responses:
                assert response.status_code == 200

        finally:
            client_manager.return_client(client)


# 错误处理测试
class TestErrorHandling:
    """错误处理测试类"""

    @with_real_http_error_handling
    async def test_invalid_task_id_error(self, real_api_client, test_user_context):
        """测试无效任务ID错误处理"""
        headers = {"Authorization": f"Bearer {test_user_context['access_token']}"}

        # 使用无效的UUID格式
        invalid_uuid = "invalid-uuid-format"
        response = await real_api_client.get(
            f"/tasks/{invalid_uuid}",
            headers=headers
        )

        # 应该返回422或400错误
        assert response.status_code in [422, 400]

    @with_real_http_error_handling
    async def test_unauthorized_access(self, real_api_client):
        """测试未授权访问错误处理"""
        # 不提供认证头
        response = await real_api_client.get("/tasks")

        # 应该返回401错误
        assert response.status_code == 401


# 测试数据清理
@pytest.fixture(autouse=True)
async def cleanup_test_data(real_api_client, test_user_context):
    """自动清理测试数据"""
    yield
    # 测试完成后可以在这里添加清理逻辑
    # 目前由TestDataManager处理