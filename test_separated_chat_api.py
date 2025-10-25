#!/usr/bin/env python3
"""
测试SeparatedChatService API，验证修复效果
"""

import logging
import requests
import sys
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def test_api():
    """测试API端点"""

    # API基础URL
    base_url = "http://localhost:8001"

    print("🧪 测试SeparatedChatService API")
    print("=" * 50)

    try:
        # 1. 创建会话
        print("1️⃣ 测试创建聊天会话...")
        create_session_url = f"{base_url}/chat/sessions"

        # 首先需要获取认证token
        print("🔐 获取认证token...")
        init_url = f"{base_url}/auth/guest/init"
        init_response = requests.post(init_url, json={})

        if init_response.status_code != 200:
            print(f"❌ 认证失败: {init_response.text}")
            return

        auth_data = init_response.json()
        token = auth_data["data"]["access_token"]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        session_response = requests.post(create_session_url,
                                         json={"title": "SeparatedChat测试会话"},
                                         headers=headers)

        if session_response.status_code != 200:
            print(f"❌ 创建会话失败: {session_response.text}")
            return

        session_data = session_response.json()
        session_id = session_data["data"]["session_id"]
        print(f"✅ 会话创建成功: session_id={session_id}")

        # 2. 发送消息
        print("\n2️⃣ 测试发送消息...")
        send_url = f"{base_url}/chat/sessions/{session_id}/send"

        message_response = requests.post(send_url,
                                         json={"message": "这是一条测试消息，验证SeparatedChatService是否修复了LangGraph类型错误"},
                                         headers=headers)

        print(f"📨 发送消息状态码: {message_response.status_code}")
        print(f"📄 响应内容: {message_response.text}")

        if message_response.status_code == 200:
            print("🎉 ✅ 消息发送成功！SeparatedChatService工作正常")
            message_data = message_response.json()
            print(f"📋 AI回复: {message_data['data']['ai_response']}")
        else:
            print(f"❌ 消息发送失败: {message_response.text}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()