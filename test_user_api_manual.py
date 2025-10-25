#!/usr/bin/env python3
"""
测试User API修复效果

手动测试脚本，验证UUID类型绑定错误是否已修复。
这个脚本会启动实际的API调用，测试User领域的端点。
"""

import requests
import json
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8001"

def test_guest_init() -> Dict[str, Any]:
    """测试游客初始化"""
    logger.info("🚀 测试游客初始化...")

    try:
        response = requests.post(f"{API_BASE_URL}/api/v3/auth/guest-init")

        if response.status_code == 200:
            data = response.json()
            logger.info("✅ 游客初始化成功")
            return data
        else:
            logger.error(f"❌ 游客初始化失败: {response.status_code} - {response.text}")
            return {}

    except Exception as e:
        logger.error(f"❌ 游客初始化异常: {e}")
        return {}

def test_get_user_profile(access_token: str) -> bool:
    """测试获取用户信息（原始出错点）"""
    logger.info("📝 测试获取用户信息...")

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(f"{API_BASE_URL}/user/profile", headers=headers)

        if response.status_code == 200:
            data = response.json()
            logger.info("✅ 获取用户信息成功")
            logger.info(f"   用户ID: {data['data']['id']}")
            logger.info(f"   昵称: {data['data']['nickname']}")
            logger.info(f"   是否为游客: {data['data']['is_guest']}")
            return True
        else:
            logger.error(f"❌ 获取用户信息失败: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ 获取用户信息异常: {e}")
        return False

def test_update_user_profile(access_token: str) -> bool:
    """测试更新用户信息（另一个原始出错点）"""
    logger.info("📝 测试更新用户信息...")

    headers = {"Authorization": f"Bearer {access_token}"}
    update_data = {"nickname": "测试修复用户"}

    try:
        response = requests.put(f"{API_BASE_URL}/user/profile",
                              headers=headers,
                              json=update_data)

        if response.status_code == 200:
            data = response.json()
            logger.info("✅ 更新用户信息成功")
            logger.info(f"   用户ID: {data['data']['id']}")
            logger.info(f"   昵称: {data['data']['nickname']}")
            logger.info(f"   更新字段: {data['data']['updated_fields']}")
            return True
        else:
            logger.error(f"❌ 更新用户信息失败: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ 更新用户信息异常: {e}")
        return False

def test_welcome_gift_apis(access_token: str) -> bool:
    """测试欢迎礼包相关API"""
    logger.info("🎁 测试欢迎礼包API...")

    headers = {"Authorization": f"Bearer {access_token}"}

    # 测试领取欢迎礼包
    try:
        response = requests.post(f"{API_BASE_URL}/user/welcome-gift/claim", headers=headers)

        if response.status_code == 200:
            data = response.json()
            logger.info("✅ 领取欢迎礼包成功")
            logger.info(f"   获得积分: {data['data']['points_granted']}")
            logger.info(f"   事务组: {data['data']['transaction_group']}")
        else:
            logger.error(f"❌ 领取欢迎礼包失败: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ 领取欢迎礼包异常: {e}")
        return False

    # 测试获取礼包历史
    try:
        response = requests.get(f"{API_BASE_URL}/user/welcome-gift/history", headers=headers)

        if response.status_code == 200:
            data = response.json()
            logger.info("✅ 获取礼包历史成功")
            logger.info(f"   历史记录数: {data['data']['total_count']}")
            return True
        else:
            logger.error(f"❌ 获取礼包历史失败: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ 获取礼包历史异常: {e}")
        return False

def check_server_health() -> bool:
    """检查服务器健康状态"""
    logger.info("🏥 检查服务器健康状态...")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ 服务器健康")
            return True
        else:
            logger.error(f"❌ 服务器不健康: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ 无法连接到服务器: {e}")
        logger.info("💡 请确保API服务器在 http://localhost:8001 运行")
        return False

def main():
    """主测试流程"""
    print("🧪 User API 修复验证测试")
    print("=" * 50)

    # 1. 检查服务器状态
    if not check_server_health():
        print("\n❌ 服务器未运行，测试终止")
        return

    # 2. 创建测试用户
    guest_data = test_guest_init()
    if not guest_data or "data" not in guest_data:
        print("\n❌ 无法创建测试用户，测试终止")
        return

    access_token = guest_data["data"]["access_token"]
    user_id = guest_data["data"]["user_id"]

    print(f"\n👤 测试用户创建成功")
    print(f"   用户ID: {user_id}")
    print(f"   访问令牌: {access_token[:20]}...")

    # 3. 测试核心API
    test_results = []

    print("\n🧪 开始API测试...")
    print("-" * 30)

    # 测试获取用户信息
    test_results.append(("获取用户信息", test_get_user_profile(access_token)))

    # 测试更新用户信息
    test_results.append(("更新用户信息", test_update_user_profile(access_token)))

    # 测试欢迎礼包API
    test_results.append(("欢迎礼包API", test_welcome_gift_apis(access_token)))

    # 4. 总结测试结果
    print("\n📊 测试结果总结")
    print("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1

    print(f"\n📈 总体结果: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！UUID类型绑定错误已修复。")
    else:
        print("⚠️  部分测试失败，可能需要进一步检查。")

    print("\n💡 修复说明:")
    print("   - 在User领域内添加了UUID到字符串的类型转换")
    print("   - 使用 _ensure_string_user_id() 函数确保数据库查询兼容性")
    print("   - 使用 _get_user_by_string_id() 函数统一处理用户查询")
    print("   - 所有User API端点现在都能正确处理UUID参数")

if __name__ == "__main__":
    main()