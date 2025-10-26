"""
并发测试工具

用于模拟多个并发用户访问API，测试系统的并发性能和数据一致性。

作者：TaKeKe团队
版本：1.0.0 - 并发负载测试工具
"""

import asyncio
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

import httpx
from statistics import mean, median, quantiles


@dataclass
class ConcurrentResult:
    """并发测试结果"""
    success_count: int
    error_count: int
    status_codes: Dict[int, int]
    errors: List[str]
    durations: List[float]
    total_time: float

    def __post_init__(self):
        if not self.status_codes:
            self.status_codes = {}
        if not self.errors:
            self.errors = []

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 0

    @property
    def p50_latency(self) -> float:
        """P50延迟"""
        if not self.durations:
            return 0.0
        return median(self.durations)

    @property
    def p95_latency(self) -> float:
        """P95延迟"""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        n = len(sorted_durations)
        if n >= 20:
            return sorted_durations[int(0.95 * n)]
        return sorted_durations[-1]

    @property
    def p99_latency(self) -> float:
        """P99延迟"""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        n = len(sorted_durations)
        if n >= 100:
            return sorted_durations[int(0.99 * n)]
        return sorted_durations[-1]

    @property
    def mean_latency(self) -> float:
        """平均延迟"""
        if not self.durations:
            return 0.0
        return mean(self.durations)

    @property
    def requests_per_second(self) -> float:
        """每秒请求数"""
        if self.total_time <= 0:
            return 0.0
        total_requests = self.success_count + self.error_count
        return total_requests / self.total_time

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "status_codes": self.status_codes,
            "error_count": len(self.errors),
            "errors": self.errors[:5],  # 只保留前5个错误
            "latency": {
                "p50": self.p50_latency,
                "p95": self.p95_latency,
                "p99": self.p99_latency,
                "mean": self.mean_latency,
                "min": min(self.durations) if self.durations else 0,
                "max": max(self.durations) if self.durations else 0
            },
            "total_requests": self.success_count + self.error_count,
            "requests_per_second": self.requests_per_second,
            "total_time": self.total_time
        }


