"""
测试工具库

提供API覆盖率分析、性能测试、并发测试、边界测试等专业工具。

模块：
- endpoint_discovery: API端点发现和覆盖率分析
- performance_tracker: 性能追踪和基准测试
- concurrent_tester: 并发负载测试
- edge_case_generator: 边界条件测试用例生成

作者：TaKeKe团队
版本：1.0.0 - 测试工具套件
"""

from .endpoint_discovery import EndpointDiscovery
from .performance_tracker import PerformanceTracker, PerformanceStats
from .concurrent_tester import ConcurrentTester, ConcurrentResult
from .edge_case_generator import EdgeCaseGenerator, TestCase

__all__ = [
    "EndpointDiscovery",
    "PerformanceTracker",
    "PerformanceStats",
    "ConcurrentTester",
    "ConcurrentResult",
    "EdgeCaseGenerator",
    "TestCase"
]

__version__ = "1.0.0"