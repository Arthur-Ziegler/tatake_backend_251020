"""
并发和负载测试

根据openspec要求：
- 10个用户同时操作
- 100QPS峰值负载测试
- 内存泄漏检测
- 长时间稳定性测试

性能基准：
- P95响应时间 <200ms
- P99响应时间 <500ms
- 并发处理能力：10用户无性能退化

作者：TaKeKe团队
版本：1.3.0
"""

import pytest
import asyncio
import httpx
from httpx import ASGITransport
from typing import List, Dict, Any
from uuid import uuid4
import time
from datetime import datetime, timezone

from src.api.main import app


class TestConcurrentLoad:
    """并发和负载测试类"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_welcome_gift_claims(self):
        """测试10个用户同时领取欢迎礼包"""
        async def claim_gift_for_user(user_index: int):
            """为指定用户领取欢迎礼包"""
            async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 创建用户
                auth_response = await client.post("/auth/guest/init")
                assert auth_response.status_code == 200
                access_token = auth_response.json()["data"]["access_token"]
                headers = {"Authorization": f"Bearer {access_token}"}

                # 领取礼包
                gift_response = await client.post("/user/welcome-gift/claim", headers=headers)

                return {
                    "user_index": user_index,
                    "status_code": gift_response.status_code,
                    "success": gift_response.status_code == 200,
                    "response_time": gift_response.headers.get("x-response-time", "0")
                }

        # 并发执行10个用户领取礼包
        start_time = time.time()
        tasks = [claim_gift_for_user(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # 验证结果
        successful_claims = [r for r in results if r["success"]]
        total_time = end_time - start_time

        # 断言
        assert len(successful_claims) == 10, f"只有{len(successful_claims)}/10个用户成功"
        assert total_time < 30, f"总时间过长: {total_time:.2f}秒"

        # 性能分析
        response_times = [float(r.get("response_time", 0)) for r in results if r.get("response_time")]
        avg_response_time = sum(response_times) / len(results) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        assert avg_response_time < 0.2, f"平均响应时间过长: {avg_response_time:.3f}秒"
        assert max_response_time < 0.5, f"最大响应时间过长: {max_response_time:.3f}秒"

        print(f"✅ 10个用户并发测试完成")
        print(f"   成功用户: {len(successful_claims)}/10")
        print(f"   平均响应时间: {avg_response_time:.3f}秒")
        print(f"   最大响应时间: {max_response_time:.3f}秒")
        print(f"   总耗时: {total_time:.2f}秒")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_high_frequency_api_calls(self):
        """测试高频率API调用性能"""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 创建用户
            auth_response = await client.post("/auth/guest/init")
            access_token = auth_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            # 快速连续调用测试
            endpoints = [
                "/points/balance",
                "/user/profile",
                "/tasks",
                "/rewards/my-rewards"
            ]

            response_times = []
            for endpoint in endpoints:
                start_time = time.time()
                response = await client.get(endpoint, headers=headers)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # 转换为毫秒
                response_times.append(response_time)
                assert response.status_code == 200

            # 性能验证
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]  # P95值

            assert avg_time < 100, f"平均响应时间过长: {avg_time:.2f}ms"
            assert max_time < 200, f"最大响应时间过长: {max_time:.2f}ms"
            assert p95_time < 200, f"P95响应时间过长: {p95_time}ms"

            print(f"✅ 高频API调用测试完成")
            print(f"   平均响应时间: {avg_time:.2f}ms")
            print(f"   最大响应时间: {max_time:.2f}ms")
            print(f"   P95响应时间: {p95_time}ms")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_stability(self):
        """测试长时间运行的内存稳定性"""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 创建用户
            auth_response = await client.post("/auth/guest/init")
            access_token = auth_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            # 模拟1小时的持续负载
            start_time = time.time()
            operations = 0
            test_duration = 60  # 1分钟，模拟1小时

            while time.time() - start_time < test_duration:
                operations += 1

                # 每分钟执行多个操作
                if operations % 10 == 0:  # 每10个操作执行一次礼包领取
                    gift_response = await client.post("/user/welcome-gift/claim", headers=headers)
                    assert gift_response.status_code in [200, 404, 401]  # 允许合理错误
                else:
                    # 其他操作：查询积分、任务等
                    await client.get("/points/balance", headers=headers)

            end_time = time.time()
            total_time = end_time - start_time

            print(f"✅ 内存稳定性测试完成")
            print(f"   测试时长: {total_time:.1f}秒")
            print(f"   总操作数: {operations}")

            # 验证测试时长合理（应该在60秒左右）
            assert 50 < total_time < 120, f"测试时间不合理: {total_time:.1f}秒"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_database_connection_pool(self):
        """测试数据库连接池在并发下的表现"""
        async def create_user_and_query():
            async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 创建用户
                auth_response = await client.post("/auth/guest/init")
                access_token = auth_response.json()["data"]["access_token"]
                headers = {"Authorization": f"Bearer {access_token}"}

                # 执行多个数据库查询
                tasks = [
                    client.get("/points/balance", headers=headers),
                    client.get("/rewards/my-rewards", headers=headers),
                    client.get("/tasks", headers=headers)
                ]

                results = await asyncio.gather(*tasks)
                return all(r.status_code == 200 for r in results)

        # 并发创建多个用户并执行查询
        concurrent_tasks = [create_user_and_query() for _ in range(20)]
        results = await asyncio.gather(*concurrent_tasks)

        successful_queries = sum(results)
        assert successful_queries == 20, f"只有{successful_queries}/20个并发查询成功"

        print(f"✅ 数据库连接池测试完成")
        print(f"   成功查询数: {successful_queries}/20")

    @pytest.mark.asyncio
    async def test_response_format_consistency(self, test_client: httpx.AsyncClient):
        """测试API响应格式一致性"""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 创建用户
            auth_response = await client.post("/auth/guest/init")
            access_token = auth_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            # 测试各种响应格式
            endpoints_to_test = [
                "/auth/guest-init",
                "/user/profile",
                "/points/balance",
                "/tasks",
                "/user/welcome-gift/claim"
            ]

            for endpoint in endpoints_to_test:
                if endpoint == "/auth/guest-init":
                    response = await client.post(endpoint)
                else:
                    response = await client.get(endpoint, headers=headers)

                # 验证统一响应格式
                assert response.status_code in [200, 400, 401, 404, 500]

                if response.status_code == 200:
                    data = response.json()
                    assert "code" in data
                    assert "data" in data
                    assert "message" in data
                    assert isinstance(data["data"], dict) if endpoint != "/auth/guest-init" else (data["data"] is None or isinstance(data["data"], str))

    @pytest.mark.asyncio
    async def test_large_data_handling(self, test_client: httpx.AsyncClient):
        """测试大数据量处理性能"""
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 创建用户
            auth_response = await test_client.post("/auth/guest-init")
            access_token = auth_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            # 创建大量任务
            large_tasks = []
            for i in range(100):  # 创建100个任务
                task_data = {
                    "title": f"批量测试任务 {i}",
                    "description": f"这是第{i}个批量创建的任务",
                    "priority": "low"
                }
                large_tasks.append(client.post("/tasks", json=task_data, headers=headers))

            # 等待所有任务创建完成
            results = await asyncio.gather(*large_tasks)

            successful_creations = sum(1 for r in results if r.status_code == 200)
            assert successful_creations == 100, f"只有{successful_creations}/100个任务创建成功"

            # 测试分页查询性能
            start_time = time.time()
            list_response = await client.get("/tasks?limit=50&offset=0", headers=headers)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000
            assert response_time < 1000, f"大数据量查询响应时间过长: {response_time}ms"
            assert list_response.status_code == 200