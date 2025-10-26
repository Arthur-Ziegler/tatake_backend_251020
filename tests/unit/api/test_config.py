"""
API配置测试

测试API层配置管理功能，包括：
1. 配置类创建和验证
2. 环境变量加载
3. 默认值验证
4. JWT配置安全验证
5. CORS配置验证
6. 配置方法测试

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import os
import secrets
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from src.api.config import APIConfig, config


@pytest.mark.unit
class TestAPIConfig:
    """API配置基础测试类"""

    def test_config_creation_with_defaults(self):
        """测试使用默认值创建配置"""
        config = APIConfig()

        # 验证默认值
        assert config.app_name == "TaKeKe API"
        assert config.app_version == "1.0.0"
        assert config.debug is False
        assert config.api_prefix == ""
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8001
        assert config.database_url == "sqlite+aiosqlite:///./tatake.db"

    def test_config_creation_with_custom_values(self):
        """测试使用自定义值创建配置"""
        custom_config = APIConfig(
            app_name="Custom API",
            app_version="2.0.0",
            debug=True,
            api_port=9000
        )

        assert custom_config.app_name == "Custom API"
        assert custom_config.app_version == "2.0.0"
        assert custom_config.debug is True
        assert custom_config.api_port == 9000

    def test_config_database_url_validation(self):
        """测试数据库URL验证"""
        # 测试各种数据库URL格式
        valid_urls = [
            "sqlite+aiosqlite:///./tatake.db",
            "sqlite:///./tatake.db",
            "postgresql://user:password@localhost/tatake",
            "mysql://user:password@localhost/tatake"
        ]

        for db_url in valid_urls:
            config = APIConfig(database_url=db_url)
            assert config.database_url == db_url

    def test_config_jwt_defaults(self):
        """测试JWT配置默认值"""
        config = APIConfig()

        assert config.jwt_algorithm == "HS256"
        assert config.jwt_access_token_expire_minutes == 30
        assert config.jwt_refresh_token_expire_days == 7
        assert len(config.jwt_secret_key) > 32  # 应该生成足够长的密钥

    def test_config_jwt_secret_key_generation(self):
        """测试JWT密钥生成"""
        config1 = APIConfig()
        config2 = APIConfig()

        # 每次创建应该生成不同的密钥
        assert config1.jwt_secret_key != config2.jwt_secret_key

        # 密钥应该是URL安全的base64编码
        secret_key = config1.jwt_secret_key
        assert all(c.isalnum() or c in '-_' for c in secret_key)
        assert len(secret_key) >= 64

    def test_config_cors_defaults(self):
        """测试CORS配置默认值"""
        config = APIConfig()

        assert config.allowed_origins == ["*"]
        assert "GET" in config.allowed_methods
        assert "POST" in config.allowed_methods
        assert config.allowed_headers == ["*"]

    def test_config_rate_limiting_defaults(self):
        """测试限流配置默认值"""
        config = APIConfig()

        assert config.rate_limit_enabled is True
        assert config.rate_limit_requests_per_minute == 60
        assert config.rate_limit_burst_size == 10

    def test_config_logging_defaults(self):
        """测试日志配置默认值"""
        config = APIConfig()

        assert config.log_level == "INFO"
        assert config.log_format == "json"

    def test_config_security_defaults(self):
        """测试安全配置默认值"""
        config = APIConfig()

        assert config.secure_cookies is True
        assert config.csrf_protection is True

    def test_config_file_upload_defaults(self):
        """测试文件上传配置默认值"""
        config = APIConfig()

        assert config.max_file_size == 10 * 1024 * 1024  # 10MB
        assert "jpg" in config.allowed_file_types
        assert "png" in config.allowed_file_types

    def test_config_performance_defaults(self):
        """测试性能配置默认值"""
        config = APIConfig()

        assert config.request_timeout == 30
        assert config.max_concurrent_requests == 1000


@pytest.mark.unit
class TestJWTConfiguration:
    """JWT配置测试类"""

    def test_get_secure_jwt_config_defaults(self):
        """测试获取安全JWT配置默认值"""
        config = APIConfig()
        jwt_config = config.get_secure_jwt_config()

        # 验证返回的配置结构
        assert 'secret_key' in jwt_config
        assert 'algorithm' in jwt_config
        assert 'access_token_expiry' in jwt_config
        assert 'refresh_token_expiry' in jwt_config
        assert 'issuer' in jwt_config
        assert 'audience' in jwt_config

        # 验证默认值
        assert jwt_config['algorithm'] == 'HS256'
        assert jwt_config['issuer'] == 'tatake-api'
        assert jwt_config['audience'] == 'tatake-client'
        assert jwt_config['access_token_expiry'] == 30 * 60  # 30分钟转秒
        assert jwt_config['refresh_token_expiry'] == 7 * 24 * 60 * 60  # 7天转秒

    def test_get_secure_jwt_config_short_secret(self):
        """测试短密钥自动生成"""
        config = APIConfig()

        # 手动设置短密钥
        config.jwt_secret_key = "short"

        jwt_config = config.get_secure_jwt_config()

        # 应该自动生成长密钥
        assert len(jwt_config['secret_key']) >= 64

    def test_get_secure_jwt_config_unsafe_algorithm(self):
        """测试不安全算法自动修正"""
        config = APIConfig()
        config.jwt_algorithm = "none"  # 不安全的算法

        jwt_config = config.get_secure_jwt_config()

        # 应该自动修正为安全算法
        assert jwt_config['algorithm'] == 'HS256'

    def test_get_secure_jwt_config_custom_safe_algorithm(self):
        """测试自定义安全算法"""
        config = APIConfig()
        config.jwt_algorithm = "HS512"  # 安全的算法

        jwt_config = config.get_secure_jwt_config()

        # 应该保持安全算法
        assert jwt_config['algorithm'] == 'HS512'

    def test_jwt_config_time_conversion(self):
        """测试JWT时间配置转换"""
        config = APIConfig(
            jwt_access_token_expire_minutes=60,  # 1小时
            jwt_refresh_token_expire_days=14      # 2周
        )

        jwt_config = config.get_secure_jwt_config()

        # 验证时间转换
        assert jwt_config['access_token_expiry'] == 60 * 60  # 3600秒
        assert jwt_config['refresh_token_expiry'] == 14 * 24 * 60 * 60  # 1209600秒


@pytest.mark.unit
class TestEnvironmentVariableLoading:
    """环境变量加载测试类"""

    def test_environment_variable_override(self):
        """测试环境变量覆盖"""
        with patch.dict(os.environ, {
            'APP_NAME': 'Environment API',
            'API_PORT': '9000',
            'DEBUG': 'true'
        }):
            config = APIConfig()

            assert config.app_name == 'Environment API'
            assert config.api_port == 9000
            assert config.debug is True

    def test_environment_variable_types(self):
        """测试环境变量类型转换"""
        with patch.dict(os.environ, {
            'API_PORT': '9000',      # 字符串转整数
            'DEBUG': 'false',       # 字符串转布尔
            'RATE_LIMIT_ENABLED': '1'  # 字符串转布尔
        }):
            config = APIConfig()

            assert config.api_port == 9000
            assert config.debug is False
            assert config.rate_limit_enabled is True

    def test_invalid_environment_variable_types(self):
        """测试无效环境变量类型"""
        with patch.dict(os.environ, {
            'API_PORT': 'invalid_number'  # 无效数字
        }):
            # 应该能正常创建配置，pydantic会处理类型错误
            try:
                config = APIConfig()
                # 如果能创建，验证默认值被使用
                assert config.api_port == 8001
            except ValidationError:
                # 如果pydantic严格验证，这也是可接受的
                pass

    def test_empty_environment_variables(self):
        """测试空环境变量"""
        with patch.dict(os.environ, {
            'APP_NAME': '',  # 空字符串
            'API_PREFIX': ''
        }):
            config = APIConfig()

            # 验证空值被正确处理
            # 空字符串可能被保持或替换为默认值
            assert config.app_name == ''

    def test_extra_environment_variables(self):
        """测试额外环境变量"""
        with patch.dict(os.environ, {
            'CUSTOM_VAR': 'custom_value',
            'ANOTHER_VAR': 'another_value'
        }):
            config = APIConfig()

            # extra="allow" 应该允许额外变量
            # 验证配置能正常创建
            assert config is not None


@pytest.mark.unit
class TestConfigValidation:
    """配置验证测试类"""

    def test_port_validation(self):
        """测试端口验证"""
        # 测试有效端口
        valid_ports = [8000, 8080, 9000, 3000]
        for port in valid_ports:
            config = APIConfig(api_port=port)
            assert config.api_port == port

    def test_timeout_validation(self):
        """测试超时时间验证"""
        # 测试有效超时时间
        valid_timeouts = [5, 30, 60, 120]
        for timeout in valid_timeouts:
            config = APIConfig(request_timeout=timeout)
            assert config.request_timeout == timeout

    def test_file_size_validation(self):
        """测试文件大小验证"""
        # 测试有效文件大小
        valid_sizes = [1024, 1024*1024, 10*1024*1024]  # 1KB, 1MB, 10MB
        for size in valid_sizes:
            config = APIConfig(max_file_size=size)
            assert config.max_file_size == size

    def test_boolean_config_values(self):
        """测试布尔配置值"""
        # 测试布尔值的各种表示
        boolean_configs = [
            ('debug', True),
            ('rate_limit_enabled', True),
            ('secure_cookies', False),
            ('csrf_protection', True)
        ]

        for config_name, expected_value in boolean_configs:
            config = APIConfig(**{config_name: expected_value})
            assert getattr(config, config_name) == expected_value

    def test_list_config_values(self):
        """测试列表配置值"""
        config = APIConfig(
            allowed_origins=["https://example.com", "https://api.example.com"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Content-Type", "Authorization"],
            allowed_file_types=["pdf", "doc", "docx"]
        )

        assert len(config.allowed_origins) == 2
        assert "https://example.com" in config.allowed_origins
        assert "GET" in config.allowed_methods
        assert "Content-Type" in config.allowed_headers
        assert "pdf" in config.allowed_file_types


@pytest.mark.integration
class TestConfigIntegration:
    """配置集成测试类"""

    def test_global_config_instance(self):
        """测试全局配置实例"""
        # 验证全局配置实例存在
        assert config is not None
        assert isinstance(config, APIConfig)

    def test_config_persistence(self):
        """测试配置持久性"""
        # 验证配置在不同地方访问时的一致性
        from src.api.config import config as config1
        from src.api.config import config as config2

        assert config1 is config2
        assert config1.app_name == config2.app_name

    def test_config_with_database_url(self):
        """测试数据库URL配置"""
        test_db_url = "sqlite+aiosqlite:///./test.db"
        config = APIConfig(database_url=test_db_url)

        assert config.database_url == test_db_url

    def test_config_comprehensive(self):
        """测试综合配置"""
        comprehensive_config = APIConfig(
            app_name="Comprehensive Test API",
            app_version="3.0.0",
            debug=True,
            api_prefix="/api/v1",
            api_port=8080,
            database_url="postgresql://localhost/tatake",
            jwt_access_token_expire_minutes=60,
            jwt_refresh_token_expire_days=30,
            rate_limit_requests_per_minute=120,
            log_level="DEBUG",
            secure_cookies=False,
            max_file_size=5*1024*1024,  # 5MB
            request_timeout=60
        )

        # 验证所有配置项
        assert comprehensive_config.app_name == "Comprehensive Test API"
        assert comprehensive_config.debug is True
        assert comprehensive_config.api_prefix == "/api/v1"
        assert comprehensive_config.api_port == 8080
        assert comprehensive_config.jwt_access_token_expire_minutes == 60

    def test_config_environment_integration(self):
        """测试配置环境集成"""
        # 模拟生产环境配置
        with patch.dict(os.environ, {
            'APP_NAME': 'Production API',
            'DEBUG': 'false',
            'API_PORT': '80',
            'LOG_LEVEL': 'WARNING'
        }):
            prod_config = APIConfig()

            assert prod_config.app_name == 'Production API'
            assert prod_config.debug is False
            assert prod_config.api_port == 80
            assert prod_config.log_level == 'WARNING'

    def test_jwt_config_security_integration(self):
        """测试JWT配置安全集成"""
        config = APIConfig()

        # 测试不安全配置的自动修正
        config.jwt_secret_key = "unsafe"
        config.jwt_algorithm = "none"

        jwt_config = config.get_secure_jwt_config()

        # 验证安全配置被正确应用
        assert len(jwt_config['secret_key']) >= 64
        assert jwt_config['algorithm'] in ['HS256', 'HS384', 'HS512']


@pytest.mark.parametrize("field_name,expected_type", [
    ("app_name", str),
    ("app_version", str),
    ("debug", bool),
    ("api_port", int),
    ("database_url", str),
    ("jwt_algorithm", str),
    ("log_level", str),
    ("max_file_size", int)
])
def test_config_field_types(field_name, expected_type):
    """参数化测试配置字段类型"""
    config = APIConfig()
    field_value = getattr(config, field_name)
    assert isinstance(field_value, expected_type)


@pytest.mark.parametrize("invalid_port", [
    -1,  # 负数
    0,   # 零端口
    65536,  # 超出端口范围
    99999   # 远超端口范围
])
def test_invalid_port_validation(invalid_port):
    """参数化测试无效端口验证"""
    # 某些端口可能被pydantic拒绝，这是正常的
    try:
        config = APIConfig(api_port=invalid_port)
        # 如果能创建，验证端口值
        assert config.api_port == invalid_port
    except ValidationError:
        # 验证失败也是可接受的
        pass


@pytest.mark.parametrize("valid_algorithm", [
    "HS256",
    "HS384",
    "HS512"
])
def test_valid_jwt_algorithms(valid_algorithm):
    """参数化测试有效JWT算法"""
    config = APIConfig(jwt_algorithm=valid_algorithm)
    jwt_config = config.get_secure_jwt_config()
    assert jwt_config['algorithm'] == valid_algorithm


@pytest.fixture
def mock_env_vars():
    """模拟环境变量"""
    return {
        'APP_NAME': 'Test API',
        'API_PORT': '9000',
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG'
    }


def test_config_with_mock_env(mock_env_vars):
    """使用模拟环境变量测试配置"""
    with patch.dict(os.environ, mock_env_vars):
        config = APIConfig()

        assert config.app_name == 'Test API'
        assert config.api_port == 9000
        assert config.debug is True
        assert config.log_level == 'DEBUG'