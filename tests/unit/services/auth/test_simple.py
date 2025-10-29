"""
简单的认证服务测试

测试认证服务的基本功能，确保集成正常工作。

作者：TaTakeKe团队
版本：1.0.0
"""

import pytest
from src.services.auth.client import AuthMicroserviceClient
from src.services.auth.jwt_validator import JWTValidationError


@pytest.mark.unit
class TestAuthBasic:
    """认证基本功能测试"""

    def test_auth_client_creation(self):
        """测试认证客户端创建"""
        client = AuthMicroserviceClient()
        assert client.base_url == "http://45.152.65.130:8987"
        assert client.project == "tatake_backend"

        client2 = AuthMicroserviceClient(
            base_url="http://test.com:8000",
            project="test_project"
        )
        assert client2.base_url == "http://test.com:8000"
        assert client2.project == "test_project"

    def test_jwt_validation_error(self):
        """测试JWT验证错误"""
        error = JWTValidationError("Test error")
        assert str(error) == "Test error"

    def test_client_url_handling(self):
        """测试客户端URL处理"""
        # 测试尾部斜杠移除
        client1 = AuthMicroserviceClient(base_url="http://test.com/")
        client2 = AuthMicroserviceClient(base_url="http://test.com")
        assert client1.base_url == client2.base_url

    @pytest.mark.asyncio
    async def test_client_methods_exist(self):
        """测试客户端方法存在"""
        client = AuthMicroserviceClient()

        # 验证所有主要方法都存在
        assert hasattr(client, 'guest_init')
        assert hasattr(client, 'wechat_register')
        assert hasattr(client, 'wechat_login')
        assert hasattr(client, 'wechat_bind')
        assert hasattr(client, 'refresh_token')
        assert hasattr(client, 'email_send_code')
        assert hasattr(client, 'email_register')
        assert hasattr(client, 'email_login')
        assert hasattr(client, 'email_bind')
        assert hasattr(client, 'phone_send_code')
        assert hasattr(client, 'phone_verify')
        assert hasattr(client, 'get_public_key')
        assert hasattr(client, '_make_request')

        # 验证方法是可调用的
        assert callable(getattr(client, 'guest_init'))
        assert callable(getattr(client, 'wechat_register'))
        assert callable(getattr(client, '_make_request'))