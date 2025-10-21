"""
认证领域数据访问层

提供对认证数据库的抽象访问，封装所有数据库操作。
Repository层遵循依赖倒置原则，为Service层提供数据访问接口。

主要Repository:
- AuthRepository: 用户认证和令牌管理
- UserRepository: 用户基本信息管理
- SMSRepository: 短信验证码管理
- SessionRepository: 用户会话管理

设计原则:
1. 单一责任原则: 每个Repository负责特定的数据类型
2. 依赖倒置原则: 通过抽象接口定义数据访问契约
3. 异步操作: 所有数据库操作都是异步的
4. 错误处理: 统一的异常处理和错误传播
5. 事务支持: 支持复杂的事务操作
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, select, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_auth_db
from .models import (
    User, UserSettings, SMSVerification, TokenBlacklist,
    UserSession, AuthLog
)
from .exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    SMSException,
    ValidationError
)


class BaseRepository:
    """基础Repository类，提供通用的数据库操作方法"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, model_instance) -> Any:
        """保存模型实例"""
        self.session.add(model_instance)
        await self.session.commit()
        await self.session.refresh(model_instance)
        return model_instance

    async def delete(self, model_instance) -> None:
        """删除模型实例"""
        await self.session.delete(model_instance)
        await self.session.commit()

    async def execute_query(self, query):
        """执行查询并返回结果"""
        result = await self.session.execute(query)
        return result

    async def get_by_id(self, model_class, id: UUID):
        """根据ID获取模型实例"""
        query = select(model_class).where(model_class.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def count(self, model_class, **filters):
        """统计记录数量"""
        query = select(func.count(model_class.id))
        for field, value in filters.items():
            if hasattr(model_class, field):
                query = query.where(getattr(model_class, field) == value)
        result = await self.session.execute(query)
        return result.scalar()


class AuthRepository(BaseRepository):
    """认证Repository，处理用户认证和令牌管理相关操作"""

    async def create_user(
        self,
        username: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        password_hash: Optional[str] = None,
        is_guest: bool = False,
        device_id: Optional[str] = None,
        device_type: Optional[str] = None,
        nickname: Optional[str] = None
    ) -> User:
        """创建新用户"""
        user = User(
            username=username,
            email=email,
            phone=phone,
            password_hash=password_hash,
            is_guest=is_guest,
            device_id=device_id,
            device_type=device_type,
            nickname=nickname or username or phone or "游客用户"
        )
        return await self.save(user)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        query = select(User).where(
            and_(
                User.username == username,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        query = select(User).where(
            and_(
                User.email == email,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        """根据手机号获取用户"""
        query = select(User).where(
            and_(
                User.phone == phone,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_device(self, device_id: str) -> Optional[User]:
        """根据设备ID获取游客用户"""
        query = select(User).where(
            and_(
                User.device_id == device_id,
                User.is_guest == True,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_user_last_login(self, user_id: UUID) -> None:
        """更新用户最后登录时间"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.now(timezone.utc),
                login_count=User.login_count + 1
            )
        )
        await self.session.execute(query)
        await self.session.commit()

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None:
        """更新用户密码哈希"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def upgrade_guest_account(
        self,
        user_id: UUID,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        username: Optional[str] = None,
        nickname: Optional[str] = None
    ) -> User:
        """升级游客账号为正式用户"""
        user = await self.get_by_id(User, user_id)
        if not user:
            raise UserNotFoundException(f"用户不存在: {user_id}")

        if not user.is_guest:
            raise ValidationError("只能升级游客账号")

        # 准备更新数据
        update_data = {
            "is_guest": False,
            "is_verified": True,
            "updated_at": datetime.now(timezone.utc)
        }

        if phone:
            update_data["phone"] = phone
        if email:
            update_data["email"] = email
        if password_hash:
            update_data["password_hash"] = password_hash
        if username:
            update_data["username"] = username
        if nickname:
            update_data["nickname"] = nickname

        query = update(User).where(User.id == user_id).values(**update_data)
        await self.session.execute(query)
        await self.session.commit()

        # 刷新并返回更新后的用户
        await self.session.refresh(user)
        return user

    async def invalidate_user_tokens(self, user_id: UUID) -> None:
        """使用户所有令牌失效（增加JWT版本）"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(jwt_version=User.jwt_version + 1)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def soft_delete_user(self, user_id: UUID) -> None:
        """软删除用户"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(
                is_active=False,
                deleted_at=datetime.now(timezone.utc)
            )
        )
        await self.session.execute(query)
        await self.session.commit()


class SMSRepository(BaseRepository):
    """短信验证码Repository，处理短信验证码相关操作"""

    async def create_verification_code(
        self,
        phone: str,
        code: str,
        verification_type: str = "login",
        user_id: Optional[UUID] = None,
        expire_minutes: int = 5
    ) -> SMSVerification:
        """创建短信验证码"""
        # 先使该手机号的旧验证码失效
        await self.invalidate_old_codes(phone, verification_type)

        verification = SMSVerification(
            phone=phone,
            code=code,
            verification_type=verification_type,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
        )
        return await self.save(verification)

    async def invalidate_old_codes(self, phone: str, verification_type: str) -> None:
        """使指定手机号的旧验证码失效"""
        query = (
            update(SMSVerification)
            .where(
                and_(
                    SMSVerification.phone == phone,
                    SMSVerification.verification_type == verification_type,
                    SMSVerification.is_used == False,
                    SMSVerification.expires_at > datetime.now(timezone.utc)
                )
            )
            .values(is_used=True)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def verify_code(
        self,
        phone: str,
        code: str,
        verification_type: str = "login"
    ) -> Optional[SMSVerification]:
        """验证短信验证码"""
        query = select(SMSVerification).where(
            and_(
                SMSVerification.phone == phone,
                SMSVerification.code == code,
                SMSVerification.verification_type == verification_type,
                SMSVerification.is_used == False,
                SMSVerification.expires_at > datetime.now(timezone.utc),
                SMSVerification.attempts < SMSVerification.max_attempts
            )
        )
        result = await self.session.execute(query)
        verification = result.scalar_one_or_none()

        if verification:
            # 增加尝试次数
            await self.increment_attempt_count(verification.id)

        return verification

    async def mark_code_used(self, verification_id: UUID) -> None:
        """标记验证码为已使用"""
        query = (
            update(SMSVerification)
            .where(SMSVerification.id == verification_id)
            .values(
                is_used=True,
                verified_at=datetime.now(timezone.utc)
            )
        )
        await self.session.execute(query)
        await self.session.commit()

    async def increment_attempt_count(self, verification_id: UUID) -> None:
        """增加验证码尝试次数"""
        query = (
            update(SMSVerification)
            .where(SMSVerification.id == verification_id)
            .values(attempts=SMSVerification.attempts + 1)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def get_latest_code(
        self,
        phone: str,
        verification_type: str = "login"
    ) -> Optional[SMSVerification]:
        """获取指定手机号的最新验证码"""
        query = select(SMSVerification).where(
            and_(
                SMSVerification.phone == phone,
                SMSVerification.verification_type == verification_type,
                SMSVerification.is_used == False
            )
        ).order_by(SMSVerification.created_at.desc())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class TokenRepository(BaseRepository):
    """令牌Repository，处理令牌黑名单相关操作"""

    async def blacklist_token(
        self,
        token_id: str,
        user_id: UUID,
        token_type: str,
        expires_at: datetime,
        reason: Optional[str] = None
    ) -> TokenBlacklist:
        """将令牌加入黑名单"""
        blacklisted_token = TokenBlacklist(
            token_id=token_id,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
            reason=reason
        )
        return await self.save(blacklisted_token)

    async def is_token_blacklisted(self, token_id: str) -> bool:
        """检查令牌是否在黑名单中"""
        query = select(TokenBlacklist).where(
            and_(
                TokenBlacklist.token_id == token_id,
                TokenBlacklist.expires_at > datetime.now(timezone.utc)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def blacklist_user_tokens(
        self,
        user_id: UUID,
        token_type: Optional[str] = None,
        reason: Optional[str] = None
    ) -> None:
        """将用户所有令牌加入黑名单"""
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()

        if user:
            # 根据JWT版本使所有旧令牌失效
            reason = reason or f"用户登出，JWT版本: {user.jwt_version}"

    async def cleanup_expired_tokens(self) -> int:
        """清理过期的黑名单令牌"""
        query = delete(TokenBlacklist).where(
            TokenBlacklist.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount


class SessionRepository(BaseRepository):
    """会话Repository，处理用户会话相关操作"""

    async def create_session(
        self,
        user_id: UUID,
        session_id: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_hours: int = 24
    ) -> UserSession:
        """创建用户会话"""
        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        )
        return await self.save(session)

    async def get_active_session(self, session_id: str) -> Optional[UserSession]:
        """获取活跃的用户会话"""
        query = select(UserSession).where(
            and_(
                UserSession.session_id == session_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(timezone.utc)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_session_activity(self, session_id: str) -> None:
        """更新会话最后活动时间"""
        query = (
            update(UserSession)
            .where(UserSession.session_id == session_id)
            .values(last_activity_at=datetime.now(timezone.utc))
        )
        await self.session.execute(query)
        await self.session.commit()

    async def invalidate_session(self, session_id: str) -> None:
        """使会话失效"""
        query = (
            update(UserSession)
            .where(UserSession.session_id == session_id)
            .values(is_active=False)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def invalidate_user_sessions(self, user_id: UUID) -> None:
        """使用户所有会话失效"""
        query = (
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .values(is_active=False)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def cleanup_expired_sessions(self) -> int:
        """清理过期的会话"""
        query = delete(UserSession).where(
            UserSession.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount


class AuditRepository(BaseRepository):
    """审计Repository，处理认证日志相关操作"""

    async def create_log(
        self,
        user_id: Optional[UUID],
        action: str,
        result: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> AuthLog:
        """创建认证日志"""
        log = AuthLog(
            user_id=user_id,
            action=action,
            result=result,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
            error_code=error_code
        )
        return await self.save(log)

    async def get_user_logs(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuthLog]:
        """获取用户认证日志"""
        query = (
            select(AuthLog)
            .where(AuthLog.user_id == user_id)
            .order_by(AuthLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_login_attempts(
        self,
        ip_address: str,
        time_minutes: int = 15
    ) -> List[AuthLog]:
        """获取指定IP的登录尝试记录"""
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=time_minutes)

        query = select(AuthLog).where(
            and_(
                AuthLog.ip_address == ip_address,
                AuthLog.action == "login",
                AuthLog.created_at >= time_threshold
            )
        ).order_by(AuthLog.created_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧的审计日志"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = delete(AuthLog).where(AuthLog.created_at < cutoff_date)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount


# 便捷函数，用于在Service层获取Repository实例
async def get_auth_repository() -> AuthRepository:
    """获取认证Repository实例"""
    async with get_auth_db() as session:
        return AuthRepository(session)


async def get_sms_repository() -> SMSRepository:
    """获取短信Repository实例"""
    async with get_auth_db() as session:
        return SMSRepository(session)


async def get_token_repository() -> TokenRepository:
    """获取令牌Repository实例"""
    async with get_auth_db() as session:
        return TokenRepository(session)


async def get_session_repository() -> SessionRepository:
    """获取会话Repository实例"""
    async with get_auth_db() as session:
        return SessionRepository(session)


async def get_audit_repository() -> AuditRepository:
    """获取审计Repository实例"""
    async with get_auth_db() as session:
        return AuditRepository(session)