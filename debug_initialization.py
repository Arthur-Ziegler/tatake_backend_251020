#!/usr/bin/env python3
"""
调试初始化过程中的类型问题

专门检查数据库初始化和会话创建过程中的类型转换
"""

import sys
import os
sys.path.append('.')

def debug_initialization_process():
    """调试初始化过程"""
    print("🔍 调试初始化过程...")

    from src.domains.chat.service import ChatService

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 1. 检查服务初始化
    print("1️⃣ 创建ChatService...")
    service = ChatService()
    print("✅ ChatService创建成功")

    # 2. 检查数据库初始化
    print("2️⃣ 检查数据库初始化...")
    try:
        service._ensure_database_initialized()
        print("✅ 数据库初始化成功")

        # 检查初始化后的checkpoint
        with service.db_manager.create_checkpointer() as checkpointer:
            config = {"configurable": {"thread_id": "__db_init__", "checkpoint_ns": ""}}
            checkpoint = checkpointer.get(config)
            if checkpoint and isinstance(checkpoint, dict):
                if "channel_versions" in checkpoint:
                    cv = checkpoint["channel_versions"]
                    print(f"   初始化后channel_versions: {cv}")
                    for k, v in cv.items():
                        print(f"     {k}: {v} (类型: {type(v)})")
                        if isinstance(v, str):
                            print(f"       ❌ 初始化时就出现类型错误！")

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")

    # 3. 检查会话创建
    print("3️⃣ 检查会话创建...")
    try:
        session_result = service.create_session('test-user', '测试会话')
        session_id = session_result['session_id']
        print(f"✅ 会话创建成功: {session_id}")

        # 检查会话创建后的checkpoint
        with service.db_manager.create_checkpointer() as checkpointer:
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            checkpoint = checkpointer.get(config)
            if checkpoint and isinstance(checkpoint, dict):
                if "channel_versions" in checkpoint:
                    cv = checkpoint["channel_versions"]
                    print(f"   会话后channel_versions: {cv}")
                    for k, v in cv.items():
                        print(f"     {k}: {v} (类型: {type(v)})")
                        if isinstance(v, str):
                            print(f"       ❌ 会话创建时出现类型错误！")

    except Exception as e:
        print(f"❌ 会话创建失败: {e}")

    # 4. 检查第一次消息发送前的状态
    print("4️⃣ 检查消息发送前状态...")
    try:
        session_id = session_result['session_id']

        # 创建消息状态
        from src.domains.chat.models import create_chat_state
        from langchain_core.messages import HumanMessage

        current_state = create_chat_state('test-user', session_id, '测试会话')
        current_state['messages'] = [HumanMessage(content='测试消息')]

        print(f"   创建的状态: {list(current_state.keys())}")
        print(f"   状态是否包含channel_versions: {'channel_versions' in current_state}")

        # 检查图的初始状态
        config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

        with service.db_manager.create_checkpointer() as checkpointer:
            from src.domains.chat.graph import create_chat_graph
            from src.domains.chat.database import create_memory_store

            store = create_memory_store()
            graph = create_chat_graph(checkpointer, store)

            # 检查图的当前状态
            try:
                snapshot = graph.graph.get_state(config)
                if hasattr(snapshot, 'values') and isinstance(snapshot.values, dict):
                    if "channel_versions" in snapshot.values:
                        cv = snapshot.values["channel_versions"]
                        print(f"   图当前channel_versions: {cv}")
                        for k, v in cv.items():
                            print(f"     {k}: {v} (类型: {type(v)})")
                            if isinstance(v, str):
                                print(f"       ❌ 图状态中已有类型错误！")
                    else:
                        print(f"   图状态中没有channel_versions")
                else:
                    print(f"   图状态values不是dict或无values")

            except Exception as e:
                print(f"   获取图状态失败: {e}")

    except Exception as e:
        print(f"❌ 消息发送前检查失败: {e}")

def debug_langgraph_internal():
    """调试LangGraph内部行为"""
    print(f"\n🔍 调试LangGraph内部行为...")

    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    with create_chat_checkpointer() as checkpointer:
        store = create_memory_store()
        graph = create_chat_graph(checkpointer, store)

        session_id = "debug-session"
        config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

        # 创建状态
        state = create_chat_state('test-user', session_id, '调试会话')
        state['messages'] = [HumanMessage(content='调试消息')]

        print("1. 调用图前的状态检查...")
        try:
            snapshot = graph.graph.get_state(config)
            print(f"   图状态类型: {type(snapshot)}")
        except Exception as e:
            print(f"   获取初始状态失败: {e}")

        print("2. 尝试图调用...")
        try:
            # 这里应该触发错误
            result = graph.graph.invoke(state, config)
            print("✅ 图调用成功")
        except Exception as e:
            print(f"❌ 图调用失败: {e}")

            # 立即检查checkpoint状态
            checkpoint = checkpointer.get(config)
            if checkpoint and isinstance(checkpoint, dict):
                if "channel_versions" in checkpoint:
                    cv = checkpoint["channel_versions"]
                    print(f"   失败后checkpoint: {cv}")
                    for k, v in cv.items():
                        print(f"     {k}: {v} (类型: {type(v)})")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 调试初始化过程中的类型问题")
    print("=" * 60)

    debug_initialization_process()
    debug_langgraph_internal()

    print("\n" + "=" * 60)
    print("🎯 调试结论:")
    print("1. 确定类型转换的确切时间点")
    print("2. 找到问题的根源")
    print("3. 提供修复方向")
    print("=" * 60)