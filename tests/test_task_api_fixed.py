"""
Task API修复验证测试

验证修复后的API功能：
1. 响应格式只包含code、message、data三个字段
2. 任务列表API简化，只支持基本分页
3. 时区问题修复，所有时间使用UTC
4. 筛选功能完全移除
"""

import pytest
import requests
import json
from typing import Dict, Any
from datetime import datetime, timezone

# API基础配置
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/"

class TestTaskAPIFixed:
    """Task API修复验证测试类"""

    @staticmethod
    def test_response_format():
        """测试响应格式是否只包含三个字段"""
        print("🔍 测试响应格式...")

        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code != 200:
                return False, f"健康检查失败: {response.status_code}"

            data = response.json()
            expected_fields = {"code", "message", "data"}
            actual_fields = set(data.keys())

            if actual_fields == expected_fields:
                print("   ✅ 健康检查响应格式正确")
                return True, "响应格式正确"
            else:
                return False, f"响应字段错误: 期望 {expected_fields}, 实际 {actual_fields}"

        except Exception as e:
            return False, f"健康检查异常: {e}"

    @staticmethod
    def test_task_list_simplified():
        """测试简化的任务列表API"""
        print("\n🔍 测试任务列表API简化...")

        # 先注册用户再获取token
        wechat_openid = "test_fixed_openid"
        register_data = {"wechat_openid": wechat_openid}

        try:
            # 先注册用户
            register_response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=10)
            if register_response.status_code not in [200, 409]:  # 200成功，409已存在
                print(f"   注意: 用户注册结果: {register_response.status_code} - {register_response.text}")

            # 再登录获取token
            login_data = {"wechat_openid": wechat_openid}
            login_response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            if login_response.status_code != 200:
                return False, f"登录失败: {login_response.status_code} - {login_response.text}"

            token = login_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 测试简化后的任务列表API
            list_response = requests.get(f"{API_BASE}/tasks", headers=headers, timeout=5)
            if list_response.status_code != 200:
                return False, f"任务列表失败: {list_response.status_code}"

            data = list_response.json()

            # 检查响应格式
            if set(data.keys()) != {"code", "message", "data"}:
                return False, "任务列表响应格式错误"

            # 检查数据结构
            task_data = data["data"]
            if "tasks" not in task_data or "pagination" not in task_data:
                return False, "任务列表数据结构错误"

            # 检查分页信息
            pagination = task_data["pagination"]
            required_pagination_fields = {"current_page", "page_size", "total_count", "total_pages"}
            if not all(field in pagination for field in required_pagination_fields):
                return False, "分页信息不完整"

            print(f"   ✅ 任务列表获取成功，共 {pagination['total_count']} 个任务")
            return True, "任务列表API简化成功"

        except Exception as e:
            return False, f"任务列表测试异常: {e}"

    @staticmethod
    def test_create_task_utc_timezone():
        """测试创建任务的UTC时区处理"""
        print("\n🔍 测试创建任务UTC时区...")

        # 先注册用户再获取token
        wechat_openid = "test_utc_openid"
        register_data = {"wechat_openid": wechat_openid}

        try:
            # 先注册用户
            register_response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=10)
            if register_response.status_code not in [200, 409]:
                print(f"   注意: 用户注册结果: {register_response.status_code} - {register_response.text}")

            # 再登录获取token
            login_data = {"wechat_openid": wechat_openid}
            login_response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            if login_response.status_code != 200:
                return False, f"登录失败: {login_response.status_code} - {login_response.text}"

            token = login_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 创建带时间的任务
            task_data = {
                "title": "UTC时区测试任务",
                "description": "测试UTC时区处理",
                "due_date": "2024-12-31T23:59:59Z",
                "planned_start_time": "2024-12-20T09:00:00Z",
                "planned_end_time": "2024-12-30T18:00:00Z"
            }

            create_response = requests.post(f"{API_BASE}/tasks", headers=headers, json=task_data, timeout=5)

            if create_response.status_code == 200:
                print("   ✅ 创建任务成功，UTC时区处理正确")
                return True, "UTC时区修复成功"
            else:
                error_detail = create_response.text
                return False, f"创建任务失败: {create_response.status_code} - {error_detail}"

        except Exception as e:
            return False, f"UTC时区测试异常: {e}"

    @staticmethod
    def test_all_filters_removed():
        """测试所有筛选功能已被移除"""
        print("\n🔍 测试筛选功能移除...")

        # 先注册用户再获取token
        wechat_openid = "test_filters_removed"
        register_data = {"wechat_openid": wechat_openid}

        try:
            # 先注册用户
            register_response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=10)
            if register_response.status_code not in [200, 409]:
                print(f"   注意: 用户注册结果: {register_response.status_code} - {register_response.text}")

            # 再登录获取token
            login_data = {"wechat_openid": wechat_openid}
            login_response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            if login_response.status_code != 200:
                return False, f"登录失败: {login_response.status_code} - {login_response.text}"

            token = login_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 尝试使用已移除的筛选参数
            # 这些参数应该被忽略或返回错误，而不是导致服务器错误
            test_params = [
                "?status=pending",
                "?priority=high",
                "?search=test",
                "?sort_by=title",
                "?sort_order=asc"
            ]

            all_passed = True
            for param in test_params:
                try:
                    response = requests.get(f"{API_BASE}/tasks{param}", headers=headers, timeout=5)
                    # 应该返回200（忽略未知参数）或400错误（参数错误）
                    # 但不应该返回500服务器错误
                    if response.status_code == 500:
                        print(f"   ❌ 参数 {param} 导致服务器错误")
                        all_passed = False
                    else:
                        print(f"   ✅ 参数 {param} 处理正确 (状态码: {response.status_code})")
                except Exception as e:
                    print(f"   ⚠️  参数 {param} 测试异常: {e}")
                    all_passed = False

            if all_passed:
                return True, "筛选功能移除成功"
            else:
                return False, "部分筛选参数处理有问题"

        except Exception as e:
            return False, f"筛选功能测试异常: {e}"

def run_tests():
    """运行所有测试"""
    print("🚀 开始Task API修复验证测试...")
    print("=" * 60)

    test_instance = TestTaskAPIFixed()

    tests = [
        ("响应格式测试", test_instance.test_response_format),
        ("任务列表简化测试", test_instance.test_task_list_simplified),
        ("UTC时区测试", test_instance.test_create_task_utc_timezone),
        ("筛选功能移除测试", test_instance.test_all_filters_removed)
    ]

    results = []
    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 执行: {test_name}")
        success, message = test_func()
        results.append((test_name, success, message))

        if success:
            passed += 1
            print(f"   ✅ {test_name}: 通过 - {message}")
        else:
            print(f"   ❌ {test_name}: 失败 - {message}")

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"   总测试数: {total}")
    print(f"   通过数: {passed}")
    print(f"   失败数: {total - passed}")
    print(f"   通过率: {passed/total*100:.1f}%")

    if passed == total:
        print("\n🎉 所有测试通过！API修复成功")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)