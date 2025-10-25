#!/usr/bin/env python3
"""
验证关于类型错误的假设

假设：问题出现在状态创建的格式差异上
"""

import sys
import os
sys.path.append('.')

def test_state_creation_difference():
    """测试不同状态创建方式的差异"""
    print("🔍 测试状态创建差异...")

    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 方式1：使用create_chat_state函数
    state1 = create_chat_state('test-user', 'test-session', '测试会话')
    state1['messages'] = [HumanMessage(content='测试消息')]

    print("方式1 (create_chat_state):")
    for key, value in state1.items():
        print(f"  {key}: {value} (类型: {type(value)})")

    # 方式2：手动创建字典（ChatService的方式）
    state2 = {
        "user_id": "test-user",
        "session_id": "test-session",
        "session_title": "聊天会话",
        "messages": [HumanMessage(content='测试消息')]
    }

    print("\n方式2 (手动创建):")
    for key, value in state2.items():
        print(f"  {key}: {value} (类型: {type(value)})")

    # 比较两种方式
    print(f"\n差异比较:")
    for key in set(state1.keys()) | set(state2.keys()):
        if key not in state1:
            print(f"  ❌ 只有方式2有: {key}")
        elif key not in state2:
            print(f"  ❌ 只有方式1有: {key}")
        else:
            v1, v2 = state1[key], state2[key]
            if type(v1) != type(v2):
                print(f"  ❌ 类型差异 {key}: {type(v1)} vs {type(v2)}")
            elif v1 != v2:
                print(f"  ⚠️ 值差异 {key}: {v1} vs {v2}")

def test_config_difference():
    """测试配置差异"""
    print(f"\n🔍 测试配置差异...")

    # 方式1：简单配置
    config1 = {"configurable": {"thread_id": "test-session", "checkpoint_ns": ""}}

    # 方式2：ChatService配置
    config2 = {"configurable": {"thread_id": "test-session", "user_id": "test-user"}}

    print("配置1 (简单):", config1)
    print("配置2 (ChatService):", config2)

def test_fixed_state_creation():
    """测试修复后的状态创建"""
    print(f"\n🔍 测试修复后的状态创建...")

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

    # 使用正确的状态创建方式
    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 修复：使用create_chat_state而不是手动创建
    current_state = create_chat_state('test-user', session_id, '测试会话')
    current_state['messages'] = [HumanMessage(content='测试消息')]

    print(f"修复后的状态:")
    for key, value in current_state.items():
        print(f"  {key}: {value} (类型: {type(value)})")

    # 测试图调用
    try:
        result = service._with_checkpointer(lambda checkpointer: (
            lambda cp: (
                lambda g, c, s: g.graph.invoke(s, c)
            )(
                __import__('src.domains.chat.graph', fromlist=['create_chat_graph']).create_chat_graph(cp, service._store),
                {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}},
                current_state
            )
        )(checkpointer))

        print("✅ 修复后的状态调用成功")
    except Exception as e:
        print(f"❌ 修复后的状态调用失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 验证关于类型错误的假设")
    print("=" * 60)

    test_state_creation_difference()
    test_config_difference()
    test_fixed_state_creation()

    print("\n" + "=" * 60)
    print("🎯 验证结论:")
    print("1. 确定状态创建方式的差异")
    print("2. 验证修复方案")
    print("3. 提供最终的修复")
    print("=" * 60)