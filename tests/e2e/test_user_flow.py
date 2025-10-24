#!/usr/bin/env python3
"""
完整用户操作流程测试脚本

模拟真实前端用户操作，包括：
1. 游客初始化
2. 短信登录
3. 使用token进行任务管理操作
4. 完成任务获得奖励
5. Top3设置
6. 全面验证所有API功能

作者：TaTakeKe团队
版本：2.0.0 - 完整用户流程测试
"""

import requests
import json
from typing import Dict, Any, Optional
import time
import uuid

# API基础URL（无前缀）
BASE_URL = "http://localhost:8001"

class UserFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.auth_token = None
        self.user_id = None
        self.device_id = str(uuid.uuid4())
        self.phone_number = "13800138000"  # 测试手机号

    def log_test(self, test_name: str, method: str, url: str,
                 expected_status: int, actual_status: int, response: Dict[Any, Any]):
        """记录测试结果"""
        status = "✅ PASS" if actual_status == expected_status else "❌ FAIL"
        self.test_results.append({
            "test_name": test_name,
            "method": method,
            "url": url,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "status": status,
            "response": response
        })
        print(f"{status} {test_name}: {method} {url} ({actual_status})")

        # 检查响应格式是否为 {code, message, data}
        if isinstance(response, dict) and "code" in response and "message" in response:
            print(f"   ✅ 响应格式正确: {response['code']} - {response['message']}")
        else:
            print(f"   ❌ 响应格式错误: {response}")

    def test_api(self, method: str, endpoint: str, data: Dict[Any, Any] = None,
                 expected_status: int = 200, headers: Dict[str, str] = None) -> Dict[Any, Any]:
        """测试单个API"""
        url = f"{BASE_URL}{endpoint}"

        request_headers = {}
        if headers:
            request_headers.update(headers)

        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=request_headers)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=request_headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=request_headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=request_headers)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}

            self.log_test(
                test_name=f"{method.upper()} {endpoint}",
                method=method.upper(),
                url=url,
                expected_status=expected_status,
                actual_status=response.status_code,
                response=response_data
            )

            return response_data

        except Exception as e:
            print(f"❌ 测试失败: {method.upper()} {url} - {str(e)}")
            return {"error": str(e)}

    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        if not self.auth_token:
            raise ValueError("未获取到认证token")
        return {"Authorization": f"Bearer {self.auth_token}"}

    def test_guest_init(self):
        """测试游客初始化"""
        print("\n🔐 测试游客初始化")

        data = {
            "device_id": self.device_id,
            "device_type": "web"
        }

        response = self.test_api("POST", "/auth/guest/init", data, expected_status=200)

        if response.get("code") == 200 and response.get("data", {}).get("access_token"):
            self.auth_token = response["data"]["access_token"]
            self.user_id = response["data"].get("user_id")
            print(f"   ✅ 获得游客token: {self.auth_token[:20]}...")
            print(f"   ✅ 用户ID: {self.user_id}")
            return True
        else:
            print(f"   ❌ 游客初始化失败: {response}")
            return False

    def test_sms_login(self):
        """测试短信登录"""
        print("\n📱 测试短信登录")

        # 发送短信验证码
        send_sms_data = {
            "phone_number": self.phone_number,
            "device_id": self.device_id
        }

        sms_response = self.test_api("POST", "/auth/sms/send", send_sms_data, expected_status=200)

        if sms_response.get("code") != 200:
            print(f"   ⚠️ 短信发送失败，但继续测试: {sms_response}")

        # 使用默认验证码登录（测试环境）
        login_data = {
            "phone_number": self.phone_number,
            "verification_code": "123456",  # 测试环境默认验证码
            "device_id": self.device_id
        }

        login_response = self.test_api("POST", "/auth/login", login_data, expected_status=200)

        if login_response.get("code") == 200 and login_response.get("data", {}).get("access_token"):
            self.auth_token = login_response["data"]["access_token"]
            self.user_id = login_response["data"].get("user_id")
            print(f"   ✅ 登录成功，获得token: {self.auth_token[:20]}...")
            print(f"   ✅ 用户ID: {self.user_id}")
            return True
        else:
            print(f"   ❌ 登录失败: {login_response}")
            return False

    def test_task_crud(self):
        """测试任务CRUD操作"""
        print("\n📝 测试任务管理")

        headers = self.get_auth_headers()

        # 创建任务
        task_data = {
            "title": "测试任务-用户流程验证",
            "description": "这是一个用于验证完整用户流程的测试任务",
            "status": "pending",
            "priority": "medium",
            "tags": ["测试", "流程验证", "用户操作"]
        }

        create_response = self.test_api("POST", "/tasks", task_data, expected_status=201, headers=headers)

        task_id = None
        if create_response.get("code") == 201 and create_response.get("data", {}).get("id"):
            task_id = create_response["data"]["id"]
            print(f"   ✅ 任务创建成功，ID: {task_id}")
        else:
            print(f"   ❌ 任务创建失败: {create_response}")
            return False

        # 获取任务列表
        self.test_api("GET", "/tasks?page=1&page_size=10", expected_status=200, headers=headers)

        # 获取任务详情
        if task_id:
            self.test_api("GET", f"/tasks/{task_id}", expected_status=200, headers=headers)

            # 更新任务
            update_data = {
                "title": "测试任务-已更新",
                "status": "in_progress",
                "completion_percentage": 50
            }
            self.test_api("PUT", f"/tasks/{task_id}", update_data, expected_status=200, headers=headers)

            # 完成任务
            complete_response = self.test_api("POST", f"/tasks/{task_id}/complete", expected_status=200, headers=headers)

            if complete_response.get("code") == 200:
                print(f"   ✅ 任务完成，获得奖励: {complete_response.get('data', {})}")

            # 取消完成
            self.test_api("POST", f"/tasks/{task_id}/uncomplete", expected_status=200, headers=headers)

            # 删除任务
            self.test_api("DELETE", f"/tasks/{task_id}", expected_status=200, headers=headers)

        return True

    def test_top3_operations(self):
        """测试Top3操作"""
        print("\n🏆 测试Top3操作")

        headers = self.get_auth_headers()

        # 首先获取一些任务ID用于Top3设置
        tasks_response = self.test_api("GET", "/tasks?page=1&page_size=5", headers=headers)

        task_ids = []
        if tasks_response.get("code") == 200 and tasks_response.get("data", {}).get("items"):
            tasks = tasks_response["data"]["items"]
            task_ids = [task["id"] for task in tasks[:2]]  # 取前两个任务

        # 如果没有任务，创建一些测试任务
        if not task_ids:
            print("   📝 没有找到任务，创建测试任务...")
            for i in range(2):
                task_data = {
                    "title": f"Top3测试任务-{i+1}",
                    "description": f"用于Top3设置的测试任务{i+1}",
                    "status": "pending"
                }
                create_response = self.test_api("POST", "/tasks", task_data, expected_status=201, headers=headers)
                if create_response.get("code") == 201:
                    task_id = create_response["data"]["id"]
                    task_ids.append(task_id)

        if len(task_ids) >= 2:
            # 设置Top3
            top3_data = {
                "date": "2025-10-23",
                "task_ids": task_ids[:2]  # 使用前两个任务
            }

            top3_response = self.test_api("POST", "/tasks/top3", top3_data, expected_status=200, headers=headers)

            if top3_response.get("code") == 200:
                print(f"   ✅ Top3设置成功: {top3_response.get('data', {})}")

            # 获取Top3
            self.test_api("GET", "/tasks/top3/2025-10-23", expected_status=200, headers=headers)
        else:
            print("   ⚠️ 没有足够的任务进行Top3测试")

        return True

    def test_reward_operations(self):
        """测试奖励系统操作"""
        print("\n🎁 测试奖励系统")

        headers = self.get_auth_headers()

        # 获取奖品目录
        self.test_api("GET", "/rewards/catalog", expected_status=200, headers=headers)

        # 获取我的奖品
        self.test_api("GET", f"/rewards/my-rewards?user_id={self.user_id}", expected_status=200, headers=headers)

        # 获取积分余额
        points_response = self.test_api("GET", f"/points/my-points?user_id={self.user_id}", expected_status=200, headers=headers)

        if points_response.get("code") == 200:
            balance = points_response["data"]["current_balance"]
            print(f"   💰 当前积分余额: {balance}")

        # 获取积分流水
        self.test_api("GET", f"/points/transactions?user_id={self.user_id}&page=1&page_size=20", expected_status=200, headers=headers)

        return True

    def run_complete_flow(self):
        """运行完整的用户操作流程"""
        print("🚀 开始完整用户操作流程测试")
        print("=" * 60)

        # 1. 系统健康检查
        print("\n📋 1. 系统健康检查")
        self.test_api("GET", "/health")
        self.test_api("GET", "/")
        self.test_api("GET", "/info")

        # 2. 认证流程
        print("\n📋 2. 认证流程")

        # 游客初始化
        if not self.test_guest_init():
            print("❌ 游客初始化失败，跳过后续测试")
            return self.print_summary()

        # 短信登录
        if not self.test_sms_login():
            print("❌ 短信登录失败，使用游客token继续测试")

        # 3. 任务管理流程
        print("\n📋 3. 任务管理流程")
        self.test_task_crud()

        # 4. Top3操作
        print("\n📋 4. Top3操作")
        self.test_top3_operations()

        # 5. 奖励系统
        print("\n📋 5. 奖励系统")
        self.test_reward_operations()

        # 输出测试结果
        return self.print_summary()

    def print_summary(self):
        """输出测试结果统计"""
        print("\n" + "=" * 60)
        print("📊 完整用户流程测试结果统计")

        passed = sum(1 for r in self.test_results if r["status"] == "✅ PASS")
        total = len(self.test_results)

        print(f"总计: {total} 个测试")
        print(f"通过: {passed} 个")
        print(f"失败: {total - passed} 个")
        print(f"成功率: {passed/total*100:.1f}%")

        # 显示失败的测试
        failed_tests = [r for r in self.test_results if r["status"] == "❌ FAIL"]
        if failed_tests:
            print("\n❌ 失败的测试:")
            for test in failed_tests:
                print(f"   - {test['test_name']}: {test['url']} (期望: {test['expected_status']}, 实际: {test['actual_status']})")

        print(f"\n🎯 用户信息:")
        print(f"   - 设备ID: {self.device_id}")
        print(f"   - 手机号: {self.phone_number}")
        print(f"   - 用户ID: {self.user_id}")
        print(f"   - 认证Token: {self.auth_token[:20] if self.auth_token else 'None'}...")

        print("\n🎉 完整用户流程测试完成!")
        return passed, total, failed_tests

if __name__ == "__main__":
    tester = UserFlowTester()
    passed, total, failed_tests = tester.run_complete_flow()

    if len(failed_tests) > 0:
        exit(1)
    else:
        exit(0)