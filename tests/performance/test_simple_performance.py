"""
简化的服务层性能测试

该测试文件包含对服务层核心组件的性能测试，用于识别性能瓶颈。
"""

import sys
import os
import time
import asyncio
import threading
from typing import Dict, Any, List
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.base import BaseService
from src.services.logging_config import get_logger, operation_logger, performance_logger
from src.services.exceptions import BusinessException, ValidationException

# 设置测试环境变量
os.environ['SERVICE_LOG_LEVEL'] = 'ERROR'  # 减少日志输出
os.environ['SERVICE_LOG_CONSOLE'] = 'false'
os.environ['SERVICE_LOG_FILE'] = 'false'


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        self.results = {}

    def measure_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000  # ms
        return result, execution_time

    def measure_memory(self):
        """简单的内存测量（使用tracemalloc）"""
        import tracemalloc
        import gc

        tracemalloc.start()
        gc.collect()  # 强制垃圾回收

        # 执行一些操作来分配内存
        dummy_data = []
        for i in range(1000):
            dummy_data.append({
                "id": i,
                "data": "x" * 100,
                "timestamp": datetime.now().isoformat()
            })

        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()

        return len(str(dummy_data)), len(snapshot.statistics("lineno"))

    def record_result(self, test_name: str, metric_name: str, value: float, unit: str = "ms"):
        """记录测试结果"""
        if test_name not in self.results:
            self.results[test_name] = {}
        self.results[test_name][metric_name] = f"{value:.2f}{unit}"

    def print_summary(self):
        """打印测试结果摘要"""
        print("\n" + "="*60)
        print("性能测试结果摘要")
        print("="*60)

        for test_name, metrics in self.results.items():
            print(f"\n🔍 {test_name}:")
            for metric_name, value in metrics.items():
                print(f"   {metric_name}: {value}")


class TestServiceCreationPerformance:
    """服务创建性能测试"""

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()

    def test_service_instantiation(self):
        """测试服务实例化性能"""
        print("\n=== 服务实例化性能测试 ===")

        # 测试BaseService实例化
        times = []
        for i in range(50):
            _, exec_time = self.analyzer.measure_time(BaseService)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        self.analyzer.record_result("BaseService实例化", "平均时间", avg_time)
        self.analyzer.record_result("BaseService实例化", "最小时间", min_time)
        self.analyzer.record_result("BaseService实例化", "最大时间", max_time)

        print(f"BaseService实例化性能:")
        print(f"  平均时间: {avg_time:.2f}ms")
        print(f"  最快时间: {min_time:.2f}ms")
        print(f"  最慢时间: {max_time:.2f}ms")

        # 性能评估
        if avg_time > 10:
            print("⚠️ 服务实例化较慢，需要优化")
        else:
            print("✅ 服务实例化性能良好")

        return avg_time

    def test_multiple_services_creation(self):
        """测试多个服务创建性能"""
        print("\n=== 多服务创建性能测试 ===")

        times = []
        for i in range(30):
            _, exec_time = self.analyzer.measure_time(self._create_multiple_services)
            times.append(exec_time)

        avg_time = sum(times) / len(times)
        self.analyzer.record_result("多服务创建", "平均时间", avg_time)

        print(f"创建多个服务平均时间: {avg_time:.2f}ms")

        if avg_time > 50:
            print("⚠️ 多服务创建性能较慢")
        else:
            print("✅ 多服务创建性能良好")

        return avg_time

    def _create_multiple_services(self):
        """创建多个服务实例"""
        services = []
        for i in range(5):
            service = BaseService()
            services.append(service)
        return services


