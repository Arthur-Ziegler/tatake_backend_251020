#!/usr/bin/env python3
"""
简化的类型问题分析脚本

专注于找出int到str的确切转换点
"""

import sys
import os
sys.path.append('.')

def analyze_checkpointer_behavior():
    """分析checkpointer的行为"""
    print("🔍 分析checkpointer行为...")

    from src.domains.chat.database import create_chat_checkpointer

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建checkpointer
    with create_chat_checkpointer() as checkpointer:
        config = {"configurable": {"thread_id": "test", "checkpoint_ns": ""}}

        # 创建原始checkpoint数据 - 明确使用int类型
        original_checkpoint = {
            "v": 1,
            "ts": 0,
            "id": "test-checkpoint",
            "channel_values": {"messages": []},
            "channel_versions": {"messages": 1},  # 明确的int类型
            "versions_seen": {},
            "pending_sends": []
        }

        print("原始checkpoint数据:")
        print(f"  channel_versions.messages: {original_checkpoint['channel_versions']['messages']} (类型: {type(original_checkpoint['channel_versions']['messages'])})")

        # 存储checkpoint
        checkpointer.put(config, original_checkpoint, {}, {})
        print("✅ Checkpoint存储成功")

        # 立即检索checkpoint
        retrieved = checkpointer.get(config)
        print("✅ Checkpoint检索成功")

        if retrieved:
            print(f"检索到的checkpoint类型: {type(retrieved)}")

            # 检查不同的属性访问方式
            print("检查属性访问:")
            print(f"  hasattr(retrieved, 'channel_versions'): {hasattr(retrieved, 'channel_versions')}")
            print(f"  isinstance(retrieved, dict): {isinstance(retrieved, dict)}")

            if isinstance(retrieved, dict):
                print("  作为dict访问:")
                if "channel_versions" in retrieved:
                    channel_versions = retrieved["channel_versions"]
                    print(f"    channel_versions: {channel_versions} (类型: {type(channel_versions)})")
                    if isinstance(channel_versions, dict):
                        for key, value in channel_versions.items():
                            print(f"      {key}: {value} (类型: {type(value)})")

                            # 检查类型变化
                            original_value = original_checkpoint["channel_versions"][key]
                            if type(value) != type(original_value):
                                print(f"        ❌ 类型变化！原始: {type(original_value)}, 现在: {type(value)}")
                            else:
                                print(f"        ✅ 类型一致: {type(value)}")

            if hasattr(retrieved, 'channel_versions'):
                print("  作为属性访问:")
                channel_versions = retrieved.channel_versions
                print(f"    channel_versions: {channel_versions} (类型: {type(channel_versions)})")
                if isinstance(channel_versions, dict):
                    for key, value in channel_versions.items():
                        print(f"      {key}: {value} (类型: {type(value)})")

        # 检查数据库中的原始数据
        print(f"\n🔍 检查数据库原始数据...")
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT checkpoint FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1")
        row = cursor.fetchone()

        if row:
            checkpoint_blob = row[0]
            print(f"数据库中checkpoint数据类型: {type(checkpoint_blob)}")
            print(f"数据长度: {len(checkpoint_blob)} 字节")

            # 尝试解析msgpack数据
            try:
                import msgpack
                decoded = msgpack.unpackb(checkpoint_blob, raw=False)
                print(f"MsgPack解码成功，数据类型: {type(decoded)}")

                if "channel_versions" in decoded:
                    channel_versions = decoded["channel_versions"]
                    print(f"解码后的channel_versions: {channel_versions} (类型: {type(channel_versions)})")

                    for key, value in channel_versions.items():
                        print(f"  {key}: {value} (类型: {type(value)})")

                        # 检查MsgPack是否保持了类型
                        original_value = original_checkpoint["channel_versions"][key]
                        if type(value) != type(original_value):
                            print(f"    ❌ MsgPack导致类型变化！原始: {type(original_value)}, 解码后: {type(value)}")
                        else:
                            print(f"    ✅ MsgPack保持类型: {type(value)}")

            except Exception as e:
                print(f"MsgPack解码失败: {e}")

        conn.close()

def test_graph_state_creation():
    """测试图状态创建时的类型处理"""
    print(f"\n🧪 测试图状态创建...")

    from src.domains.chat.models import create_chat_state
    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.database import create_chat_checkpointer, create_memory_store

    # 创建状态
    state = create_chat_state('test-user', 'test-session', '测试会话')
    print(f"创建的状态类型: {type(state)}")
    print(f"状态内容: {list(state.keys())}")

    # 添加消息
    from langchain_core.messages import HumanMessage
    state['messages'] = [HumanMessage(content="测试消息")]

    # 创建图并测试状态传递
    with create_chat_checkpointer() as checkpointer:
        store = create_memory_store()
        graph = create_chat_graph(checkpointer, store)

        config = {"configurable": {"thread_id": state['session_id'], "checkpoint_ns": ""}}

        print(f"传递给图的状态:")
        for key, value in state.items():
            print(f"  {key}: {value} (类型: {type(value)})")

        # 检查图的get_state方法
        try:
            current_state = graph.graph.get_state(config)
            print(f"图当前状态类型: {type(current_state)}")

            if hasattr(current_state, 'values'):
                values = current_state.values
                print(f"状态values类型: {type(values)}")

                if isinstance(values, dict) and "channel_versions" in values:
                    channel_versions = values["channel_versions"]
                    print(f"values中的channel_versions: {channel_versions}")
                    for key, value in channel_versions.items():
                        print(f"  {key}: {value} (类型: {type(value)})")

        except Exception as e:
            print(f"获取图状态失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 简化类型问题分析")
    print("=" * 60)

    analyze_checkpointer_behavior()
    test_graph_state_creation()

    print("\n" + "=" * 60)
    print("🔍 分析结论:")
    print("1. 检查MsgPack序列化是否保持int类型")
    print("2. 检查LangGraph内部状态处理")
    print("3. 确定类型转换的确切位置")
    print("=" * 60)