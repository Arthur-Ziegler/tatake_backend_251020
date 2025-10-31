#!/usr/bin/env python3
"""
配置验证工具

验证认证微服务配置是否正确
"""

import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境配置
print("📁 加载环境配置文件...")
load_dotenv('.env')
load_dotenv('.env.development')
load_dotenv('.env.production')

async def validate_auth_config():
    """验证认证配置"""
    print("🔍 验证认证微服务配置...")

    # 1. 检查环境变量
    auth_url = os.getenv("AUTH_MICROSERVICE_URL")
    project = os.getenv("AUTH_PROJECT")

    print(f"   AUTH_MICROSERVICE_URL: {auth_url}")
    print(f"   AUTH_PROJECT: {project}")

    if not auth_url:
        print("❌ AUTH_MICROSERVICE_URL 未设置")
        return False

    if not project:
        print("❌ AUTH_PROJECT 未设置")
        return False

    # 2. 测试连接
    try:
        from src.services.auth.client import AuthMicroserviceClient

        client = AuthMicroserviceClient()
        health = await client.health_check()

        if health.get("code") == 200:
            print("✅ 认证微服务连接正常")
            return True
        else:
            print(f"❌ 认证微服务响应异常: {health}")
            return False

    except Exception as e:
        print(f"❌ 认证微服务连接失败: {str(e)}")
        return False

def check_env_files():
    """检查环境配置文件"""
    print("📁 检查环境配置文件...")

    env_files = [".env", ".env.development", ".env.production"]

    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"✅ 找到配置文件: {env_file}")

            # 检查关键配置
            with open(env_file, "r") as f:
                content = f.read()

            if "AUTH_MICROSERVICE_URL" in content:
                print(f"   ✓ 包含 AUTH_MICROSERVICE_URL 配置")
            else:
                print(f"   ❌ 缺少 AUTH_MICROSERVICE_URL 配置")
        else:
            print(f"❌ 配置文件不存在: {env_file}")

async def main():
    """主函数"""
    print("🔧 配置验证工具")
    print("=" * 50)

    # 1. 检查环境配置文件
    check_env_files()

    # 2. 验证认证配置
    config_valid = await validate_auth_config()

    # 3. 输出结果
    print("\n" + "=" * 50)
    if config_valid:
        print("🎉 配置验证通过！")
        print("认证微服务配置正确，可以正常使用。")
    else:
        print("❌ 配置验证失败！")
        print("请检查认证微服务配置并重新验证。")

        print("\n📋 修复建议:")
        print("1. 确保设置了 AUTH_MICROSERVICE_URL=http://localhost:8987")
        print("2. 确保设置了 AUTH_PROJECT=tatake_backend")
        print("3. 确保认证微服务在指定地址正常运行")
        print("4. 检查网络连接和防火墙设置")

if __name__ == "__main__":
    asyncio.run(main())
