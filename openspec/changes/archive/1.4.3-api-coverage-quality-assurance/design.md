# Design: 1.4.3-api-coverage-quality-assurance

## 架构概览

本次变更建立**四维度质量保障体系**，确保系统在功能、性能、并发、边界各个维度的质量：

```
┌─────────────────────────────────────────────────────────────┐
│                    质量保障体系架构                            │
└─────────────────────────────────────────────────────────────┘

维度1：端点覆盖                维度2：边界异常
┌──────────────┐              ┌──────────────┐
│ 端点发现引擎  │              │ 边界用例库    │
│  - FastAPI   │              │  - 无效UUID   │
│    路由扫描   │              │  - SQL注入    │
│  - 测试扫描   │              │  - XSS攻击    │
│  - 覆盖率计算 │              │  - 边界值     │
└──────────────┘              └──────────────┘
       ↓                              ↓
┌──────────────┐              ┌──────────────┐
│ 100%端点测试  │              │ 异常场景测试  │
│  - 正常流程   │              │  - 输入验证   │
│  - 权限控制   │              │  - 错误处理   │
│  - 数据验证   │              │  - 安全防御   │
└──────────────┘              └──────────────┘

维度3：性能基准                维度4：并发负载
┌──────────────┐              ┌──────────────┐
│ 性能追踪器    │              │ 并发测试器    │
│  - 响应时间   │              │  - asyncio    │
│  - 统计分析   │              │  - httpx异步  │
│  - 基准对比   │              │  - 结果聚合   │
│  - 回归检测   │              │  - 一致性验证 │
└──────────────┘              └──────────────┘
       ↓                              ↓
┌──────────────┐              ┌──────────────┐
│ 性能测试套件  │              │ 并发测试套件  │
│  - P50/P95    │              │  - 积分一致性 │
│  - SLA验证    │              │  - Top3唯一性 │
│  - 性能报告   │              │  - 奖励幂等性 │
└──────────────┘              └──────────────┘

                    ↓
         ┌──────────────────┐
         │  质量度量与报告    │
         │  - 覆盖率报告     │
         │  - 性能基准数据   │
         │  - 并发测试结果   │
         │  - CI/CD集成      │
         └──────────────────┘
```

## 核心组件设计

### 组件1：端点发现与覆盖追踪系统

#### ADR-301: 端点发现策略

**背景**：
需要自动发现所有API端点并追踪测试覆盖率，避免手动维护端点清单导致的遗漏。

**决策**：
使用**双向扫描策略** - 扫描FastAPI路由定义和测试代码中的HTTP调用。

**实现细节**：

