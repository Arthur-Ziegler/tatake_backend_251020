#!/usr/bin/env python3
"""
简化的防刷测试
"""

import requests
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8001"

def simple_anti_spam_test():
    """简化的防刷测试"""
    print("🔍 开始简化防刷测试...")

    # 1. 注册测试用户
    print("\n1. 注册测试用户...")
    register_data = {
        "wechat_openid": f"simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code != 200:
        print(f"❌ 注册失败: {response.status_code} - {response.text}")
        return False

    auth_data = response.json()["data"]
    user_id = auth_data["user_id"]
    token = auth_data["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"✅ 用户注册成功: {user_id}")

    # 2. 创建测试任务
    print("\n2. 创建测试任务...")
    task_data = {
        "title": "简化防刷测试任务",
        "description": "测试防刷机制",
        "status": "pending",
        "priority": "high"
    }

    response = requests.post(f"{BASE_URL}/tasks/", json=task_data, headers=headers)
    if response.status_code not in [200, 201]:
        print(f"❌ 创建任务失败: {response.status_code} - {response.text}")
        return False

    created_task = response.json()["data"]
    task_id = created_task["id"]
    print(f"✅ 任务创建成功: {task_id}")

    # 3. 第一次完成任务
    print("\n3. 第一次完成任务...")
    response = requests.post(f"{BASE_URL}/tasks/{task_id}/complete", json={}, headers=headers)
    if response.status_code != 200:
        print(f"❌ 完成任务失败: {response.status_code} - {response.text}")
        return False

    complete_result = response.json()["data"]
    first_points = complete_result['completion_result']['points_awarded']
    print(f"✅ 第一次完成，获得积分: {first_points}")

    # 4. 取消任务完成
    print("\n4. 取消任务完成...")
    response = requests.post(f"{BASE_URL}/tasks/{task_id}/uncomplete", json={}, headers=headers)
    if response.status_code != 200:
        print(f"❌ 取消完成失败: {response.status_code} - {response.text}")
        return False

    uncomplete_result = response.json()["data"]
    print(f"✅ 取消完成，状态: {uncomplete_result['task']['status']}")

    # 5. 再次完成任务（关键测试）
    print("\n5. 再次完成任务（关键测试）...")
    response = requests.post(f"{BASE_URL}/tasks/{task_id}/complete", json={}, headers=headers)
    if response.status_code != 200:
        print(f"❌ 再次完成失败: {response.status_code} - {response.text}")
        return False

    result = response.json()["data"]
    points_awarded = result['completion_result']['points_awarded']
    reward_type = result['completion_result']['reward_type']
    message = result['completion_result']['message']

    print(f"✅ 再次完成结果:")
    print(f"   - 积分奖励: {points_awarded}")
    print(f"   - 奖励类型: {reward_type}")
    print(f"   - 消息: {message}")

    # 6. 判断防刷是否生效
    if points_awarded > 0:
        print(f"❌ 防刷机制失效！取消了完成之后还能再次获得积分")
        return False
    else:
        print(f"✅ 防刷机制生效，取消了完成之后不能再次获得积分")
        return True

if __name__ == "__main__":
    success = simple_anti_spam_test()
    exit(0 if success else 1)