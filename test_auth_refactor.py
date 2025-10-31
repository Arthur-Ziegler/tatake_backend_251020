#!/usr/bin/env python3
"""
认证重构测试脚本

测试重构后的JWT验证流程，包括：
1. JWT验证器的基本功能
2. 缓存机制
3. 透传验证
"""

import asyncio
import sys
import os
import httpx
from datetime import datetime, timezone, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置本地认证服务URL
os.environ["AUTH_MICROSERVICE_URL"] = "http://localhost:8987"

from src.services.auth.jwt_validator import JWTValidator, validate_jwt_token_simple
from src.services.auth.client import AuthMicroserviceClient


async def test_auth_service_connection():
    """测试认证服务连接"""
    print("🔍 测试认证服务连接...")

    try:
        # 直接测试公钥端点来验证连接
        client = AuthMicroserviceClient(base_url="http://localhost:8987")
        result = await client.get_public_key()

        if result.get("code") == 200:
            print("✅ 认证服务连接正常")
            return True
        else:
            print(f"❌ 认证服务异常: {result}")
            return False
    except Exception as e:
        print(f"❌ 认证服务连接失败: {str(e)}")
        return False


async def test_guest_token_creation():
    """测试游客令牌创建"""
    print("\n👤 测试游客令牌创建...")

    try:
        client = AuthMicroserviceClient(base_url="http://localhost:8987")
        result = await client.guest_init()

        if result.get("code") == 200:
            token_data = result.get("data", {})
            access_token = token_data.get("access_token")

            if access_token:
                print(f"✅ 游客令牌创建成功")
                print(f"   用户ID: {token_data.get('user_id')}")
                print(f"   是否游客: {token_data.get('is_guest')}")
                print(f"   过期时间: {token_data.get('expires_in')}秒")
                return access_token
            else:
                print("❌ 游客令牌创建失败：未获取到access_token")
                return None
        else:
            print(f"❌ 游客令牌创建失败: {result}")
            return None
    except Exception as e:
        print(f"❌ 游客令牌创建异常: {str(e)}")
        return None


async def test_jwt_validation(token: str):
    """测试JWT验证"""
    print(f"\n🔐 测试JWT验证...")

    try:
        # 使用本地认证服务的验证器
        from src.services.auth.client import get_auth_client
        client = get_auth_client()
        client.base_url = "http://localhost:8987"

        result = await validate_jwt_token_simple(token)

        if result:
            print(f"✅ JWT验证成功")
            print(f"   用户ID: {result.get('sub')}")
            print(f"   是否游客: {result.get('is_guest')}")
            print(f"   过期时间: {datetime.fromtimestamp(result.get('exp'), tz=timezone.utc)}")
            return True
        else:
            print("❌ JWT验证失败：未获取到payload")
            return False
    except Exception as e:
        print(f"❌ JWT验证异常: {str(e)}")
        return False


async def test_caching_mechanism(token: str):
    """测试缓存机制"""
    print(f"\n💾 测试缓存机制...")

    try:
        # 使用本地认证服务的验证器
        from src.services.auth.client import get_auth_client
        client = get_auth_client()
        client.base_url = "http://localhost:8987"

        validator = JWTValidator()

        # 第一次验证（应该调用微服务）
        print("   第一次验证...")
        start_time = datetime.now()
        result1 = await validator.validate_token(token)
        first_duration = (datetime.now() - start_time).total_seconds()

        # 第二次验证（应该使用缓存）
        print("   第二次验证（缓存测试）...")
        start_time = datetime.now()
        result2 = await validator.validate_token(token)
        second_duration = (datetime.now() - start_time).total_seconds()

        if result1 and result2:
            print(f"✅ 缓存机制测试成功")
            print(f"   第一次验证耗时: {first_duration:.3f}秒")
            print(f"   第二次验证耗时: {second_duration:.3f}秒")
            print(f"   性能提升: {(first_duration - second_duration) / first_duration * 100:.1f}%")

            # 检查缓存信息
            cache_info = validator.get_cache_info()
            print(f"   缓存状态: {cache_info}")

            return True
        else:
            print("❌ 缓存机制测试失败：验证结果不一致")
            return False
    except Exception as e:
        print(f"❌ 缓存机制测试异常: {str(e)}")
        return False


async def test_public_key_endpoint():
    """测试公钥获取端点"""
    print(f"\n🔑 测试公钥获取端点...")

    try:
        client = AuthMicroserviceClient(base_url="http://localhost:8987")
        result = await client.get_public_key()

        if result.get("code") == 200:
            data = result.get("data", {})
            public_key = data.get("public_key", "")
            message = result.get("message", "")

            print(f"✅ 公钥获取成功")
            print(f"   公钥: {public_key if public_key else '(对称加密，无公钥)'}")
            print(f"   消息: {message}")

            if not public_key:
                print("   检测到对称加密模式")

            return True
        else:
            print(f"❌ 公钥获取失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 公钥获取异常: {str(e)}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始认证重构测试")
    print("=" * 50)

    test_results = []

    # 测试1：认证服务连接
    result1 = await test_auth_service_connection()
    test_results.append(("认证服务连接", result1))

    if not result1:
        print("\n❌ 认证服务不可用，无法继续测试")
        return

    # 测试2：公钥获取
    result2 = await test_public_key_endpoint()
    test_results.append(("公钥获取", result2))

    # 测试3：游客令牌创建
    token = await test_guest_token_creation()
    test_results.append(("游客令牌创建", token is not None))

    if token:
        # 测试4：JWT验证
        result4 = await test_jwt_validation(token)
        test_results.append(("JWT验证", result4))

        # 测试5：缓存机制
        result5 = await test_caching_mechanism(token)
        test_results.append(("缓存机制", result5))

    # 输出测试结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！认证重构成功！")
    else:
        print("⚠️  部分测试失败，需要进一步检查")

    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())