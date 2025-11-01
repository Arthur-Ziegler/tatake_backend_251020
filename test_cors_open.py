#!/usr/bin/env python3
"""
CORS开放性测试脚本

验证CORS配置是否完全开放，允许所有域名、IP和端口访问所有API。

测试覆盖：
1. OPTIONS预检请求测试
2. 不同Origin请求测试
3. 自定义Headers测试
4. 跨域认证测试

作者：CORS测试工程师
版本：1.0.0
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CORSTestResult:
    """CORS测试结果"""
    test_name: str
    origin: str
    method: str
    success: bool
    cors_headers: Dict[str, str]
    status_code: int
    error_message: str = ""

class CORSTester:
    """CORS开放性测试器"""

    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.session = None
        self.auth_token = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_auth_token(self) -> str:
        """获取认证令牌"""
        try:
            async with self.session.post(f"{self.base_url}/auth/wechat/login", json={
                "wechat_openid": "cors_test_123456",
                "project": "tatake_backend_f3111d"
            }) as resp:
                data = await resp.json()
                if resp.status == 200 and data.get('code') == 200:
                    return data.get('data', {}).get('access_token', '')
        except Exception as e:
            print(f"获取认证令牌失败: {e}")
        return ""

    async def test_cors_headers(self, origin: str, method: str = "GET", path: str = "/") -> CORSTestResult:
        """测试CORS响应头"""
        headers = {
            'Origin': origin,
            'Access-Control-Request-Method': method,
            'Access-Control-Request-Headers': 'Content-Type,Authorization,X-Custom-Header'
        }

        try:
            # 首先测试OPTIONS预检请求
            async with self.session.options(f"{self.base_url}{path}", headers=headers) as resp:
                cors_headers = {
                    'Access-Control-Allow-Origin': resp.headers.get('Access-Control-Allow-Origin', ''),
                    'Access-Control-Allow-Methods': resp.headers.get('Access-Control-Allow-Methods', ''),
                    'Access-Control-Allow-Headers': resp.headers.get('Access-Control-Allow-Headers', ''),
                    'Access-Control-Allow-Credentials': resp.headers.get('Access-Control-Allow-Credentials', ''),
                    'Access-Control-Max-Age': resp.headers.get('Access-Control-Max-Age', ''),
                    'Access-Control-Expose-Headers': resp.headers.get('Access-Control-Expose-Headers', '')
                }

                success = (
                    cors_headers['Access-Control-Allow-Origin'] in ['*', origin] and
                    cors_headers['Access-Control-Allow-Methods'] == '*' or
                    all(method in cors_headers['Access-Control-Allow-Methods'] for method in ['GET', 'POST', 'PUT', 'DELETE']) and
                    cors_headers['Access-Control-Allow-Headers'] == '*' or
                    all(header in cors_headers['Access-Control-Allow-Headers'] for header in ['Content-Type', 'Authorization', 'X-Custom-Header'])
                )

                return CORSTestResult(
                    test_name=f"OPTIONS预检请求",
                    origin=origin,
                    method=method,
                    success=success,
                    cors_headers=cors_headers,
                    status_code=resp.status
                )

        except Exception as e:
            return CORSTestResult(
                test_name="OPTIONS预检请求",
                origin=origin,
                method=method,
                success=False,
                cors_headers={},
                status_code=0,
                error_message=str(e)
            )

    async def test_actual_request(self, origin: str, method: str = "GET", path: str = "/docs",
                                custom_headers: Dict = None, use_auth: bool = False) -> CORSTestResult:
        """测试实际请求的CORS响应"""
        headers = {'Origin': origin}
        if custom_headers:
            headers.update(custom_headers)
        if use_auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        try:
            if method == 'GET':
                async with self.session.get(f"{self.base_url}{path}", headers=headers) as resp:
                    cors_headers = {
                        'Access-Control-Allow-Origin': resp.headers.get('Access-Control-Allow-Origin', ''),
                        'Access-Control-Allow-Credentials': resp.headers.get('Access-Control-Allow-Credentials', ''),
                        'Access-Control-Expose-Headers': resp.headers.get('Access-Control-Expose-Headers', '')
                    }
                    content = await resp.text()

                    success = (
                        resp.status == 200 and
                        cors_headers['Access-Control-Allow-Origin'] in ['*', origin]
                    )

                    return CORSTestResult(
                        test_name=f"实际{method}请求",
                        origin=origin,
                        method=method,
                        success=success,
                        cors_headers=cors_headers,
                        status_code=resp.status
                    )

            elif method == 'POST':
                async with self.session.post(f"{self.base_url}{path}",
                                           json={"test": "cors_test"}, headers=headers) as resp:
                    cors_headers = {
                        'Access-Control-Allow-Origin': resp.headers.get('Access-Control-Allow-Origin', ''),
                        'Access-Control-Allow-Credentials': resp.headers.get('Access-Control-Allow-Credentials', ''),
                        'Access-Control-Expose-Headers': resp.headers.get('Access-Control-Expose-Headers', '')
                    }

                    success = (
                        resp.status in [200, 422] and  # 422表示参数验证错误，但CORS正常
                        cors_headers['Access-Control-Allow-Origin'] in ['*', origin]
                    )

                    return CORSTestResult(
                        test_name=f"实际{method}请求",
                        origin=origin,
                        method=method,
                        success=success,
                        cors_headers=cors_headers,
                        status_code=resp.status
                    )

        except Exception as e:
            return CORSTestResult(
                test_name=f"实际{method}请求",
                origin=origin,
                method=method,
                success=False,
                cors_headers={},
                status_code=0,
                error_message=str(e)
            )

    async def run_comprehensive_cors_tests(self) -> List[CORSTestResult]:
        """运行全面的CORS测试"""
        print("🌐 开始CORS开放性全面测试...")
        print(f"📅 测试时间: {datetime.now().isoformat()}")
        print(f"🎯 测试目标: {self.base_url}")
        print("=" * 80)

        # 获取认证令牌
        self.auth_token = await self.get_auth_token()
        if self.auth_token:
            print("✅ 获取认证令牌成功")
        else:
            print("⚠️ 认证令牌获取失败，部分测试将跳过")

        results = []

        # 测试各种Origin
        test_origins = [
            "http://localhost:3000",
            "https://localhost:3000",
            "http://127.0.0.1:3000",
            "https://127.0.0.1:3000",
            "http://192.168.1.100:8080",
            "https://192.168.1.100:8080",
            "http://example.com",
            "https://example.com",
            "http://subdomain.example.com:9000",
            "https://subdomain.example.com:9000",
            "http://10.0.0.1:5000",
            "https://172.16.0.1:7000",
            "http://random-domain-12345.com",
            "https://mobile-app://localhost",
            "file://",
            "null"
        ]

        print(f"\n🔍 测试 {len(test_origins)} 个不同Origin的CORS配置...")

        for i, origin in enumerate(test_origins, 1):
            print(f"\n📍 [{i:2d}/{len(test_origins)}] 测试Origin: {origin}")

            # 1. OPTIONS预检请求测试
            options_result = await self.test_cors_headers(origin, "GET", "/tasks/")
            results.append(options_result)

            if options_result.success:
                print(f"   ✅ OPTIONS预检: 成功")
            else:
                print(f"   ❌ OPTIONS预检: 失败 ({options_result.status_code})")
                if options_result.error_message:
                    print(f"      错误: {options_result.error_message}")

            # 2. 实际GET请求测试
            get_result = await self.test_actual_request(origin, "GET", "/docs")
            results.append(get_result)

            if get_result.success:
                print(f"   ✅ GET请求: 成功")
            else:
                print(f"   ❌ GET请求: 失败 ({get_result.status_code})")

            # 3. 实际POST请求测试 (测试Task API)
            post_headers = {'Content-Type': 'application/json'}
            if self.auth_token:
                post_headers['Authorization'] = f'Bearer {self.auth_token}'

            post_result = await self.test_actual_request(
                origin, "POST", "/tasks/",
                custom_headers=post_headers
            )
            results.append(post_result)

            if post_result.success:
                print(f"   ✅ POST请求: 成功")
            else:
                print(f"   ❌ POST请求: 失败 ({post_result.status_code})")

            # 4. 带认证的请求测试
            if self.auth_token and i <= 5:  # 只测试前5个origin的认证请求
                auth_result = await self.test_actual_request(
                    origin, "GET", "/rewards/points",
                    use_auth=True
                )
                results.append(auth_result)

                if auth_result.success:
                    print(f"   ✅ 认证请求: 成功")
                else:
                    print(f"   ❌ 认证请求: 失败 ({auth_result.status_code})")

        return results

    def print_summary(self, results: List[CORSTestResult]):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📊 CORS开放性测试总结报告")
        print("=" * 80)

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"📈 总体统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过数量: {passed_tests}")
        print(f"   失败数量: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        # 按测试类型分组统计
        options_tests = [r for r in results if "OPTIONS" in r.test_name]
        get_tests = [r for r in results if "实际GET" in r.test_name]
        post_tests = [r for r in results if "实际POST" in r.test_name]
        auth_tests = [r for r in results if "认证请求" in r.test_name]

        print(f"\n📋 分类统计:")
        print(f"   OPTIONS预检: {sum(1 for r in options_tests if r.success)}/{len(options_tests)} ({(sum(1 for r in options_tests if r.success)/len(options_tests)*100):.1f}%)")
        print(f"   GET请求: {sum(1 for r in get_tests if r.success)}/{len(get_tests)} ({(sum(1 for r in get_tests if r.success)/len(get_tests)*100):.1f}%)")
        print(f"   POST请求: {sum(1 for r in post_tests if r.success)}/{len(post_tests)} ({(sum(1 for r in post_tests if r.success)/len(post_tests)*100):.1f}%)")
        if auth_tests:
            print(f"   认证请求: {sum(1 for r in auth_tests if r.success)}/{len(auth_tests)} ({(sum(1 for r in auth_tests if r.success)/len(auth_tests)*100):.1f}%)")

        # 显示失败的测试
        failed_tests = [r for r in results if not r.success]
        if failed_tests:
            print(f"\n❌ 失败的测试详情:")
            for i, failed_test in enumerate(failed_tests[:10], 1):  # 只显示前10个失败
                print(f"   {i}. {failed_test.origin} - {failed_test.test_name}")
                print(f"      状态码: {failed_test.status_code}")
                if failed_test.error_message:
                    print(f"      错误: {failed_test.error_message}")

            if len(failed_tests) > 10:
                print(f"      ... 还有 {len(failed_tests) - 10} 个失败测试")

        # CORS配置分析
        print(f"\n🔍 CORS配置分析:")
        if success_rate >= 95:
            print("🟢 CORS状态: 完全开放 - 允许所有域名、IP和端口访问")
        elif success_rate >= 85:
            print("🟡 CORS状态: 基本开放 - 大部分域名可以访问")
        elif success_rate >= 70:
            print("🟠 CORS状态: 部分限制 - 部分域名访问受限")
        else:
            print("🔴 CORS状态: 严格限制 - 多数域名无法访问")

        print(f"\n🎯 测试完成时间: {datetime.now().isoformat()}")

async def main():
    """主函数"""
    async with CORSTester() as tester:
        results = await tester.run_comprehensive_cors_tests()
        tester.print_summary(results)

if __name__ == "__main__":
    asyncio.run(main())