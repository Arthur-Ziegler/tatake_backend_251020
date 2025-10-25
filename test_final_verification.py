#!/usr/bin/env python3
"""
最终验证：Chat API LangGraph类型错误修复效果

测试真实的API调用，验证错误是否已经完全修复
"""

import requests
import uuid
import json

def test_chat_api_final():
    """最终验证Chat API修复效果"""
    print("🎯 最终验证：Chat API LangGraph类型错误修复")
    print("=" * 60)

    base_url = "http://localhost:8001"

    # 测试1: 创建用户
    print("📋 步骤1: 创建Guest用户")
    try:
        response = requests.post(f"{base_url}/auth/guest/init", timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data["data"]["user_id"]
            print(f"✅ 用户创建成功: {user_id}")
        else:
            print(f"❌ 用户创建失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 用户创建请求失败: {e}")
        return False

    # 测试2: 创建会话
    print("\n📋 步骤2: 创建聊天会话")
    try:
        session_response = requests.post(f"{base_url}/chat/sessions", json={
            "user_id": user_id,
            "title": "最终验证测试会话"
        }, timeout=10)
        if session_response.status_code == 200:
            session_data = session_response.json()
            session_id = session_data["data"]["session_id"]
            print(f"✅ 会话创建成功: {session_id}")
        else:
            print(f"❌ 会话创建失败: {session_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 会话创建请求失败: {e}")
        return False

    # 测试3: 发送消息 - 这里应该不再出现类型错误
    print("\n📋 步骤3: 发送聊天消息（关键测试）")
    try:
        message_response = requests.post(
            f"{base_url}/chat/sessions/{session_id}/send",
            json={"message": "LangGraph类型错误修复验证测试消息"},
            timeout=30  # 增加超时时间，因为需要调用AI
        )

        print(f"📊 响应状态码: {message_response.status_code}")

        if message_response.status_code == 200:
            result_data = message_response.json()
            print("✅ 🎉 消息发送成功！LangGraph类型错误已修复！")
            print(f"   AI回复: {result_data.get('data', {}).get('ai_response', 'N/A')[:100]}...")
            print(f"   状态: {result_data.get('data', {}).get('status', 'N/A')}")
            return True
        else:
            print(f"❌ 消息发送失败: {message_response.status_code}")
            try:
                error_data = message_response.json()
                error_message = error_data.get('message', 'Unknown error')
                print(f"   错误信息: {error_message}")

                # 检查是否还是类型错误
                if "'>' not supported between instances of 'str' and 'int'" in error_message:
                    print("🚨 仍然是LangGraph类型错误！修复失败！")
                else:
                    print("📝 错误类型已改变，LangGraph类型错误可能已修复")
            except:
                print(f"   原始响应: {message_response.text[:200]}...")
            return False

    except Exception as e:
        print(f"❌ 消息发送请求失败: {e}")
        return False

def test_multiple_messages():
    """测试多条消息发送，确保稳定性"""
    print("\n📋 步骤4: 多条消息稳定性测试")

    base_url = "http://localhost:8001"

    # 重新创建用户和会话
    try:
        # 创建用户
        user_response = requests.post(f"{base_url}/auth/guest/init", timeout=10)
        user_data = user_response.json()
        user_id = user_data["data"]["user_id"]

        # 创建会话
        session_response = requests.post(f"{base_url}/chat/sessions", json={
            "user_id": user_id,
            "title": "多条消息测试"
        }, timeout=10)
        session_data = session_response.json()
        session_id = session_data["data"]["session_id"]

        # 发送多条消息
        messages = [
            "第一条测试消息",
            "第二条测试消息",
            "请帮我计算 1+1",
            "今天天气怎么样？",
            "测试LangGraph稳定性"
        ]

        success_count = 0
        for i, message in enumerate(messages, 1):
            try:
                response = requests.post(
                    f"{base_url}/chat/sessions/{session_id}/send",
                    json={"message": message},
                    timeout=30
                )

                if response.status_code == 200:
                    success_count += 1
                    print(f"  ✅ 消息 {i}: 发送成功")
                else:
                    print(f"  ❌ 消息 {i}: 发送失败 ({response.status_code})")

            except Exception as e:
                print(f"  ❌ 消息 {i}: 请求失败 ({e})")

        print(f"\n📊 多条消息测试结果: {success_count}/{len(messages)} 成功")
        return success_count == len(messages)

    except Exception as e:
        print(f"❌ 多条消息测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始最终验证测试")
    print("验证LangGraph类型错误修复效果...")
    print()

    # 检查服务器状态
    try:
        health_response = requests.get("http://localhost:8001/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ 服务器不可用")
            exit(1)
    except:
        print("❌ 无法连接到服务器")
        print("💡 请确保服务器运行: uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8001")
        exit(1)

    # 执行测试
    basic_test = test_chat_api_final()
    stability_test = test_multiple_messages() if basic_test else False

    print("\n" + "=" * 60)
    print("🎯 最终验证结果总结")
    print("=" * 60)
    print(f"基本功能测试: {'✅ 通过' if basic_test else '❌ 失败'}")
    print(f"稳定性测试:   {'✅ 通过' if stability_test else '❌ 失败'}")

    if basic_test and stability_test:
        print("\n🎉🎉🎉 完美！LangGraph类型错误已完全修复！🎉🎉🎉")
        print("Chat API现在可以正常工作，不再出现类型比较错误。")
    elif basic_test:
        print("\n✅ 基本功能已修复，但稳定性需要进一步测试。")
    else:
        print("\n❌ 修复未完全成功，需要进一步调试。")

    print("\n🎯 验证完成！")