#!/usr/bin/env python3
"""
深入分析TypedDict和checkpoint类型问题

根本原因分析：
1. MessagesState是TypedDict，实例化返回dict对象
2. TypedDict的序列化/反序列化可能导致类型转换
3. LangGraph在checkpoint处理中可能将int转换为str
"""

import sys
import os
sys.path.append('.')

from typing import TypedDict
from src.domains.chat.models import ChatState, create_chat_state
from src.domains.chat.database import create_chat_checkpointer
from src.domains.chat.graph import create_chat_graph
from src.domains.chat.database import create_memory_store
from langchain_core.messages import HumanMessage

def analyze_typeddict_behavior():
    """分析TypedDict的行为"""
    print("🔍 分析TypedDict行为...")

    # 创建自定义TypedDict来测试
    class TestState(TypedDict):
        messages: list
        user_id: str
        version: int

    # 实例化TypedDict
    test_state = TestState(
        messages=[],
        user_id="test",
        version=1
    )

    print(f"TypedDict实例类型: {type(test_state)}")
    print(f"是否为dict: {isinstance(test_state, dict)}")
    print(f"版本字段类型: {type(test_state['version'])}")

    # 测试序列化
    import json
    serialized = json.dumps(test_state)
    deserialized = json.loads(serialized)

    print(f"序列化后版本类型: {type(deserialized['version'])}")
    print(f"JSON序列化将int转换为str: {type(deserialized['version']) != int}")

    return test_state

def analyze_checkpoint_serialization():
    """分析checkpoint序列化过程中的类型变化"""
    print("\n🔍 分析checkpoint序列化...")

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建ChatState
    state = create_chat_state('test-user', 'test-session', '测试会话')
    print(f"ChatState类型: {type(state)}")
    print(f"ChatState内容: {list(state.keys())}")

    # 创建checkpoint配置
    session_id = state['session_id']
    config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

    # 手动创建checkpoint数据
    checkpoint_data = {
        "v": 1,
        "ts": 0,
        "id": "test-checkpoint",
        "channel_values": state,
        "channel_versions": {"messages": 1},  # 明确使用int
        "versions_seen": {},
        "pending_sends": []
    }

    print(f"原始checkpoint数据:")
    for key, value in checkpoint_data.items():
        if key == "channel_versions":
            for ck, cv in value.items():
                print(f"  {key}.{ck}: {cv} (类型: {type(cv)})")
        else:
            print(f"  {key}: {type(value)}")

    # 使用checkpointer测试存储和检索
    with create_chat_checkpointer() as checkpointer:
        # 存储checkpoint
        checkpointer.put(config, checkpoint_data, {}, {})
        print(f"\n✅ Checkpoint存储成功")

        # 检索checkpoint
        retrieved = checkpointer.get(config)
        print(f"✅ Checkpoint检索成功")
        print(f"检索到的类型: {type(retrieved)}")

        if retrieved:
            print(f"检索到的checkpoint结构:")
            if isinstance(retrieved, dict):
                for key, value in retrieved.items():
                    print(f"  {key}: {type(value)}")
                    if key == "channel_versions":
                        for ck, cv in value.items():
                            print(f"    {ck}: {cv} (类型: {type(cv)})")

                            # 检查类型是否匹配
                            if isinstance(cv, str):
                                print(f"      ❌ 类型错误：期望int，实际str")
                            elif isinstance(cv, int):
                                print(f"      ✅ 类型正确：int")
            else:
                # 检查是否有channel_versions属性
                if hasattr(retrieved, 'channel_versions'):
                    print(f"检索到的channel_versions:")
                    for key, value in retrieved.channel_versions.items():
                        print(f"  {key}: {value} (类型: {type(value)})")

                        # 检查类型是否匹配
                        if isinstance(value, str):
                            print(f"    ❌ 类型错误：期望int，实际str")
                        elif isinstance(value, int):
                            print(f"    ✅ 类型正确：int")

        # 测试图调用
        print(f"\n🧪 测试图调用...")
        store = create_memory_store()
        graph = create_chat_graph(checkpointer, store)

        # 添加消息到状态
        state['messages'] = [HumanMessage(content="测试消息")]

        try:
            result = graph.graph.invoke(state, config)
            print(f"✅ 图调用成功")
        except Exception as e:
            print(f"❌ 图调用失败: {e}")

            # 详细分析错误
            print(f"\n🔍 详细分析错误...")
            print(f"错误类型: {type(e)}")

            # 检查checkpoint状态
            current_checkpoint = checkpointer.get(config)
            if current_checkpoint:
                print(f"当前checkpoint结构:")
                if isinstance(current_checkpoint, dict):
                    print(f"  类型: dict，键: {list(current_checkpoint.keys())}")
                    if "channel_versions" in current_checkpoint:
                        for key, value in current_checkpoint["channel_versions"].items():
                            print(f"    channel_versions.{key}: {value} (类型: {type(value)})")
                else:
                    print(f"  类型: {type(current_checkpoint)}")
                    if hasattr(current_checkpoint, 'channel_versions'):
                        for key, value in current_checkpoint.channel_versions.items():
                            print(f"    channel_versions.{key}: {value} (类型: {type(value)})")

def test_direct_state_comparison():
    """测试直接状态比较中的类型问题"""
    print(f"\n🧪 测试状态比较...")

    # 模拟LangGraph内部的版本比较逻辑
    def simulate_version_comparison(new_versions, previous_versions):
        """模拟LangGraph的get_new_channel_versions逻辑"""
        print(f"比较版本: {new_versions} vs {previous_versions}")

        for k, v in new_versions.items():
            previous_v = previous_versions.get(k, 0)
            print(f"  比较键 {k}: {v} (类型: {type(v)}) > {previous_v} (类型: {type(previous_v)})")

            try:
                result = v > previous_v
                print(f"    比较结果: {result}")
            except TypeError as e:
                print(f"    ❌ 比较失败: {e}")
                return False
        return True

    # 测试不同类型组合
    test_cases = [
        ({"messages": 1}, {"messages": 0}),  # int vs int - 应该成功
        ({"messages": "1"}, {"messages": 0}),  # str vs int - 应该失败
        ({"messages": 1}, {"messages": "0"}),  # int vs str - 应该失败
        ({"messages": "2"}, {"messages": "1"}),  # str vs str - 可能成功但不正确
    ]

    for i, (new_v, prev_v) in enumerate(test_cases):
        print(f"\n测试案例 {i+1}:")
        success = simulate_version_comparison(new_v, prev_v)
        print(f"结果: {'✅ 成功' if success else '❌ 失败'}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 深入分析TypedDict和checkpoint类型问题")
    print("=" * 60)

    # 1. 分析TypedDict基本行为
    analyze_typeddict_behavior()

    # 2. 分析checkpoint序列化
    analyze_checkpoint_serialization()

    # 3. 测试状态比较
    test_direct_state_comparison()

    print("\n" + "=" * 60)
    print("🔍 根本原因总结:")
    print("1. MessagesState是TypedDict，实例化返回dict对象")
    print("2. Checkpoint序列化/反序列化过程中int可能被转换为str")
    print("3. LangGraph版本比较要求严格的int类型")
    print("4. 需要在checkpoint处理过程中保持类型一致性")
    print("=" * 60)