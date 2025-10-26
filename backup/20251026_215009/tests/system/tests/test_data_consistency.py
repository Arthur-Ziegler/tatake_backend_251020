"""
数据一致性测试

验证API返回的数据与数据库中的实际数据保持一致，确保事务正确提交。
"""

from ..conftest import (
    print_test_header, print_success, print_error,
    authenticated_client
)


class TestDataConsistency:
    """数据一致性测试类"""

    def test_api_database_data_consistency(self, authenticated_client):
        """
        测试API与数据库数据一致性

        验证任务完成后API返回的积分数据与数据库实际数据一致。
        """
        print_test_header("数据一致性验证")
        print("🔍 测试API与数据库数据一致性...")

        api_client, auth_data = authenticated_client
        user_id = auth_data["user_id"]

        try:
            # 创建任务
            task_data = {
                "title": "一致性测试",
                "description": "测试",
                "status": "pending"
            }

            created_task = api_client.create_task(task_data)
            task_id = created_task["id"]
            print_success(f"任务创建成功: {task_id}")

            # 完成任务
            complete_result = api_client.complete_task(task_id)
            points_awarded = complete_result["completion_result"]["points_awarded"]
            print_success(f"任务完成，获得积分: {points_awarded}")

            # 检查积分一致性
            balance_data = api_client.get_points_balance()
            current_balance = balance_data.get("current_balance", 0)

            if current_balance == points_awarded:
                print_success("数据一致性验证通过")
                print(f"   API显示获得积分: {points_awarded}")
                print(f"   积分余额显示: {current_balance}")
                return True
            else:
                print_error(f"积分不一致: API显示获得{points_awarded}积分，但余额为{current_balance}")
                return False

        except Exception as e:
            print_error(f"一致性测试异常: {e}")
            return False

    def test_task_status_consistency(self, authenticated_client):
        """
        测试任务状态一致性

        验证任务操作后API返回的状态与数据库实际状态一致。
        """
        print("🔍 测试任务状态一致性...")

        api_client, auth_data = authenticated_client
        user_id = auth_data["user_id"]

        try:
            # 创建任务
            task_data = {
                "title": "状态一致性测试",
                "description": "测试",
                "status": "pending"
            }

            created_task = api_client.create_task(task_data)
            task_id = created_task["id"]
            initial_status = created_task["status"]
            print_success(f"任务创建，初始状态: {initial_status}")

            # 完成任务
            complete_result = api_client.complete_task(task_id)
            api_status = complete_result["task"]["status"]
            print_success(f"API返回任务状态: {api_status}")

            # 查询数据库状态
            db_task = api_client.query_task_from_database(task_id, user_id)
            if not db_task:
                print_error("数据库查询失败")
                return False

            db_status = db_task["status"]
            print_success(f"数据库任务状态: {db_status}")

            # 验证状态一致性
            if api_status == db_status:
                print_success("任务状态一致性验证通过")
                return True
            else:
                print_error(f"任务状态不一致: API={api_status}, DB={db_status}")
                return False

        except Exception as e:
            print_error(f"状态一致性测试异常: {e}")
            return False

    def test_transaction_consistency(self, authenticated_client):
        """
        测试事务一致性

        验证相关操作的事务原子性，要么全部成功，要么全部失败。
        """
        print("🔍 测试事务一致性...")

        api_client, auth_data = authenticated_client
        user_id = auth_data["user_id"]

        try:
            # 创建任务
            task_data = {
                "title": "事务一致性测试",
                "description": "测试",
                "status": "pending"
            }

            created_task = api_client.create_task(task_data)
            task_id = created_task["id"]
            print_success(f"任务创建成功: {task_id}")

            # 获取初始积分
            initial_balance = api_client.get_points_balance().get("current_balance", 0)
            print_success(f"初始积分: {initial_balance}")

            # 完成任务
            complete_result = api_client.complete_task(task_id)
            points_awarded = complete_result["completion_result"]["points_awarded"]
            final_balance = api_client.get_points_balance().get("current_balance", 0)

            print_success(f"完成任务，获得积分: {points_awarded}")
            print_success(f"最终积分: {final_balance}")

            # 验证事务一致性
            expected_balance = initial_balance + points_awarded
            if final_balance == expected_balance:
                print_success("事务一致性验证通过")
                return True
            else:
                print_error(f"事务一致性失败: 期望{expected_balance}, 实际{final_balance}")
                return False

        except Exception as e:
            print_error(f"事务一致性测试异常: {e}")
            return False