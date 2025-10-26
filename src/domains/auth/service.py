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
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from jose import JWTError, jwt

from .database import get_auth_db
from .repository import AuthRepository, AuditRepository
from .models import Auth, SMSVerification
from .sms_client import get_sms_client
from .exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    ValidationError,
    RateLimitException,
    DailyLimitException,
    AccountLockedException,
    VerificationNotFoundException,
    VerificationExpiredException,
    InvalidVerificationCodeException,
    PhoneNotFoundException,
    PhoneAlreadyExistsException,
    PhoneAlreadyBoundException,
)
from .schemas import (
    # 请求模型
    GuestInitRequest,
    WeChatRegisterRequest,
    WeChatLoginRequest,
    GuestUpgradeRequest,
    TokenRefreshRequest,
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
            "jti": str(uuid4()),  # JWT ID
        }

        # 刷新令牌载荷
        refresh_payload = {
            "sub": str(user_data["user_id"]),
            "is_guest": user_data.get("is_guest", False),
            "jwt_version": user_data.get("jwt_version", 1),
            "token_type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days),
            "jti": str(uuid4()),  # JWT ID
        }

        # 生成令牌
        access_token = jwt.encode(
            access_payload, self.secret_key, algorithm=self.algorithm
        )
        refresh_token = jwt.encode(
            refresh_payload, self.secret_key, algorithm=self.algorithm
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,  # 秒
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
                raise TokenException(
                    f"令牌类型不匹配，期望: {expected_type}", "TOKEN_TYPE_MISMATCH"
                )

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

    def __init__(self, db=None):
        """
        初始化认证服务

        Args:
            db: 可选的数据库session。如果提供，使用该session创建repository；
                 如果为None，则不创建repository实例，需要在使用时动态创建。

        Note:
            当db为None时，service将不包含repository实例，
            这是为依赖注入模式设计的，确保session管理在调用方控制。
        """
        self.jwt_service = JWTService()
        self.sms_client = get_sms_client()
        self._db = db  # 保存数据库session引用

        # 只有提供了数据库session时才初始化Repository
        if db:
            self.repository = AuthRepository(db)
            self.audit_repository = AuditRepository(db)
        else:
            # 不创建repository，使用时通过with语句动态创建
            self.repository = None
            self.audit_repository = None

    def _ensure_repositories(self):
        """
        确保repository实例存在

        Raises:
            RuntimeError: 当没有数据库session且无法创建repository时
        """
        if self.repository is None:
            raise RuntimeError(
                "AuthService没有初始化repository。请通过依赖注入创建实例："
                "AuthService = Depends(get_auth_service_with_db)"
            )

    def init_guest_account(
        self, request: GuestInitRequest, ip_address: str = None, user_agent: str = None
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
                guest = auth_repo.create_user(is_guest=True, wechat_openid=None)

                # 生成JWT令牌
                user_data = {
                    "user_id": str(guest.id),
                    "is_guest": True,
                    "jwt_version": guest.jwt_version,
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=guest.id,
                    action="guest_init",
                    result="success",
                    details="游客账号初始化成功",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return {"user_id": str(guest.id), "is_guest": True, **tokens}

        except Exception as e:
            raise AuthenticationException(f"游客账号初始化失败: {str(e)}")

    def wechat_register(
        self,
        request: WeChatRegisterRequest,
        ip_address: str = None,
        user_agent: str = None,
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
                guest = auth_repo.create_user(is_guest=True, wechat_openid=None)

                # 3. 立即升级为正式用户
                user = auth_repo.upgrade_guest_account(
                    user_id=UUID(guest.id),  # 转换字符串为UUID对象
                    wechat_openid=request.wechat_openid,
                )

                # 4. 生成JWT令牌
                user_data = {
                    "user_id": str(user.id),
                    "is_guest": False,
                    "jwt_version": user.jwt_version,
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 5. 记录审计日志
                audit_repo.create_log(
                    user_id=user.id,
                    action="register",
                    result="success",
                    details=f"微信注册成功，openid: {request.wechat_openid}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return {"user_id": str(user.id), "is_guest": False, **tokens}

        except ValidationError:
            raise  # 重新抛出验证错误
        except Exception as e:
            raise AuthenticationException(f"微信注册失败: {str(e)}")

    def wechat_login(
        self,
        request: WeChatLoginRequest,
        ip_address: str = None,
        user_agent: str = None,
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
                auth_repo.update_last_login(UUID(user.id))  # 转换字符串为UUID对象

                # 生成JWT令牌
                user_data = {
                    "user_id": str(user.id),
                    "is_guest": user.is_guest,
                    "jwt_version": user.jwt_version,
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=user.id,
                    action="login",
                    result="success",
                    details=f"微信登录成功，openid: {request.wechat_openid}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return {"user_id": str(user.id), "is_guest": user.is_guest, **tokens}

        except (ValidationError, UserNotFoundException):
            raise  # 重新抛出验证错误
        except Exception as e:
            raise AuthenticationException(f"微信登录失败: {str(e)}")

    def upgrade_guest_account(
        self,
        request: GuestUpgradeRequest,
        current_user_id: UUID,
        ip_address: str = None,
        user_agent: str = None,
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
                    user_id=current_user_id, wechat_openid=request.wechat_openid
                )

                # 生成新的JWT令牌
                user_data = {
                    "user_id": str(updated_user.id),
                    "is_guest": False,
                    "jwt_version": updated_user.jwt_version,
                }
                tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=updated_user.id,
                    action="upgrade",
                    result="success",
                    details=f"游客升级成功，openid: {request.wechat_openid}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return {"user_id": str(updated_user.id), "is_guest": False, **tokens}

        except ValidationError:
            raise  # 重新抛出验证错误
        except Exception as e:
            raise AuthenticationException(f"游客升级失败: {str(e)}")

    def refresh_token(
        self,
        request: TokenRefreshRequest,
        ip_address: str = None,
        user_agent: str = None,
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
            token_payload = self.jwt_service.verify_token(
                request.refresh_token, "refresh"
            )
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
                    "jwt_version": user.jwt_version,
                }
                new_tokens = self.jwt_service.generate_tokens(user_data)

                # 记录审计日志
                audit_repo.create_log(
                    user_id=user.id,
                    action="token_refresh",
                    result="success",
                    details="令牌刷新成功",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return {
                    "user_id": str(user.id),
                    "is_guest": user.is_guest,
                    **new_tokens,
                }

        except (ValidationError, TokenException, UserNotFoundException):
            raise  # 重新抛出验证错误
        except Exception as e:
            raise TokenException(f"令牌刷新失败: {str(e)}", "TOKEN_REFRESH_FAILED")

    # ===== SMS认证相关方法 =====

    async def send_sms_code(
        self,
        phone: str,
        scene: str,
        ip_address: str,
        user_wechat_openid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发送短信验证码

        Args:
            phone: 手机号
            scene: 使用场景 (register/login/bind)
            ip_address: 请求IP地址
            user_wechat_openid: 用户微信OpenID（bind场景需要）

        Returns:
            Dict: {
                "success": bool,
                "expires_in": int,  # 验证码有效期（秒）
                "retry_after": int   # 重试间隔（秒）
            }

        Raises:
            ValidationError: 手机号格式错误
            PhoneAlreadyExistsException: 注册时手机号已存在
            PhoneNotFoundException: 登录时手机号不存在
            PhoneAlreadyBoundException: 绑定时手机号已被其他账号绑定
            RateLimitException: 发送频率限制
            DailyLimitException: 每日发送次数限制
            AccountLockedException: 账号锁定
        """
        # 确保repository已初始化
        self._ensure_repositories()

        try:
            # 1. 手机号格式验证
            if not self._validate_phone_format(phone):
                raise ValidationError("手机号格式错误")

            # 2. 检查手机号状态
            self._check_phone_status(phone, scene, user_wechat_openid)

            # 3. 限流检查
            self._check_rate_limits(phone)

            # 4. 生成验证码
            code = self.generate_code()

            # 5. 发送短信
            sms_result = await self.sms_client.send_code(phone, code)
            if not sms_result.get("success"):
                raise AuthenticationException("短信发送失败")

            # 6. 保存验证码记录
            verification = SMSVerification(
                phone=phone, code=code, scene=scene, ip_address=ip_address
            )
            self.repository.create_sms_verification(verification)

            # 7. 记录审计日志
            self.audit_repository.create_log(
                action="sms_send",
                user_id=None,
                result="success",
                details=f"发送短信验证码到{phone}，场景：{scene}",
                ip_address=ip_address,
            )

            return {
                "success": True,
                "expires_in": 300,  # 5分钟
                "retry_after": 60,  # 60秒限流
            }

        except Exception as e:
            # 记录失败日志
            self.audit_repository.create_log(
                action="sms_send",
                user_id=None,
                result="failure",
                details=f"发送短信失败：{str(e)}",
                ip_address=ip_address,
                error_code=getattr(e, "error_code", None),
            )
            raise

    def verify_sms_code(
        self,
        phone: str,
        code: str,
        scene: str,
        user_wechat_openid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        验证短信验证码

        Args:
            phone: 手机号
            code: 验证码
            scene: 使用场景 (register/login/bind)
            user_wechat_openid: 用户微信OpenID（bind场景需要）

        Returns:
            Dict: {
                "success": bool,
                "access_token": str,
                "refresh_token": str,
                "user_id": str,
                "is_new_user": bool,
                "upgraded": bool  # 仅bind场景
            }

        Raises:
            VerificationNotFoundException: 验证码不存在
            VerificationExpiredException: 验证码过期
            InvalidVerificationCodeException: 验证码错误
            AccountLockedException: 账号锁定
        """
        # 确保repository已初始化
        self._ensure_repositories()

        try:
            # 1. 获取最新的未验证验证码
            verification = self.repository.get_latest_unverified(phone, scene)
            if not verification:
                raise VerificationNotFoundException("验证码不存在")

            # 2. 检查验证码过期
            if self.is_code_expired(verification):
                raise VerificationExpiredException("验证码已过期")

            # 3. 验证码匹配验证
            if verification.code != code:
                self._handle_verification_error(verification)
                raise InvalidVerificationCodeException("验证码错误")

            # 4. 标记验证码已使用
            verification.verified = True
            verification.verified_at = datetime.now(timezone.utc)
            self.repository.update_verification(verification)

            # 5. 根据场景处理业务逻辑
            if scene == "register":
                return self._handle_register(phone, verification)
            elif scene == "login":
                return self._handle_login(phone, verification)
            elif scene == "bind":
                return self._handle_bind(phone, verification, user_wechat_openid)
            else:
                raise ValidationError("不支持的验证场景", "INVALID_SCENE")

        except Exception as e:
            # 记录失败日志
            self.audit_repository.create_log(
                action="sms_verify",
                user_id=None,
                result="failure",
                details=f"验证码验证失败：{str(e)}",
                error_code=getattr(e, "error_code", None),
            )
            raise

    # ===== 辅助方法 =====

    def _validate_phone_format(self, phone: str) -> bool:
        """验证手机号格式"""
        # 中国大陆手机号格式：11位数字，以1开头
        pattern = r"^1[3-9]\d{9}$"
        return bool(re.match(pattern, phone))

    def _check_phone_status(
        self, phone: str, scene: str, user_wechat_openid: Optional[str]
    ):
        """检查手机号状态"""
        existing_user = self.repository.get_auth_by_phone(phone)

        if scene == "register":
            # 注册场景：手机号不能存在
            if existing_user:
                raise PhoneAlreadyExistsException(
                    "手机号已注册", "PHONE_ALREADY_EXISTS"
                )
        elif scene == "login":
            # 登录场景：手机号必须存在
            if not existing_user:
                raise PhoneNotFoundException("手机号未注册", "PHONE_NOT_FOUND")
        elif scene == "bind":
            # 绑定场景：检查是否被其他账号绑定
            if existing_user and existing_user.wechat_openid != user_wechat_openid:
                raise PhoneAlreadyBoundException("手机号已绑定", "PHONE_ALREADY_BOUND")

    def _check_rate_limits(self, phone: str):
        """检查发送频率限制"""
        # 检查60秒频率限制
        latest_verification = self.repository.get_latest_verification(phone)
        if latest_verification and self._check_rate_limit(latest_verification):
            raise RateLimitException("发送过于频繁，请60秒后重试")

        # 检查每日次数限制
        today_count = self.repository.count_today_sends(phone)
        if self._check_daily_limit(today_count):
            raise DailyLimitException("今日发送次数已达上限")

        # 检查账号锁定
        if latest_verification and latest_verification.locked_until:
            if datetime.now(timezone.utc) < latest_verification.locked_until:
                raise AccountLockedException("账号已锁定，请稍后再试")

    def _check_rate_limit(self, verification: SMSVerification) -> bool:
        """检查60秒频率限制"""
        now = datetime.now(timezone.utc)

        # 确保created_at是时区感知的
        if verification.created_at.tzinfo is None:
            created_at = verification.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = verification.created_at

        time_diff = (now - created_at).total_seconds()
        return time_diff < 60  # 60秒内不能重复发送

    def _check_daily_limit(self, count: int) -> bool:
        """检查每日次数限制"""
        return count >= 5  # 每日最多5次

    def _handle_verification_error(self, verification: SMSVerification):
        """处理验证码错误"""
        verification.error_count += 1

        # 5次错误后锁定账号1小时
        if verification.error_count >= 5:
            verification.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)

        self.repository.update_verification(verification)

    def _handle_register(
        self, phone: str, verification: SMSVerification
    ) -> Dict[str, Any]:
        """处理注册场景"""
        # 创建新用户
        created_user = self.repository.create_user(
            user_id=None, wechat_openid=None, is_guest=False
        )

        # 手动设置手机号（因为create_user不支持phone参数）
        created_user.phone = phone
        self._db.commit()

        # 生成JWT令牌
        user_data = {
            "user_id": str(created_user.id),
            "is_guest": False,
            "jwt_version": getattr(created_user, 'jwt_version', 1),
        }
        tokens = self.jwt_service.generate_tokens(user_data)

        # 记录审计日志
        self.audit_repository.create_log(
            action="phone_register",
            user_id=str(created_user.id),
            result="success",
            details="手机号注册成功",
            ip_address=verification.ip_address,
        )

        return {
            "success": True,
            "is_new_user": True,
            "user_id": str(created_user.id),
            **tokens,
        }

    def _handle_login(
        self, phone: str, verification: SMSVerification
    ) -> Dict[str, Any]:
        """处理登录场景"""
        # 获取用户
        user = self.repository.get_auth_by_phone(phone)
        if not user:
            raise PhoneNotFoundException("手机号未注册", "PHONE_NOT_FOUND")

        # 更新最后登录时间
        self.repository.update_last_login(user.id)

        # 生成JWT令牌
        tokens = self.jwt_service.generate_tokens(user.id)

        # 记录审计日志
        self.audit_repository.create_log(
            action="phone_login",
            user_id=str(user.id),
            result="success",
            details="手机号登录成功",
            ip_address=verification.ip_address,
        )

        return {
            "success": True,
            "is_new_user": False,
            "user_id": str(user.id),
            **tokens,
        }

    def _handle_bind(
        self, phone: str, verification: SMSVerification, user_wechat_openid: str
    ) -> Dict[str, Any]:
        """处理绑定场景"""
        if not user_wechat_openid:
            raise ValidationError("绑定场景需要提供微信OpenID", "MISSING_WECHAT_OPENID")

        # 获取微信用户
        user = self.repository.get_by_wechat_openid(user_wechat_openid)
        if not user:
            raise UserNotFoundException("微信用户不存在", "USER_NOT_FOUND")

        # 更新用户手机号
        user.phone = phone
        updated_user = self.repository.update_user(user.id, phone=phone)

        # 生成JWT令牌
        tokens = self.jwt_service.generate_tokens(updated_user.id)

        # 记录审计日志
        self.audit_repository.create_log(
            action="phone_bind",
            user_id=str(updated_user.id),
            result="success",
            details="手机号绑定成功",
            ip_address=verification.ip_address,
        )

        return {
            "success": True,
            "upgraded": True,
            "user_id": str(updated_user.id),
            **tokens,
        }

    def generate_code(self, length: int = 6) -> str:
        """生成验证码"""
        return "".join(random.choices("0123456789", k=length))

    def is_code_expired(self, verification: SMSVerification) -> bool:
        """检查验证码是否过期"""
        now = datetime.now(timezone.utc)

        # 确保created_at是时区感知的
        if verification.created_at.tzinfo is None:
            # 如果是时区无关的，假设它是UTC时间
            created_at = verification.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = verification.created_at

        time_diff = (now - created_at).total_seconds()
        return time_diff > 300  # 5分钟过期


# ===== 删除的服务注释 =====
# 以下服务已被删除，原因：
# - SMSService: 移除短信验证功能
# - UserService: 用户管理移至独立user领域
# - 会话管理相关服务: 采用无状态JWT设计
