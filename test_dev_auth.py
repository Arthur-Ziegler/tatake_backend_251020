#!/usr/bin/env python3
"""
开发环境认证测试脚本

测试开发环境JWT验证器的功能
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载开发环境配置
from dotenv import load_dotenv
load_dotenv('.env.development')

# 设置环境变量
os.environ.update({
    "ENVIRONMENT": "development",
    "JWT_SKIP_SIGNATURE": "true",
    "JWT_FALLBACK_SKIP_SIGNATURE": "true",
    "AUTH_MICROSERVICE_URL": "http://localhost:8987"
})

from src.services.auth.dev_jwt_validator import validate_jwt_token_dev, validate_jwt_token_dev_result
from src.services.auth.client import AuthMicroserviceClient


async def test_dev_auth_flow():
    """测试开发环境认证流程"""
    print("🧪 开发环境认证测试")
    print("=" * 50)

    # 1. 获取测试令牌
    print("1. 获取测试令牌...")
    try:
        client = AuthMicroserviceClient(base_url="http://localhost:8987")
        guest_result = await client.guest_init()

        if guest_result.get("code") == 200:
            token = guest_result["data"]["access_token"]
            user_id = guest_result["data"]["user_id"]
            is_guest = guest_result["data"]["is_guest"]
            print(f"✅ 获取测试令牌成功")
            print(f"   用户ID: {user_id}")
            print(f"   是否游客: {is_guest}")
            print(f"   令牌: {token[:50]}...")
        else:
            print(f"❌ 获取令牌失败: {guest_result}")
            return
    except Exception as e:
        print(f"❌ 获取令牌异常: {str(e)}")
        return

    # 2. 测试开发环境JWT验证（返回payload）
    print(f"\n2. 测试开发环境JWT验证（payload模式）...")
    try:
        payload = await validate_jwt_token_dev(token)
        print(f"✅ JWT验证成功")
        print(f"   用户ID: {payload.get('sub')}")
        print(f"   是否游客: {payload.get('is_guest')}")
        print(f"   令牌类型: {payload.get('token_type')}")
        print(f"   签发时间: {payload.get('iat')}")
        print(f"   过期时间: {payload.get('exp')}")
    except Exception as e:
        print(f"❌ JWT验证失败: {str(e)}")
        return

    # 3. 测试开发环境JWT验证（返回完整结果）
    print(f"\n3. 测试开发环境JWT验证（完整结果模式）...")
    try:
        result = await validate_jwt_token_dev_result(token)
        print(f"✅ JWT验证成功")
        print(f"   用户ID: {result.user_info.user_id}")
        print(f"   是否游客: {result.user_info.is_guest}")
        print(f"   令牌哈希: {result.user_info.token_hash[:16]}...")
        print(f"   缓存时间: {result.user_info.cache_time}")

        # 验证payload和user_info的一致性
        if result.payload.get('sub') == result.user_info.user_id:
            print(f"✅ Payload和用户信息一致")
        else:
            print(f"❌ Payload和用户信息不一致")
    except Exception as e:
        print(f"❌ JWT验证失败: {str(e)}")
        return

    # 4. 测试缓存机制
    print(f"\n4. 测试缓存机制...")
    try:
        from src.services.auth.dev_jwt_validator import get_dev_jwt_validator
        validator = get_dev_jwt_validator()

        # 第一次验证
        print("   第一次验证...")
        import time
        start_time = time.time()
        result1 = await validator.validate_token(token)
        first_duration = time.time() - start_time

        # 第二次验证
        print("   第二次验证...")
        start_time = time.time()
        result2 = await validator.validate_token(token)
        second_duration = time.time() - start_time

        print(f"✅ 缓存测试完成")
        print(f"   第一次耗时: {first_duration:.3f}秒")
        print(f"   第二次耗时: {second_duration:.3f}秒")

        # 检查缓存信息
        cache_info = validator.get_cache_info()
        print(f"   缓存状态: {cache_info}")

    except Exception as e:
        print(f"❌ 缓存测试失败: {str(e)}")

    # 5. 测试过期令牌
    print(f"\n5. 测试令牌过期检查...")
    try:
        # 创建一个过期的令牌（手动构造）
        expired_payload = {
            "sub": "test-user",
            "is_guest": True,
            "jwt_version": 1,
            "token_type": "access",
            "iat": 1640000000,  # 过去的时间戳
            "exp": 1640000001,  # 已过期
            "jti": "test-jti"
        }

        import jwt
        expired_token = jwt.encode(expired_payload, "dummy-secret", algorithm="HS256")

        # 尝试验证过期令牌
        await validate_jwt_token_dev(expired_token)
        print(f"❌ 过期令牌验证失败：应该抛出异常")

    except Exception as e:
        if "已过期" in str(e):
            print(f"✅ 过期令牌正确被拒绝")
        else:
            print(f"⚠️ 过期令牌验证异常: {str(e)}")

    print(f"\n🎉 开发环境认证测试完成!")


async def main():
    """主函数"""
    print("🔧 开发环境认证验证器测试")
    print(f"环境配置:")
    print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
    print(f"   JWT_SKIP_SIGNATURE: {os.getenv('JWT_SKIP_SIGNATURE')}")
    print(f"   JWT_FALLBACK_SKIP_SIGNATURE: {os.getenv('JWT_FALLBACK_SKIP_SIGNATURE')}")
    print(f"   AUTH_MICROSERVICE_URL: {os.getenv('AUTH_MICROSERVICE_URL')}")
    print("=" * 50)

    await test_dev_auth_flow()


if __name__ == "__main__":
    asyncio.run(main())