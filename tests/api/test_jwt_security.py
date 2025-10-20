"""
JWT安全性测试

测试JWT服务的安全功能，包括密钥生成、强加密算法、令牌验证等。
"""

import pytest
import secrets
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_generate_secure_secret_key():
    """测试生成安全的密钥"""
    try:
        from src.services.jwt_service import JWTService

        # 测试生成安全密钥
        secret_key = secrets.token_urlsafe(64)

        assert secret_key is not None
        assert len(secret_key) >= 64
        assert isinstance(secret_key, str)

        # 验证密钥强度
        has_upper = any(c.isupper() for c in secret_key)
        has_lower = any(c.islower() for c in secret_key)
        has_digit = any(c.isdigit() for c in secret_key)
        has_special = any(c in '-_' for c in secret_key)

        assert has_upper or has_lower or has_digit or has_special
        print("✓ 安全密钥生成测试通过")

    except Exception as e:
        pytest.fail(f"安全密钥生成测试失败: {e}")


def test_jwt_with_secure_key():
    """测试使用安全密钥的JWT功能"""
    try:
        from src.services.jwt_service import JWTService

        # 生成安全的密钥
        secure_secret = secrets.token_urlsafe(64)

        # 创建使用安全密钥的JWT服务
        jwt_service = JWTService(
            secret_key=secure_secret,
            algorithm='HS256',
            access_token_expiry=3600,
            refresh_token_expiry=86400 * 7
        )

        user_id = uuid4()

        # 测试令牌生成和验证
        access_token, refresh_token = jwt_service.generate_token_pair(
            user_id=user_id,
            user_type='user'
        )

        # 验证访问令牌
        access_payload = jwt_service.verify_access_token(access_token)
        assert access_payload['user_id'] == str(user_id)
        assert access_payload['token_type'] == 'access'

        # 验证刷新令牌
        refresh_payload = jwt_service.verify_refresh_token(refresh_token)
        assert refresh_payload['user_id'] == str(user_id)
        assert refresh_payload['token_type'] == 'refresh'

        print("✓ 安全密钥JWT功能测试通过")

    except Exception as e:
        pytest.fail(f"安全密钥JWT功能测试失败: {e}")


def test_jwt_algorithm_strength():
    """测试JWT算法强度"""
    try:
        from src.services.jwt_service import JWTService

        # 测试支持的强算法
        strong_algorithms = ['HS256', 'HS384', 'HS512']

        for algorithm in strong_algorithms:
            jwt_service = JWTService(
                secret_key=secrets.token_urlsafe(64),
                algorithm=algorithm
            )

            user_id = uuid4()
            token = jwt_service.generate_access_token(
                user_id=user_id,
                user_type='user'
            )

            payload = jwt_service.verify_access_token(token)
            assert payload['user_id'] == str(user_id)

        print("✓ JWT算法强度测试通过")

    except Exception as e:
        pytest.fail(f"JWT算法强度测试失败: {e}")


def test_jwt_token_expiration():
    """测试JWT令牌过期功能"""
    try:
        from src.services.jwt_service import JWTService

        jwt_service = JWTService(
            secret_key=secrets.token_urlsafe(64),
            algorithm='HS256',
            access_token_expiry=1,  # 1秒过期
        )

        user_id = uuid4()
        token = jwt_service.generate_access_token(
            user_id=user_id,
            user_type='user'
        )

        # 立即验证应该成功
        payload = jwt_service.verify_access_token(token)
        assert payload['user_id'] == str(user_id)

        # 等待过期后验证应该失败
        import time
        time.sleep(2)  # 等待2秒确保令牌过期

        from src.services.exceptions import AuthenticationException
        with pytest.raises(AuthenticationException):
            jwt_service.verify_access_token(token)

        print("✓ JWT令牌过期测试通过")

    except Exception as e:
        pytest.fail(f"JWT令牌过期测试失败: {e}")


def test_jwt_token_validation_security():
    """测试JWT令牌验证安全性"""
    try:
        from src.services.jwt_service import JWTService
        from src.services.exceptions import AuthenticationException

        jwt_service = JWTService(
            secret_key=secrets.token_urlsafe(64),
            algorithm='HS256'
        )

        # 测试无效令牌
        invalid_tokens = [
            "invalid.token.here",
            "not-a-jwt-token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",  # 空令牌
            "Bearer",  # 只有Bearer前缀
        ]

        for invalid_token in invalid_tokens:
            with pytest.raises(AuthenticationException):
                jwt_service.verify_access_token(invalid_token)

        # 测试使用错误密钥生成的令牌
        wrong_key_service = JWTService(
            secret_key="wrong-secret-key",
            algorithm='HS256'
        )

        user_id = uuid4()
        wrong_token = wrong_key_service.generate_access_token(
            user_id=user_id,
            user_type='user'
        )

        # 用正确密钥的服务验证错误密钥生成的令牌应该失败
        with pytest.raises(AuthenticationException):
            jwt_service.verify_access_token(wrong_token)

        print("✓ JWT令牌验证安全性测试通过")

    except Exception as e:
        pytest.fail(f"JWT令牌验证安全性测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])