```python
# tests/tools/endpoint_discovery.py
from fastapi import FastAPI
from fastapi.routing import APIRoute
from typing import List, Dict, Set, Tuple
import ast
import inspect
from pathlib import Path

class EndpointDiscovery:
    """端点发现与覆盖追踪引擎"""

    def __init__(self, app: FastAPI, test_dir: str = "tests"):
        self.app = app
        self.test_dir = Path(test_dir)

    def get_all_endpoints(self) -> List[Dict]:
        """
        扫描FastAPI应用，获取所有端点定义

        Returns:
            List[Dict]: 端点列表，每个端点包含：
                - path: 路径（如 /tasks/{task_id}/complete）
                - method: HTTP方法（GET/POST/PUT/DELETE/PATCH）
                - name: 端点名称（函数名）
                - module: 所属模块
                - tags: 标签（用于分组）
        """
        endpoints = []

        for route in self.app.routes:
            # 只处理APIRoute，忽略Mount等其他路由
            if not isinstance(route, APIRoute):
                continue

            # 遍历该路由支持的所有方法
            for method in route.methods:
                # 忽略OPTIONS和HEAD（自动生成的）
                if method in ["OPTIONS", "HEAD"]:
                    continue

                endpoints.append({
                    "path": route.path,
                    "method": method,
                    "name": route.name,
                    "module": route.endpoint.__module__,
                    "tags": route.tags,
                    "signature": f"{method} {route.path}"
                })

        return endpoints

    def get_tested_endpoints(self) -> Set[str]:
        """
        扫描测试代码，提取已测试的端点

        原理：
        1. 遍历所有测试文件
        2. 解析Python AST，查找 client.get/post/put/delete/patch 调用
        3. 提取调用的URL参数
        4. 生成 "METHOD /path" 格式的签名

        Returns:
            Set[str]: 已测试端点签名集合，如 {"GET /tasks", "POST /user/login"}
        """
        tested = set()

        # 遍历所有测试文件
        for test_file in self.test_dir.rglob("test_*.py"):
            try:
                # 读取并解析文件
                source = test_file.read_text()
                tree = ast.parse(source)

                # 使用AST访问者模式查找HTTP调用
                visitor = HTTPCallVisitor()
                visitor.visit(tree)

                # 添加到已测试集合
                tested.update(visitor.endpoints)

            except Exception as e:
                print(f"Warning: 无法解析 {test_file}: {e}")
                continue

        return tested

    def generate_coverage_report(self) -> Dict:
        """
        生成覆盖率报告

        Returns:
            Dict: 包含以下字段：
                - total: 总端点数
                - tested: 已测试端点数
                - coverage_rate: 覆盖率（0.0-1.0）
                - untested_endpoints: 未测试端点列表
                - by_domain: 按域分组的覆盖率
        """
        all_endpoints = self.get_all_endpoints()
        tested_endpoints = self.get_tested_endpoints()

        # 计算总体覆盖率
        coverage_rate = len(tested_endpoints) / len(all_endpoints) if all_endpoints else 0

        # 找出未测试端点
        untested = [
            ep["signature"]
            for ep in all_endpoints
            if ep["signature"] not in tested_endpoints
        ]

        # 按域分组统计
        by_domain = self._calculate_domain_coverage(all_endpoints, tested_endpoints)

        return {
            "total": len(all_endpoints),
            "tested": len(tested_endpoints),
            "coverage_rate": coverage_rate,
            "untested_endpoints": sorted(untested),
            "by_domain": by_domain,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_domain_coverage(
        self,
        all_endpoints: List[Dict],
        tested_endpoints: Set[str]
    ) -> Dict[str, Dict]:
        """按域计算覆盖率"""
        from collections import defaultdict

        domain_stats = defaultdict(lambda: {"total": 0, "tested": 0})

        for ep in all_endpoints:
            # 从path提取域名（/tasks/... -> tasks）
            domain = ep["path"].split("/")[1] if len(ep["path"].split("/")) > 1 else "root"
            domain_stats[domain]["total"] += 1

            if ep["signature"] in tested_endpoints:
                domain_stats[domain]["tested"] += 1

        # 计算每个域的覆盖率
        for domain, stats in domain_stats.items():
            stats["coverage_rate"] = stats["tested"] / stats["total"]

        return dict(domain_stats)


class HTTPCallVisitor(ast.NodeVisitor):
    """AST访问者，用于查找HTTP调用"""

    def __init__(self):
        self.endpoints = set()

    def visit_Call(self, node):
        """访问函数调用节点"""
        # 查找 client.get/post/put/delete/patch(...) 模式
        if isinstance(node.func, ast.Attribute):
            # 提取方法名（get/post/etc）
            method_name = node.func.attr.upper()

            # 只关心HTTP方法
            if method_name not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                self.generic_visit(node)
                return

            # 提取URL参数（第一个位置参数）
            if node.args:
                url_arg = node.args[0]

                # 处理字符串字面量
                if isinstance(url_arg, ast.Constant):
                    url = url_arg.value
                    self.endpoints.add(f"{method_name} {url}")

                # 处理f-string（如 f"/tasks/{task_id}/complete"）
                elif isinstance(url_arg, ast.JoinedStr):
                    # 简化处理：提取静态部分，将变量替换为占位符
                    url = self._extract_url_from_fstring(url_arg)
                    if url:
                        self.endpoints.add(f"{method_name} {url}")

        self.generic_visit(node)

    def _extract_url_from_fstring(self, node: ast.JoinedStr) -> str:
        """从f-string提取URL模式"""
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                # 静态字符串部分
                parts.append(value.value)
            else:
                # 变量部分，替换为通配符
                parts.append("{id}")

        url = "".join(parts)

        # 标准化：将 {id} 替换为 {task_id} 等（根据上下文）
        # 简化处理：统一使用 {id}
        return url
```

**使用示例**：

