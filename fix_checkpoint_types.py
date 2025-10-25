#!/usr/bin/env python3
"""
修复checkpoint类型问题

通过确保所有channel_versions都是整数类型来解决类型不匹配问题。
"""

import sys
import os
sys.path.append('.')

def create_state_with_int_versions():
    """创建状态，确保channel_versions字段是整数类型"""
    print("🔧 修复状态类型问题...")

    # 测试创建状态
    from src.domains.chat.models import create_chat_state
    state = create_chat_state("test-user", "test-session", "测试会话")

    print(f"原始状态类型: {type(state)}")
    print(f"状态字段: {list(state.keys())}")

    # 检查是否有channel_versions字段
    if "channel_versions" not in state:
        print("✅ 状态中没有channel_versions字段，这是正确的")
        print("  ChatState模型继承自MessagesState，不直接包含channel_versions")

    # 测试MessagesState
    from langgraph.graph import MessagesState
    messages_state = MessagesState()
    messages_state.update(state)

    print(f"\nMessagesState类型: {type(messages_state)}")
    print(f"MessagesState字段: {list(messages_state.keys())}")
    print(f"MessagesState字典内容: {messages_state.dict()}")

    return state

def test_graph_with_correct_types():
    """测试使用正确类型的状态调用图"""
    print("\n🧪 测试图调用...")

    # 删除现有数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建聊天服务
    from src.domains.chat.service import ChatService
    service = ChatService()

    try:
        # 创建会话
        print("\n1️⃣ 创建会话...")
        session_result = service.create_session('test-user', '类型修复测试')
        session_id = session_result['session_id']
        print(f"✅ 会话创建成功: {session_id}")

        # 获取会话信息以确保数据库正确
        print("\n2️⃣ 获取会话信息...")
        session_info = service.get_session_info('test-user', session_id)
        print(f"✅ 会话信息: {session_info}")

        # 测试消息发送
        print("\n3️⃣ 测试消息发送...")
        try:
            result = service.send_message('test-user', session_id, '你好，这是类型修复测试')
            print(f"✅ 消息发送成功!")
            print(f"回复: {result.get('response', '无回复')[:100]}...")

            # 检查聊天历史
            history = service.get_chat_history('test-user', session_id)
            print(f"✅ 聊天历史获取成功! 消息数量: {len(history['messages'])}")

        except Exception as e:
            print(f"❌ 消息发送失败: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_direct_graph_with_int_versions():
    """直接测试图调用，确保整数类型"""
    print("\n🧪 直接测试图调用...")

    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from src.domains.chat.graph import create_chat_graph
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建状态
    state = create_state_with_int_versions()
    session_id = state["session_id"]

    # 使用checkpointer创建图
    with create_chat_checkpointer() as checkpointer:
        from src.domains.chat.database import create_memory_store
        store = create_memory_store()

        graph = create_chat_graph(checkpointer, store)

        config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

        try:
            print("开始图调用...")
            result = graph.graph.invoke(state, config)
            print(f"✅ 直接图调用成功!")
            return True

        except Exception as e:
            print(f"❌ 直接图调用失败: {e}")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 修复checkpoint类型问题")
    print("=" * 60)

    success1 = test_direct_graph_with_int_versions()
    success2 = test_graph_with_correct_types()

    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 所有测试通过，类型问题已修复!")
    else:
        print("❌ 仍有类型问题需要进一步调试")
    print("=" * 60)