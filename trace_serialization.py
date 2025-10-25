#!/usr/bin/env python3
"""
追踪序列化过程中的类型转换

专门追踪int到str的转换过程
"""

import sys
import os
sys.path.append('.')

def trace_checkpoint_lifecycle():
    """追踪checkpoint的完整生命周期"""
    print("🔍 追踪checkpoint生命周期...")

    from src.domains.chat.database import create_chat_checkpointer
    import msgpack

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建checkpointer
    with create_chat_checkpointer() as checkpointer:
        config = {"configurable": {"thread_id": "trace-test", "checkpoint_ns": ""}}

        # 创建原始checkpoint - 严格使用int
        original_checkpoint = {
            "v": 1,
            "ts": 0,
            "id": "trace-checkpoint",
            "channel_values": {"messages": []},
            "channel_versions": {"messages": 1},  # 明确的int
            "versions_seen": {},
            "pending_sends": []
        }

        print("1️⃣ 原始checkpoint:")
        print(f"   channel_versions.messages: {original_checkpoint['channel_versions']['messages']} (类型: {type(original_checkpoint['channel_versions']['messages'])})")

        # 存储checkpoint
        checkpointer.put(config, original_checkpoint, {}, {})
        print("2️⃣ 存储成功")

        # 立即检索
        retrieved = checkpointer.get(config)
        print("3️⃣ 检索成功")

        if retrieved and isinstance(retrieved, dict):
            if "channel_versions" in retrieved:
                value = retrieved["channel_versions"]["messages"]
                print(f"   检索到的channel_versions.messages: {value} (类型: {type(value)})")

                if isinstance(value, str):
                    print(f"   ❌ 问题出现！int被转换为str")
                else:
                    print(f"   ✅ 类型保持正确")

        # 检查数据库原始数据
        print("4️⃣ 检查数据库原始数据...")
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT checkpoint FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1")
        row = cursor.fetchone()

        if row:
            checkpoint_blob = row[0]

            # 手动解码msgpack
            try:
                decoded = msgpack.unpackb(checkpoint_blob, raw=False, strict_map_key=False)
                print(f"   MsgPack解码成功")

                if "channel_versions" in decoded:
                    msgpack_value = decoded["channel_versions"]["messages"]
                    print(f"   MsgPack中的channel_versions.messages: {msgpack_value} (类型: {type(msgpack_value)})")

                    if isinstance(msgpack_value, str):
                        print(f"   ❌ MsgPack存储时已经是字符串！")
                    elif isinstance(msgpack_value, int):
                        print(f"   ✅ MsgPack正确存储为整数")
                        # 问题可能在SqliteSaver的检索过程中
                        print(f"   🔍 问题可能在SqliteSaver的检索过程中...")

            except Exception as e:
                print(f"   MsgPack解码失败: {e}")

        conn.close()

def test_different_initialization():
    """测试不同的初始化方式"""
    print(f"\n🧪 测试不同初始化方式...")

    # 方式1: 直接创建状态并调用图
    from src.domains.chat.models import create_chat_state
    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 创建状态
    state = create_chat_state('test-user', 'test-session', '测试会话')
    state['messages'] = [HumanMessage(content="测试")]

    print("方式1: 直接创建图并调用")

    with create_chat_checkpointer() as checkpointer:
        store = create_memory_store()
        graph = create_chat_graph(checkpointer, store)
        config = {"configurable": {"thread_id": state['session_id'], "checkpoint_ns": ""}}

        try:
            # 调用图前检查初始状态
            snapshot = graph.graph.get_state(config)
            print(f"   初始状态类型: {type(snapshot)}")
            if hasattr(snapshot, 'values') and isinstance(snapshot.values, dict):
                if "channel_versions" in snapshot.values:
                    cv = snapshot.values["channel_versions"]
                    print(f"   初始channel_versions: {cv}")
                    if isinstance(cv, dict):
                        for k, v in cv.items():
                            print(f"     {k}: {v} (类型: {type(v)})")

            # 调用图
            result = graph.graph.invoke(state, config)
            print(f"   ✅ 图调用成功")

        except Exception as e:
            print(f"   ❌ 图调用失败: {e}")

            # 检查调用后的状态
            try:
                snapshot = graph.graph.get_state(config)
                if hasattr(snapshot, 'values') and isinstance(snapshot.values, dict):
                    if "channel_versions" in snapshot.values:
                        cv = snapshot.values["channel_versions"]
                        print(f"   调用后channel_versions: {cv}")
                        if isinstance(cv, dict):
                            for k, v in cv.items():
                                print(f"     {k}: {v} (类型: {type(v)})")
                                if isinstance(v, str):
                                    print(f"       ❌ 图调用后类型变为字符串！")
            except Exception as e2:
                print(f"   获取调用后状态失败: {e2}")

def test_service_creation():
    """测试通过服务创建的方式"""
    print(f"\n🧪 测试服务创建方式...")

    from src.domains.chat.service import ChatService

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    service = ChatService()

    try:
        # 创建会话
        session_result = service.create_session('test-user', '测试会话')
        session_id = session_result['session_id']
        print(f"   会话创建成功: {session_id}")

        # 检查创建后的checkpoint状态
        with service.db_manager.create_checkpointer() as checkpointer:
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            checkpoint = checkpointer.get(config)

            if checkpoint and isinstance(checkpoint, dict):
                if "channel_versions" in checkpoint:
                    cv = checkpoint["channel_versions"]
                    print(f"   会话创建后channel_versions: {cv}")
                    for k, v in cv.items():
                        print(f"     {k}: {v} (类型: {type(v)})")
                        if isinstance(v, str):
                            print(f"       ❌ 会话创建时类型已经错误！")

    except Exception as e:
        print(f"   ❌ 服务测试失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 追踪序列化过程中的类型转换")
    print("=" * 60)

    trace_checkpoint_lifecycle()
    test_different_initialization()
    test_service_creation()

    print("\n" + "=" * 60)
    print("🎯 追踪结论:")
    print("1. 确定类型转换的确切时间点")
    print("2. 找到导致转换的具体操作")
    print("3. 为修复提供精确的位置")
    print("=" * 60)