```python
# tests/test_api_coverage.py
import pytest
from src.api.main import app
from tests.tools.endpoint_discovery import EndpointDiscovery

def test_100_percent_endpoint_coverage():
    """验证100%端点覆盖率"""
    discovery = EndpointDiscovery(app)
    report = discovery.generate_coverage_report()

    # 打印详细报告
    print("\n" + "="*60)
    print("API端点覆盖率报告")
    print("="*60)
    print(f"总端点数: {report['total']}")
    print(f"已测试: {report['tested']}")
    print(f"覆盖率: {report['coverage_rate']:.1%}")
    print("\n按域分组:")
    for domain, stats in report['by_domain'].items():
        print(f"  {domain}: {stats['tested']}/{stats['total']} ({stats['coverage_rate']:.1%})")

    if report['untested_endpoints']:
        print(f"\n未测试端点 ({len(report['untested_endpoints'])}):")
        for ep in report['untested_endpoints']:
            print(f"  - {ep}")

    # 验证100%覆盖
    assert report['coverage_rate'] == 1.0, \
        f"端点覆盖率不足100%，缺少 {len(report['untested_endpoints'])} 个端点测试"
```

**优势**：
1. ✅ 完全自动化，无需手动维护端点清单
2. ✅ 实时检测，每次测试都验证覆盖率
3. ✅ 按域分组，快速定位未覆盖的模块

### 组件2：性能基准测试系统

#### ADR-302: 性能追踪器设计

**背景**：
需要为所有端点建立性能基准，并检测性能回归。

**决策**：
使用**统计分析+基准对比**策略 - 测量多次请求的P50/P95/P99，与历史基准对比。

**实现细节**：

```python
# tests/tools/performance_tracker.py
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Callable
from statistics import median, quantile
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class PerformanceStats:
    """性能统计数据"""
    p50: float  # 中位数（ms）
    p95: float  # 95分位数（ms）
    p99: float  # 99分位数（ms）
    min: float  # 最小值（ms）
    max: float  # 最大值（ms）
    mean: float  # 平均值（ms）
    count: int  # 样本数
    timestamp: str  # 测量时间

class PerformanceTracker:
    """性能追踪器"""

    def __init__(self, baseline_file: str = "tests/reports/performance_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.measurements: List[float] = []

    def measure(self, func: Callable, *args, **kwargs):
        """
        测量函数执行时间

        Args:
            func: 要测量的函数
            *args, **kwargs: 函数参数

        Returns:
            函数的返回值
        """
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # 即使函数抛出异常，也记录执行时间
            duration = (time.perf_counter() - start) * 1000  # 转换为毫秒
            self.measurements.append(duration)

    def get_statistics(self) -> Optional[PerformanceStats]:
        """
        计算统计数据

        Returns:
            PerformanceStats: 性能统计，如果没有测量数据则返回None
        """
        if not self.measurements:
            return None

        sorted_data = sorted(self.measurements)

        return PerformanceStats(
            p50=median(sorted_data),
            p95=quantile(sorted_data, 0.95),
            p99=quantile(sorted_data, 0.99),
            min=min(sorted_data),
            max=max(sorted_data),
            mean=sum(sorted_data) / len(sorted_data),
            count=len(sorted_data),
            timestamp=datetime.now().isoformat()
        )

    def compare_with_baseline(self, endpoint: str, threshold: float = 1.2) -> Dict:
        """
        与基准对比

        Args:
            endpoint: 端点签名（如 "GET /tasks"）
            threshold: 回归阈值（默认1.2 = 20%）

        Returns:
            Dict: 对比结果，包含：
                - status: "baseline_created" | "ok" | "regression"
                - current: 当前统计数据
                - baseline: 基准统计数据（首次为None）
                - diff_p95: P95差异（ms）
                - regression_percent: 回归百分比
        """
        stats = self.get_statistics()
        if not stats:
            return {"status": "error", "message": "No measurements"}

        baseline = self.load_baseline()

        # 首次测试，保存为基准
        if endpoint not in baseline:
            self.save_baseline(endpoint, stats)
            return {
                "status": "baseline_created",
                "current": asdict(stats),
                "baseline": None,
                "message": f"创建性能基准: P95={stats.p95:.2f}ms"
            }

        # 对比基准
        baseline_stats = PerformanceStats(**baseline[endpoint])
        diff_p95 = stats.p95 - baseline_stats.p95
        regression_percent = (stats.p95 / baseline_stats.p95 - 1) * 100

        # 判断是否回归
        is_regression = stats.p95 > baseline_stats.p95 * threshold

        return {
            "status": "regression" if is_regression else "ok",
            "current": asdict(stats),
            "baseline": asdict(baseline_stats),
            "diff_p95": diff_p95,
            "regression_percent": regression_percent,
            "message": (
                f"性能回归: P95增加 {diff_p95:.2f}ms ({regression_percent:.1f}%)"
                if is_regression else
                f"性能正常: P95={stats.p95:.2f}ms (基准{baseline_stats.p95:.2f}ms)"
            )
        }

    def load_baseline(self) -> Dict:
        """加载基准数据"""
        if self.baseline_file.exists():
            return json.loads(self.baseline_file.read_text())
        return {}

    def save_baseline(self, endpoint: str, stats: PerformanceStats):
        """保存基准数据"""
        baseline = self.load_baseline()
        baseline[endpoint] = asdict(stats)

        self.baseline_file.write_text(
            json.dumps(baseline, indent=2, ensure_ascii=False)
        )

    def reset(self):
        """重置测量数据（用于下一个测试）"""
        self.measurements.clear()


@pytest.fixture
def perf_tracker():
    """性能追踪器fixture"""
    tracker = PerformanceTracker()
    yield tracker
    tracker.reset()
```

