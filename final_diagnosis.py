#!/usr/bin/env python3
"""
最终诊断 - 确定问题的确切根源

专门分析为什么ChatService会创建错误的checkpoint类型
"""

import sys
import os
sys.path.append('.')

def compare_working_vs_broken():
    """比较工作的图调用 vs 失败的ChatService调用"""
    print("🔍 比较工作 vs 失败的调用...")

    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    session_id = "comparison-test"
    config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

    # 1. 工作的方式：直接创建图和checkpoint
    print("1️⃣ 工作的方式（直接创建）:")
    try:
        with create_chat_checkpointer() as checkpointer:
            store = create_memory_store()
            graph = create_chat_graph(checkpointer, store)

            state = create_chat_state('test-user', session_id, '测试会话')
            state['messages'] = [HumanMessage(content='工作测试')]

            # 检查调用前的checkpoint
            pre_checkpoint = checkpointer.get(config)
            if pre_checkpoint and isinstance(pre_checkpoint, dict):
                if "channel_versions" in pre_checkpoint:
                    cv = pre_checkpoint["channel_versions"]
                    print(f"   调用前channel_versions: {cv}")
                    for k, v in cv.items():
                        print(f"     {k}: {v} ({type(v)})")

            result = graph.graph.invoke(state, config)
            print("   ✅ 直接创建成功")

    except Exception as e:
        print(f"   ❌ 直接创建失败: {e}")

    # 2. 失败的方式：模拟ChatService
    print("\n2️⃣ 失败的方式（模拟ChatService）:")
    try:
        from src.domains.chat.service import ChatService

        service = ChatService()

        # 创建会话（这会创建初始checkpoint）
        session_result = service.create_session('test-user', '模拟测试')
        test_session_id = session_result['session_id']
        test_config = {"configurable": {"thread_id": test_session_id, "checkpoint_ns": ""}}

        # 检查会话创建后的checkpoint
        with service.db_manager.create_checkpointer() as checkpointer:
            post_session_checkpoint = checkpointer.get(test_config)
            if post_session_checkpoint and isinstance(post_session_checkpoint, dict):
                if "channel_versions" in post_session_checkpoint:
                    cv = post_session_checkpoint["channel_versions"]
                    print(f"   会话后channel_versions: {cv}")
                    for k, v in cv.items():
                        print(f"     {k}: {v} ({type(v)})")
                        if isinstance(v, str):
                            print(f"       ❌ 会话创建时就已出现字符串类型！")

        # 现在尝试发送消息
        result = service.send_message('test-user', test_session_id, '模拟测试消息')
        print("   ✅ 模拟ChatService成功")

    except Exception as e:
        print(f"   ❌ 模拟ChatService失败: {e}")

def check_session_creation_impact():
    """检查会话创建对checkpoint类型的影响"""
    print(f"\n🔍 检查会话创建影响...")

    from src.domains.chat.database import create_chat_checkpointer

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 手动创建checkpoint，模拟会话创建
    with create_chat_checkpointer() as checkpointer:
        session_id = "session-impact-test"
        config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

        # 创建初始checkpoint
        initial_checkpoint = {
            "v": 1,
            "ts": 0,
            "id": "initial-checkpoint",
            "channel_values": {"messages": []},
            "channel_versions": {"messages": 1},  # 明确int
            "versions_seen": {},
            "pending_sends": []
        }

        checkpointer.put(config, initial_checkpoint, {}, {})

        # 检查初始checkpoint
        checkpoint1 = checkpointer.get(config)
        if checkpoint1 and isinstance(checkpoint1, dict):
            if "channel_versions" in checkpoint1:
                cv = checkpoint1["channel_versions"]
                print(f"初始checkpoint: {cv}")
                for k, v in cv.items():
                    print(f"  {k}: {v} ({type(v)})")

        # 现在创建第二个checkpoint，模拟会话创建
        session_checkpoint = {
            "v": 1,
            "ts": 1,
            "id": "session-checkpoint",
            "channel_values": {
                "user_id": "test-user",
                "session_id": session_id,
                "session_title": "测试会话",
                "created_at": "2025-10-25T13:56:00+00:00",
                "messages": []
            },
            "channel_versions": {"messages": 1},  # 明确int
            "versions_seen": {},
            "pending_sends": []
        }

        checkpointer.put(config, session_checkpoint, {}, {})

        # 检查会话checkpoint
        checkpoint2 = checkpointer.get(config)
        if checkpoint2 and isinstance(checkpoint2, dict):
            if "channel_versions" in checkpoint2:
                cv = checkpoint2["channel_versions"]
                print(f"会话checkpoint: {cv}")
                for k, v in cv.items():
                    print(f"  {k}: {v} ({type(v)})")
                    if isinstance(v, str):
                        print(f"    ❌ 会话checkpoint中出现字符串类型！")

        # 检查最终的checkpoint状态
        final_checkpoint = checkpointer.get(config)
        if final_checkpoint and isinstance(final_checkpoint, dict):
            print(f"最终checkpoint完整结构:")
            for key, value in final_checkpoint.items():
                if key == "channel_versions":
                    print(f"  {key}: {value}")
                    for ck, cv in value.items():
                        print(f"    {ck}: {cv} ({type(cv)})")
                else:
                    print(f"  {key}: {type(value)}")

def trace_exact_conversion_point():
    """追踪确切的转换点"""
    print(f"\n🔍 追踪确切转换点...")

    # 这里我们需要查看ChatService的_create_session_record_directly方法
    # 是否在某个地方有类型转换

    from src.domains.chat.service import ChatService

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    service = ChatService()

    # 在会话创建前后检查数据库
    print("会话创建前数据库状态:")
    if os.path.exists(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        count = cursor.fetchone()[0]
        print(f"  checkpoint数量: {count}")
        conn.close()

    # 创建会话
    session_result = service.create_session('test-user', '转换点测试')
    session_id = session_result['session_id']

    print("会话创建后数据库状态:")
    if os.path.exists(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        count = cursor.fetchone()[0]
        print(f"  checkpoint数量: {count}")

        if count > 0:
            cursor.execute("SELECT checkpoint FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                checkpoint_blob = row[0]
                print(f"  最新checkpoint长度: {len(checkpoint_blob)} 字节")

                # 尝试手动解码
                try:
                    import msgpack
                    decoded = msgpack.unpackb(checkpoint_blob, raw=False)
                    if "channel_versions" in decoded:
                        cv = decoded["channel_versions"]
                        print(f"  解码后的channel_versions: {cv}")
                        for k, v in cv.items():
                            print(f"    {k}: {v} ({type(v)})")
                            if isinstance(v, str):
                                print(f"      ❌ 数据库中已经是字符串！")
                except Exception as e:
                    print(f"  解码失败: {e}")

        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 最终诊断 - 确定问题的确切根源")
    print("=" * 60)

    compare_working_vs_broken()
    check_session_creation_impact()
    trace_exact_conversion_point()

    print("\n" + "=" * 60)
    print("🎯 最终诊断结论:")
    print("1. 确定问题的确切来源")
    print("2. 找到类型转换的根本原因")
    print("3. 提供最终的解决方案")
    print("=" * 60)