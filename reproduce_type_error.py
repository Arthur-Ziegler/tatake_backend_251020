#!/usr/bin/env python3
"""
重现channel_versions类型错误

专门重现'>' not supported between instances of 'str' and 'int'错误
"""

import sys
import os
sys.path.append('.')

def reproduce_type_error():
    """重现类型错误"""
    print("🎯 重现channel_versions类型错误...")

    from src.domains.chat.service import ChatService

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f'删除了现有数据库文件: {db_path}')

    # 创建聊天服务
    service = ChatService()

    try:
        # 创建会话
        print("1️⃣ 创建会话...")
        session_result = service.create_session('test-user', '类型错误重现')
        session_id = session_result['session_id']
        print(f"✅ 会话创建成功: {session_id}")

        # 尝试发送消息 - 这里应该触发类型错误
        print("2️⃣ 发送消息...")
        result = service.send_message('test-user', session_id, '你好，这是一个测试消息')
        print(f"✅ 消息发送成功!")
        print(f"回复: {result.get('response', '无回复')[:100]}...")

    except Exception as e:
        print(f"❌ 错误重现成功: {e}")
        print(f"错误类型: {type(e)}")

        # 详细分析错误
        import traceback
        traceback.print_exc()

        # 尝试定位错误的确切位置
        error_msg = str(e)
        if "'>' not supported between instances of 'str' and 'int'" in error_msg:
            print(f"\n🎯 这就是我们要找的类型错误！")
            analyze_error_location()
        else:
            print(f"\n⚠️ 这不是我们要找的类型错误")

def analyze_error_location():
    """分析错误发生的位置"""
    print(f"\n🔍 分析类型错误位置...")

    # 直接使用图来重现错误
    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 创建状态
    state = create_chat_state('test-user', 'test-session', '测试会话')
    session_id = state['session_id']

    # 手动创建一个可能有问题的checkpoint
    with create_chat_checkpointer() as checkpointer:
        config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

        # 创建一个checkpoint，其中某个版本号是字符串
        problematic_checkpoint = {
            "v": 1,
            "ts": 0,
            "id": "problematic-checkpoint",
            "channel_values": state,
            "channel_versions": {"messages": "1"},  # 故意使用字符串
            "versions_seen": {},
            "pending_sends": []
        }

        print("存储有问题的checkpoint...")
        checkpointer.put(config, problematic_checkpoint, {}, {})

        # 现在尝试图调用
        print("尝试图调用...")
        store = create_memory_store()
        graph = create_chat_graph(checkpointer, store)

        # 添加新消息
        new_state = state.copy()
        new_state['messages'] = [HumanMessage(content="测试消息")]

        try:
            result = graph.graph.invoke(new_state, config)
            print("✅ 意外成功")
        except Exception as e:
            print(f"❌ 错误重现: {e}")

            # 检查当前的checkpoint状态
            current = checkpointer.get(config)
            if current and isinstance(current, dict):
                if "channel_versions" in current:
                    print("当前checkpoint的channel_versions:")
                    for key, value in current["channel_versions"].items():
                        print(f"  {key}: {value} (类型: {type(value)})")

def test_version_comparison_directly():
    """直接测试版本比较逻辑"""
    print(f"\n🧪 直接测试版本比较...")

    # 模拟LangGraph的版本比较逻辑
    test_cases = [
        ("正常的int比较", {"messages": 2}, {"messages": 1}),
        ("str vs int比较", {"messages": "2"}, {"messages": 1}),
        ("int vs str比较", {"messages": 2}, {"messages": "1"}),
        ("str vs str比较", {"messages": "2"}, {"messages": "1"}),
    ]

    for desc, new_versions, old_versions in test_cases:
        print(f"\n测试: {desc}")
        print(f"  新版本: {new_versions}")
        print(f"  旧版本: {old_versions}")

        try:
            # 模拟LangGraph内部的比较逻辑
            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                from langgraph.pregel._utils import null_version
            else:
                # 定义一个默认的null_version
                null_version = 0

            for k, v in new_versions.items():
                previous_v = old_versions.get(k, null_version)
                print(f"    比较 {k}: {v} ({type(v)}) > {previous_v} ({type(previous_v)})")

                result = v > previous_v  # 这里应该触发类型错误
                print(f"    结果: {result}")

        except TypeError as e:
            print(f"    ❌ 类型错误: {e}")
        except Exception as e:
            print(f"    ❌ 其他错误: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 重现channel_versions类型错误")
    print("=" * 60)

    # 1. 尝试重现原始错误
    reproduce_type_error()

    # 2. 测试版本比较
    test_version_comparison_directly()

    print("\n" + "=" * 60)
    print("🎯 分析结论:")
    print("1. 确定类型错误的确切触发条件")
    print("2. 找到类型转换的源头")
    print("3. 为修复方案提供依据")
    print("=" * 60)