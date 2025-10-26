"""
SMS客户端单元测试

测试短信发送客户端的抽象接口、Mock实现和阿里云实现。
采用TDD方式，先写测试再实现代码。

测试覆盖：
- SMSClientInterface抽象接口
- MockSMSClient模拟客户端
- AliyunSMSClient阿里云客户端（Mock测试）
- get_sms_client()工厂函数
- 环境变量切换测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from abc import ABC, abstractmethod
import os

from src.domains.auth.sms_client import (
    SMSClientInterface,
    MockSMSClient,
    AliyunSMSClient,
    get_sms_client
)


class TestSMSClientInterface:
    """SMS客户端接口测试"""

    def test_interface_is_abstract(self):
        """测试接口是抽象的，不能直接实例化"""
        with pytest.raises(TypeError):
            SMSClientInterface()

    def test_interface_has_abstract_method(self):
        """测试接口定义了抽象方法"""
        assert hasattr(SMSClientInterface, 'send_code')
        assert getattr(SMSClientInterface.send_code, '__isabstractmethod__', False) is True


class TestMockSMSClient:
    """Mock SMS客户端测试"""

    @pytest.fixture
    def mock_client(self):
        """创建Mock SMS客户端实例"""
        return MockSMSClient()

    def test_mock_client_inherits_interface(self, mock_client):
        """测试Mock客户端继承接口"""
        assert isinstance(mock_client, SMSClientInterface)

    @pytest.mark.asyncio
    async def test_send_code_success(self, mock_client, capsys):
        """测试发送验证码成功"""
        result = await mock_client.send_code("13800138000", "123456")

        assert result["success"] is True
        assert "message_id" in result
        assert result["message_id"] == "mock_123"

        # 验证控制台输出
        captured = capsys.readouterr()
        assert "📱 [MOCK SMS]" in captured.out
        assert "13800138000" in captured.out
        assert "123456" in captured.out

    @pytest.mark.asyncio
    async def test_send_code_different_inputs(self, mock_client):
        """测试不同输入的发送"""
        test_cases = [
            ("15900000000", "111111"),
            ("18888888888", "999999"),
            ("10000000000", "000000"),
        ]

        for phone, code in test_cases:
            result = await mock_client.send_code(phone, code)
            assert result["success"] is True
            assert result["message_id"] == "mock_123"

    @pytest.mark.asyncio
    async def test_mock_client_always_succeeds(self, mock_client):
        """测试Mock客户端总是成功"""
        # 即使输入异常数据也能成功（Mock特性）
        result = await mock_client.send_code("", "")
        assert result["success"] is True


class TestAliyunSMSClient:
    """阿里云SMS客户端测试"""

    @pytest.fixture
    def aliyun_env_vars(self):
        """设置阿里云环境变量"""
        env_vars = {
            "ALIYUN_ACCESS_KEY_ID": "test_access_key",
            "ALIYUN_ACCESS_KEY_SECRET": "test_access_secret",
            "ALIYUN_SMS_SIGN_NAME": "测试签名",
            "ALIYUN_SMS_TEMPLATE_CODE": "SMS_123456789",
            "ALIYUN_SMS_ENDPOINT": "dysmsapi.ap-southeast-1.aliyuncs.com"
        }

        # 保存原环境变量
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        yield env_vars

        # 恢复原环境变量
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

    def test_aliyun_client_inherits_interface(self, aliyun_env_vars):
        """测试阿里云客户端继承接口"""
        client = AliyunSMSClient()
        assert isinstance(client, SMSClientInterface)

    @patch('src.domains.auth.sms_client.Client')
    @patch('src.domains.auth.sms_client.Config')
    @pytest.mark.asyncio
    async def test_send_code_success(self, mock_config, mock_client_class, aliyun_env_vars):
        """测试阿里云发送验证码成功"""
        # Mock阿里云SDK
        mock_client_instance = AsyncMock()
        mock_response = Mock()
        mock_response.response_code = "OK"
        mock_response.message_id = "aliyun_msg_123"

        mock_client_instance.send_message_with_template_async.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        client = AliyunSMSClient()
        result = await client.send_code("13800138000", "123456")

        assert result["success"] is True
        assert result["message_id"] == "aliyun_msg_123"

        # 验证调用参数
        mock_client_instance.send_message_with_template_async.assert_called_once()
        call_args = mock_client_instance.send_message_with_template_async.call_args[0][0]

        assert call_args.to == "8613800138000"
        assert call_args.from_ == "测试签名"
        assert call_args.template_code == "SMS_123456789"
        assert '"code": "123456"' in call_args.template_param

    @patch('src.domains.auth.sms_client.Client')
    @patch('src.domains.auth.sms_client.Config')
    @pytest.mark.asyncio
    async def test_send_code_failure(self, mock_config, mock_client_class, aliyun_env_vars):
        """测试阿里云发送验证码失败"""
        # Mock阿里云SDK失败情况
        mock_client_instance = AsyncMock()
        mock_response = Mock()
        mock_response.response_code = "InvalidParameter"

        mock_client_instance.send_message_with_template_async.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        client = AliyunSMSClient()
        result = await client.send_code("13800138000", "123456")

        assert result["success"] is False
        assert "message_id" not in result

    @patch('src.domains.auth.sms_client.Client')
    @patch('src.domains.auth.sms_client.Config')
    @pytest.mark.asyncio
    async def test_send_code_exception(self, mock_config, mock_client_class, aliyun_env_vars):
        """测试阿里云SDK抛出异常"""
        # Mock阿里云SDK异常
        mock_client_instance = AsyncMock()
        mock_client_instance.send_message_with_template_async.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client_instance

        client = AliyunSMSClient()

        with pytest.raises(Exception, match="Network error"):
            await client.send_code("13800138000", "123456")

    def test_aliyun_client_missing_env_vars(self):
        """测试缺少环境变量时的处理"""
        # 清除环境变量
        keys_to_remove = [
            "ALIYUN_ACCESS_KEY_ID",
            "ALIYUN_ACCESS_KEY_SECRET",
            "ALIYUN_SMS_SIGN_NAME",
            "ALIYUN_SMS_TEMPLATE_CODE"
        ]

        original_env = {}
        for key in keys_to_remove:
            original_env[key] = os.environ.get(key)
            os.environ.pop(key, None)

        try:
            with pytest.raises(Exception):  # 应该抛出配置异常
                AliyunSMSClient()
        finally:
            # 恢复环境变量
            for key, original_value in original_env.items():
                if original_value is not None:
                    os.environ[key] = original_value


class TestGetSMSClient:
    """SMS客户端工厂函数测试"""

    @patch.dict(os.environ, {"SMS_MODE": "mock"})
    def test_get_mock_client(self):
        """测试获取Mock客户端"""
        client = get_sms_client()
        assert isinstance(client, MockSMSClient)
        assert type(client).__name__ == "MockSMSClient"

    @patch('src.domains.auth.sms_client.AliyunSMSClient')
    @patch.dict(os.environ, {"SMS_MODE": "aliyun"})
    def test_get_aliyun_client(self, mock_aliyun_class):
        """测试获取阿里云客户端"""
        mock_aliyun_instance = Mock()
        mock_aliyun_class.return_value = mock_aliyun_instance

        client = get_sms_client()

        mock_aliyun_class.assert_called_once()
        assert client == mock_aliyun_instance

    @patch.dict(os.environ, {}, clear=True)
    def test_get_default_client(self):
        """测试默认获取Mock客户端"""
        client = get_sms_client()
        assert isinstance(client, MockSMSClient)

    @patch.dict(os.environ, {"SMS_MODE": "unknown"})
    def test_get_unknown_client(self):
        """测试未知模式时返回Mock客户端"""
        client = get_sms_client()
        assert isinstance(client, MockSMSClient)

    @patch('src.domains.auth.sms_client.AliyunSMSClient')
    @patch.dict(os.environ, {"SMS_MODE": "ALIYUN"})  # 测试大写
    def test_case_insensitive_mode(self, mock_aliyun_class):
        """测试模式名称大小写不敏感"""
        mock_aliyun_instance = Mock()
        mock_aliyun_class.return_value = mock_aliyun_instance

        client = get_sms_client()

        # 应该识别大写的ALIYUN
        mock_aliyun_class.assert_called_once()
        assert client == mock_aliyun_instance


class TestSMSClientIntegration:
    """SMS客户端集成测试"""

    @pytest.mark.asyncio
    async def test_both_clients_same_interface(self):
        """测试两种客户端都实现相同接口"""
        mock_client = MockSMSClient()

        # Mock阿里云客户端环境
        with patch.dict(os.environ, {
            "ALIYUN_ACCESS_KEY_ID": "test_key",
            "ALIYUN_ACCESS_KEY_SECRET": "test_secret",
            "ALIYUN_SMS_SIGN_NAME": "test",
            "ALIYUN_SMS_TEMPLATE_CODE": "test",
            "SMS_MODE": "aliyun"
        }):
            with patch('src.domains.auth.sms_client.Client'), \
                 patch('src.domains.auth.sms_client.Config'):
                aliyun_client = get_sms_client()

        # 两种客户端都应该实现相同的接口
        assert isinstance(mock_client, SMSClientInterface)
        assert isinstance(aliyun_client, SMSClientInterface)

        # 两种客户端都应该有send_code方法
        assert hasattr(mock_client, 'send_code')
        assert hasattr(aliyun_client, 'send_code')
        assert callable(mock_client.send_code)
        assert callable(aliyun_client.send_code)

    @pytest.mark.asyncio
    async def test_client_return_format_consistency(self):
        """测试客户端返回格式一致性"""
        mock_client = MockSMSClient()
        result = await mock_client.send_code("13800138000", "123456")

        # 验证返回格式
        assert isinstance(result, dict)
        assert "success" in result
        assert isinstance(result["success"], bool)

        if result["success"]:
            assert "message_id" in result
            assert isinstance(result["message_id"], str)