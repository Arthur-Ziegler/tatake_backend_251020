#!/usr/bin/env python3
"""
任务完成奖励系统端到端测试

专门测试任务完成奖励系统：
1. 普通任务完成获得2积分
2. Top3任务设置和完成
3. 防刷机制验证
4. 父任务完成度更新
5. 完整奖励流程

作者：TaKeKe团队
版本：v3 API实施测试
"""

import json
import requests
import uuid
from datetime import date
from typing import Dict, List, Optional

# 测试配置
BASE_URL = "http://localhost:8001"


class TaskCompletionE2ETester:
    """任务完成奖励系统端到端测试器"""

    def __init__(self):
        self.base_url = BASE_URL
        self.user_token = None
        self.user_id = None
        self.task_ids = []
        self.test_results = []

    def log_result(self, test_name: str, success: bool, data: Optional[Dict] = None, error: Optional[str] = None):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "timestamp": date.today().isoformat()
        }
        if data:
            result["data"] = data
        if error:
            result["error"] = error

        self.test_results.append(result)
        print(f"{status} {test_name}")
        if data:
            print(f"   数据: {json.dumps(data, ensure_ascii=False)}")
        if error:
            print(f"   错误: {error}")

    def create_test_user(self, identifier: str) -> bool:
        """创建测试用户"""
        try:
            openid = f"e2e_openid_{identifier}_{uuid.uuid4().hex[:8]}"

            # 注册用户
            register_response = requests.post(f"{self.base_url}/auth/register", json={
                "wechat_openid": openid
            })

            if register_response.status_code != 200:
                self.log_result("用户注册", False, error=f"HTTP {register_response.status_code}")
                return False

            register_data = register_response.json()
            if register_data.get("code") != 200:
                self.log_result("用户注册", False, error=register_data.get("message"))
                return False

            self.user_token = register_data["data"]["access_token"]
            self.user_id = register_data["data"]["user_id"]

            self.log_result("创建测试用户", True, {"user_id": self.user_id, "identifier": identifier})
            return True

        except Exception as e:
            self.log_result("创建测试用户", False, error=str(e))
            return False

    def get_headers(self) -> Dict[str, str]:
        """获取认证头"""
        return {"Authorization": f"Bearer {self.user_token}"}

    def test_normal_task_completion(self) -> bool:
        """测试普通任务完成获得2积分"""
        print("\n" + "="*80)
        print("测试：普通任务完成获得2积分")
        print("="*80)

        try:
            # 1. 创建普通任务
            task_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "E2E普通任务",
                "description": "用于测试普通任务完成获得2积分",
                "priority": "medium"
            }, headers=self.get_headers())

            if task_response.status_code not in [200, 201]:
                self.log_result("创建普通任务", False, error=f"HTTP {task_response.status_code}")
                return False

            task_data = task_response.json()
            if task_data.get("code") not in [200, 201]:
                self.log_result("创建普通任务", False, error=task_data.get("message"))
                return False

            task_id = task_data["data"]["id"]
            self.log_result("创建普通任务", True, {"task_id": task_id})

            # 2. 获取初始积分
            balance_response = requests.get(f"{self.base_url}/points/my-points?user_id={self.user_id}", headers=self.get_headers())
            if balance_response.status_code != 200 or balance_response.json().get("code") != 200:
                self.log_result("获取初始积分", False)
                return False

            initial_balance = balance_response.json()["data"]["current_balance"]
            self.log_result("获取初始积分", True, {"balance": initial_balance})

            # 3. 完成任务
            complete_response = requests.post(f"{self.base_url}/tasks/{task_id}/complete", json={}, headers=self.get_headers())

            if complete_response.status_code != 200:
                self.log_result("完成普通任务", False, error=f"HTTP {complete_response.status_code}")
                return False

            complete_data = complete_response.json()
            if complete_data.get("code") != 200:
                self.log_result("完成普通任务", False, error=complete_data.get("message"))
                return False

            points_awarded = complete_data["data"]["completion_result"]["points_awarded"]
            self.log_result("完成普通任务", True, {"points_awarded": points_awarded})

            # 4. 验证积分增加
            final_balance_response = requests.get(f"{self.base_url}/points/my-points?user_id={self.user_id}", headers=self.get_headers())
            if final_balance_response.status_code == 200 and final_balance_response.json().get("code") == 200:
                final_balance = final_balance_response.json()["data"]["current_balance"]
                self.log_result("验证积分增加", True, {
                    "initial": initial_balance,
                    "final": final_balance,
                    "earned": final_balance - initial_balance,
                    "expected": 2
                })

                if final_balance - initial_balance == 2:
                    return True
                else:
                    self.log_result("验证积分增加", False, error=f"期望增加2积分，实际增加{final_balance - initial_balance}")
                    return False
            else:
                self.log_result("验证积分增加", False)
                return False

        except Exception as e:
            self.log_result("普通任务完成测试", False, error=str(e))
            return False

    def test_top3_task_completion(self) -> bool:
        """测试Top3任务完成抽奖"""
        print("\n" + "="*80)
        print("测试：Top3任务完成抽奖")
        print("="*80)

        try:
            # 1. 创建Top3任务
            top3_task_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "E2E Top3任务",
                "description": "用于测试Top3任务完成抽奖机制",
                "priority": "high"
            }, headers=self.get_headers())

            if top3_task_response.status_code not in [200, 201]:
                self.log_result("创建Top3任务", False, error=f"HTTP {top3_task_response.status_code}")
                return False

            top3_task_data = top3_task_response.json()
            if top3_task_data.get("code") not in [200, 201]:
                self.log_result("创建Top3任务", False, error=top3_task_data.get("message"))
                return False

            top3_task_id = top3_task_data["data"]["id"]
            self.log_result("创建Top3任务", True, {"task_id": top3_task_id})

            # 2. 设置为Top3（直接操作数据库）
            today = date.today().isoformat()
            top3_setup_response = requests.post(f"{self.base_url}/tasks/top3", json={
                "task_ids": [top3_task_id],
                "date": today
            }, headers=self.get_headers())

            if top3_setup_response.status_code not in [200, 201]:
                self.log_result("设置Top3", False, error=f"HTTP {top3_setup_response.status_code}")
                return False

            self.log_result("设置Top3任务", True)

            # 3. 获取初始积分
            balance_response = requests.get(f"{self.base_url}/points/my-points?user_id={self.user_id}", headers=self.get_headers())
            if balance_response.status_code != 200 or balance_response.json().get("code") != 200:
                self.log_result("获取初始积分", False)
                return False

            initial_balance = balance_response.json()["data"]["current_balance"]
            self.log_result("获取初始积分", True, {"balance": initial_balance})

            # 4. 完成Top3任务
            complete_response = requests.post(f"{self.base_url}/tasks/{top3_task_id}/complete", json={}, headers=self.get_headers())

            if complete_response.status_code != 200:
                self.log_result("完成Top3任务", False, error=f"HTTP {complete_response.status_code}")
                return False

            complete_data = complete_response.json()
            if complete_data.get("code") != 200:
                self.log_result("完成Top3任务", False, error=complete_data.get("message"))
                return False

            points_awarded = complete_data["data"]["completion_result"]["points_awarded"]
            lottery_result = complete_data["data"].get("lottery_result")

            self.log_result("完成Top3任务", True, {
                "points_awarded": points_awarded,
                "lottery_result": lottery_result
            })

            # 5. 验证积分变化
            final_balance_response = requests.get(f"{self.base_url}/points/my-points?user_id={self.user_id}", headers=self.get_headers())
            if final_balance_response.status_code == 200 and final_balance_response.json().get("code") == 200:
                final_balance = final_balance_response.json()["data"]["current_balance"]
                self.log_result("验证Top3积分变化", True, {
                    "initial": initial_balance,
                    "final": final_balance,
                    "earned": final_balance - initial_balance,
                    "base_points": points_awarded,
                    "lottery_points": lottery_result.get("amount", 0) if lottery_result and lottery_result.get("type") == "points" else 0
                })

                return True
            else:
                self.log_result("验证Top3积分变化", False)
                return False

        except Exception as e:
            self.log_result("Top3任务完成测试", False, error=str(e))
            return False

    def test_anti_spam_mechanism(self) -> bool:
        """测试防刷机制"""
        print("\n" + "="*80)
        print("测试：防刷机制")
        print("="*80)

        try:
            # 1. 创建测试任务
            anti_spam_task_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "E2E防刷测试任务",
                "description": "用于测试防刷机制",
                "priority": "medium"
            }, headers=self.get_headers())

            if anti_spam_task_response.status_code not in [200, 201]:
                self.log_result("创建防刷测试任务", False, error=f"HTTP {anti_spam_task_response.status_code}")
                return False

            anti_spam_task_data = anti_spam_task_response.json()
            if anti_spam_task_data.get("code") not in [200, 201]:
                self.log_result("创建防刷测试任务", False, error=anti_spam_task_data.get("message"))
                return False

            anti_spam_task_id = anti_spam_task_data["data"]["id"]
            self.log_result("创建防刷测试任务", True, {"task_id": anti_spam_task_id})

            # 2. 第一次完成任务
            first_complete_response = requests.post(f"{self.base_url}/tasks/{anti_spam_task_id}/complete", json={}, headers=self.get_headers())

            if first_complete_response.status_code != 200:
                self.log_result("第一次完成任务", False, error=f"HTTP {first_complete_response.status_code}")
                return False

            first_complete_data = first_complete_response.json()
            if first_complete_data.get("code") != 200:
                self.log_result("第一次完成任务", False, error=first_complete_data.get("message"))
                return False

            first_points = first_complete_data["data"]["completion_result"]["points_awarded"]
            self.log_result("第一次完成任务", True, {"points_awarded": first_points})

            # 3. 第二次完成同一任务
            second_complete_response = requests.post(f"{self.base_url}/tasks/{anti_spam_task_id}/complete", json={}, headers=self.get_headers())

            if second_complete_response.status_code != 200:
                self.log_result("第二次完成任务", False, error=f"HTTP {second_complete_response.status_code}")
                return False

            second_complete_data = second_complete_response.json()
            if second_complete_data.get("code") != 200:
                self.log_result("第二次完成任务", False, error=second_complete_data.get("message"))
                return False

            second_points = second_complete_data["data"]["completion_result"]["points_awarded"]
            self.log_result("第二次完成任务", True, {"points_awarded": second_points})

            # 4. 验证防刷机制
            if first_points > 0 and second_points == 0:
                self.log_result("验证防刷机制", True, {
                    "first_points": first_points,
                    "second_points": second_points,
                    "anti_spam_works": True
                })
                return True
            else:
                self.log_result("验证防刷机制", False, error=f"防刷机制失效，第一次{first_points}，第二次{second_points}")
                return False

        except Exception as e:
            self.log_result("防刷机制测试", False, error=str(e))
            return False

    def test_parent_task_completion_update(self) -> bool:
        """测试父任务完成度更新"""
        print("\n" + "="*80)
        print("测试：父任务完成度自动更新")
        print("="*80)

        try:
            # 1. 创建父任务
            parent_task_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "E2E父任务",
                "description": "包含子任务的父任务",
                "priority": "high"
            }, headers=self.get_headers())

            if parent_task_response.status_code not in [200, 201]:
                self.log_result("创建父任务", False, error=f"HTTP {parent_task_response.status_code}")
                return False

            parent_task_data = parent_task_response.json()
            if parent_task_data.get("code") not in [200, 201]:
                self.log_result("创建父任务", False, error=parent_task_data.get("message"))
                return False

            parent_task_id = parent_task_data["data"]["id"]
            self.log_result("创建父任务", True, {"task_id": parent_task_id})

            # 2. 创建子任务1
            child1_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "E2E子任务1",
                "description": "父任务的第一个子任务",
                "priority": "medium",
                "parent_id": parent_task_id
            }, headers=self.get_headers())

            if child1_response.status_code not in [200, 201]:
                self.log_result("创建子任务1", False, error=f"HTTP {child1_response.status_code}")
                return False

            child1_data = child1_response.json()
            if child1_data.get("code") not in [200, 201]:
                self.log_result("创建子任务1", False, error=child1_data.get("message"))
                return False

            child1_id = child1_data["data"]["id"]
            self.log_result("创建子任务1", True, {"task_id": child1_id})

            # 3. 创建子任务2
            child2_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "E2E子任务2",
                "description": "父任务的第二个子任务",
                "priority": "medium",
                "parent_id": parent_task_id
            }, headers=self.get_headers())

            if child2_response.status_code not in [200, 201]:
                self.log_result("创建子任务2", False, error=f"HTTP {child2_response.status_code}")
                return False

            child2_data = child2_response.json()
            if child2_data.get("code") not in [200, 201]:
                self.log_result("创建子任务2", False, error=child2_data.get("message"))
                return False

            child2_id = child2_data["data"]["id"]
            self.log_result("创建子任务2", True, {"task_id": child2_id})

            # 4. 检查父任务初始完成度
            parent_check_response = requests.get(f"{self.base_url}/tasks/{parent_task_id}", headers=self.get_headers())
            if parent_check_response.status_code != 200 or parent_check_response.json().get("code") != 200:
                self.log_result("检查父任务初始状态", False)
                return False

            initial_completion = parent_check_response.json()["data"]["completion_percentage"]
            self.log_result("检查父任务初始完成度", True, {"completion_percentage": initial_completion})

            # 5. 完成第一个子任务
            complete_child1_response = requests.post(f"{self.base_url}/tasks/{child1_id}/complete", json={}, headers=self.get_headers())

            if complete_child1_response.status_code != 200:
                self.log_result("完成子任务1", False, error=f"HTTP {complete_child1_response.status_code}")
                return False

            # 6. 检查父任务完成度更新
            parent_after_child1_response = requests.get(f"{self.base_url}/tasks/{parent_task_id}", headers=self.get_headers())
            if parent_after_child1_response.status_code == 200 and parent_after_child1_response.json().get("code") == 200:
                completion_after_child1 = parent_after_child1_response.json()["data"]["completion_percentage"]
                self.log_result("检查父任务完成度(子任务1完成)", True, {"completion_percentage": completion_after_child1})
            else:
                self.log_result("检查父任务完成度(子任务1完成)", False)
                return False

            # 7. 完成第二个子任务
            complete_child2_response = requests.post(f"{self.base_url}/tasks/{child2_id}/complete", json={}, headers=self.get_headers())

            if complete_child2_response.status_code != 200:
                self.log_result("完成子任务2", False, error=f"HTTP {complete_child2_response.status_code}")
                return False

            # 8. 检查父任务最终完成度
            parent_final_response = requests.get(f"{self.base_url}/tasks/{parent_task_id}", headers=self.get_headers())
            if parent_final_response.status_code == 200 and parent_final_response.json().get("code") == 200:
                final_completion = parent_final_response.json()["data"]["completion_percentage"]
                self.log_result("检查父任务最终完成度", True, {"completion_percentage": final_completion})

                # 验证完成度递增逻辑
                if initial_completion == 0 and completion_after_child1 == 50.0 and final_completion == 100.0:
                    self.log_result("验证父任务完成度递增", True, {
                        "initial": initial_completion,
                        "after_child1": completion_after_child1,
                        "final": final_completion
                    })
                    return True
                else:
                    self.log_result("验证父任务完成度递增", False, error=f"完成度不符合预期")
                    return False
            else:
                self.log_result("检查父任务最终完成度", False)
                return False

        except Exception as e:
            self.log_result("父任务完成度更新测试", False, error=str(e))
            return False

    def run_all_tests(self) -> bool:
        """运行所有端到端测试"""
        print("开始任务完成奖励系统端到端测试...")
        print(f"测试目标: {self.base_url}")
        print(f"测试时间: {date.today().isoformat()}")

        # 创建测试用户
        if not self.create_test_user("task_completion_rewards"):
            print("❌ 无法创建测试用户，停止测试")
            return False

        # 运行所有测试
        tests = [
            ("普通任务完成获得2积分", self.test_normal_task_completion),
            ("Top3任务完成抽奖", self.test_top3_task_completion),
            ("防刷机制验证", self.test_anti_spam_mechanism),
            ("父任务完成度自动更新", self.test_parent_task_completion_update)
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✅ {test_name} - 通过")
                else:
                    print(f"❌ {test_name} - 失败")
            except Exception as e:
                print(f"❌ {test_name} - 异常: {e}")

        # 生成测试报告
        self.generate_test_report(passed_tests, total_tests)

        return passed_tests == total_tests

    def generate_test_report(self, passed: int, total: int):
        """生成测试报告"""
        print("\n" + "="*80)
        print("任务完成奖励系统端到端测试报告")
        print("="*80)
        print(f"测试时间: {date.today().isoformat()}")
        print(f"总测试数: {total}")
        print(f"通过测试数: {passed}")
        print(f"失败测试数: {total - passed}")
        print(f"通过率: {passed/total*100:.1f}%")

        print(f"\n详细结果:")
        for result in self.test_results:
            print(f"  {result['status']} {result['test']}")
            if not result['success'] and 'error' in result:
                print(f"    错误: {result['error']}")

        # 保存测试报告到文件
        report_data = {
            "test_time": date.today().isoformat(),
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": total - passed,
                "pass_rate": passed/total*100
            },
            "user_id": self.user_id,
            "results": self.test_results
        }

        try:
            with open("task_completion_e2e_report.json", "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"\n详细测试报告已保存到: task_completion_e2e_report.json")
        except Exception as e:
            print(f"保存测试报告失败: {e}")


def main():
    """主函数"""
    print("TaTakeKe任务完成奖励系统端到端测试")
    print("="*80)

    tester = TaskCompletionE2ETester()
    success = tester.run_all_tests()

    if success:
        print("\n🎉 所有端到端测试通过！")
        exit(0)
    else:
        print("\n❌ 部分端到端测试失败")
        exit(1)


if __name__ == "__main__":
    main()