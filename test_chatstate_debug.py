#!/usr/bin/env python3
"""
调试ChatState类型问题
"""

def test_chatstate_debug():
    """调试ChatState类型问题"""
    print("🎯 调试ChatState类型问题")

    try:
        from src.domains.chat.models import ChatState
        from langgraph.graph import MessagesState

        print(f"ChatState类: {ChatState}")
        print(f"ChatState基类: {ChatState.__bases__}")

        # 测试直接创建
        print("\n1. 直接创建ChatState:")
        state1 = ChatState()
        print(f"   类型: {type(state1)}")
        print(f"   内容: {state1}")

        # 测试MessagesState
        print("\n2. 直接创建MessagesState:")
        state2 = MessagesState()
        print(f"   类型: {type(state2)}")
        print(f"   内容: {state2}")

        # 测试字典创建
        print("\n3. 使用字典创建:")
        state3 = ChatState(messages=[])
        print(f"   类型: {type(state3)}")
        print(f"   内容: {state3}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_chatstate_debug()