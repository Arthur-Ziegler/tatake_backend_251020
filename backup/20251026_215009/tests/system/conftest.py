"""
系统测试配置和共享工具

提供系统测试所需的配置、工具函数和测试数据。
"""

import pytest
import requests
import uuid
import sqlite3
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8001"
DATABASE_PATH = "tatake.db"


class SystemTestClient:
    """系统测试客户端，提供API调用和数据库操作工具"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def register_user(self, openid_prefix: str = "test") -> Dict[str, Any]:
        """注册测试用户"""
        register_data = {
            "wechat_openid": f"{openid_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        }

        response = self.session.post(f"{self.base_url}/auth/register", json=register_data)
        if response.status_code != 200:
            raise Exception(f"用户注册失败: {response.status_code} - {response.text}")

        auth_data = response.json()["data"]
        token = auth_data["access_token"]

        # 设置认证头
        self.session.headers.update({"Authorization": f"Bearer {token}"})

        return auth_data

    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务"""
        response = self.session.post(f"{self.base_url}/tasks/", json=task_data)
        if response.status_code not in [200, 201]:
            raise Exception(f"创建任务失败: {response.status_code} - {response.text}")

        return response.json()["data"]

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """完成任务"""
        response = self.session.post(f"{self.base_url}/tasks/{task_id}/complete", json={})
        if response.status_code != 200:
            raise Exception(f"完成任务失败: {response.status_code} - {response.text}")

        return response.json()["data"]

    def uncomplete_task(self, task_id: str) -> Dict[str, Any]:
        """取消完成任务"""
        response = self.session.post(f"{self.base_url}/tasks/{task_id}/uncomplete", json={})
        if response.status_code != 200:
            raise Exception(f"取消完成失败: {response.status_code} - {response.text}")

        return response.json()["data"]

    def get_points_balance(self) -> Dict[str, Any]:
        """获取积分余额"""
        response = self.session.get(f"{self.base_url}/points/balance")
        if response.status_code != 200:
            raise Exception(f"获取积分余额失败: {response.status_code} - {response.text}")

        return response.json()["data"]

    def query_task_from_database(self, task_id: str, user_id: str) -> Optional[Dict[str, Any]]:
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


@pytest.fixture(scope="module")
def api_client():
    """API测试客户端fixture"""
    return SystemTestClient()


@pytest.fixture(scope="module")
def authenticated_client(api_client):
    """已认证的API客户端fixture"""
    auth_data = api_client.register_user("system_test")
    return api_client, auth_data


def verify_standard_response_format(response_data: Dict[str, Any]) -> bool:
    """验证标准响应格式"""
    return ("code" in response_data and
            "data" in response_data and
            "message" in response_data)


def print_test_header(test_name: str):
    """打印测试标题"""
    print(f"\n📋 {test_name}")
    print("-" * 40)


def print_success(message: str):
    """打印成功信息"""
    print(f"✅ {message}")


def print_error(message: str):
    """打印错误信息"""
    print(f"❌ {message}")