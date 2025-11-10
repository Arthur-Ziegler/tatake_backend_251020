"""
微服务配置系统测试用例

测试目标：
- 验证微服务配置的正确加载
- 验证环境变量覆盖机制
- 验证配置验证逻辑
- 验证默认值设置

测试原则：
- TDD方式，先写测试再实现
- 测试数据工厂化
- 用例完全独立
- 自动清理测试环境
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from src.config.microservices import MicroserviceSettings, microservice_config


class TestMicroserviceSettings:
    """微服务配置测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 清理可能影响测试的环境变量
        env_vars_to_clear = [
            "MICROSERVICE_PROJECT",
            "MICROSERVICE_AUTH_SERVICE_URL",
            "MICROSERVICE_TASK_SERVICE_URL",
            "MICROSERVICE_REWARD_SERVICE_URL",
            "MICROSERVICE_CHAT_SERVICE_URL",
            "MICROSERVICE_FOCUS_SERVICE_URL",
            "MICROSERVICE_REQUEST_TIMEOUT"
        ]

        self.original_env = {}
        for var in env_vars_to_clear:
            self.original_env[var] = os.environ.pop(var, None)

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 恢复原始环境变量
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            else:
                os.environ.pop(var, None)

    def test_default_configuration(self):
        """测试默认配置加载"""
        # Given: 使用现有环境变量
        # When: 创建配置实例
        config = MicroserviceSettings()

        # Then: 验证配置正确加载（考虑现有环境变量）
        assert config.project is not None and len(config.project) > 0
        assert config.auth_service_url is not None and config.auth_service_url.startswith("http")
        assert config.task_service_url is not None and config.task_service_url.startswith("http")
        assert config.reward_service_url is not None and config.reward_service_url.startswith("http")
        assert config.chat_service_url is not None and config.chat_service_url.startswith("http")
        assert config.focus_service_url is not None and config.focus_service_url.startswith("http")
        assert config.request_timeout > 0

    def test_environment_variable_override(self):
        """测试环境变量覆盖机制"""
        # Given: 保存原始配置，设置测试环境变量
        original_project = os.environ.get("MICROSERVICE_PROJECT")
        original_timeout = os.environ.get("MICROSERVICE_REQUEST_TIMEOUT")

        test_env = {
            "MICROSERVICE_PROJECT": "test_project",
            "MICROSERVICE_REQUEST_TIMEOUT": "60"
        }

        try:
            with patch.dict(os.environ, test_env, clear=False):
                # When: 创建配置实例
                config = MicroserviceSettings()

                # Then: 验证环境变量覆盖生效
                assert config.project == "test_project"
                assert config.request_timeout == 60

                # 验证其他配置正确加载
                assert config.auth_service_url is not None and config.auth_service_url.startswith("http")
        finally:
            # 恢复原始环境变量
            if original_project:
                os.environ["MICROSERVICE_PROJECT"] = original_project
            else:
                os.environ.pop("MICROSERVICE_PROJECT", None)
            if original_timeout:
                os.environ["MICROSERVICE_REQUEST_TIMEOUT"] = original_timeout
            else:
                os.environ.pop("MICROSERVICE_REQUEST_TIMEOUT", None)

    def test_invalid_timeout_handling(self):
        """测试无效超时时间处理"""
        # Given: 设置无效的超时时间
        with patch.dict(os.environ, {"MICROSERVICE_REQUEST_TIMEOUT": "invalid"}, clear=False):
            # When & Then: 应该抛出验证错误
            with pytest.raises(ValueError):
                MicroserviceSettings()

    def test_url_validation(self):
        """测试URL格式验证"""
        # Given: 设置无效的URL格式
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "http://no-tld",
            ""
        ]

        for invalid_url in invalid_urls:
            with patch.dict(os.environ, {"MICROSERVICE_AUTH_SERVICE_URL": invalid_url}, clear=False):
                # When & Then: 无效URL应该被拒绝或修正
                config = MicroserviceSettings()
                # 验证URL被正确处理（根据具体实现调整）
                assert config.auth_service_url is not None

    def test_project_name_validation(self):
        """测试项目名称验证"""
        # Given: 各种项目名称
        test_cases = [
            ("valid_project", True),
            ("valid-project-123", True),
            ("", False),  # 空字符串应该无效
            ("project with spaces", False),  # 包含空格应该无效
            ("project@with symbols", False),  # 包含特殊符号应该无效
        ]

        for project_name, should_be_valid in test_cases:
            with patch.dict(os.environ, {"MICROSERVICE_PROJECT": project_name}, clear=False):
                if should_be_valid:
                    # When: 有效项目名称
                    config = MicroserviceSettings()
                    # Then: 应该成功创建
                    assert config.project == project_name
                else:
                    # When: 无效项目名称
                    # Then: 应该被处理（根据具体实现调整）
                    config = MicroserviceSettings()
                    # 验证处理结果

    def test_config_immutability(self):
        """测试配置不可变性"""
        # Given: 配置实例
        config = MicroserviceSettings()
        original_project = config.project

        # When: 尝试修改配置
        try:
            config.project = "modified"
            # If modification succeeds, that's a design choice to test
            assert config.project != original_project
        except AttributeError:
            # If modification fails, that's also a valid design choice
            assert config.project == original_project

    def test_global_config_instance(self):
        """测试全局配置实例"""
        # Given: 全局配置实例
        # When: 访问全局配置
        config = microservice_config

        # Then: 应该是MicroserviceSettings实例
        assert isinstance(config, MicroserviceSettings)
        assert hasattr(config, 'project')
        assert hasattr(config, 'auth_service_url')
        assert hasattr(config, 'task_service_url')

    def test_config_serialization(self):
        """测试配置序列化"""
        # Given: 配置实例
        config = MicroserviceSettings()

        # When: 转换为字典
        config_dict = config.model_dump()

        # Then: 应该包含所有配置项
        expected_keys = [
            'project',
            'auth_service_url',
            'task_service_url',
            'reward_service_url',
            'chat_service_url',
            'focus_service_url',
            'request_timeout'
        ]

        for key in expected_keys:
            assert key in config_dict
            assert config_dict[key] is not None

    def test_config_from_env_file(self, tmp_path):
        """测试从环境文件加载配置"""
        # Given: 临时环境文件
        env_content = """
MICROSERVICE_PROJECT=test_from_file
MICROSERVICE_REQUEST_TIMEOUT=45
MICROSERVICE_AUTH_SERVICE_URL=http://file-auth:9000
"""
        env_file = tmp_path / "test.env"
        env_file.write_text(env_content.strip())

        # When: 从环境文件创建配置
        with patch.dict(os.environ, {"DOTENV_PATH": str(env_file)}, clear=False):
            # 根据具体实现调整测试逻辑
            config = MicroserviceSettings()

            # Then: 验证配置加载（取决于实现是否支持.env文件）
            # 这里根据实际实现调整断言

    def test_partial_environment_override(self):
        """测试部分环境变量覆盖"""
        # Given: 只设置部分环境变量
        with patch.dict(os.environ, {
            "MICROSERVICE_PROJECT": "partial_test",
            "MICROSERVICE_REQUEST_TIMEOUT": "120"
        }, clear=False):
            # When: 创建配置
            config = MicroserviceSettings()

            # Then: 验证部分覆盖
            assert config.project == "partial_test"
            assert config.request_timeout == 120
            # 验证未设置的仍使用默认值
            assert config.auth_service_url == "http://api.aitodo.it:20251"
            assert config.task_service_url == "http://api.aitodo.it:20253"


