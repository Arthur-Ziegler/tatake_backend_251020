"""
认证数据仓储层

该模块提供认证相关的数据访问操作，包括JWT令牌黑名单管理、
短信验证码存储、用户会话管理和认证日志记录。

核心功能：
- JWT令牌黑名单管理
- 短信验证码存储和验证
- 用户会话管理
- 认证日志记录

设计原则：
- 安全存储：敏感信息安全处理
- 过期管理：自动清理过期数据
- 频率限制：防止恶意请求
- 性能优化：高效查询设计
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from src.models.auth import (
    TokenBlacklist, TokenBlacklistCreate, TokenBlacklistRead,
    SmsVerification, SmsVerificationCreate, SmsVerificationRead,
    UserSession, UserSessionCreate, UserSessionRead,
    AuthLog, AuthLogCreate, AuthLogRead
)
from src.services.exceptions import (
    ResourceNotFoundException,
    BusinessException,
    ValidationException
)


class TokenBlacklistRepository(BaseRepository[TokenBlacklist]):
    """JWT令牌黑名单数据仓储类"""

    def __init__(self, session: AsyncSession):
        """
        初始化JWT令牌黑名单仓储

        Args:
            session: 数据库会话
        """
        super().__init__(session, TokenBlacklist)

    async def create_blacklist_record(self, blacklist_data: Dict[str, Any]) -> TokenBlacklistRead:
        """
        创建JWT黑名单记录

        Args:
            blacklist_data: 黑名单数据，包含jti、user_id、reason等

        Returns:
            创建的黑名单记录

        Raises:
            RepositoryValidationError: 数据验证失败时
            RepositoryIntegrityError: 数据完整性约束冲突时
        """
        # 验证必需字段
        required_fields = ['jti', 'user_id', 'reason', 'expires_at']
        for field in required_fields:
            if field not in blacklist_data:
                raise ValidationException(f"缺少必需字段: {field}")

        # 检查是否已存在
        existing = await self.get_by_jti(blacklist_data['jti'])
        if existing:
            raise BusinessException("令牌已在黑名单中", "token_already_blacklisted")

        return await self.create(blacklist_data)

    async def get_by_jti(self, jti: str) -> Optional[TokenBlacklistRead]:
        """
        根据JWT ID获取黑名单记录

        Args:
            jti: JWT令牌的唯一标识符

        Returns:
            黑名单记录或None
        """
        stmt = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        return TokenBlacklistRead.from_orm(record) if record else None

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        检查令牌是否在黑名单中

        Args:
            jti: JWT令牌的唯一标识符

        Returns:
            True如果在黑名单中，False否则
        """
        # 检查是否存在未过期的黑名单记录
        stmt = select(func.count(TokenBlacklist.id)).where(
            and_(
                TokenBlacklist.jti == jti,
                TokenBlacklist.expires_at > datetime.now(timezone.utc)
            )
        )
        result = await self.session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def get_user_blacklisted_tokens(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[TokenBlacklistRead]:
        """
        获取用户的黑名单令牌列表

        Args:
            user_id: 用户ID
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            黑名单记录列表
        """
        stmt = (
            select(TokenBlacklist)
            .where(TokenBlacklist.user_id == user_id)
            .order_by(desc(TokenBlacklist.revoked_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [TokenBlacklistRead.from_orm(record) for record in records]

    async def cleanup_expired_tokens(self) -> int:
        """
        清理过期的黑名单记录

        Returns:
            清理的记录数量
        """
        stmt = select(TokenBlacklist).where(
            TokenBlacklist.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        expired_tokens = result.scalars().all()

        for token in expired_tokens:
            await self.session.delete(token)

        await self.session.commit()
        return len(expired_tokens)


class SmsVerificationRepository(BaseRepository[SmsVerification]):
    """短信验证码数据仓储类"""

    def __init__(self, session: AsyncSession):
        """
        初始化短信验证码仓储

        Args:
            session: 数据库会话
        """
        super().__init__(session, SmsVerification)

    async def create_verification(self, verification_data: Dict[str, Any]) -> SmsVerificationRead:
        """
        创建短信验证码记录

        Args:
            verification_data: 验证码数据

        Returns:
            创建的验证码记录

        Raises:
            BusinessException: 频率限制触发时
        """
        phone_number = verification_data['phone_number']
        verification_type = verification_data['verification_type']

        # 检查发送频率限制
        await self._check_send_rate_limit(phone_number, verification_type)

        # 检查是否有未使用的验证码
        await self._invalidate_existing_codes(phone_number, verification_type)

        return await self.create(verification_data)

    async def verify_code(
        self,
        phone_number: str,
        code: str,
        verification_type: str
    ) -> bool:
        """
        验证短信验证码

        Args:
            phone_number: 手机号码
            code: 验证码
            verification_type: 验证类型

        Returns:
            True验证成功，False验证失败
        """
        # 查找有效的验证码记录
        stmt = select(SmsVerification).where(
            and_(
                SmsVerification.phone_number == phone_number,
                SmsVerification.verification_type == verification_type,
                SmsVerification.code == code,
                SmsVerification.is_used == False,
                SmsVerification.expires_at > datetime.now(timezone.utc),
                SmsVerification.attempt_count < SmsVerification.max_attempts
            )
        ).order_by(desc(SmsVerification.created_at))

        result = await self.session.execute(stmt)
        verification = result.scalar_one_or_none()

        if not verification:
            return False

        # 更新尝试次数
        verification.attempt_count += 1

        if verification.attempt_count >= verification.max_attempts:
            # 超过最大尝试次数，标记为已使用
            verification.is_used = True
            verification.used_at = datetime.now(timezone.utc)

        # 验证成功，标记为已使用
        if verification.code == code:
            verification.is_used = True
            verification.used_at = datetime.now(timezone.utc)

        await self.session.commit()
        return verification.code == code

    async def get_latest_verification(
        self,
        phone_number: str,
        verification_type: str
    ) -> Optional[SmsVerificationRead]:
        """
        获取最新的验证码记录

        Args:
            phone_number: 手机号码
            verification_type: 验证类型

        Returns:
            验证码记录或None
        """
        stmt = (
            select(SmsVerification)
            .where(
                and_(
                    SmsVerification.phone_number == phone_number,
                    SmsVerification.verification_type == verification_type
                )
            )
            .order_by(desc(SmsVerification.created_at))
        )
        result = await self.session.execute(stmt)
        verification = result.scalar_one_or_none()
        return SmsVerificationRead.from_orm(verification) if verification else None

    async def _check_send_rate_limit(self, phone_number: str, verification_type: str) -> None:
        """
        检查发送频率限制

        Args:
            phone_number: 手机号码
            verification_type: 验证类型

        Raises:
            BusinessException: 频率限制触发时
        """
        now = datetime.now(timezone.utc)

        # 检查1分钟内发送次数限制
        one_minute_ago = now - timedelta(minutes=1)
        stmt = select(func.count(SmsVerification.id)).where(
            and_(
                SmsVerification.phone_number == phone_number,
                SmsVerification.verification_type == verification_type,
                SmsVerification.created_at > one_minute_ago
            )
        )
        result = await self.session.execute(stmt)
        recent_count = result.scalar()

        if recent_count >= 1:  # 1分钟内只能发送1次
            raise BusinessException("发送频率过快，请稍后再试", "rate_limit_exceeded")

        # 检查1小时内发送次数限制
        one_hour_ago = now - timedelta(hours=1)
        stmt = select(func.count(SmsVerification.id)).where(
            and_(
                SmsVerification.phone_number == phone_number,
                SmsVerification.verification_type == verification_type,
                SmsVerification.created_at > one_hour_ago
            )
        )
        result = await self.session.execute(stmt)
        hourly_count = result.scalar()

        if hourly_count >= 5:  # 1小时内最多发送5次
            raise BusinessException("今日发送次数已达上限", "daily_limit_exceeded")

    async def _invalidate_existing_codes(self, phone_number: str, verification_type: str) -> None:
        """
        使现有的验证码失效

        Args:
            phone_number: 手机号码
            verification_type: 验证类型
        """
        stmt = select(SmsVerification).where(
            and_(
                SmsVerification.phone_number == phone_number,
                SmsVerification.verification_type == verification_type,
                SmsVerification.is_used == False
            )
        )
        result = await self.session.execute(stmt)
        existing_codes = result.scalars().all()

        for code in existing_codes:
            code.is_used = True
            code.used_at = datetime.now(timezone.utc)

        await self.session.commit()

    async def cleanup_expired_codes(self) -> int:
        """
        清理过期的验证码记录

        Returns:
            清理的记录数量
        """
        stmt = select(SmsVerification).where(
            SmsVerification.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        expired_codes = result.scalars().all()

        for code in expired_codes:
            await self.session.delete(code)

        await self.session.commit()
        return len(expired_codes)


class UserSessionRepository(BaseRepository[UserSession]):
    """用户会话数据仓储类"""

    def __init__(self, session: AsyncSession):
        """
        初始化用户会话仓储

        Args:
            session: 数据库会话
        """
        super().__init__(session, UserSession)

    async def create_session(self, session_data: Dict[str, Any]) -> UserSessionRead:
        """
        创建用户会话

        Args:
            session_data: 会话数据

        Returns:
            创建的会话记录
        """
        return await self.create(session_data)

    async def get_by_session_token(self, session_token: str) -> Optional[UserSessionRead]:
        """
        根据会话令牌获取会话记录

        Args:
            session_token: 会话令牌

        Returns:
            会话记录或None
        """
        stmt = select(UserSession).where(
            and_(
                UserSession.session_token == session_token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(timezone.utc)
            )
        )
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()
        return UserSessionRead.from_orm(session) if session else None

    async def get_user_active_sessions(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[UserSessionRead]:
        """
        获取用户的活跃会话列表

        Args:
            user_id: 用户ID
            limit: 返回记录数限制

        Returns:
            活跃会话列表
        """
        stmt = (
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                )
            )
            .order_by(desc(UserSession.last_activity_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()
        return [UserSessionRead.from_orm(session) for session in sessions]

    async def update_session_activity(self, session_token: str) -> bool:
        """
        更新会话活跃时间

        Args:
            session_token: 会话令牌

        Returns:
            True更新成功，False会话不存在或已过期
        """
        stmt = select(UserSession).where(
            and_(
                UserSession.session_token == session_token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(timezone.utc)
            )
        )
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.last_activity_at = datetime.now(timezone.utc)
            await self.session.commit()
            return True
        return False

    async def revoke_session(self, session_token: str) -> bool:
        """
        撤销用户会话

        Args:
            session_token: 会话令牌

        Returns:
            True撤销成功，False会话不存在
        """
        stmt = select(UserSession).where(UserSession.session_token == session_token)
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.is_active = False
            await self.session.commit()
            return True
        return False

    async def revoke_user_sessions(self, user_id: UUID, exclude_token: Optional[str] = None) -> int:
        """
        撤销用户的所有会话

        Args:
            user_id: 用户ID
            exclude_token: 要排除的会话令牌（可选）

        Returns:
            撤销的会话数量
        """
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )

        if exclude_token:
            stmt = stmt.where(UserSession.session_token != exclude_token)

        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        for session in sessions:
            session.is_active = False

        await self.session.commit()
        return len(sessions)

    async def cleanup_expired_sessions(self) -> int:
        """
        清理过期的会话记录

        Returns:
            清理的记录数量
        """
        stmt = select(UserSession).where(
            or_(
                UserSession.expires_at <= datetime.now(timezone.utc),
                and_(
                    UserSession.is_active == False,
                    UserSession.last_activity_at <= datetime.now(timezone.utc) - timedelta(days=7)
                )
            )
        )
        result = await self.session.execute(stmt)
        expired_sessions = result.scalars().all()

        for session in expired_sessions:
            await self.session.delete(session)

        await self.session.commit()
        return len(expired_sessions)


class AuthLogRepository(BaseRepository[AuthLog]):
    """认证日志数据仓储类"""

    def __init__(self, session: AsyncSession):
        """
        初始化认证日志仓储

        Args:
            session: 数据库会话
        """
        super().__init__(session, AuthLog)

    async def create_log(self, log_data: Dict[str, Any]) -> AuthLogRead:
        """
        创建认证日志记录

        Args:
            log_data: 日志数据

        Returns:
            创建的日志记录
        """
        return await self.create(log_data)

    async def get_user_logs(
        self,
        user_id: UUID,
        action: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AuthLogRead]:
        """
        获取用户认证日志

        Args:
            user_id: 用户ID
            action: 操作类型过滤
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            日志记录列表
        """
        stmt = select(AuthLog).where(AuthLog.user_id == user_id)

        if action:
            stmt = stmt.where(AuthLog.action == action)

        stmt = stmt.order_by(desc(AuthLog.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        logs = result.scalars().all()
        return [AuthLogRead.from_orm(log) for log in logs]

    async def get_identifier_logs(
        self,
        identifier: str,
        action: Optional[str] = None,
        limit: int = 20
    ) -> List[AuthLogRead]:
        """
        根据标识符获取认证日志

        Args:
            identifier: 操作标识（手机号/邮箱等）
            action: 操作类型过滤
            limit: 返回记录数限制

        Returns:
            日志记录列表
        """
        stmt = select(AuthLog).where(AuthLog.identifier == identifier)

        if action:
            stmt = stmt.where(AuthLog.action == action)

        stmt = stmt.order_by(desc(AuthLog.created_at)).limit(limit)

        result = await self.session.execute(stmt)
        logs = result.scalars().all()
        return [AuthLogRead.from_orm(log) for log in logs]

    async def get_failed_attempts(
        self,
        identifier: str,
        time_window_minutes: int = 15,
        action: str = "login"
    ) -> int:
        """
        获取指定时间窗口内的失败尝试次数

        Args:
            identifier: 操作标识
            time_window_minutes: 时间窗口（分钟）
            action: 操作类型

        Returns:
            失败尝试次数
        """
        time_window = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)

        stmt = select(func.count(AuthLog.id)).where(
            and_(
                AuthLog.identifier == identifier,
                AuthLog.action == action,
                AuthLog.success == False,
                AuthLog.created_at > time_window
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        清理旧的认证日志

        Args:
            days_to_keep: 保留天数

        Returns:
            清理的记录数量
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        stmt = select(AuthLog).where(AuthLog.created_at < cutoff_date)
        result = await self.session.execute(stmt)
        old_logs = result.scalars().all()

        for log in old_logs:
            await self.session.delete(log)

        await self.session.commit()
        return len(old_logs)