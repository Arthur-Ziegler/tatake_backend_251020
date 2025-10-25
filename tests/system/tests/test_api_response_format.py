"""
API响应格式统一测试

验证所有API都返回标准格式：{"code":200,"message":"...","data":{...}}。
"""

from tests.system.conftest import (
    print_test_header, print_success, print_error,
    verify_standard_response_format, authenticated_client
)


class TestApiResponseFormat:
    """API响应格式统一测试类"""

    def test_points_api_response_format(self, authenticated_client):
        """
        测试积分API响应格式统一

        验证积分相关API使用标准响应格式包装。
        """
        print_test_header("API响应格式统一验证")
        print("🔍 测试API响应格式统一...")

        api_client, auth_data = authenticated_client

        try:
            # 测试积分余额API响应格式
            balance_data = api_client.get_points_balance()

            # 验证响应格式
            if verify_standard_response_format(balance_data):
                print_success("积分API响应格式正确")
                return True
            else:
                print_error(f"积分API响应格式错误: {balance_data}")
                return False

        except Exception as e:
            print_error(f"API格式测试异常: {e}")
            return False

    def test_auth_api_response_format(self, api_client):
        """
        测试认证API响应格式

        验证认证相关API使用标准响应格式。
        """
        print("🔍 测试认证API响应格式...")

        try:
            # 测试用户注册API响应格式
            auth_data = api_client.register_user("format_test")

            # 验证响应格式
            if ("user_id" in auth_data and
                "access_token" in auth_data and
                "refresh_token" in auth_data):
                print_success("认证API响应格式正确")
                return True
            else:
                print_error(f"认证API响应格式错误: {auth_data}")
                return False

        except Exception as e:
            print_error(f"认证API格式测试异常: {e}")
            return False

    def test_task_api_response_format(self, authenticated_client):
        """
        测试任务API响应格式

        验证任务相关API使用标准响应格式。
        """
        print("🔍 测试任务API响应格式...")

        api_client, auth_data = authenticated_client

        try:
            # 测试任务创建API响应格式
            task_data = {
                "title": "格式测试任务",
                "description": "测试API响应格式",
                "status": "pending"
            }

            response = api_client.session.post(f"{api_client.base_url}/tasks/", json=task_data)
            if response.status_code not in [200, 201]:
                print_error(f"创建任务失败: {response.status_code}")
                return False

            response_data = response.json()

            # 验证响应格式
            if ("code" in response_data and
                "data" in response_data and
                "message" in response_data and
                "id" in response_data["data"]):
                print_success("任务API响应格式正确")
                return True
            else:
                print_error(f"任务API响应格式错误: {response_data}")
                return False

        except Exception as e:
            print_error(f"任务API格式测试异常: {e}")
            return False