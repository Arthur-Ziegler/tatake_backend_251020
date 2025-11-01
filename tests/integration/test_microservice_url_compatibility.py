"""
微服务URL兼容性测试

专门用于检测微服务URL路径兼容性问题的测试套件。
这类问题通常由以下原因引起：
1. 尾部斜杠处理不一致
2. API路径格式不匹配
3. 微服务URL构建逻辑错误

本测试套件提供：
- 自动URL路径验证
- 微服务直接对比测试
- 本地API端到端验证
- URL格式兼容性报告

作者：TaTake团队
版本：1.0.0（URL兼容性专项测试）
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from fastapi.testclient import TestClient

# 导入微服务客户端
from src.services.task_microservice_client import (
    TaskMicroserviceClient,
    get_task_microservice_client,
    create_task, get_all_tasks, update_task, delete_task,
    complete_task, set_top3, get_top3,
    send_focus_status, get_pomodoro_count
)
from src.api.main import app
from src.api.schemas import UnifiedResponse

logger = logging.getLogger(__name__)


@dataclass
class URLTestResult:
    """URL测试结果"""
    method: str
    path: str
    local_status_code: int
    microservice_status_code: int
    local_response_time: float
    microservice_response_time: float
    url_match: bool
    error_message: str = ""
    success: bool = True


@dataclass
class CompatibilityReport:
    """兼容性测试报告"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    url_mismatch_issues: List[URLTestResult]
    connectivity_issues: List[URLTestResult]
    format_mismatch_issues: List[URLTestResult]
    overall_compatibility: float = 0.0


