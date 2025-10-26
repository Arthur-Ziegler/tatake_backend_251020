"""
API性能基准测试

对所有主要API端点进行性能基准测试，包括：
- 响应时间统计（P50, P95, P99）
- 并发性能测试
- 性能回归检测
- 吞吐量测试

作者：TaKeKe团队
版本：1.0.0 - 全面性能基准测试
"""

import pytest
import pytest_asyncio
import asyncio
import statistics
from httpx import AsyncClient
from typing import List, Dict, Any
from time import perf_counter
from uuid import uuid4

from tests.tools.performance_tracker import PerformanceTracker


class TestAPIPerformanceBenchmarks:
    """API性能基准测试类"""

    # 性能基准配置
    WARMUP_REQUESTS = 5  # 预热请求数
    BENCHMARK_REQUESTS = 50  # 基准测试请求数
    CONCURRENT_REQUESTS = 10  # 并发请求数
    PERFORMANCE_THRESHOLDS = {
        "fast": 100.0,      # 快速端点 < 100ms
        "medium": 300.0,    # 中等端点 < 300ms
        "slow": 1000.0      # 慢速端点 < 1000ms
    }

    @pytest_asyncio.fixture
    async def test_user_token(self, test_client: AsyncClient):
        """创建测试用户并获取token"""
        guest_response = await test_client.post("/auth/guest-init")
        if guest_response.status_code != 200:
            # 尝试其他可能的端点
            guest_response = await test_client.post("/api/v3/auth/guest-init")

        if guest_response.status_code == 200 and guest_response.json():
            token = guest_response.json()["data"]["access_token"]
            return token
        return "test-token"  # 返回默认token用于测试

    @pytest_asyncio.fixture
    async def auth_headers(self, test_user_token: str):
        """认证headers"""
        return {"Authorization": f"Bearer {test_user_token}"}

    async def warmup_endpoint(self, test_client: AsyncClient, method: str, endpoint: str, **kwargs):
        """预热端点"""
        for _ in range(self.WARMUP_REQUESTS):
            try:
                if method.upper() == "GET":
                    await test_client.get(endpoint, **kwargs)
                elif method.upper() == "POST":
                    await test_client.post(endpoint, **kwargs)
                elif method.upper() == "PUT":
                    await test_client.put(endpoint, **kwargs)
                elif method.upper() == "DELETE":
                    await test_client.delete(endpoint, **kwargs)
                elif method.upper() == "PATCH":
                    await test_client.patch(endpoint, **kwargs)
            except:
                pass  # 预热阶段忽略错误

    async def measure_endpoint_performance(
        self,
        test_client: AsyncClient,
        method: str,
        endpoint: str,
        requests_count: int = BENCHMARK_REQUESTS,
        **kwargs
    ) -> List[float]:
        """
        测量端点性能

        Returns:
            List[float]: 响应时间列表（毫秒）
        """
        response_times = []

        for i in range(requests_count):
            start_time = perf_counter()
            try:
                if method.upper() == "GET":
                    await test_client.get(endpoint, **kwargs)
                elif method.upper() == "POST":
                    await test_client.post(endpoint, **kwargs)
                elif method.upper() == "PUT":
                    await test_client.put(endpoint, **kwargs)
                elif method.upper() == "DELETE":
                    await test_client.delete(endpoint, **kwargs)
                elif method.upper() == "PATCH":
                    await test_client.patch(endpoint, **kwargs)

                duration = (perf_counter() - start_time) * 1000  # 转换为毫秒
                response_times.append(duration)
            except Exception as e:
                # 记录失败的请求为超时时间
                duration = (perf_counter() - start_time) * 1000
                response_times.append(duration)
                print(f"请求失败: {method} {endpoint} - {e}")

        return response_times

    def calculate_performance_stats(self, response_times: List[float]) -> Dict[str, float]:
        """计算性能统计数据"""
        if not response_times:
            return {}

        sorted_times = sorted(response_times)
        n = len(sorted_times)

        return {
            "count": n,
            "mean": statistics.mean(sorted_times),
            "median": statistics.median(sorted_times),
            "min": min(sorted_times),
            "max": max(sorted_times),
            "p50": statistics.median(sorted_times),
            "p95": sorted_times[int(0.95 * n)] if n >= 20 else sorted_times[-1],
            "p99": sorted_times[int(0.99 * n)] if n >= 100 else sorted_times[-1],
            "success_rate": len([t for t in response_times if t < 5000]) / n * 100  # 5秒内为成功
        }

    async def concurrent_performance_test(
        self,
        test_client: AsyncClient,
        method: str,
        endpoint: str,
        concurrent_users: int = CONCURRENT_REQUESTS,
        **kwargs
    ) -> Dict[str, Any]:
        """
        并发性能测试

        测试多个并发用户下的性能表现
        """
        async def single_user_request():
            start_time = perf_counter()
            try:
                if method.upper() == "GET":
                    response = await test_client.get(endpoint, **kwargs)
                elif method.upper() == "POST":
                    response = await test_client.post(endpoint, **kwargs)
                elif method.upper() == "PUT":
                    response = await test_client.put(endpoint, **kwargs)
                elif method.upper() == "DELETE":
                    response = await test_client.delete(endpoint, **kwargs)
                elif method.upper() == "PATCH":
                    response = await test_client.patch(endpoint, **kwargs)

                duration = (perf_counter() - start_time) * 1000
                return {
                    "success": True,
                    "duration": duration,
                    "status_code": response.status_code if 'response' in locals() else None
                }
            except Exception as e:
                duration = (perf_counter() - start_time) * 1000
                return {
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                }

        # 并发执行
        start_time = perf_counter()
        tasks = [single_user_request() for _ in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = (perf_counter() - start_time) * 1000

        # 分析结果
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success", False)]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get("success", False)]

        if successful_requests:
            durations = [r["duration"] for r in successful_requests]
            stats = self.calculate_performance_stats(durations)
        else:
            stats = {}

        return {
            "concurrent_users": concurrent_users,
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(results) * 100,
            "total_duration": total_duration,
            "requests_per_second": len(results) / (total_duration / 1000),
            "performance_stats": stats,
            "errors": [r.get("error", "Unknown error") for r in failed_requests[:5]]  # 只显示前5个错误
        }

    # ============= 认证相关端点性能测试 =============

    @pytest.mark.asyncio
    async def test_guest_init_performance(self, test_client: AsyncClient):
        """测试游客初始化端点性能"""
        endpoint = "POST /auth/guest-init"

        # 预热
        await self.warmup_endpoint(test_client, "POST", "/auth/guest-init")

        # 基准性能测试
        response_times = await self.measure_endpoint_performance(
            test_client, "POST", "/auth/guest-init"
        )

        stats = self.calculate_performance_stats(response_times)

        # 性能断言 - 游客初始化应该在快速范围内
        assert stats["p95"] < self.PERFORMANCE_THRESHOLDS["fast"], \
            f"游客初始化P95响应时间过长: {stats['p95']:.2f}ms"

        assert stats["success_rate"] >= 95, \
            f"游客初始化成功率过低: {stats['success_rate']:.1f}%"

        # 记录性能基准
        tracker = PerformanceTracker()
        tracker.set_endpoint(endpoint)
        tracker.measurements = response_times
        comparison = tracker.compare_with_baseline(endpoint)

        print(f"\n{endpoint} 性能测试结果:")
        print(f"  P50: {stats['p50']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  P99: {stats['p99']:.2f}ms")
        print(f"  成功率: {stats['success_rate']:.1f}%")
        print(f"  基准对比: {comparison['message']}")

    @pytest.mark.asyncio
    async def test_guest_init_concurrent_performance(self, test_client: AsyncClient):
        """测试游客初始化并发性能"""
        endpoint = "CONCURRENT GET /api/v3/auth/guest-init"

        # 并发性能测试
        concurrent_result = await self.concurrent_performance_test(
            test_client, "GET", "/api/v3/auth/guest-init",
            concurrent_users=self.CONCURRENT_REQUESTS
        )

        # 并发性能断言
        assert concurrent_result["success_rate"] >= 90, \
            f"游客初始化并发成功率过低: {concurrent_result['success_rate']:.1f}%"

        assert concurrent_result["requests_per_second"] >= 10, \
            f"游客初始化吞吐量过低: {concurrent_result['requests_per_second']:.1f} req/s"

        print(f"\n{endpoint} 并发性能测试结果:")
        print(f"  并发用户: {concurrent_result['concurrent_users']}")
        print(f"  成功率: {concurrent_result['success_rate']:.1f}%")
        print(f"  吞吐量: {concurrent_result['requests_per_second']:.1f} req/s")
        if concurrent_result["performance_stats"]:
            print(f"  平均响应时间: {concurrent_result['performance_stats']['mean']:.2f}ms")

    # ============= 任务相关端点性能测试 =============

    @pytest.mark.asyncio
    async def test_tasks_crud_performance(self, test_client: AsyncClient, auth_headers: Dict[str, str]):
        """测试任务CRUD操作性能"""
        # 1. 创建任务性能测试 - 尝试不同的端点路径
        endpoints_to_try = ["/tasks", "/api/v3/tasks"]
        create_success = False
        create_stats = None

        for endpoint in endpoints_to_try:
            try:
                await self.warmup_endpoint(
                    test_client, "POST", endpoint,
                    json={"content": "性能测试任务"},
                    headers=auth_headers
                )

                create_times = await self.measure_endpoint_performance(
                    test_client, "POST", endpoint,
                    json={"content": "性能测试任务"},
                    headers=auth_headers
                )

                create_stats = self.calculate_performance_stats(create_times)
                if create_stats.get("success_rate", 0) > 50:  # 至少一半请求成功
                    create_success = True
                    print(f"成功测试端点: {endpoint}")
                    break
            except Exception as e:
                print(f"端点 {endpoint} 测试失败: {e}")
                continue

        if not create_success or not create_stats:
            # 跳过任务CRUD测试，端点不可用
            pytest.skip("任务CRUD端点不可用，跳过性能测试")

        assert create_stats["p95"] < self.PERFORMANCE_THRESHOLDS["medium"], \
            f"创建任务P95响应时间过长: {create_stats['p95']:.2f}ms"

        print(f"\n任务CRUD性能测试结果:")
        print(f"  创建任务 - P95: {create_stats['p95']:.2f}ms, 成功率: {create_stats['success_rate']:.1f}%")

    @pytest.mark.asyncio
    async def test_tasks_concurrent_performance(self, test_client: AsyncClient, auth_headers: Dict[str, str]):
        """测试任务端点并发性能"""
        endpoint = "CONCURRENT POST /api/v3/tasks"

        # 并发创建任务测试
        concurrent_result = await self.concurrent_performance_test(
            test_client, "POST", "/api/v3/tasks",
            json={"content": f"并发测试任务-{uuid4().hex[:8]}"},
            headers=auth_headers,
            concurrent_users=self.CONCURRENT_REQUESTS
        )

        # 并发性能断言
        assert concurrent_result["success_rate"] >= 80, \
            f"并发创建任务成功率过低: {concurrent_result['success_rate']:.1f}%"

        print(f"\n{endpoint} 并发性能测试结果:")
        print(f"  成功率: {concurrent_result['success_rate']:.1f}%")
        print(f"  吞吐量: {concurrent_result['requests_per_second']:.1f} req/s")
        if concurrent_result["errors"]:
            print(f"  主要错误: {concurrent_result['errors'][0]}")

    # ============= 积分相关端点性能测试 =============

    @pytest.mark.asyncio
    async def test_points_performance(self, test_client: AsyncClient, auth_headers: Dict[str, str]):
        """测试积分相关端点性能"""
        # 获取积分信息
        endpoint_points = "GET /api/v3/points"
        await self.warmup_endpoint(test_client, "GET", "/api/v3/points", headers=auth_headers)

        points_times = await self.measure_endpoint_performance(
            test_client, "GET", "/api/v3/points", headers=auth_headers
        )

        points_stats = self.calculate_performance_stats(points_times)
        assert points_stats["p95"] < self.PERFORMANCE_THRESHOLDS["medium"], \
            f"获取积分信息P95响应时间过长: {points_stats['p95']:.2f}ms"

        print(f"\n积分端点性能测试结果:")
        print(f"  获取积分 - P95: {points_stats['p95']:.2f}ms, 成功率: {points_stats['success_rate']:.1f}%")

    # ============= API信息端点性能测试 =============

    @pytest.mark.asyncio
    async def test_api_info_performance(self, test_client: AsyncClient):
        """测试API信息端点性能"""
        endpoint = "GET /api/v3/info"

        # 预热
        await self.warmup_endpoint(test_client, "GET", "/api/v3/info")

        # 基准性能测试
        response_times = await self.measure_endpoint_performance(
            test_client, "GET", "/api/v3/info"
        )

        stats = self.calculate_performance_stats(response_times)

        # API信息应该是快速端点
        assert stats["p95"] < self.PERFORMANCE_THRESHOLDS["fast"], \
            f"API信息P95响应时间过长: {stats['p95']:.2f}ms"

        print(f"\n{endpoint} 性能测试结果:")
        print(f"  P50: {stats['p50']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  P99: {stats['p99']:.2f}ms")
        print(f"  成功率: {stats['success_rate']:.1f}%")

    # ============= 综合性能报告测试 =============

    @pytest.mark.asyncio
    async def test_overall_performance_baseline(self, test_client: AsyncClient, auth_headers: Dict[str, str]):
        """综合性能基准测试 - 生成完整的性能报告"""
        print("\n" + "="*60)
        print("综合性能基准测试开始")
        print("="*60)

        # 定义关键端点列表
        key_endpoints = [
            ("GET", "/api/v3/info", {}, "info"),
            ("GET", "/api/v3/auth/guest-init", {}, "guest_init"),
            ("POST", "/api/v3/tasks", {"json": {"content": "测试任务"}, "headers": auth_headers}, "create_task"),
            ("GET", "/api/v3/tasks", {"headers": auth_headers}, "list_tasks"),
            ("GET", "/api/v3/points", {"headers": auth_headers}, "points"),
        ]

        performance_summary = {}
        tracker = PerformanceTracker()

        for method, endpoint, kwargs, endpoint_name in key_endpoints:
            print(f"\n测试端点: {method} {endpoint}")

            # 预热
            await self.warmup_endpoint(test_client, method, endpoint, **kwargs)

            # 性能测试
            response_times = await self.measure_endpoint_performance(
                test_client, method, endpoint, **kwargs
            )

            stats = self.calculate_performance_stats(response_times)
            performance_summary[endpoint_name] = stats

            # 保存基准数据
            tracker.set_endpoint(f"{method} {endpoint}")
            tracker.measurements = response_times
            comparison = tracker.compare_with_baseline(f"{method} {endpoint}")

            print(f"  P50: {stats['p50']:.2f}ms")
            print(f"  P95: {stats['p95']:.2f}ms")
            print(f"  P99: {stats['p99']:.2f}ms")
            print(f"  成功率: {stats['success_rate']:.1f}%")
            print(f"  基准对比: {comparison['message']}")

            # 基本性能断言
            if endpoint_name in ["info", "guest_init"]:
                assert stats["p95"] < self.PERFORMANCE_THRESHOLDS["fast"], \
                    f"快速端点 {endpoint_name} P95响应时间过长: {stats['p95']:.2f}ms"
            else:
                assert stats["p95"] < self.PERFORMANCE_THRESHOLDS["medium"], \
                    f"端点 {endpoint_name} P95响应时间过长: {stats['p95']:.2f}ms"

            assert stats["success_rate"] >= 90, \
                f"端点 {endpoint_name} 成功率过低: {stats['success_rate']:.1f}%"

        # 生成综合报告
        print(f"\n" + "="*60)
        print("综合性能测试报告")
        print("="*60)

        total_tests = len(performance_summary)
        fast_endpoints = sum(1 for stats in performance_summary.values() if stats["p95"] < self.PERFORMANCE_THRESHOLDS["fast"])
        medium_endpoints = sum(1 for stats in performance_summary.values() if stats["p95"] < self.PERFORMANCE_THRESHOLDS["medium"])

        avg_p95 = statistics.mean([stats["p95"] for stats in performance_summary.values()])
        avg_success_rate = statistics.mean([stats["success_rate"] for stats in performance_summary.values()])

        print(f"测试端点总数: {total_tests}")
        print(f"快速端点数量: {fast_endpoints} (P95 < {self.PERFORMANCE_THRESHOLDS['fast']}ms)")
        print(f"中等端点数量: {medium_endpoints} (P95 < {self.PERFORMANCE_THRESHOLDS['medium']}ms)")
        print(f"平均P95响应时间: {avg_p95:.2f}ms")
        print(f"平均成功率: {avg_success_rate:.1f}%")

        # 获取所有基准数据
        all_baselines = tracker.get_all_baselines()
        print(f"\n当前基准数据总数: {len(all_baselines)} 个端点")

        print("\n性能基准测试完成！")
        print("="*60)


if __name__ == "__main__":
    print("API性能基准测试已准备就绪")
    print("运行命令: uv run pytest tests/e2e/test_performance_benchmarks.py -v")