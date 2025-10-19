"""
服务层性能测试

该测试文件包含对整个服务层的性能测试，用于识别性能瓶颈和优化机会。
测试包括：
1. 服务初始化性能测试
2. 内存使用分析
3. 日志系统性能测试
4. 异常处理性能测试
5. 并发访问性能测试
6. 长时间运行稳定性测试
"""

import pytest
import asyncio
import time
import tracemalloc
import psutil
import os
import threading
from typing import List, Dict, Any
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.services.task_service import TaskService
from src.services.focus_service import FocusService
from src.services.reward_service import RewardService
from src.services.statistics_service import StatisticsService
from src.services.chat_service import ChatService
from src.services.base import BaseService, ServiceFactory

pytestmark = pytest.mark.asyncio


class PerformanceTestBase:
    """性能测试基类"""

    @staticmethod
    def measure_memory_usage():
        """测量当前内存使用情况"""
        process = psutil.Process()
        return {
            "rss": process.memory_info().rss / 1024 / 1024,  # MB
            "vms": process.memory_info().vms / 1024 / 1024,  # MB
            "percent": process.memory_percent()
        }

    @staticmethod
    def measure_cpu_usage():
        """测量CPU使用情况"""
        process = psutil.Process()
        return process.cpu_percent()

    @staticmethod
    def start_memory_tracing():
        """开始内存跟踪"""
        tracemalloc.start()

    @staticmethod
    def stop_memory_tracing():
        """停止内存跟踪并返回结果"""
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        return snapshot


class TestServiceInitializationPerformance(PerformanceTestBase):
    """服务初始化性能测试"""

    def test_service_initialization_performance(self):
        """测试服务初始化性能"""
        print("\n=== 服务初始化性能测试 ===")

        services_to_test = [
            (AuthService, "AuthService"),
            (UserService, "UserService"),
            (TaskService, "TaskService"),
            (FocusService, "FocusService"),
            (RewardService, "RewardService"),
            (StatisticsService, "StatisticsService"),
            (ChatService, "ChatService")
        ]

        results = []

        for service_class, service_name in services_to_test:
            print(f"\n测试 {service_name} 初始化性能...")

            # 预热
            for _ in range(3):
                service = service_class()
                del service

            # 正式测试
            initialization_times = []
            memory_usage_before = []

            for i in range(10):
                # 记录初始化前内存
                memory_before = self.measure_memory_usage()
                memory_usage_before.append(memory_before)

                # 测量初始化时间
                start_time = time.perf_counter()
                service = service_class()
                end_time = time.perf_counter()

                init_time = (end_time - start_time) * 1000  # ms
                initialization_times.append(init_time)

                # 清理
                del service

            # 计算统计信息
            avg_time = sum(initialization_times) / len(initialization_times)
            min_time = min(initialization_times)
            max_time = max(initialization_times)

            avg_memory_before = sum(m["rss"] for m in memory_usage_before) / len(memory_usage_before)

            results.append({
                "service": service_name,
                "avg_time_ms": avg_time,
                "min_time_ms": min_time,
                "max_time_ms": max_time,
                "avg_memory_mb": avg_memory_before,
                "iterations": len(initialization_times)
            })

            print(f"  {service_name}:")
            print(f"    平均初始化时间: {avg_time:.2f}ms")
            print(f"    最快初始化时间: {min_time:.2f}ms")
            print(f"    最慢初始化时间: {max_time:.2f}ms")
            print(f"    平均内存使用: {avg_memory_before:.2f}MB")

        # 性能评估
        print(f"\n=== 初始化性能评估 ===")
        for result in results:
            if result["avg_time_ms"] > 100:  # 100ms阈值
                print(f"⚠️  {result['service']} 初始化较慢: {result['avg_time_ms']:.2f}ms")
            else:
                print(f"✅ {result['service']} 初始化性能良好: {result['avg_time_ms']:.2f}ms")

        return results

    def test_service_factory_performance(self):
        """测试ServiceFactory性能"""
        print("\n=== ServiceFactory性能测试 ===")

        factory_times = []
        memory_usage = []

        for i in range(20):
            memory_before = self.measure_memory_usage()
            memory_usage.append(memory_before)

            start_time = time.perf_counter()
            service = ServiceFactory.create_service(UserService)
            end_time = time.perf_counter()

            factory_time = (end_time - start_time) * 1000
            factory_times.append(factory_time)

            del service

        avg_time = sum(factory_times) / len(factory_times)
        avg_memory = sum(m["rss"] for m in memory_usage) / len(memory_usage)

        print(f"ServiceFactory平均创建时间: {avg_time:.2f}ms")
        print(f"平均内存使用: {avg_memory:.2f}MB")

        if avg_time > 50:
            print("⚠️ ServiceFactory创建性能需要优化")
        else:
            print("✅ ServiceFactory性能良好")


