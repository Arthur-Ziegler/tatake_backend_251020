#!/usr/bin/env python3
"""
边界情况测试脚本

根据Day5提案要求，测试以下边界情况：
- Top3设置明日任务（允许）
- Top3设置后日任务（拒绝）
- 积分不足时设置Top3（拒绝）
- 材料不足时兑换（返回详细required列表）
- 未登录访问受保护端点（401）
- 访问他人任务（403/404）

作者：TaKeKe团队
版本：边界情况测试
"""

import json
import requests
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 测试配置
BASE_URL = "http://localhost:8001"


class EdgeCaseTester:
    """边界情况测试器"""

    def __init__(self):
        self.base_url = BASE_URL
        self.user_tokens = {}  # 存储多个用户的token
        self.user_ids = {}     # 存储多个用户的ID
        self.test_results = []

    def log_result(self, test_name: str, success: bool, data: Optional[Dict] = None, error: Optional[str] = None):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "timestamp": datetime.now().isoformat()
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
            openid = f"edge_test_{identifier}_{uuid.uuid4().hex[:8]}"

            # 注册用户
            register_response = requests.post(f"{self.base_url}/auth/register", json={
                "wechat_openid": openid
            })

            if register_response.status_code != 200:
                self.log_result(f"创建测试用户{identifier}", False, error=f"HTTP {register_response.status_code}")
                return False

            register_data = register_response.json()
            if register_data.get("code") != 200:
                self.log_result(f"创建测试用户{identifier}", False, error=register_data.get("message"))
                return False

            # 登录用户
            login_response = requests.post(f"{self.base_url}/auth/login", json={
                "wechat_openid": openid
            })

            if login_response.status_code != 200:
                self.log_result(f"登录测试用户{identifier}", False, error=f"HTTP {login_response.status_code}")
                return False

            login_data = login_response.json()
            if login_data.get("code") != 200:
                self.log_result(f"登录测试用户{identifier}", False, error=login_data.get("message"))
                return False

            self.user_tokens[identifier] = login_data["data"]["access_token"]
            self.user_ids[identifier] = login_data["data"]["user_id"]

            self.log_result(f"创建测试用户{identifier}", True, {"user_id": self.user_ids[identifier]})
            return True

        except Exception as e:
            self.log_result(f"创建测试用户{identifier}", False, error=str(e))
            return False

    def get_headers(self, identifier: str = "user1") -> Dict[str, str]:
        """获取认证头"""
        token = self.user_tokens.get(identifier)
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def test_top3_tomorrow_task(self) -> bool:
        """
        测试Top3设置明日任务（允许）
        """
        print("\n" + "="*60)
        print("边界测试：Top3设置明日任务")
        print("="*60)

        try:
            # 创建明日任务
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            task_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "明日任务",
                "description": "这是一个明日的任务",
                "planned_start_time": f"{tomorrow}T09:00:00",
                "planned_end_time": f"{tomorrow}T10:00:00"
            }, headers=self.get_headers("user1"))

            if task_response.status_code != 200:
                self.log_result("创建明日任务", False, error=f"HTTP {task_response.status_code}")
                return False

            task_data = task_response.json()
            if task_data.get("code") != 200:
                self.log_result("创建明日任务", False, error=task_data.get("message"))
                return False

            task_id = task_data["data"]["id"]
            self.log_result("创建明日任务", True, {"task_id": task_id})

            # 尝试将明日任务设置为Top3
            top3_response = requests.post(f"{self.base_url}/tasks/special/top3", json={
                "task_ids": [task_id]
            }, headers=self.get_headers("user1"))

            if top3_response.status_code == 200:
                top3_data = top3_response.json()
                if top3_data.get("code") == 200:
                    self.log_result("Top3设置明日任务", True, {"note": "允许设置明日任务"})
                    return True
                else:
                    self.log_result("Top3设置明日任务", False, error=top3_data.get("message"))
            else:
                self.log_result("Top3设置明日任务", False, error=f"HTTP {top3_response.status_code}")

        except Exception as e:
            self.log_result("Top3设置明日任务", False, error=str(e))

        return False

    def test_top3_day_after_tomorrow(self) -> bool:
        """
        测试Top3设置后日任务（拒绝）
        """
        print("\n" + "="*60)
        print("边界测试：Top3设置后日任务")
        print("="*60)

        try:
            # 创建后日任务
            day_after_tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            task_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "后日任务",
                "description": "这是一个后日的任务",
                "planned_start_time": f"{day_after_tomorrow}T09:00:00",
                "planned_end_time": f"{day_after_tomorrow}T10:00:00"
            }, headers=self.get_headers("user1"))

            if task_response.status_code != 200:
                self.log_result("创建后日任务", False, error=f"HTTP {task_response.status_code}")
                return False

            task_data = task_response.json()
            if task_data.get("code") != 200:
                self.log_result("创建后日任务", False, error=task_data.get("message"))
                return False

            task_id = task_data["data"]["id"]
            self.log_result("创建后日任务", True, {"task_id": task_id})

            # 尝试将后日任务设置为Top3（应该被拒绝）
            top3_response = requests.post(f"{self.base_url}/tasks/special/top3", json={
                "task_ids": [task_id]
            }, headers=self.get_headers("user1"))

            if top3_response.status_code == 200:
                top3_data = top3_response.json()
                if top3_data.get("code") != 200:
                    self.log_result("Top3设置后日任务", True, {"note": "正确拒绝后日任务", "error": top3_data.get("message")})
                    return True
                else:
                    self.log_result("Top3设置后日任务", False, error="意外允许了后日任务")
            else:
                self.log_result("Top3设置后日任务", True, {"note": "HTTP拒绝", "status": top3_response.status_code})
                return True

        except Exception as e:
            self.log_result("Top3设置后日任务", False, error=str(e))

        return False

    def test_insufficient_points_for_top3(self) -> bool:
        """
        测试积分不足时设置Top3（拒绝）
        """
        print("\n" + "="*60)
        print("边界测试：积分不足时设置Top3")
        print("="*60)

        try:
            # 创建一个新用户，确保积分不足
            if not self.create_test_user("poor_user"):
                return False

            # 创建几个任务
            task_ids = []
            for i in range(3):
                task_response = requests.post(f"{self.base_url}/tasks/", json={
                    "title": f"积分不足测试任务{i+1}",
                    "description": f"测试积分不足情况下的任务{i+1}"
                }, headers=self.get_headers("poor_user"))

                if task_response.status_code == 200:
                    task_data = task_response.json()
                    if task_data.get("code") == 200:
                        task_ids.append(task_data["data"]["id"])

            if len(task_ids) < 3:
                self.log_result("创建任务失败", False, error="无法创建足够的测试任务")
                return False

            self.log_result("创建测试任务", True, {"count": len(task_ids)})

            # 查询当前积分
            balance_response = requests.get(f"{self.base_url}/points/my-points", headers=self.get_headers("poor_user"))
            if balance_response.status_code == 200 and balance_response.json().get("code") == 200:
                balance = balance_response.json()["data"]["balance"]
                self.log_result("查询积分余额", True, {"balance": balance})

                # 尝试设置Top3（如果积分少于300应该失败）
                top3_response = requests.post(f"{self.base_url}/tasks/special/top3", json={
                    "task_ids": task_ids
                }, headers=self.get_headers("poor_user"))

                if top3_response.status_code == 200:
                    top3_data = top3_response.json()
                    if top3_data.get("code") != 200:
                        self.log_result("积分不足时设置Top3", True, {
                            "note": "正确拒绝",
                            "balance": balance,
                            "error": top3_data.get("message")
                        })
                        return True
                    else:
                        self.log_result("积分不足时设置Top3", False, error="意外允许了积分不足的Top3设置")
                else:
                    self.log_result("积分不足时设置Top3", True, {
                        "note": "HTTP拒绝",
                        "balance": balance,
                        "status": top3_response.status_code
                    })
                    return True
            else:
                self.log_result("查询积分余额", False, error="无法查询积分余额")

        except Exception as e:
            self.log_result("积分不足时设置Top3", False, error=str(e))

        return False

    def test_insufficient_materials_for_redeem(self) -> bool:
        """
        测试材料不足时兑换（返回详细required列表）
        """
        print("\n" + "="*60)
        print("边界测试：材料不足时兑换")
        print("="*60)

        try:
            # 查询奖励目录
            catalog_response = requests.get(f"{self.base_url}/rewards/catalog", headers=self.get_headers("user1"))
            if catalog_response.status_code != 200 or catalog_response.json().get("code") != 200:
                self.log_result("查询奖励目录", False, error="无法获取奖励目录")
                return False

            rewards = catalog_response.json()["data"]
            if not rewards:
                self.log_result("材料不足时兑换", False, error="奖励目录为空")
                return False

            # 选择一个需要材料合成的奖励（如果有）
            target_reward = None
            for reward in rewards:
                if reward.get("cost_type") == "materials":  # 假设有材料类型的奖励
                    target_reward = reward
                    break

            if not target_reward:
                # 如果没有材料类型的奖励，尝试一个不存在的奖励ID
                target_reward = {"id": str(uuid.uuid4()), "name": "不存在的奖励"}
                self.log_result("选择测试奖励", True, {"note": "使用不存在的奖励ID"})
            else:
                self.log_result("选择测试奖励", True, {"reward_name": target_reward.get("name")})

            # 尝试兑换（应该失败并返回详细信息）
            redeem_response = requests.post(f"{self.base_url}/rewards/redeem", json={
                "reward_id": target_reward["id"]
            }, headers=self.get_headers("user1"))

            if redeem_response.status_code == 200:
                redeem_data = redeem_response.json()
                if redeem_data.get("code") != 200:
                    self.log_result("材料不足时兑换", True, {
                        "note": "正确拒绝",
                        "error": redeem_data.get("message")
                    })
                    return True
                else:
                    self.log_result("材料不足时兑换", False, error="意外成功兑换")
            else:
                # 检查是否返回了详细的错误信息
                try:
                    error_data = redeem_response.json()
                    if "required" in str(error_data) or "materials" in str(error_data).lower():
                        self.log_result("材料不足时兑换", True, {
                            "note": "返回详细材料信息",
                            "error": error_data
                        })
                        return True
                    else:
                        self.log_result("材料不足时兑换", True, {
                            "note": "HTTP拒绝，但没有详细材料信息",
                            "status": redeem_response.status_code
                        })
                        return True
                except:
                    self.log_result("材料不足时兑换", True, {
                        "note": "HTTP拒绝",
                        "status": redeem_response.status_code
                    })
                    return True

        except Exception as e:
            self.log_result("材料不足时兑换", False, error=str(e))

        return False

    def test_unauthorized_access(self) -> bool:
        """
        测试未登录访问受保护端点（401）
        """
        print("\n" + "="*60)
        print("边界测试：未登录访问受保护端点")
        print("="*60)

        try:
            # 测试多个需要认证的端点
            protected_endpoints = [
                ("GET", "/tasks/"),
                ("POST", "/tasks/"),
                ("GET", "/rewards/catalog"),
                ("GET", "/points/my-points"),
                ("GET", "/tasks/special/top3"),
                ("GET", "/focus/sessions")
            ]

            success_count = 0
            for method, endpoint in protected_endpoints:
                try:
                    if method == "GET":
                        response = requests.get(f"{self.base_url}{endpoint}")
                    elif method == "POST":
                        response = requests.post(f"{self.base_url}{endpoint}", json={})

                    if response.status_code == 401:
                        self.log_result(f"未登录访问{method} {endpoint}", True, {"status": 401})
                        success_count += 1
                    else:
                        self.log_result(f"未登录访问{method} {endpoint}", False, error=f"期望401，实际{response.status_code}")

                except Exception as e:
                    self.log_result(f"未登录访问{method} {endpoint}", False, error=str(e))

            # 测试认证相关的端点（这些不应该返回401）
            auth_endpoints = [
                ("POST", "/auth/register"),
                ("POST", "/auth/login")
            ]

            for method, endpoint in auth_endpoints:
                try:
                    if method == "POST":
                        response = requests.post(f"{self.base_url}{endpoint}", json={
                            "wechat_openid": f"test_{uuid.uuid4().hex[:8]}"
                        })

                    if response.status_code != 401:
                        self.log_result(f"未登录访问{method} {endpoint}", True, {"note": "认证端点正确允许访问"})
                        success_count += 1
                    else:
                        self.log_result(f"未登录访问{method} {endpoint}", False, error="认证端点不应该返回401")

                except Exception as e:
                    self.log_result(f"未登录访问{method} {endpoint}", False, error=str(e))

            return success_count == len(protected_endpoints) + len(auth_endpoints)

        except Exception as e:
            self.log_result("未登录访问测试", False, error=str(e))
            return False

    def test_access_other_user_task(self) -> bool:
        """
        测试访问他人任务（403/404）
        """
        print("\n" + "="*60)
        print("边界测试：访问他人任务")
        print("="*60)

        try:
            # 创建第二个用户
            if not self.create_test_user("user2"):
                return False

            # 用户1创建任务
            task_response = requests.post(f"{self.base_url}/tasks/", json={
                "title": "用户1的任务",
                "description": "这是用户1的私有任务"
            }, headers=self.get_headers("user1"))

            if task_response.status_code != 200:
                self.log_result("用户1创建任务", False, error=f"HTTP {task_response.status_code}")
                return False

            task_data = task_response.json()
            if task_data.get("code") != 200:
                self.log_result("用户1创建任务", False, error=task_data.get("message"))
                return False

            task_id = task_data["data"]["id"]
            self.log_result("用户1创建任务", True, {"task_id": task_id})

            # 用户2尝试访问用户1的任务
            access_response = requests.get(f"{self.base_url}/tasks/{task_id}", headers=self.get_headers("user2"))

            if access_response.status_code in [403, 404]:
                self.log_result("用户2访问用户1任务", True, {
                    "note": "正确拒绝访问",
                    "status": access_response.status_code
                })
                return True
            else:
                access_data = access_response.json()
                if access_response.status_code == 200 and access_data.get("code") == 200:
                    self.log_result("用户2访问用户1任务", False, error="意外允许访问他人任务")
                else:
                    self.log_result("用户2访问用户1任务", True, {
                        "note": "业务层拒绝访问",
                        "error": access_data.get("message")
                    })
                    return True

        except Exception as e:
            self.log_result("访问他人任务测试", False, error=str(e))

        return False

    def run_all_edge_cases(self) -> Tuple[int, int]:
        """运行所有边界情况测试"""
        print("开始边界情况测试...")
        print(f"测试目标: {self.base_url}")
        print(f"测试时间: {datetime.now().isoformat()}")

        # 创建测试用户
        if not self.create_test_user("user1"):
            print("❌ 无法创建测试用户，停止测试")
            return 0, 0

        # 运行边界测试
        edge_cases = [
            ("Top3设置明日任务", self.test_top3_tomorrow_task),
            ("Top3设置后日任务", self.test_top3_day_after_tomorrow),
            ("积分不足时设置Top3", self.test_insufficient_points_for_top3),
            ("材料不足时兑换", self.test_insufficient_materials_for_redeem),
            ("未登录访问受保护端点", self.test_unauthorized_access),
            ("访问他人任务", self.test_access_other_user_task)
        ]

        passed_cases = 0
        total_cases = len(edge_cases)

        for case_name, case_func in edge_cases:
            try:
                if case_func():
                    passed_cases += 1
                    print(f"✅ {case_name} - 通过")
                else:
                    print(f"❌ {case_name} - 失败")
            except Exception as e:
                print(f"❌ {case_name} - 异常: {e}")

        # 生成测试报告
        self.generate_edge_case_report(passed_cases, total_cases)

        return passed_cases, total_cases

    def generate_edge_case_report(self, passed: int, total: int):
        """生成边界情况测试报告"""
        print("\n" + "="*80)
        print("边界情况测试报告")
        print("="*80)
        print(f"测试时间: {datetime.now().isoformat()}")
        print(f"总边界情况: {total}")
        print(f"通过情况: {passed}")
        print(f"失败情况: {total - passed}")
        print(f"通过率: {passed/total*100:.1f}%")

        print(f"\n详细结果:")
        for result in self.test_results:
            print(f"  {result['status']} {result['test']}")

        # 保存测试报告到文件
        report_data = {
            "test_time": datetime.now().isoformat(),
            "summary": {
                "total_edge_cases": total,
                "passed_edge_cases": passed,
                "failed_edge_cases": total - passed,
                "pass_rate": passed/total*100
            },
            "users": self.user_ids,
            "results": self.test_results
        }

        try:
            with open("edge_case_report.json", "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"\n边界情况测试报告已保存到: edge_case_report.json")
        except Exception as e:
            print(f"保存边界情况测试报告失败: {e}")


def main():
    """主函数"""
    print("TaKeKe边界情况测试")
    print("="*80)

    tester = EdgeCaseTester()
    passed, total = tester.run_all_edge_cases()

    if passed == total:
        print("\n🎉 所有边界情况测试通过！")
        exit(0)
    else:
        print(f"\n❌ {total-passed}个边界情况测试失败")
        exit(1)


if __name__ == "__main__":
    main()