**使用示例**：

```python
# tests/performance/test_api_performance.py
import pytest

class TestTaskAPIPerformance:
    """任务API性能测试"""

    def test_list_tasks_performance(
        self,
        real_api_client,
        test_user_token,
        perf_tracker
    ):
        """测试任务列表性能"""

        # 准备测试数据：创建100个任务
        for i in range(100):
            real_api_client.post(
                "/tasks/create",
                json={"content": f"Performance test task {i}"},
                headers={"Authorization": f"Bearer {test_user_token}"}
            )

        # 性能测试：执行20次请求
        for _ in range(20):
            perf_tracker.measure(
                real_api_client.get,
                "/tasks",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )

        # 获取统计数据
        stats = perf_tracker.get_statistics()
        print(f"\n性能统计:")
        print(f"  P50: {stats.p50:.2f}ms")
        print(f"  P95: {stats.p95:.2f}ms")
        print(f"  P99: {stats.p99:.2f}ms")

        # 验证性能SLA
        assert stats.p95 < 200, \
            f"P95响应时间超标: {stats.p95:.2f}ms > 200ms"
        assert stats.p99 < 500, \
            f"P99响应时间超标: {stats.p99:.2f}ms > 500ms"

        # 对比基准
        comparison = perf_tracker.compare_with_baseline("GET /tasks")
        print(f"\n{comparison['message']}")

        assert comparison["status"] != "regression", \
            f"性能回归: {comparison['diff_p95']:.2f}ms ({comparison['regression_percent']:.1f}%)"
```

**优势**：
1. ✅ 自动基准管理，首次运行创建基准，后续运行对比
2. ✅ 统计严谨，使用P95/P99而非平均值避免离群值影响
3. ✅ 回归检测，自动识别性能退化

### 组件3：并发负载测试系统

#### ADR-303: 并发测试器设计

**背景**：
需要验证系统在并发场景下的数据一致性和性能稳定性。

**决策**：
使用**asyncio + httpx**实现真实并发测试，而非threading（避免GIL限制）。

**实现细节**：

