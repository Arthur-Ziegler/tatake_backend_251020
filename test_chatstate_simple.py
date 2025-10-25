#!/usr/bin/env python3
"""
简化的ChatState测试
"""

def test_chatstate_simple():
    """简单测试ChatState"""
    print("🎯 简单ChatState测试")

    try:
        from src.domains.chat.models import ChatState

        # 测试直接创建ChatState
        state = ChatState()
        print(f"✅ ChatState创建成功")
        print(f"   messages类型: {type(state.messages)}")
        print(f"   messages内容: {state.messages}")
        print(f"   消息数量: {len(state.messages)}")

        # 测试添加消息
        state.add_human_message("测试消息")
        print(f"✅ 添加消息成功")
        print(f"   消息数量: {len(state.messages)}")
        print(f"   最后消息: {state.get_last_message().content}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_chatstate_simple()