#!/usr/bin/env python3
"""
调试checkpoint类型问题

这个脚本用于调试LangGraph中的channel_versions类型不匹配问题。
"""

import sys
import os
sys.path.append('.')

from src.domains.chat.service import ChatService
from src.domains.chat.database import create_chat_checkpointer
from src.domains.chat.models import create_chat_state

def debug_checkpoint_types():
    """调试checkpoint中的类型问题"""
    print("🔍 开始调试checkpoint类型问题")

    # 删除现有数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建聊天服务实例
    service = ChatService()

    try:
        # 1. 创建会话（这会初始化数据库）
        print("\n1️⃣ 测试会话创建...")
        session_result = service.create_session('test-user', '调试测试')
        session_id = session_result['session_id']
        print(f"✅ 会话创建成功: {session_id}")

        # 2. 检查数据库中的checkpoint数据结构
        print("\n2️⃣ 检查数据库中的checkpoint...")
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 查询所有checkpoint记录
        cursor.execute("SELECT checkpoint_id, checkpoint FROM checkpoints ORDER BY checkpoint_id")
        rows = cursor.fetchall()

        print(f"数据库中找到 {len(rows)} 个checkpoint记录:")
        for i, (checkpoint_id, checkpoint_blob) in enumerate(rows):
            print(f"\n记录 {i+1}:")
            print(f"  checkpoint_id: {checkpoint_id}")
            print(f"  数据类型: {type(checkpoint_blob)}")
            print(f"  数据长度: {len(checkpoint_blob)} 字节")

            # 尝试解析checkpoint数据
            try:
                import json
                # checkpoint是以msgpack格式存储的，但我们可以查看原始数据
                print(f"  前50字节: {checkpoint_blob[:50]}")

                # 使用checkpointer读取数据以验证类型
                with create_chat_checkpointer() as checkpointer:
                    config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
                    retrieved = checkpointer.get(config)
                    if retrieved:
                        print(f"  成功读取checkpoint")
                        print(f"  类型: {type(retrieved)}")

                        # 检查channel_versions
                        if hasattr(retrieved, 'channel_versions'):
                            print(f"  channel_versions: {retrieved.channel_versions}")
                            print(f"  channel_versions类型: {type(retrieved.channel_versions)}")

                            # 检查每个channel_version的类型
                            for key, value in retrieved.channel_versions.items():
                                print(f"    {key}: {value} (类型: {type(value)})")

                        # 检查channel_values
                        if hasattr(retrieved, 'channel_values'):
                            print(f"  channel_values字段: {list(retrieved.channel_values.keys())}")
                    else:
                        print("  读取checkpoint失败")

            except Exception as e:
                print(f"  解析失败: {e}")

        conn.close()

        # 3. 测试状态创建的类型
        print("\n3️⃣ 测试状态创建类型...")
        state = create_chat_state('test-user', 'test-session', '测试会话')
        print(f"  状态类型: {type(state)}")
        print(f"  状态内容键: {list(state.keys())}")

        for key, value in state.items():
            print(f"    {key}: {value} (类型: {type(value)})")

        # 4. 测试图创建和状态传递
        print("\n4️⃣ 测试图创建...")
        try:
            from src.domains.chat.database import create_memory_store
            store = create_memory_store()

            with create_chat_checkpointer() as checkpointer:
                from src.domains.chat.graph import create_chat_graph
                graph = create_chat_graph(checkpointer, store)

                config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

                # 尝试调用图的get_state方法
                snapshot = graph.graph.get_state(config)
                print(f"  成功获取状态快照")
                print(f"  快照类型: {type(snapshot)}")
                print(f"  快照values类型: {type(snapshot.values)}")
                print(f"  快照值字段: {list(snapshot.values.keys())}")

                if 'channel_versions' in snapshot.values:
                    print(f"  快照channel_versions: {snapshot.values['channel_versions']}")
                    for key, value in snapshot.values['channel_versions'].items():
                        print(f"    {key}: {value} (类型: {type(value)})")

        except Exception as e:
            print(f"  图创建失败: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_checkpoint_types()