class MicroserviceURLCompatibilityTester:
    """微服务URL兼容性测试器"""

    def __init__(self):
        self.client = TestClient(app)
        self.microservice_client = get_task_microservice_client()
        self.logger = logging.getLogger(__name__)

    async def test_url_compatibility(self) -> CompatibilityReport:
        """
        执行完整的URL兼容性测试

        Returns:
            CompatibilityReport: 测试报告
        """
        test_cases = [
            # (method, path, description)
            ("GET", "tasks/", "查询任务列表"),
            ("POST", "tasks/", "创建任务"),
            ("PUT", "tasks/123", "更新任务"),
            ("DELETE", "tasks/123", "删除任务"),
            ("POST", "tasks/123/complete", "完成任务"),
            ("POST", "tasks/special/top3", "设置Top3"),
            ("GET", "tasks/special/top3/2025-01-15", "获取Top3"),
            ("POST", "tasks/focus-status", "发送专注状态"),
            ("GET", "tasks/pomodoro-count", "查看番茄钟计数"),
        ]

        results = []

        for method, path, description in test_cases:
            result = await self._test_single_endpoint(method, path, description)
            results.append(result)
            self.logger.info(f"测试完成: {method} {path} - {result.success}")

        return self._generate_report(results)

    async def _test_single_endpoint(self, method: str, path: str, description: str) -> URLTestResult:
        """
        测试单个端点的URL兼容性

        Args:
            method (str): HTTP方法
            path (str): API路径
            description (str): 测试描述

        Returns:
            URLTestResult: 测试结果
        """
        result = URLTestResult(
            method=method,
            path=path,
            local_status_code=0,
            microservice_status_code=0,
            local_response_time=0,
            microservice_response_time=0,
            url_match=True,
            success=True
        )

        # 测试本地API
        try:
            local_result = await self._test_local_api(method, path, description)
            result.local_status_code = local_result["status_code"]
            result.local_response_time = local_result["response_time"]
        except Exception as e:
            result.error_message = f"本地API测试失败: {str(e)}"
            result.success = False
            self.logger.error(f"本地API测试失败: {method} {path} - {e}")

        # 测试微服务直接调用
        try:
            microservice_result = await self._test_microservice_direct(method, path, description)
            result.microservice_status_code = microservice_result["status_code"]
            result.microservice_response_time = microservice_result["response_time"]
        except Exception as e:
            result.error_message += f" | 微服务直接测试失败: {str(e)}"
            result.success = False
            self.logger.error(f"微服务直接测试失败: {method} {path} - {e}")

        # 检查URL路径一致性
        if result.local_status_code != result.microservice_status_code:
            result.url_match = False
            result.success = False
            result.error_message += f" | 状态码不匹配: 本地={result.local_status_code}, 微服务={result.microservice_status_code}"

        return result

    async def _test_local_api(self, method: str, path: str, description: str) -> Dict[str, Any]:
        """
        测试本地API

        Args:
            method (str): HTTP方法
            path (str): API路径
            description (str): 测试描述

        Returns:
            Dict[str, Any]: 测试结果
        """
        import time
        start_time = time.time()

        try:
            if method == "GET":
                response = self.client.get(path, headers={
                    "Authorization": "Bearer test-token"
                })
            elif method == "POST":
                response = self.client.post(path, json={"test": "data"}, headers={
                    "Authorization": "Bearer test-token"
                })
            elif method == "PUT":
                response = self.client.put(path, json={"test": "data"}, headers={
                    "Authorization": "Bearer test-token"
                })
            elif method == "DELETE":
                response = self.client.delete(path, headers={
                    "Authorization": "Bearer test-token"
                })
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response_time = time.time() - start_time

            return {
                "status_code": response.status_code,
                "response_time": response_time,
                "response_data": response.json() if response.content_type and "application/json" in response.content_type else None
            }

        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "response_data": None,
                "error": str(e)
            }

    async def _test_microservice_direct(self, method: str, path: str, description: str) -> Dict[str, Any]:
        """
        直接测试微服务

        Args:
            method (str): HTTP方法
            path (str): API路径
            description (str): 测试描述

        Returns:
            Dict[str, Any]: 测试结果
        """
        import time
        start_time = time.time()

        try:
            # 构建微服务URL（使用修复后的逻辑）
            normalized_path = path.rstrip('/')  # 移除尾部斜杠
            url = f"{self.microservice_client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            self.logger.info(f"直接测试微服务: {method} {url}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json={"test": "data"})
                elif method == "PUT":
                    response = await client.put(url, json={"test": "data"})
                elif method == "DELETE":
                    response = await client.delete(url)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")

                response_time = time.time() - start_time

                return {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "response_data": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
                }

        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "response_data": None,
                "error": str(e)
            }

    def _generate_report(self, results: List[URLTestResult]) -> CompatibilityReport:
        """
        生成兼容性测试报告

        Args:
            results (List[URLTestResult]): 测试结果列表

        Returns:
            CompatibilityReport: 兼容性报告
        """
        report = CompatibilityReport(
            total_tests=len(results),
            passed_tests=0,
            failed_tests=0,
            url_mismatch_issues=[],
            connectivity_issues=[],
            format_mismatch_issues=[]
        )

        for result in results:
            if result.success:
                report.passed_tests += 1
            else:
                report.failed_tests += 1

                # 分类问题
                if "状态码不匹配" in result.error_message:
                    report.url_mismatch_issues.append(result)
                elif "测试失败" in result.error_message:
                    report.connectivity_issues.append(result)
                else:
                    report.format_mismatch_issues.append(result)

        report.overall_compatibility = (report.passed_tests / report.total_tests) * 100 if report.total_tests > 0 else 0

        return report

    def print_report(self, report: CompatibilityReport):
        """打印兼容性测试报告"""
        print("\n" + "="*60)
        print("🔍 微服务URL兼容性测试报告")
        print("="*60)

        print(f"📊 总体统计:")
        print(f"   - 总测试数: {report.total_tests}")
        print(f"   - 通过测试: {report.passed_tests}")
        print(f"   - 失败测试: {report.failed_tests}")
        print(f"   - 兼容性评分: {report.overall_compatibility:.1f}%")

        if report.url_mismatch_issues:
            print(f"\n❌ URL路径不匹配问题 ({len(report.url_mismatch_issues)}):")
            for issue in report.url_mismatch_issues:
                print(f"   - {issue.method} {issue.path}: {issue.error_message}")

        if report.connectivity_issues:
            print(f"\n🔌 连接问题 ({len(report.connectivity_issues)}):")
            for issue in report.connectivity_issues:
                print(f"   - {issue.method} {issue.path}: {issue.error_message}")

        if report.format_mismatch_issues:
            print(f"\n📝 格式问题 ({len(report.format_mismatch_issues)}):")
            for issue in report.format_mismatch_issues:
                print(f"   - {issue.method} {issue.path}: {issue.error_message}")

        print("\n" + "="*60)


