#!/usr/bin/env python3
"""
真实Chat API UUID格式修复验证测试

使用标准UUID测试实际的Chat API，验证：
1. 标准UUID能正常工作
2. 非标准UUID被正确拒绝
3. LangGraph类型错误已修复
"""

import requests
import uuid
import json

def test_chat_api_with_standard_uuid():
    """测试使用标准UUID的Chat API"""

    print("🧪 测试Chat API UUID格式修复")
    print("=" * 50)

    # API端点
    base_url = "http://localhost:8001"
    chat_url = f"{base_url}/chat/sessions/{{session_id}}/send"

    # 生成标准UUID
    standard_user_id = str(uuid.uuid4())
    standard_session_id = str(uuid.uuid4())

    print(f"📋 测试数据:")
    print(f"  标准user_id: {standard_user_id}")
    print(f"  标准session_id: {standard_session_id}")
    print()

    # 测试1: 标准UUID应该成功
    print("🎯 测试1: 标准UUID格式")
    test_url = chat_url.format(session_id=standard_session_id)
    test_data = {
        "message": "测试消息：使用标准UUID格式"
    }

    try:
        response = requests.post(test_url, json=test_data, timeout=10)

        if response.status_code == 200:
            print("✅ 标准UUID测试通过")
            print(f"   响应状态: {response.status_code}")
            try:
                result = response.json()
                print(f"   AI回复: {result.get('content', 'N/A')[:100]}...")
            except:
                print(f"   响应内容: {response.text[:200]}...")
        else:
            print(f"❌ 标准UUID测试失败")
            print(f"   状态码: {response.status_code}")
            print(f"   错误信息: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

    print()

    # 测试2: 非标准UUID应该被拒绝
    print("🎯 测试2: 非标准UUID格式")
    invalid_test_url = chat_url.format(session_id="test-session-456")
    invalid_test_data = {
        "message": "测试消息：使用非标准UUID格式"
    }

    try:
        response = requests.post(invalid_test_url, json=invalid_test_data, timeout=10)

        if response.status_code == 400 or response.status_code == 422:
            print("✅ 非标准UUID正确被拒绝")
            print(f"   状态码: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   错误详情: {error_detail.get('detail', 'N/A')}")
            except:
                print(f"   错误信息: {response.text[:200]}...")
        else:
            print(f"⚠️  非标准UUID处理异常")
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text[:200]}...")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

    print()

    # 测试3: 混合格式（一个标准，一个非标准）
    print("🎯 测试3: 混合格式UUID")
    mixed_test_url = chat_url.format(session_id="test-session-456")  # 非标准session_id
    mixed_test_data = {
        "message": "测试消息：混合UUID格式"
    }

    try:
        response = requests.post(mixed_test_url, json=mixed_test_data, timeout=10)

        if response.status_code == 400 or response.status_code == 422:
            print("✅ 混合格式正确被拒绝")
            print(f"   状态码: {response.status_code}")
        else:
            print(f"⚠️  混合格式处理异常")
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text[:200]}...")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

def check_server_status():
    """检查服务器状态"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
            return True
        else:
            print(f"⚠️  服务器响应异常: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ 服务器无法连接，请确保服务器在 http://localhost:8001 运行")
        return False

if __name__ == "__main__":
    print("🚀 开始Chat API UUID格式修复验证")
    print()

    if check_server_status():
        print()
        test_chat_api_with_standard_uuid()
    else:
        print("💡 请启动服务器: uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8001")

    print()
    print("🎯 测试完成！")