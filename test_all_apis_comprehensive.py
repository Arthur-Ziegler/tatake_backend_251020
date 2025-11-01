#!/usr/bin/env python3
"""
全面API测试脚本

系统性测试TaKeKe后端所有域的API端点，确保所有功能正常工作。

测试覆盖：
1. 认证API - 微服务
2. Task API - 微服务代理（10个端点）
3. 奖励系统API - 微服务
4. 聊天API - 本地实现
5. Focus API - 本地实现
6. 健康检查API

作者：系统测试
版本：1.0.0
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, date
import sys
import os

# 添加项目路径
sys.path.append('.')

@dataclass
class TestResult:
    """测试结果"""
    endpoint: str
    method: str
    status_code: int
    success: bool
    response_data: Any = None
    error_message: str = ""
    duration: float = 0.0

@dataclass
class APITestCase:
    """API测试用例"""
    name: str
    method: str
    endpoint: str
    data: Dict = None
    params: Dict = None
    headers: Dict = None
    expected_status: int = 200
    description: str = ""

class ComprehensiveAPITester:
    """全面API测试器"""

    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        self.test_user_id = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_endpoint(self, test_case: APITestCase) -> TestResult:
        """测试单个API端点"""
        url = f"{self.base_url}{test_case.endpoint}"
        headers = test_case.headers or {}

        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        start_time = datetime.now()

        try:
            if test_case.method.upper() == 'GET':
                async with self.session.get(url, params=test_case.params, headers=headers) as resp:
                    status_code = resp.status
                    response_data = await resp.json() if resp.content_type == 'application/json' else await resp.text()
            elif test_case.method.upper() == 'POST':
                async with self.session.post(url, json=test_case.data, params=test_case.params, headers=headers) as resp:
                    status_code = resp.status
                    response_data = await resp.json() if resp.content_type == 'application/json' else await resp.text()
            elif test_case.method.upper() == 'PUT':
                async with self.session.put(url, json=test_case.data, headers=headers) as resp:
                    status_code = resp.status
                    response_data = await resp.json() if resp.content_type == 'application/json' else await resp.text()
            elif test_case.method.upper() == 'DELETE':
                async with self.session.delete(url, headers=headers) as resp:
                    status_code = resp.status
                    response_data = await resp.json() if resp.content_type == 'application/json' else await resp.text()
            else:
                raise ValueError(f"不支持的HTTP方法: {test_case.method}")

            duration = (datetime.now() - start_time).total_seconds()
            success = status_code == test_case.expected_status

            return TestResult(
                endpoint=test_case.endpoint,
                method=test_case.method,
                status_code=status_code,
                success=success,
                response_data=response_data,
                duration=duration
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return TestResult(
                endpoint=test_case.endpoint,
                method=test_case.method,
                status_code=0,
                success=False,
                error_message=str(e),
                duration=duration
            )

    async def authenticate(self) -> bool:
        """获取认证令牌"""
        auth_test = APITestCase(
            name="微信登录认证",
            method="POST",
            endpoint="/auth/wechat/login",
            data={
                "wechat_openid": "test_comprehensive_api_123456",
                "project": "tatake_backend_f3111d"
            },
            expected_status=200,
            description="通过微信OpenID获取访问令牌"
        )

        result = await self.test_endpoint(auth_test)

        if result.success and isinstance(result.response_data, dict):
            if result.response_data.get('code') == 200:
                data = result.response_data.get('data', {})
                self.auth_token = data.get('access_token')
                self.test_user_id = data.get('user_id')
                print(f"✅ 认证成功 - 用户ID: {self.test_user_id}")
                return True

        print(f"❌ 认证失败: {result.error_message or result.response_data}")
        return False

    def get_all_test_cases(self) -> List[APITestCase]:
        """获取所有测试用例"""
        test_cases = []

        # 1. 认证API测试
        test_cases.extend([
            APITestCase(
                name="刷新令牌",
                method="POST",
                endpoint="/auth/refresh",
                data={"refresh_token": "dummy_refresh_token"},
                expected_status=401,  # 预期失败，因为令牌无效
                description="测试令牌刷新接口"
            ),
            APITestCase(
                name="验证令牌",
                method="GET",
                endpoint="/auth/verify",
                expected_status=401,  # 没有提供令牌
                description="测试令牌验证接口"
            )
        ])

        # 2. Task API测试 - 微服务代理模式（10个端点）
        test_cases.extend([
            APITestCase(
                name="创建任务",
                method="POST",
                endpoint="/tasks/",
                data={
                    "title": "测试任务 - 全面API测试",
                    "description": "用于验证API完整性的测试任务",
                    "priority": "high",
                    "status": "pending",
                    "tags": ["测试", "API验证"]
                },
                expected_status=200,
                description="测试任务创建功能"
            ),
            APITestCase(
                name="查询任务列表",
                method="POST",
                endpoint="/tasks/query",
                data={
                    "page": 1,
                    "page_size": 10,
                    "status": "pending"
                },
                expected_status=200,
                description="测试任务列表查询功能"
            ),
            APITestCase(
                name="获取今日Top3",
                method="GET",
                endpoint=f"/tasks/special/top3/{date.today().isoformat()}",
                expected_status=200,
                description="测试获取今日Top3任务功能"
            ),
            APITestCase(
                name="设置Top3任务",
                method="POST",
                endpoint="/tasks/special/top3",
                data={
                    "date": date.today().isoformat(),
                    "task_ids": [
                        "550e8400-e29b-41d4-a716-446655440000",
                        "550e8400-e29b-41d4-a716-446655440001",
                        "550e8400-e29b-41d4-a716-446655440002"
                    ]
                },
                expected_status=200,
                description="测试设置Top3任务功能"
            ),
            APITestCase(
                name="记录专注状态",
                method="POST",
                endpoint="/tasks/focus-status",
                data={
                    "focus_status": "focused",
                    "duration_minutes": 30,
                    "task_id": "550e8400-e29b-41d4-a716-446655440000"
                },
                expected_status=200,
                description="测试专注状态记录功能"
            ),
            APITestCase(
                name="获取番茄钟计数",
                method="GET",
                endpoint="/tasks/pomodoro-count",
                params={"date_filter": "today"},
                expected_status=200,
                description="测试番茄钟计数查询功能"
            ),
            APITestCase(
                name="更新任务",
                method="PUT",
                endpoint="/tasks/550e8400-e29b-41d4-a716-446655440000",
                data={
                    "title": "更新后的任务标题",
                    "description": "任务描述已更新",
                    "priority": "medium",
                    "status": "in_progress"
                },
                expected_status=200,
                description="测试任务更新功能"
            ),
            APITestCase(
                name="完成任务",
                method="POST",
                endpoint="/tasks/550e8400-e29b-41d4-a716-446655440000/complete",
                data={
                    "completion_notes": "任务已完成",
                    "actual_duration": 45
                },
                expected_status=200,
                description="测试任务完成功能"
            ),
            APITestCase(
                name="删除任务",
                method="DELETE",
                endpoint="/tasks/550e8400-e29b-41d4-a716-446655440000",
                expected_status=200,
                description="测试任务删除功能"
            ),
            APITestCase(
                name="Task健康检查",
                method="GET",
                endpoint="/tasks/health",
                expected_status=200,
                description="测试Task域健康检查"
            )
        ])

        # 3. 奖励系统API测试 - 微服务
        test_cases.extend([
            APITestCase(
                name="获取积分余额",
                method="GET",
                endpoint="/rewards/balance",
                expected_status=200,
                description="测试积分余额查询"
            ),
            APITestCase(
                name="获取积分历史",
                method="GET",
                endpoint="/rewards/history",
                params={"page": 1, "page_size": 10},
                expected_status=200,
                description="测试积分历史查询"
            ),
            APITestCase(
                name="获取奖励列表",
                method="GET",
                endpoint="/rewards/list",
                expected_status=200,
                description="测试奖励列表查询"
            )
        ])

        # 4. 聊天API测试 - 本地实现
        test_cases.extend([
            APITestCase(
                name="创建聊天会话",
                method="POST",
                endpoint="/chat/sessions",
                data={
                    "title": "API测试会话",
                    "context": "全面API验证测试"
                },
                expected_status=200,
                description="测试创建聊天会话"
            ),
            APITestCase(
                name="发送聊天消息",
                method="POST",
                endpoint="/chat/message",
                data={
                    "session_id": "test_session_123",
                    "message": "你好，这是一个API测试消息",
                    "message_type": "user"
                },
                expected_status=200,
                description="测试发送聊天消息"
            )
        ])

        # 5. Focus API测试 - 本地实现
        test_cases.extend([
            APITestCase(
                name="开始专注会话",
                method="POST",
                endpoint="/focus/session/start",
                data={
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "planned_duration": 25
                },
                expected_status=200,
                description="测试开始专注会话"
            ),
            APITestCase(
                name="结束专注会话",
                method="POST",
                endpoint="/focus/session/end",
                data={
                    "session_id": "test_session_456",
                    "actual_duration": 23,
                    "completion_status": "completed"
                },
                expected_status=200,
                description="测试结束专注会话"
            ),
            APITestCase(
                name="获取专注统计",
                method="GET",
                endpoint="/focus/stats",
                params={"period": "today"},
                expected_status=200,
                description="测试专注统计查询"
            )
        ])

        # 6. 系统级API测试
        test_cases.extend([
            APITestCase(
                name="根路径健康检查",
                method="GET",
                endpoint="/",
                expected_status=200,
                description="测试根路径健康检查"
            ),
            APITestCase(
                name="API文档",
                method="GET",
                endpoint="/docs",
                expected_status=200,
                description="测试API文档访问"
            ),
            APITestCase(
                name="OpenAPI规范",
                method="GET",
                endpoint="/openapi.json",
                expected_status=200,
                description="测试OpenAPI规范访问"
            )
        ])

        return test_cases

    async def run_all_tests(self) -> Dict[str, List[TestResult]]:
        """运行所有测试"""
        print("🧪 开始全面API测试...")
        print(f"📅 测试时间: {datetime.now().isoformat()}")
        print(f"🌐 测试目标: {self.base_url}")
        print("=" * 80)

        # 首先进行认证
        if not await self.authenticate():
            print("❌ 认证失败，跳过需要认证的测试")

        results = {
            "认证API": [],
            "Task API": [],
            "奖励系统API": [],
            "聊天API": [],
            "Focus API": [],
            "系统API": []
        }

        all_test_cases = self.get_all_test_cases()
        total_tests = len(all_test_cases)
        passed_tests = 0
        failed_tests = 0

        for i, test_case in enumerate(all_test_cases, 1):
            print(f"\n🔍 [{i:2d}/{total_tests}] 测试: {test_case.name}")
            print(f"   📝 {test_case.description}")
            print(f"   🔗 {test_case.method} {test_case.endpoint}")

            result = await self.test_endpoint(test_case)

            # 分类结果
            if "认证" in test_case.name or "auth" in test_case.endpoint.lower():
                results["认证API"].append(result)
            elif "tasks" in test_case.endpoint or "task" in test_case.name.lower():
                results["Task API"].append(result)
            elif "rewards" in test_case.endpoint or "reward" in test_case.name.lower():
                results["奖励系统API"].append(result)
            elif "chat" in test_case.endpoint or "聊天" in test_case.name:
                results["聊天API"].append(result)
            elif "focus" in test_case.endpoint or "专注" in test_case.name:
                results["Focus API"].append(result)
            else:
                results["系统API"].append(result)

            # 显示结果
            if result.success:
                print(f"   ✅ 成功 ({result.status_code}) - {result.duration:.3f}s")
                passed_tests += 1
            else:
                print(f"   ❌ 失败 ({result.status_code}) - {result.duration:.3f}s")
                if result.error_message:
                    print(f"      🚨 错误: {result.error_message}")
                failed_tests += 1

        return results, passed_tests, failed_tests

    def print_summary(self, results: Dict[str, List[TestResult]], passed: int, failed: int):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📊 API测试总结报告")
        print("=" * 80)

        total = passed + failed
        success_rate = (passed / total * 100) if total > 0 else 0

        print(f"📈 总体统计:")
        print(f"   总测试数: {total}")
        print(f"   通过数量: {passed}")
        print(f"   失败数量: {failed}")
        print(f"   成功率: {success_rate:.1f}%")

        print(f"\n📋 分类统计:")
        for category, category_results in results.items():
            if category_results:
                category_passed = sum(1 for r in category_results if r.success)
                category_total = len(category_results)
                category_rate = (category_passed / category_total * 100) if category_total > 0 else 0
                print(f"   {category}: {category_passed}/{category_total} ({category_rate:.1f}%)")

        # 显示失败的测试
        failed_tests = []
        for category_results in results.values():
            failed_tests.extend([r for r in category_results if not r.success])

        if failed_tests:
            print(f"\n❌ 失败的测试详情:")
            for i, failed_test in enumerate(failed_tests, 1):
                print(f"   {i}. {failed_test.method} {failed_test.endpoint}")
                print(f"      状态码: {failed_test.status_code}")
                if failed_test.error_message:
                    print(f"      错误: {failed_test.error_message}")

        print(f"\n🎯 测试完成时间: {datetime.now().isoformat()}")

        # 系统状态评估
        if success_rate >= 90:
            print("🟢 系统状态: 优秀 - API功能基本正常")
        elif success_rate >= 75:
            print("🟡 系统状态: 良好 - 大部分API功能正常，少数需要关注")
        elif success_rate >= 50:
            print("🟠 系统状态: 一般 - 约一半API正常，需要检查失败项")
        else:
            print("🔴 系统状态: 需要修复 - 多数API存在问题，建议立即处理")

async def main():
    """主函数"""
    async with ComprehensiveAPITester() as tester:
        results, passed, failed = await tester.run_all_tests()
        tester.print_summary(results, passed, failed)

if __name__ == "__main__":
    asyncio.run(main())