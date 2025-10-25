#!/usr/bin/env python3
"""
测试现有会话的LangGraph修复效果

使用之前创建的会话ID进行测试，避免认证问题
"""

import requests

def test_existing_session():
    """测试现有会话"""
    print("🎯 测试现有会话的LangGraph修复效果")
    print("=" * 50)

    base_url = "http://localhost:8001"

    # 使用之前日志中的session_id
    session_id = "bdd402b0-7daa-4a25-bb2a-2ddcdc334d8c"  # 从之前的测试中获取
    print(f"📋 使用现有会话ID: {session_id}")

    # 测试发送消息
    print("🎯 发送测试消息...")
    try:
        response = requests.post(
            f"{base_url}/chat/sessions/{session_id}/send",
            json={"message": "验证LangGraph修复效果 - 这条消息应该能成功发送"},
            timeout=30
        )

        print(f"📊 响应状态码: {response.status_code}")

        if response.status_code == 200:
            result_data = response.json()
            print("✅ 🎉 消息发送成功！")
            print(f"   AI回复: {result_data.get('data', {}).get('ai_response', 'N/A')[:100]}...")
            print(f"   状态: {result_data.get('data', {}).get('status', 'N/A')}")

            # 检查是否有类型错误
            error_message = result_data.get('message', '')
            if "'>' not supported between instances of 'str' and 'int'" in error_message:
                print("🚨 仍然存在LangGraph类型错误！")
                return False
            else:
                print("✅ 没有发现类型错误")
                return True
        else:
            print(f"❌ 消息发送失败: {response.status_code}")
            try:
                error_data = response.json()
                error_message = error_data.get('message', 'Unknown error')
                print(f"   错误信息: {error_message}")

                if "'>' not supported between instances of 'str' and 'int'" in error_message:
                    print("🚨 仍然是LangGraph类型错误！")
                else:
                    print("📝 错误类型已改变")
            except:
                print(f"   原始响应: {response.text[:200]}...")
            return False

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_list_sessions():
    """列出会话，找到可用的session_id"""
    print("\n📋 列出可用会话")
    print("=" * 50)

    base_url = "http://localhost:8001"

    try:
        response = requests.get(f"{base_url}/chat/sessions?limit=10", timeout=10)

        if response.status_code == 200:
            sessions_data = response.json()
            sessions = sessions_data.get('data', {}).get('sessions', [])

            print(f"📊 找到 {len(sessions)} 个会话:")
            for i, session in enumerate(sessions, 1):
                session_id = session.get('session_id', 'N/A')
                title = session.get('title', 'N/A')
                created_at = session.get('created_at', 'N/A')
                print(f"  {i}. ID: {session_id}")
                print(f"     标题: {title}")
                print(f"     创建时间: {created_at}")
                print()

            if sessions:
                return sessions[0].get('session_id')
            else:
                print("❌ 没有找到会话")
                return None
        else:
            print(f"❌ 获取会话列表失败: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

if __name__ == "__main__":
    print("🚀 测试现有会话的LangGraph修复效果")
    print()

    # 检查服务器状态
    try:
        health_response = requests.get("http://localhost:8001/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ 服务器不可用")
            exit(1)
    except:
        print("❌ 无法连接到服务器")
        exit(1)

    # 先获取最新的会话
    latest_session_id = test_list_sessions()

    # 测试会话
    if latest_session_id:
        print(f"📋 测试最新会话: {latest_session_id}")

        base_url = "http://localhost:8001"
        try:
            response = requests.post(
                f"{base_url}/chat/sessions/{latest_session_id}/send",
                json={"message": "最终验证：LangGraph类型错误修复测试"},
                timeout=30
            )

            if response.status_code == 200:
                result_data = response.json()
                print("✅ 🎉 最新会话测试成功！")
                print(f"   AI回复: {result_data.get('data', {}).get('ai_response', 'N/A')[:100]}...")
            else:
                print(f"❌ 最新会话测试失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 最新会话测试请求失败: {e}")

    # 测试原有会话
    test_existing_session()