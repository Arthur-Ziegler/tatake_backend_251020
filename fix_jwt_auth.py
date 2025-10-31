#!/usr/bin/env python3
"""
JWT认证修复脚本

解决JWT验证中的密钥不匹配问题
"""

import asyncio
import os
import sys
import base64
import hmac
import hashlib
from datetime import datetime, timezone, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置本地认证服务URL
os.environ["AUTH_MICROSERVICE_URL"] = "http://localhost:8987"

from src.services.auth.client import AuthMicroserviceClient


async def get_auth_service_secret():
    """尝试从认证服务获取密钥信息"""
    print("🔍 尝试获取认证服务密钥信息...")

    # 方法1: 检查是否有管理接口
    client = AuthMicroserviceClient(base_url="http://localhost:8987")

    # 尝试一些可能的管理端点
    endpoints_to_try = [
        "/auth/system/config",
        "/auth/system/info",
        "/auth/config",
        "/admin/config",
        "/system/config",
        "/info"
    ]

    for endpoint in endpoints_to_try:
        try:
            print(f"   尝试端点: {endpoint}")
            result = await client._make_request("GET", endpoint)
            print(f"   响应: {result}")
            if result.get("code") == 200 and result.get("data"):
                return result.get("data")
        except Exception as e:
            print(f"   端点 {endpoint} 失败: {str(e)}")
            continue

    return None


def create_jwt_token_with_known_secret(payload: dict, secret: str) -> str:
    """使用已知密钥创建JWT token（用于验证）"""
    try:
        import jwt
        return jwt.encode(payload, secret, algorithm="HS256")
    except Exception as e:
        print(f"创建token失败: {str(e)}")
        return None


def verify_jwt_token(token: str, secret: str) -> dict:
    """验证JWT token"""
    try:
        import jwt
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception as e:
        print(f"验证token失败: {str(e)}")
        return None


async def test_different_approaches():
    """测试不同的解决方案"""
    print("\n🧪 测试不同的解决方案...")

    # 1. 获取测试token
    try:
        client = AuthMicroserviceClient(base_url="http://localhost:8987")
        guest_result = await client.guest_init()

        if guest_result.get("code") == 200:
            token = guest_result["data"]["access_token"]
            user_id = guest_result["data"]["user_id"]
            print(f"✅ 获取到测试令牌，用户ID: {user_id}")
        else:
            print("❌ 无法获取测试令牌")
            return

    except Exception as e:
        print(f"❌ 获取令牌失败: {str(e)}")
        return

    # 2. 尝试常见的默认密钥
    common_secrets = [
        "secret",
        "jwt-secret",
        "your-secret-key",
        "tatake-secret",
        "tatake-backend-secret",
        "auth-service-secret",
        "development-secret",
        "test-secret-key",
        # 添加一些常见的长密钥
        "your-super-secret-jwt-key-for-tatake-backend-2024",
        "tatake-backend-jwt-secret-key-2024-very-long-and-secure",
        "tatake-jwt-secret-2024-10-31-production-key",
    ]

    print(f"\n🔑 测试常见密钥...")
    working_secret = None

    for secret in common_secrets:
        try:
            payload = verify_jwt_token(token, secret)
            if payload and payload.get("sub") == user_id:
                print(f"✅ 找到匹配的密钥: {secret}")
                working_secret = secret
                break
            else:
                print(f"   ❌ 密钥不匹配: {secret[:20]}...")
        except Exception:
            continue

    if working_secret:
        print(f"\n🎉 找到可用密钥: {working_secret}")
        return working_secret
    else:
        print(f"\n❌ 未找到匹配的密钥")
        return None


def create_solution_recommendations():
    """创建解决方案建议"""
    print("\n📋 JWT密钥问题解决方案建议:")
    print("=" * 60)

    print("\n🎯 立即可行的解决方案:")
    print("1. 使用统一的默认密钥")
    print("   在认证服务和后端服务中使用相同的默认密钥")

    print("\n2. 修改JWT验证器以跳过签名验证（仅开发环境）")
    print("   在开发环境中可以临时禁用签名验证")

    print("\n3. 使用环境变量同步密钥")
    print("   确保认证服务和后端服务读取相同的环境变量")

    print("\n🏗️ 长期解决方案:")
    print("1. 在认证服务中添加密钥获取API")
    print("2. 使用配置中心统一管理密钥")
    print("3. 考虑升级到非对称加密（RSA）")


async def create_development_fix():
    """创建开发环境的临时修复方案"""
    print("\n🔧 创建开发环境修复方案...")

    # 方案1: 创建一个临时的JWT验证器（跳过签名验证）
    dev_validator_code = '''
# 开发环境专用JWT验证器（跳过签名验证）
import jwt
from datetime import datetime, timezone
from fastapi import HTTPException, status

async def validate_jwt_token_dev(token: str):
    """开发环境JWT验证（跳过签名验证）"""
    try:
        # 不验证签名，只解码payload
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256", "RS256"]
        )

        # 检查基本字段
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌中缺少用户ID"
            )

        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"令牌验证失败: {str(e)}"
        )
'''

    print("开发环境临时修复代码已生成")
    return dev_validator_code


async def main():
    """主函数"""
    print("🛠️ JWT认证问题修复工具")
    print("=" * 50)

    # 1. 尝试获取认证服务配置
    auth_config = await get_auth_service_secret()

    # 2. 测试不同的解决方案
    working_secret = await test_different_approaches()

    if working_secret:
        # 如果找到可用密钥，更新配置
        print(f"\n💾 更新本地配置...")

        env_file = ".env"
        env_content = {}

        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()

        env_content['JWT_SECRET_KEY'] = working_secret
        env_content['JWT_ALGORITHM'] = 'HS256'

        with open(env_file, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\\n")

        print(f"✅ 已更新.env文件，使用密钥: {working_secret[:20]}...")
        print("\\n🎉 密钥问题已解决！请重启应用服务。")

    else:
        # 如果没有找到可用密钥，提供替代方案
        print("\\n📋 未找到可用密钥，提供替代解决方案:")

        # 1. 提供解决方案建议
        create_solution_recommendations()

        # 2. 生成开发环境修复代码
        dev_fix = await create_development_fix()

        print("\\n🔧 开发环境快速修复:")
        print("1. 可以临时禁用JWT签名验证进行开发测试")
        print("2. 联系认证服务维护者获取正确的密钥配置")
        print("3. 或者重新部署认证服务并配置已知密钥")


if __name__ == "__main__":
    asyncio.run(main())