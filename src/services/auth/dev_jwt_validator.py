"""
开发环境JWT验证器

提供开发环境下的JWT验证解决方案，包括：
1. 跳过签名验证（仅限开发环境）
2. 智能密钥匹配
3. 降级验证模式
"""

import os
import jwt
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

from .jwt_validator import JWTValidator, TokenValidationResult, UserInfo


class DevJWTValidator(JWTValidator):
    """
    开发环境JWT验证器

    继承自JWTValidator，添加开发环境的特殊处理逻辑：
    - 在无法获取正确密钥时，跳过签名验证
    - 提供更详细的调试信息
    - 支持开发环境的降级验证
    """

    def __init__(self, auth_client=None, skip_signature_verification: bool = None):
        """
        初始化开发环境JWT验证器

        Args:
            auth_client: 认证微服务客户端
            skip_signature_verification: 是否跳过签名验证，None时自动判断
        """
        super().__init__(auth_client)

        # 开发环境检测
        self.is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"

        # 签名验证控制
        if skip_signature_verification is None:
            self.skip_signature = self.is_development and os.getenv("JWT_SKIP_SIGNATURE", "false").lower() == "true"
        else:
            self.skip_signature = skip_signature_verification

        print(f"[DevJWTValidator] 初始化: development={self.is_development}, skip_signature={self.skip_signature}")

    async def validate_token(self, token: str) -> TokenValidationResult:
        """
        开发环境JWT验证方法

        Args:
            token: JWT令牌字符串

        Returns:
            TokenValidationResult: 验证结果
        """
        # 如果启用跳过签名验证，直接解码
        if self.skip_signature:
            return await self._validate_without_signature(token)

        # 否则使用正常验证流程
        try:
            return await super().validate_token(token)
        except Exception as e:
            # 在开发环境下，如果正常验证失败，尝试跳过签名验证
            if self.is_development and os.getenv("JWT_FALLBACK_SKIP_SIGNATURE", "true").lower() == "true":
                print(f"[DevJWTValidator] 正常验证失败，尝试跳过签名验证: {str(e)}")
                return await self._validate_without_signature(token)
            else:
                raise

    async def _validate_without_signature(self, token: str) -> TokenValidationResult:
        """
        跳过签名验证的JWT解码（仅限开发环境）

        Args:
            token: JWT令牌字符串

        Returns:
            TokenValidationResult: 验证结果
        """
        if not self.is_development:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="跳过签名验证仅限开发环境使用"
            )

        try:
            print(f"[DevJWTValidator] 跳过签名验证，解码JWT: {token[:20]}...")

            # 解码JWT但不验证签名
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "require": ["exp", "iat", "sub"],
                    "verify_exp": True,  # 仍然验证过期时间
                    "verify_aud": False,
                    "verify_iss": False
                },
                algorithms=["HS256", "RS256"]
            )

            print(f"[DevJWTValidator] JWT解码成功: user_id={payload.get('sub')}")

            # 创建用户信息对象
            user_info = UserInfo(
                user_id=payload.get('sub', ''),
                is_guest=payload.get('is_guest', True),
                exp=payload.get('exp', 0),
                iat=payload.get('iat', 0),
                token_hash=self._get_token_hash(token),
                cache_time=0  # 跳过签名验证时不缓存
            )

            return TokenValidationResult(payload=payload, user_info=user_info)

        except jwt.ExpiredSignatureError as e:
            print(f"[DevJWTValidator] 令牌已过期: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证令牌已过期",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            print(f"[DevJWTValidator] 无效令牌: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"无效的认证令牌: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            print(f"[DevJWTValidator] 令牌验证异常: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"令牌验证失败: {str(e)}"
            )


# 全局开发环境验证器实例
_dev_jwt_validator: Optional[DevJWTValidator] = None


def get_dev_jwt_validator() -> DevJWTValidator:
    """获取全局开发环境JWT验证器实例"""
    global _dev_jwt_validator
    if _dev_jwt_validator is None:
        _dev_jwt_validator = DevJWTValidator()
    return _dev_jwt_validator


async def validate_jwt_token_dev(token: str) -> Dict[str, Any]:
    """
    开发环境JWT验证便捷函数

    Args:
        token: JWT令牌字符串

    Returns:
        解码后的令牌payload
    """
    validator = get_dev_jwt_validator()
    result = await validator.validate_token(token)
    return result.payload


async def validate_jwt_token_dev_result(token: str) -> TokenValidationResult:
    """
    开发环境JWT验证便捷函数（返回完整结果）

    Args:
        token: JWT令牌字符串

    Returns:
        TokenValidationResult: 完整验证结果
    """
    validator = get_dev_jwt_validator()
    return await validator.validate_token(token)