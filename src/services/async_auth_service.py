"""
异步认证服务模块

该模块实现异步用户认证相关的业务逻辑，包括游客账号初始化、游客账号升级、
用户登录、令牌刷新、用户登出等功能。支持多种认证方式：手机号、邮箱、微信等。

设计原则：
1. 安全优先：采用JWT Token + RefreshToken双重令牌机制
2. 多途径认证：支持手机号、邮箱、微信等多种登录方式
3. 游客模式：零门槛体验，支持数据无缝迁移
4. 异步处理：高并发场景下的高效处理
5. 异常处理：详细的错误信息和安全建议
6. 业务规则：严格的验证和防刷机制

核心功能：
- 异步游客账号初始化和管理
- 异步游客账号升级为正式账号
- 异步多种方式用户登录
- 异步JWT令牌生成和验证
- 异步短信验证码发送和验证
- 异步用户登出和会话管理
"""

import uuid
import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from .async_base import AsyncBaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    DuplicateResourceException,
    AuthenticationException,
    AuthorizationException,
    RateLimitException
)
from src.repositories.async_base import AsyncRepositoryNotFoundError, AsyncRepositoryError
from src.models.user import User


class AsyncAuthService(AsyncBaseService):
    """
    异步认证服务类

    处理异步用户认证相关的所有业务逻辑，包括游客账号管理、用户登录、
    令牌管理等核心认证功能。

    Attributes:
        _user_repo: 异步用户数据访问对象
        _auth_repo: 异步认证数据访问对象
        _token_expiry: 访问令牌过期时间（默认24小时）
        _refresh_token_expiry: 刷新令牌过期时间（默认7天）
    """

    def __init__(self, user_repo=None, auth_repo=None, **kwargs):
        """
        初始化异步认证服务

        Args:
            user_repo: 异步用户数据访问对象
            auth_repo: 异步认证数据访问对象
            **kwargs: 其他参数传递给父类
        """
        super().__init__(_user_repo=user_repo, _auth_repo=auth_repo, **kwargs)

        # 认证相关的Repository
        self._auth_repo = auth_repo
        self._user_repo = user_repo

        # 令牌配置
        self._token_expiry = timedelta(hours=24)  # 访问令牌24小时过期
        self._refresh_token_expiry = timedelta(days=7)  # 刷新令牌7天过期

        # 短信验证码配置
        self._sms_code_expiry = timedelta(minutes=5)  # 验证码5分钟过期
        self._sms_cooldown = timedelta(seconds=60)  # 发送冷却时间1分钟

    # ==================== 游客账号管理 ====================

    async def init_guest_account(self, device_id: Optional[str] = None, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        异步初始化游客账号

        Args:
            device_id: 设备ID，可选
            platform: 平台标识，可选

        Returns:
            Dict[str, Any]: 包含用户信息和令牌的字典

        Raises:
            BusinessException: 游客账号创建失败时
        """
        try:
            self._log_operation_start("初始化游客账号", device_id=device_id, platform=platform)

            # 创建游客用户
            nickname = f"游客_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            user = await self._user_repo.create_guest_user(nickname)

            # 生成JWT令牌
            from .jwt_service import JWTService
            jwt_service = JWTService()

            additional_claims = {
                "is_guest": True,
                "device_id": device_id,
                "platform": platform
            }

            access_token, refresh_token = jwt_service.generate_token_pair(
                user_id=user.id,
                user_type="guest",
                additional_claims=additional_claims
            )

            token_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": 24 * 60 * 60  # 24小时
            }

            self._log_operation_success("初始化游客账号", user_id=user.id)

            return {
                "user": user.to_dict(),
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data["expires_in"]
            }

        except Exception as e:
            self._log_operation_error("初始化游客账号", e)
            raise BusinessException("GUEST_INIT_FAILED", f"初始化游客账号失败: {str(e)}")

    async def upgrade_guest_account(self, guest_user_id: str, upgrade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步升级游客账号为正式账号

        Args:
            guest_user_id: 游客用户ID
            upgrade_data: 升级数据，包含邮箱、手机号等信息

        Returns:
            Dict[str, Any]: 包含升级后用户信息和新令牌的字典

        Raises:
            ValidationException: 升级数据验证失败时
            ResourceNotFoundException: 游客用户不存在时
            DuplicateResourceException: 邮箱或手机号已被使用时
            BusinessException: 升级失败时
        """
        try:
            self._log_operation_start("升级游客账号", guest_user_id=guest_user_id)

            # 验证必要字段
            if not upgrade_data.get("email"):
                raise ValidationException("邮箱是升级账号的必填项")

            # 升级游客用户
            user = await self._user_repo.upgrade_guest_to_registered(
                guest_user_id,
                upgrade_data["email"],
                **{k: v for k, v in upgrade_data.items() if k != "email"}
            )

            # 生成新的JWT令牌
            from .jwt_service import JWTService
            jwt_service = JWTService()

            token_data = jwt_service.generate_token_pair(
                user_id=user.id,
                user_type="registered",
                email=user.email
            )

            self._log_operation_success("升级游客账号", user_id=user.id)

            return {
                "user": user.to_dict(),
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data["expires_in"]
            }

        except (ValidationException, ResourceNotFoundException, DuplicateResourceException):
            raise
        except Exception as e:
            self._log_operation_error("升级游客账号", e)
            raise BusinessException("GUEST_UPGRADE_FAILED", f"升级游客账号失败: {str(e)}")

    # ==================== 短信验证码服务 ====================

    async def send_sms_verification(self, phone: str, verification_type: str, ip_address: str = None) -> Dict[str, Any]:
        """
        异步发送短信验证码

        Args:
            phone: 手机号码
            verification_type: 验证类型（login, register, reset_password等）
            ip_address: 请求IP地址，可选

        Returns:
            Dict[str, Any]: 发送结果

        Raises:
            ValidationException: 手机号格式验证失败时
            RateLimitException: 发送频率超限时
            BusinessException: 发送失败时
        """
        try:
            self._log_operation_start("发送短信验证码", phone=phone, verification_type=verification_type)

            # 验证手机号格式
            if not re.match(r'^1[3-9]\d{9}$', phone):
                raise ValidationException("手机号格式不正确")

            # 检查发送频率限制
            if not await self._auth_repo.check_sms_frequency(phone, verification_type):
                raise RateLimitException(
                    "短信发送频率过快，请稍后再试",
                    cooldown_seconds=60,
                    limit_type="sms_frequency"
                )

            # 使用Mock短信服务发送
            from src.services.external.mock_sms_service import MockSMSService
            mock_sms_service = MockSMSService()

            sms_result = mock_sms_service.send_verification_code(
                phone=phone,
                verification_type=verification_type,
                ip_address=ip_address
            )

            if sms_result["success"]:
                # 获取Mock短信服务生成的验证码
                code = sms_result.get("code", "123456")  # Mock服务默认返回123456

                # 记录短信发送
                await self._auth_repo.record_sms_sent(
                    phone=phone,
                    verification_type=verification_type,
                    code=code,
                    ip_address=ip_address
                )

                self._log_operation_success("发送短信验证码", phone=phone, verification_type=verification_type)

                return {
                    "success": True,
                    "message": "验证码发送成功",
                    "cooldown_seconds": self._sms_cooldown.total_seconds()
                }
            else:
                raise BusinessException("SMS_SEND_FAILED", f"短信发送失败: {sms_result.get('message', '未知错误')}")

        except (ValidationException, RateLimitException, BusinessException):
            raise
        except Exception as e:
            self._log_operation_error("发送短信验证码", e)
            raise BusinessException("SMS_VERIFICATION_SEND_FAILED", f"发送短信验证码失败: {str(e)}")

    async def verify_sms_code(self, phone: str, verification_type: str, code: str) -> Dict[str, Any]:
        """
        异步验证短信验证码

        Args:
            phone: 手机号码
            verification_type: 验证类型
            code: 验证码

        Returns:
            Dict[str, Any]: 验证结果

        Raises:
            ValidationException: 验证码格式验证失败时
            BusinessException: 验证失败时
        """
        try:
            self._log_operation_start("验证短信验证码", phone=phone, verification_type=verification_type)

            # 获取最新的短信记录
            sms_record = await self._auth_repo.get_latest_sms_code(phone, verification_type)
            if not sms_record:
                raise ValidationException("请先获取验证码")

            # 检查验证码是否正确
            if sms_record.code != code:
                self._log_business_exception("验证短信验证码",
                    ValidationException("验证码错误"))
                raise ValidationException("验证码错误")

            # 检查验证码是否过期
            # 确保时间比较的时区一致性
            now = datetime.now(timezone.utc)
            created_at = sms_record.created_at
            # 如果created_at是timezone-naive，则假设其为UTC时间
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            if now > created_at + self._sms_code_expiry:
                raise ValidationException("验证码已过期，请重新获取")

            # 标记短信记录为已验证
            await self._auth_repo.mark_sms_verified(sms_record.id)

            self._log_operation_success("验证短信验证码", phone=phone, verification_type=verification_type)

            return {
                "success": True,
                "message": "验证码验证成功"
            }

        except ValidationException:
            raise
        except Exception as e:
            self._log_operation_error("验证短信验证码", e)
            raise BusinessException("SMS_VERIFICATION_FAILED", f"验证短信验证码失败: {str(e)}")

    # ==================== 用户登录服务 ====================

    async def login_with_phone(self, phone: str, code: str, device_id: str = None) -> Dict[str, Any]:
        """
        异步手机号验证码登录

        Args:
            phone: 手机号码
            code: 短信验证码
            device_id: 设备ID，可选

        Returns:
            Dict[str, Any]: 登录结果，包含用户信息和令牌

        Raises:
            ValidationException: 验证码验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 登录失败时
        """
        try:
            self._log_operation_start("手机号登录", phone=phone)

            # 验证短信验证码
            await self.verify_sms_code(phone, "login", code)

            # 查找或创建用户
            try:
                user = await self._user_repo.find_by_phone(phone)
            except (ResourceNotFoundException, AsyncRepositoryNotFoundError) as e:
                # 用户不存在，自动创建
                user = await self._user_repo.create({
                    "phone": phone,
                    "nickname": f"用户_{phone[-4:]}",  # 使用手机号后4位作为昵称
                    "is_guest": False
                })
            except AsyncRepositoryError as e:
                # 检查是否是用户不存在的错误（被包装的AsyncRepositoryNotFoundError）
                if "未找到手机号为" in str(e):
                    user = await self._user_repo.create({
                        "phone": phone,
                        "nickname": f"用户_{phone[-4:]}",  # 使用手机号后4位作为昵称
                        "is_guest": False
                    })
                else:
                    # 其他类型的数据库错误，重新抛出
                    raise

            # 更新最后登录时间
            await self._user_repo.update(user.id, {
                "last_login_at": datetime.now(timezone.utc),
                "last_login_device": device_id
            })

            # 生成JWT令牌
            from .jwt_service import JWTService
            jwt_service = JWTService()

            additional_claims = {
                "phone": phone,
                "device_id": device_id
            }

            access_token, refresh_token = jwt_service.generate_token_pair(
                user_id=user.id,
                user_type="registered",
                additional_claims=additional_claims
            )

            token_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": 24 * 60 * 60  # 24小时
            }

            self._log_operation_success("手机号登录", user_id=user.id)

            return {
                "user": user.to_dict(),
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data["expires_in"]
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            self._log_operation_error("手机号登录", e)
            raise BusinessException("PHONE_LOGIN_FAILED", f"手机号登录失败: {str(e)}")

    async def login_with_email(self, email: str, password: str, device_id: str = None) -> Dict[str, Any]:
        """
        异步邮箱密码登录

        Args:
            email: 邮箱地址
            password: 密码
            device_id: 设备ID，可选

        Returns:
            Dict[str, Any]: 登录结果，包含用户信息和令牌

        Raises:
            ValidationException: 邮箱或密码验证失败时
            ResourceNotFoundException: 用户不存在时
            AuthenticationException: 密码错误时
            BusinessException: 登录失败时
        """
        try:
            self._log_operation_start("邮箱登录", email=email)

            # 查找用户
            user = await self._user_repo.find_by_email(email)

            # 验证密码（这里需要实现密码哈希验证）
            if not self._verify_password(password, user.password_hash if hasattr(user, 'password_hash') else None):
                raise AuthenticationException("邮箱或密码错误")

            # 更新最后登录时间
            await self._user_repo.update(user.id, {
                "last_login_at": datetime.now(timezone.utc),
                "last_login_device": device_id
            })

            # 生成JWT令牌
            from .jwt_service import JWTService
            jwt_service = JWTService()

            token_data = jwt_service.generate_token_pair(
                user_id=user.id,
                user_type="registered",
                email=email,
                device_id=device_id
            )

            self._log_operation_success("邮箱登录", user_id=user.id)

            return {
                "user": user.to_dict(),
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data["expires_in"]
            }

        except (ValidationException, ResourceNotFoundException, AsyncRepositoryNotFoundError, AuthenticationException):
            raise
        except Exception as e:
            self._log_operation_error("邮箱登录", e)
            raise BusinessException("EMAIL_LOGIN_FAILED", f"邮箱登录失败: {str(e)}")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        验证密码

        Args:
            password: 明文密码
            password_hash: 密码哈希

        Returns:
            bool: 密码正确返回True，否则返回False
        """
        # 这里需要实现密码哈希验证逻辑
        # 目前简化处理，实际项目中应该使用bcrypt等安全的哈希算法
        if password_hash is None:
            return False
        return hashlib.sha256(password.encode()).hexdigest() == password_hash

    # ==================== 令牌管理服务 ====================

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        异步刷新访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            Dict[str, Any]: 新的令牌信息

        Raises:
            ValidationException: 刷新令牌无效时
            BusinessException: 刷新失败时
        """
        try:
            self._log_operation_start("刷新访问令牌")

            # 验证刷新令牌
            from .jwt_service import JWTService
            jwt_service = JWTService()

            token_payload = jwt_service.verify_refresh_token(refresh_token)
            user_id = token_payload.get("user_id")

            # 检查用户是否存在
            user = await self._user_repo.get_by_id(user_id)
            if not user:
                raise ResourceNotFoundException("用户不存在")

            # 生成新的令牌对
            token_data = jwt_service.generate_token_pair(
                user_id=user.id,
                user_type=token_payload.get("user_type", "registered"),
                email=getattr(user, 'email', None),
                phone=getattr(user, 'phone', None)
            )

            self._log_operation_success("刷新访问令牌", user_id=user.id)

            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data["expires_in"]
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            self._log_operation_error("刷新访问令牌", e)
            raise BusinessException("TOKEN_REFRESH_FAILED", f"刷新访问令牌失败: {str(e)}")

    async def logout(self, access_token: str, refresh_token: str = None) -> Dict[str, Any]:
        """
        异步用户登出

        Args:
            access_token: 访问令牌
            refresh_token: 刷新令牌，可选

        Returns:
            Dict[str, Any]: 登出结果

        Raises:
            BusinessException: 登出失败时
        """
        try:
            self._log_operation_start("用户登出")

            from .jwt_service import JWTService
            jwt_service = JWTService()

            # 将访问令牌加入黑名单
            try:
                token_payload = jwt_service.verify_access_token(access_token)
                expires_at = datetime.fromtimestamp(token_payload["exp"], tz=timezone.utc)

                await self._auth_repo.add_to_blacklist(
                    token=access_token,
                    expires_at=expires_at,
                    user_id=token_payload.get("user_id"),
                    reason="用户登出"
                )
            except Exception:
                # 令牌验证失败，忽略错误继续处理
                pass

            # 将刷新令牌加入黑名单（如果提供）
            if refresh_token:
                try:
                    refresh_payload = jwt_service.verify_refresh_token(refresh_token)
                    expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)

                    await self._auth_repo.add_to_blacklist(
                        token=refresh_token,
                        expires_at=expires_at,
                        user_id=refresh_payload.get("user_id"),
                        reason="用户登出"
                    )
                except Exception:
                    # 刷新令牌验证失败，忽略错误继续处理
                    pass

            self._log_operation_success("用户登出")

            return {
                "success": True,
                "message": "登出成功"
            }

        except Exception as e:
            self._log_operation_error("用户登出", e)
            raise BusinessException("LOGOUT_FAILED", f"用户登出失败: {str(e)}")

    # ==================== 用户信息服务 ====================

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        异步获取用户资料

        Args:
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 用户资料信息

        Raises:
            ResourceNotFoundException: 用户不存在时
            BusinessException: 获取失败时
        """
        try:
            self._log_operation_start("获取用户资料", user_id=user_id)

            user = await self._user_repo.get_by_id(user_id)
            if not user:
                raise ResourceNotFoundException("用户不存在")

            self._log_operation_success("获取用户资料", user_id=user_id)

            return {
                "user": user.to_dict()
            }

        except ResourceNotFoundException:
            raise
        except Exception as e:
            self._log_operation_error("获取用户资料", e)
            raise BusinessException("GET_USER_PROFILE_FAILED", f"获取用户资料失败: {str(e)}")


# 导出AsyncAuthService类
__all__ = ["AsyncAuthService"]