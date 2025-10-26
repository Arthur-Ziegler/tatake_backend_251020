"""
任务状态修复测试

验证修复后的任务状态更新逻辑：
1. 防刷场景下任务状态应该正确更新为completed
2. 取消完成后再次完成，状态应该变为completed（而不是卡在pending）
"""

from ..conftest import (
    print_test_header, print_success, print_error,
    authenticated_client
)


class TestTaskStatusFix:
    """任务状态修复测试类"""

    def test_task_status_updates_after_anti_spam(self, authenticated_client):
        """
        测试防刷场景下任务状态更新

        验证任务完成过一次后，取消完成再次完成时，
        虽然不给积分，但任务状态应该正确更新为completed。
        """
        print_test_header("任务状态更新修复验证")
        print("🔍 测试防刷场景下任务状态更新...")

        api_client, auth_data = authenticated_client
        user_id = auth_data["user_id"]

        try:
            # 1. 创建测试任务
            task_data = {
                "title": "状态修复测试任务",
                "description": "测试任务状态更新修复",
                "status": "pending"
            }

            created_task = api_client.create_task(task_data)
            task_id = created_task["id"]
            print_success(f"任务创建成功: {task_id}, 初始状态: {created_task['status']}")

            # 2. 第一次完成任务
            complete_result = api_client.complete_task(task_id)
            first_points = complete_result['completion_result']['points_awarded']
            first_status = complete_result['task']['status']

            print_success(f"第一次完成: 积分={first_points}, 状态={first_status}")

            if first_points <= 0 or first_status != "completed":
                print_error("第一次完成结果异常")
                return False

            # 3. 取消完成任务
            uncomplete_result = api_client.uncomplete_task(task_id)
            uncomplete_status = uncomplete_result['task']['status']

            print_success(f"取消完成: 状态={uncomplete_status}")

            if uncomplete_status != "pending":
                print_error(f"取消完成后状态应该为pending，实际为: {uncomplete_status}")
                return False

            # 4. 再次完成任务（关键测试）
            print("执行关键测试：再次完成任务...")
            second_complete_result = api_client.complete_task(task_id)
            second_points = second_complete_result['completion_result']['points_awarded']
            second_status = second_complete_result['task']['status']
            reward_type = second_complete_result['completion_result']['reward_type']

            print_success(f"再次完成: 积分={second_points}, 状态={second_status}, 奖励类型={reward_type}")

            # 5. 验证修复结果
            print("验证修复结果...")

            # 防刷应该生效（不给积分）
            if second_points != 0:
                print_error(f"防刷失效，再次完成不应该获得积分，实际获得: {second_points}")
                return False

            if reward_type != "task_already_completed_once":
                print_error(f"奖励类型错误，期望: task_already_completed_once, 实际: {reward_type}")
                return False

            # 状态应该正确更新为completed
            if second_status != "completed":
                print_error(f"任务状态修复失败！期望: completed, 实际: {second_status}")
                print_error("这是原始bug：任务状态卡在pending无法更新")
                return False

            print_success("✅ 任务状态修复成功！")
            print_success("   - 防刷机制正确生效（不给积分）")
            print_success("   - 任务状态正确更新为completed")
            print_success("   - 不再卡在pending状态")

            # 6. 验证数据库状态一致性
            db_task = api_client.query_task_from_database(task_id, user_id)
            if db_task and db_task["status"] == "completed":
                print_success("数据库状态一致性验证通过")
                return True
            else:
                print_error(f"数据库状态不一致: {db_task}")
                return False

        except Exception as e:
            print_error(f"测试异常: {e}")
            return False

    def test_multiple_completion_cycle(self, authenticated_client):
        """
        测试多次完成循环

        验证任务经历多次完成/取消完成循环后，
        最终状态仍能正确更新。
        """
        print_test_header("多次完成循环测试")
        print("🔍 测试多次完成循环后的状态更新...")

        api_client, auth_data = authenticated_client
        user_id = auth_data["user_id"]

        try:
            # 创建任务
            task_data = {
                "title": "循环测试任务",
                "description": "测试多次循环",
                "status": "pending"
            }

            created_task = api_client.create_task(task_data)
            task_id = created_task["id"]

            # 第一次完成
            api_client.complete_task(task_id)
            print_success("第1次完成")

            # 循环：取消完成 -> 再次完成
            for i in range(3):
                print(f"执行第{i+2}次循环...")

                # 取消完成
                uncomplete_result = api_client.uncomplete_task(task_id)
                if uncomplete_result['task']['status'] != "pending":
                    print_error(f"第{i+1}次取消完成状态错误")
                    return False

                # 再次完成
                complete_result = api_client.complete_task(task_id)
                status = complete_result['task']['status']
                points = complete_result['completion_result']['points_awarded']

                if status != "completed":
                    print_error(f"第{i+2}次完成状态错误: {status}")
                    return False

                if points != 0:
                    print_error(f"第{i+2}次完成不应该获得积分: {points}")
                    return False

                print_success(f"第{i+2}次循环完成: 状态={status}, 积分={points}")

            print_success("多次完成循环测试通过")
            return True

        except Exception as e:
            print_error(f"循环测试异常: {e}")
            return False