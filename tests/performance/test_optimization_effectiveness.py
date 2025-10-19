"""
性能优化效果测试

该模块测试各种性能优化策略的实际效果，包括：
1. 异常处理优化
2. 日志记录优化
3. 快速验证优化
4. 批量操作优化
"""

import time
import os
import sys
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.base import BaseService
from src.services.base_optimized import OptimizedBaseService
from src.services.exceptions import ValidationException, ResourceNotFoundException
from src.services.performance_optimization import (
    FastExceptionHandler,
    fast_validate_required,
    performance_monitor,
    conditional_logging
)


class PerformanceComparisonTest:
    """性能对比测试类"""

    def __init__(self):
        self.iterations = 1000
        self.results = {}

    def measure_execution_time(self, func, *args, **kwargs) -> tuple:
        """
        测量函数执行时间

        Returns:
            (执行结果, 执行时间毫秒)
        """
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result, (time.perf_counter() - start_time) * 1000
        except Exception as e:
            return e, (time.perf_counter() - start_time) * 1000

    def test_exception_creation_performance(self):
        """测试异常创建性能对比"""
        print("\n=== 异常创建性能对比测试 ===")

        # 原始异常创建方式
        def create_original_exception():
            return ValidationException(
                field="test_field",
                value="invalid_value",
                message="验证失败",
                user_message="用户友好的错误消息"
            )

        # 优化异常创建方式
        def create_optimized_exception():
            handler = FastExceptionHandler()
            return handler.fast_validation_error(
                field="test_field",
                value="invalid_value",
                user_message="用户友好的错误消息"
            )

        # 测试原始方式
        original_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_execution_time(create_original_exception)
            original_times.append(exec_time)

        # 测试优化方式
        optimized_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_execution_time(create_optimized_exception)
            optimized_times.append(exec_time)

        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_original - avg_optimized) / avg_original) * 100

        print(f"原始异常创建平均时间: {avg_original:.3f}μs")
        print(f"优化异常创建平均时间: {avg_optimized:.3f}μs")
        print(f"性能提升: {improvement:.1f}%")

        self.results["exception_creation"] = {
            "original": avg_original,
            "optimized": avg_optimized,
            "improvement": improvement
        }

    def test_validation_performance(self):
        """测试验证性能对比"""
        print("\n=== 验证性能对比测试 ===")

        test_data = {"name": "test", "value": 123}
        required_fields = ["name", "value", "type"]  # 缺少type字段

        # 原始验证方式（模拟BaseService中的方式）
        def original_validation():
            try:
                for field in required_fields:
                    if field not in test_data or test_data[field] is None:
                        raise ValidationException(
                            field=field,
                            value=test_data.get(field),
                            message=f"Missing required field: {field}",
                            user_message=f"缺少必填字段: {field}"
                        )
                return True
            except Exception:
                return False

        # 优化验证方式
        def optimized_validation():
            try:
                fast_validate_required(test_data, required_fields)
                return True
            except Exception:
                return False

        # 测试原始方式
        original_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_execution_time(original_validation)
            original_times.append(exec_time)

        # 测试优化方式
        optimized_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_execution_time(optimized_validation)
            optimized_times.append(exec_time)

        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_original - avg_optimized) / avg_original) * 100

        print(f"原始验证平均时间: {avg_original:.3f}μs")
        print(f"优化验证平均时间: {avg_optimized:.3f}μs")
        print(f"性能提升: {improvement:.1f}%")

        self.results["validation"] = {
            "original": avg_original,
            "optimized": avg_optimized,
            "improvement": improvement
        }

    def test_service_instantiation_performance(self):
        """测试服务实例化性能对比"""
        print("\n=== 服务实例化性能对比测试 ===")

        # 测试原始BaseService
        def create_original_service():
            return BaseService()

        # 测试优化版BaseService
        def create_optimized_service():
            return OptimizedBaseService(enable_detailed_logging=False)

        # 测试原始服务
        original_times = []
        for _ in range(100):  # 减少迭代次数，因为服务创建开销较大
            _, exec_time = self.measure_execution_time(create_original_service)
            original_times.append(exec_time)

        # 测试优化服务
        optimized_times = []
        for _ in range(100):
            _, exec_time = self.measure_execution_time(create_optimized_service)
            optimized_times.append(exec_time)

        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_original - avg_optimized) / avg_original) * 100

        print(f"原始服务实例化平均时间: {avg_original:.3f}ms")
        print(f"优化服务实例化平均时间: {avg_optimized:.3f}ms")
        print(f"性能提升: {improvement:.1f}%")

        self.results["service_instantiation"] = {
            "original": avg_original,
            "optimized": avg_optimized,
            "improvement": improvement
        }

    def test_logging_performance(self):
        """测试日志性能对比"""
        print("\n=== 日志性能对比测试 ===")

        # 创建测试服务
        original_service = BaseService()
        optimized_service = OptimizedBaseService(enable_detailed_logging=False)

        # 测试原始服务日志
        def original_logging():
            original_service._log_info("测试日志消息", extra_data={"key": "value"})

        # 测试优化服务日志
        def optimized_logging():
            optimized_service._log_info("测试日志消息", extra_data={"key": "value"})

        # 测试原始日志
        original_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_execution_time(original_logging)
            original_times.append(exec_time)

        # 测试优化日志
        optimized_times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_execution_time(optimized_logging)
            optimized_times.append(exec_time)

        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_original - avg_optimized) / avg_original) * 100

        print(f"原始日志记录平均时间: {avg_original:.3f}μs")
        print(f"优化日志记录平均时间: {avg_optimized:.3f}μs")
        print(f"性能提升: {improvement:.1f}%")

        self.results["logging"] = {
            "original": avg_original,
            "optimized": avg_optimized,
            "improvement": improvement
        }

    def test_error_handling_performance(self):
        """测试错误处理性能对比"""
        print("\n=== 错误处理性能对比测试 ===")

        # 创建测试服务
        original_service = BaseService()
        optimized_service = OptimizedBaseService(enable_detailed_logging=False)

        test_error = Exception("测试错误")

        # 测试原始错误处理
        def original_error_handling():
            try:
                original_service._handle_repository_error(test_error, "test_operation")
            except Exception:
                pass  # 忽略异常，只测试处理性能

        # 测试优化错误处理
        def optimized_error_handling():
            try:
                optimized_service._handle_repository_error_fast(test_error, "test_operation")
            except Exception:
                pass  # 忽略异常，只测试处理性能

        # 测试原始错误处理
        original_times = []
        for _ in range(100):  # 减少迭代次数，因为错误处理开销较大
            _, exec_time = self.measure_execution_time(original_error_handling)
            original_times.append(exec_time)

        # 测试优化错误处理
        optimized_times = []
        for _ in range(100):
            _, exec_time = self.measure_execution_time(optimized_error_handling)
            optimized_times.append(exec_time)

        avg_original = sum(original_times) / len(original_times)
        avg_optimized = sum(optimized_times) / len(optimized_times)
        improvement = ((avg_original - avg_optimized) / avg_original) * 100

        print(f"原始错误处理平均时间: {avg_original:.3f}ms")
        print(f"优化错误处理平均时间: {avg_optimized:.3f}ms")
        print(f"性能提升: {improvement:.1f}%")

        self.results["error_handling"] = {
            "original": avg_original,
            "optimized": avg_optimized,
            "improvement": improvement
        }

    def run_all_tests(self):
        """运行所有性能对比测试"""
        print("🚀 开始性能优化效果测试")
        print("="*60)

        self.test_exception_creation_performance()
        self.test_validation_performance()
        self.test_service_instantiation_performance()
        self.test_logging_performance()
        self.test_error_handling_performance()

        self._print_summary()

    def _print_summary(self):
        """打印测试总结"""
        print("\n" + "="*60)
        print("性能优化效果总结")
        print("="*60)

        total_improvement = 0
        test_count = 0

        for test_name, result in self.results.items():
            improvement = result["improvement"]
            if improvement > 0:
                print(f"✅ {test_name}: 性能提升 {improvement:.1f}%")
                total_improvement += improvement
            else:
                print(f"❌ {test_name}: 性能下降 {abs(improvement):.1f}%")
            test_count += 1

        if test_count > 0:
            avg_improvement = total_improvement / test_count
            print(f"\n📊 平均性能提升: {avg_improvement:.1f}%")

        # 优化建议
        print("\n🎯 优化建议:")
        if self.results.get("exception_handling", {}).get("improvement", 0) > 50:
            print("1. 异常处理优化效果显著，建议在生产环境中使用")
        if self.results.get("logging", {}).get("improvement", 0) > 30:
            print("2. 日志优化效果明显，建议在高并发场景下启用优化模式")
        if self.results.get("validation", {}).get("improvement", 0) > 20:
            print("3. 验证优化有效，建议在数据密集型操作中使用快速验证")


def main():
    """主函数"""
    test = PerformanceComparisonTest()
    test.run_all_tests()
    print("\n✅ 性能优化效果测试完成！")


if __name__ == "__main__":
    main()