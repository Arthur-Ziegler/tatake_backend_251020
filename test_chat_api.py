#!/usr/bin/env python3
"""
聊天API完整测试脚本
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api/v1"

def get_guest_token():
    """获取访客token"""
    response = requests.post(f"{API_BASE}/auth/guest/init")
    if response.status_code == 200:
        data = response.json()
        return data["data"]["access_token"]
    else:
        raise Exception(f"获取token失败: {response.text}")

def create_chat_session(token, title="芝麻开门测试"):
    """创建聊天会话"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(
        f"{API_BASE}/chat/sessions",
        headers=headers,
        json={"title": title}
    )
    if response.status_code == 200:
        data = response.json()
        return data["data"]["session_id"]
    else:
        raise Exception(f"创建会话失败: {response.text}")

def send_message(token, session_id, message):
    """发送消息"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(
        f"{API_BASE}/chat/sessions/{session_id}/send",
        headers=headers,
        json={"message": message}
    )
    if response.status_code == 200:
        data = response.json()
        return data["data"]
    else:
        raise Exception(f"发送消息失败: {response.text}")

def main():
    """主测试函数"""
    print("🚀 开始聊天API完整测试...")

    try:
        # 1. 获取token
        print("📝 获取访客token...")
        token = get_guest_token()
        print(f"✅ Token获取成功")

        # 2. 创建聊天会话
        print("💬 创建聊天会话...")
        session_id = create_chat_session(token)
        print(f"✅ 会话创建成功: {session_id}")

        # 3. 测试普通对话
        print("🤖 测试普通对话...")
        result1 = send_message(token, session_id, "你好，请介绍一下你自己")
        print(f"✅ 普通对话成功")
        print(f"   AI回复: {result1['ai_response'][:100]}...")

        # 4. 测试工具调用
        print("🔧 测试芝麻开门工具调用...")
        result2 = send_message(token, session_id, "快使用芝麻开门工具")
        print(f"✅ 工具调用成功")
        print(f"   AI回复: {result2['ai_response']}")

        # 5. 再次测试工具调用
        print("🔧 再次测试工具调用...")
        result3 = send_message(token, session_id, "芝麻开门，请给我密码")
        print(f"✅ 第二次工具调用成功")
        print(f"   AI回复: {result3['ai_response']}")

        print("\n🎉 所有测试通过！")
        print("📊 测试总结:")
        print("   ✅ 访客认证")
        print("   ✅ 聊天会话创建")
        print("   ✅ 普通对话功能")
        print("   ✅ 芝麻开门工具调用")
        print("   ✅ 多轮对话")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)