class TestLoggingSystemPerformance(PerformanceTestBase):
    """日志系统性能测试"""

    def test_logging_performance(self):
        """测试日志系统性能"""
        print("\n=== 日志系统性能测试 ===")

        # 设置日志级别为DEBUG以测试所有日志
        os.environ['SERVICE_LOG_LEVEL'] = 'DEBUG'
        os.environ['SERVICE_LOG_CONSOLE'] = 'false'  # 关闭控制台输出避免干扰
        os.environ['SERVICE_LOG_FILE'] = 'false'      # 关闭文件输出

        service = UserService()

        # 测试基本日志性能
        print("\n1. 基本日志性能测试...")
        basic_log_times = []

        for i in range(100):
            start_time = time.perf_counter()
            service._log_info(f"测试日志消息 {i}", test_data=f"test_value_{i}")
            end_time = time.perf_counter()

            log_time = (end_time - start_time) * 1000 * 1000  # 转换为微秒
            basic_log_times.append(log_time)

        avg_basic_time = sum(basic_log_times) / len(basic_log_times)
        print(f"   平均基本日志时间: {avg_basic_time:.2f}μs")

        # 测试操作日志性能
        print("\n2. 操作日志性能测试...")
        operation_log_times = []

        for i in range(50):
            start_time = time.perf_counter()
            service._log_operation_start(f"测试操作 {i}", user_id=f"user_{i}")
            service._log_operation_success(f"测试操作 {i}", duration_ms=100 + i)
            end_time = time.perf_counter()

            log_time = (end_time - start_time) * 1000
            operation_log_times.append(log_time)

        avg_operation_time = sum(operation_log_times) / len(operation_log_times)
        print(f"   平均操作日志时间: {avg_operation_time:.2f}ms")

        # 测试错误日志性能
        print("\n3. 错误日志性能测试...")
        error_log_times = []

        test_exception = Exception("测试异常")

        for i in range(30):
            start_time = time.perf_counter()
            service._log_error(f"测试错误日志 {i}", error=test_exception)
            end_time = time.perf_counter()

            log_time = (end_time - start_time) * 1000
            error_log_times.append(log_time)

        avg_error_time = sum(error_log_times) / len(error_log_times)
        print(f"   平均错误日志时间: {avg_error_time:.2f}ms")

        # 性能评估
        print(f"\n=== 日志性能评估 ===")
        if avg_basic_time > 1000:  # 1ms阈值
            print(f"⚠️ 基本日志性能较慢: {avg_basic_time:.2f}μs")
        else:
            print(f"✅ 基本日志性能良好: {avg_basic_time:.2f}μs")

        if avg_operation_time > 5:  # 5ms阈值
            print(f"⚠️ 操作日志性能较慢: {avg_operation_time:.2f}ms")
        else:
            print(f"✅ 操作日志性能良好: {avg_operation_time:.2f}ms")

        return {
            "basic_log_avg_us": avg_basic_time,
            "operation_log_avg_ms": avg_operation_time,
            "error_log_avg_ms": avg_error_time
        }

    def test_logging_decorator_performance(self):
        """测试日志装饰器性能"""
        print("\n=== 日志装饰器性能测试 ===")

        from src.services.logging_config import operation_logger, performance_logger

        class TestService(BaseService):
            @operation_logger("测试方法", log_args=True, log_result=True)
            def test_method(self, data: Dict[str, Any]) -> Dict[str, Any]:
                # 模拟一些处理
                result = {"processed": True, "data": data}
                return result

            @performance_logger("性能测试方法")
            def performance_method(self, size: int) -> int:
                # 模拟一些计算
                return sum(range(size))

        service = TestService()

        # 测试操作日志装饰器
        print("\n1. 操作日志装饰器性能测试...")
        decorator_times = []

        test_data = {"key": "value", "number": 42}

        for i in range(50):
            start_time = time.perf_counter()
            result = service.test_method(test_data)
            end_time = time.perf_counter()

            decorator_time = (end_time - start_time) * 1000
            decorator_times.append(decorator_time)

        avg_decorator_time = sum(decorator_times) / len(decorator_times)
        print(f"   平均装饰器执行时间: {avg_decorator_time:.2f}ms")

        # 测试性能日志装饰器
        print("\n2. 性能日志装饰器测试...")
        perf_decorator_times = []

        for i in range(50):
            start_time = time.perf_counter()
            result = service.performance_method(1000)
            end_time = time.perf_counter()

            decorator_time = (end_time - start_time) * 1000
            perf_decorator_times.append(decorator_time)

        avg_perf_time = sum(perf_decorator_times) / len(perf_decorator_times)
        print(f"   平均性能装饰器时间: {avg_perf_time:.2f}ms")

        # 性能评估
        print(f"\n=== 装饰器性能评估 ===")
        if avg_decorator_time > 10:  # 10ms阈值
            print(f"⚠️ 操作日志装饰器性能较慢: {avg_decorator_time:.2f}ms")
        else:
            print(f"✅ 操作日志装饰器性能良好: {avg_decorator_time:.2f}ms")

        if avg_perf_time > 5:  # 5ms阈值
            print(f"⚠️ 性能日志装饰器较慢: {avg_perf_time:.2f}ms")
        else:
            print(f"✅ 性能日志装饰器良好: {avg_perf_time:.2f}ms")

        return {
            "operation_decorator_ms": avg_decorator_time,
            "performance_decorator_ms": avg_perf_time
        }