```python
# tests/tools/concurrent_tester.py
import asyncio
import httpx
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from statistics import median, quantile

@dataclass
class ConcurrentResult:
    """并发测试结果"""
    success_count: int
    error_count: int
    status_codes: Dict[int, int]  # {200: 8, 422: 2}
    errors: List[str]
    durations: List[float]
    p50_latency: float
    p95_latency: float
    max_latency: float

class ConcurrentTester:
    """并发测试工具"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout

    async def run_concurrent_requests(
        self,
        method: str,
        path: str,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        repeat: int = 10
    ) -> ConcurrentResult:
        """
        执行并发请求

        Args:
            method: HTTP方法（GET/POST/PUT/DELETE/PATCH）
            path: 请求路径
            headers: 请求头（可选）
            json_data: JSON数据（可选）
            repeat: 并发请求数量

        Returns:
            ConcurrentResult: 聚合结果
        """

        async def single_request() -> Dict:
            """单个请求"""
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            ) as client:
                start = asyncio.get_event_loop().time()
                try:
                    response = await client.request(
                        method=method,
                        url=path,
                        headers=headers,
                        json=json_data
                    )
                    duration = (asyncio.get_event_loop().time() - start) * 1000

                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "duration": duration,
                        "error": None,
                        "data": response.json() if response.text else None
                    }
                except Exception as e:
                    duration = (asyncio.get_event_loop().time() - start) * 1000
                    return {
                        "success": False,
                        "status_code": None,
                        "duration": duration,
                        "error": str(e),
                        "data": None
                    }

        # 执行并发请求
        tasks = [single_request() for _ in range(repeat)]
        results = await asyncio.gather(*tasks)

        # 聚合结果
        return self._aggregate_results(results)

    def _aggregate_results(self, results: List[Dict]) -> ConcurrentResult:
        """聚合多个请求结果"""
        success_count = sum(1 for r in results if r["success"])
        error_count = len(results) - success_count

        # 统计状态码分布
        status_codes = {}
        for r in results:
            if r["status_code"]:
                status_codes[r["status_code"]] = status_codes.get(r["status_code"], 0) + 1

        # 收集错误
        errors = [r["error"] for r in results if r["error"]]

        # 统计延迟
        durations = [r["duration"] for r in results]
        sorted_durations = sorted(durations)

        return ConcurrentResult(
            success_count=success_count,
            error_count=error_count,
            status_codes=status_codes,
            errors=errors,
            durations=durations,
            p50_latency=median(sorted_durations),
            p95_latency=quantile(sorted_durations, 0.95),
            max_latency=max(sorted_durations)
        )

    async def run_concurrent_scenarios(
        self,
        scenarios: List[Dict]
    ) -> List[ConcurrentResult]:
        """
        执行多个并发场景

        Args:
            scenarios: 场景列表，每个场景是一个请求配置字典

        Returns:
            List[ConcurrentResult]: 每个场景的结果
        """
        tasks = [
            self.run_concurrent_requests(**scenario)
            for scenario in scenarios
        ]
        return await asyncio.gather(*tasks)
```

**使用示例**：

```python
# tests/concurrent/test_points_concurrency.py
import pytest
import asyncio

@pytest.mark.asyncio
class TestPointsConcurrency:
    """积分系统并发测试"""

    async def test_concurrent_points_deduction_consistency(
        self,
        live_api_server,
        real_api_client,
        test_user_token
    ):
        """测试积分并发扣减的数据一致性"""

        # 给用户充值3000积分（恰好够扣10次）
        # （省略充值逻辑）

        # 并发扣减：10个并发请求，每次扣300积分
        tester = ConcurrentTester(live_api_server)
        result = await tester.run_concurrent_requests(
            method="POST",
            path="/top3/set",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "date": "2025-10-26",
                "task_ids": ["uuid1", "uuid2", "uuid3"]
            },
            repeat=10
        )

        # 打印结果
        print(f"\n并发测试结果:")
        print(f"  成功: {result.success_count}")
        print(f"  失败: {result.error_count}")
        print(f"  状态码分布: {result.status_codes}")
        print(f"  P95延迟: {result.p95_latency:.2f}ms")

        # 验证：部分成功，部分因余额不足失败
        assert result.success_count <= 10, "成功次数不应超过10"
        assert result.success_count > 0, "至少应有部分请求成功"

        # 验证最终余额正确（关键：数据一致性）
        balance_response = real_api_client.get(
            "/points/my-points",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        final_balance = balance_response.json()["data"]["current_balance"]
        expected_balance = 3000 - (result.success_count * 300)

        assert final_balance == expected_balance, \
            f"并发场景下积分计算错误: 实际={final_balance}, 预期={expected_balance}"

    async def test_concurrent_mixed_operations(
        self,
        live_api_server,
        test_user_token
    ):
        """测试混合操作的并发"""

        tester = ConcurrentTester(live_api_server)

        # 同时执行：查询余额、扣除积分、添加积分
        scenarios = [
            # 5个查询请求
            *[{
                "method": "GET",
                "path": "/points/my-points",
                "headers": {"Authorization": f"Bearer {test_user_token}"},
                "repeat": 5
            }],
            # 3个扣除请求
            {
                "method": "POST",
                "path": "/top3/set",
                "headers": {"Authorization": f"Bearer {test_user_token}"},
                "json": {"date": "2025-10-27", "task_ids": ["a", "b", "c"]},
                "repeat": 3
            }
        ]

        results = await tester.run_concurrent_scenarios(scenarios)

        # 验证所有请求都成功（查询不应受扣除影响）
        for i, result in enumerate(results):
            print(f"\n场景{i+1}: 成功={result.success_count}, 失败={result.error_count}")
            assert result.error_count == 0 or result.status_codes.get(422, 0) > 0, \
                "应该只有业务逻辑错误（422），不应有系统错误（500）"
```