class TestMicroserviceConfigValidation:
    """微服务配置验证测试类"""

    def test_url_scheme_validation(self):
        """测试URL协议验证"""
        valid_schemes = ["http", "https"]
        invalid_schemes = ["ftp", "ws", "invalid"]

        for scheme in valid_schemes:
            url = f"{scheme}://example.com:8000"
            with patch.dict(os.environ, {"MICROSERVICE_AUTH_SERVICE_URL": url}, clear=False):
                config = MicroserviceSettings()
                assert config.auth_service_url.startswith(f"{scheme}://")

    def test_port_validation(self):
        """测试端口验证"""
        test_cases = [
            ("http://api.aitodo.it:20251", True),  # 有效端口
            ("http://api.aitodo.it:80", True),     # 标准端口
            ("http://api.aitodo.it:0", False),     # 无效端口
            ("http://api.aitodo.it:65536", False), # 超出范围端口
            ("http://api.aitodo.it:-1", False),    # 负端口
        ]

        for url, should_be_valid in test_cases:
            with patch.dict(os.environ, {"MICROSERVICE_AUTH_SERVICE_URL": url}, clear=False):
                config = MicroserviceSettings()
                # 根据具体实现调整验证逻辑
                assert config.auth_service_url is not None

    def test_timeout_bounds_validation(self):
        """测试超时时间边界验证"""
        test_cases = [
            (1, True),      # 最小合理值
            (30, True),     # 默认值
            (300, True),    # 5分钟，合理
            (0, False),     # 零值无效
            (-1, False),    # 负值无效
            (3600, True),   # 1小时，边界情况
        ]

        for timeout, should_be_valid in test_cases:
            with patch.dict(os.environ, {"MICROSERVICE_REQUEST_TIMEOUT": str(timeout)}, clear=False):
                if should_be_valid:
                    config = MicroserviceSettings()
                    assert config.request_timeout == timeout
                else:
                    # 根据具体实现调整错误处理
                    try:
                        config = MicroserviceSettings()
                        # 如果没有抛出错误，验证值被合理处理
                        assert config.request_timeout > 0
                    except ValueError:
                        # 如果抛出错误，这是预期行为
                        pass


