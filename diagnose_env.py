#!/usr/bin/env python3
"""
环境变量诊断工具

诊断AUTH_MICROSERVICE_URL配置的来源
"""

import os
import sys
from pathlib import Path

def diagnose_env_variables():
    """诊断环境变量"""
    print("🔍 环境变量诊断工具")
    print("=" * 50)

    # 检查.env文件内容
    print("\n📁 检查.env文件内容:")
    env_files = ['.env', '.env.development', '.env.production']

    for env_file in env_files:
        print(f"\n   {env_file}:")
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if 'AUTH_MICROSERVICE_URL' in line:
                        print(f"     {line}")
        else:
            print("     文件不存在")

    # 检查当前环境变量
    print(f"\n🌍 当前环境变量:")
    print(f"   AUTH_MICROSERVICE_URL = '{os.getenv('AUTH_MICROSERVICE_URL', '未设置')}'")
    print(f"   AUTH_PROJECT = '{os.getenv('AUTH_PROJECT', '未设置')}'")
    print(f"   ENVIRONMENT = '{os.getenv('ENVIRONMENT', '未设置')}'")

    # 检查所有相关环境变量
    print(f"\n🔍 所有AUTH相关环境变量:")
    for key, value in os.environ.items():
        if 'AUTH' in key.upper():
            print(f"   {key} = {value}")

    # 检查进程环境
    print(f"\n⚙️  进程信息:")
    print(f"   当前工作目录: {os.getcwd()}")
    print(f"   Python路径: {sys.executable}")
    print(f"   脚本路径: {__file__}")

    # 尝试加载dotenv并检查结果
    print(f"\n📦 测试dotenv加载:")
    try:
        from dotenv import load_dotenv

        print("   加载前:", os.getenv('AUTH_MICROSERVICE_URL', '未设置'))

        load_dotenv('.env')
        print("   加载.env后:", os.getenv('AUTH_MICROSERVICE_URL', '未设置'))

        load_dotenv('.env.development')
        print("   加载.env.development后:", os.getenv('AUTH_MICROSERVICE_URL', '未设置'))

        load_dotenv('.env.production')
        print("   加载.env.production后:", os.getenv('AUTH_MICROSERVICE_URL', '未设置'))

    except ImportError:
        print("   python-dotenv未安装")

def force_local_config():
    """强制设置本地配置"""
    print(f"\n🔧 强制设置本地配置...")

    # 直接设置环境变量
    os.environ['AUTH_MICROSERVICE_URL'] = 'http://localhost:8987'
    os.environ['AUTH_PROJECT'] = 'tatake_backend'
    os.environ['ENVIRONMENT'] = 'development'

    print(f"   已设置 AUTH_MICROSERVICE_URL = {os.environ['AUTH_MICROSERVICE_URL']}")
    print(f"   已设置 AUTH_PROJECT = {os.environ['AUTH_PROJECT']}")
    print(f"   已设置 ENVIRONMENT = {os.environ['ENVIRONMENT']}")

async def test_connection():
    """测试连接"""
    print(f"\n🔗 测试认证服务连接...")

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.services.auth.client import AuthMicroserviceClient

        client = AuthMicroserviceClient()
        print(f"   客户端URL: {client.base_url}")

        health = await client.health_check()
        print(f"   连接结果: {health}")

        return health.get('code') == 200

    except Exception as e:
        print(f"   连接失败: {str(e)}")
        return False

async def main():
    """主函数"""
    # 1. 诊断环境变量
    diagnose_env_variables()

    # 2. 强制设置本地配置
    force_local_config()

    # 3. 测试连接
    success = await test_connection()

    if success:
        print(f"\n✅ 诊断完成：连接成功！")
        print(f"   建议：在启动业务服务前设置环境变量：")
        print(f"   export AUTH_MICROSERVICE_URL=http://localhost:8987")
    else:
        print(f"\n❌ 诊断完成：连接失败！")
        print(f"   建议：检查认证服务是否在localhost:8987正常运行")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())