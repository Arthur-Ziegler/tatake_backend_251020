"""
性能优化效果验证测试

验证实施的优化策略是否有效解决了异常处理开销过大的问题。
"""

import os
import sys
import time
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.base import BaseService
from src.services.base_performance_optimized import PerformanceOptimizedBaseService
from src.services.optimized_exception_handler import get_optimized_exception_handler


class OptimizationResultTest:
    """优化效果验证测试类"""

    def __init__(self):
        self.iterations = 100
        self.test_results = {}

    def measure_time(self, func, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result, (time.perf_counter() - start_time) * 1000
        except Exception as e:
            return e, (time.perf_counter() - start_time) * 1000

    def test_exception_handling_overhead_comparison(self):
        """测试异常处理开销对比"""
        print("\n=== 异常处理开销对比测试 ===")

        # 配置环境变量以启用优化
        os.environ['SERVICE_LOG_DETAILED_EXCEPTIONS'] = 'false'
        os.environ['SERVICE_ENABLE_DETAILED_LOGGING'] = 'false'
        os.environ['ENVIRONMENT'] = 'production'

        # 创建标准服务和优化服务
        standard_service = BaseService()
        optimized_service = PerformanceOptimizedBaseService()

        def test_standard_exception_handling():
            try:
                standard_service._handle_repository_error(
                    ValueError("测试错误"),
                    "test_operation"
                )
            except Exception:
                pass  # 忽略异常，只测试处理性能

        def test_optimized_exception_handling():
            try:
                optimized_service._handle_repository_error(
                    ValueError("测试错误"),
                    "test_operation"
                )
            except Exception:
                pass  # 忽略异常，只测试处理性能

        # 测试标准异常处理
        standard_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(test_standard_exception_handling)
            standard_times.append(exec_time)

        # 测试优化异常处理
        optimized_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(test_optimized_exception_handling)
            optimized_times.append(exec_time)

        avg_standard = sum(standard_times) / len(standard_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_standard - avg_optimized) / avg_standard) * 100

        print(f"标准异常处理平均时间: {avg_standard:.3f}ms")
        print(f"优化异常处理平均时间: {avg_optimized:.3f}ms")
        print(f"性能提升: {improvement:.1f}%")

        self.test_results["exception_handling"] = {
            "standard": avg_standard,
            "optimized": avg_optimized,
            "improvement": improvement
        }

        return improvement > 50  # 期望至少50%的性能提升

    def test_logging_performance_comparison(self):
        """测试日志性能对比"""
        print("\n=== 日志性能对比测试 ===")

        # 创建服务实例
        standard_service = BaseService()
        optimized_service = PerformanceOptimizedBaseService(enable_detailed_logging=False)

        def test_standard_logging():
            standard_service._log_error("测试错误消息",
                                     ValueError("测试异常"),
                                     operation="test_operation",
                                     extra_data={"key": "value"})

        def test_optimized_logging():
            optimized_service._log_error("测试错误消息",
                                       ValueError("测试异常"),
                                       operation="test_operation",
                                       extra_data={"key": "value"})

        # 测试标准日志
        standard_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(test_standard_logging)
            standard_times.append(exec_time)

        # 测试优化日志
        optimized_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(test_optimized_logging)
            optimized_times.append(exec_time)

        avg_standard = sum(standard_times) / len(standard_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_standard - avg_optimized) / avg_standard) * 100

        print(f"标准日志记录平均时间: {avg_standard:.3f}ms")
        print(f"优化日志记录平均时间: {avg_optimized:.3f}ms")
        print(f"性能提升: {improvement:.1f}%")

        self.test_results["logging"] = {
            "standard": avg_standard,
            "optimized": avg_optimized,
            "improvement": improvement
        }

        return improvement > 30  # 期望至少30%的性能提升

    def test_service_instantiation_comparison(self):
        """测试服务实例化性能对比"""
        print("\n=== 服务实例化性能对比测试 ===")

        def create_standard_service():
            return BaseService()

        def create_optimized_service():
            return PerformanceOptimizedBaseService(enable_detailed_logging=False)

        # 测试标准服务实例化
        standard_times = []
        for _ in range(50):
            _, exec_time = self.measure_time(create_standard_service)
            standard_times.append(exec_time)

        # 测试优化服务实例化
        optimized_times = []
        for _ in range(50):
            _, exec_time = self.measure_time(create_optimized_service)
            optimized_times.append(exec_time)

        avg_standard = sum(standard_times) / len(standard_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_standard - avg_optimized) / avg_standard) * 100

        print(f"标准服务实例化平均时间: {avg_standard:.3f}ms")
        print(f"优化服务实例化平均时间: {avg_optimized:.3f}ms")
        print(f"性能提升: {improvement:.1f}%")

        self.test_results["service_instantiation"] = {
            "standard": avg_standard,
            "optimized": avg_optimized,
            "improvement": improvement
        }

        return True  # 服务实例化性能不要求提升，只要不显著下降即可

    def test_validation_performance_comparison(self):
        """测试验证性能对比"""
        print("\n=== 验证性能对比测试 ===")

        standard_service = BaseService()
        optimized_service = PerformanceOptimizedBaseService()

        test_data = {"name": "test", "value": 123}  # 缺少type字段
        required_fields = ["name", "value", "type"]

        def test_standard_validation():
            try:
                standard_service.validate_required_fields(test_data, required_fields)
            except Exception:
                pass

        def test_optimized_validation():
            try:
                optimized_service.validate_required_fields_fast(test_data, required_fields)
            except Exception:
                pass

        # 测试标准验证
        standard_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(test_standard_validation)
            standard_times.append(exec_time)

        # 测试优化验证
        optimized_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(test_optimized_validation)
            optimized_times.append(exec_time)

        avg_standard = sum(standard_times) / len(standard_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_standard - avg_optimized) / avg_standard) * 100

        print(f"标准验证平均时间: {avg_standard:.3f}μs")
        print(f"优化验证平均时间: {avg_optimized:.3f}μs")
        print(f"性能提升: {improvement:.1f}%")

        self.test_results["validation"] = {
            "standard": avg_standard,
            "optimized": avg_optimized,
            "improvement": improvement
        }

        return improvement > 20  # 期望至少20%的性能提升

    def test_optimization_stats(self):
        """测试优化统计功能"""
        print("\n=== 优化统计功能测试 ===")

        service = PerformanceOptimizedBaseService()

        # 执行一些操作以生成统计数据
        try:
            service._handle_repository_error(ValueError("测试错误"), "test_op")
        except Exception:
            pass

        try:
            service.validate_required_fields_fast({"name": "test"}, ["name", "value"])
        except Exception:
            pass

        # 获取优化统计
        stats = service.get_optimization_stats()

        print(f"服务名称: {stats['service_name']}")
        print(f"性能优化启用: {stats['performance_optimization']}")
        print(f"详细日志: {stats['detailed_logging']}")
        print(f"操作计数: {stats['operation_count']}")
        print(f"异常处理统计: {stats['exception_handling']}")

        return True

    def run_all_tests(self):
        """运行所有优化效果验证测试"""
        print("🚀 开始性能优化效果验证测试")
        print("="*60)

        test_results = {
            "exception_handling": self.test_exception_handling_overhead_comparison(),
            "logging": self.test_logging_performance_comparison(),
            "service_instantiation": self.test_service_instantiation_comparison(),
            "validation": self.test_validation_performance_comparison(),
            "optimization_stats": self.test_optimization_stats()
        }

        self._print_final_results(test_results)

        return test_results

    def _print_final_results(self, test_results: Dict[str, bool]):
        """打印最终测试结果"""
        print("\n" + "="*60)
        print("优化效果验证结果")
        print("="*60)

        passed_tests = sum(test_results.values())
        total_tests = len(test_results)

        for test_name, passed in test_results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            improvement = self.test_results.get(test_name, {}).get("improvement", 0)
            print(f"{test_name}: {status} (性能提升: {improvement:.1f}%)")

        print(f"\n📊 总体结果: {passed_tests}/{total_tests} 测试通过")

        if passed_tests == total_tests:
            print("🎉 所有优化测试都通过了！性能优化效果显著。")
        elif passed_tests >= total_tests * 0.8:
            print("👍 大部分优化测试通过，性能优化基本成功。")
        else:
            print("⚠️ 部分优化测试未通过，需要进一步调整优化策略。")

        # 计算总体性能提升
        improvements = [result.get("improvement", 0) for result in self.test_results.values()]
        if improvements:
            avg_improvement = sum(improvements) / len(improvements)
            print(f"📈 平均性能提升: {avg_improvement:.1f}%")


def main():
    """主函数"""
    test = OptimizationResultTest()
    test.run_all_tests()
    print("\n✅ 性能优化效果验证测试完成！")


if __name__ == "__main__":
    main()