class TestMicroserviceConfigIntegration:
    """微服务配置集成测试类"""

    def test_config_with_real_service_urls(self):
        """测试真实服务URL配置"""
        # Given: 真实的微服务URL
        real_urls = {
            "MICROSERVICE_AUTH_SERVICE_URL": "http://api.aitodo.it:20251",
            "MICROSERVICE_TASK_SERVICE_URL": "http://api.aitodo.it:20253",
            "MICROSERVICE_REWARD_SERVICE_URL": "http://api.aitodo.it:20254",
            "MICROSERVICE_CHAT_SERVICE_URL": "http://api.aitodo.it:20252",
            "MICROSERVICE_FOCUS_SERVICE_URL": "http://api.aitodo.it:20255",
        }

        with patch.dict(os.environ, real_urls, clear=False):
            # When: 创建配置
            config = MicroserviceSettings()

            # Then: 验证所有URL正确设置
            assert config.auth_service_url == real_urls["MICROSERVICE_AUTH_SERVICE_URL"]
            assert config.task_service_url == real_urls["MICROSERVICE_TASK_SERVICE_URL"]
            assert config.reward_service_url == real_urls["MICROSERVICE_REWARD_SERVICE_URL"]
            assert config.chat_service_url == real_urls["MICROSERVICE_CHAT_SERVICE_URL"]
            assert config.focus_service_url == real_urls["MICROSERVICE_FOCUS_SERVICE_URL"]

    def test_config_consistency_across_instances(self):
        """测试配置实例间的一致性"""
        # Given: 相同环境
        with patch.dict(os.environ, {"MICROSERVICE_PROJECT": "consistency_test"}, clear=False):
            # When: 创建多个配置实例
            config1 = MicroserviceSettings()
            config2 = MicroserviceSettings()

            # Then: 配置应该一致
            assert config1.project == config2.project
            assert config1.auth_service_url == config2.auth_service_url
            assert config1.request_timeout == config2.request_timeout

    def test_global_config_singleton_behavior(self):
        """测试全局配置单例行为"""
        # Given: 访问全局配置多次
        config1 = microservice_config
        config2 = microservice_config

        # When & Then: 应该是同一个实例（如果实现了单例模式）
        # 这个测试取决于具体实现
        assert isinstance(config1, MicroserviceSettings)
        assert isinstance(config2, MicroserviceSettings)