**优势**：
1. ✅ 真实并发，asyncio实现真正的并发请求
2. ✅ 详细结果，提供成功率、状态码分布、延迟统计
3. ✅ 灵活组合，支持混合场景的并发测试

### 组件4：边界与异常测试库

#### ADR-304: 边界用例生成器设计

**背景**：
需要系统化地测试各种边界条件和异常输入，避免遗漏常见的攻击向量。

**决策**：
使用**用例库 + 参数化测试**策略 - 预定义常见边界用例，通过pytest.mark.parametrize批量测试。

**实现细节**：

```python
# tests/tools/edge_case_generator.py
from typing import List, Any, Dict
from uuid import uuid4
from datetime import date, timedelta

class EdgeCaseGenerator:
    """边界用例生成器"""

    @staticmethod
    def invalid_uuids() -> List[Dict[str, Any]]:
        """无效UUID测试用例"""
        return [
            {"value": "not-a-uuid", "desc": "非UUID字符串"},
            {"value": "12345", "desc": "纯数字"},
            {"value": "00000000-0000-0000-0000-000000000000", "desc": "nil UUID"},
            {"value": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "desc": "非法字符"},
            {"value": "", "desc": "空字符串"},
            {"value": "' OR '1'='1", "desc": "SQL注入"},
            {"value": "<script>alert('xss')</script>", "desc": "XSS攻击"},
            {"value": "../../../etc/passwd", "desc": "路径遍历"},
            {"value": "a" * 1000, "desc": "超长字符串"},
        ]

    @staticmethod
    def boundary_integers() -> List[Dict[str, Any]]:
        """边界整数测试用例"""
        return [
            {"value": 0, "desc": "零"},
            {"value": -1, "desc": "负数"},
            {"value": -999999, "desc": "大负数"},
            {"value": 999999, "desc": "大正数"},
            {"value": 2**31 - 1, "desc": "INT_MAX"},
            {"value": 2**31, "desc": "超过INT_MAX"},
            {"value": 2**63 - 1, "desc": "BIGINT_MAX"},
        ]

    @staticmethod
    def boundary_strings() -> List[Dict[str, Any]]:
        """边界字符串测试用例"""
        return [
            {"value": "", "desc": "空字符串"},
            {"value": " ", "desc": "单个空格"},
            {"value": "   ", "desc": "多个空格"},
            {"value": "a" * 1000, "desc": "超长字符串（1000字符）"},
            {"value": "a" * 10000, "desc": "极长字符串（10000字符）"},
            {"value": "中文测试内容", "desc": "中文字符"},
            {"value": "emoji 测试 😀🎉", "desc": "Emoji字符"},
            {"value": "\n\r\t", "desc": "特殊字符"},
            {"value": "\\x00\\x01\\x02", "desc": "控制字符"},
            {"value": "<script>alert('xss')</script>", "desc": "XSS脚本"},
            {"value": "'; DROP TABLE users; --", "desc": "SQL注入"},
        ]

    @staticmethod
    def boundary_dates() -> List[Dict[str, Any]]:
        """边界日期测试用例"""
        today = date.today()
        return [
            {"value": today.isoformat(), "desc": "今天"},
            {"value": (today - timedelta(days=1)).isoformat(), "desc": "昨天"},
            {"value": (today + timedelta(days=1)).isoformat(), "desc": "明天"},
            {"value": "1970-01-01", "desc": "Unix epoch"},
            {"value": "2099-12-31", "desc": "遥远未来"},
            {"value": "2000-02-29", "desc": "闰年2月29日"},
            {"value": "2001-02-29", "desc": "非闰年2月29日（无效）"},
            {"value": "invalid-date", "desc": "无效格式"},
            {"value": "2025-13-01", "desc": "无效月份"},
            {"value": "2025-02-30", "desc": "不存在的日期"},
            {"value": "", "desc": "空字符串"},
        ]

    @staticmethod
    def attack_vectors() -> List[Dict[str, Any]]:
        """常见攻击向量"""
        return [
            {
                "type": "sql_injection",
                "payloads": [
                    "' OR '1'='1",
                    "'; DROP TABLE users; --",
                    "' UNION SELECT * FROM auth --",
                ]
            },
            {
                "type": "xss",
                "payloads": [
                    "<script>alert('xss')</script>",
                    "<img src=x onerror=alert('xss')>",
                    "javascript:alert('xss')",
                ]
            },
            {
                "type": "path_traversal",
                "payloads": [
                    "../../../etc/passwd",
                    "..\\..\\..\\windows\\system32\\config\\sam",
                    "/etc/passwd",
                ]
            },
            {
                "type": "command_injection",
                "payloads": [
                    "; ls -la",
                    "| cat /etc/passwd",
                    "`whoami`",
                ]
            },
        ]
```

