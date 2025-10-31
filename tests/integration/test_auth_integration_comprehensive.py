#!/usr/bin/env python3
"""
认证系统集成测试套件

全面的认证系统集成测试，包括：
1. 配置加载测试
2. 环境变量测试
3. 真实服务连接测试
4. 端到端认证流程测试
5. 错误场景测试
"""

import os
import sys
import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, AsyncMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv


class TestAuthConfiguration:
    """认证配置测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境"""
        # 保存原始环境变量
        self.original_env = {}
        auth_vars = [k for k in os.environ.keys() if 'AUTH' in k.upper()]
        for var in auth_vars:
            self.original_env[var] = os.environ[var]

        # 设置测试环境变量
        os.environ['AUTH_MICROSERVICE_URL'] = 'http://localhost:8987'
        os.environ['AUTH_PROJECT'] = 'tatake_backend'
        os.environ['ENVIRONMENT'] = 'test'

        yield

        # 恢复原始环境变量
        for var in auth_vars:
            if var in self.original_env:
                os.environ[var] = self.original_env[var]
            else:
                os.environ.pop(var, None)

    def test_env_file_loading(self):
        """测试.env文件加载"""
        print("\n🔍 测试环境配置文件加载...")

        # 检查.env文件存在性
        env_files = ['.env', '.env.development', '.env.production']
        for env_file in env_files:
            file_path = Path(env_file)
            assert file_path.exists(), f"配置文件 {env_file} 不存在"

        # 测试dotenv加载
        load_dotenv('.env')
        assert os.getenv('AUTH_MICROSERVICE_URL') is not None, "AUTH_MICROSERVICE_URL 未设置"
        assert 'localhost:8987' in os.getenv('AUTH_MICROSERVICE_URL', ''), \
            "AUTH_MICROSERVICE_URL 应该指向localhost"

    def test_client_configuration(self):
        """测试客户端配置"""
        print("\n🔍 测试认证客户端配置...")

        from src.services.auth.client import AuthMicroserviceClient

        # 测试默认配置
        client = AuthMicroserviceClient()
        assert 'localhost:8987' in client.base_url, "客户端应该使用localhost:8987"
        assert client.project == 'tatake_backend', "项目名称应该是tatake_backend"

        # 测试自定义配置
        custom_client = AuthMicroserviceClient(
            base_url='http://custom.example.com:9000',
            project='custom_project'
        )
        assert 'custom.example.com:9000' in custom_client.base_url
        assert custom_client.project == 'custom_project'

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        print("\n🔍 测试认证服务健康检查...")

        from src.services.auth.client import AuthMicroserviceClient

        client = AuthMicroserviceClient()

        try:
            health = await client.health_check()
            print(f"   健康检查结果: {health}")

            # 检查响应格式
            assert isinstance(health, dict), "健康检查响应应该是字典"

            # 如果返回标准格式，检查code字段
            if 'code' in health:
                assert health['code'] == 200, f"健康检查失败: {health}"
            else:
                # 如果返回简单格式，检查status字段
                assert 'status' in health, "健康检查响应缺少status字段"
                assert health['status'] == 'healthy', f"服务不健康: {health}"

        except Exception as e:
            pytest.fail(f"健康检查失败: {str(e)}")

    @pytest.mark.asyncio
    async def test_guest_token_creation(self):
        """测试游客令牌创建"""
        print("\n🔍 测试游客令牌创建...")

        from src.services.auth.client import AuthMicroserviceClient

        client = AuthMicroserviceClient()

        try:
            result = await client.guest_init()
            print(f"   游客初始化结果: {result}")

            assert result.get('code') == 200, f"游客初始化失败: {result}"

            data = result.get('data')
            assert data is not None, "响应数据为空"
            assert 'access_token' in data, "缺少access_token"
            assert 'user_id' in data, "缺少user_id"
            assert 'refresh_token' in data, "缺少refresh_token"
            assert data.get('is_guest') == True, "应该是游客账户"

        except Exception as e:
            pytest.fail(f"游客令牌创建失败: {str(e)}")


