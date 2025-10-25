"""
P0级Bug修复验证测试

专门测试1.4.1 OpenSpec中修复的2个P0级Bug：
1. 任务完成API请求体问题 - 支持空请求体
2. Top3 UUID类型混用问题 - 修复AttributeError

使用requests进行真实HTTP请求测试，避免async问题。

作者：TaKeKe团队
版本：1.4.1
日期：2025-10-25
"""

import requests
import json
import uuid
from typing import Dict, Any, Tuple

# API基础配置
BASE_URL = "http://localhost:8003"
API_BASE = f"{BASE_URL}/"

class TestP0BugFixes:
    """P0级Bug修复验证测试类"""

    def test_health_check(self) -> Tuple[bool, str]:
        """测试服务器健康状态"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                return True, "服务器运行正常"
            else:
                return False, f"健康检查失败: {response.status_code}"
        except Exception as e:
            return False, f"连接失败: {e}"

    def get_auth_headers(self) -> Tuple[Dict[str, str], str]:
        """获取认证头"""
        wechat_openid = f"test_p0_user_{uuid.uuid4().hex[:8]}"

        # 使用游客初始化接口
        guest_response = requests.post(f"{API_BASE}/auth/guest/init", timeout=10)

        if guest_response.status_code != 200:
            raise Exception(f"游客初始化失败: {guest_response.status_code} - {guest_response.text}")

        token = guest_response.json()["data"]["access_token"]
        user_id = guest_response.json()["data"]["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 领取欢迎礼包获得积分
        gift_response = requests.post(f"{API_BASE}/user/welcome-gift/claim", headers=headers, timeout=10)

        return headers, user_id

    def test_task_completion_empty_body(self) -> Tuple[bool, str]:
        """测试Bug #1: 任务完成API空请求体"""
        print("\n🔍 测试Bug #1: 任务完成API空请求体...")

        try:
            headers, _ = self.get_auth_headers()

            # 创建测试任务
            task_data = {
                "title": "P0 Bug修复测试任务 - 空请求体",
                "description": "用于验证任务完成API支持空请求体"
            }
            create_response = requests.post(f"{API_BASE}/tasks", headers=headers, json=task_data, timeout=10)

            if create_response.status_code != 200:
                return False, f"创建任务失败: {create_response.status_code}"

            task_id = create_response.json()["data"]["id"]
            print(f"   ✅ 创建任务成功: {task_id}")

            # 完成任务，不传递请求体（这是Bug修复的核心）
            complete_response = requests.post(
                f"{API_BASE}/tasks/{task_id}/complete",
                headers=headers,
                timeout=10
                # 注意：没有json参数，测试空请求体
            )

            if complete_response.status_code == 200:
                result = complete_response.json()
                if result["code"] == 200 and result["data"]["task"]["status"] == "completed":
                    print("   ✅ 空请求体完成任务成功")
                    return True, "Bug #1修复成功"
                else:
                    return False, f"任务状态不正确: {result}"
            else:
                return False, f"空请求体完成失败: {complete_response.status_code} - {complete_response.text}"

        except Exception as e:
            return False, f"测试异常: {e}"

    def test_task_completion_with_feedback(self) -> Tuple[bool, str]:
        """测试任务完成API带mood_feedback"""
        print("\n🔍 测试任务完成API带mood_feedback...")

        try:
            headers, _ = self.get_auth_headers()

            # 创建测试任务
            task_data = {
                "title": "P0 Bug修复测试任务 - 带反馈",
                "description": "用于验证mood_feedback处理"
            }
            create_response = requests.post(f"{API_BASE}/tasks", headers=headers, json=task_data, timeout=10)

            if create_response.status_code != 200:
                return False, f"创建任务失败: {create_response.status_code}"

            task_id = create_response.json()["data"]["id"]

            # 完成任务，带mood_feedback
            complete_data = {
                "mood_feedback": {
                    "comment": "这个任务很有挑战性，但顺利完成了",
                    "difficulty": "medium"
                }
            }
            complete_response = requests.post(
                f"{API_BASE}/tasks/{task_id}/complete",
                headers=headers,
                json=complete_data,
                timeout=10
            )

            if complete_response.status_code == 200:
                result = complete_response.json()
                if result["code"] == 200 and result["data"]["task"]["status"] == "completed":
                    print("   ✅ 带反馈完成任务成功")
                    return True, "mood_feedback处理正常"
                else:
                    return False, f"任务状态不正确: {result}"
            else:
                return False, f"带反馈完成失败: {complete_response.status_code}"

        except Exception as e:
            return False, f"测试异常: {e}"

    def test_top3_uuid_fix(self) -> Tuple[bool, str]:
        """测试Bug #2: Top3 UUID类型混用修复"""
        print("\n🔍 测试Bug #2: Top3 UUID类型混用修复...")

        try:
            headers, _ = self.get_auth_headers()  # 已包含欢迎礼包领取

            # 创建3个测试任务
            task_ids = []
            for i in range(3):
                task_data = {
                    "title": f"Top3 UUID测试任务 {i+1}",
                    "description": f"验证UUID类型修复 {i+1}"
                }
                create_response = requests.post(f"{API_BASE}/tasks", headers=headers, json=task_data, timeout=10)

                if create_response.status_code != 200:
                    return False, f"创建任务{i+1}失败: {create_response.status_code}"

                task_id = create_response.json()["data"]["id"]
                task_ids.append(task_id)
                print(f"   ✅ 创建任务{i+1}: {task_id}")

            # 设置Top3（这是Bug #2修复的核心 - 不应该出现UUID AttributeError）
            top3_data = {
                "date": "2025-10-26",
                "task_ids": task_ids
            }
            top3_response = requests.post(
                f"{API_BASE}/tasks/special/top3",
                headers=headers,
                json=top3_data,
                timeout=10
            )

            if top3_response.status_code == 200:
                result = top3_response.json()
                if result["code"] == 200:
                    print("   ✅ Top3设置成功，UUID类型修复生效")
                    print(f"   ✅ 消耗积分: {result['data']['points_consumed']}")
                    print(f"   ✅ 剩余余额: {result['data']['remaining_balance']}")
                    return True, "Bug #2修复成功"
                else:
                    return False, f"Top3设置返回错误: {result}"
            else:
                error_detail = top3_response.text
                if "AttributeError" in error_detail and "replace" in error_detail:
                    return False, f"UUID错误未修复: {error_detail}"
                else:
                    return False, f"Top3设置失败: {top3_response.status_code} - {error_detail}"

        except Exception as e:
            return False, f"测试异常: {e}"

    def test_top3_query(self) -> Tuple[bool, str]:
        """测试Top3查询功能"""
        print("\n🔍 测试Top3查询功能...")

        try:
            headers, _ = self.get_auth_headers()

            # 查询今日Top3 - 修复：使用路径参数而不是查询参数
            today = "2025-10-25"
            query_response = requests.get(
                f"{API_BASE}/tasks/special/top3/{today}",
                headers=headers,
                timeout=10
            )

            if query_response.status_code == 200:
                result = query_response.json()
                if result["code"] == 200:
                    print("   ✅ Top3查询成功")
                    return True, "Top3查询正常"
                else:
                    return False, f"查询返回错误: {result}"
            else:
                return False, f"查询失败: {query_response.status_code} - {query_response.text}"

        except Exception as e:
            return False, f"测试异常: {e}"


