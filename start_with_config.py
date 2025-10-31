#!/usr/bin/env python3
"""
带配置启动的业务服务

确保业务服务使用正确的认证微服务配置
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """设置正确的环境配置"""
    print("🔧 设置认证微服务配置...")

    # 1. 优先级：环境变量 > .env文件 > 默认值
    # 如果当前环境变量指向远程地址，强制覆盖
    current_url = os.getenv('AUTH_MICROSERVICE_URL', '')
    if current_url and '45.152.65.130' in current_url:
        print("   检测到远程配置，强制覆盖为本地配置")
        os.environ['AUTH_MICROSERVICE_URL'] = 'http://localhost:8987'

    # 2. 确保关键配置存在
    required_configs = {
        'AUTH_MICROSERVICE_URL': 'http://localhost:8987',
        'AUTH_PROJECT': 'tatake_backend',
        'ENVIRONMENT': 'development',
        'JWT_SKIP_SIGNATURE': 'true',
        'JWT_FALLBACK_SKIP_SIGNATURE': 'true'
    }

    for key, default_value in required_configs.items():
        if not os.getenv(key):
            os.environ[key] = default_value
            print(f"   设置 {key} = {default_value}")

    # 3. 输出最终配置
    print(f"\n✅ 最终配置:")
    print(f"   AUTH_MICROSERVICE_URL = {os.getenv('AUTH_MICROSERVICE_URL')}")
    print(f"   AUTH_PROJECT = {os.getenv('AUTH_PROJECT')}")
    print(f"   ENVIRONMENT = {os.getenv('ENVIRONMENT')}")

def create_startup_script():
    """创建启动脚本"""
    print("📝 创建启动脚本...")

    startup_script = '''#!/bin/bash
# 业务服务启动脚本

echo "🚀 启动TaKeKe后端服务..."

# 设置认证微服务配置
export AUTH_MICROSERVICE_URL=http://localhost:8987
export AUTH_PROJECT=tatake_backend
export ENVIRONMENT=development

# 开发环境JWT配置
export JWT_SKIP_SIGNATURE=true
export JWT_FALLBACK_SKIP_SIGNATURE=true

# 输出配置信息
echo "认证微服务配置:"
echo "   AUTH_MICROSERVICE_URL=$AUTH_MICROSERVICE_URL"
echo "   AUTH_PROJECT=$AUTH_PROJECT"
echo "   ENVIRONMENT=$ENVIRONMENT"

# 启动服务
echo "启动FastAPI服务..."
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
'''

    with open('start_service.sh', 'w') as f:
        f.write(startup_script)

    # 设置执行权限
    os.chmod('start_service.sh', 0o755)
    print("✅ 已创建启动脚本: start_service.sh")

def create_service_config():
    """创建服务配置文件"""
    print("📄 创建服务配置...")

    config_content = """# 服务配置文件
# 可以通过环境变量或此文件配置认证微服务

[auth_service]
url = "http://localhost:8987"
project = "tatake_backend"
timeout = 30

[environment]
name = "development"
debug = true

[jwt]
skip_signature = true
fallback_skip_signature = true
"""

    with open('service_config.ini', 'w') as f:
        f.write(config_content)

    print("✅ 已创建服务配置: service_config.ini")

def main():
    """主函数"""
    print("🔧 TaKeKe后端服务配置工具")
    print("=" * 50)

    # 1. 设置环境配置
    setup_environment()

    # 2. 创建启动脚本
    create_startup_script()

    # 3. 创建服务配置文件
    create_service_config()

    print("\n🎉 配置完成！")
    print("\n📋 启动方式（选择一种）:")
    print("方式1: 使用启动脚本")
    print("   ./start_service.sh")
    print("\n方式2: 手动设置环境变量后启动")
    print("   export AUTH_MICROSERVICE_URL=http://localhost:8987")
    print("   uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload")
    print("\n方式3: 使用配置启动脚本")
    print("   uv run python start_with_config.py")

    print("\n🔍 验证配置:")
    print("   uv run python validate_config.py")

if __name__ == "__main__":
    main()