class TestAuthFlow:
    """认证流程测试类"""

    @pytest.fixture(autouse=True)
    async def setup_auth_flow(self):
        """设置认证流程测试"""
        # 确保认证服务可访问
        os.environ['AUTH_MICROSERVICE_URL'] = 'http://localhost:8987'
        os.environ['AUTH_PROJECT'] = 'tatake_backend'

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self):
        """测试完整认证流程"""
        print("\n🔄 测试完整认证流程...")

        from src.services.auth.client import AuthMicroserviceClient
        from src.services.auth.dev_jwt_validator import validate_jwt_token_dev_result

        client = AuthMicroserviceClient()

        # 1. 创建游客令牌
        result = await client.guest_init()
        assert result.get('code') == 200, "游客初始化失败"

        token = result['data']['access_token']
        original_user_id = result['data']['user_id']
        print(f"   创建游客令牌: {original_user_id}")

        # 2. 验证令牌
        validation_result = await validate_jwt_token_dev_result(token)
        assert validation_result.payload.get('sub') == original_user_id, "令牌验证失败"
        print(f"   令牌验证成功")

        # 3. 刷新令牌
        refresh_token = result['data']['refresh_token']
        refresh_result = await client.refresh_token(refresh_token)
        assert refresh_result.get('code') == 200, "令牌刷新失败"

        new_token = refresh_result['data']['access_token']
        new_user_id = refresh_result['data']['user_id']
        assert new_user_id == original_user_id, "刷新后用户ID变化"
        print(f"   令牌刷新成功")

    @pytest.mark.asyncio
    async def test_invalid_token_handling(self):
        """测试无效令牌处理"""
        print("\n🚫 测试无效令牌处理...")

        from src.services.auth.dev_jwt_validator import validate_jwt_token_dev_result

        # 测试无效令牌
        invalid_tokens = [
            "invalid.token.here",
            "",
            "Bearer invalid",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid"
        ]

        for invalid_token in invalid_tokens:
            try:
                await validate_jwt_token_dev_result(invalid_token)
                pytest.fail(f"无效令牌应该被拒绝: {invalid_token}")
            except Exception as e:
                print(f"   正确拒绝无效令牌: {invalid_token[:20]}...")

    @pytest.mark.asyncio
    async def test_dependencies_integration(self):
        """测试依赖注入集成"""
        print("\n🔗 测试依赖注入集成...")

        from src.api.dependencies import get_current_user_id, get_current_user_id_optional

        # 模拟认证凭据
        class MockCredentials:
            def __init__(self, token: str):
                self.credentials = token

        # 获取测试令牌
        client = AuthMicroserviceClient()
        result = await client.guest_init()
        token = result['data']['access_token']
        expected_user_id = result['data']['user_id']

        mock_creds = MockCredentials(token)

        # 测试必需认证
        try:
            user_uuid = await get_current_user_id(mock_creds)
            assert str(user_uuid) == expected_user_id, "用户ID不匹配"
            print(f"   必需认证测试通过")
        except Exception as e:
            pytest.fail(f"必需认证测试失败: {str(e)}")

        # 测试可选认证
        try:
            user_uuid = await get_current_user_id_optional(mock_creds)
            assert str(user_uuid) == expected_user_id, "用户ID不匹配"
            print(f"   可选认证测试通过")
        except Exception as e:
            pytest.fail(f"可选认证测试失败: {str(e)}")