class TestLoggingSystemPerformance:
    """日志系统性能测试"""

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.service = BaseService()

    def test_basic_logging(self):
        """测试基本日志性能"""
        print("\n=== 基本日志性能测试 ===")

        # 测试INFO日志
        info_times = []
        for i in range(100):
            _, exec_time = self.analyzer.measure_time(
                self.service._log_info, f"测试日志消息 {i}", test_data=i
            )
            info_times.append(exec_time)

        avg_info_time = sum(info_times) / len(info_times)
        self.analyzer.record_result("INFO日志", "平均时间", avg_info_time, "μs")

        # 测试ERROR日志
        error_times = []
        test_exception = Exception("测试异常")
        for i in range(50):
            _, exec_time = self.analyzer.measure_time(
                self.service._log_error, f"测试错误日志 {i}", error=test_exception
            )
            error_times.append(exec_time)

        avg_error_time = sum(error_times) / len(error_times)
        self.analyzer.record_result("ERROR日志", "平均时间", avg_error_time)

        print(f"INFO日志平均时间: {avg_info_time*1000:.2f}μs")
        print(f"ERROR日志平均时间: {avg_error_time:.2f}ms")

        # 性能评估
        if avg_info_time > 5:  # 5ms阈值
            print("⚠️ INFO日志性能较慢")
        else:
            print("✅ INFO日志性能良好")

        if avg_error_time > 10:  # 10ms阈值
            print("⚠️ ERROR日志性能较慢")
        else:
            print("✅ ERROR日志性能良好")

        return {"info": avg_info_time, "error": avg_error_time}

    def test_operation_logging(self):
        """测试操作日志性能"""
        print("\n=== 操作日志性能测试 ===")

        operation_times = []
        for i in range(50):
            _, exec_time = self.analyzer.measure_time(
                self._log_operation_cycle, f"测试操作 {i}", f"user_{i}"
            )
            operation_times.append(exec_time)

        avg_time = sum(operation_times) / len(operation_times)
        self.analyzer.record_result("操作日志", "平均时间", avg_time)

        print(f"操作日志平均时间: {avg_time:.2f}ms")

        if avg_time > 20:
            print("⚠️ 操作日志性能较慢")
        else:
            print("✅ 操作日志性能良好")

        return avg_time

    def _log_operation_cycle(self, operation_name: str, user_id: str):
        """完整的操作日志周期"""
        self.service._log_operation_start(operation_name, user_id=user_id)
        self.service._log_operation_success(operation_name, duration_ms=100, user_id=user_id)

    def test_logging_decorators(self):
        """测试日志装饰器性能"""
        print("\n=== 日志装饰器性能测试 ===")

        class TestService(BaseService):
            @operation_logger("装饰器测试", log_args=True, log_result=True)
            def test_method(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return {"processed": True, "data": data}

            @performance_logger("性能装饰器测试")
            def performance_test(self, size: int) -> int:
                return sum(range(size))

        test_service = TestService()

        # 测试操作日志装饰器
        decorator_times = []
        test_data = {"key": "value", "number": 42}

        for i in range(30):
            _, exec_time = self.analyzer.measure_time(
                test_service.test_method, test_data
            )
            decorator_times.append(exec_time)

        avg_decorator_time = sum(decorator_times) / len(decorator_times)
        self.analyzer.record_result("操作日志装饰器", "平均时间", avg_decorator_time)

        print(f"操作日志装饰器平均时间: {avg_decorator_time:.2f}ms")

        if avg_decorator_time > 15:
            print("⚠️ 操作日志装饰器性能较慢")
        else:
            print("✅ 操作日志装饰器性能良好")

        # 测试性能日志装饰器
        perf_times = []
        for i in range(30):
            _, exec_time = self.analyzer.measure_time(
                test_service.performance_test, 100
            )
            perf_times.append(exec_time)

        avg_perf_time = sum(perf_times) / len(perf_times)
        self.analyzer.record_result("性能日志装饰器", "平均时间", avg_perf_time)

        print(f"性能日志装饰器平均时间: {avg_perf_time:.2f}ms")

        if avg_perf_time > 10:
            print("⚠️ 性能日志装饰器较慢")
        else:
            print("✅ 性能日志装饰器良好")

        return {
            "operation_decorator": avg_decorator_time,
            "performance_decorator": avg_perf_time
        }


class TestExceptionHandlingPerformance:
    """异常处理性能测试"""

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.service = BaseService()

    def test_exception_creation(self):
        """测试异常创建性能"""
        print("\n=== 异常创建性能测试 ===")

        # 测试BusinessException创建
        exception_times = []
        for i in range(100):
            _, exec_time = self.analyzer.measure_time(
                BusinessException, "TEST_ERROR", "测试消息", user_message="用户友好消息"
            )
            exception_times.append(exec_time)

        avg_time = sum(exception_times) / len(exception_times)
        self.analyzer.record_result("异常创建", "平均时间", avg_time, "μs")

        print(f"异常创建平均时间: {avg_time*1000:.2f}μs")

        if avg_time > 50:  # 50微秒阈值
            print("⚠️ 异常创建性能较慢")
        else:
            print("✅ 异常创建性能良好")

        return avg_time

    def test_exception_handling_overhead(self):
        """测试异常处理开销"""
        print("\n=== 异常处理开销测试 ===")

        # 测试正常执行
        normal_times = []
        for i in range(50):
            _, exec_time = self.analyzer.measure_time(
                self._validate_data_normal, {"name": "test", "value": i}
            )
            normal_times.append(exec_time)

        avg_normal_time = sum(normal_times) / len(normal_times)

        # 测试异常处理
        exception_times = []
        for i in range(50):
            _, exec_time = self.analyzer.measure_time(
                self._validate_data_with_exception, {"name": "test"}  # 缺少value字段
            )
            exception_times.append(exec_time)

        avg_exception_time = sum(exception_times) / len(exception_times)

        overhead = ((avg_exception_time / avg_normal_time) - 1) * 100

        self.analyzer.record_result("正常执行", "平均时间", avg_normal_time)
        self.analyzer.record_result("异常处理", "平均时间", avg_exception_time)
        self.analyzer.record_result("异常处理", "开销百分比", overhead)

        print(f"正常执行平均时间: {avg_normal_time:.2f}ms")
        print(f"异常处理平均时间: {avg_exception_time:.2f}ms")
        print(f"异常处理开销: {overhead:.1f}%")

        if overhead > 200:  # 200%阈值
            print("⚠️ 异常处理开销过大")
        else:
            print("✅ 异常处理开销在可接受范围内")

        return {
            "normal_time": avg_normal_time,
            "exception_time": avg_exception_time,
            "overhead": overhead
        }

    def _validate_data_normal(self, data: Dict[str, Any]) -> bool:
        """正常的数据验证"""
        return "name" in data and "value" in data

    def _validate_data_with_exception(self, data: Dict[str, Any]) -> bool:
        """会抛出异常的数据验证"""
        try:
            if "name" not in data or "value" not in data:
                raise ValidationException("field", "value", "缺少必填字段")
            return True
        except Exception:
            return False


class TestConcurrencyPerformance:
    """并发性能测试"""

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()

    def test_concurrent_service_creation(self):
        """测试并发服务创建"""
        print("\n=== 并发服务创建性能测试 ===")

        def create_service_thread(results, thread_id):
            """创建服务的线程函数"""
            thread_times = []
            for i in range(10):
                _, exec_time = self.analyzer.measure_time(BaseService)
                thread_times.append(exec_time)

            results.append({
                "thread_id": thread_id,
                "times": thread_times,
                "avg_time": sum(thread_times) / len(thread_times)
            })

        # 创建多个线程
        threads = []
        results = []

        for i in range(5):
            thread = threading.Thread(
                target=create_service_thread,
                args=(results, i)
            )
            threads.append(thread)

        # 启动所有线程
        start_time = time.perf_counter()
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()
        end_time = time.perf_counter()

        total_time = (end_time - start_time) * 1000
        total_operations = sum(len(r["times"]) for r in results)
        avg_thread_time = sum(r["avg_time"] for r in results) / len(results)

        print(f"总执行时间: {total_time:.2f}ms")
        print(f"总操作数: {total_operations}")
        print(f"每线程平均时间: {avg_thread_time:.2f}ms")
        print(f"并发吞吐量: {total_operations / (total_time / 1000):.2f} 操作/秒")

        self.analyzer.record_result("并发服务创建", "总时间", total_time)
        self.analyzer.record_result("并发服务创建", "操作数", total_operations)
        self.analyzer.record_result("并发服务创建", "吞吐量", total_operations / (total_time / 1000), "操作/秒")

        return total_operations / (total_time / 1000)

    def test_concurrent_logging(self):
        """测试并发日志记录"""
        print("\n=== 并发日志记录性能测试 ===")

        def logging_thread(service, results, thread_id):
            """日志记录线程函数"""
            thread_times = []
            for i in range(50):
                _, exec_time = self.analyzer.measure_time(
                    service._log_info, f"线程{thread_id}日志{i}",
                    thread_id=thread_id,
                    iteration=i
                )
                thread_times.append(exec_time)

            results.append({
                "thread_id": thread_id,
                "avg_time": sum(thread_times) / len(thread_times)
            })

        service = BaseService()
        threads = []
        results = []

        # 创建多个日志线程
        for i in range(3):
            thread = threading.Thread(
                target=logging_thread,
                args=(service, results, i)
            )
            threads.append(thread)

        # 启动所有线程
        start_time = time.perf_counter()
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()
        end_time = time.perf_counter()

        total_time = (end_time - start_time) * 1000
        total_logs = sum(len(r.get("times", [])) for r in results)
        avg_thread_time = sum(r["avg_time"] for r in results) / len(results)

        print(f"总执行时间: {total_time:.2f}ms")
        print(f"总日志数: {total_logs}")
        print(f"每线程平均时间: {avg_thread_time:.2f}ms")
        print(f"并发日志吞吐量: {total_logs / (total_time / 1000):.2f} 日志/秒")

        self.analyzer.record_result("并发日志记录", "吞吐量", total_logs / (total_time / 1000), "日志/秒")

        return total_logs / (total_time / 1000)


class TestMemoryUsage:
    """内存使用测试"""

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()

    def test_service_memory_usage(self):
        """测试服务内存使用"""
        print("\n=== 服务内存使用测试 ===")

        # 测试单个服务实例的内存使用
        services = []
        memory_info = []

        for i in range(100):
            service = BaseService()
            services.append(service)

            # 每20个实例检查一次内存
            if (i + 1) % 20 == 0:
                items, lines = self.analyzer.measure_memory()
                memory_info.append({
                    "count": len(services),
                    "items": items,
                    "lines": lines
                })

        print(f"创建100个服务实例的内存使用:")
        for info in memory_info:
            print(f"  {info['count']}个实例: {info['items']}个项目, {info['lines']}行")

        # 清理
        del services
        import gc
        gc.collect()

        # 检查内存是否释放
        final_items, final_lines = self.analyzer.measure_memory()
        print(f"清理后内存使用: {final_items}个项目, {final_lines}行")

        if final_lines > 1000:
            print("⚠️ 可能存在内存泄漏")
        else:
            print("✅ 内存使用正常")

        return memory_info

    def test_logging_memory_impact(self):
        """测试日志对内存的影响"""
        print("\n=== 日志内存影响测试 ===")

        service = BaseService()

        # 测试大量日志记录的内存影响
        print("记录大量日志...")
        for i in range(1000):
            service._log_info(f"内存测试日志 {i}",
                            iteration=i,
                            large_data="x" * 50)  # 包含一些数据

        items, lines = self.analyzer.measure_memory()
        print(f"1000条日志后内存使用: {items}个项目, {lines}行")

        # 测试异常日志的内存影响
        print("记录大量异常日志...")
        test_exception = Exception("内存测试异常")
        for i in range(100):
            service._log_error(f"内存测试错误 {i}",
                            error=test_exception,
                            iteration=i)

        items, lines = self.analyzer.measure_memory()
        print(f"100条异常日志后内存使用: {items}个项目, {lines}行")

        self.analyzer.record_result("日志内存影响", "最大项目数", items)
        self.analyzer.record_result("日志内存影响", "最大行数", lines)

        if lines > 5000:
            print("⚠️ 日志系统内存影响较大")
        else:
            print("✅ 日志系统内存影响可接受")

        return {"items": items, "lines": lines}


class PerformanceTestSuite:
    """完整性能测试套件"""

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.all_results = {}

    def run_all_tests(self):
        """运行所有性能测试"""
        print("🚀 开始服务层性能测试")
        print("="*60)

        # 1. 服务创建性能测试
        print("\n🔧 第一部分: 服务创建性能测试")
        creation_test = TestServiceCreationPerformance()
        self.all_results["service_creation"] = creation_test.test_service_instantiation()
        creation_test.test_multiple_services_creation()

        # 2. 日志系统性能测试
        print("\n📝 第二部分: 日志系统性能测试")
        logging_test = TestLoggingSystemPerformance()
        basic_results = logging_test.test_basic_logging()
        operation_results = logging_test.test_operation_logging()
        decorator_results = logging_test.test_logging_decorators()
        self.all_results["logging_system"] = {
            **basic_results,
            "operation": operation_results,
            **decorator_results
        }

        # 3. 异常处理性能测试
        print("\n⚠️ 第三部分: 异常处理性能测试")
        exception_test = TestExceptionHandlingPerformance()
        exception_creation_time = exception_test.test_exception_creation()
        handling_results = exception_test.test_exception_handling_overhead()
        self.all_results["exception_handling"] = {
            "exception_creation": exception_creation_time,
            "normal_time": handling_results.get("normal_time", 0),
            "exception_time": handling_results.get("exception_time", 0),
            "overhead": handling_results.get("overhead", 0)
        }

        # 4. 并发性能测试
        print("\n🔄 第四部分: 并发性能测试")
        concurrency_test = TestConcurrencyPerformance()
        concurrent_service_throughput = concurrency_test.test_concurrent_service_creation()
        concurrent_logging_throughput = concurrency_test.test_concurrent_logging()
        self.all_results["concurrency"] = {
            "service_throughput": concurrent_service_throughput,
            "logging_throughput": concurrent_logging_throughput
        }

        # 5. 内存使用测试
        print("\n💾 第五部分: 内存使用测试")
        memory_test = TestMemoryUsage()
        memory_results = memory_test.test_service_memory_usage()
        logging_memory_results = memory_test.test_logging_memory_impact()
        self.all_results["memory"] = {
            "service": memory_results,
            "logging": logging_memory_results
        }

        # 6. 生成综合报告
        # 将所有结果转换为适合打印的格式
        formatted_results = {}
        for key, value in self.all_results.items():
            if isinstance(value, dict):
                formatted_results[key] = value
            else:
                formatted_results[key] = {"result": f"{value:.2f}"}

        self.analyzer.results.update(formatted_results)
        self.analyzer.print_summary()
        self._generate_performance_recommendations()

        print("\n✅ 所有性能测试完成！")
        return self.all_results

    def _generate_performance_recommendations(self):
        """生成性能优化建议"""
        print("\n" + "="*60)
        print("性能优化建议")
        print("="*60)

        recommendations = []

        # 基于测试结果生成建议
        if "service_creation" in self.all_results:
            creation_time = self.all_results["service_creation"]
            if creation_time > 10:
                recommendations.append("🔧 考虑使用对象池来重用服务实例")
                recommendations.append("🔧 延迟加载非关键服务")

        if "logging_system" in self.all_results:
            logging_results = self.all_results["logging_system"]
            if logging_results.get("operation", 0) > 20:
                recommendations.append("📝 优化操作日志装饰器，减少日志开销")
            if logging_results.get("performance_decorator", 0) > 15:
                recommendations.append("📝 在生产环境中谨慎使用性能日志装饰器")

        if "exception_handling" in self.all_results:
            handling_results = self.all_results["exception_handling"]
            if handling_results.get("overhead", 0) > 200:
                recommendations.append("⚠️ 减少异常创建频率，优化异常处理逻辑")
                recommendations.append("⚠️ 使用快速失败模式，避免不必要的异常处理")

        if "concurrency" in self.all_results:
            concurrency_results = self.all_results["concurrency"]
            if concurrency_results.get("service_throughput", 0) < 100:
                recommendations.append("🔄 优化服务创建逻辑，提高并发性能")
            if concurrency_results.get("logging_throughput", 0) < 1000:
                recommendations.append("📝 优化日志系统，提高并发日志性能")

        if "memory" in self.all_results:
            memory_results = self.all_results["memory"]
            if memory_results.get("logging", {}).get("lines", 0) > 5000:
                recommendations.append("💾 优化日志系统，减少内存占用")

        if recommendations:
            print("\n优化建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("\n🎉 当前性能表现良好，无需特别优化")

        print("\n📊 长期监控建议:")
        print("1. 定期运行性能测试，监控性能变化")
        print("2. 在生产环境中监控关键指标")
        print("3. 根据业务增长调整性能优化策略")
        print("4. 建立性能基线和告警机制")


def main():
    """主函数"""
    suite = PerformanceTestSuite()
    results = suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()