class ConcurrentTester:
    """并发测试工具"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        初始化并发测试器

        Args:
            base_url: API基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    async def run_concurrent_requests(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        repeat: int = 10,
        concurrency: int = 10
    ) -> ConcurrentResult:
        """
        执行并发请求

        Args:
            method: HTTP方法
            path: 请求路径
            headers: 请求头
            json_data: JSON数据
            params: 查询参数
            repeat: 总请求数
            concurrency: 并发数

        Returns:
            ConcurrentResult: 并发测试结果
        """
        if repeat <= 0:
            raise ValueError("repeat必须大于0")
        if concurrency <= 0:
            raise ValueError("concurrency必须大于0")

        start_time = asyncio.get_event_loop().time()

        # 创建异步信号量控制并发数
        semaphore = asyncio.Semaphore(concurrency)

        async def single_request(request_id: int) -> Dict[str, Any]:
            """单个请求"""
            async with semaphore:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        request_start = asyncio.get_event_loop().time()

                        response = await client.request(
                            method=method.upper(),
                            url=f"{self.base_url}{path}",
                            headers=headers,
                            json=json_data,
                            params=params
                        )

                        duration = asyncio.get_event_loop().time() - request_start

                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "duration": duration * 1000,  # 转换为毫秒
                            "response_text": response.text[:200],  # 只保留前200字符
                            "request_id": request_id
                        }
                except Exception as e:
                    duration = asyncio.get_event_loop().time() - request_start
                    return {
                        "success": False,
                        "status_code": None,
                        "duration": duration * 1000,
                        "error": str(e),
                        "request_id": request_id
                    }

        # 执行所有请求
        tasks = [single_request(i) for i in range(repeat)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = asyncio.get_event_loop().time() - start_time

        # 统计结果
        success_count = 0
        error_count = 0
        status_codes = {}
        errors = []
        durations = []

        for result in results:
            if isinstance(result, Exception):
                error_count += 1
                errors.append(f"Task exception: {str(result)}")
                continue

            if result["success"]:
                success_count += 1
                status_code = result["status_code"]
                status_codes[status_code] = status_codes.get(status_code, 0) + 1
            else:
                error_count += 1
                errors.append(result.get("error", "Unknown error"))

            durations.append(result["duration"])

        return ConcurrentResult(
            success_count=success_count,
            error_count=error_count,
            status_codes=status_codes,
            errors=errors,
            durations=durations,
            total_time=total_time
        )

    async def run_concurrent_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        overall_timeout: float = 60.0
    ) -> Dict[str, ConcurrentResult]:
        """
        运行多个并发场景

        Args:
            scenarios: 场景列表，每个场景包含请求参数
            overall_timeout: 总超时时间

        Returns:
            Dict[str, ConcurrentResult]: 各场景的结果
        """
        async def run_scenario(scenario_name: str, scenario: Dict[str, Any]) -> tuple:
            """运行单个场景"""
            try:
                result = await self.run_concurrent_requests(**scenario)
                return scenario_name, result
            except Exception as e:
                error_result = ConcurrentResult(
                    success_count=0,
                    error_count=scenario.get("repeat", 1),
                    status_codes={},
                    errors=[f"Scenario failed: {str(e)}"],
                    durations=[],
                    total_time=0
                )
                return scenario_name, error_result

        # 并发执行所有场景
        tasks = [
            run_scenario(name, scenario)
            for name, scenario in scenarios.items()
            if isinstance(scenario, dict)
        ]

        results = {}
        if tasks:
            completed_tasks = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=overall_timeout
            )

            for task_result in completed_tasks:
                if isinstance(task_result, Exception):
                    print(f"场景执行异常: {task_result}")
                else:
                    scenario_name, scenario_result = task_result
                    results[scenario_name] = scenario_result

        return results

    def save_results(
        self,
        results: Dict[str, ConcurrentResult],
        output_file: str = "tests/reports/concurrent_test_results.json"
    ):
        """
        保存测试结果

        Args:
            results: 测试结果
            output_file: 输出文件路径
        """
        # 确保目录存在
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化的格式
        serializable_results = {
            name: result.to_dict()
            for name, result in results.items()
        }

        # 添加元数据
        report_data = {
            "timestamp": time.time(),
            "base_url": self.base_url,
            "results": serializable_results
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"并发测试结果已保存到: {output_file}")
        except Exception as e:
            print(f"错误：无法保存结果到文件 {output_file}: {e}")

    async def test_data_consistency(
        self,
        setup_request: Dict[str, Any],
        verify_request: Dict[str, Any],
        concurrent_requests: Dict[str, Any],
        expected_final_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        测试数据一致性

        Args:
            setup_request: 准备数据的请求
            verify_request: 验证数据的请求
            concurrent_requests: 并发执行的请求
            expected_final_state: 期望的最终状态

        Returns:
            Dict[str, Any]: 一致性测试结果
        """
        results = {
            "setup_success": False,
            "concurrent_results": None,
            "final_state": None,
            "consistency_check": False,
            "errors": []
        }

        try:
            # 1. 准备数据
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                setup_response = await client.request(**setup_request)
                results["setup_success"] = setup_response.status_code == 200

                if not results["setup_success"]:
                    results["errors"].append(f"Setup failed: {setup_response.status_code}")
                    return results

            # 2. 执行并发请求
            concurrent_result = await self.run_concurrent_requests(**concurrent_requests)
            results["concurrent_results"] = concurrent_result.to_dict()

            # 3. 验证最终状态
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                verify_response = await client.request(**verify_request)
                if verify_response.status_code == 200:
                    results["final_state"] = verify_response.json()
                else:
                    results["errors"].append(f"Verify failed: {verify_response.status_code}")

            # 4. 检查一致性
            if results["final_state"]:
                # 这里可以根据具体业务逻辑实现一致性检查
                # 简单示例：检查关键字段
                results["consistency_check"] = self._check_consistency(
                    results["final_state"],
                    expected_final_state
                )

        except Exception as e:
            results["errors"].append(f"Test execution error: {str(e)}")

        return results

    def _check_consistency(
        self,
        actual_state: Dict[str, Any],
        expected_state: Dict[str, Any]
    ) -> bool:
        """
        检查数据一致性

        Args:
            actual_state: 实际状态
            expected_state: 期望状态

        Returns:
            bool: 是否一致
        """
        # 简单实现，可以根据业务需要扩展
        for key, expected_value in expected_state.items():
            if key not in actual_state:
                return False
            if actual_state[key] != expected_value:
                return False
        return True


# pytest fixture
import pytest

@pytest.fixture
async def concurrent_tester():
    """并发测试器fixture"""
    tester = ConcurrentTester("http://localhost:8001")
    yield tester


async def main():
    """命令行测试入口"""
    tester = ConcurrentTester("http://localhost:8001")

    print("开始并发测试...")

    # 测试场景1：简单的GET请求
    print("\n=== 测试场景1：GET /health ===")
    result1 = await tester.run_concurrent_requests(
        method="GET",
        path="/health",
        repeat=20,
        concurrency=5
    )

    print(f"成功: {result1.success_count}, 失败: {result1.error_count}")
    print(f"成功率: {result1.success_rate:.1%}")
    print(f"P95延迟: {result1.p95_latency:.2f}ms")
    print(f"每秒请求数: {result1.requests_per_second:.2f}")

    # 测试场景2：多个场景并发
    print("\n=== 测试场景2：多场景并发 ===")
    scenarios = {
        "health_check": {
            "method": "GET",
            "path": "/health",
            "repeat": 10,
            "concurrency": 3
        },
        "api_info": {
            "method": "GET",
            "path": "/api/v3/info",
            "repeat": 10,
            "concurrency": 3
        }
    }

    results2 = await tester.run_concurrent_scenarios(scenarios)
    for name, result in results2.items():
        print(f"{name}: 成功率 {result.success_rate:.1%}, P95 {result.p95_latency:.2f}ms")

    # 保存结果
    tester.save_results(results2, "tests/reports/concurrent_test_results.json")

    print("\n并发测试完成！")


if __name__ == "__main__":
    asyncio.run(main())