"""
JWT令牌验证器

提供JWT令牌的本地验证功能，通过从微服务获取公钥进行验证。
支持对称加密（HMAC）和非对称加密（RSA）两种算法。

设计原则：
- 支持动态获取公钥
- 实现公钥缓存机制
- 支持多种JWT算法
- 提供详细的错误信息
- 异步设计，提升性能
"""

import os
import asyncio
import time
from typing import Dict, Any, Optional, NamedTuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import hashlib

import jwt
from fastapi import HTTPException, status

from .client import AuthMicroserviceClient


class JWTValidationError(Exception):
    """JWT验证错误"""
    pass


@dataclass
class UserInfo:
    """用户信息缓存对象"""
    user_id: str
    is_guest: bool
    exp: int
    iat: int
    token_hash: str
    cache_time: float

    def is_expired(self) -> bool:
        """检查用户信息是否过期"""
        return datetime.now(timezone.utc).timestamp() > self.exp

    def is_cache_expired(self, ttl: int = 300) -> bool:
        """检查缓存是否过期（默认5分钟）"""
        return time.time() - self.cache_time > ttl


class TokenValidationResult(NamedTuple):
    """Token验证结果"""
    payload: Dict[str, Any]
    user_info: UserInfo


class JWTValidator:
    """
    JWT令牌验证器

    这个类负责：
    - 从微服务获取公钥（或对称密钥信息）
    - 本地验证JWT令牌
    - 缓存公钥，减少网络调用
    - 处理多种加密算法

    设计思路：
    - 对称加密：直接使用共享密钥验证
    - 非对称加密：从微服务获取公钥验证
    - 缓存机制：避免频繁获取公钥
    - 自动刷新：定期更新缓存的公钥
    """

    def __init__(self, auth_client: Optional[AuthMicroserviceClient] = None):
        """
        初始化JWT验证器

        Args:
            auth_client: 认证微服务客户端，可选
        """
        self.auth_client = auth_client or AuthMicroserviceClient()

        # 本地对称密钥（从环境变量获取，用于降级）
        self.local_secret = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-for-tatake-backend-2024")
        self.local_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        # 本地公钥（从环境变量获取，Base64编码的PEM格式）
        self.local_public_key = os.getenv("JWT_PUBLIC_KEY", "")
        if self.local_public_key:
            try:
                # Base64解码公钥
                import base64
                self.local_public_key = base64.b64decode(self.local_public_key).decode('utf-8')
                print(f"[JWTValidator] 成功加载本地公钥配置，算法={self.local_algorithm}")
            except Exception as e:
                print(f"[JWTValidator] 解码本地公钥失败: {str(e)}")
                self.local_public_key = ""

        # 公钥缓存
        self._public_key_cache: Optional[str] = None
        self._public_key_algorithm: Optional[str] = None
        self._key_cache_time: Optional[float] = None
        self._key_cache_ttl = 3600  # 公钥缓存1小时

        # 是否使用对称加密（从微服务获取的配置）
        self._is_symmetric: Optional[bool] = None

        # 用户信息缓存 {token_hash: UserInfo}
        self._user_cache: Dict[str, UserInfo] = {}
        self._user_cache_ttl = 300  # 用户信息缓存5分钟
        self._max_cache_size = 1000  # 最大缓存条目数

        print("[JWTValidator] 初始化JWT验证器")

    async def _get_public_key_info(self) -> tuple[str, str, bool]:
        """
        从微服务获取公钥信息（微服务优先，本地配置作为降级方案）

        设计原则：
        - 认证微服务是公钥的唯一权威来源（Single Source of Truth）
        - 优先从微服务动态获取最新公钥
        - 微服务不可用时才降级到本地配置
        - 使用缓存减少网络请求，但不影响动态更新能力

        Returns:
            (key_data, algorithm, is_symmetric)
            - key_data: 密钥数据（公钥或对称密钥标识）
            - algorithm: 算法名称
            - is_symmetric: 是否为对称加密

        Raises:
            JWTValidationError: 获取公钥失败时
        """
        try:
            # 检查缓存是否有效（缓存提升性能，但不阻止动态更新）
            current_time = time.time()
            if (self._public_key_cache and
                self._public_key_algorithm and
                self._is_symmetric is not None and
                self._key_cache_time and
                current_time - self._key_cache_time < self._key_cache_ttl):

                print("[JWTValidator] 使用缓存的公钥信息")
                return self._public_key_cache, self._public_key_algorithm, self._is_symmetric

            # 优先从微服务获取最新公钥（权威来源）
            print("[JWTValidator] 从认证微服务获取公钥信息")
            response = await self.auth_client.get_public_key()

            if response.get("code") != 200:
                raise JWTValidationError(f"获取公钥失败: {response.get('message', '未知错误')}")

            data = response.get("data", {})
            public_key = data.get("public_key", "")

            if not public_key:
                # 微服务返回空公钥，表示使用对称加密
                print("[JWTValidator] 微服务明确使用对称加密")
                key_data = self.local_secret
                algorithm = self.local_algorithm
                is_symmetric = True
            else:
                # 微服务返回公钥，使用非对称加密
                print("[JWTValidator] 微服务返回RS256公钥")
                key_data = public_key
                # 这里假设微服务也会返回算法信息，否则使用默认值
                algorithm = data.get("algorithm", "RS256")
                is_symmetric = False

            # 更新缓存
            self._public_key_cache = key_data
            self._public_key_algorithm = algorithm
            self._is_symmetric = is_symmetric
            self._key_cache_time = current_time

            print(f"[JWTValidator] 成功缓存公钥信息: algorithm={algorithm}, is_symmetric={is_symmetric}")
            return key_data, algorithm, is_symmetric

        except Exception as e:
            # 微服务不可用，降级到本地配置（备份方案）
            print(f"[JWTValidator] ⚠️  从微服务获取公钥失败: {str(e)}")

            if self.local_public_key and self.local_algorithm in ["RS256", "RS384", "RS512"]:
                print("[JWTValidator] 🔄 降级使用本地配置的公钥（备份方案）")
                return self.local_public_key, self.local_algorithm, False

            print("[JWTValidator] 🔄 降级使用本地对称密钥（备份方案）")
            return self.local_secret, self.local_algorithm, True

    def _get_token_hash(self, token: str) -> str:
        """生成token的哈希值用作缓存键"""
        return hashlib.sha256(token.encode()).hexdigest()

    def _clean_cache(self) -> None:
        """清理过期的用户信息缓存"""
        current_time = time.time()
        expired_keys = []

        for token_hash, user_info in self._user_cache.items():
            if user_info.is_cache_expired(self._user_cache_ttl):
                expired_keys.append(token_hash)

        for key in expired_keys:
            del self._user_cache[key]

        # 如果缓存太大，删除最旧的条目
        if len(self._user_cache) > self._max_cache_size:
            sorted_items = sorted(self._user_cache.items(), key=lambda x: x[1].cache_time)
            excess_count = len(self._user_cache) - self._max_cache_size
            for token_hash, _ in sorted_items[:excess_count]:
                del self._user_cache[token_hash]

    def _get_user_from_cache(self, token: str) -> Optional[UserInfo]:
        """从缓存获取用户信息"""
        token_hash = self._get_token_hash(token)
        user_info = self._user_cache.get(token_hash)

        if user_info:
            # 检查缓存和token是否过期
            if not user_info.is_cache_expired(self._user_cache_ttl) and not user_info.is_expired():
                return user_info
            else:
                # 过期则删除
                del self._user_cache[token_hash]

        return None

    def _cache_user_info(self, token: str, payload: Dict[str, Any]) -> UserInfo:
        """缓存用户信息"""
        token_hash = self._get_token_hash(token)
        user_info = UserInfo(
            user_id=payload.get('sub', ''),
            is_guest=payload.get('is_guest', True),
            exp=payload.get('exp', 0),
            iat=payload.get('iat', 0),
            token_hash=token_hash,
            cache_time=time.time()
        )

        self._user_cache[token_hash] = user_info
        self._clean_cache()  # 清理过期缓存

        return user_info

    async def validate_token(self, token: str) -> TokenValidationResult:
        """
        验证JWT令牌

        这是主要的验证方法，负责：
        - 检查缓存
        - 获取公钥信息
        - 验证令牌签名
        - 检查令牌有效性
        - 缓存用户信息
        - 返回解码后的payload和用户信息

        Args:
            token: JWT令牌字符串

        Returns:
            TokenValidationResult: 包含payload和用户信息的验证结果

        Raises:
            HTTPException: 令牌验证失败时
        """
        try:
            # 首先检查缓存
            cached_user = self._get_user_from_cache(token)
            if cached_user:
                print(f"[JWTValidator] 使用缓存的用户信息: user_id={cached_user.user_id}")
                # 从缓存中恢复payload（基本信息）
                payload = {
                    'sub': cached_user.user_id,
                    'is_guest': cached_user.is_guest,
                    'exp': cached_user.exp,
                    'iat': cached_user.iat,
                    'token_type': 'access'
                }
                return TokenValidationResult(payload=payload, user_info=cached_user)

            print(f"[JWTValidator] 缓存未命中，验证token: {token[:20]}...")

            # 获取公钥信息
            key_data, algorithm, is_symmetric = await self._get_public_key_info()

            print(f"[JWTValidator] 验证令牌: algorithm={algorithm}, is_symmetric={is_symmetric}")

            # 根据加密类型选择验证方式
            if is_symmetric:
                # 对称加密验证
                payload = jwt.decode(
                    token,
                    key_data,
                    algorithms=[algorithm],
                    options={
                        'require': ['exp', 'iat', 'sub'],  # 必需字段
                        'verify_aud': False,  # 暂时不验证aud
                        'verify_iss': False   # 暂时不验证iss
                    }
                )
            else:
                # 非对称加密验证
                payload = jwt.decode(
                    token,
                    key_data,
                    algorithms=[algorithm],
                    options={
                        'require': ['exp', 'iat', 'sub'],
                        'verify_aud': False,
                        'verify_iss': False
                    }
                )

            print(f"[JWTValidator] 令牌验证成功: user_id={payload.get('sub')}")

            # 缓存用户信息
            user_info = self._cache_user_info(token, payload)

            return TokenValidationResult(payload=payload, user_info=user_info)

        except jwt.ExpiredSignatureError as e:
            print(f"[JWTValidator] 令牌已过期: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证令牌已过期",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            print(f"[JWTValidator] 无效令牌: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"无效的认证令牌: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            print(f"[JWTValidator] 令牌验证异常: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"令牌验证失败: {str(e)}"
            )

    def invalidate_cache(self) -> None:
        """
        使缓存失效

        当怀疑公钥已更新时，可以调用此方法强制刷新缓存
        """
        print("[JWTValidator] 使公钥和用户缓存失效")
        self._public_key_cache = None
        self._public_key_algorithm = None
        self._is_symmetric = None
        self._key_cache_time = None
        self._user_cache.clear()  # 清空用户信息缓存

    async def refresh_public_key(self) -> bool:
        """
        强制刷新公钥缓存

        Returns:
            刷新是否成功
        """
        try:
            self.invalidate_cache()
            await self._get_public_key_info()
            print("[JWTValidator] 公钥缓存刷新成功")
            return True
        except Exception as e:
            print(f"[JWTValidator] 公钥缓存刷新失败: {str(e)}")
            return False

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            缓存状态信息
        """
        return {
            "has_cached_key": self._public_key_cache is not None,
            "algorithm": self._public_key_algorithm,
            "is_symmetric": self._is_symmetric,
            "cache_time": self._key_cache_time,
            "cache_age": time.time() - self._key_cache_time if self._key_cache_time else None,
            "cache_ttl": self._key_cache_ttl
        }


# 全局JWT验证器实例（单例模式）
_jwt_validator: Optional[JWTValidator] = None


def get_jwt_validator() -> JWTValidator:
    """
    获取全局JWT验证器实例

    使用单例模式，避免重复创建验证器实例。

    Returns:
        JWTValidator实例
    """
    global _jwt_validator
    if _jwt_validator is None:
        _jwt_validator = JWTValidator()
    return _jwt_validator


async def validate_jwt_token(token: str) -> TokenValidationResult:
    """
    便捷的JWT令牌验证函数

    Args:
        token: JWT令牌字符串

    Returns:
        TokenValidationResult: 包含payload和用户信息的验证结果

    Raises:
        HTTPException: 令牌验证失败时
    """
    validator = get_jwt_validator()
    return await validator.validate_token(token)


async def validate_jwt_token_simple(token: str) -> Dict[str, Any]:
    """
    简化的JWT令牌验证函数（向后兼容）

    Args:
        token: JWT令牌字符串

    Returns:
        解码后的令牌payload

    Raises:
        HTTPException: 令牌验证失败时
    """
    result = await validate_jwt_token(token)
    return result.payload