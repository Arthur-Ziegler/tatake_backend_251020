"""
认证服务模块

该模块实现用户认证相关的业务逻辑，包括游客账号初始化、游客账号升级、
用户登录、令牌刷新、用户登出等功能。支持多种认证方式：手机号、邮箱、微信等。

设计原则：
1. 安全优先：采用JWT Token + RefreshToken双重令牌机制
2. 多途径认证：支持手机号、邮箱、微信等多种登录方式
3. 游客模式：零门槛体验，支持数据无缝迁移
4. 异常处理：详细的错误信息和安全建议
5. 业务规则：严格的验证和防刷机制

核心功能：
- 游客账号初始化和管理
- 游客账号升级为正式账号
- 多种方式用户登录
- JWT令牌生成和验证
- 短信验证码发送和验证
- 用户登出和会话管理
"""

import uuid
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from .base import BaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    DuplicateResourceException,
    AuthenticationException,
    AuthorizationException
)
from src.models.user import User


class AuthService(BaseService):
    """
    认证服务类

    处理用户认证相关的所有业务逻辑，包括游客账号管理、用户登录、
    令牌管理等核心认证功能。

    Attributes:
        _user_repo: 用户数据访问对象
        _token_expiry: 访问令牌过期时间（默认24小时）
        _refresh_token_expiry: 刷新令牌过期时间（默认7天）
    """

    def __init__(self, user_repo=None, task_repo=None, focus_repo=None, reward_repo=None, chat_repo=None,
                 token_blacklist_repo=None, sms_verification_repo=None, user_session_repo=None,
                 auth_log_repo=None, **kwargs):
        """
        初始化认证服务

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            chat_repo: 聊天数据访问对象
            token_blacklist_repo: JWT令牌黑名单数据访问对象
            sms_verification_repo: 短信验证码数据访问对象
            user_session_repo: 用户会话数据访问对象
            auth_log_repo: 认证日志数据访问对象
            **kwargs: 其他参数传递给父类
        """
        super().__init__(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo,
            chat_repo=chat_repo,
            **kwargs
        )

        # 认证相关的Repository（用于替代Redis功能）
        self._token_blacklist_repo = token_blacklist_repo
        self._sms_verification_repo = sms_verification_repo
        self._user_session_repo = user_session_repo
        self._auth_log_repo = auth_log_repo

        # 令牌配置
        self._token_expiry = timedelta(hours=24)  # 访问令牌24小时过期
        self._refresh_token_expiry = timedelta(days=7)  # 刷新令牌7天过期

        # 短信验证码配置
        self._sms_code_expiry = timedelta(minutes=5)  # 验证码5分钟过期
        self._sms_cooldown = timedelta(seconds=60)  # 发送冷却时间1分钟

    # ==================== 游客账号管理 ====================

    def init_guest_account(self, device_id: Optional[str] = None, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        初始化游客账号

        创建一个临时的游客账号，返回访问令牌和用户信息。
        游客账号有一定的功能限制，但可以体验核心功能。

        Args:
            device_id: 设备ID（可选，用于设备绑定）
            platform: 平台信息（可选，如iOS、Android、Web等）

        Returns:
            包含用户信息和令牌的字典

        Raises:
            BusinessException: 当账号创建失败时
        """
        try:
            self._log_info("开始初始化游客账号", {
                "device_id": device_id,
                "platform": platform
            })

            # 生成唯一的游客用户ID
            guest_user_id = f"guest_{uuid.uuid4().hex[:16]}"

            # 创建游客用户数据
            user_data = {
                "id": guest_user_id,
                "nickname": f"游客{datetime.now().strftime('%m%d%H%M')}",
                "is_guest": True,
                "is_active": True,
                "device_id": device_id,
                "platform": platform,
                "points": 0,  # 游客初始积分为0
                "fragments": 0,  # 游客初始碎片为0
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }

            # 创建用户
            guest_user = self.get_user_repository().create(user_data)

            # 生成令牌
            access_token, refresh_token = self._generate_tokens(guest_user)

            # 构建响应
            response = {
                "user_id": guest_user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": int(self._token_expiry.total_seconds()),
                "is_guest": True,
                "user_info": {
                    "nickname": guest_user.nickname,
                    "points": guest_user.points,
                    "fragments": guest_user.fragments
                }
            }

            self._log_info("游客账号初始化成功", {
                "user_id": guest_user.id,
                "device_id": device_id
            })

            return response

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "init_guest_account", {
                "device_id": device_id,
                "platform": platform
            })

    def upgrade_guest_account(
        self,
        guest_user_id: str,
        upgrade_type: str,
        **upgrade_data
    ) -> Dict[str, Any]:
        """
        游客账号升级

        将游客账号升级为正式账号，支持手机号、邮箱、微信等多种升级方式。
        升级后保留游客账号的所有数据，并激活正式账号功能。

        Args:
            guest_user_id: 游客用户ID
            upgrade_type: 升级类型（phone/email/wechat）
            **upgrade_data: 升级数据，根据类型不同而不同

        Returns:
            包含更新后用户信息和令牌的字典

        Raises:
            ValidationException: 当升级数据无效时
            ResourceNotFoundException: 当游客账号不存在时
            DuplicateResourceException: 当升级账号已存在时
            AuthenticationException: 当验证失败时
        """
        try:
            self._log_info("开始游客账号升级", {
                "guest_user_id": guest_user_id,
                "upgrade_type": upgrade_type
            })

            # 验证升级类型
            if upgrade_type not in ["phone", "email", "wechat"]:
                raise ValidationException(
                    message="不支持的升级类型",
                    details={"upgrade_type": upgrade_type, "supported_types": ["phone", "email", "wechat"]}
                )

            # 检查游客账号是否存在
            guest_user = self._check_resource_exists(
                self.get_user_repository(),
                guest_user_id,
                "游客账号"
            )

            if not guest_user.is_guest:
                raise ValidationException(
                    message="只有游客账号可以升级",
                    details={"is_guest": guest_user.is_guest}
                )

            # 根据升级类型执行升级逻辑
            if upgrade_type == "phone":
                self._upgrade_by_phone(guest_user, **upgrade_data)
            elif upgrade_type == "email":
                self._upgrade_by_email(guest_user, **upgrade_data)
            elif upgrade_type == "wechat":
                self._upgrade_by_wechat(guest_user, **upgrade_data)

            # 更新用户类型为注册用户
            update_data = {
                "is_guest": False,
                "updated_at": datetime.now()
            }

            # 添加账号特定信息
            if upgrade_type == "phone" and "phone" in upgrade_data:
                update_data["phone"] = upgrade_data["phone"]
            elif upgrade_type == "email" and "email" in upgrade_data:
                update_data["email"] = upgrade_data["email"]
            elif upgrade_type == "wechat" and "wechat_openid" in upgrade_data:
                update_data["wechat_openid"] = upgrade_data["wechat_openid"]

            # 如果提供了昵称，更新昵称
            if "nickname" in upgrade_data and upgrade_data["nickname"]:
                update_data["nickname"] = upgrade_data["nickname"]

            # 升级游客账号
            updated_user = self.get_user_repository().upgrade_guest_to_registered(
                guest_user_id,
                **update_data
            )

            # 生成新的令牌
            access_token, refresh_token = self._generate_tokens(updated_user)

            # 构建响应
            response = {
                "user_id": updated_user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": int(self._token_expiry.total_seconds()),
                "is_guest": False,
                "user_info": {
                    "nickname": updated_user.nickname,
                    "avatar": getattr(updated_user, 'avatar', None),
                    "phone": getattr(updated_user, 'phone', None),
                    "email": getattr(updated_user, 'email', None),
                    "wechat_openid": getattr(updated_user, 'wechat_openid', None),
                    "points": updated_user.points,
                    "fragments": updated_user.fragments
                }
            }

            self._log_info("游客账号升级成功", {
                "user_id": updated_user.id,
                "upgrade_type": upgrade_type
            })

            return response

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "upgrade_guest_account", {
                "guest_user_id": guest_user_id,
                "upgrade_type": upgrade_type
            })

    # ==================== 用户登录 ====================

    def login(
        self,
        login_type: str,
        **login_data
    ) -> Dict[str, Any]:
        """
        用户登录

        支持多种登录方式：手机号密码、手机号验证码、邮箱密码、邮箱验证码、微信等。
        登录成功后返回访问令牌和用户信息。

        Args:
            login_type: 登录类型
            **login_data: 登录数据，根据类型不同而不同

        Returns:
            包含用户信息和令牌的字典

        Raises:
            ValidationException: 当登录数据无效时
            AuthenticationException: 当认证失败时
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("开始用户登录", {
                "login_type": login_type
            })

            # 验证登录类型
            if login_type not in ["phone_password", "phone_sms", "email_password", "email_code", "wechat"]:
                raise ValidationException(
                    message="不支持的登录类型",
                    details={"login_type": login_type}
                )

            # 根据登录类型执行认证逻辑
            user = None
            if login_type == "phone_password":
                user = self._login_by_phone_password(**login_data)
            elif login_type == "phone_sms":
                user = self._login_by_phone_sms(**login_data)
            elif login_type == "email_password":
                user = self._login_by_email_password(**login_data)
            elif login_type == "email_code":
                user = self._login_by_email_code(**login_data)
            elif login_type == "wechat":
                user = self._login_by_wechat(**login_data)

            if not user:
                raise AuthenticationException(
                    reason="用户认证失败",
                    user_identifier=login_data.get("phone") or login_data.get("email") or login_data.get("wechat_openid")
                )

            # 检查用户状态
            if not user.is_active:
                raise AuthenticationException(
                    reason="账号已被禁用",
                    user_identifier=user.id
                )

            # 生成令牌
            access_token, refresh_token = self._generate_tokens(user)

            # 构建响应
            response = {
                "user_id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": int(self._token_expiry.total_seconds()),
                "is_guest": user.is_guest,
                "user_info": {
                    "nickname": user.nickname,
                    "avatar": getattr(user, 'avatar', None),
                    "phone": getattr(user, 'phone', None),
                    "email": getattr(user, 'email', None),
                    "wechat_openid": getattr(user, 'wechat_openid', None),
                    "points": user.points,
                    "fragments": user.fragments
                }
            }

            self._log_info("用户登录成功", {
                "user_id": user.id,
                "login_type": login_type
            })

            return response

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "login", {
                "login_type": login_type
            })

    # ==================== 令牌管理 ====================

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        刷新访问令牌

        使用刷新令牌获取新的访问令牌和刷新令牌。
        刷新令牌验证通过后会失效，需要使用新的刷新令牌。

        Args:
            refresh_token: 刷新令牌

        Returns:
            包含新令牌的字典

        Raises:
            AuthenticationException: 当刷新令牌无效时
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("开始刷新令牌")

            # 验证刷新令牌并获取用户信息
            user_id = self._validate_refresh_token(refresh_token)

            # 获取用户信息
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 检查用户状态
            if not user.is_active:
                raise AuthenticationException(
                    reason="账号已被禁用，无法刷新令牌",
                    user_identifier=user_id
                )

            # 生成新的令牌
            new_access_token, new_refresh_token = self._generate_tokens(user)

            response = {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": int(self._token_expiry.total_seconds())
            }

            self._log_info("令牌刷新成功", {
                "user_id": user_id
            })

            return response

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "refresh_token")

    def logout(self, user_id: str, access_token: str) -> Dict[str, Any]:
        """
        用户登出

        将访问令牌和刷新令牌标记为失效，清理用户会话。

        Args:
            user_id: 用户ID
            access_token: 访问令牌

        Returns:
            登出结果

        Raises:
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("开始用户登出", {
                "user_id": user_id
            })

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # TODO: 实现令牌黑名单机制
            # 这里应该将令牌添加到黑名单中，防止令牌继续使用
            # 目前简单返回成功，实际项目中需要实现令牌失效机制

            response = {
                "success": True,
                "message": "登出成功"
            }

            self._log_info("用户登出成功", {
                "user_id": user_id
            })

            return response

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "logout", {
                "user_id": user_id
            })

    # ==================== 短信验证码 ====================

    async def send_sms_code(self, phone: str, sms_type: str) -> Dict[str, Any]:
        """
        发送短信验证码

        向指定手机号发送验证码，支持登录、注册、找回密码等场景。
        实现发送频率限制和验证码有效期控制。

        Args:
            phone: 手机号
            sms_type: 短信类型（login/register/reset_password）

        Returns:
            发送结果和冷却时间信息

        Raises:
            ValidationException: 当手机号格式错误时
            BusinessException: 当发送频率过高时
        """
        try:
            self._log_info("开始发送短信验证码", {
                "phone": phone,
                "sms_type": sms_type
            })

            # 验证手机号格式
            if not self._validate_phone_format(phone):
                raise ValidationException(
                    message="手机号格式错误",
                    details={"phone": phone}
                )

            # 验证短信类型
            if sms_type not in ["login", "register", "reset_password"]:
                raise ValidationException(
                    message="不支持的短信类型",
                    details={"sms_type": sms_type}
                )

            # 检查发送频率限制
            cooldown_info = await self._check_sms_cooldown(phone)
            if cooldown_info["in_cooldown"]:
                raise BusinessException(
                    error_code="SERVICE_SMS_COOLDOWN",
                    message="短信发送过于频繁，请稍后再试",
                    user_message="发送过于频繁，请稍后再试",
                    details=cooldown_info
                )

            # 检查手机号是否已存在（注册时需要检查）
            if sms_type == "register" and self.get_user_repository().phone_exists(phone):
                raise DuplicateResourceException(
                    resource_type="User",
                    conflict_field="phone",
                    conflict_value=phone,
                    user_message="该手机号已被注册"
                )

            # 检查手机号是否存在（登录时需要检查）
            if sms_type == "login" and not self.get_user_repository().phone_exists(phone):
                raise ResourceNotFoundException(
                    resource_type="User",
                    user_message="该手机号未注册，请先注册"
                )

            # 生成验证码
            sms_code = self._generate_sms_code()

            # TODO: 实际发送短信（这里需要集成短信服务）
            # self._send_sms_service(phone, sms_code, sms_type)

            # 模拟发送成功
            send_success = True

            if send_success:
                # 记录发送信息（用于验证和频率控制）
                await self._record_sms_sent(phone, sms_code, sms_type)

                response = {
                    "success": True,
                    "message": "验证码发送成功",
                    "cooldown_seconds": int(self._sms_cooldown.total_seconds()),
                    "next_send_time": (datetime.now() + self._sms_cooldown).isoformat()
                }

                self._log_info("短信验证码发送成功", {
                    "phone": phone,
                    "sms_type": sms_type
                })

                return response
            else:
                raise BusinessException(
                    error_code="SERVICE_SMS_SEND_FAILED",
                    message="短信发送失败",
                    user_message="验证码发送失败，请稍后重试"
                )

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "send_sms_code", {
                "phone": phone,
                "sms_type": sms_type
            })

    # ==================== 用户信息获取 ====================

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        获取当前用户信息

        根据用户ID获取用户详细信息，包括基本资料、积分、碎片等。

        Args:
            user_id: 用户ID

        Returns:
            用户详细信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("获取用户信息", {
                "user_id": user_id
            })

            # 获取用户信息
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 过滤敏感信息
            user_info = self._filter_sensitive_data({
                "id": user.id,
                "nickname": user.nickname,
                "avatar": getattr(user, 'avatar', None),
                "user_type": "guest" if user.is_guest else "registered",
                "is_active": user.is_active,
                "phone": getattr(user, 'phone', None),
                "email": getattr(user, 'email', None),
                "wechat_openid": getattr(user, 'wechat_openid', None),
                "points": user.points,
                "fragments": user.fragments,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            })

            self._log_info("用户信息获取成功", {
                "user_id": user_id
            })

            return {"user_info": user_info}

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_user_info", {
                "user_id": user_id
            })

    # ==================== 私有方法 ====================

    def _generate_tokens(self, user: User) -> Tuple[str, str]:
        """
        生成访问令牌和刷新令牌

        Args:
            user: 用户对象

        Returns:
            (access_token, refresh_token) 元组
        """
        # TODO: 实现JWT令牌生成
        # 这里需要集成JWT库，实际生成有效的令牌
        # 目前返回模拟令牌

        access_token = f"access_{uuid.uuid4().hex}_{user.id}"
        refresh_token = f"refresh_{uuid.uuid4().hex}_{user.id}"

        # TODO: 存储令牌信息（用于验证和黑名单）

        return access_token, refresh_token

    def _validate_refresh_token(self, refresh_token: str) -> str:
        """
        验证刷新令牌并返回用户ID

        Args:
            refresh_token: 刷新令牌

        Returns:
            用户ID

        Raises:
            AuthenticationException: 当刷新令牌无效时
        """
        # TODO: 实现刷新令牌验证逻辑
        # 这里需要验证令牌签名、有效期等
        # 目前简单解析令牌获取用户ID

        if not refresh_token.startswith("refresh_"):
            raise AuthenticationException(
                reason="无效的刷新令牌格式"
            )

        # 模拟解析用户ID
        try:
            parts = refresh_token.split("_")
            if len(parts) < 3:
                raise AuthenticationException(
                    reason="刷新令牌格式错误"
                )
            user_id = parts[-1]
            return user_id
        except Exception:
            raise AuthenticationException(
                reason="刷新令牌解析失败"
            )

    def _upgrade_by_phone(self, guest_user: User, phone: str, password: str, sms_code: str, **kwargs) -> None:
        """
        通过手机号升级游客账号

        Args:
            guest_user: 游客用户对象
            phone: 手机号
            password: 密码
            sms_code: 短信验证码
            **kwargs: 其他参数
        """
        # 验证手机号格式
        if not self._validate_phone_format(phone):
            raise ValidationException(
                message="手机号格式错误",
                details={"phone": phone}
            )

        # 验证密码强度
        if not self._validate_password_strength(password):
            raise ValidationException(
                message="密码强度不足",
                details={"password_requirements": "至少8位，包含字母和数字"}
            )

        # 检查手机号是否已存在
        if self.get_user_repository().phone_exists(phone):
            raise DuplicateResourceException(
                resource_type="User",
                conflict_field="phone",
                conflict_value=phone,
                user_message="该手机号已被使用"
            )

        # 验证短信验证码
        self._validate_sms_code(phone, sms_code)

        # 加密密码
        password_hash = self._hash_password(password)

        # 更新用户信息
        update_data = {
            "phone": phone,
            "password_hash": password_hash
        }
        self.get_user_repository().update(guest_user.id, update_data)

    def _upgrade_by_email(self, guest_user: User, email: str, email_code: str, **kwargs) -> None:
        """
        通过邮箱升级游客账号

        Args:
            guest_user: 游客用户对象
            email: 邮箱地址
            email_code: 邮箱验证码
            **kwargs: 其他参数
        """
        # 验证邮箱格式
        if not self._validate_email_format(email):
            raise ValidationException(
                message="邮箱格式错误",
                details={"email": email}
            )

        # 检查邮箱是否已存在
        if self.get_user_repository().email_exists(email):
            raise DuplicateResourceException(
                resource_type="User",
                conflict_field="email",
                conflict_value=email,
                user_message="该邮箱已被使用"
            )

        # 验证邮箱验证码
        self._validate_email_code(email, email_code)

        # 更新用户信息
        update_data = {
            "email": email
        }
        self.get_user_repository().update(guest_user.id, update_data)

    def _upgrade_by_wechat(self, guest_user: User, wechat_openid: str, **kwargs) -> None:
        """
        通过微信升级游客账号

        Args:
            guest_user: 游客用户对象
            wechat_openid: 微信OpenID
            **kwargs: 其他参数
        """
        # 检查微信OpenID是否已存在
        existing_user = self.get_user_repository().find_by_wechat_openid(wechat_openid)
        if existing_user:
            raise DuplicateResourceException(
                resource_type="User",
                conflict_field="wechat_openid",
                conflict_value=wechat_openid,
                user_message="该微信账号已被绑定"
            )

        # 更新用户信息
        update_data = {
            "wechat_openid": wechat_openid
        }
        self.get_user_repository().update(guest_user.id, update_data)

    def _login_by_phone_password(self, phone: str, password: str, **kwargs) -> Optional[User]:
        """手机号密码登录"""
        user = self.get_user_repository().find_by_phone(phone)
        if not user:
            raise AuthenticationException(
                reason="用户不存在",
                user_identifier=phone
            )

        # 验证密码
        if not self._verify_password(password, getattr(user, 'password_hash', '')):
            raise AuthenticationException(
                reason="密码错误",
                user_identifier=phone
            )

        return user

    def _login_by_phone_sms(self, phone: str, sms_code: str, **kwargs) -> Optional[User]:
        """手机号验证码登录"""
        user = self.get_user_repository().find_by_phone(phone)
        if not user:
            raise AuthenticationException(
                reason="用户不存在",
                user_identifier=phone
            )

        # 验证短信验证码
        self._validate_sms_code(phone, sms_code)

        return user

    def _login_by_email_password(self, email: str, password: str, **kwargs) -> Optional[User]:
        """邮箱密码登录"""
        user = self.get_user_repository().find_by_email(email)
        if not user:
            raise AuthenticationException(
                reason="用户不存在",
                user_identifier=email
            )

        # 验证密码
        if not self._verify_password(password, getattr(user, 'password_hash', '')):
            raise AuthenticationException(
                reason="密码错误",
                user_identifier=email
            )

        return user

    def _login_by_email_code(self, email: str, email_code: str, **kwargs) -> Optional[User]:
        """邮箱验证码登录"""
        user = self.get_user_repository().find_by_email(email)
        if not user:
            raise AuthenticationException(
                reason="用户不存在",
                user_identifier=email
            )

        # 验证邮箱验证码
        self._validate_email_code(email, email_code)

        return user

    def _login_by_wechat(self, wechat_openid: str, **kwargs) -> Optional[User]:
        """微信登录"""
        user = self.get_user_repository().find_by_wechat_openid(wechat_openid)
        if not user:
            # 微信自动注册逻辑
            return self._auto_register_wechat_user(wechat_openid, **kwargs)

        return user

    def _auto_register_wechat_user(self, wechat_openid: str, **kwargs) -> User:
        """
        微信自动注册用户

        Args:
            wechat_openid: 微信OpenID
            **kwargs: 其他用户信息

        Returns:
            新创建的用户对象
        """
        user_data = {
            "id": str(uuid.uuid4()),
            "wechat_openid": wechat_openid,
            "nickname": kwargs.get("nickname", f"微信用户{datetime.now().strftime('%m%d%H%M')}"),
            "avatar": kwargs.get("avatar"),
            "is_guest": False,
            "is_active": True,
            "points": 100,  # 新用户注册赠送积分
            "fragments": 10,  # 新用户注册赠送碎片
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        return self.get_user_repository().create(user_data)

    # ==================== 工具方法 ====================

    def _validate_phone_format(self, phone: str) -> bool:
        """验证手机号格式"""
        import re
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))

    def _validate_email_format(self, email: str) -> bool:
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _validate_password_strength(self, password: str) -> bool:
        """验证密码强度"""
        if len(password) < 8:
            return False

        has_letter = bool(re.search(r'[a-zA-Z]', password))
        has_digit = bool(re.search(r'\d', password))

        return has_letter and has_digit

    def _hash_password(self, password: str) -> str:
        """密码加密"""
        # 使用SHA-256加盐加密
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        if not password_hash or ":" not in password_hash:
            return False

        salt, hash_value = password_hash.split(":", 1)
        computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return computed_hash == hash_value

    def _generate_sms_code(self) -> str:
        """生成短信验证码"""
        return str(secrets.randbelow(900000) + 100000)  # 6位数字验证码

    def _validate_sms_code(self, phone: str, sms_code: str) -> None:
        """验证短信验证码"""
        # TODO: 实现短信验证码验证逻辑
        # 这里需要从缓存或数据库中获取存储的验证码进行比对
        # 目前简单验证格式
        if not sms_code.isdigit() or len(sms_code) != 6:
            raise AuthenticationException(
                reason="短信验证码格式错误"
            )

    def _validate_email_code(self, email: str, email_code: str) -> None:
        """验证邮箱验证码"""
        # TODO: 实现邮箱验证码验证逻辑
        if not email_code or len(email_code) < 4:
            raise AuthenticationException(
                reason="邮箱验证码格式错误"
            )

    async def _check_sms_cooldown(self, phone: str) -> Dict[str, Any]:
        """
        检查短信发送冷却时间

        使用数据库查询最近的短信发送记录，实现发送频率限制。

        Args:
            phone: 手机号

        Returns:
            冷却时间信息字典
        """
        try:
            # 检查最近发送的验证码记录
            recent_record = await self._sms_verification_repo.get_latest_by_phone(
                phone_number=phone,
                within_minutes=int(self._sms_cooldown.total_seconds() / 60)
            )

            if recent_record:
                # 计算距离上次发送的时间
                now = datetime.now(timezone.utc)
                time_since_last_send = now - recent_record.created_at
                remaining_cooldown = self._sms_cooldown - time_since_last_send

                if remaining_cooldown.total_seconds() > 0:
                    # 仍在冷却期内
                    return {
                        "in_cooldown": True,
                        "cooldown_seconds": int(remaining_cooldown.total_seconds()),
                        "next_send_time": (datetime.now() + remaining_cooldown).isoformat(),
                        "last_send_time": recent_record.created_at.isoformat()
                    }

            # 不在冷却期内
            return {
                "in_cooldown": False,
                "cooldown_seconds": 0,
                "next_send_time": None
            }

        except Exception as e:
            # 数据库查询失败时，为了安全起见，假设在冷却期内
            self._log_error("检查短信冷却时间失败", {
                "phone": phone,
                "error": str(e)
            })
            return {
                "in_cooldown": True,
                "cooldown_seconds": int(self._sms_cooldown.total_seconds()),
                "next_send_time": (datetime.now(timezone.utc) + self._sms_cooldown).isoformat(),
                "error": "查询失败，请稍后重试"
            }

    async def _record_sms_sent(self, phone: str, sms_code: str, sms_type: str) -> None:
        """
        记录短信发送信息

        将验证码信息存储到数据库中，用于后续验证和发送频率控制。

        Args:
            phone: 手机号
            sms_code: 验证码
            sms_type: 短信类型
        """
        try:
            # 创建验证码记录
            verification_data = {
                'phone_number': phone,
                'code': sms_code,
                'verification_type': sms_type,
                'expires_at': datetime.now(timezone.utc) + self._sms_code_expiry,
                'ip_address': None,  # TODO: 从请求上下文获取IP地址
                'user_agent': None   # TODO: 从请求上下文获取User Agent
            }

            await self._sms_verification_repo.create_verification_record(verification_data)

            self._log_info("短信验证码记录创建成功", {
                "phone": phone,
                "sms_type": sms_type,
                "expires_at": verification_data['expires_at'].isoformat()
            })

        except Exception as e:
            # 记录失败不应该影响发送成功，但需要记录错误
            self._log_error("短信验证码记录创建失败", {
                "phone": phone,
                "sms_type": sms_type,
                "error": str(e)
            })
            # 不抛出异常，因为短信已经发送成功