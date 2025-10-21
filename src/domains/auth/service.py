"""
认证领域服务层

提供认证相关的业务逻辑处理和规则验证。
Service层是业务逻辑的核心，协调多个Repository完成复杂的业务操作。

主要服务:
- AuthService: 核心认证服务
- JWTService: JWT令牌管理服务
- SMSService: 短信验证码服务
- UserService: 用户管理服务

设计原则:
1. 业务逻辑封装: 将复杂的业务规则封装在Service层
2. 事务管理: 跨Repository的事务协调
3. 验证规则: 业务数据的验证和约束检查
4. 异常处理: 统一的业务异常处理
5. 依赖注入: 通过构造函数注入Repository依赖
"""

import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

import bcrypt
from jose import JWTError, jwt

from .database import get_auth_db
from .repository import (
    AuthRepository, SMSRepository, TokenRepository,
    SessionRepository, AuditRepository
)
from .models import User, SMSVerification, TokenBlacklist
from .exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    SMSException,
    ValidationError
)
from .schemas import (
    GuestInitRequest, GuestUpgradeRequest, LoginRequest,
    SMSCodeRequest, TokenRefreshRequest, DeviceInfo
)


class JWTService:
    """JWT令牌管理服务"""

    def __init__(self, secret_key: str, access_token_expire_minutes: int = 30, refresh_token_expire_days: int = 7):
        self.secret_key = secret_key
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.algorithm = "HS256"

    def generate_tokens(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成访问令牌和刷新令牌"""
        now = datetime.now(timezone.utc)

        # 访问令牌载荷
        access_payload = {
            "sub": str(user_data["user_id"]),
            "user_type": user_data.get("user_type", "registered"),
            "is_guest": user_data.get("is_guest", False),
            "jwt_version": user_data.get("jwt_version", 1),
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes),
            "jti": str(uuid4())  # JWT ID，用于黑名单管理
        }

        # 刷新令牌载荷
        refresh_payload = {
            "sub": str(user_data["user_id"]),
            "user_type": user_data.get("user_type", "registered"),
            "is_guest": user_data.get("is_guest", False),
            "jwt_version": user_data.get("jwt_version", 1),
            "token_type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days),
            "jti": str(uuid4())  # JWT ID，用于黑名单管理
        }

        # 生成令牌
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,  # 秒
            "access_token_jti": access_payload["jti"],
            "refresh_token_jti": refresh_payload["jti"],
            "access_token_expires_at": access_payload["exp"],
            "refresh_token_expires_at": refresh_payload["exp"]
        }

    def verify_token(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 验证令牌类型
            if payload.get("token_type") != expected_type:
                raise TokenException(f"令牌类型不匹配，期望: {expected_type}")

            # 验证过期时间
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                raise TokenException("令牌已过期")

            return payload

        except JWTError as e:
            raise TokenException(f"令牌验证失败: {str(e)}")

    def get_token_jti(self, token: str) -> str:
        """获取令牌的JTI（JWT ID）"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            return payload.get("jti")
        except JWTError:
            raise TokenException("无法获取令牌ID")


class SMSService:
    """短信验证码服务（Mock实现）"""

    def __init__(self, repository: SMSRepository):
        self.repository = repository
        self.code_length = 6
        self.rate_limit_minutes = 1
        self.expire_minutes = 5
        self.max_attempts = 5

    def generate_code(self) -> str:
        """生成6位数字验证码"""
        return "".join([str(secrets.randbelow(10)) for _ in range(self.code_length)])

    async def send_verification_code(
        self,
        phone: str,
        verification_type: str = "login",
        user_id: Optional[UUID] = None
    ) -> str:
        """发送短信验证码"""
        # 检查发送频率限制
        await self._check_rate_limit(phone, verification_type)

        # 生成验证码
        code = self.generate_code()

        # 保存验证码到数据库
        await self.repository.create_verification_code(
            phone=phone,
            code=code,
            verification_type=verification_type,
            user_id=user_id,
            expire_minutes=self.expire_minutes
        )

        # Mock发送短信（实际项目中应调用真实短信服务）
        self._mock_send_sms(phone, code, verification_type)

        return code

    async def verify_code(
        self,
        phone: str,
        code: str,
        verification_type: str = "login"
    ) -> bool:
        """验证短信验证码"""
        verification = await self.repository.verify_code(phone, code, verification_type)

        if not verification:
            raise SMSException("验证码无效或已过期")

        # 检查尝试次数
        if verification.attempts >= verification.max_attempts:
            raise SMSException("验证码尝试次数过多，请重新获取")

        # 标记验证码为已使用
        await self.repository.mark_code_used(verification.id)

        return True

    async def _check_rate_limit(self, phone: str, verification_type: str) -> None:
        """检查发送频率限制"""
        latest_code = await self.repository.get_latest_code(phone, verification_type)

        if latest_code:
            time_diff = datetime.now(timezone.utc) - latest_code.created_at
            if time_diff < timedelta(minutes=self.rate_limit_minutes):
                remaining_seconds = 60 - time_diff.seconds
                raise SMSException(f"发送过于频繁，请等待 {remaining_seconds} 秒后重试")

    def _mock_send_sms(self, phone: str, code: str, verification_type: str) -> None:
        """Mock发送短信（控制台彩色输出）"""
        import sys

        # 验证类型对应的中文描述
        type_names = {
            "login": "登录",
            "register": "注册",
            "reset_password": "重置密码",
            "bind_phone": "绑定手机",
            "unbind_phone": "解绑手机"
        }

        type_name = type_names.get(verification_type, "验证")

        # 彩色控制台输出
        print("\n" + "="*60)
        print(f"📱 【TaKeKe】{type_name}验证码短信模拟")
        print("="*60)
        print(f"📞 手机号: \033[32m{phone}\033[0m")
        print(f"🔢 验证码: \033[33;1m{code}\033[0m")
        print(f"⏰ 有效期: \033[31m{self.expire_minutes}\033[0m 分钟")
        print(f"📝 用途: \033[36m{type_name}\033[0m")
        print("="*60)
        print("💡 提示: 在实际环境中，这里将调用真实的短信服务API")
        print("="*60 + "\n", flush=True)


class UserService:
    """用户管理服务"""

    def __init__(self, repository: AuthRepository):
        self.repository = repository

    async def create_guest_user(
        self,
        device_id: str,
        device_type: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> User:
        """创建游客用户"""
        # 检查设备是否已存在游客账号
        existing_guest = await self.repository.get_user_by_device(device_id)
        if existing_guest:
            return existing_guest

        # 生成唯一的用户名
        nickname = f"游客_{device_id[-8:]}"

        # 创建游客用户
        guest_user = await self.repository.create_user(
            is_guest=True,
            device_id=device_id,
            device_type=device_type,
            nickname=nickname
        )

        return guest_user

    async def upgrade_guest_account(
        self,
        guest_user_id: UUID,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        username: Optional[str] = None,
        nickname: Optional[str] = None
    ) -> User:
        """升级游客账号为正式用户"""
        # 获取游客用户
        guest_user = await self.repository.get_by_id(User, guest_user_id)
        if not guest_user or not guest_user.is_guest:
            raise ValidationError("无效的游客账号")

        # 验证至少提供一种正式身份信息
        if not phone and not email:
            raise ValidationError("升级账号需要提供手机号或邮箱")

        # 检查手机号或邮箱是否已被使用
        if phone and await self.repository.get_user_by_phone(phone):
            raise ValidationError("手机号已被注册")
        if email and await self.repository.get_user_by_email(email):
            raise ValidationError("邮箱已被注册")

        # 处理密码
        password_hash = None
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 升级账号
        updated_user = await self.repository.upgrade_guest_account(
            user_id=guest_user_id,
            phone=phone,
            email=email,
            password_hash=password_hash,
            username=username,
            nickname=nickname
        )

        return updated_user

    async def authenticate_user(
        self,
        identifier: str,  # 可以是用户名、邮箱或手机号
        password: str
    ) -> Optional[User]:
        """用户身份验证"""
        # 尝试通过不同方式查找用户
        user = None

        # 1. 尝试用户名
        if identifier.isalnum() and not identifier.isdigit():
            user = await self.repository.get_user_by_username(identifier)

        # 2. 尝试邮箱
        if not user and "@" in identifier:
            user = await self.repository.get_user_by_email(identifier)

        # 3. 尝试手机号
        if not user and identifier.isdigit() and len(identifier) == 11:
            user = await self.repository.get_user_by_phone(identifier)

        # 验证密码
        if user and user.password_hash:
            if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                # 更新最后登录时间
                await self.repository.update_user_last_login(user.id)
                return user

        return None

    async def authenticate_by_sms(
        self,
        phone: str,
        code: str
    ) -> Optional[User]:
        """通过短信验证码进行身份验证"""
        # 验证短信验证码
        # 这里应该调用SMSService的verify_code方法
        # 为了简化，这里先通过手机号查找用户

        user = await self.repository.get_user_by_phone(phone)
        if user:
            # 更新最后登录时间
            await self.repository.update_user_last_login(user.id)

        return user

    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


class AuthService:
    """核心认证服务"""

    def __init__(
        self,
        auth_repository: AuthRepository,
        sms_repository: SMSRepository,
        token_repository: TokenRepository,
        session_repository: SessionRepository,
        audit_repository: AuditRepository,
        jwt_service: JWTService,
        sms_service: SMSService,
        user_service: UserService
    ):
        self.auth_repository = auth_repository
        self.sms_repository = sms_repository
        self.token_repository = token_repository
        self.session_repository = session_repository
        self.audit_repository = audit_repository
        self.jwt_service = jwt_service
        self.sms_service = sms_service
        self.user_service = user_service

    async def init_guest_account(
        self,
        request: GuestInitRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """初始化游客账号"""
        try:
            # 创建游客用户
            guest_user = await self.user_service.create_guest_user(
                device_id=request.device_id,
                device_type=request.device_type,
                app_version=request.app_version
            )

            # 生成JWT令牌
            user_data = {
                "user_id": str(guest_user.id),
                "user_type": "guest",
                "is_guest": True,
                "jwt_version": guest_user.jwt_version
            }
            tokens = self.jwt_service.generate_tokens(user_data)

            # 创建会话
            session_id = tokens["access_token_jti"]
            await self.session_repository.create_session(
                user_id=guest_user.id,
                session_id=session_id,
                device_info=request.device_type,
                ip_address=ip_address,
                user_agent=user_agent
            )

            # 记录审计日志
            await self.audit_repository.create_log(
                user_id=guest_user.id,
                action="guest_init",
                result="success",
                details=f"设备ID: {request.device_id}",
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=request.device_id
            )

            return {
                "user_id": str(guest_user.id),
                "is_guest": True,
                **tokens
            }

        except Exception as e:
            # 记录失败日志
            await self.audit_repository.create_log(
                action="guest_init",
                result="failure",
                details=f"错误: {str(e)}",
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=request.device_id
            )
            raise AuthenticationException(f"游客账号初始化失败: {str(e)}")

    async def upgrade_guest_account(
        self,
        request: GuestUpgradeRequest,
        current_user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """升级游客账号"""
        try:
            # 验证短信验证码
            await self.sms_service.verify_code(
                phone=request.phone,
                code=request.sms_code,
                verification_type="upgrade"
            )

            # 升级账号
            updated_user = await self.user_service.upgrade_guest_account(
                guest_user_id=current_user_id,
                phone=request.phone,
                password=request.password,
                nickname=request.nickname
            )

            # 使旧令牌失效（增加JWT版本）
            await self.auth_repository.invalidate_user_tokens(current_user_id)

            # 生成新令牌
            user_data = {
                "user_id": str(updated_user.id),
                "user_type": "registered",
                "is_guest": False,
                "jwt_version": updated_user.jwt_version
            }
            new_tokens = self.jwt_service.generate_tokens(user_data)

            # 记录审计日志
            await self.audit_repository.create_log(
                user_id=updated_user.id,
                action="guest_upgrade",
                result="success",
                details=f"手机号: {request.phone}",
                ip_address=ip_address,
                user_agent=user_agent
            )

            return {
                "user_id": str(updated_user.id),
                "is_guest": False,
                **new_tokens
            }

        except Exception as e:
            # 记录失败日志
            await self.audit_repository.create_log(
                user_id=current_user_id,
                action="guest_upgrade",
                result="failure",
                details=f"错误: {str(e)}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationException(f"账号升级失败: {str(e)}")

    async def login(
        self,
        request: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """用户登录"""
        try:
            # 身份验证
            if request.login_type == "password":
                # 密码登录
                user = await self.user_service.authenticate_user(
                    identifier=request.identifier,
                    password=request.password
                )
            elif request.login_type == "sms":
                # 短信验证码登录
                user = await self.user_service.authenticate_by_sms(
                    phone=request.identifier,
                    code=request.sms_code
                )
            else:
                raise ValidationError("不支持的登录类型")

            if not user:
                raise AuthenticationException("用户名或密码错误")

            # 生成JWT令牌
            user_data = {
                "user_id": str(user.id),
                "user_type": "registered" if not user.is_guest else "guest",
                "is_guest": user.is_guest,
                "jwt_version": user.jwt_version
            }
            tokens = self.jwt_service.generate_tokens(user_data)

            # 创建会话
            session_id = tokens["access_token_jti"]
            await self.session_repository.create_session(
                user_id=user.id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )

            # 记录审计日志
            await self.audit_repository.create_log(
                user_id=user.id,
                action="login",
                result="success",
                details=f"登录方式: {request.login_type}",
                ip_address=ip_address,
                user_agent=user_agent
            )

            return {
                "user_id": str(user.id),
                "is_guest": user.is_guest,
                **tokens
            }

        except Exception as e:
            # 记录失败日志
            await self.audit_repository.create_log(
                action="login",
                result="failure",
                details=f"错误: {str(e)}, 登录方式: {request.login_type}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationException(f"登录失败: {str(e)}")

    async def refresh_token(
        self,
        request: TokenRefreshRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """刷新访问令牌"""
        try:
            # 验证刷新令牌
            token_payload = self.jwt_service.verify_token(request.refresh_token, "refresh")

            # 检查令牌是否在黑名单中
            token_jti = token_payload.get("jti")
            if token_jti and await self.token_repository.is_token_blacklisted(token_jti):
                raise TokenException("刷新令牌已失效")

            # 获取用户信息
            user_id = UUID(token_payload["sub"])
            user = await self.auth_repository.get_by_id(User, user_id)

            if not user or not user.is_active:
                raise UserNotFoundException("用户不存在或已被禁用")

            # 检查JWT版本
            if token_payload.get("jwt_version", 1) != user.jwt_version:
                raise TokenException("令牌版本不匹配")

            # 生成新的访问令牌
            user_data = {
                "user_id": str(user.id),
                "user_type": "registered" if not user.is_guest else "guest",
                "is_guest": user.is_guest,
                "jwt_version": user.jwt_version
            }
            new_tokens = self.jwt_service.generate_tokens(user_data)

            # 将旧的刷新令牌加入黑名单
            if token_jti:
                await self.token_repository.blacklist_token(
                    token_id=token_jti,
                    user_id=user_id,
                    token_type="refresh",
                    expires_at=datetime.fromtimestamp(token_payload["exp"], timezone.utc),
                    reason="令牌刷新"
                )

            # 记录审计日志
            await self.audit_repository.create_log(
                user_id=user.id,
                action="token_refresh",
                result="success",
                ip_address=ip_address,
                user_agent=user_agent
            )

            return new_tokens

        except Exception as e:
            # 记录失败日志
            await self.audit_repository.create_log(
                action="token_refresh",
                result="failure",
                details=f"错误: {str(e)}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise TokenException(f"令牌刷新失败: {str(e)}")

    async def logout(
        self,
        token_jti: str,
        user_id: UUID,
        token_type: str = "access",
        expires_at: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """用户登出"""
        try:
            # 将令牌加入黑名单
            if expires_at:
                await self.token_repository.blacklist_token(
                    token_id=token_jti,
                    user_id=user_id,
                    token_type=token_type,
                    expires_at=expires_at,
                    reason="用户登出"
                )

            # 使用户所有会话失效
            await self.session_repository.invalidate_user_sessions(user_id)

            # 记录审计日志
            await self.audit_repository.create_log(
                user_id=user_id,
                action="logout",
                result="success",
                ip_address=ip_address,
                user_agent=user_agent
            )

        except Exception as e:
            # 记录失败日志
            await self.audit_repository.create_log(
                user_id=user_id,
                action="logout",
                result="failure",
                details=f"错误: {str(e)}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationException(f"登出失败: {str(e)}")

    async def send_sms_code(
        self,
        request: SMSCodeRequest,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """发送短信验证码"""
        try:
            # 发送验证码
            code = await self.sms_service.send_verification_code(
                phone=request.phone,
                verification_type=request.verification_type,
                user_id=user_id
            )

            # 记录审计日志
            await self.audit_repository.create_log(
                user_id=user_id,
                action="sms_send",
                result="success",
                details=f"手机号: {request.phone}, 类型: {request.verification_type}",
                ip_address=ip_address,
                user_agent=user_agent
            )

            return code

        except Exception as e:
            # 记录失败日志
            await self.audit_repository.create_log(
                user_id=user_id,
                action="sms_send",
                result="failure",
                details=f"错误: {str(e)}, 手机号: {request.phone}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise SMSException(f"短信发送失败: {str(e)}")

    async def get_user_info(self, user_id: UUID) -> Dict[str, Any]:
        """获取用户信息"""
        user = await self.auth_repository.get_by_id(User, user_id)

        if not user or not user.is_active:
            raise UserNotFoundException("用户不存在或已被禁用")

        return {
            "user_id": str(user.id),
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "phone": user.phone,
            "avatar": user.avatar,
            "is_guest": user.is_guest,
            "is_verified": user.is_verified,
            "user_type": "guest" if user.is_guest else "registered",
            "level": user.level,
            "total_points": user.total_points,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at
        }


# 便捷函数，用于创建Service实例
async def create_auth_service() -> AuthService:
    """创建认证服务实例"""
    async with get_auth_db() as session:
        # 创建Repository实例
        auth_repository = AuthRepository(session)
        sms_repository = SMSRepository(session)
        token_repository = TokenRepository(session)
        session_repository = SessionRepository(session)
        audit_repository = AuditRepository(session)

        # 创建Service实例
        jwt_service = JWTService(
            secret_key="your-super-secret-jwt-key-here",  # 应该从环境变量获取
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
        sms_service = SMSService(sms_repository)
        user_service = UserService(auth_repository)

        # 创建AuthService实例
        auth_service = AuthService(
            auth_repository=auth_repository,
            sms_repository=sms_repository,
            token_repository=token_repository,
            session_repository=session_repository,
            audit_repository=audit_repository,
            jwt_service=jwt_service,
            sms_service=sms_service,
            user_service=user_service
        )

        return auth_service