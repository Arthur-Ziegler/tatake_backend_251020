#!/usr/bin/env python3
"""
测试聊天记录持久化功能
"""

import os
import sys
import uuid
import logging
from dotenv import load_dotenv

# 设置路径
sys.path.append('src')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

from langchain_core.messages import HumanMessage
from domains.chat.database import create_chat_checkpointer, create_memory_store
from domains.chat.graph import create_chat_graph
from domains.chat.service import ChatService

def test_sqlite_persistence():
    """测试SQLite聊天记录持久化"""
    print("💾 开始测试SQLite聊天记录持久化...")

    # 创建聊天服务
    chat_service = ChatService()

    # 创建会话
    user_id = "test-user-persistence"
    session_result = chat_service.create_session(user_id, "持久化测试会话")
    session_id = session_result["session_id"]

    print(f"✅ 创建会话成功: {session_id}")

    # 发送多条消息
    messages = [
        "你好",
        "请使用芝麻开门工具",
        "芝麻开门",
        "谢谢！"
    ]

    for i, message in enumerate(messages):
        print(f"\n📨 发送消息 {i+1}: {message}")
        result = chat_service.send_message(user_id, session_id, message)
        print(f"🤖 AI回复: {result['ai_response'][:100]}...")

    # 获取聊天历史
    print(f"\n📚 获取聊天历史...")
    history = chat_service.get_chat_history(user_id, session_id)

    print(f"✅ 历史记录获取成功，总共 {history['total_count']} 条消息:")
    for i, msg in enumerate(history["messages"]):
        print(f"  {i+1}. [{msg['type']}] {msg['content'][:50]}...")

    # 检查工具消息是否保存
    tool_messages = [msg for msg in history["messages"] if msg['type'] == 'tool']
    print(f"\n🔧 工具消息数量: {len(tool_messages)}")
    for tool_msg in tool_messages:
        print(f"   工具结果: {tool_msg['content']}")

    return len(tool_messages) > 0

def test_session_recovery():
    """测试会话恢复"""
    print(f"\n🔄 开始测试会话恢复...")

    # 创建新的聊天服务实例（模拟重启）
    new_chat_service = ChatService()

    user_id = "test-user-recovery"
    session_id = "test-session-recovery-123"

    # 尝试获取会话信息
    try:
        session_info = new_chat_service.get_session_info(user_id, session_id)
        print(f"✅ 会话恢复成功: {session_info['title']}")
        print(f"   消息数量: {session_info['message_count']}")
        return True
    except ValueError as e:
        print(f"❌ 会话恢复失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("聊天记录持久化测试")
    print("=" * 60)

    # 测试持久化
    persistence_ok = test_sqlite_persistence()

    # 测试会话恢复
    recovery_ok = test_session_recovery()

    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"  持久化功能: {'✅ 通过' if persistence_ok else '❌ 失败'}")
    print(f"  会话恢复功能: {'✅ 通过' if recovery_ok else '❌ 失败'}")
    print("=" * 60)