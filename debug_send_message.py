#!/usr/bin/env python3
"""
调试消息发送时的类型问题

专门调试send_message过程中的channel_versions类型不匹配问题。
"""

import sys
import os
sys.path.append('.')

from src.domains.chat.service import ChatService
from src.domains.chat.database import create_chat_checkpointer
from src.domains.chat.graph import create_chat_graph

def debug_send_message_types():
    """调试消息发送时的类型问题"""
    print("🔍 开始调试消息发送类型问题")

    # 删除现有数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建聊天服务实例
    service = ChatService()

    try:
        # 1. 创建会话
        print("\n1️⃣ 创建会话...")
        session_result = service.create_session('test-user', '调试消息发送')
        session_id = session_result['session_id']
        print(f"✅ 会话创建成功: {session_id}")

        # 2. 手动测试图调用（模拟send_message过程）
        print("\n2️⃣ 手动测试图调用...")

        from langchain_core.messages import HumanMessage
        user_message = HumanMessage(content="你好，这是一个测试消息")

        # 创建当前状态
        current_state = {
            "user_id": "test-user",
            "session_id": session_id,
            "session_title": "调试消息发送",
            "messages": [user_message]
        }

        print(f"  当前状态类型: {type(current_state)}")
        for key, value in current_state.items():
            print(f"    {key}: {value} (类型: {type(value)})")

        # 创建配置
        config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
        print(f"  配置: {config}")

        # 使用checkpointer创建图并调用
        print("\n3️⃣ 创建图并调用invoke...")
        from src.domains.chat.database import create_memory_store
        store = create_memory_store()

        with create_chat_checkpointer() as checkpointer:
            graph = create_chat_graph(checkpointer, store)

            print("  开始图调用...")
            try:
                result = graph.graph.invoke(current_state, config)
                print(f"  ✅ 图调用成功")
                print(f"  结果类型: {type(result)}")
                print(f"  结果键: {list(result.keys())}")

            except Exception as e:
                print(f"  ❌ 图调用失败: {e}")
                import traceback
                traceback.print_exc()

                # 分析具体是哪个类型不匹配
                print(f"\n  🔍 分析类型不匹配...")

                # 检查现有的checkpoint
                retrieved = checkpointer.get(config)
                if retrieved and hasattr(retrieved, 'channel_versions'):
                    print(f"  现有channel_versions: {retrieved.channel_versions}")
                    for key, value in retrieved.channel_versions.items():
                        print(f"    {key}: {value} (类型: {type(value)})")

                # 检查当前状态的版本号
                print(f"  当前状态没有channel_versions字段")

    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_send_message_types()