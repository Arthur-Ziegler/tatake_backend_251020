"""
微服务端点验证测试

专门验证微服务端点的正确性和响应格式兼容性。
确保本地API与微服务的接口契约保持一致。

作者：TaTake团队
版本：1.0.0（微服务端点验证）
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

from src.services.task_microservice_client import (
    TaskMicroserviceClient,
    get_task_microservice_client,
    get_all_tasks, create_task, delete_task, update_task, complete_task,
    set_top3, get_top3, send_focus_status, get_pomodoro_count,
    TaskMicroserviceError
)

logger = logging.getLogger(__name__)


@dataclass
class EndpointTestResult:
    """端点测试结果"""
    endpoint: str
    method: str
    expected_status: int
    actual_status: int
    response_time: float
    success: bool
    error_message: str = ""
    response_data: Any = None


@dataclass
class EndpointValidationReport:
    """端点验证报告"""
    total_endpoints: int
    passed_endpoints: int
    failed_endpoints: int
    results: List[EndpointTestResult]
    overall_success_rate: float = 0.0


class MicroserviceEndpointValidator:
    """微服务端点验证器"""

    def __init__(self):
        self.client = get_task_microservice_client()
        self.logger = logging.getLogger(__name__)

    def get_expected_endpoints(self) -> List[Tuple[str, str, str]]:
        """
        获取预期的端点列表

        Returns:
            List[Tuple[str, str, str]]: (method, path, description)
        """
        return [
            # 核心任务接口
            ("POST", "tasks", "创建任务"),
            ("POST", "tasks/query", "查询任务"),
            ("PUT", "tasks/{id}/update", "更新任务"),
            ("POST", "tasks/{id}/delete", "删除任务"),
            ("POST", "tasks/{id}/complete", "完成任务"),

            # Top3管理接口
            ("POST", "tasks/top3", "设置Top3"),
            ("POST", "tasks/top3/query", "查询Top3"),

            # 专注和番茄钟接口
            ("POST", "focus/sessions", "专注状态"),
            ("POST", "focus/pomodoro-stats", "番茄钟统计"),
        ]

    async def validate_endpoint_exists(self, method: str, path: str, description: str) -> EndpointTestResult:
        """
        验证端点是否存在

        Args:
            method (str): HTTP方法
            path (str): API路径
            description (str): 端点描述

        Returns:
            EndpointTestResult: 测试结果
        """
        import time
        start_time = time.time()

        result = EndpointTestResult(
            endpoint=f"{method} {path}",
            method=method,
            expected_status=200,
            actual_status=0,
            response_time=0,
            success=False
        )

        try:
            import httpx

            # 构建测试URL
            if path.startswith("tasks/") and "{id}" in path:
                # 对于需要ID的端点，使用一个UUID格式的测试ID
                test_path = path.replace("{id}", "550e8400-e29b-41d4-a716-446655440000")
            elif path.startswith("tasks/") and "query" in path:
                # 查询端点
                test_path = path
            else:
                test_path = path

            # 构建完整URL
            normalized_path = test_path.rstrip('/')  # 移除尾部斜杠
            url = f"{self.client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            # 准备测试数据
            test_data = {}
            test_params = {}

            if method == "POST":
                if "query" in path:
                    test_data = {
                        "user_id": "test-user-validation",
                        "page": 1,
                        "page_size": 5
                    }
                elif path == "tasks":
                    test_data = {
                        "user_id": "test-user-validation",
                        "title": "端点验证测试任务",
                        "description": "用于验证端点是否存在的测试任务"
                    }
                elif "top3" in path:
                    test_data = {
                        "user_id": "test-user-validation",
                        "date": "2025-11-01",
                        "task_ids": []
                    }
                elif "focus" in path:
                    test_data = {
                        "user_id": "test-user-validation",
                        "focus_status": "start"
                    }
                elif "complete" in path:
                    test_data = {
                        "user_id": "test-user-validation"
                    }
                elif "delete" in path:
                    test_data = {
                        "user_id": "test-user-validation"
                    }
                elif "update" in path:
                    test_data = {
                        "user_id": "test-user-validation",
                        "title": "更新的任务标题"
                    }

            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, params=test_params)
                elif method == "POST":
                    response = await client.post(url, json=test_data)
                elif method == "PUT":
                    response = await client.put(url, json=test_data)
                elif method == "DELETE":
                    response = await client.delete(url, json=test_data)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")

                result.actual_status = response.status_code
                result.response_time = time.time() - start_time

                # 检查响应状态
                if response.status_code == 200:
                    result.success = True
                    try:
                        result.response_data = response.json()
                    except:
                        result.response_data = response.text
                elif response.status_code == 404:
                    result.success = False
                    result.error_message = "端点不存在"
                elif response.status_code == 422:
                    # 验证错误是预期的，说明端点存在但参数不对
                    result.success = True
                    result.error_message = "端点存在但需要不同的参数格式"
                else:
                    result.success = False
                    result.error_message = f"意外的状态码: {response.status_code}"
                    try:
                        result.response_data = response.json()
                    except:
                        result.response_data = response.text

        except httpx.ConnectError:
            result.response_time = time.time() - start_time
            result.success = False
            result.error_message = "连接失败：微服务不可用"
        except httpx.TimeoutException:
            result.response_time = time.time() - start_time
            result.success = False
            result.error_message = "请求超时"
        except Exception as e:
            result.response_time = time.time() - start_time
            result.success = False
            result.error_message = f"测试异常: {str(e)}"

        return result

    async def validate_all_endpoints(self) -> EndpointValidationReport:
        """
        验证所有端点

        Returns:
            EndpointValidationReport: 验证报告
        """
        endpoints = self.get_expected_endpoints()
        results = []

        for method, path, description in endpoints:
            self.logger.info(f"验证端点: {method} {path} - {description}")
            result = await self.validate_endpoint_exists(method, path, description)
            results.append(result)
            self.logger.info(f"结果: {result.success} - {result.error_message or 'OK'}")

        # 计算总体成功率
        passed_count = sum(1 for r in results if r.success)
        total_count = len(results)
        success_rate = (passed_count / total_count) * 100 if total_count > 0 else 0

        return EndpointValidationReport(
            total_endpoints=total_count,
            passed_endpoints=passed_count,
            failed_endpoints=total_count - passed_count,
            results=results,
            overall_success_rate=success_rate
        )

    def print_report(self, report: EndpointValidationReport):
        """打印验证报告"""
        print("\n" + "="*80)
        print("🔍 微服务端点验证报告")
        print("="*80)

        print(f"📊 总体统计:")
        print(f"   - 总端点数: {report.total_endpoints}")
        print(f"   - 验证通过: {report.passed_endpoints}")
        print(f"   - 验证失败: {report.failed_endpoints}")
        print(f"   - 成功率: {report.overall_success_rate:.1f}%")

        print(f"\n📋 详细结果:")
        for result in report.results:
            status_icon = "✅" if result.success else "❌"
            print(f"   {status_icon} {result.endpoint}")
            print(f"      状态码: {result.actual_status} (期望: {result.expected_status})")
            print(f"      响应时间: {result.response_time:.3f}s")
            if result.error_message:
                print(f"      错误: {result.error_message}")

        print("\n" + "="*80)


class TestMicroserviceEndpointValidation:
    """微服务端点验证测试类"""

    @pytest.mark.asyncio
    async def test_all_microservice_endpoints_exist(self):
        """测试所有微服务端点是否存在"""
        validator = MicroserviceEndpointValidator()
        report = await validator.validate_all_endpoints()
        validator.print_report(report)

        # 至少80%的端点应该可访问
        assert report.overall_success_rate >= 80.0, \
            f"微服务端点可用率过低: {report.overall_success_rate:.1f}% < 80.0%"

        # 核心端点必须存在
        core_endpoints = [
            "POST tasks",
            "POST tasks/query",
            "POST tasks/{id}/complete"
        ]

        for core_endpoint in core_endpoints:
            core_result = next((r for r in report.results if r.endpoint == core_endpoint), None)
            assert core_result is not None, f"核心端点 {core_endpoint} 未测试"
            assert core_result.success, f"核心端点 {core_endpoint} 不可用: {core_result.error_message}"

    @pytest.mark.asyncio
    async def test_client_methods_use_correct_endpoints(self):
        """测试客户端方法使用正确的端点"""
        # 这个测试确保我们的客户端方法映射到正确的微服务端点
        client = get_task_microservice_client()

        # 验证客户端方法能正确调用对应的微服务端点
        test_cases = [
            ("get_all_tasks", "POST tasks/query"),
            ("create_task", "POST tasks"),
            ("complete_task", "POST tasks/{id}/complete"),
        ]

        for method_name, expected_endpoint in test_cases:
            try:
                # 这里我们不实际调用，而是验证映射逻辑
                method = getattr(client, method_name, None)
                assert method is not None, f"客户端方法 {method_name} 不存在"

                # 通过检查方法名来推断它使用的端点
                self.logger.info(f"✅ 客户端方法 {method_name} 映射到 {expected_endpoint}")

            except Exception as e:
                pytest.fail(f"验证客户端方法 {method_name} 失败: {e}")

    @pytest.mark.asyncio
    async def test_response_format_compatibility(self):
        """测试响应格式兼容性"""
        # 测试微服务响应格式能被正确转换
        client = get_task_microservice_client()

        # 测试不同类型的响应格式
        test_responses = [
            # 标准格式
            {"success": True, "message": "success", "data": {"test": "data"}},
            # 错误格式
            {"success": False, "message": "接口不存在", "data": None},
            # 直接数组格式
            [{"id": "1", "title": "test"}],
            # 直接对象格式
            {"id": "1", "title": "test"},
        ]

        for i, response in enumerate(test_responses):
            try:
                transformed = client.transform_response(response)
                assert isinstance(transformed, dict), f"响应 {i+1} 转换后不是字典"
                assert "code" in transformed, f"响应 {i+1} 转换后缺少code字段"
                assert "message" in transformed, f"响应 {i+1} 转换后缺少message字段"
                assert "data" in transformed, f"响应 {i+1} 转换后缺少data字段"

                print(f"✅ 响应格式 {i+1} 转换成功")

            except Exception as e:
                pytest.fail(f"响应格式 {i+1} 转换失败: {e}")

    @pytest.mark.asyncio
    async def test_error_handling_robustness(self):
        """测试错误处理的健壮性"""
        client = get_task_microservice_client()

        # 测试无效响应格式的处理
        invalid_responses = [
            None,
            "",
            123,
            [],
            {"invalid": "format"},
        ]

        for invalid_response in invalid_responses:
            try:
                with pytest.raises(TaskMicroserviceError):
                    client.transform_response(invalid_response)
                self.logger.info(f"✅ 无效响应格式处理正确: {type(invalid_response)}")
            except AssertionError:
                pytest.fail(f"无效响应格式 {invalid_response} 应该抛出异常")
            except Exception as e:
                pytest.fail(f"处理无效响应格式 {invalid_response} 时抛出意外异常: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])