"""
JWT安全配置测试

测试JWT服务的安全配置功能，包括自动生成安全密钥、配置验证等。
"""

import pytest
import secrets
from unittest.mock import AsyncMock

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_secure_jwt_config_generation():
    """测试安全JWT配置生成"""
    try:
        from src.api.config import APIConfig
        from src.services.jwt_service import JWTService

        # 创建配置实例
        config = APIConfig()

        # 获取安全配置
        jwt_config = config.get_secure_jwt_config()

        # 验证配置包含所有必需字段
        assert 'secret_key' in jwt_config
        assert 'algorithm' in jwt_config
        assert 'access_token_expiry' in jwt_config
        assert 'refresh_token_expiry' in jwt_config
        assert 'issuer' in jwt_config
        assert 'audience' in jwt_config

        # 验证密钥长度足够
        assert len(jwt_config['secret_key']) >= 64

        # 验证算法是安全的
        assert jwt_config['algorithm'] in ['HS256', 'HS384', 'HS512']

        # 验证过期时间合理
        assert jwt_config['access_token_expiry'] > 0
        assert jwt_config['refresh_token_expiry'] > jwt_config['access_token_expiry']

        # 验证发行者和受众
        assert jwt_config['issuer'] == 'tatake-api'
        assert jwt_config['audience'] == 'tatake-client'

        print("✓ 安全JWT配置生成测试通过")

    except Exception as e:
        pytest.fail(f"安全JWT配置生成测试失败: {e}")


def test_jwt_service_with_secure_config():
    """测试JWT服务使用安全配置"""
    try:
        from src.api.config import APIConfig
        from src.services.jwt_service import JWTService
        from unittest.mock import AsyncMock

        # 创建配置实例
        config = APIConfig()

        # 获取安全配置
        jwt_config = config.get_secure_jwt_config()

        # 创建模拟的Repository
        mock_session = AsyncMock()
        mock_repo = AsyncMock()

        # 使用安全配置创建JWT服务
        jwt_service = JWTService(
            token_blacklist_repo=mock_repo,
            **jwt_config
        )

        # 验证服务创建成功
        assert jwt_service is not None
        assert jwt_service._secret_key == jwt_config['secret_key']
        assert jwt_service._algorithm == jwt_config['algorithm']
        assert jwt_service._access_token_expiry.total_seconds() == jwt_config['access_token_expiry']
        assert jwt_service._refresh_token_expiry.total_seconds() == jwt_config['refresh_token_expiry']
        assert jwt_service._issuer == jwt_config['issuer']
        assert jwt_service._audience == jwt_config['audience']

        print("✓ JWT服务安全配置测试通过")

    except Exception as e:
        pytest.fail(f"JWT服务安全配置测试失败: {e}")


def test_weak_key_replacement():
    """测试弱密钥被替换"""
    try:
        from src.api.config import APIConfig

        # 创建配置实例并设置弱密钥
        config = APIConfig()
        config.jwt_secret_key = "weak"

        # 获取安全配置
        jwt_config = config.get_secure_jwt_config()

        # 验证弱密钥被替换
        assert jwt_config['secret_key'] != "weak"
        assert len(jwt_config['secret_key']) >= 64

        print("✓ 弱密钥替换测试通过")

    except Exception as e:
        pytest.fail(f"弱密钥替换测试失败: {e}")


def test_weak_algorithm_replacement():
    """测试弱算法被替换"""
    try:
        from src.api.config import APIConfig

        # 创建配置实例并设置弱算法
        config = APIConfig()
        config.jwt_algorithm = "none"  # 不安全的算法

        # 获取安全配置
        jwt_config = config.get_secure_jwt_config()

        # 验证弱算法被替换
        assert jwt_config['algorithm'] == "HS256"

        print("✓ 弱算法替换测试通过")

    except Exception as e:
        pytest.fail(f"弱算法替换测试失败: {e}")


def test_jwt_token_with_secure_config():
    """测试使用安全配置生成和验证令牌"""
    try:
        from src.api.config import APIConfig
        from src.services.jwt_service import JWTService
        from uuid import uuid4

        # 创建配置实例
        config = APIConfig()

        # 获取安全配置
        jwt_config = config.get_secure_jwt_config()

        # 创建模拟的Repository
        mock_repo = AsyncMock()

        # 创建JWT服务
        jwt_service = JWTService(
            token_blacklist_repo=mock_repo,
            **jwt_config
        )

        # 生成令牌对
        user_id = uuid4()
        access_token, refresh_token = jwt_service.generate_token_pair(
            user_id=user_id,
            user_type='user'
        )

        # 验证令牌
        access_payload = jwt_service.verify_access_token(access_token)
        refresh_payload = jwt_service.verify_refresh_token(refresh_token)

        # 验证令牌内容
        assert access_payload['user_id'] == str(user_id)
        assert access_payload['token_type'] == 'access'
        assert access_payload['iss'] == 'tatake-api'
        assert access_payload['aud'] == 'tatake-client'

        assert refresh_payload['user_id'] == str(user_id)
        assert refresh_payload['token_type'] == 'refresh'
        assert refresh_payload['iss'] == 'tatake-api'
        assert refresh_payload['aud'] == 'tatake-client'

        print("✓ JWT令牌安全配置测试通过")

    except Exception as e:
        pytest.fail(f"JWT令牌安全配置测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])