"""
异步认证Repository实现

提供异步认证相关的数据访问层操作，封装认证业务逻辑查询。
继承自AsyncBaseRepository，专注于认证特有的业务场景。

功能特性：
1. 异步令牌黑名单管理（存储、查询、删除、清理）
2. 异步短信记录管理（发送记录、验证记录、频率控制）
3. 异步会话管理（会话创建、查询、删除、过期清理）
4. 异步安全日志管理（登录日志、操作日志、异常日志）
5. 异步统计和分析（认证统计、风险分析等）

设计原则：
1. 单一责任：专注于认证相关的数据访问
2. 查询封装：复杂业务查询封装在Repository方法中
3. 异常统一：使用统一的异常处理机制
4. 类型安全：强类型参数和返回值
5. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建异步认证Repository
    >>> auth_repo = AsyncAuthRepository(async_session)
    >>>
    >>> # 异步检查令牌是否在黑名单中
    >>> is_blacklisted = await auth_repo.is_token_blacklisted("token123")
    >>>
    >>> # 异步添加令牌到黑名单
    >>> await auth_repo.add_to_blacklist("token123", expiry_time)
    >>>
    >>> # 异步记录短信发送
    >>> await auth_repo.record_sms_sent("13800138000", "login", "123456")
    >>>
    >>> # 异步检查短信发送频率
    >>> can_send = await auth_repo.check_sms_frequency("13800138000", "login")
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_, func, delete
from sqlalchemy.exc import SQLAlchemyError

# 导入异步基础Repository和异常类
from src.repositories.async_base import (
    AsyncBaseRepository, AsyncRepositoryError,
    AsyncRepositoryValidationError, AsyncRepositoryNotFoundError
)
from src.models.auth import TokenBlacklist, SMSRecord


class AsyncAuthRepository:
    """
    异步认证Repository类

    提供异步认证相关的数据库操作，封装认证业务逻辑查询。
    不继承自AsyncBaseRepository，直接处理多种模型。

    Attributes:
        session: SQLAlchemy异步会话对象
    """

    def __init__(self, session: AsyncSession):
        """
        初始化异步AuthRepository

        Args:
            session: SQLAlchemy异步会话对象
        """
        self.session = session
        self.model_name = "Auth"

    # ============= 令牌黑名单管理 =============

    async def add_to_blacklist(self, token: str, expires_at: datetime, user_id: str = None, reason: str = None) -> TokenBlacklist:
        """
        异步添加令牌到黑名单

        Args:
            token: JWT令牌字符串
            expires_at: 令牌过期时间
            user_id: 用户ID，可选
            reason: 加入黑名单的原因，可选

        Returns:
            TokenBlacklist: 创建的黑名单记录

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not token or not isinstance(token, str):
                raise AsyncRepositoryValidationError("令牌参数不能为空且必须是字符串类型")

            if not isinstance(expires_at, datetime):
                raise AsyncRepositoryValidationError("过期时间参数必须是datetime类型")

            # 检查令牌是否已在黑名单中
            if await self.is_token_blacklisted(token):
                raise AsyncRepositoryValidationError(f"令牌已在黑名单中: {token[:50]}...")

            # 创建黑名单记录
            blacklist_data = {
                "token": token,
                "expires_at": expires_at,
                "user_id": user_id,
                "reason": reason
            }

            return await self.create(blacklist_data)

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            raise AsyncRepositoryError(
                f"添加令牌到黑名单失败: {str(e)}",
                operation="create",
                model_name="TokenBlacklist"
            )

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        异步检查令牌是否在黑名单中

        Args:
            token: JWT令牌字符串

        Returns:
            bool: 令牌在黑名单中返回True，否则返回False

        Raises:
            AsyncRepositoryValidationError: 令牌参数无效时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not token or not isinstance(token, str):
                raise AsyncRepositoryValidationError("令牌参数不能为空且必须是字符串类型")

            # 构建查询：查找未过期的黑名单记录
            statement = select(TokenBlacklist).where(
                and_(
                    TokenBlacklist.token == token,
                    TokenBlacklist.expires_at > datetime.now(timezone.utc)
                )
            )

            # 执行查询
            result = await self.session.execute(statement)
            blacklist_record = result.scalar_one_or_none()

            return blacklist_record is not None

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            raise AsyncRepositoryError(
                f"检查令牌黑名单状态失败: {str(e)}",
                operation="read",
                model_name="TokenBlacklist"
            )

    async def remove_expired_blacklist(self) -> int:
        """
        异步清理过期的黑名单记录

        Returns:
            int: 清理的记录数量

        Raises:
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 构建删除查询：删除已过期的记录
            statement = delete(TokenBlacklist).where(
                TokenBlacklist.expires_at <= datetime.now(timezone.utc)
            )

            # 执行删除
            result = await self.session.execute(statement)
            await self.session.commit()

            return result.rowcount

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"清理过期黑名单记录失败: {str(e)}",
                operation="delete",
                model_name="TokenBlacklist"
            )
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"清理过期黑名单记录时发生未知错误: {str(e)}",
                operation="delete",
                model_name="TokenBlacklist"
            )

    async def get_user_blacklisted_tokens(self, user_id: str) -> List[TokenBlacklist]:
        """
        异步获取用户的所有黑名单令牌

        Args:
            user_id: 用户ID

        Returns:
            List[TokenBlacklist]: 黑名单令牌列表

        Raises:
            AsyncRepositoryValidationError: 用户ID参数无效时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise AsyncRepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(TokenBlacklist).where(
                and_(
                    TokenBlacklist.user_id == user_id,
                    TokenBlacklist.expires_at > datetime.now(timezone.utc)
                )
            ).order_by(TokenBlacklist.created_at.desc())

            # 执行查询
            result = await self.session.execute(statement)
            tokens = result.scalars().all()

            return list(tokens)

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取用户黑名单令牌失败: {str(e)}",
                operation="read",
                model_name="TokenBlacklist"
            )

    # ============= 短信记录管理 =============

    async def record_sms_sent(self, phone: str, verification_type: str, code: str,
                             ip_address: str = None, user_id: str = None) -> SMSRecord:
        """
        异步记录短信发送

        Args:
            phone: 手机号码
            verification_type: 验证类型（login, register, reset_password等）
            code: 验证码
            ip_address: 发送IP地址，可选
            user_id: 用户ID，可选

        Returns:
            SMSRecord: 创建的短信记录

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not phone or not isinstance(phone, str):
                raise AsyncRepositoryValidationError("手机号参数不能为空且必须是字符串类型")

            if not verification_type or not isinstance(verification_type, str):
                raise AsyncRepositoryValidationError("验证类型参数不能为空且必须是字符串类型")

            if not code or not isinstance(code, str):
                raise AsyncRepositoryValidationError("验证码参数不能为空且必须是字符串类型")

            # 创建短信记录
            sms_record = SMSRecord(
                phone=phone,
                verification_type=verification_type,
                code=code,
                ip_address=ip_address,
                user_id=user_id,
                status="sent",
                created_at=datetime.now(timezone.utc)  # 使用timezone-aware的时间戳
            )

            # 添加到会话并提交
            self.session.add(sms_record)
            await self.session.commit()
            await self.session.refresh(sms_record)

            return sms_record

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"记录短信发送失败: {str(e)}",
                operation="create",
                model_name="SMSRecord"
            )

    async def check_sms_frequency(self, phone: str, verification_type: str,
                                 time_window_minutes: int = 1, max_count: int = 1) -> bool:
        """
        异步检查短信发送频率限制

        Args:
            phone: 手机号码
            verification_type: 验证类型
            time_window_minutes: 时间窗口（分钟），默认1分钟
            max_count: 最大发送次数，默认1次

        Returns:
            bool: 可以发送返回True，否则返回False

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not phone or not isinstance(phone, str):
                raise AsyncRepositoryValidationError("手机号参数不能为空且必须是字符串类型")

            if not verification_type or not isinstance(verification_type, str):
                raise AsyncRepositoryValidationError("验证类型参数不能为空且必须是字符串类型")

            # 计算时间窗口
            time_threshold = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)

            # 构建查询：统计时间窗口内的发送次数
            statement = select(func.count()).select_from(SMSRecord).where(
                and_(
                    SMSRecord.phone == phone,
                    SMSRecord.verification_type == verification_type,
                    SMSRecord.created_at >= time_threshold
                )
            )

            # 执行查询
            result = await self.session.execute(statement)
            count = result.scalar()

            return count < max_count

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            raise AsyncRepositoryError(
                f"检查短信发送频率失败: {str(e)}",
                operation="read",
                model_name="SMSRecord"
            )

    async def get_latest_sms_code(self, phone: str, verification_type: str) -> Optional[SMSRecord]:
        """
        异步获取最新的短信验证码记录

        Args:
            phone: 手机号码
            verification_type: 验证类型

        Returns:
            Optional[SMSRecord]: 最新的短信记录，未找到返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not phone or not isinstance(phone, str):
                raise AsyncRepositoryValidationError("手机号参数不能为空且必须是字符串类型")

            if not verification_type or not isinstance(verification_type, str):
                raise AsyncRepositoryValidationError("验证类型参数不能为空且必须是字符串类型")

            # 构建查询：查找最新的验证码记录
            statement = select(SMSRecord).where(
                and_(
                    SMSRecord.phone == phone,
                    SMSRecord.verification_type == verification_type
                )
            ).order_by(SMSRecord.created_at.desc())

            # 执行查询，添加限制条件确保只返回一条记录
            result = await self.session.execute(statement.limit(1))
            sms_record = result.scalar_one_or_none()

            return sms_record

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取最新短信验证码失败: {str(e)}",
                operation="read",
                model_name="SMSRecord"
            )

    async def mark_sms_verified(self, sms_id) -> bool:
        """
        异步标记短信记录为已验证

        Args:
            sms_id: 短信记录ID（支持str或int类型）

        Returns:
            bool: 标记成功返回True，记录不存在返回False

        Raises:
            AsyncRepositoryValidationError: 短信ID参数无效时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证，支持str和int类型
            if not sms_id or not isinstance(sms_id, (str, int)):
                raise AsyncRepositoryValidationError("短信ID参数不能为空且必须是字符串或整数类型")

            # 转换为字符串进行查询
            sms_id_str = str(sms_id)

            # 直接查找并更新短信记录
            statement = select(SMSRecord).where(SMSRecord.id == sms_id_str)
            result = await self.session.execute(statement)
            sms_record = result.scalar_one_or_none()

            if sms_record is None:
                return False

            # 更新状态
            sms_record.status = "verified"
            sms_record.verified_at = datetime.now(timezone.utc)

            await self.session.commit()
            return True

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"标记短信验证状态失败: {str(e)}",
                operation="update",
                model_name="SMSRecord"
            )

    # ============= 统计和分析方法 =============

    async def get_auth_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        异步获取认证统计信息

        Args:
            days: 统计天数，默认7天

        Returns:
            Dict[str, Any]: 统计信息字典

        Raises:
            AsyncRepositoryValidationError: 天数参数无效时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not isinstance(days, int) or days <= 0:
                raise AsyncRepositoryValidationError("天数参数必须是正整数")

            # 计算统计时间范围
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            # 统计短信发送次数
            sms_statement = select(func.count()).select_from(SMSRecord).where(
                SMSRecord.created_at >= start_time
            )
            sms_result = await self.session.execute(sms_statement)
            sms_count = sms_result.scalar()

            # 统计黑名单令牌数量
            blacklist_statement = select(func.count()).select_from(TokenBlacklist).where(
                and_(
                    TokenBlacklist.created_at >= start_time,
                    TokenBlacklist.expires_at > datetime.now(timezone.utc)
                )
            )
            blacklist_result = await self.session.execute(blacklist_statement)
            blacklist_count = blacklist_result.scalar()

            return {
                "period_days": days,
                "sms_sent_count": sms_count or 0,
                "blacklisted_tokens_count": blacklist_count or 0,
                "statistics_time": datetime.now(timezone.utc).isoformat()
            }

        except AsyncRepositoryValidationError:
            raise
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取认证统计信息失败: {str(e)}",
                operation="read",
                model_name="Auth"
            )


# 导出AsyncAuthRepository类
__all__ = ["AsyncAuthRepository"]