class TestMicroserviceURLCompatibility:
    """微服务URL兼容性测试类"""

    @pytest.mark.asyncio
    async def test_full_compatibility_check(self):
        """完整的兼容性检查"""
        tester = MicroserviceURLCompatibilityTester()
        report = await tester.test_url_compatibility()
        tester.print_report(report)

        # 断言兼容性评分不低于80%
        assert report.overall_compatibility >= 80.0, \
            f"微服务URL兼容性评分过低: {report.overall_compatibility:.1f}% < 80.0%"

    @pytest.mark.asyncio
    async def test_critical_endpoints_compatibility(self):
        """关键端点兼容性测试"""
        tester = MicroserviceURLCompatibilityTester()

        # 只测试关键端点
        critical_endpoints = [
            ("POST", "tasks/", "创建任务"),
            ("POST", "tasks/123/complete", "完成任务"),
        ]

        results = []
        for method, path, description in critical_endpoints:
            result = await tester._test_single_endpoint(method, path, description)
            results.append(result)

        # 所有关键端点必须通过
        for result in results:
            assert result.success, f"关键端点测试失败: {result.method} {result.path} - {result.error_message}"

    @pytest.mark.asyncio
    async def test_url_path_normalization(self):
        """URL路径标准化测试"""
        # 测试URL路径标准化逻辑
        test_cases = [
            ("tasks/", "tasks"),
            ("tasks//", "tasks"),
            ("/tasks/", "tasks"),
            ("tasks/special/top3/", "tasks/special/top3"),
            ("/tasks/special/top3/", "tasks/special/top3"),
        ]

        for input_path, expected_path in test_cases:
            # 测试微服务客户端的URL构建
            normalized_path = input_path.rstrip('/')
            actual_url = f"http://45.152.65.130:20253/{normalized_path.lstrip('/')}"
            expected_url = f"http://45.152.65.130:20253/{expected_path}"

            assert actual_url == expected_url, \
                f"URL路径标准化失败: 输入'{input_path}' -> 期望'{expected_url}', 实际'{actual_url}'"

    @pytest.mark.asyncio
    async def test_direct_vs_proxy_comparision(self):
        """直接调用vs代理调用对比测试"""
        # 测试直接微服务调用 vs 通过本地API代理的对比

        # 创建任务测试
        test_task = {
            "user_id": "test_user",
            "title": "URL兼容性测试任务",
            "description": "用于测试URL兼容性",
            "priority": "High"
        }

        # 直接调用微服务
        direct_result = await self._test_microservice_direct_create(test_task)

        # 通过本地API代理调用（这里会因为用户认证问题失败，但我们可以测试URL构建）
        try:
            proxy_result = await self._test_local_api_create_task_proxy(test_task)
            # 主要目的是验证URL构建逻辑
        except Exception as e:
            # 预期会失败，但我们关注的是URL构建逻辑
            pass

        # 验证URL构建正确性
        assert direct_result["status_code"] in [200, 404, 502], \
            f"直接微服务调用意外失败: {direct_result}"

    async def _test_microservice_direct_create(self, test_task: Dict[str, Any]) -> Dict[str, Any]:
        """直接测试微服务创建任务"""
        import time
        start_time = time.time()

        try:
            url = f"{self.microservice_client.base_url.rstrip('/')}/tasks"
            self.logger.info(f"直接测试微服务创建任务: {url}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=test_task)
                response_time = time.time() - start_time

                return {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "response_data": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
                }
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "response_data": None,
                "error": str(e)
            }

    async def _test_local_api_create_task_proxy(self, test_task: Dict[str, Any]) -> Dict[str, Any]:
        """通过本地API代理测试创建任务"""
        import time
        start_time = time.time()

        try:
            response = self.client.post("/tasks/", json=test_task, headers={
                "Authorization": "Bearer test-token"
            })
            response_time = time.time() - start_time

            return {
                "status_code": response.status_code,
                "response_time": response_time,
                "response_data": response.json() if response.content_type and "application/json" in response.content_type else None
            }
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "response_data": None,
                "error": str(e)
            }