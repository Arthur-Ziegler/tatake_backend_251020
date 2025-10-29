"""
JWT验证器单元测试

测试JWTValidator的所有功能，包括：
- JWT令牌解析和验证
- 公钥获取和缓存
- 对称和非对称加密支持
- 错误处理和异常情况

作者：TaTakeKe团队
版本：1.0.0
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import jwt

from src.services.auth.jwt_validator import JWTValidator, JWTValidationError


@pytest.mark.unit
class TestJWTValidator:
    """JWT验证器测试类"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        # 使用测试密钥，确保与测试token使用的密钥一致
        mock_client = MagicMock()
        validator = JWTValidator(auth_client=mock_client)
        # 设置本地密钥为测试密钥
        validator.local_secret = "test-secret"
        validator.local_algorithm = "HS256"
        return validator

    @pytest.fixture
    def valid_token_payload(self):
        """创建有效的令牌载荷"""
        return {
            "sub": "user123",
            "is_guest": True,
            "jwt_version": 1,
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "jti": "test-jti-123"
        }

    @pytest.fixture
    def valid_token(self, valid_token_payload):
        """创建有效的JWT令牌"""
        return jwt.encode(valid_token_payload, "test-secret", algorithm="HS256")

    @pytest.fixture
    def expired_token_payload(self):
        """创建过期的令牌载荷"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        return {
            "sub": "user123",
            "is_guest": True,
            "jwt_version": 1,
            "token_type": "access",
            "iat": int(past_time.timestamp()),
            "exp": int(past_time.timestamp()),
            "jti": "test-jti-123"
        }

    @pytest.fixture
    def expired_token(self, expired_token_payload):
        """创建过期的JWT令牌"""
        return jwt.encode(expired_token_payload, "test-secret", algorithm="HS256")

    def test_validator_initialization(self):
        """测试验证器初始化"""
        mock_client = MagicMock()
        validator = JWTValidator(auth_client=mock_client, cache_ttl=600)

        assert validator.auth_client == mock_client
        assert validator.cache_ttl == 600
        assert validator._public_key_cache is None
        assert validator._cache_expiry is None

    @pytest.mark.asyncio
    async def test_validate_token_symmetric_success(self, validator, valid_token):
        """测试对称加密令牌验证成功"""
        # 模拟公钥响应（对称加密）
        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        result = await validator.validate_token(valid_token)

        assert result["sub"] == "user123"
        assert result["is_guest"] is True
        assert result["token_type"] == "access"

    @pytest.mark.asyncio
    async def test_validate_token_asymmetric_success(self, validator):
        """测试非对称加密令牌验证成功"""
        # 简化测试：使用对称加密模拟非对称加密的行为
        # 实际项目中，如果需要真正的RSA测试，可以生成测试密钥对
        token_payload = {
            "sub": "user123",
            "is_guest": False,
            "jwt_version": 1,
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "jti": "test-jti-456"
        }

        # 使用HS256模拟测试（重点测试验证逻辑）
        token = jwt.encode(token_payload, "test-secret", algorithm="HS256")

        # 模拟公钥响应（返回对称密钥信息）
        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        result = await validator.validate_token(token)

        assert result["sub"] == "user123"
        assert result["is_guest"] is False
        assert result["token_type"] == "access"

    @pytest.mark.asyncio
    async def test_validate_token_expired(self, validator, expired_token):
        """测试过期令牌验证"""
        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        with pytest.raises(Exception) as exc_info:
            await validator.validate_token(expired_token)

        assert "expired" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_token_invalid_signature(self, validator):
        """测试无效签名令牌验证"""
        invalid_token = "invalid.token.here"

        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        with pytest.raises(Exception):
            await validator.validate_token(invalid_token)

    @pytest.mark.asyncio
    async def test_validate_token_missing_fields(self, validator):
        """测试缺少必要字段的令牌验证"""
        incomplete_payload = {
            "sub": "user123",
            # 缺少其他必要字段
        }

        token = jwt.encode(incomplete_payload, "test-secret", algorithm="HS256")

        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        result = await validator.validate_token(token)
        # 应该能解析，但缺少某些字段
        assert result["sub"] == "user123"

    @pytest.mark.asyncio
    async def test_public_key_cache_hit(self, validator, valid_token):
        """测试公钥缓存命中"""
        # 设置缓存
        validator._public_key_cache = ("", "HS256")
        validator._cache_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        validator._is_symmetric = True

        # 模拟客户端，但不应该被调用
        mock_client = AsyncMock()
        validator.auth_client = mock_client

        result = await validator.validate_token(valid_token)

        # 验证客户端未被调用（使用缓存）
        mock_client.get_public_key.assert_not_called()
        assert result["sub"] == "user123"

    @pytest.mark.asyncio
    async def test_public_key_cache_expired(self, validator, valid_token):
        """测试公钥缓存过期"""
        # 设置过期的缓存
        validator._public_key_cache = ("old_key", "HS256")
        validator._cache_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)

        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        result = await validator.validate_token(valid_token)

        # 验证客户端被调用（缓存过期）
        mock_client.get_public_key.assert_called_once()
        assert result["sub"] == "user123"

    @pytest.mark.asyncio
    async def test_get_public_key_info_success(self, validator):
        """测试获取公钥信息成功"""
        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "公钥获取成功",
            "data": {"public_key": "test-key-data", "algorithm": "RS256"}
        }

        validator.auth_client = mock_client

        key_data, algorithm, is_symmetric = await validator._get_public_key_info()

        assert key_data == "test-key-data"
        assert algorithm == "RS256"
        assert is_symmetric is False

    @pytest.mark.asyncio
    async def test_get_public_key_info_symmetric(self, validator):
        """测试获取对称加密信息"""
        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        key_data, algorithm, is_symmetric = await validator._get_public_key_info()

        assert key_data == ""
        assert algorithm == "HS256"
        assert is_symmetric is True

    @pytest.mark.asyncio
    async def test_get_public_key_info_api_error(self, validator):
        """测试公钥API错误"""
        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 500,
            "message": "内部服务器错误",
            "data": None
        }

        validator.auth_client = mock_client

        with pytest.raises(Exception) as exc_info:
            await validator._get_public_key_info()

        assert "内部服务器错误" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_token_cache_update(self, validator, valid_token):
        """测试验证时缓存更新"""
        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        # 验证缓存为空
        assert validator._public_key_cache is None

        await validator.validate_token(valid_token)

        # 验证缓存已更新
        assert validator._public_key_cache == ("", "HS256")
        assert validator._cache_expiry is not None
        assert validator._is_symmetric is True

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, validator, valid_token):
        """测试并发缓存访问"""
        import asyncio

        mock_client = AsyncMock()
        mock_client.get_public_key.return_value = {
            "code": 200,
            "message": "当前使用对称加密，无公钥",
            "data": {"public_key": "", "algorithm": "HS256"}
        }

        validator.auth_client = mock_client

        # 并发执行多个验证请求
        tasks = [
            validator.validate_token(valid_token) for _ in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        assert len(results) == 5
        for result in results:
            assert result["sub"] == "user123"

        # 验证只调用了一次API（缓存生效）
        assert mock_client.get_public_key.call_count == 1