#!/usr/bin/env python3
"""
最终调试 - 确定确切的问题原因
"""

import sys
import os
sys.path.append('.')

def test_config_impact():
    """测试配置对类型的影响"""
    print("🔍 测试配置影响...")

    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 测试不同的配置
    configs = [
        {"configurable": {"thread_id": "test1", "checkpoint_ns": ""}, "name": "基础配置"},
        {"configurable": {"thread_id": "test2", "checkpoint_ns": "", "user_id": "test-user"}, "name": "带user_id配置"},
        {"configurable": {"thread_id": "test3", "checkpoint_ns": "", "user_id": "test-user", "extra": "value"}, "name": "复杂配置"},
    ]

    for config_data in configs:
        config = {k: v for k, v in config_data.items() if k != 'name'}
        name = config_data['name']

        print(f"\n测试配置: {name}")
        print(f"配置内容: {config}")

        try:
            with create_chat_checkpointer() as checkpointer:
                store = create_memory_store()
                graph = create_chat_graph(checkpointer, store)

                # 创建状态
                session_id = config["configurable"]["thread_id"]
                state = create_chat_state('test-user', session_id, '测试会话')
                state['messages'] = [HumanMessage(content=f"测试消息 - {name}")]

                # 调用图
                result = graph.graph.invoke(state, config)
                print(f"✅ {name} - 成功")

        except Exception as e:
            print(f"❌ {name} - 失败: {e}")

            # 检查失败后的checkpoint
            try:
                with create_chat_checkpointer() as checkpointer2:
                    checkpoint = checkpointer2.get(config)
                    if checkpoint and isinstance(checkpoint, dict):
                        if "channel_versions" in checkpoint:
                            cv = checkpoint["channel_versions"]
                            print(f"   失败后channel_versions: {cv}")
                            for k, v in cv.items():
                                if isinstance(v, str):
                                    print(f"     ❌ 发现字符串类型: {k} = {v} ({type(v)})")
            except Exception as e2:
                print(f"   无法获取失败后checkpoint: {e2}")

def test_direct_chat_service():
    """直接测试ChatService但使用不同的状态创建"""
    print(f"\n🔍 直接测试ChatService...")

    from src.domains.chat.service import ChatService

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    service = ChatService()

    # 创建会话
    session_result = service.create_session('test-user', '测试会话')
    session_id = session_result['session_id']
    print(f"会话创建: {session_id}")

    # 测试简化的配置
    print(f"\n测试简化配置...")
    try:
        # 使用最简单的配置
        simple_config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

        # 手动创建状态，但使用最简格式
        from src.domains.chat.models import create_chat_state
        from langchain_core.messages import HumanMessage

        state = create_chat_state('test-user', session_id, '测试会话')
        state['messages'] = [HumanMessage(content='简化配置测试')]

        # 直接使用图调用
        result = service._with_checkpointer(lambda checkpointer: (
            __import__('src.domains.chat.graph', fromlist=['create_chat_graph']).create_chat_graph(
                checkpointer, service._store
            ).graph.invoke(state, simple_config)
        ))

        print("✅ 简化配置成功")

    except Exception as e:
        print(f"❌ 简化配置失败: {e}")

    # 测试原始配置
    print(f"\n测试原始配置...")
    try:
        # 使用ChatService的原始配置
        original_config = service._create_runnable_config('test-user', session_id)

        state = create_chat_state('test-user', session_id, '测试会话')
        state['messages'] = [HumanMessage(content='原始配置测试')]

        result = service._with_checkpointer(lambda checkpointer: (
            __import__('src.domains.chat.graph', fromlist=['create_chat_graph']).create_chat_graph(
                checkpointer, service._store
            ).graph.invoke(state, original_config)
        ))

        print("✅ 原始配置成功")

    except Exception as e:
        print(f"❌ 原始配置失败: {e}")
        print(f"原始配置内容: {original_config}")

def trace_checkpoint_versions():
    """追踪checkpoint版本的确切来源"""
    print(f"\n🔍 追踪checkpoint版本来源...")

    from src.domains.chat.database import create_chat_checkpointer
    import sqlite3

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 手动创建一个checkpoint
    with create_chat_checkpointer() as checkpointer:
        config = {"configurable": {"thread_id": "version-test", "checkpoint_ns": ""}}

        checkpoint = {
            "v": 1,
            "ts": 0,
            "id": "version-test-checkpoint",
            "channel_values": {"messages": []},
            "channel_versions": {"messages": 1},  # 明确的int
            "versions_seen": {},
            "pending_sends": []
        }

        checkpointer.put(config, checkpoint, {}, {})

    # 检查数据库中的原始数据
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT checkpoint FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1")
    row = cursor.fetchone()

    if row:
        checkpoint_blob = row[0]

        # 检查原始字节
        print(f"数据库中的原始数据 (前100字节):")
        print(f"  {checkpoint_blob[:100]}")

        # 查看是否包含ASCII字符
        try:
            # 尝试作为字符串查看
            as_str = checkpoint_blob.decode('utf-8', errors='ignore')
            print(f"作为字符串查看 (前200字符):")
            print(f"  {as_str[:200]}")
        except:
            print("无法解码为字符串")

    conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 最终调试 - 确定确切的问题原因")
    print("=" * 60)

    test_config_impact()
    test_direct_chat_service()
    trace_checkpoint_versions()

    print("\n" + "=" * 60)
    print("🎯 最终结论:")
    print("1. 确定配置对类型的影响")
    print("2. 找到确切的问题触发条件")
    print("3. 提供精确的修复方案")
    print("=" * 60)