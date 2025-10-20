"""
JWT服务测试

测试新创建的JWT服务，包括令牌生成、验证、黑名单管理等功能。
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_jwt_service_import():
    """测试JWT服务导入"""
    try:
        from src.services.jwt_service import JWTService
        assert JWTService is not None
        print("✓ JWT服务导入成功")
    except ImportError as e:
        pytest.fail(f"JWT服务导入失败: {e}")


def test_jwt_service_creation():
    """测试JWT服务创建"""
    try:
        from src.services.jwt_service import JWTService

        # 创建JWT服务实例
        jwt_service = JWTService(
            secret_key='test-secret-key',
            algorithm='HS256',
            access_token_expiry=3600,  # 1小时
            refresh_token_expiry=86400 * 7  # 7天
        )

        assert jwt_service is not None
        assert jwt_service._secret_key == 'test-secret-key'
        assert jwt_service._algorithm == 'HS256'
        print("✓ JWT服务创建成功")

    except Exception as e:
        pytest.fail(f"JWT服务创建失败: {e}")


def test_generate_access_token():
    """测试生成访问令牌"""
    try:
        from src.services.jwt_service import JWTService

        jwt_service = JWTService(
            secret_key='test-secret-key',
            algorithm='HS256'
        )

        user_id = uuid4()
        token = jwt_service.generate_access_token(
            user_id=user_id,
            user_type='user'
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        print("✓ 访问令牌生成成功")

    except Exception as e:
        pytest.fail(f"访问令牌生成失败: {e}")


def test_decode_token():
    """测试解码令牌"""
    try:
        from src.services.jwt_service import JWTService

        jwt_service = JWTService(
            secret_key='test-secret-key',
            algorithm='HS256'
        )

        user_id = uuid4()
        token = jwt_service.generate_access_token(
            user_id=user_id,
            user_type='user'
        )

        # 解码令牌（不验证黑名单）
        payload = jwt_service.decode_token(token, verify_blacklist=False)

        assert payload is not None
        assert payload['user_id'] == str(user_id)
        assert payload['user_type'] == 'user'
        assert payload['token_type'] == 'access'
        assert 'jti' in payload
        assert 'exp' in payload
        print("✓ 令牌解码成功")

    except Exception as e:
        pytest.fail(f"令牌解码失败: {e}")


def test_generate_token_pair():
    """测试生成令牌对"""
    try:
        from src.services.jwt_service import JWTService

        jwt_service = JWTService(
            secret_key='test-secret-key',
            algorithm='HS256'
        )

        user_id = uuid4()
        access_token, refresh_token = jwt_service.generate_token_pair(
            user_id=user_id,
            user_type='user'
        )

        assert access_token is not None
        assert refresh_token is not None
        assert access_token != refresh_token

        # 验证访问令牌
        access_payload = jwt_service.decode_token(access_token, verify_blacklist=False)
        assert access_payload['token_type'] == 'access'

        # 验证刷新令牌
        refresh_payload = jwt_service.decode_token(refresh_token, verify_blacklist=False)
        assert refresh_payload['token_type'] == 'refresh'
        assert refresh_payload['access_jti'] == access_payload['jti']

        print("✓ 令牌对生成成功")

    except Exception as e:
        pytest.fail(f"令牌对生成失败: {e}")


def test_verify_access_token():
    """测试验证访问令牌"""
    try:
        from src.services.jwt_service import JWTService

        jwt_service = JWTService(
            secret_key='test-secret-key',
            algorithm='HS256'
        )

        user_id = uuid4()
        token = jwt_service.generate_access_token(
            user_id=user_id,
            user_type='user'
        )

        # 验证访问令牌
        payload = jwt_service.verify_access_token(token)

        assert payload is not None
        assert payload['user_id'] == str(user_id)
        assert payload['user_type'] == 'user'
        assert payload['token_type'] == 'access'
        print("✓ 访问令牌验证成功")

    except Exception as e:
        pytest.fail(f"访问令牌验证失败: {e}")


def test_verify_refresh_token():
    """测试验证刷新令牌"""
    try:
        from src.services.jwt_service import JWTService

        jwt_service = JWTService(
            secret_key='test-secret-key',
            algorithm='HS256'
        )

        user_id = uuid4()
        access_token, refresh_token = jwt_service.generate_token_pair(
            user_id=user_id,
            user_type='user'
        )

        # 验证刷新令牌
        payload = jwt_service.verify_refresh_token(refresh_token)

        assert payload is not None
        assert payload['user_id'] == str(user_id)
        assert payload['token_type'] == 'refresh'
        print("✓ 刷新令牌验证成功")

    except Exception as e:
        pytest.fail(f"刷新令牌验证失败: {e}")


def test_extract_token_from_header():
    """测试从Authorization头提取令牌"""
    try:
        from src.services.jwt_service import JWTService

        jwt_service = JWTService()

        # 测试有效的Bearer token
        auth_header = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        token = jwt_service.extract_token_from_header(auth_header)
        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"

        # 测试无效的header格式
        invalid_headers = [
            "Invalid token",
            "Bearer",
            "",
            None,
            "Basic dXNlcjpwYXNz"
        ]

        for header in invalid_headers:
            token = jwt_service.extract_token_from_header(header)
            assert token is None

        print("✓ 令牌提取功能测试成功")

    except Exception as e:
        pytest.fail(f"令牌提取功能测试失败: {e}")


def test_invalid_token():
    """测试无效令牌验证"""
    try:
        from src.services.jwt_service import JWTService
        from src.services.exceptions import AuthenticationException

        jwt_service = JWTService(
            secret_key='test-secret-key',
            algorithm='HS256'
        )

        # 测试无效令牌
        invalid_tokens = [
            "invalid.token.here",
            "not-a-jwt-token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        ]

        for token in invalid_tokens:
            with pytest.raises(AuthenticationException):
                jwt_service.decode_token(token, verify_blacklist=False)

        print("✓ 无效令牌验证测试成功")

    except Exception as e:
        pytest.fail(f"无效令牌验证测试失败: {e}")


def test_service_factory_jwt_service():
    """测试ServiceFactory能创建JWT服务"""
    try:
        from src.api.dependencies import ServiceFactory

        # 创建ServiceFactory实例
        factory = ServiceFactory()

        # 创建模拟session
        mock_session = AsyncMock()

        # 测试创建JWT服务
        jwt_service = factory.get_jwt_service(mock_session)

        assert jwt_service is not None
        print("✓ ServiceFactory JWT服务创建成功")

    except ImportError as e:
        pytest.fail(f"ServiceFactory测试失败: {e}")
    except Exception as e:
        pytest.fail(f"ServiceFactory测试异常: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])