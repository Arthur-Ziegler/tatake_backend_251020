"""
简化认证领域Service层

根据设计文档，Service层大幅简化：
1. 只保留核心的JWTService和AuthService
2. 移除SMS、用户管理等非核心服务
3. 专注于微信登录和游客管理的简化流程
4. 统一响应格式和错误处理

Service职责:
- JWTService: JWT令牌生成和验证
- AuthService: 核心认证业务逻辑

设计原则:
- 极简化：只保留认证核心功能
- 微信单一登录：只支持微信OpenID认证
- 游客简化：每次创建新的随机游客身份
- 统一响应：所有API返回统一格式
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from uuid import UUID, uuid4

from jose import JWTError, jwt

from .database import get_auth_db
from .repository import AuthRepository, AuditRepository
from .models import Auth, AuthLog
from .schemas import (
    # 请求模型
    GuestInitRequest,
    WeChatRegisterRequest,
    WeChatLoginRequest,
    GuestUpgradeRequest,
    TokenRefreshRequest,
)
from .exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    ValidationError
)


class JWTService:
    """
    简化的JWT令牌管理服务

    专注于JWT令牌的生成、验证和基本管理。
    移除复杂黑名单管理，采用无状态设计。
    """

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-here")
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.algorithm = "HS256"

    def generate_tokens(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成访问令牌和刷新令牌

        Args:
            user_data: 用户数据字典，至少包含user_id

        Returns:
            Dict[str, Any]: 包含access_token和refresh_token的字典
        """
        now = datetime.now(timezone.utc)

        # 访问令牌载荷
        access_payload = {
            "sub": str(user_data["user_id"]),
            "is_guest": user_data.get("is_guest", False),
            "jwt_version": user_data.get("jwt_version", 1),
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes),
            "jti": str(uuid4())  # JWT ID
        }

        # 刷新令牌载荷
        refresh_payload = {
            "sub": str(user_data["user_id"]),
            "is_guest": user_data.get("is_guest", False),
            "jwt_version": user_data.get("jwt_version", 1),
            "token_type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days),
            "jti": str(uuid4())  # JWT ID
        }

        # 生成令牌
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60  # 秒
        }

    def verify_token(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
        """
        验证JWT令牌

        Args:
            token: JWT令牌字符串
            expected_type: 期望的令牌类型（access或refresh）

        Returns:
            Dict[str, Any]: 令牌载荷数据

        Raises:
            TokenException: 令牌验证失败
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 验证令牌类型
            if payload.get("token_type") != expected_type:
                raise TokenException(f"令牌类型不匹配，期望: {expected_type}", "TOKEN_TYPE_MISMATCH")

            return payload

        except JWTError as e:
            raise TokenException(f"令牌验证失败: {str(e)}", "TOKEN_VERIFICATION_FAILED")


class AuthService:
    """
    简化的核心认证服务

    专注于核心认证业务逻辑：
    - 游客初始化
    - 微信注册（创建游客+立即升级）
    - 微信登录
    - 游客升级
    - 令牌刷新

    移除的功能：
    - SMS验证码
    - 密码登录
    - 会话管理
    - 用户信息查询
    """

    def __init__(self):
        self.jwt_service = JWTService()

    def init_guest_account(
        self,
        request: GuestInitRequest,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        初始化游客账号

        根据设计文档，每次都创建全新的随机游客身份，
        不依赖任何设备信息。

        Args:
            request: 游客初始化请求（无参数）
            ip_address: 客户端IP地址
            user_agent: 客户端用户代理

        Returns:
            Dict[str, Any]: 包含用户信息和令牌的字典

        Raises:
            AuthenticationException: 游客账号创建失败
        """
        try:
            with get_auth_db() as session:
                auth_repo = AuthRepository(session)
                audit_repo = AuditRepository(session)

                # 创建游客用户（每次都是新的）
                guest = auth_repo.create_user(
                    is_guest=True,
                    wechat_openid=None
                )

                # 生成JWT令牌
                user_data = {
                    "user_id": str(guest.id),
                    "is_guest": True,
                    "jwt_version": guest.jwt_version
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=guest.id,
                    action="guest_init",
                    result="success",
                    details="游客账号初始化成功",
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                return {
                    "user_id": str(guest.id),
                    "is_guest": True,
                    **tokens
                }

        except Exception as e:
            raise AuthenticationException(f"游客账号初始化失败: {str(e)}")

    def wechat_register(
        self,
        request: WeChatRegisterRequest,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        微信注册

        根据设计文档，微信注册本质上是"创建游客 + 立即升级"的组合操作。
        内部实现：1. 检查openid是否已存在 2. 创建游客账号 3. 立即升级

        Args:
            request: 微信注册请求
            ip_address: 客户端IP地址
            user_agent: 客户端用户代理

        Returns:
            Dict[str, Any]: 包含用户信息和令牌的字典

        Raises:
            AuthenticationException: 注册失败
        """
        try:
            with get_auth_db() as session:
                auth_repo = AuthRepository(session)
                audit_repo = AuditRepository(session)

                # 1. 检查openid是否已存在
                existing_user = auth_repo.get_by_wechat_openid(request.wechat_openid)
                if existing_user:
                    raise ValidationError("该微信账号已注册")

                # 2. 创建游客账号
                guest = auth_repo.create_user(
                    is_guest=True,
                    wechat_openid=None
                )

                # 3. 立即升级为正式用户
                user = auth_repo.upgrade_guest_account(
                    user_id=guest.id,
                    wechat_openid=request.wechat_openid
                )

                # 4. 生成JWT令牌
                user_data = {
                    "user_id": str(user.id),
                    "is_guest": False,
                    "jwt_version": user.jwt_version
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 5. 记录审计日志
                audit_repo.create_log(
                    user_id=user.id,
                    action="register",
                    result="success",
                    details=f"微信注册成功，openid: {request.wechat_openid}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                return {
                    "user_id": str(user.id),
                    "is_guest": False,
                    **tokens
                }

        except ValidationError:
            raise  # 重新抛出验证错误
        except Exception as e:
            raise AuthenticationException(f"微信注册失败: {str(e)}")

    def wechat_login(
        self,
        request: WeChatLoginRequest,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        微信登录

        Args:
            request: 微信登录请求
            ip_address: 客户端IP地址
            user_agent: 客户端用户代理

        Returns:
            Dict[str, Any]: 包含用户信息和令牌的字典

        Raises:
            AuthenticationException: 登录失败
        """
        try:
            with get_auth_db() as session:
                auth_repo = AuthRepository(session)
                audit_repo = AuditRepository(session)

                # 查找用户
                user = auth_repo.get_by_wechat_openid(request.wechat_openid)
                if not user:
                    raise UserNotFoundException("用户不存在，请先注册")

                # 更新最后登录时间
                auth_repo.update_last_login(user.id)

                # 生成JWT令牌
                user_data = {
                    "user_id": str(user.id),
                    "is_guest": user.is_guest,
                    "jwt_version": user.jwt_version
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=user.id,
                    action="login",
                    result="success",
                    details=f"微信登录成功，openid: {request.wechat_openid}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                return {
                    "user_id": str(user.id),
                    "is_guest": user.is_guest,
                    **tokens
                }

        except (ValidationError, UserNotFoundException):
            raise  # 重新抛出验证错误
        except Exception as e:
            raise AuthenticationException(f"微信登录失败: {str(e)}")

    def upgrade_guest_account(
        self,
        request: GuestUpgradeRequest,
        current_user_id: UUID,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        升级游客账号

        Args:
            request: 游客升级请求
            current_user_id: 当前用户的ID（从JWT中获取）
            ip_address: 客户端IP地址
            user_agent: 客户端用户代理

        Returns:
            Dict[str, Any]: 包含用户信息和令牌的字典

        Raises:
            AuthenticationException: 升级失败
        """
        try:
            with get_auth_db() as session:
                auth_repo = AuthRepository(session)
                audit_repo = AuditRepository(session)

                # 获取当前用户
                current_user = auth_repo.get_by_id(current_user_id)
                if not current_user or not current_user.is_guest:
                    raise ValidationError("无效的游客账号")

                # 检查openid是否已被使用
                existing_user = auth_repo.get_by_wechat_openid(request.wechat_openid)
                if existing_user and existing_user.id != current_user_id:
                    raise ValidationError("该微信账号已被其他用户使用")

                # 升级游客账号
                updated_user = auth_repo.upgrade_guest_account(
                    user_id=current_user_id,
                    wechat_openid=request.wechat_openid
                )

                # 生成新的JWT令牌
                user_data = {
                    "user_id": str(updated_user.id),
                    "is_guest": False,
                    "jwt_version": updated_user.jwt_version
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=updated_user.id,
                    action="upgrade",
                    result="success",
                    details=f"游客升级成功，openid: {request.wechat_openid}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                return {
                    "user_id": str(updated_user.id),
                    "is_guest": False,
                    **tokens
                }

        except ValidationError:
            raise  # 重新抛出验证错误
        except Exception as e:
            raise AuthenticationException(f"游客升级失败: {str(e)}")

    def refresh_token(
        self,
        request: TokenRefreshRequest,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        刷新访问令牌

        Args:
            request: 令牌刷新请求
            ip_address: 客户端IP地址
            user_agent: 客户端用户代理

        Returns:
            Dict[str, Any]: 包含新令牌的字典

        Raises:
            TokenException: 令牌刷新失败
        """
        try:
            # 验证刷新令牌
            token_payload = self.jwt_service.verify_token(request.refresh_token, "refresh")
            user_id = UUID(token_payload["sub"])

            with get_auth_db() as session:
                auth_repo = AuthRepository(session)
                audit_repo = AuditRepository(session)

                # 获取用户信息
                user = auth_repo.get_by_id(user_id)
                if not user:
                    raise UserNotFoundException("用户不存在")

                # 检查JWT版本
                if token_payload.get("jwt_version", 1) != user.jwt_version:
                    raise TokenException("令牌版本不匹配", "TOKEN_VERSION_MISMATCH")

                # 生成新的令牌
                user_data = {
                    "user_id": str(user.id),
                    "is_guest": user.is_guest,
                    "jwt_version": user.jwt_version
                }
                new_tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=user.id,
                    action="token_refresh",
                    result="success",
                    details="令牌刷新成功",
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                return {
                    "user_id": str(user.id),
                    "is_guest": user.is_guest,
                    **new_tokens
                }

        except (ValidationError, TokenException, UserNotFoundException):
            raise  # 重新抛出验证错误
        except Exception as e:
            raise TokenException(f"令牌刷新失败: {str(e)}", "TOKEN_REFRESH_FAILED")


# ===== 删除的服务注释 =====
# 以下服务已被删除，原因：
# - SMSService: 移除短信验证功能
# - UserService: 用户管理移至独立user领域
# - 会话管理相关服务: 采用无状态JWT设计