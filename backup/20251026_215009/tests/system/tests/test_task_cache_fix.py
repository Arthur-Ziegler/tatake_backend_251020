"""
任务缓存问题修复测试

验证任务更新后数据能立即同步到数据库，确保事务正确提交。
"""

from ..conftest import (
    print_test_header, print_success, print_error,
    authenticated_client
)


class TestTaskCacheFix:
    """任务缓存问题修复测试类"""

    def test_task_cache_data_synchronization(self, authenticated_client):
        """
        测试任务更新后数据同步到数据库

        验证Repository层的commit()调用确保数据持久化。
        """
        print_test_header("任务缓存问题修复验证")
        print("🔍 测试任务更新后数据同步...")

        api_client, auth_data = authenticated_client
        user_id = auth_data["user_id"]

        try:
            # 创建任务
            task_data = {
                "title": "缓存测试任务",
                "description": "测试缓存修复",
                "status": "pending"
            }

            created_task = api_client.create_task(task_data)
            task_id = created_task["id"]
            print_success(f"任务创建成功: {task_id}")

            # 更新任务
            update_data = {
                "title": "缓存测试任务-已更新",
                "status": "in_progress"
            }

            response = api_client.session.put(
                f"{api_client.base_url}/tasks/{task_id}",
                json=update_data
            )

            if response.status_code != 200:
                print_error(f"更新任务失败: {response.status_code}")
                return False

            print_success("任务更新成功")

            # 立即查询数据库验证
            db_task = api_client.query_task_from_database(task_id, user_id)
            if not db_task:
                print_error("数据库查询失败")
                return False

            # 验证数据一致性
            expected_title = update_data["title"]
            expected_status = update_data["status"]

            if (db_task["title"] == expected_title and
                db_task["status"] == expected_status):
                print_success("任务缓存问题已修复，数据正确同步到数据库")
                return True
            else:
                print_error(f"数据不一致！期望: title={expected_title}, status={expected_status}")
                print_error(f"实际: title={db_task['title']}, status={db_task['status']}")
                return False

        except Exception as e:
            print_error(f"测试异常: {e}")
            return False