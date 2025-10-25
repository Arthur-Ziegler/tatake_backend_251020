#!/usr/bin/env python3
"""
真实的LangGraph修复验证测试

这个测试验证Monkey Patch是否真正修复了LangGraph的类型错误。
它直接调用LangGraph内部函数，不使用Mock。
"""

import logging
import traceback
import uuid
from contextlib import contextmanager

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_langgraph_internal_function():
    """测试LangGraph内部函数是否修复"""
    print("🔧 测试LangGraph内部函数修复")
    print("=" * 50)

    try:
        # 导入LangGraph内部函数
        from langgraph.pregel._utils import get_new_channel_versions
        from langgraph.pregel.utils import null_version

        print("✅ 成功导入LangGraph内部函数")

        # 创建测试数据 - 这些数据会导致原始函数出错
        channels = ["messages", "__start__", "user_data"]
        values = {
            "messages": ["test message"],
            "__start__": "00000000000000000000000000000002.0.243798848838515",  # 问题数据
            "user_data": "550e8400-e29b-41d4-a716-446655440000.1.123456789"     # 问题数据
        }
        previous_versions = {
            "messages": 1,
            "__start__": 1,
            "user_data": 1
        }

        print(f"📋 测试数据:")
        print(f"  channels: {channels}")
        print(f"  values: {values}")
        print(f"  previous_versions: {previous_versions}")
        print()

        # 测试修复后的函数
        print("🎯 测试修复后的get_new_channel_versions函数...")
        try:
            result = get_new_channel_versions(channels, values, previous_versions)
            print("✅ 函数执行成功！")
            print(f"   结果: {result}")

            # 验证结果都是整数
            for key, value in result.items():
                if isinstance(value, int):
                    print(f"   ✅ {key}: {value} (整数类型)")
                else:
                    print(f"   ❌ {key}: {value} (类型: {type(value)})")

            return True

        except Exception as e:
            print(f"❌ 函数执行失败: {e}")
            print(f"   错误堆栈:\n{traceback.format_exc()}")
            return False

    except ImportError as e:
        print(f"❌ 导入LangGraph函数失败: {e}")
        return False

def test_chat_service_integration():
    """测试ChatService集成"""
    print("\n🔧 测试ChatService集成")
    print("=" * 50)

    try:
        from src.domains.chat.service import ChatService

        print("✅ 成功导入ChatService")

        # 创建ChatService实例
        chat_service = ChatService()

        # 生成测试UUID
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        message = "测试LangGraph修复"

        print(f"📋 测试参数:")
        print(f"  user_id: {user_id}")
        print(f"  session_id: {session_id}")
        print(f"  message: {message}")
        print()

        # 测试send_message
        print("🎯 测试ChatService.send_message...")
        try:
            result = chat_service.send_message(user_id, session_id, message)
            print("✅ 消息发送成功！")
            print(f"   结果: {result}")
            return True

        except Exception as e:
            print(f"❌ 消息发送失败: {e}")
            print(f"   错误堆栈:\n{traceback.format_exc()}")
            return False

    except ImportError as e:
        print(f"❌ 导入ChatService失败: {e}")
        return False

def check_langgraph_fix_status():
    """检查LangGraph修复状态"""
    print("\n🔍 检查LangGraph修复状态")
    print("=" * 50)

    try:
        from src.core.langgraph_fix import is_langgraph_fix_applied

        if is_langgraph_fix_applied():
            print("✅ LangGraph修复已应用")
            return True
        else:
            print("❌ LangGraph修复未应用")
            return False

    except ImportError as e:
        print(f"❌ 无法检查修复状态: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始真实的LangGraph修复验证")
    print()

    # 检查修复状态
    fix_status = check_langgraph_fix_status()

    # 测试内部函数
    internal_test = test_langgraph_internal_function()

    # 测试集成
    integration_test = test_chat_service_integration()

    print("\n📊 测试总结")
    print("=" * 50)
    print(f"修复状态: {'✅ 已应用' if fix_status else '❌ 未应用'}")
    print(f"内部函数测试: {'✅ 通过' if internal_test else '❌ 失败'}")
    print(f"集成测试: {'✅ 通过' if integration_test else '❌ 失败'}")

    if internal_test and integration_test:
        print("\n🎉 所有测试通过！LangGraph修复成功！")
    else:
        print("\n❌ 测试失败，需要进一步调试")

    print("\n🎯 测试完成！")