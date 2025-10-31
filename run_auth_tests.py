#!/usr/bin/env python3
"""
认证测试运行器

运行所有认证相关测试，确保系统正常工作
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def setup_test_environment():
    """设置测试环境"""
    print("🔧 设置测试环境...")

    # 强制设置正确的配置
    os.environ['AUTH_MICROSERVICE_URL'] = 'http://localhost:8987'
    os.environ['AUTH_PROJECT'] = 'tatake_backend'
    os.environ['ENVIRONMENT'] = 'development'
    os.environ['JWT_SKIP_SIGNATURE'] = 'true'
    os.environ['JWT_FALLBACK_SKIP_SIGNATURE'] = 'true'

    print(f"   AUTH_MICROSERVICE_URL = {os.environ['AUTH_MICROSERVICE_URL']}")
    print(f"   AUTH_PROJECT = {os.environ['AUTH_PROJECT']}")
    print(f"   ENVIRONMENT = {os.environ['ENVIRONMENT']}")

async def run_quick_tests():
    """运行快速测试"""
    print("🚀 运行快速认证测试...")
    print("=" * 50)

    tests_passed = 0
    tests_total = 0

    # 测试1: 认证服务连接
    tests_total += 1
    print("\\n1️⃣ 测试认证服务连接...")
    try:
        from src.services.auth.client import AuthMicroserviceClient
        client = AuthMicroserviceClient()
        health = await client.health_check()

        if 'code' in health and health['code'] == 200:
            print("   ✅ 健康检查通过")
            tests_passed += 1
        elif 'status' in health and health['status'] == 'healthy':
            print("   ✅ 健康检查通过（简单格式）")
            tests_passed += 1
        else:
            print(f"   ⚠️ 健康检查异常: {health}")
    except Exception as e:
        print(f"   ❌ 健康检查失败: {str(e)}")

    # 测试2: 游客令牌创建
    tests_total += 1
    print("\\n2️⃣ 测试游客令牌创建...")
    try:
        from src.services.auth.client import AuthMicroserviceClient
        client = AuthMicroserviceClient()
        result = await client.guest_init()

        if result.get('code') == 200:
            data = result.get('data', {})
            print("   ✅ 游客令牌创建成功")
            print(f"      用户ID: {data.get('user_id')}")
            print(f"      是否游客: {data.get('is_guest')}")
            tests_passed += 1
        else:
            print(f"   ❌ 游客令牌创建失败: {result}")
    except Exception as e:
        print(f"   ❌ 游客令牌创建失败: {str(e)}")

    # 测试3: JWT验证
    tests_total += 1
    print("\\n3️⃣ 测试JWT验证...")
    try:
        from src.services.auth.client import AuthMicroserviceClient
        from src.services.auth.dev_jwt_validator import validate_jwt_token_dev_result

        client = AuthMicroserviceClient()
        result = await client.guest_init()

        if result.get('code') == 200:
            token = result['data']['access_token']
            validation_result = await validate_jwt_token_dev_result(token)

            if validation_result.payload.get('sub') == result['data']['user_id']:
                print("   ✅ JWT验证成功")
                tests_passed += 1
            else:
                print("   ❌ JWT验证失败：用户ID不匹配")
    except Exception as e:
        print(f"   ❌ JWT验证失败: {str(e)}")

    # 测试4: 依赖注入
    tests_total += 1
    print("\\n4️⃣ 测试依赖注入...")
    try:
        from src.api.dependencies import get_current_user_id

        class MockCredentials:
            def __init__(self, token):
                self.credentials = token

        from src.services.auth.client import AuthMicroserviceClient
        client = AuthMicroserviceClient()
        result = await client.guest_init()

        if result.get('code') == 200:
            token = result['data']['access_token']
            mock_creds = MockCredentials(token)
            user_uuid = await get_current_user_id(mock_creds)

            if str(user_uuid) == result['data']['user_id']:
                print("   ✅ 依赖注入测试通过")
                tests_passed += 1
            else:
                print("   ❌ 依赖注入失败：用户ID不匹配")
    except Exception as e:
        print(f"   ❌ 依赖注入失败: {str(e)}")

    # 测试5: 配置验证
    tests_total += 1
    print("\\n5️⃣ 测试配置验证...")
    try:
        from src.services.auth.client import AuthMicroserviceClient
        client = AuthMicroserviceClient()

        if 'localhost:8987' in client.base_url:
            print("   ✅ 配置验证通过")
            tests_passed += 1
        else:
            print(f"   ❌ 配置验证失败：URL应该是localhost:8987，实际是{client.base_url}")
    except Exception as e:
        print(f"   ❌ 配置验证失败: {str(e)}")

    # 输出结果
    print("\\n" + "=" * 50)
    print(f"📊 测试结果: {tests_passed}/{tests_total} 通过")

    if tests_passed == tests_total:
        print("🎉 所有测试通过！认证系统正常工作！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查配置和服务状态")
        return False

async def run_comprehensive_tests():
    """运行完整测试"""
    print("🔬 运行完整测试套件...")

    try:
        import subprocess
        result = subprocess.run([
            'uv', 'run', 'pytest',
            'tests/integration/test_auth_integration_comprehensive.py',
            '-v', '--tb=short'
        ], capture_output=True, text=True)

        print("测试输出:")
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"运行pytest失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🧪 认证测试运行器")
    print("=" * 50)

    # 设置测试环境
    setup_test_environment()

    if len(sys.argv) > 1 and sys.argv[1] == '--comprehensive':
        # 运行完整测试
        success = asyncio.run(run_comprehensive_tests())
    else:
        # 运行快速测试
        success = asyncio.run(run_quick_tests())

    if success:
        print("\\n✅ 测试通过！可以启动服务了。")
        print("\\n🚀 启动命令:")
        print("   ./start_service.sh")
        print("   或者:")
        print("   export AUTH_MICROSERVICE_URL=http://localhost:8987")
        print("   uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload")
    else:
        print("\\n❌ 测试失败！")
        print("\\n🔧 故障排除:")
        print("1. 确保认证微服务在localhost:8987运行")
        print("2. 检查防火墙设置")
        print("3. 运行配置验证: python validate_config.py")
        print("4. 重新配置: python start_with_config.py")

if __name__ == "__main__":
    main()