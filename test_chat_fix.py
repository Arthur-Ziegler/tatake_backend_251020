#!/usr/bin/env python3
"""
直接测试 TypeSafeCheckpointer 修复LangGraph版本号类型不一致问题

这个测试脚本模拟LangGraph产生的问题数据，验证我们的TypeSafeCheckpointer
能够正确处理字符串和整数混合的版本号类型。

运行方式：
uv run python test_chat_fix.py
"""

import logging
from unittest.mock import Mock
from src.domains.chat.service import ChatService

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_langgraph_version_fix():
    """测试LangGraph版本号类型修复"""
    print("🔧 测试 TypeSafeCheckpoint er 修复LangGraph版本号类型不一致问题")
    print("=" * 70)

    # 创建ChatService实例
    chat_service = ChatService()

    # 模拟LangGraph产生的问题数据
    problematic_checkpoint = {
        "channel_versions": {
            "__start__": "00000000000000000000000000000002.0.243798848838515",  # 问题字符串
            "messages": 1,  # 正确的整数
            "agent": "3.0",  # 浮点数字符串
            "tools": "invalid_version_string",  # 无效版本字符串
            "empty_string": "",  # 空字符串
            "negative": "-5",  # 负数字符串
        },
        "values": {"messages": []}
    }

    print("📋 原始问题数据:")
    for key, value in problematic_checkpoint["channel_versions"].items():
        print(f"  {key}: {value} (类型: {type(value).__name__})")

    # 创建Mock checkpointer
    mock_config = Mock()
    mock_checkpointer = Mock()
    mock_checkpointer.put.return_value = "success"

    # 创建类型安全的checkpointer
    safe_checkpointer = chat_service._create_type_safe_checkpointer(mock_checkpointer)

    print("\n🔧 执行类型安全修复...")

    # 执行put操作（应该修复类型）
    result = safe_checkpointer.put(mock_config, problematic_checkpoint, {}, {})

    print("\n✅ 修复后的数据:")
    for key, value in problematic_checkpoint["channel_versions"].items():
        print(f"  {key}: {value} (类型: {type(value).__name__})")

    # 验证修复结果
    print("\n🔍 验证修复结果:")

    # 验证所有版本号都是整数
    all_integers = all(isinstance(value, int) for value in problematic_checkpoint["channel_versions"].values())
    print(f"  ✓ 所有版本号都是整数: {all_integers}")

    # 验证具体的修复
    assert problematic_checkpoint["channel_versions"]["__start__"] == 2, \
        f"期望 __start__ = 2，实际 = {problematic_checkpoint['channel_versions']['__start__']}"
    print(f"  ✓ LangGraph UUID格式修复: 00000000000000000000000000000002.0.243798848838515 → 2")

    assert problematic_checkpoint["channel_versions"]["messages"] == 1, \
        f"期望 messages = 1，实际 = {problematic_checkpoint['channel_versions']['messages']}"
    print(f"  ✓ 整数保持不变: 1 → 1")

    assert problematic_checkpoint["channel_versions"]["agent"] == 3, \
        f"期望 agent = 3，实际 = {problematic_checkpoint['channel_versions']['agent']}"
    print(f"  ✓ 浮点字符串修复: '3.0' → 3")

    assert isinstance(problematic_checkpoint["channel_versions"]["tools"], int), \
        f"期望 tools 是整数，实际 = {problematic_checkpoint['channel_versions']['tools']} ({type(problematic_checkpoint['channel_versions']['tools'])})"
    print(f"  ✓ 无效字符串转换为整数: 'invalid_version_string' → {problematic_checkpoint['channel_versions']['tools']}")

    assert problematic_checkpoint["channel_versions"]["empty_string"] == 0, \
        f"期望 empty_string = 0，实际 = {problematic_checkpoint['channel_versions']['empty_string']}"
    print(f"  ✓ 空字符串处理: '' → 0")

    assert problematic_checkpoint["channel_versions"]["negative"] == -5, \
        f"期望 negative = -5，实际 = {problematic_checkpoint['channel_versions']['negative']}"
    print(f"  ✓ 负数处理: '-5' → -5")

    # 验证原方法被调用
    mock_checkpointer.put.assert_called_once()
    print(f"  ✓ 原始checkpointer.put()被正确调用")

    print(f"\n🎉 TypeSafeCheckpointer 测试通过！")
    print(f"   原始的LangGraph版本号类型不一致问题已修复")

    return True

def test_get_method_also_fixes_types():
    """测试get方法也能修复类型"""
    print("\n🔧 测试 get 方法的类型修复功能")
    print("=" * 50)

    chat_service = ChatService()

    # 模拟数据库返回的问题数据
    problematic_result = {
        "channel_versions": {
            "__start__": "00000000000000000000000000000003.1.123456789012345",  # 问题字符串
            "messages": 2,  # 正确的整数
            "invalid": "not_a_number"  # 无效字符串
        },
        "values": {"messages": []}
    }

    print("📋 从数据库获取的问题数据:")
    for key, value in problematic_result["channel_versions"].items():
        print(f"  {key}: {value} (类型: {type(value).__name__})")

    mock_config = Mock()
    mock_checkpointer = Mock()
    mock_checkpointer.get.return_value = problematic_result

    # 创建类型安全的checkpointer
    safe_checkpointer = chat_service._create_type_safe_checkpointer(mock_checkpointer)

    print("\n🔧 执行get操作并修复类型...")

    # 执行get操作（应该修复类型）
    result = safe_checkpointer.get(mock_config)

    print("\n✅ 修复后的数据:")
    for key, value in result["channel_versions"].items():
        print(f"  {key}: {value} (类型: {type(value).__name__})")

    # 验证修复结果
    assert result["channel_versions"]["__start__"] == 3, \
        f"期望 __start__ = 3，实际 = {result['channel_versions']['__start__']}"
    assert result["channel_versions"]["messages"] == 2, \
        f"期望 messages = 2，实际 = {result['channel_versions']['messages']}"
    assert isinstance(result["channel_versions"]["invalid"], int), \
        f"期望 invalid 是整数，实际 = {result['channel_versions']['invalid']}"

    print("\n✅ get方法类型修复测试通过！")

    return True

if __name__ == "__main__":
    print("🧪 Chat TypeSafeCheckpointer 修复验证")
    print("=" * 70)
    print("这个测试验证LangGraph版本号类型不一致问题的修复")
    print("原始错误: '>' not supported between instances of 'str' and 'int'")
    print()

    try:
        # 测试put方法的类型修复
        test_langgraph_version_fix()

        # 测试get方法的类型修复
        test_get_method_also_fixes_types()

        print("\n🎉 所有测试通过！")
        print("✅ LangGraph版本号类型不一致问题已成功修复")
        print("✅ Chat API不再出现 '>' not supported between instances of 'str' and 'int' 错误")
        print()
        print("📝 修复总结:")
        print("   1. TypeSafeCheckpointer包装器自动修复LangGraph的版本号类型")
        print("   2. 支持各种UUID格式的版本号字符串")
        print("   3. 提供防御性编程，确保类型一致性")
        print("   4. 包含详细的日志记录用于调试")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)