def run_p0_tests():
    """运行所有P0级Bug修复测试"""
    print("🚀 开始P0级Bug修复验证测试...")
    print("=" * 70)

    test_instance = TestP0BugFixes()

    # 首先检查服务器健康状态
    health_ok, health_msg = test_instance.test_health_check()
    if not health_ok:
        print(f"❌ 服务器健康检查失败: {health_msg}")
        return False
    print(f"✅ 服务器健康检查: {health_msg}")

    # P0级Bug修复测试列表
    p0_tests = [
        ("Bug #1修复: 任务完成API空请求体", test_instance.test_task_completion_empty_body),
        ("Bug #1扩展: 任务完成API带反馈", test_instance.test_task_completion_with_feedback),
        ("Bug #2修复: Top3 UUID类型混用", test_instance.test_top3_uuid_fix),
        ("Top3功能验证: 查询接口", test_instance.test_top3_query)
    ]

    results = []
    passed = 0
    total = len(p0_tests)

    for test_name, test_func in p0_tests:
        print(f"\n📋 执行: {test_name}")
        success, message = test_func()
        results.append((test_name, success, message))

        if success:
            passed += 1
            print(f"   ✅ {test_name}: 通过 - {message}")
        else:
            print(f"   ❌ {test_name}: 失败 - {message}")

    # 总结
    print("\n" + "=" * 70)
    print("📊 P0级Bug修复测试结果:")
    print(f"   总测试数: {total}")
    print(f"   通过数: {passed}")
    print(f"   失败数: {total - passed}")
    print(f"   通过率: {passed/total*100:.1f}%")

    if passed == total:
        print("\n🎉 所有P0级Bug修复测试通过！")
        print("✅ 任务完成API支持空请求体 - Bug #1修复成功")
        print("✅ Top3 UUID类型混用问题已解决 - Bug #2修复成功")
        print("✅ 1.4.1 OpenSpec P0级修复验证完成")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个P0测试失败，Bug修复不完整")
        for test_name, success, message in results:
            if not success:
                print(f"   ❌ {test_name}: {message}")
        return False


if __name__ == "__main__":
    success = run_p0_tests()
    exit(0 if success else 1)