class TestExceptionHandlingPerformance(PerformanceTestBase):
    """异常处理性能测试"""

    def test_exception_creation_performance(self):
        """测试异常创建性能"""
        print("\n=== 异常创建性能测试 ===")

        from src.services.exceptions import (
            BusinessException,
            ValidationException,
            ResourceNotFoundException
        )

        # 测试不同异常类型的创建性能
        exception_types = [
            (BusinessException, "error_code", "message"),
            (ValidationException, "field", "value", "message"),
            (ResourceNotFoundException, "resource", "id")
        ]

        results = {}

        for exception_type in exception_types:
            print(f"\n测试 {exception_type.__name__} 创建性能...")

            creation_times = []
            args = exception_type[1:]  # 获取构造函数参数

            for i in range(1000):
                start_time = time.perf_counter()
                exception = exception_type(*args)
                end_time = time.perf_counter()

                creation_time = (end_time - start_time) * 1000 * 1000  # 微秒
                creation_times.append(creation_time)

                del exception

            avg_time = sum(creation_times) / len(creation_times)
            results[exception_type.__name__] = avg_time
            print(f"   平均创建时间: {avg_time:.2f}μs")

        # 性能评估
        print(f"\n=== 异常创建性能评估 ===")
        for exc_name, avg_time in results.items():
            if avg_time > 100:  # 100微秒阈值
                print(f"⚠️ {exc_name} 创建较慢: {avg_time:.2f}μs")
            else:
                print(f"✅ {exc_name} 创建性能良好: {avg_time:.2f}μs")

        return results

    def test_exception_handling_overhead(self):
        """测试异常处理开销"""
        print("\n=== 异常处理开销测试 ===")

        service = UserService()

        # 测试正常执行性能
        normal_times = []

        for i in range(100):
            start_time = time.perf_counter()
            # 正常的验证调用
            service.validate_required_fields(
                {"name": "test", "email": "test@example.com"},
                ["name", "email"]
            )
            end_time = time.perf_counter()

            normal_time = (end_time - start_time) * 1000
            normal_times.append(normal_time)

        avg_normal_time = sum(normal_times) / len(normal_times)

        # 测试异常处理性能
        exception_times = []

        for i in range(100):
            start_time = time.perf_counter()
            try:
                # 会抛出异常的调用
                service.validate_required_fields(
                    {"name": "test"},  # 缺少email字段
                    ["name", "email"]
                )
            except Exception:
                pass
            end_time = time.perf_counter()

            exception_time = (end_time - start_time) * 1000
            exception_times.append(exception_time)

        avg_exception_time = sum(exception_times) / len(exception_times)

        print(f"正常执行平均时间: {avg_normal_time:.2f}ms")
        print(f"异常处理平均时间: {avg_exception_time:.2f}ms")
        print(f"异常处理开销: {(avg_exception_time / avg_normal_time - 1) * 100:.1f}%")

        if avg_exception_time > avg_normal_time * 5:
            print("⚠️ 异常处理开销较大，需要优化")
        else:
            print("✅ 异常处理开销在可接受范围内")

        return {
            "normal_time_ms": avg_normal_time,
            "exception_time_ms": avg_exception_time,
            "overhead_percent": (avg_exception_time / avg_normal_time - 1) * 100
        }


