#!/usr/bin/env python3
"""
JWT密钥同步脚本

从认证微服务获取密钥配置并同步到本地环境
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置本地认证服务URL
os.environ["AUTH_MICROSERVICE_URL"] = "http://localhost:8987"

from src.services.auth.client import AuthMicroserviceClient


async def check_auth_service_jwt_config():
    """检查认证服务的JWT配置"""
    print("🔍 检查认证服务JWT配置...")

    try:
        client = AuthMicroserviceClient(base_url="http://localhost:8987")

        # 获取公钥信息
        result = await client.get_public_key()
        print(f"公钥端点响应: {result}")

        # 检查认证服务的环境变量或配置
        # 这里可能需要检查认证服务的配置文件或环境变量

    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")


def create_local_jwt_env():
    """创建本地JWT环境配置"""
    print("\n📝 创建本地JWT配置...")

    # 常见的JWT密钥配置
    jwt_configs = {
        # 方案1: 使用常见的测试密钥
        "COMMON_SECRET": "your-super-secret-jwt-key-for-tatake-backend-2024",

        # 方案2: 使用更强的密钥
        "STRONG_SECRET": "tatake-backend-jwt-secret-key-2024-very-long-and-secure",

        # 方案3: 使用时间戳生成的密钥
        "TIMESTAMP_SECRET": "tatake-jwt-secret-2024-10-31-production-key",
    }

    print("请选择要使用的JWT密钥配置:")
    for i, (name, key) in enumerate(jwt_configs.items(), 1):
        print(f"{i}. {name}: {key[:20]}...")

    return jwt_configs


def update_env_file(secret_key: str):
    """更新.env文件中的JWT配置"""
    env_file = ".env"

    print(f"\n📄 更新 {env_file} 文件...")

    # 读取现有.env文件
    env_content = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()

    # 更新JWT配置
    env_content['JWT_SECRET_KEY'] = secret_key
    env_content['JWT_ALGORITHM'] = 'HS256'

    # 写入.env文件
    with open(env_file, 'w') as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")

    print(f"✅ 已更新JWT配置:")
    print(f"   JWT_SECRET_KEY={secret_key[:20]}...")
    print(f"   JWT_ALGORITHM=HS256")


async def test_jwt_with_key(token: str, secret_key: str):
    """测试指定密钥的JWT验证"""
    print(f"\n🧪 测试密钥: {secret_key[:20]}...")

    # 临时设置环境变量
    os.environ["JWT_SECRET_KEY"] = secret_key

    try:
        from src.services.auth.jwt_validator import validate_jwt_token_simple

        result = await validate_jwt_token_simple(token)
        if result:
            print("✅ 密钥验证成功!")
            return True
        else:
            print("❌ 密钥验证失败")
            return False

    except Exception as e:
        print(f"❌ 密钥验证异常: {str(e)}")
        return False


async def main():
    """主函数"""
    print("🔐 JWT密钥同步工具")
    print("=" * 50)

    # 1. 检查认证服务配置
    await check_auth_service_jwt_config()

    # 2. 获取可用密钥配置
    jwt_configs = create_local_jwt_env()

    # 3. 获取一个测试token
    print("\n🎫 获取测试令牌...")
    try:
        client = AuthMicroserviceClient(base_url="http://localhost:8987")
        guest_result = await client.guest_init()

        if guest_result.get("code") == 200:
            token = guest_result["data"]["access_token"]
            print(f"✅ 获取到测试令牌: {token[:30]}...")
        else:
            print("❌ 无法获取测试令牌")
            return

    except Exception as e:
        print(f"❌ 获取令牌失败: {str(e)}")
        return

    # 4. 测试不同的密钥配置
    print(f"\n🔍 测试不同密钥配置...")

    working_key = None
    for config_name, secret_key in jwt_configs.items():
        if await test_jwt_with_key(token, secret_key):
            working_key = secret_key
            print(f"✅ 找到可用密钥配置: {config_name}")
            break

    # 5. 如果找到可用密钥，更新配置
    if working_key:
        update_env_file(working_key)
        print("\n🎉 JWT密钥同步完成!")
        print("请重启你的应用服务以使配置生效。")
    else:
        print("\n❌ 未找到可用的密钥配置")
        print("可能需要检查认证服务的具体密钥配置")

        # 提供手动配置指导
        print("\n📋 手动配置指导:")
        print("1. 检查认证服务的JWT_SECRET_KEY环境变量")
        print("2. 或者检查认证服务的配置文件")
        print("3. 将相同的密钥配置到本地的.env文件中")
        print("4. 确保JWT_ALGORITHM设置为HS256")


if __name__ == "__main__":
    asyncio.run(main())