"""
性能追踪器

用于测量和追踪API端点的性能指标，支持基准对比和回归检测。

作者：TaKeKe团队
版本：1.0.0 - 性能基准测试工具
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from statistics import median, mean, quantiles

from fastapi import FastAPI


@dataclass
class PerformanceStats:
    """性能统计数据"""
    p50: float = 0.0  # 50分位数（中位数）
    p95: float = 0.0  # 95分位数
    p99: float = 0.0  # 99分位数
    min: float = 0.0  # 最小值
    max: float = 0.0  # 最大值
    mean: float = 0.0  # 平均值
    count: int = 0  # 测量次数
    timestamp: float = 0.0  # 测量时间戳


@dataclass
class BaselineData:
    """基准数据结构"""
    stats: PerformanceStats
    endpoint: str
    created_at: float
    updated_at: float


class PerformanceTracker:
    """性能追踪器"""

    def __init__(self, baseline_file: str = "tests/reports/performance_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.measurements: List[float] = []
        self.endpoint_name: Optional[str] = None

    def set_endpoint(self, endpoint: str):
        """设置当前测量的端点名称"""
        self.endpoint_name = endpoint

    def measure(self, func: Callable, *args, **kwargs) -> Any:
        """
        测量函数执行时间

        Args:
            func: 要测量的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数的返回值
        """
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = (time.perf_counter() - start_time) * 1000  # 转换为毫秒
            self.measurements.append(duration)

    def measure_sync(self, func: Callable, *args, **kwargs) -> Any:
        """
        测量同步函数执行时间（别名）

        Args:
            func: 要测量的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数的返回值
        """
        return self.measure(func, *args, **kwargs)

    async def measure_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        测量异步函数执行时间

        Args:
            func: 要测量的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            异步函数的返回值
        """
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = (time.perf_counter() - start_time) * 1000  # 转换为毫秒
            self.measurements.append(duration)

    def get_statistics(self) -> PerformanceStats:
        """
        计算统计数据

        Returns:
            PerformanceStats: 性能统计数据
        """
        if not self.measurements:
            return PerformanceStats()

        sorted_data = sorted(self.measurements)
        n = len(sorted_data)

        # 计算分位数
        p50 = median(sorted_data)
        p95 = sorted_data[int(0.95 * n)] if n >= 20 else sorted_data[-1]
        p99 = sorted_data[int(0.99 * n)] if n >= 100 else sorted_data[-1]

        return PerformanceStats(
            p50=p50,
            p95=p95,
            p99=p99,
            min=min(sorted_data),
            max=max(sorted_data),
            mean=mean(sorted_data),
            count=n,
            timestamp=time.time()
        )

    def reset(self):
        """重置测量数据"""
        self.measurements.clear()
        self.endpoint_name = None

    def load_baseline(self) -> Dict[str, BaselineData]:
        """
        加载基准数据

        Returns:
            Dict[str, BaselineData]: 端点到基准数据的映射
        """
        if not self.baseline_file.exists():
            return {}

        try:
            with open(self.baseline_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            baseline = {}
            for endpoint, baseline_dict in data.items():
                stats_dict = baseline_dict['stats']
                stats = PerformanceStats(**stats_dict)
                baseline[endpoint] = BaselineData(
                    stats=stats,
                    endpoint=baseline_dict['endpoint'],
                    created_at=baseline_dict['created_at'],
                    updated_at=baseline_dict['updated_at']
                )
            return baseline
        except Exception as e:
            print(f"警告：无法加载基准数据文件 {self.baseline_file}: {e}")
            return {}

    def save_baseline(self, endpoint: str, stats: PerformanceStats):
        """
        保存基准数据

        Args:
            endpoint: 端点名称
            stats: 性能统计数据
        """
        # 确保目录存在
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载现有基准数据
        baseline = self.load_baseline()

        # 更新或添加新的基准数据
        current_time = time.time()
        if endpoint in baseline:
            baseline[endpoint].stats = stats
            baseline[endpoint].updated_at = current_time
        else:
            baseline[endpoint] = BaselineData(
                stats=stats,
                endpoint=endpoint,
                created_at=current_time,
                updated_at=current_time
            )

        # 保存到文件
        try:
            serializable_baseline = {}
            for ep, baseline_data in baseline.items():
                serializable_baseline[ep] = {
                    'stats': asdict(baseline_data.stats),
                    'endpoint': baseline_data.endpoint,
                    'created_at': baseline_data.created_at,
                    'updated_at': baseline_data.updated_at
                }

            with open(self.baseline_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_baseline, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"错误：无法保存基准数据到文件 {self.baseline_file}: {e}")

    def compare_with_baseline(
        self,
        endpoint: str,
        regression_threshold: float = 1.2
    ) -> Dict[str, Any]:
        """
        与基准对比

        Args:
            endpoint: 端点名称
            regression_threshold: 回归阈值倍数（默认1.2表示20%的回归）

        Returns:
            Dict[str, Any]: 对比结果
        """
        stats = self.get_statistics()
        baseline = self.load_baseline()

        if endpoint not in baseline:
            # 首次测试，保存为基准
            self.save_baseline(endpoint, stats)
            return {
                "status": "baseline_created",
                "stats": asdict(stats),
                "message": f"为端点 {endpoint} 创建了性能基准"
            }

        baseline_stats = baseline[endpoint].stats

        # 计算回归检测
        p95_regression = stats.p95 > baseline_stats.p95 * regression_threshold
        p99_regression = stats.p99 > baseline_stats.p99 * regression_threshold
        mean_regression = stats.mean > baseline_stats.mean * regression_threshold

        has_regression = p95_regression or p99_regression or mean_regression

        result = {
            "status": "regression" if has_regression else "ok",
            "current": asdict(stats),
            "baseline": asdict(baseline_stats),
            "differences": {
                "p95": stats.p95 - baseline_stats.p95,
                "p99": stats.p99 - baseline_stats.p99,
                "mean": stats.mean - baseline_stats.mean,
                "p95_percent": ((stats.p95 / baseline_stats.p95) - 1) * 100 if baseline_stats.p95 > 0 else 0,
                "p99_percent": ((stats.p99 / baseline_stats.p99) - 1) * 100 if baseline_stats.p99 > 0 else 0,
                "mean_percent": ((stats.mean / baseline_stats.mean) - 1) * 100 if baseline_stats.mean > 0 else 0
            },
            "regression_detected": has_regression,
            "threshold": regression_threshold
        }

        if has_regression:
            result["message"] = f"端点 {endpoint} 检测到性能回归"
            if p95_regression:
                result["message"] += f" (P95: +{result['differences']['p95_percent']:.1f}%)"
            if p99_regression:
                result["message"] += f" (P99: +{result['differences']['p99_percent']:.1f}%)"
        else:
            improvement_p95 = ((baseline_stats.p95 / stats.p95) - 1) * 100 if stats.p95 > 0 else 0
            result["message"] = f"端点 {endpoint} 性能正常"
            if improvement_p95 > 5:
                result["message"] += f" (P95改善: {improvement_p95:.1f}%)"

        return result

    def get_all_baselines(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有基准数据的摘要

        Returns:
            Dict[str, Dict[str, Any]]: 所有基准数据的摘要
        """
        baseline = self.load_baseline()
        summary = {}

        for endpoint, baseline_data in baseline.items():
            stats = baseline_data.stats
            summary[endpoint] = {
                "p95": stats.p95,
                "p99": stats.p99,
                "mean": stats.mean,
                "count": stats.count,
                "created_at": baseline_data.created_at,
                "updated_at": baseline_data.updated_at,
                "last_measured": stats.timestamp
            }

        return summary


# pytest fixture
import pytest

@pytest.fixture
def perf_tracker():
    """性能追踪器fixture"""
    tracker = PerformanceTracker()
    yield tracker
    # 清理：如果有未保存的数据，可以选择自动保存
    if tracker.measurements and tracker.endpoint_name:
        stats = tracker.get_statistics()
        tracker.save_baseline(tracker.endpoint_name, stats)


def main():
    """命令行测试入口"""
    tracker = PerformanceTracker()

    # 模拟一些测量数据
    import random
    tracker.set_endpoint("test GET /api/sample")

    # 模拟100次请求，响应时间在100-300ms之间
    for _ in range(100):
        duration = random.uniform(100, 300)  # 模拟100-300ms的响应时间
        tracker.measurements.append(duration)

    stats = tracker.get_statistics()
    print(f"性能统计数据:")
    print(f"  P50: {stats.p50:.2f}ms")
    print(f"  P95: {stats.p95:.2f}ms")
    print(f"  P99: {stats.p99:.2f}ms")
    print(f"  平均: {stats.mean:.2f}ms")
    print(f"  最小: {stats.min:.2f}ms")
    print(f"  最大: {stats.max:.2f}ms")
    print(f"  次数: {stats.count}")

    # 与基准对比
    comparison = tracker.compare_with_baseline("test GET /api/sample")
    print(f"\n基准对比结果: {comparison['status']}")
    print(f"消息: {comparison['message']}")

    # 获取所有基准数据
    all_baselines = tracker.get_all_baselines()
    print(f"\n所有基准数据 ({len(all_baselines)} 个端点):")
    for endpoint, summary in all_baselines.items():
        print(f"  {endpoint}: P95={summary['p95']:.2f}ms, P99={summary['p99']:.2f}ms")


if __name__ == "__main__":
    main()