**使用示例**：

```python
# tests/edge_cases/test_invalid_inputs.py
import pytest
from tests.tools.edge_case_generator import EdgeCaseGenerator

class TestInvalidInputHandling:
    """无效输入处理测试"""

    @pytest.mark.parametrize(
        "case",
        EdgeCaseGenerator.invalid_uuids(),
        ids=lambda c: c["desc"]
    )
    def test_invalid_uuid_in_task_complete(
        self,
        real_api_client,
        test_user_token,
        case
    ):
        """测试任务完成接口的无效UUID处理"""
        invalid_uuid = case["value"]

        response = real_api_client.patch(
            f"/tasks/{invalid_uuid}/complete",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )

        # 应该返回4xx错误，而不是500内部错误
        assert response.status_code in [400, 404, 422], \
            f"无效UUID [{case['desc']}] 应返回4xx，实际: {response.status_code}"

        # 响应应该是标准格式
        data = response.json()
        assert "code" in data, "响应应包含code字段"
        assert "message" in data, "响应应包含message字段"

        # 错误消息应该友好
        assert "uuid" in data["message"].lower() or "invalid" in data["message"].lower(), \
            f"错误消息应提示UUID无效: {data['message']}"

    @pytest.mark.parametrize(
        "case",
        EdgeCaseGenerator.boundary_strings(),
        ids=lambda c: c["desc"]
    )
    def test_boundary_string_in_task_content(
        self,
        real_api_client,
        test_user_token,
        case
    ):
        """测试任务内容的边界字符串处理"""
        content = case["value"]

        response = real_api_client.post(
            "/tasks/create",
            json={"content": content},
            headers={"Authorization": f"Bearer {test_user_token}"}
        )

        # 验证处理逻辑
        if content.strip() == "":
            # 空内容应该被拒绝
            assert response.status_code == 422, \
                f"空内容 [{case['desc']}] 应返回422"
        elif len(content) > 500:
            # 超长内容应该被拒绝或截断
            assert response.status_code in [422, 200], \
                f"超长内容 [{case['desc']}] 应被处理"
        elif "<script>" in content or "DROP TABLE" in content:
            # 攻击向量应该被转义
            assert response.status_code == 200, \
                f"攻击向量 [{case['desc']}] 应被正常处理（转义）"

            # 验证返回的内容已转义
            if response.status_code == 200:
                returned_content = response.json()["data"]["content"]
                assert "<script>" not in returned_content, \
                    "XSS脚本应该被转义"
```

**优势**：
1. ✅ 全面覆盖，预定义常见边界和攻击向量
2. ✅ 参数化测试，一个测试函数覆盖多个用例
3. ✅ 易于扩展，添加新用例只需修改生成器

## 测试组织架构

### 目录结构