class TestConcurrentAccessPerformance(PerformanceTestBase):
    """并发访问性能测试"""

    def test_concurrent_service_creation(self):
        """测试并发服务创建性能"""
        print("\n=== 并发服务创建性能测试 ===")

        def create_service_thread(service_class, results_list, thread_id):
            """创建服务的线程函数"""
            thread_times = []

            for i in range(10):
                start_time = time.perf_counter()
                service = service_class()
                end_time = time.perf_counter()

                creation_time = (end_time - start_time) * 1000
                thread_times.append(creation_time)

                del service

            results_list.append({
                "thread_id": thread_id,
                "times": thread_times,
                "avg_time": sum(thread_times) / len(thread_times)
            })

        # 测试不同服务的并发创建
        services_to_test = [
            (UserService, "UserService"),
            (TaskService, "TaskService"),
            (FocusService, "FocusService")
        ]

        for service_class, service_name in services_to_test:
            print(f"\n测试 {service_name} 并发创建性能...")

            threads = []
            results = []

            # 创建10个并发线程
            for i in range(10):
                thread = threading.Thread(
                    target=create_service_thread,
                    args=(service_class, results, i)
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

            print(f"   总执行时间: {total_time:.2f}ms")
            print(f"   总操作数: {total_operations}")
            print(f"   每线程平均时间: {avg_thread_time:.2f}ms")
            print(f"   吞吐量: {total_operations / (total_time / 1000):.2f} 操作/秒")

    def test_concurrent_logging(self):
        """测试并发日志记录性能"""
        print("\n=== 并发日志记录性能测试 ===")

        os.environ['SERVICE_LOG_LEVEL'] = 'INFO'
        os.environ['SERVICE_LOG_CONSOLE'] = 'false'
        os.environ['SERVICE_LOG_FILE'] = 'false'

        def logging_thread(service, thread_id, results):
            """日志记录线程函数"""
            thread_times = []

            for i in range(50):
                start_time = time.perf_counter()
                service._log_info(f"线程{thread_id}日志{i}", thread_id=thread_id, iteration=i)
                end_time = time.perf_counter()

                log_time = (end_time - start_time) * 1000 * 1000  # 微秒
                thread_times.append(log_time)

            results.append({
                "thread_id": thread_id,
                "avg_time_us": sum(thread_times) / len(thread_times),
                "times": thread_times
            })

        service = UserService()
        threads = []
        results = []

        # 创建20个并发日志线程
        for i in range(20):
            thread = threading.Thread(
                target=logging_thread,
                args=(service, i, results)
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
        total_logs = sum(len(r["times"]) for r in results)
        avg_thread_time = sum(r["avg_time_us"] for r in results) / len(results)

        print(f"   总执行时间: {total_time:.2f}ms")
        print(f"   总日志数: {total_logs}")
        print(f"   每线程平均时间: {avg_thread_time:.2f}μs")
        print(f"   日志吞吐量: {total_logs / (total_time / 1000):.2f} 日志/秒")

        # 性能评估
        if total_logs / (total_time / 1000) < 1000:  # 1000日志/秒阈值
            print("⚠️ 并发日志性能较低")
        else:
            print("✅ 并发日志性能良好")


class TestMemoryUsageOptimization(PerformanceTestBase):
    """内存使用优化测试"""

    def test_service_memory_leaks(self):
        """测试服务内存泄漏"""
        print("\n=== 服务内存泄漏测试 ===")

        services_to_test = [UserService, TaskService, FocusService]

        for service_class in services_to_test:
            print(f"\n测试 {service_class.__name__} 内存使用...")

            initial_memory = self.measure_memory_usage()

            # 创建大量服务实例
            services = []
            for i in range(100):
                service = service_class()
                services.append(service)

            peak_memory = self.measure_memory_usage()

            # 删除服务实例
            del services

            # 强制垃圾回收
            import gc
            gc.collect()

            final_memory = self.measure_memory_usage()

            memory_increase = peak_memory["rss"] - initial_memory["rss"]
            memory_leak = final_memory["rss"] - initial_memory["rss"]

            print(f"   初始内存: {initial_memory['rss']:.2f}MB")
            print(f"   峰值内存: {peak_memory['rss']:.2f}MB")
            print(f"   最终内存: {final_memory['rss']:.2f}MB")
            print(f"   内存增长: {memory_increase:.2f}MB")
            print(f"   内存泄漏: {memory_leak:.2f}MB")

            if memory_leak > 10:  # 10MB阈值
                print(f"⚠️ {service_class.__name__} 可能存在内存泄漏")
            else:
                print(f"✅ {service_class.__name__} 内存使用正常")

    def test_logging_memory_impact(self):
        """测试日志系统对内存的影响"""
        print("\n=== 日志系统内存影响测试 ===")

        os.environ['SERVICE_LOG_LEVEL'] = 'DEBUG'
        os.environ['SERVICE_LOG_CONSOLE'] = 'false'
        os.environ['SERVICE_LOG_FILE'] = 'false'

        service = UserService()

        # 测试大量日志记录的内存影响
        initial_memory = self.measure_memory_usage()

        # 记录大量日志
        for i in range(1000):
            service._log_info(f"内存测试日志 {i}",
                            iteration=i,
                            large_data="x" * 100)  # 包含一些数据

        after_logging_memory = self.measure_memory_usage()

        # 测试异常日志的内存影响
        test_exception = Exception("内存测试异常")
        for i in range(100):
            service._log_error(f"内存测试错误 {i}",
                            error=test_exception,
                            iteration=i)

        after_error_memory = self.measure_memory_usage()

        # 计算内存增长
        logging_growth = after_logging_memory["rss"] - initial_memory["rss"]
        error_growth = after_error_memory["rss"] - after_logging_memory["rss"]

        print(f"   初始内存: {initial_memory['rss']:.2f}MB")
        print(f"   大量日志后: {after_logging_memory['rss']:.2f}MB")
        print(f"   大量错误后: {after_error_memory['rss']:.2f}MB")
        print(f"   日志内存增长: {logging_growth:.2f}MB")
        print(f"   错误内存增长: {error_growth:.2f}MB")

        if logging_growth > 20:  # 20MB阈值
            print("⚠️ 日志系统内存使用较高")
        else:
            print("✅ 日志系统内存使用正常")


class TestOverallSystemPerformance(PerformanceTestBase):
    """整体系统性能测试"""

    def test_end_to_end_performance(self):
        """端到端性能测试"""
        print("\n=== 端到端性能测试 ===")

        # 模拟完整的业务流程
        service = UserService()

        # 测试完整的用户管理流程
        workflows = [
            "用户注册流程",
            "用户资料更新流程",
            "用户设置管理流程",
            "积分操作流程"
        ]

        workflow_times = {}

        for workflow in workflows:
            print(f"\n测试 {workflow}...")

            workflow_times_list = []

            for i in range(20):
                start_time = time.perf_counter()

                # 模拟业务流程
                if workflow == "用户注册流程":
                    # 模拟用户注册
                    service._log_operation_start("用户注册", user_id=f"user_{i}")
                    # 模拟一些处理
                    result = {"user_id": f"user_{i}", "status": "created"}
                    service._log_operation_success("用户注册", user_id=f"user_{i}")

                elif workflow == "用户资料更新流程":
                    # 模拟资料更新
                    profile_data = {
                        "display_name": f"用户{i}",
                        "avatar_url": f"https://avatar{i}.jpg"
                    }
                    service._log_operation_start("更新资料", user_id=f"user_{i}")
                    result = {"updated": True, "data": profile_data}
                    service._log_operation_success("更新资料", user_id=f"user_{i}")

                elif workflow == "用户设置管理流程":
                    # 模拟设置管理
                    settings_data = {
                        "notification_enabled": True,
                        "theme": "dark",
                        "language": "zh-CN"
                    }
                    service._log_operation_start("更新设置", user_id=f"user_{i}")
                    result = {"updated": True, "settings": settings_data}
                    service._log_operation_success("更新设置", user_id=f"user_{i}")

                elif workflow == "积分操作流程":
                    # 模拟积分操作
                    service._log_operation_start("添加积分", user_id=f"user_{i}")
                    result = {"points_added": 50, "new_balance": 150}
                    service._log_operation_success("添加积分", user_id=f"user_{i}")

                end_time = time.perf_counter()
                workflow_time = (end_time - start_time) * 1000
                workflow_times_list.append(workflow_time)

            avg_time = sum(workflow_times_list) / len(workflow_times_list)
            workflow_times[workflow] = avg_time

            print(f"   平均执行时间: {avg_time:.2f}ms")

        # 性能评估
        print(f"\n=== 端到端性能评估 ===")
        total_avg_time = sum(workflow_times.values()) / len(workflow_times)
        print(f"整体平均执行时间: {total_avg_time:.2f}ms")

        for workflow, avg_time in workflow_times.items():
            if avg_time > 50:  # 50ms阈值
                print(f"⚠️ {workflow} 性能较慢: {avg_time:.2f}ms")
            else:
                print(f"✅ {workflow} 性能良好: {avg_time:.2f}ms")

        return workflow_times

    def generate_performance_report(self, all_test_results: Dict[str, Any]):
        """生成性能测试报告"""
        print("\n" + "="*50)
        print("性能测试综合报告")
        print("="*50)

        # 这里可以生成详细的性能报告
        # 包括各个测试的结果汇总、性能瓶颈分析、优化建议等

        print("\n📊 测试结果汇总:")
        for test_name, results in all_test_results.items():
            print(f"\n🔍 {test_name}:")
            if isinstance(results, dict):
                for key, value in results.items():
                    if isinstance(value, (int, float)):
                        print(f"   {key}: {value:.2f}")
                    else:
                        print(f"   {key}: {value}")

        print(f"\n🎯 性能优化建议:")
        print("1. 监控日志系统性能，避免在生产环境使用DEBUG级别")
        print("2. 优化异常处理，减少不必要的异常创建")
        print("3. 考虑使用对象池来重用服务实例")
        print("4. 定期进行内存泄漏检测")
        print("5. 监控并发访问性能，确保线程安全")


@pytest.fixture
def performance_test_results():
    """存储所有测试结果的fixture"""
    return {}


class TestServicePerformanceComplete:
    """完整的服务层性能测试套件"""

    def test_all_performance_tests(self, performance_test_results):
        """运行所有性能测试"""
        print("🚀 开始服务层完整性能测试")
        print("="*60)

        # 1. 服务初始化性能测试
        init_test = TestServiceInitializationPerformance()
        init_results = init_test.test_service_initialization_performance()
        init_test.test_service_factory_performance()
        performance_test_results["initialization"] = init_results

        # 2. 日志系统性能测试
        logging_test = TestLoggingSystemPerformance()
        logging_results = logging_test.test_logging_performance()
        decorator_results = logging_test.test_logging_decorator_performance()
        performance_test_results["logging"] = {**logging_results, **decorator_results}

        # 3. 异常处理性能测试
        exception_test = TestExceptionHandlingPerformance()
        exception_results = exception_test.test_exception_creation_performance()
        handling_results = exception_test.test_exception_handling_overhead()
        performance_test_results["exceptions"] = {**exception_results, **handling_results}

        # 4. 并发访问性能测试
        concurrent_test = TestConcurrentAccessPerformance()
        concurrent_test.test_concurrent_service_creation()
        concurrent_test.test_concurrent_logging()

        # 5. 内存使用测试
        memory_test = TestMemoryUsageOptimization()
        memory_test.test_service_memory_leaks()
        memory_test.test_logging_memory_impact()

        # 6. 端到端性能测试
        e2e_test = TestOverallSystemPerformance()
        e2e_results = e2e_test.test_end_to_end_performance()
        performance_test_results["end_to_end"] = e2e_results

        # 7. 生成综合报告
        e2e_test.generate_performance_report(performance_test_results)

        print("\n✅ 所有性能测试完成！")


if __name__ == "__main__":
    # 直接运行性能测试
    suite = TestServicePerformanceComplete()
    results = {}
    suite.test_all_performance_tests(results)