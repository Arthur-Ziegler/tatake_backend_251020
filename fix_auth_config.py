#!/usr/bin/env python3
"""
认证微服务配置修复工具

彻底解决认证微服务连接问题
"""

import os
import sys
from pathlib import Path

def create_production_env():
    """创建生产环境配置文件"""
    print("📝 创建生产环境配置文件...")

    env_content = """# 生产环境配置
ENVIRONMENT=production

# 认证微服务配置
AUTH_MICROSERVICE_URL=http://localhost:8987
AUTH_PROJECT=tatake_backend

# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key-for-tatake-backend-2024
JWT_ALGORITHM=HS256

# 开发环境配置（仅在开发时使用）
# JWT_SKIP_SIGNATURE=false
# JWT_FALLBACK_SKIP_SIGNATURE=false

# 应用配置
DEBUG=false
"""

    with open(".env.production", "w") as f:
        f.write(env_content)

    print("✅ 已创建 .env.production")

def create_default_env():
    """创建默认环境配置文件"""
    print("📝 创建默认环境配置文件...")

    env_content = """# 默认环境配置
# 根据实际部署环境修改以下配置

# 环境类型 (development/production)
ENVIRONMENT=development

# 认证微服务配置 - 最重要的配置
AUTH_MICROSERVICE_URL=http://localhost:8987
AUTH_PROJECT=tatake_backend

# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key-for-tatake-backend-2024
JWT_ALGORITHM=HS256

# 开发环境特殊配置
JWT_SKIP_SIGNATURE=true
JWT_FALLBACK_SKIP_SIGNATURE=true

# 调试模式
DEBUG=true
"""

    with open(".env", "w") as f:
        f.write(env_content)

    print("✅ 已创建 .env")

def update_auth_client():
    """更新认证客户端配置"""
    print("🔧 更新认证客户端默认配置...")

    client_file = "src/services/auth/client.py"

    with open(client_file, "r") as f:
        content = f.read()

    # 修改默认URL为localhost
    old_default = 'os.getenv("AUTH_MICROSERVICE_URL", "http://45.152.65.130:8987")'
    new_default = 'os.getenv("AUTH_MICROSERVICE_URL", "http://localhost:8987")'

    if old_default in content:
        content = content.replace(old_default, new_default)

        with open(client_file, "w") as f:
            f.write(content)

        print("✅ 已更新认证客户端默认URL为localhost")
    else:
        print("⚠️ 认证客户端配置已修改或未找到默认配置")

def create_config_validator():
    """创建配置验证工具"""
    print("🔍 创建配置验证工具...")

    validator_code = '''#!/usr/bin/env python3
"""
配置验证工具

验证认证微服务配置是否正确
"""

import os
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

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
    print("\\n" + "=" * 50)
    if config_valid:
        print("🎉 配置验证通过！")
        print("认证微服务配置正确，可以正常使用。")
    else:
        print("❌ 配置验证失败！")
        print("请检查认证微服务配置并重新验证。")

        print("\\n📋 修复建议:")
        print("1. 确保设置了 AUTH_MICROSERVICE_URL=http://localhost:8987")
        print("2. 确保设置了 AUTH_PROJECT=tatake_backend")
        print("3. 确保认证微服务在指定地址正常运行")
        print("4. 检查网络连接和防火墙设置")

if __name__ == "__main__":
    asyncio.run(main())
'''

    with open("validate_config.py", "w") as f:
        f.write(validator_code)

    # 设置执行权限
    os.chmod("validate_config.py", 0o755)

    print("✅ 已创建配置验证工具: validate_config.py")

def main():
    """主修复函数"""
    print("🛠️ 认证微服务配置修复工具")
    print("=" * 50)

    # 1. 创建配置文件
    create_default_env()
    create_production_env()

    # 2. 更新认证客户端
    update_auth_client()

    # 3. 创建配置验证工具
    create_config_validator()

    print("\\n🎉 配置修复完成！")
    print("\\n📋 后续步骤:")
    print("1. 运行配置验证: python validate_config.py")
    print("2. 重启业务服务以加载新配置")
    print("3. 测试认证功能")
    print("4. 根据环境需要调整配置文件")

    print("\\n🔧 如果问题仍然存在，请检查:")
    print("- 认证微服务是否在 localhost:8987 正常运行")
    print("- 防火墙设置是否阻止了连接")
    print("- Docker网络配置（如果使用容器部署）")

if __name__ == "__main__":
    main()