```
tests/
├── conftest.py                          # 全局fixtures
├── pytest.ini                           # pytest配置
├── __init__.py
│
├── tools/                               # 测试工具库
│   ├── __init__.py
│   ├── endpoint_discovery.py           # 端点发现
│   ├── performance_tracker.py          # 性能追踪
│   ├── concurrent_tester.py            # 并发测试
│   └── edge_case_generator.py          # 边界用例生成
│
├── e2e/                                 # 端到端测试（100%覆盖）
│   ├── __init__.py
│   ├── test_task_endpoints.py          # 任务域（15个端点）
│   ├── test_points_endpoints.py        # 积分域（3个端点）
│   ├── test_reward_endpoints.py        # 奖励域（2个端点）
│   ├── test_top3_endpoints.py          # Top3域（2个端点）
│   ├── test_user_endpoints.py          # 用户域（5个端点）
│   ├── test_chat_endpoints.py          # 对话域（3个端点）
│   └── test_api_coverage.py            # 覆盖率验证（元测试）
│
├── performance/                         # 性能测试
│   ├── __init__.py
│   ├── test_api_response_time.py       # API响应时间
│   ├── test_database_queries.py        # 数据库查询性能
│   └── test_performance_regression.py  # 性能回归检测
│
├── concurrent/                          # 并发测试
│   ├── __init__.py
│   ├── test_points_concurrency.py      # 积分并发一致性
│   ├── test_top3_concurrency.py        # Top3并发唯一性
│   └── test_reward_concurrency.py      # 奖励并发幂等性
│
├── edge_cases/                          # 边界异常测试
│   ├── __init__.py
│   ├── test_invalid_inputs.py          # 无效输入
│   ├── test_boundary_values.py         # 边界值
│   ├── test_security_vectors.py        # 安全攻击向量
│   └── test_race_conditions.py         # 竞态条件
│
└── reports/                             # 测试报告
    ├── coverage_report.json             # 端点覆盖率报告
    ├── performance_baseline.json        # 性能基准数据
    └── test_quality_report.md           # 测试质量报告
```

### Pytest配置

```ini
# tests/pytest.ini
[pytest]
# 测试发现
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 输出配置
addopts =
    -v                          # 详细输出
    --tb=short                  # 简短traceback
    --strict-markers            # 严格标记检查
    --disable-warnings          # 禁用警告
    -p no:cacheprovider         # 禁用缓存（避免干扰）

# 标记定义
markers =
    e2e: 端到端测试（100%端点覆盖）
    performance: 性能测试
    concurrent: 并发测试
    edge_case: 边界异常测试
    slow: 慢速测试（>5秒）
    critical: 关键路径测试

# 超时配置
timeout = 300                    # 单个测试最大5分钟

# 异步支持
asyncio_mode = auto
```

## 集成策略

### CI/CD流程集成

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python & UV
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: uv sync

      # 阶段1：快速反馈测试（<2分钟）
      - name: Run critical tests
        run: uv run pytest -m "critical and not slow"

      # 阶段2：完整功能测试（<5分钟）
      - name: Run E2E tests
        run: uv run pytest tests/e2e/

      # 阶段3：性能测试（<3分钟）
      - name: Run performance tests
        run: uv run pytest tests/performance/

      # 阶段4：并发测试（<2分钟）
      - name: Run concurrent tests
        run: uv run pytest tests/concurrent/

      # 阶段5：边界测试（<2分钟）
      - name: Run edge case tests
        run: uv run pytest tests/edge_cases/

      # 生成覆盖率报告
      - name: Generate coverage report
        run: |
          uv run pytest tests/e2e/test_api_coverage.py
          cat tests/reports/coverage_report.json

      # 上传性能基准
      - name: Upload performance baseline
        uses: actions/upload-artifact@v3
        with:
          name: performance-baseline
          path: tests/reports/performance_baseline.json
```

## 成功标准

### 定量指标

1. **端点覆盖率 = 100%**
   - 验证方式：`test_api_coverage.py` 必须通过
   - 测量方式：`EndpointDiscovery.generate_coverage_report()`

2. **性能SLA达标率 > 95%**
   - P95响应时间 < 200ms
   - P99响应时间 < 500ms
   - 验证方式：所有`tests/performance/`测试通过

3. **并发测试通过率 = 100%**
   - 无数据一致性错误
   - 无死锁或超时
   - 验证方式：所有`tests/concurrent/`测试通过

4. **测试套件执行时间 < 5分钟**
   - 快速反馈，保证开发效率

### 定性指标

1. **测试稳定性**
   - 无flaky测试（不稳定测试）
   - 连续10次运行全部通过

2. **测试可维护性**
   - 测试代码清晰易读
   - 工具函数高度复用

3. **文档完善性**
   - 测试策略文档完整
   - 每个测试都有清晰的文档字符串

---

**设计状态**：待审批
**创建日期**：2025-10-25
**最后更新**：2025-10-25
