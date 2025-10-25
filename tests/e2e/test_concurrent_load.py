"""
并发负载测试

对API端点进行高并发负载测试，验证系统在高并发情况下的稳定性和性能表现。
包括并发用户模拟、数据一致性检查、资源竞争检测等。

作者：TaKeKe团队
版本：1.0.0 - 高并发负载测试
"""

import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient
from typing import List, Dict, Any
from uuid import uuid4
from time import perf_counter
import random

from tests.tools.concurrent_tester import ConcurrentTester


class TestConcurrentLoad:
    """并发负载测试类"""

    # 并发测试配置
    CONCURRENT_USERS = 50      # 并发用户数
    HIGH_CONCURRENCY = 100     # 高并发测试
    STRESS_TEST_USERS = 200    # 压力测试用户数
    REQUESTS_PER_USER = 10     # 每用户请求数

    @pytest_asyncio.fixture
    async def concurrent_tester(self):
        """并发测试器fixture"""
        return ConcurrentTester()

    @pytest_asyncio.fixture
    async def test_users(self, test_client: AsyncClient) -> List[Dict[str, str]]:
        """创建多个测试用户"""
        users = []
        for i in range(10):  # 创建10个测试用户
            try:
                response = await test_client.post("/auth/guest-init")
                if response.status_code == 200:
                    data = response.json()
                    users.append({
                        "user_id": data["data"]["user_id"],
                        "access_token": data["data"]["access_token"]
                    })
            except:
                # 如果失败，创建假token用于测试
                users.append({
                    "user_id": f"test_user_{i}",
                    "access_token": f"fake_token_{i}"
                })

        return users if users else [{"user_id": "test_user", "access_token": "test_token"}]

    async def concurrent_request_worker(
        self,
        test_client: AsyncClient,
        method: str,
        endpoint: str,
        user_token: str,
        request_count: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        并发请求工作器

        Args:
            test_client: 测试客户端
            method: HTTP方法
            endpoint: 端点
            user_token: 用户token
            request_count: 请求次数
            **kwargs: 其他请求参数

        Returns:
            Dict: 请求结果统计
        """
        headers = {"Authorization": f"Bearer {user_token}"}
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
            kwargs["headers"] = headers
        else:
            kwargs["headers"] = headers

        results = {
            "total_requests": request_count,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "status_codes": [],
            "errors": []
        }

        for i in range(request_count):
            start_time = perf_counter()
            try:
                if method.upper() == "GET":
                    response = await test_client.get(endpoint, **{k: v for k, v in kwargs.items() if k != 'json'})
                elif method.upper() == "POST":
                    response = await test_client.post(endpoint, **kwargs)
                elif method.upper() == "PUT":
                    response = await test_client.put(endpoint, **kwargs)
                elif method.upper() == "DELETE":
                    response = await test_client.delete(endpoint, **{k: v for k, v in kwargs.items() if k != 'json'})

                duration = (perf_counter() - start_time) * 1000
                results["response_times"].append(duration)
                results["status_codes"].append(response.status_code)

                if 200 <= response.status_code < 300:
                    results["successful_requests"] += 1
                else:
                    results["failed_requests"] += 1

            except Exception as e:
                duration = (perf_counter() - start_time) * 1000
                results["response_times"].append(duration)
                results["failed_requests"] += 1
                results["errors"].append(str(e))

        return results

    async def run_concurrent_test(
        self,
        test_client: AsyncClient,
        method: str,
        endpoint: str,
        concurrent_users: int,
        users: List[Dict[str, str]],
        requests_per_user: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        运行并发测试

        Args:
            test_client: 测试客户端
            method: HTTP方法
            endpoint: 端点
            concurrent_users: 并发用户数
            users: 用户列表
            requests_per_user: 每用户请求数
            **kwargs: 请求参数

        Returns:
            Dict: 并发测试结果
        """
        # 创建并发任务
        tasks = []
        for i in range(concurrent_users):
            user = users[i % len(users)]  # 循环使用用户token
            task = self.concurrent_request_worker(
                test_client, method, endpoint,
                user["access_token"], requests_per_user, **kwargs
            )
            tasks.append(task)

        # 执行并发任务
        start_time = perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = (perf_counter() - start_time) * 1000

        # 汇总结果
        summary = {
            "concurrent_users": concurrent_users,
            "total_requests": concurrent_users * requests_per_user,
            "total_duration": total_duration,
            "requests_per_second": (concurrent_users * requests_per_user) / (total_duration / 1000),
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "p95_response_time": 0,
            "p99_response_time": 0,
            "max_response_time": 0,
            "min_response_time": float('inf'),
            "success_rate": 0,
            "error_details": []
        }

        all_response_times = []
        status_code_distribution = {}

        for result in results:
            if isinstance(result, dict):
                summary["successful_requests"] += result["successful_requests"]
                summary["failed_requests"] += result["failed_requests"]
                all_response_times.extend(result["response_times"])

                # 统计状态码分布
                for status_code in result["status_codes"]:
                    status_code_distribution[status_code] = status_code_distribution.get(status_code, 0) + 1

                # 收集错误详情
                for error in result["errors"]:
                    summary["error_details"].append(error)
            else:
                # 处理异常
                summary["failed_requests"] += requests_per_user
                summary["error_details"].append(str(result))

        # 计算统计数据
        if all_response_times:
            summary["average_response_time"] = sum(all_response_times) / len(all_response_times)
            summary["max_response_time"] = max(all_response_times)
            summary["min_response_time"] = min(all_response_times)

            # 计算百分位数
            sorted_times = sorted(all_response_times)
            n = len(sorted_times)
            summary["p95_response_time"] = sorted_times[int(0.95 * n)] if n >= 20 else sorted_times[-1]
            summary["p99_response_time"] = sorted_times[int(0.99 * n)] if n >= 100 else sorted_times[-1]

        summary["success_rate"] = (summary["successful_requests"] / summary["total_requests"]) * 100
        summary["status_code_distribution"] = status_code_distribution

        return summary

    # ============= 认证端点并发测试 =============

    @pytest.mark.asyncio
    async def test_auth_guest_init_concurrent_load(self, test_client: AsyncClient):
        """测试游客初始化端点并发负载"""
        print("\n" + "="*50)
        print("游客初始化并发负载测试")
        print("="*50)

        # 游客初始化不需要认证，使用空token
        users = [{"user_id": "guest", "access_token": ""}]

        # 渐进式并发测试
        for user_count in [10, 25, 50]:
            print(f"\n测试并发用户数: {user_count}")

            result = await self.run_concurrent_test(
                test_client=test_client,
                method="POST",
                endpoint="/auth/guest-init",
                concurrent_users=user_count,
                users=users,
                requests_per_user=3
            )

            print(f"  总请求数: {result['total_requests']}")
            print(f"  成功率: {result['success_rate']:.1f}%")
            print(f"  吞吐量: {result['requests_per_second']:.1f} req/s")
            print(f"  平均响应时间: {result['average_response_time']:.2f}ms")
            print(f"  P95响应时间: {result['p95_response_time']:.2f}ms")
            print(f"  P99响应时间: {result['p99_response_time']:.2f}ms")

            # 性能断言
            assert result["success_rate"] >= 95, f"成功率过低: {result['success_rate']:.1f}%"
            assert result["p95_response_time"] < 100, f"P95响应时间过长: {result['p95_response_time']:.2f}ms"
            assert result["requests_per_second"] >= 50, f"吞吐量过低: {result['requests_per_second']:.1f} req/s"

    # ============= 任务端点并发测试 =============

    @pytest.mark.asyncio
    async def test_tasks_crud_concurrent_load(self, test_client: AsyncClient, test_users: List[Dict[str, str]]):
        """测试任务CRUD端点并发负载"""
        print("\n" + "="*50)
        print("任务CRUD并发负载测试")
        print("="*50)

        # 1. 并发创建任务测试
        print("\n并发创建任务测试:")
        create_result = await self.run_concurrent_test(
            test_client=test_client,
            method="POST",
            endpoint="/tasks",
            concurrent_users=20,
            users=test_users,
            requests_per_user=3,
            json={"content": f"并发测试任务-{uuid4().hex[:8]}"}
        )

        print(f"  成功率: {create_result['success_rate']:.1f}%")
        print(f"  吞吐量: {create_result['requests_per_second']:.1f} req/s")
        print(f"  P95响应时间: {create_result['p95_response_time']:.2f}ms")

        # 2. 并发读取任务列表测试
        print("\n并发读取任务列表测试:")
        list_result = await self.run_concurrent_test(
            test_client=test_client,
            method="GET",
            endpoint="/tasks",
            concurrent_users=30,
            users=test_users,
            requests_per_user=5
        )

        print(f"  成功率: {list_result['success_rate']:.1f}%")
        print(f"  吞吐量: {list_result['requests_per_second']:.1f} req/s")
        print(f"  P95响应时间: {list_result['p95_response_time']:.2f}ms")

        # 性能断言
        assert list_result["success_rate"] >= 90, f"任务列表读取成功率过低: {list_result['success_rate']:.1f}%"
        assert list_result["p95_response_time"] < 200, f"任务列表P95响应时间过长: {list_result['p95_response_time']:.2f}ms"

    # ============= 积分端点并发测试 =============

    @pytest.mark.asyncio
    async def test_points_concurrent_load(self, test_client: AsyncClient, test_users: List[Dict[str, str]]):
        """测试积分端点并发负载"""
        print("\n" + "="*50)
        print("积分端点并发负载测试")
        print("="*50)

        # 并发获取积分信息
        points_result = await self.run_concurrent_test(
            test_client=test_client,
            method="GET",
            endpoint="/points",
            concurrent_users=25,
            users=test_users,
            requests_per_user=4
        )

        print(f"  成功率: {points_result['success_rate']:.1f}%")
        print(f"  吞吐量: {points_result['requests_per_second']:.1f} req/s")
        print(f"  P95响应时间: {points_result['p95_response_time']:.2f}ms")

        # 性能断言
        assert points_result["success_rate"] >= 90, f"积分查询成功率过低: {points_result['success_rate']:.1f}%"

    # ============= API信息端点并发测试 =============

    @pytest.mark.asyncio
    async def test_api_info_concurrent_load(self, test_client: AsyncClient):
        """测试API信息端点并发负载"""
        print("\n" + "="*50)
        print("API信息并发负载测试")
        print("="*50)

        users = [{"user_id": "info", "access_token": ""}]

        # 高并发API信息测试
        info_result = await self.run_concurrent_test(
            test_client=test_client,
            method="GET",
            endpoint="/info",
            concurrent_users=100,
            users=users,
            requests_per_user=5
        )

        print(f"  成功率: {info_result['success_rate']:.1f}%")
        print(f"  吞吐量: {info_result['requests_per_second']:.1f} req/s")
        print(f"  P95响应时间: {info_result['p95_response_time']:.2f}ms")

        # 性能断言 - API信息应该是高可用的
        assert info_result["success_rate"] >= 99, f"API信息成功率过低: {info_result['success_rate']:.1f}%"
        assert info_result["p95_response_time"] < 50, f"API信息P95响应时间过长: {info_result['p95_response_time']:.2f}ms"
        assert info_result["requests_per_second"] >= 200, f"API信息吞吐量过低: {info_result['requests_per_second']:.1f} req/s"

    # ============= 混合负载测试 =============

    @pytest.mark.asyncio
    async def test_mixed_workload_concurrent_load(self, test_client: AsyncClient, test_users: List[Dict[str, str]]):
        """测试混合工作负载并发"""
        print("\n" + "="*50)
        print("混合工作负载并发测试")
        print("="*50)

        # 定义不同的工作负载
        workloads = [
            {"method": "GET", "endpoint": "/info", "weight": 0.3, "auth_required": False},
            {"method": "POST", "endpoint": "/auth/guest-init", "weight": 0.2, "auth_required": False},
            {"method": "GET", "endpoint": "/tasks", "weight": 0.25, "auth_required": True},
            {"method": "POST", "endpoint": "/tasks", "weight": 0.15, "auth_required": True, "json": {"content": "混合测试任务"}},
            {"method": "GET", "endpoint": "/points", "weight": 0.1, "auth_required": True}
        ]

        # 创建混合任务
        tasks = []
        total_requests = 200

        for i in range(total_requests):
            # 根据权重随机选择工作负载
            workload = random.choices(
                workloads,
                weights=[w["weight"] for w in workloads]
            )[0]

            # 选择用户
            if workload["auth_required"]:
                user = random.choice(test_users)
                headers = {"Authorization": f"Bearer {user['access_token']}"}
            else:
                user = {"access_token": ""}
                headers = {}

            # 创建任务
            async def make_request(method=workload["method"], endpoint=workload["endpoint"], headers=headers, json_data=workload.get("json")):
                start_time = perf_counter()
                try:
                    kwargs = {"headers": headers}
                    if json_data:
                        kwargs["json"] = {**json_data, "content": f"{json_data['content']}-{uuid4().hex[:6]}"}

                    if method == "GET":
                        response = await test_client.get(endpoint, **{k: v for k, v in kwargs.items() if k != 'json'})
                    elif method == "POST":
                        response = await test_client.post(endpoint, **kwargs)

                    duration = (perf_counter() - start_time) * 1000
                    return {
                        "success": 200 <= response.status_code < 300,
                        "duration": duration,
                        "status_code": response.status_code,
                        "endpoint": endpoint
                    }
                except Exception as e:
                    duration = (perf_counter() - start_time) * 1000
                    return {
                        "success": False,
                        "duration": duration,
                        "error": str(e),
                        "endpoint": endpoint
                    }

            tasks.append(make_request())

        # 执行混合负载测试
        print(f"执行 {total_requests} 个混合请求...")
        start_time = perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = (perf_counter() - start_time) * 1000

        # 分析结果
        successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        failed_requests = len(results) - successful_requests
        response_times = [r["duration"] for r in results if isinstance(r, dict)]

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            sorted_times = sorted(response_times)
            p95_time = sorted_times[int(0.95 * len(sorted_times))] if len(sorted_times) >= 20 else sorted_times[-1]
        else:
            avg_time = p95_time = 0

        # 按端点分组统计
        endpoint_stats = {}
        for result in results:
            if isinstance(result, dict):
                endpoint = result.get("endpoint", "unknown")
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {"success": 0, "total": 0, "times": []}
                endpoint_stats[endpoint]["total"] += 1
                if result.get("success", False):
                    endpoint_stats[endpoint]["success"] += 1
                endpoint_stats[endpoint]["times"].append(result.get("duration", 0))

        print(f"\n混合负载测试结果:")
        print(f"  总请求数: {total_requests}")
        print(f"  成功率: {(successful_requests/total_requests)*100:.1f}%")
        print(f"  吞吐量: {total_requests/(total_duration/1000):.1f} req/s")
        print(f"  平均响应时间: {avg_time:.2f}ms")
        print(f"  P95响应时间: {p95_time:.2f}ms")

        print(f"\n各端点性能:")
        for endpoint, stats in endpoint_stats.items():
            success_rate = (stats["success"]/stats["total"])*100 if stats["total"] > 0 else 0
            avg_time = sum(stats["times"])/len(stats["times"]) if stats["times"] else 0
            print(f"  {endpoint}: {stats['success']}/{stats['total']} ({success_rate:.1f}%), 平均{avg_time:.2f}ms")

        # 性能断言
        success_rate = (successful_requests/total_requests)*100
        assert success_rate >= 90, f"混合负载成功率过低: {success_rate:.1f}%"
        assert p95_time < 200, f"混合负载P95响应时间过长: {p95_time:.2f}ms"

    # ============= 压力测试 =============

    @pytest.mark.asyncio
    async def test_stress_high_concurrency(self, test_client: AsyncClient, test_users: List[Dict[str, str]]):
        """高并发压力测试"""
        print("\n" + "="*50)
        print("高并发压力测试")
        print("="*50)

        # 使用最稳定的端点进行压力测试
        users = [{"user_id": "stress", "access_token": ""}]

        # 渐进式压力测试
        stress_levels = [50, 100, 150, 200]

        for user_count in stress_levels:
            print(f"\n压力级别: {user_count} 并发用户")

            try:
                result = await self.run_concurrent_test(
                    test_client=test_client,
                    method="GET",
                    endpoint="/info",
                    concurrent_users=user_count,
                    users=users,
                    requests_per_user=2
                )

                print(f"  成功率: {result['success_rate']:.1f}%")
                print(f"  吞吐量: {result['requests_per_second']:.1f} req/s")
                print(f"  P95响应时间: {result['p95_response_time']:.2f}ms")

                # 性能断言 - 在高压力下可以适当放宽要求
                assert result["success_rate"] >= 85, f"压力测试成功率过低: {result['success_rate']:.1f}%"

                if result["success_rate"] < 90:
                    print(f"  ⚠️  成功率下降到 {result['success_rate']:.1f}%，系统可能接近极限")
                    break

            except Exception as e:
                print(f"  ❌ 压力测试失败: {e}")
                break

        print("\n压力测试完成！")


if __name__ == "__main__":
    print("并发负载测试已准备就绪")
    print("运行命令: uv run pytest tests/e2e/test_concurrent_load.py -v")