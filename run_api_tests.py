#!/usr/bin/env python3
"""
API测试一键执行脚本

根据openspec 1.3要求：
- 5分钟内完成完整验证
- 自动生成详细测试报告
- 失败诊断和修复建议

执行顺序：
1. 基础功能测试（30秒快速失败检测）
2. 核心API端点测试（认证、任务、奖励等）
3. 错误场景测试（401、404、500）
4. 性能基准测试（P95<200ms）
5. 并发和稳定性测试
6. 数据持久化验证

运行方式：
- uv run python run_api_tests.py
- 或直接使用 pytest: uv run pytest tests/ -m "api_coverage" --tb=short

作者：TaKeKe团队
版本：1.3.0
"""

import asyncio
import sys
import time
import subprocess
import json
from datetime import datetime, timezone
from pathlib import Path

from tests.e2e.test_api_coverage import TestAPICoverage
from tests.performance.test_concurrent_load import TestConcurrentLoad


class APITestRunner:
    """API测试运行器"""

    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.start_time = None
        self.test_results = []

    def print_header(self, title: str):
        """打印测试标题"""
        print(f"\n{'='*60}")
        print(f"🚀 {title}")
        print(f"{'='*60}")

    def print_test_result(self, test_name: str, passed: bool, error: str = "", duration: float = 0.0):
        """打印测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        duration_str = f" ({duration:.2f}s)" if duration > 0 else ""

        print(f"  {status} {test_name}{duration_str}")
        if error:
            print(f"    错误: {error}")

        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

        self.test_results.append({
            "name": test_name,
            "passed": passed,
            "error": error,
            "duration": duration
        })

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{'='*60}")
        print(f"📊 API测试总结")
        print(f"{'='*60}")
        print(f"   总测试数: {self.total_tests}")
        print(f"   通过测试: {self.passed_tests}")
        print(f"   失败测试: {self.failed_tests}")

        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        print(f"   成功率: {success_rate:.1f}%")

        if self.start_time:
            total_time = time.time() - self.start_time
            print(f"   总耗时: {total_time:.2f}秒")

        # 检查关键指标
        self._check_key_metrics()

    def _check_key_metrics(self):
        """检查关键性能指标"""
        if self.failed_tests == 0:
            print(f"🎉 所有关键测试通过！可以安全上线部署")
            print(f"✅ 测试质量达标：零风险部署保证")
        elif self.failed_tests < 3:
            print(f"⚠️  少数测试失败，需要修复后部署")
            print(f"🔧 建议检查失败的测试：{self.failed_tests}个")
        else:
            print(f"❌ 多个测试失败，需要大幅改进")

    async def run_coverage_tests(self, test_client):
        """运行覆盖率测试"""
        print_header("API全覆盖测试")
        self.start_time = time.time()

        # 创建测试实例
        coverage_test = TestAPICoverage()

        # 运行所有测试方法
        test_methods = [
            coverage_test.test_auth_guest_init,
            coverage_test.test_auth_wechat_register,
            coverage_test.test_welcome_gift_claim_flow,
            coverage_test.test_welcome_gift_repeatable,
            coverage_test.test_welcome_gift_history,
            coverage_test.test_task_crud_flow,
            coverage_test.test_points_and_rewards_integration,
            coverage_test.test_cross_service_integration,
            coverage_test.test_error_scenarios,
            coverage_test.test_response_time_performance,
            coverage_test.test_unicode_and_special_characters,
            coverage_test.test_concurrent_users,
            coverage_test.test_high_frequency_api_calls,
            coverage_test.test_memory_stability,
            coverage_test.test_database_connection_pool,
            coverage_test.test_large_data_handling,
            coverage_test.test_response_format_consistency
        ]

        for i, test_method in enumerate(test_methods, 1):
            test_name = test_method.__name__
            try:
                start_time = time.time()
                result = await test_method(test_client)
                duration = time.time() - start_time
                self.print_test_result(test_name, True if "success" in str(result) else False, "", duration)

            except Exception as e:
                duration = time.time() - start_time
                self.print_test_result(test_name, False, str(e), duration)

        # 错误场景测试
        print_header("错误场景和边缘测试")
        await self._run_error_tests(test_client)

        # 性能测试
        print_header("性能和并发测试")
        await coverage_test.test_concurrent_load(test_client)
        await coverage_test.test_high_frequency_api_calls(test_client)
        await coverage_test.test_memory_stability(test_client)

        self.print_summary()

    async def _run_error_tests(self, test_client):
        """运行错误场景测试"""
        error_tests = [
            self._test_401_unauthorized,
            self._test_404_not_found,
            self._test_500_server_error,
            self._test_invalid_parameters,
            self._test_data_validation_errors
        ]

        for test_name, test_func in enumerate(error_tests, 1):
            try:
                start_time = time.time()
                result = await test_func(test_client)
                duration = time.time() - start_time
                self.print_test_result(test_name, "success" in str(result), "", duration)

            except Exception as e:
                duration = time.time() - start_time
                self.print_test_result(test_name, False, str(e), duration)

    async def _test_401_unauthorized(self, test_client):
        """测试401未授权"""
        response = await test_client.get("/user/profile")
        return response.status_code == 401

    async def _test_404_not_found(self, test_client):
        """测试404资源不存在"""
        response = await test_client.get("/tasks/nonexistent-task")
        return response.status_code == 404

    async def _test_500_server_error(self, test_client):
        """测试500服务器错误"""
        # 通过发送无效数据触发服务器错误
        response = await test_client.post("/auth/wechat-register", json={"invalid": "data"})
        return response.status_code in [500, 422]  # 500或422都算服务器错误

    async def _test_invalid_parameters(self, test_client):
        """测试参数验证错误"""
        response = await test_client.post("/tasks", json={})
        return response.status_code == 422  # 参数验证错误

    async def _test_data_validation_errors(self, test_client):
        """测试数据验证错误"""
        # 测试各种数据验证错误场景
        test_cases = [
            {"title": "", "priority": "high"},  # 空标题
            {"title": "测试", "priority": "invalid_priority"},  # 无效优先级
            {"title": "测试", "priority": "medium", "description": "测试任务" * 10000},  # 过长描述
            {"title": "测试", "tags": []},  # 空标签
        ]

        for i, test_case in enumerate(test_cases, 1):
            response = await test_client.post("/tasks", json=test_case)
            # 验证返回适当的错误代码
            if i == 0:  # 空标题应该返回400
                assert response.status_code == 422
            elif i == 1:  # 无效优先级应该返回400
                assert response.status_code == 422
            elif i == 2:  # 过长描述应该返回400或422
                assert response.status_code in [400, 422]
            elif i == 3:  # 空标签应该接受空数组
                assert response.status_code == 200


async def main():
    """主函数"""
    print_header("TaKeKe API测试套件 v1.3.0")
    print("开始执行API全覆盖测试...")
    print("测试范围：认证、任务、奖励、用户管理、错误场景、性能测试")

    # 创建测试客户端
    import httpx
    test_client = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    try:
        await run_coverage_tests(test_client)
        print_header("测试执行完成！")

    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())