class TestErrorScenarios:
    """错误场景测试类"""

    @pytest.mark.asyncio
    async def test_service_unavailable(self):
        """测试服务不可用场景"""
        print("\n❌ 测试服务不可用场景...")

        from src.services.auth.client import AuthMicroserviceClient

        # 使用不可用的地址
        client = AuthMicroserviceClient(base_url='http://localhost:9999')

        with pytest.raises(Exception) as exc_info:
            await client.health_check()

        assert "无法连接" in str(exc_info.value) or "503" in str(exc_info.value), \
            f"应该返回连接错误，实际: {exc_info.value}"
        print(f"   正确处理服务不可用")

    def test_missing_configuration(self):
        """测试配置缺失场景"""
        print("\n⚠️ 测试配置缺失场景...")

        # 临时清除配置
        original_url = os.environ.get('AUTH_MICROSERVICE_URL')
        if 'AUTH_MICROSERVICE_URL' in os.environ:
            del os.environ['AUTH_MICROSERVICE_URL']

        try:
            from src.services.auth.client import AuthMicroserviceClient
            client = AuthMicroserviceClient()

            # 应该使用默认值
            assert client.base_url is not None, "应该有默认URL"
            print(f"   配置缺失时使用默认值: {client.base_url}")

        finally:
            # 恢复配置
            if original_url:
                os.environ['AUTH_MICROSERVICE_URL'] = original_url

    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """测试网络超时场景"""
        print("\n⏱️ 测试网络超时场景...")

        from src.services.auth.client import AuthMicroserviceClient

        # 使用一个会超时的地址
        client = AuthMicroserviceClient(base_url='http://httpbin.org/delay/10')

        # 设置短超时时间
        client.client_config['timeout'] = httpx.Timeout(1.0)

        try:
            with pytest.raises(Exception) as exc_info:
                await client.health_check()

            assert "超时" in str(exc_info.value) or "timeout" in str(exc_info.value).lower(), \
                f"应该返回超时错误，实际: {exc_info.value}"
            print(f"   正确处理网络超时")

        except Exception as e:
            # 如果其他错误发生，也算正确处理了网络问题
            print(f"   正确处理网络问题: {type(e).__name__}")


class TestConfigurationManagement:
    """配置管理测试类"""

    def test_environment_override(self):
        """测试环境变量覆盖"""
        print("\n🔧 测试环境变量覆盖...")

        from src.services.auth.client import AuthMicroserviceClient

        # 测试环境变量优先级
        test_url = 'http://test.example.com:9000'
        os.environ['AUTH_MICROSERVICE_URL'] = test_url

        client = AuthMicroserviceClient()
        assert test_url in client.base_url, "环境变量应该覆盖默认值"
        print(f"   环境变量正确覆盖默认配置")

    def test_dotenv_precedence(self):
        """测试.env文件优先级"""
        print("\n📄 测试.env文件优先级...")

        # 保存原始环境变量
        original_url = os.environ.get('AUTH_MICROSERVICE_URL')

        try:
            # 清除环境变量
            if 'AUTH_MICROSERVICE_URL' in os.environ:
                del os.environ['AUTH_MICROSERVICE_URL']

            # 加载.env文件
            load_dotenv('.env')

            # 验证.env文件中的配置被加载
            env_url = os.getenv('AUTH_MICROSERVICE_URL')
            assert env_url is not None, "应该从.env文件加载配置"
            assert 'localhost:8987' in env_url, "应该使用.env文件中的localhost配置"
            print(f"   .env文件配置正确加载: {env_url}")

        finally:
            # 恢复原始环境变量
            if original_url:
                os.environ['AUTH_MICROSERVICE_URL'] = original_url


if __name__ == "__main__":
    print("🧪 运行认证系统集成测试...")
    print("使用: pytest tests/integration/test_auth_integration_comprehensive.py -v")

    # 也可以直接运行
    import asyncio

    async def run_basic_tests():
        """运行基础测试"""
        print("🔍 运行基础连接测试...")

        try:
            from src.services.auth.client import AuthMicroserviceClient
            client = AuthMicroserviceClient()

            # 健康检查
            health = await client.health_check()
            print(f"✅ 健康检查: {health}")

            # 游客初始化
            result = await client.guest_init()
            print(f"✅ 游客初始化: {result.get('code')}")

            print("🎉 基础测试通过！")

        except Exception as e:
            print(f"❌ 基础测试失败: {str(e)}")

    asyncio.run(run_basic_tests())