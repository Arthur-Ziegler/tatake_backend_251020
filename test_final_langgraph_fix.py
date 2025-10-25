#!/usr/bin/env python3
"""
最终验证：LangGraph类型错误修复效果

专门测试原来的LangGraph类型错误是否已经完全修复
"""

import uuid
import logging
import traceback

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_multiple_messages():
    """测试多条消息发送，验证稳定性"""
    print("🎯 多条消息稳定性测试")
    print("=" * 50)

    try:
        from src.domains.chat.service import ChatService

        # 创建ChatService实例
        chat_service = ChatService()

        # 生成测试UUID
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        print(f"📋 测试参数:")
        print(f"  user_id: {user_id}")
        print(f"  session_id: {session_id}")

        # 发送多条消息
        messages = [
            "你好，我想测试LangGraph修复效果",
            "请帮我计算 1+1",
            "今天天气怎么样？",
            "测试LangGraph稳定性 - 这是最重要的测试",
            "如果没有类型错误，说明修复成功"
        ]

        success_count = 0
        for i, message in enumerate(messages, 1):
            try:
                print(f"\n📤 发送消息 {i}: {message}")
                result = chat_service.send_message(user_id, session_id, message)

                success_count += 1
                ai_response = result.get('ai_response', 'N/A')
                print(f"✅ 消息 {i} 发送成功")
                print(f"   AI回复: {ai_response[:80]}...")

            except Exception as e:
                error_str = str(e)
                print(f"❌ 消息 {i} 发送失败: {e}")

                # 检查是否是LangGraph类型错误
                if "'>' not supported between instances of 'str' and 'int'" in error_str:
                    print("🚨 发现LangGraph类型错误！修复失败！")
                    return False
                else:
                    print("📝 其他错误，不是LangGraph类型错误")

        print(f"\n📊 多条消息测试结果: {success_count}/{len(messages)} 成功")
        return success_count == len(messages)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False

def test_edge_cases():
    """测试边界情况"""
    print("\n🎯 边界情况测试")
    print("=" * 50)

    try:
        from src.domains.chat.service import ChatService

        chat_service = ChatService()

        # 测试特殊字符消息
        special_messages = [
            "测试特殊字符: !@#$%^&*()",
            "测试数字: 123456789",
            "测试中文: 这是一条包含中文的测试消息",
            "测试空格:    多个空格    ",
            "测试换行:\n第二行\n第三行"
        ]

        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        success_count = 0
        for i, message in enumerate(special_messages, 1):
            try:
                print(f"\n📤 测试特殊消息 {i}: {repr(message)}")
                result = chat_service.send_message(user_id, session_id, message)

                success_count += 1
                print(f"✅ 特殊消息 {i} 处理成功")

            except Exception as e:
                error_str = str(e)
                print(f"❌ 特殊消息 {i} 处理失败: {e}")

                if "'>' not supported between instances of 'str' and 'int'" in error_str:
                    print("🚨 发现LangGraph类型错误！")
                    return False

        print(f"\n📊 边界情况测试结果: {success_count}/{len(special_messages)} 成功")
        return success_count == len(special_messages)

    except Exception as e:
        print(f"❌ 边界测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 最终LangGraph类型错误修复验证")
    print("=" * 60)
    print("这个测试专门验证原来的类型错误是否已完全修复")
    print()

    # 检查服务器状态
    try:
        health_response = __import__('requests').get("http://localhost:8001/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ 服务器不可用，但ChatService测试仍然可以进行")
    except:
        print("📝 服务器不可用，将直接测试ChatService")

    # 执行核心测试
    basic_test = test_multiple_messages()
    edge_test = test_edge_cases()

    print("\n" + "=" * 60)
    print("🎯 最终验证结果总结")
    print("=" * 60)
    print(f"多条消息测试: {'✅ 通过' if basic_test else '❌ 失败'}")
    print(f"边界情况测试: {'✅ 通过' if edge_test else '❌ 失败'}")

    if basic_test and edge_test:
        print("\n🎉🎉🎉 完美！LangGraph类型错误已完全修复！🎉🎉🎉")
        print("✅ 根本解决方案成功:")
        print("   - 简化了ChatState结构")
        print("   - 移除了所有自定义字段")
        print("   - 通过config传递元数据")
        print("   - 避免了LangGraph内部版本号冲突")
        print("\n🏆 Chat API现在可以正常工作，不再出现类型比较错误！")
    else:
        print("\n❌ 修复未完全成功，需要进一步调试")

    print("\n🎯 验证完成！")

if __name__ == "__main__":
    main()