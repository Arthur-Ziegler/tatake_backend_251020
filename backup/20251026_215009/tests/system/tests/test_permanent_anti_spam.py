"""
永久防刷机制测试

验证任务只能领一次奖的规则：一个任务完成过一次领过一次奖励就永远不能再领奖，
不管取消完成、跨天、还是任何其他情况，都不能再领奖。
"""

from ..conftest import (
    print_test_header, print_success, print_error,
    authenticated_client
)


class TestPermanentAntiSpam:
    """永久防刷机制测试类"""

    def test_permanent_anti_spam_mechanism(self, authenticated_client):
        """
        测试永久防刷机制

        验证任务完成过一次后，即使取消完成再次完成也不能再获得积分。
        """
        print_test_header("永久防刷机制验证")
        print("🔍 测试永久防刷逻辑...")

        api_client, auth_data = authenticated_client
        user_id = auth_data["user_id"]

        try:
            # 1. 创建测试任务
            print("1. 创建测试任务...")
            task_data = {
                "title": "永久防刷测试任务",
                "description": "测试永久防刷机制",
                "status": "pending",
                "priority": "high"
            }

            created_task = api_client.create_task(task_data)
            task_id = created_task["id"]
            print_success(f"任务创建成功: {task_id}")
            print(f"   初始状态: {created_task['status']}")
            print(f"   初始last_claimed_date: {created_task.get('last_claimed_date')}")

            # 2. 第一次完成任务
            print("2. 第一次完成任务...")
            complete_result = api_client.complete_task(task_id)
            first_points = complete_result['completion_result']['points_awarded']
            reward_type = complete_result['completion_result']['reward_type']
            message = complete_result['completion_result']['message']

            print_success("第一次完成结果:")
            print(f"   - 积分奖励: {first_points}")
            print(f"   - 奖励类型: {reward_type}")
            print(f"   - 消息: {message}")
            print(f"   - 任务状态: {complete_result['task']['status']}")
            print(f"   - last_claimed_date: {complete_result['task'].get('last_claimed_date')}")

            if first_points <= 0:
                print_error(f"第一次完成应该获得积分，但实际获得: {first_points}")
                return False

            # 3. 取消完成任务
            print("3. 取消完成任务...")
            uncomplete_result = api_client.uncomplete_task(task_id)
            print_success("取消完成结果:")
            print(f"   - 任务状态: {uncomplete_result['task']['status']}")
            print(f"   - last_claimed_date: {uncomplete_result['task'].get('last_claimed_date')}")
            print(f"   - 消息: {uncomplete_result['message']}")

            # 4. 尝试再次完成任务（关键测试）
            print("4. 尝试再次完成任务（关键测试）...")
            result = api_client.complete_task(task_id)
            points_awarded = result['completion_result']['points_awarded']
            reward_type = result['completion_result']['reward_type']
            message = result['completion_result']['message']

            print_success("再次完成结果:")
            print(f"   - 积分奖励: {points_awarded}")
            print(f"   - 奖励类型: {reward_type}")
            print(f"   - 消息: {message}")
            print(f"   - 任务状态: {result['task']['status']}")
            print(f"   - last_claimed_date: {result['task'].get('last_claimed_date')}")

            # 5. 验证永久防刷
            print("5. 验证永久防刷机制...")

            if points_awarded > 0:
                print_error(f"永久防刷机制失效！任务取消后再次完成获得了积分: {points_awarded}")
                print_error("这违背了'一个任务只能领一次奖'的规则")
                return False
            else:
                print_success("永久防刷机制生效！")
                print("   - 即使取消完成后再次完成，也不能再获得积分")
                print("   - 这符合'一个任务只能领一次奖'的规则")

            # 6. 验证总积分
            print("6. 验证总积分...")
            balance_data = api_client.get_points_balance()
            total_points = balance_data.get("current_balance", 0)

            print_success(f"当前总积分: {total_points}")

            expected_points = first_points  # 应该只有第一次完成的积分
            if total_points == expected_points:
                print_success("积分计算正确，永久防刷机制完全生效！")
                return True
            else:
                print_error(f"积分计算错误！期望: {expected_points}, 实际: {total_points}")
                return False

        except Exception as e:
            print_error(f"测试异常: {e}")
            return False