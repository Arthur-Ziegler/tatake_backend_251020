#!/usr/bin/env python3
"""
找到类型转换的确切条件

专门测试什么情况下int会变成str
"""

import sys
import os
sys.path.append('.')

def test_message_flow():
    """测试消息流程中的类型变化"""
    print("🔍 测试消息流程...")

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

    # 检查初始checkpoint
    with service.db_manager.create_checkpointer() as checkpointer:
        config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
        checkpoint = checkpointer.get(config)
        if checkpoint and isinstance(checkpoint, dict):
            if "channel_versions" in checkpoint:
                cv = checkpoint["channel_versions"]
                print(f"初始channel_versions: {cv} (类型: {type(cv.get('messages', 'N/A'))})")

    # 逐步模拟send_message的过程
    print("\n🧪 模拟send_message步骤...")

    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 1. 创建当前状态
    current_state = create_chat_state('test-user', session_id, '测试会话')
    current_state['messages'] = [HumanMessage(content='测试消息')]

    print(f"1. 创建状态: channel_versions = {current_state.get('channel_versions', 'NOT_PRESENT')}")

    # 2. 获取图实例
    graph = service._get_or_create_graph()
    config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

    # 3. 检查图的当前状态
    try:
        snapshot = graph.graph.get_state(config)
        if hasattr(snapshot, 'values') and isinstance(snapshot.values, dict):
            if "channel_versions" in snapshot.values:
                cv = snapshot.values["channel_versions"]
                print(f"2. 图当前状态: channel_versions = {cv} (messages类型: {type(cv.get('messages', 'N/A'))})")
            else:
                print(f"2. 图当前状态: 没有channel_versions")
        else:
            print(f"2. 图当前状态: values不是dict或无values")
    except Exception as e:
        print(f"2. 获取图状态失败: {e}")

    # 4. 尝试调用图
    print(f"3. 准备调用图...")
    try:
        # 这里应该会触发错误
        result = graph.graph.invoke(current_state, config)
        print(f"✅ 图调用成功")

        # 检查调用后的状态
        snapshot = graph.graph.get_state(config)
        if hasattr(snapshot, 'values') and isinstance(snapshot.values, dict):
            if "channel_versions" in snapshot.values:
                cv = snapshot.values["channel_versions"]
                print(f"4. 调用后状态: channel_versions = {cv} (messages类型: {type(cv.get('messages', 'N/A'))})")

    except Exception as e:
        print(f"❌ 图调用失败: {e}")

        # 检查失败后的checkpoint状态
        with service.db_manager.create_checkpointer() as checkpointer:
            checkpoint = checkpointer.get(config)
            if checkpoint and isinstance(checkpoint, dict):
                if "channel_versions" in checkpoint:
                    cv = checkpoint["channel_versions"]
                    print(f"4. 失败后checkpoint: channel_versions = {cv} (messages类型: {type(cv.get('messages', 'N/A'))})")

                    # 检查每个值
                    for k, v in cv.items():
                        print(f"   {k}: {v} (类型: {type(v)})")
                        if isinstance(v, str):
                            print(f"     ❌ 发现字符串类型！")

def test_config_variations():
    """测试不同配置对类型的影响"""
    print(f"\n🧪 测试配置变化...")

    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 测试不同的配置组合
    configs = [
        {"configurable": {"thread_id": "test1", "checkpoint_ns": ""}},
        {"configurable": {"thread_id": "test2", "checkpoint_ns": "", "user_id": "test-user"}},
        {"configurable": {"thread_id": "test3", "checkpoint_ns": None}},
        {"configurable": {"thread_id": "test4", "checkpoint_ns": ""}, "tags": ["test"]},
    ]

    for i, config in enumerate(configs):
        print(f"\n测试配置 {i+1}: {config}")

        try:
            with create_chat_checkpointer() as checkpointer:
                store = create_memory_store()
                graph = create_chat_graph(checkpointer, store)

                # 创建状态
                state = create_chat_state('test-user', f'session{i+1}', '测试会话')
                state['messages'] = [HumanMessage(content=f"测试消息{i+1}")]

                # 调用图
                result = graph.graph.invoke(state, config)
                print(f"   ✅ 成功")

                # 检查状态
                snapshot = graph.graph.get_state(config)
                if hasattr(snapshot, 'values') and isinstance(snapshot.values, dict):
                    if "channel_versions" in snapshot.values:
                        cv = snapshot.values["channel_versions"]
                        print(f"   channel_versions: {cv}")
                        for k, v in cv.items():
                            if isinstance(v, str):
                                print(f"     ❌ 配置{i+1}导致类型转换: {k} = {v} ({type(v)})")

        except Exception as e:
            print(f"   ❌ 失败: {e}")

def test_database_manager():
    """测试数据库管理器的行为"""
    print(f"\n🧪 测试数据库管理器...")

    from src.domains.chat.database import DatabaseManager

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    db_manager = DatabaseManager()

    # 测试直接使用数据库管理器
    with db_manager.create_checkpointer() as checkpointer:
        config = {"configurable": {"thread_id": "db-manager-test", "checkpoint_ns": ""}}

        # 创建checkpoint
        checkpoint = {
            "v": 1,
            "ts": 0,
            "id": "db-test",
            "channel_values": {"messages": []},
            "channel_versions": {"messages": 1},
            "versions_seen": {},
            "pending_sends": []
        }

        checkpointer.put(config, checkpoint, {}, {})

        # 立即检索
        retrieved = checkpointer.get(config)
        if retrieved and isinstance(retrieved, dict):
            if "channel_versions" in retrieved:
                cv = retrieved["channel_versions"]
                print(f"数据库管理器测试: {cv}")
                for k, v in cv.items():
                    print(f"  {k}: {v} (类型: {type(v)})")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 找到类型转换的确切条件")
    print("=" * 60)

    test_message_flow()
    test_config_variations()
    test_database_manager()

    print("\n" + "=" * 60)
    print("🎯 结论:")
    print("1. 确定触发类型转换的具体条件")
    print("2. 找到根本原因")
    print("3. 提供修复方向")
    print("=" * 60)