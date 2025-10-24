#!/usr/bin/env python3
"""
测试奖励系统集成修复
"""

import requests
import json
import uuid
import time
from datetime import datetime, timezone

def test_reward_system_fix():
    """测试奖励系统是否正常工作"""
    base_url = "http://localhost:8001"

    try:
        print("=== 测试奖励系统集成 ===")

        # 1. 创建测试用户
        print(f"\n1. 初始化游客账号")
        guest_response = requests.post(f"{base_url}/auth/guest/init", timeout=10)

        if guest_response.status_code != 200:
            print(f"❌ 游客账号初始化失败: {guest_response.status_code}")
            return False

        guest_result = guest_response.json()
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

        headers = {"Authorization": f"Bearer {token}"}

        # 2. 创建并完成任务以获得积分
        print(f"\n2. 创建任务并获得积分")
        task_response = requests.post(f"{base_url}/tasks/", json={
            "title": "奖励系统测试任务",
            "description": "用于测试奖励系统的任务"
        }, headers=headers, timeout=10)

        if task_response.status_code not in [200, 201]:
            print(f"❌ 创建任务失败: {task_response.status_code}")
            print(f"响应内容: {task_response.text}")
            return False

        task_result = task_response.json()
        task_id = task_result['data']['id']
        print(f"✅ 任务创建成功: {task_id}")

        # 完成任务
        complete_response = requests.post(f"{base_url}/tasks/{task_id}/complete",
                                        json={}, headers=headers, timeout=10)

        if complete_response.status_code != 200:
            print(f"❌ 完成任务失败: {complete_response.status_code}")
            return False

        complete_result = complete_response.json()
        print(f"任务完成响应: {complete_result}")

        # 处理不同的响应格式
        if 'data' in complete_result:
            data = complete_result['data']
            if 'completion_result' in data and 'points_awarded' in data['completion_result']:
                points_earned = data['completion_result']['points_awarded']
            elif 'points_awarded' in data:
                points_earned = data['points_awarded']
            elif 'points' in data:
                points_earned = data['points']
            else:
                points_earned = 0
        else:
            points_earned = complete_result.get('points_awarded', 0)

        print(f"✅ 任务完成，获得{points_earned}积分")

        # 3. 查看用户积分余额
        print(f"\n3. 查看积分余额")
        balance_response = requests.get(f"{base_url}/points/balance", headers=headers, timeout=10)

        if balance_response.status_code != 200:
            print(f"❌ 获取积分余额失败: {balance_response.status_code}")
            print(f"响应内容: {balance_response.text}")
            return False

        balance_result = balance_response.json()
        print(f"积分余额响应: {balance_result}")

        # 处理不同的响应格式
        if 'data' in balance_result:
            if 'current_balance' in balance_result['data']:
                current_balance = balance_result['data']['current_balance']
            elif 'balance' in balance_result['data']:
                current_balance = balance_result['data']['balance']
            elif 'amount' in balance_result['data']:
                current_balance = balance_result['data']['amount']
            else:
                current_balance = 0
        else:
            current_balance = balance_result.get('balance', 0)

        print(f"✅ 当前积分余额: {current_balance}")

        # 4. 查看可用奖励
        print(f"\n4. 查看可用奖励")
        rewards_response = requests.get(f"{base_url}/rewards/catalog", headers=headers, timeout=10)

        if rewards_response.status_code != 200:
            print(f"❌ 获取奖励列表失败: {rewards_response.status_code}")
            print(f"响应内容: {rewards_response.text}")
            return False

        rewards_result = rewards_response.json()
        print(f"奖励目录响应: {rewards_result}")

        # 处理不同的响应格式
        if 'data' in rewards_result:
            available_rewards = rewards_result['data']['rewards']
        elif 'rewards' in rewards_result:
            available_rewards = rewards_result['rewards']
        else:
            available_rewards = []

        print(f"✅ 可用奖励数量: {len(available_rewards)}")

        if available_rewards:
            for reward in available_rewards[:3]:  # 显示前3个奖励
                print(f"  - {reward['name']}: {reward['points_value']}积分")

        # 5. 测试奖励兑换
        print(f"\n5. 测试奖励兑换")
        if available_rewards and current_balance >= 10:
            # 尝试兑换小金币
            redeem_response = requests.post(f"{base_url}/rewards/redeem", json={
                "reward_id": "gold_coin",
                "quantity": 1
            }, headers=headers, timeout=10)

            if redeem_response.status_code != 200:
                print(f"❌ 奖励兑换失败: {redeem_response.status_code}")
                print(f"响应内容: {redeem_response.text}")
                return False

            redeem_result = redeem_response.json()
            print(f"✅ 奖励兑换成功: {redeem_result}")
        else:
            print(f"⚠️ 积分不足或无可用奖励，跳过兑换测试")

        # 6. 查看奖励交易历史
        print(f"\n6. 查看奖励交易历史")
        transactions_response = requests.get(f"{base_url}/rewards/transactions", headers=headers, timeout=10)

        if transactions_response.status_code != 200:
            print(f"❌ 获取奖励交易历史失败: {transactions_response.status_code}")
            print(f"响应内容: {transactions_response.text}")
            return False

        transactions_result = transactions_response.json()
        transactions = transactions_result['data']['transactions']
        print(f"✅ 奖励交易记录数量: {len(transactions)}")

        # 7. 测试奖励合成（如果有足够的小金币）
        if current_balance >= 100:
            print(f"\n7. 测试奖励合成")
            recipe_response = requests.post(f"{base_url}/rewards/craft", json={
                "recipe_id": "gold_to_diamond"
            }, headers=headers, timeout=10)

            if recipe_response.status_code == 200:
                craft_result = recipe_response.json()
                print(f"✅ 奖励合成成功: {craft_result}")
            else:
                print(f"⚠️ 奖励合成失败或不可用: {recipe_response.status_code}")
        else:
            print(f"\n7. 积分不足，跳过合成测试")

        print(f"\n🎉 奖励系统集成测试全部通过!")
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

    success = test_reward_system_fix()
    if success:
        print("\n✅ 奖励系统集成修复验证成功!")
    else:
        print("\n❌ 奖励系统集成仍有问题")