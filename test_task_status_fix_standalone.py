#!/usr/bin/env python3
"""
任务状态修复独立测试

验证修复后的任务状态更新逻辑：
1. 防刷场景下任务状态应该正确更新为completed
2. 取消完成后再次完成，状态应该变为completed（而不是卡在pending）
"""

import requests
import uuid
import sqlite3
import os
from datetime import datetime, timezone

BASE_URL = "http://localhost:8001"
DATABASE_PATH = "tatake.db"


class TaskStatusFixTest:
    """任务状态修复测试类"""

    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.auth_data = None

    def register_user(self, openid_prefix: str = "status_fix_test"):
        """注册测试用户"""
        register_data = {
            "wechat_openid": f"{openid_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        }

        response = self.session.post(f"{self.base_url}/auth/register", json=register_data)
        if response.status_code != 200:
            raise Exception(f"用户注册失败: {response.status_code} - {response.text}")

        self.auth_data = response.json()["data"]
        token = self.auth_data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})

        return self.auth_data

    def create_task(self, task_data):
        """创建任务"""
        response = self.session.post(f"{self.base_url}/tasks/", json=task_data)
        if response.status_code not in [200, 201]:
            raise Exception(f"创建任务失败: {response.status_code} - {response.text}")

        return response.json()["data"]

    def complete_task(self, task_id):
        """完成任务"""
        response = self.session.post(f"{self.base_url}/tasks/{task_id}/complete", json={})
        if response.status_code != 200:
            raise Exception(f"完成任务失败: {response.status_code} - {response.text}")

        return response.json()["data"]

    def uncomplete_task(self, task_id):
        """取消完成任务"""
        response = self.session.post(f"{self.base_url}/tasks/{task_id}/uncomplete", json={})
        if response.status_code != 200:
            raise Exception(f"取消完成失败: {response.status_code} - {response.text}")

        return response.json()["data"]

    def query_task_from_database(self, task_id, user_id):
        """直接从数据库查询任务"""
        try:
            if not os.path.exists(DATABASE_PATH):
                return None

            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, title, status, description, updated_at, last_claimed_date FROM tasks WHERE id = ? AND user_id = ?",
                (str(task_id), str(user_id))
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            print(f"数据库查询失败: {e}")
            return None

    def test_task_status_updates_after_anti_spam(self):
        """
        测试防刷场景下任务状态更新

        验证任务完成过一次后，取消完成再次完成时，
        虽然不给积分，但任务状态应该正确更新为completed。
        """
        print("\n🔍 测试防刷场景下任务状态更新...")
        print("=" * 60)

        try:
            # 1. 注册用户
            print("1. 注册测试用户...")
            auth_data = self.register_user()
            user_id = auth_data["user_id"]
            print(f"✅ 用户注册成功: {user_id}")

            # 2. 创建测试任务
            print("\n2. 创建测试任务...")
            task_data = {
                "title": "状态修复测试任务",
                "description": "测试任务状态更新修复",
                "status": "pending"
            }

            created_task = self.create_task(task_data)
            task_id = created_task["id"]
            print(f"✅ 任务创建成功: {task_id}, 初始状态: {created_task['status']}")

            # 3. 第一次完成任务
            print("\n3. 第一次完成任务...")
            complete_result = self.complete_task(task_id)
            first_points = complete_result['completion_result']['points_awarded']
            first_status = complete_result['task']['status']

            print(f"✅ 第一次完成: 积分={first_points}, 状态={first_status}")

            if first_points <= 0 or first_status != "completed":
                print(f"❌ 第一次完成结果异常")
                return False

            # 4. 取消完成任务
            print("\n4. 取消完成任务...")
            uncomplete_result = self.uncomplete_task(task_id)
            uncomplete_status = uncomplete_result['task']['status']

            print(f"✅ 取消完成: 状态={uncomplete_status}")

            if uncomplete_status != "pending":
                print(f"❌ 取消完成后状态应该为pending，实际为: {uncomplete_status}")
                return False

            # 5. 再次完成任务（关键测试）
            print("\n5. 再次完成任务（关键测试）...")
            print("这是原始bug的测试点：任务状态会卡在pending")
            second_complete_result = self.complete_task(task_id)
            second_points = second_complete_result['completion_result']['points_awarded']
            second_status = second_complete_result['task']['status']
            reward_type = second_complete_result['completion_result']['reward_type']

            print(f"✅ 再次完成结果:")
            print(f"   - 积分奖励: {second_points}")
            print(f"   - 任务状态: {second_status}")
            print(f"   - 奖励类型: {reward_type}")

            # 6. 验证修复结果
            print("\n6. 验证修复结果...")

            # 防刷应该生效（不给积分）
            if second_points != 0:
                print(f"❌ 防刷失效，再次完成不应该获得积分，实际获得: {second_points}")
                return False

            if reward_type != "task_already_completed_once":
                print(f"❌ 奖励类型错误，期望: task_already_completed_once, 实际: {reward_type}")
                return False

            # 状态应该正确更新为completed
            if second_status != "completed":
                print(f"❌ 任务状态修复失败！期望: completed, 实际: {second_status}")
                print("   这是原始bug：任务状态卡在pending无法更新")
                return False

            print("✅ 任务状态修复成功！")
            print("   - 防刷机制正确生效（不给积分）")
            print("   - 任务状态正确更新为completed")
            print("   - 不再卡在pending状态")

            # 7. 验证数据库状态一致性
            print("\n7. 验证数据库状态一致性...")
            db_task = self.query_task_from_database(task_id, user_id)
            if db_task and db_task["status"] == "completed":
                print("✅ 数据库状态一致性验证通过")
                print(f"   数据库状态: {db_task['status']}")
                return True
            else:
                print(f"❌ 数据库状态不一致: {db_task}")
                return False

        except Exception as e:
            print(f"❌ 测试异常: {e}")
            return False

    def test_multiple_completion_cycle(self):
        """
        测试多次完成循环

        验证任务经历多次完成/取消完成循环后，
        最终状态仍能正确更新。
        """
        print("\n🔍 测试多次完成循环...")
        print("=" * 60)

        try:
            # 1. 注册新用户
            print("1. 注册新用户...")
            auth_data = self.register_user("cycle_test")
            user_id = auth_data["user_id"]

            # 2. 创建任务
            print("\n2. 创建任务...")
            task_data = {
                "title": "循环测试任务",
                "description": "测试多次循环",
                "status": "pending"
            }

            created_task = self.create_task(task_data)
            task_id = created_task["id"]
            print(f"✅ 任务创建成功: {task_id}")

            # 3. 第一次完成
            print("\n3. 第一次完成...")
            first_complete = self.complete_task(task_id)
            print(f"✅ 第1次完成: 积分={first_complete['completion_result']['points_awarded']}")

            # 4. 循环：取消完成 -> 再次完成
            for i in range(3):
                print(f"\n4.{i+1} 执行第{i+2}次循环...")

                # 取消完成
                uncomplete_result = self.uncomplete_task(task_id)
                if uncomplete_result['task']['status'] != "pending":
                    print(f"❌ 第{i+1}次取消完成状态错误")
                    return False
                print(f"   取消完成: 状态={uncomplete_result['task']['status']}")

                # 再次完成
                complete_result = self.complete_task(task_id)
                status = complete_result['task']['status']
                points = complete_result['completion_result']['points_awarded']

                if status != "completed":
                    print(f"❌ 第{i+2}次完成状态错误: {status}")
                    return False

                if points != 0:
                    print(f"❌ 第{i+2}次完成不应该获得积分: {points}")
                    return False

                print(f"   再次完成: 状态={status}, 积分={points}")

            print("\n✅ 多次完成循环测试通过")
            return True

        except Exception as e:
            print(f"❌ 循环测试异常: {e}")
            return False


def main():
    """主测试函数"""
    print("🚀 任务状态修复测试开始...")
    print("验证修复后的任务状态更新逻辑")

    tester = TaskStatusFixTest()

    test_results = []

    # 测试1：防刷场景下状态更新
    print("\n" + "=" * 80)
    print("测试1: 防刷场景下任务状态更新")
    print("=" * 80)
    result1 = tester.test_task_status_updates_after_anti_spam()
    test_results.append(("防刷场景状态更新", result1))

    # 测试2：多次完成循环
    print("\n" + "=" * 80)
    print("测试2: 多次完成循环测试")
    print("=" * 80)
    result2 = tester.test_multiple_completion_cycle()
    test_results.append(("多次完成循环", result2))

    # 总结
    print("\n" + "=" * 80)
    print("📊 测试结果总结")
    print("=" * 80)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 任务状态修复验证成功！")
        print("✅ 修复内容总结:")
        print("1. 防刷场景下任务状态正确更新为completed")
        print("2. 不再卡在pending状态")
        print("3. 积分防刷机制正常工作")
        print("4. 多次循环测试通过")
        return True
    else:
        print("❌ 部分测试失败，修复不完整")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)