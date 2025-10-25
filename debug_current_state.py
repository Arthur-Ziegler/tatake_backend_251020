#!/usr/bin/env python3
"""
调试 current_state 数据，查找类型问题的源头
"""

import logging
from unittest.mock import patch, MagicMock
from src.domains.chat.service import ChatService
from src.domains.chat.database import ChatDatabaseManager
from langchain_core.messages import HumanMessage

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_current_state():
    """调试 current_state 数据"""

    print("🔍 调试 current_state 数据")
    print("=" * 50)

    # 创建ChatService实例
    chat_service = ChatService()

    # 模拟send_message中的参数
    user_id = "test-user-123"
    session_id = "test-session-456"
    message = "测试消息"

    print(f"📋 输入参数:")
    print(f"  user_id: {user_id} (类型: {type(user_id)})")
    print(f"  session_id: {session_id} (类型: {type(session_id)})")
    print(f"  message: {message} (类型: {type(message)})")
    print()

    # 创建配置
    config = chat_service._create_runnable_config(user_id, session_id)
    print(f"🔧 Config: {config}")
    print()

    # 创建用户消息
    user_message = HumanMessage(content=message.strip())
    print(f"💬 User Message: {user_message}")
    print(f"    content: {user_message.content} (类型: {type(user_message.content)})")
    print()

    # 创建当前状态 - 这是传递给LangGraph的数据
    current_state = {
        "user_id": user_id,
        "session_id": session_id,
        "session_title": "聊天会话",
        "messages": [user_message]
    }

    print("📊 Current State (传递给LangGraph的数据):")
    for key, value in current_state.items():
        print(f"  {key}: {value} (类型: {type(value)})")
        if isinstance(value, list) and value:
            print(f"    列表内容: {value[0]} (类型: {type(value[0])})")
    print()

    # 检查是否有隐藏的类型问题
    print("🔍 深入检查数据:")

    # 检查字符串ID是否可能被LangGraph误解
    import uuid
    try:
        uuid.UUID(user_id)
        print(f"  ✅ user_id是有效的UUID格式")
    except ValueError:
        print(f"  ⚠️  user_id不是标准UUID格式: {user_id}")

    try:
        uuid.UUID(session_id)
        print(f"  ✅ session_id是有效的UUID格式")
    except ValueError:
        print(f"  ⚠️  session_id不是标准UUID格式: {session_id}")

    print()
    print("💡 可能的问题源头:")
    print("1. LangGraph可能在内部处理这些UUID字符串时产生问题")
    print("2. 某些channel可能从字符串ID派生出版本号")
    print("3. LangGraph的状态管理机制可能有问题")
    print()

    # 模拟LangGraph内部可能发生的情况
    print("🧪 模拟LangGraph内部处理:")

    # LangGraph可能会对某些字段进行处理
    simulated_channel_versions = {}

    # 模拟LangGraph可能的行为
    for key, value in current_state.items():
        if isinstance(value, str) and len(value) == 36:  # UUID长度
            # LangGraph可能基于UUID生成版本号
            hash_version = abs(hash(value)) % 1000000
            simulated_channel_versions[key] = str(hash_version)  # 注意：这里变成了字符串！
            print(f"  {key}: UUID -> 可能生成字符串版本号: {simulated_channel_versions[key]}")
        else:
            simulated_channel_versions[key] = 1
            print(f"  {key}: 默认版本号: 1")

    print()
    print("🚨 这就是问题所在！")
    print("LangGraph内部可能将某些版本号生成为字符串，")
    print("然后在比较时与现有的整数版本号冲突。")

if __name__ == "__main__":
    debug_current_state()