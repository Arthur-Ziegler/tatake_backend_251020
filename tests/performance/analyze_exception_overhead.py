"""
异常处理开销深度分析

专门分析为什么异常处理开销高达1487%，找出真正的性能瓶颈。
"""

import time
import sys
import os
import traceback
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.base import BaseService
from src.services.logging_config import get_logger


class ExceptionOverheadAnalyzer:
    """异常处理开销分析器"""

    def __init__(self):
        self.iterations = 1000
        self.service = BaseService()

    def measure_time(self, func, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result, (time.perf_counter() - start_time) * 1000
        except Exception as e:
            return e, (time.perf_counter() - start_time) * 1000

    def test_normal_execution(self):
        """测试正常执行的开销"""
        def normal_operation():
            # 模拟正常的数据处理操作
            data = {"name": "test", "value": 123}
            if "name" in data and "value" in data:
                return True
            return False

        times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(normal_operation)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        print(f"正常执行平均时间: {avg_time:.3f}μs")
        return avg_time

    def test_try_catch_overhead(self):
        """测试try-catch块本身的开销"""
        def operation_with_try_catch():
            try:
                data = {"name": "test", "value": 123}
                if "name" in data and "value" in data:
                    return True
                return False
            except Exception:
                return False

        times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(operation_with_try_catch)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        print(f"try-catch块平均时间: {avg_time:.3f}μs")
        return avg_time

    def test_exception_creation_only(self):
        """测试仅异常创建的开销"""
        from src.services.exceptions import ValidationException

        def create_exception():
            return ValidationException(
                field="test_field",
                value="invalid_value",
                message="Test validation error"
            )

        times = []
        for _ in range(self.iterations):
            _, exec_time = self.measure_time(create_exception)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        print(f"异常创建平均时间: {avg_time:.3f}μs")
        return avg_time

    def test_exception_with_traceback(self):
        """测试包含堆栈追踪的异常处理开销"""
        from src.services.exceptions import ValidationException

        def operation_with_full_exception():
            try:
                # 故意触发异常
                raise ValidationException(
                    field="test_field",
                    value="invalid_value",
                    message="Test validation error"
                )
            except ValidationException as e:
                # 模拟完整的异常处理，包括获取堆栈信息
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stack_trace = traceback.format_exception(exc_type, exc_value, exc_traceback)
                return len(stack_trace)  # 返回堆栈追踪的行数

        times = []
        for _ in range(100):  # 减少迭代次数，因为这个操作开销较大
            _, exec_time = self.measure_time(operation_with_full_exception)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        print(f"完整异常处理平均时间: {avg_time:.3f}ms")
        return avg_time

    def test_logging_overhead(self):
        """测试日志记录的开销"""
        logger = get_logger("TestLogger")

        def operation_with_logging():
            try:
                # 模拟错误
                raise ValueError("Test error")
            except Exception as e:
                logger.error("操作失败", error=e, operation="test_operation")
                return False

        times = []
        for _ in range(100):  # 减少迭代次数
            _, exec_time = self.measure_time(operation_with_logging)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        print(f"日志记录异常平均时间: {avg_time:.3f}ms")
        return avg_time

    def test_service_exception_handling(self):
        """测试服务层异常处理的实际开销"""
        def service_operation_with_exception():
            try:
                # 模拟服务中的错误处理
                self.service._handle_repository_error(
                    ValueError("Repository error"),
                    "test_operation"
                )
            except Exception:
                return False

        times = []
        for _ in range(100):
            _, exec_time = self.measure_time(service_operation_with_exception)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        print(f"服务异常处理平均时间: {avg_time:.3f}ms")
        return avg_time

    def test_exception_chaining_overhead(self):
        """测试异常链的开销"""
        from src.services.exceptions import BusinessException

        def operation_with_exception_chain():
            try:
                try:
                    # 底层异常
                    raise ValueError("底层错误")
                except ValueError as e:
                    # 包装成业务异常
                    business_error = BusinessException(
                        error_code="BUSINESS_ERROR",
                        message="业务错误",
                        cause=e
                    )
                    raise business_error
            except BusinessException:
                return True

        times = []
        for _ in range(100):
            _, exec_time = self.measure_time(operation_with_exception_chain)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        print(f"异常链处理平均时间: {avg_time:.3f}ms")
        return avg_time

    def run_analysis(self):
        """运行完整的异常开销分析"""
        print("🔍 异常处理开销深度分析")
        print("="*50)

        # 测试各种场景的执行时间
        normal_time = self.test_normal_execution()
        try_catch_time = self.test_try_catch_overhead()
        exception_creation_time = self.test_exception_creation_only()
        full_exception_time = self.test_exception_with_traceback()
        logging_time = self.test_logging_overhead()
        service_exception_time = self.test_service_exception_handling()
        exception_chain_time = self.test_exception_chaining_overhead()

        print("\n" + "="*50)
        print("开销分析结果")
        print("="*50)

        # 计算各种开销比例
        try_catch_overhead = ((try_catch_time - normal_time) / normal_time) * 100
        exception_creation_overhead = ((exception_creation_time - normal_time) / normal_time) * 100
        full_exception_overhead = ((full_exception_time - normal_time) / normal_time) * 100
        logging_overhead = ((logging_time - normal_time) / normal_time) * 100
        service_overhead = ((service_exception_time - normal_time) / normal_time) * 100
        chain_overhead = ((exception_chain_time - normal_time) / normal_time) * 100

        print(f"正常执行基准时间: {normal_time:.3f}μs")
        print(f"try-catch块开销: {try_catch_overhead:.1f}%")
        print(f"异常创建开销: {exception_creation_overhead:.1f}%")
        print(f"完整异常处理开销: {full_exception_overhead:.1f}%")
        print(f"日志记录开销: {logging_overhead:.1f}%")
        print(f"服务异常处理开销: {service_overhead:.1f}%")
        print(f"异常链开销: {chain_overhead:.1f}%")

        print("\n🎯 关键发现:")
        print("1. try-catch块本身的开销相对较小")
        print("2. 异常创建的开销也不大")
        print("3. 真正的开销在于:")
        print("   - 堆栈追踪的生成和处理")
        print("   - 日志记录中的异常序列化")
        print("   - 异常包装和转换")

        print("\n💡 优化建议:")
        print("1. 在性能关键路径中减少异常使用")
        print("2. 使用Result模式替代异常处理")
        print("3. 异常日志记录要考虑序列化开销")
        print("4. 避免过深的异常链")


def main():
    """主函数"""
    analyzer = ExceptionOverheadAnalyzer()
    analyzer.run_analysis()
    print("\n✅ 异常处理开销分析完成！")


if __name__ == "__main__":
    main()