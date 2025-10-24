#!/usr/bin/env python3
"""
测试Top3任务API修复
"""

import requests
import json
import uuid
import time

def test_top3_api_fix():
    """测试Top3任务API是否正常工作"""
    base_url = "http://localhost:8001"

    try:
        print("=== 测试Top3任务API ===")

        # 1. 创建测试用户（游客模式）
        print(f"\n1. 初始化游客账号")
        guest_response = requests.post(f"{base_url}/auth/guest/init", timeout=10)

        if guest_response.status_code != 200:
            print(f"❌ 游客账号初始化失败: {guest_response.status_code}")
            print(f"响应内容: {guest_response.text}")
            return False

        guest_result = guest_response.json()
        print(f"游客初始化响应: {guest_result}")

        if guest_result.get('code') != 200:
            print(f"❌ 游客账号初始化业务失败: {guest_result}")
            return False

        data = guest_result.get('data', {})
        token = data.get('token') or data.get('access_token')
        user_id = data.get('user_id') or data.get('id')

        if not token:
            print(f"❌ 游客初始化响应中没有token")
            return False

        print(f"✅ 游客账号初始化成功: user_id={user_id}")

        # 2. 创建Top3任务
        headers = {"Authorization": f"Bearer {token}"}

        print(f"\n2. 创建Top3任务")
        task_data = {
            "title": "Top3测试任务",
            "description": "这是一个Top3任务测试",
            "priority": "high"
        }

        create_response = requests.post(f"{base_url}/tasks/", json=task_data, headers=headers, timeout=10)

        if create_response.status_code != 200:
            print(f"❌ 创建Top3任务失败: {create_response.status_code}")
            print(f"响应内容: {create_response.text}")
            return False

        create_result = create_response.json()
        task_id = create_result.get('id')
        print(f"✅ Top3任务创建成功: task_id={task_id}")

        # 3. 测试Top3任务列表
        print(f"\n3. 获取Top3任务列表")
        list_response = requests.get(f"{base_url}/tasks/top3", headers=headers, timeout=10)

        if list_response.status_code != 200:
            print(f"❌ 获取Top3任务列表失败: {list_response.status_code}")
            print(f"响应内容: {list_response.text}")
            return False

        list_result = list_response.json()
        print(f"✅ Top3任务列表获取成功: {len(list_result.get('tasks', []))}个任务")

        # 4. 测试Top3任务完成
        print(f"\n4. 完成Top3任务")
        complete_response = requests.post(f"{base_url}/tasks/{task_id}/complete", headers=headers, timeout=10)

        if complete_response.status_code != 200:
            print(f"❌ 完成Top3任务失败: {complete_response.status_code}")
            print(f"响应内容: {complete_response.text}")
            return False

        complete_result = complete_response.json()
        print(f"✅ Top3任务完成成功: {complete_result}")

        # 5. 测试Top3抽奖功能
        print(f"\n5. 测试Top3抽奖功能")
        lottery_response = requests.post(f"{base_url}/top3/lottery", headers=headers, timeout=10)

        if lottery_response.status_code != 200:
            print(f"❌ Top3抽奖失败: {lottery_response.status_code}")
            print(f"响应内容: {lottery_response.text}")
            return False

        lottery_result = lottery_response.json()
        print(f"✅ Top3抽奖成功: {lottery_result}")

        # 6. 测试Top3排行榜
        print(f"\n6. 测试Top3排行榜")
        leaderboard_response = requests.get(f"{base_url}/top3/leaderboard", headers=headers, timeout=10)

        if leaderboard_response.status_code != 200:
            print(f"❌ 获取Top3排行榜失败: {leaderboard_response.status_code}")
            print(f"响应内容: {leaderboard_response.text}")
            return False

        leaderboard_result = leaderboard_response.json()
        print(f"✅ Top3排行榜获取成功: {leaderboard_result}")

        print(f"\n🎉 Top3任务API测试全部通过!")
        return True

    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: API服务器未启动或不可访问")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 等待服务器启动
    print("等待API服务器启动...")
    time.sleep(2)

    success = test_top3_api_fix()
    if success:
        print("\n✅ Top3任务API修复验证成功!")
    else:
        print("\n❌ Top3任务API仍有问题")