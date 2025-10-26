"""
认证领域Repository层 - 支持UUID类型转换

提供统一的数据库访问接口，在Repository层处理UUID类型转换。
Service层只需要处理UUID对象，Repository层负责与数据库的交互。

Repository职责:
- AuthRepository: 管理Auth实体的基础CRUD操作，处理UUID转换
- AuditRepository: 管理AuthLog实体的基础操作，处理UUID转换

设计原则:
- 类型隔离：Service层使用UUID，Repository层处理字符串转换
- 统一接口：提供一致的数据库操作方法
- 错误处理：封装数据库操作异常
- 极简化：只保留认证核心功能
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import select, update, Session
from sqlalchemy import and_, desc

from .models import Auth, AuthLog, SMSVerification
from src.core.uuid_converter import UUIDConverter

logger = logging.getLogger(__name__)


class AuthRepository:
    """
    简化的认证Repository

    专注于Auth实体的基础CRUD操作：
    - 创建用户（游客和正式用户）
    - 查找用户（通过ID或微信OpenID）
    - 升级游客账号
    - 更新登录时间

    移除的功能：
    - 复杂查询操作
    - 统计功能
    - 审计日志查询
    """

    def __init__(self, session: Session):
        self.session = session

    def create_user(
        self,
        user_id: Optional[UUID] = None,
        wechat_openid: Optional[str] = None,
        is_guest: bool = True
    ) -> Auth:
        """
        创建用户

        支持两种调用方式：
        1. 新方式：create_user(user_id=UUID, wechat_openid=..., is_guest=...)
        2. 旧方式：create_user(is_guest=..., wechat_openid=...) - 向后兼容

        Args:
            user_id: 用户ID（UUID对象，可选，旧方式调用时自动生成）
            wechat_openid: 微信OpenID
            is_guest: 是否为游客

        Returns:
            Auth: 创建的用户实体
        """
        try:
            # 向后兼容：如果未提供user_id，自动生成
            if user_id is None:
                user_id = uuid4()
                logger.info(f"Auto-generated user_id: {user_id}")

            # 转换UUID为字符串进行存储
            user_id_str = UUIDConverter.to_string(user_id)

            user = Auth(
                id=user_id_str,
                wechat_openid=wechat_openid,
                is_guest=is_guest
            )

            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

            logger.info(f"Created user: {user_id_str}, is_guest: {is_guest}")
            return user

        except Exception as e:
            logger.error(f"Failed to create user {user_id}: {e}")
            self.session.rollback()
            raise

    def get_by_id(self, user_id: UUID) -> Optional[Auth]:
        """
        通过ID查找用户

        Service层传入UUID对象，Repository层转换为字符串进行查询。
        增加了类型验证和详细的错误日志记录。

        Args:
            user_id: 用户ID（UUID对象）

        Returns:
            Optional[Auth]: 找到的用户实体，未找到时返回None

        Raises:
            TypeError: 当user_id不是UUID类型时
        """
        try:
            # 增强类型检查
            if not isinstance(user_id, UUID):
                raise TypeError(f"user_id must be UUID object, got {type(user_id)}: {user_id}")

            # 使用UUIDConverter进行类型转换
            user_id_str = UUIDConverter.to_string(user_id)

            # 记录查询日志（仅在DEBUG级别）
            logger.debug(f"Querying user by ID: {user_id_str}")

            statement = select(Auth).where(Auth.id == user_id_str)
            row_result = self.session.execute(statement).first()

            if row_result:
                # 从Row对象中提取Auth实体
                result = row_result[0]  # 或者使用 row_result.Auth
                logger.debug(f"Found user: {result.id}")
                return result
            else:
                logger.debug(f"User not found: {user_id_str}")
                return None
        except TypeError as te:
            logger.error(f"Type error in get_by_id: {te}")
            raise  # 重新抛出类型错误
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
            return None

    def get_by_wechat_openid(self, wechat_openid: str) -> Optional[Auth]:
        """
        通过微信OpenID查找用户

        Args:
            wechat_openid: 微信OpenID

        Returns:
            Optional[Auth]: 找到的用户实体，未找到时返回None
        """
        try:
            statement = select(Auth).where(Auth.wechat_openid == wechat_openid)
            row_result = self.session.execute(statement).first()

            if row_result:
                return row_result[0]  # 从Row对象中提取Auth实体
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to get user by wechat_openid {wechat_openid}: {e}")
            return None

    def upgrade_guest_account(
        self,
        user_id: UUID,
        wechat_openid: str
    ) -> Optional[Auth]:
        """
        升级游客账号为正式用户

        Args:
            user_id: 游客用户ID（UUID对象）
            wechat_openid: 微信OpenID

        Returns:
            Optional[Auth]: 升级后的用户实体，失败时返回None
        """
        try:
            # 使用UUIDConverter进行类型转换
            user_id_str = UUIDConverter.to_string(user_id)
            statement = (
                update(Auth)
                .where(Auth.id == user_id_str)
                .values(
                    is_guest=False,
                    wechat_openid=wechat_openid,
                    jwt_version=Auth.jwt_version + 1,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            self.session.execute(statement)
            self.session.commit()

            # 返回更新后的用户
            return self.get_by_id(user_id)
        except Exception as e:
            logger.error(f"Failed to upgrade guest account {user_id}: {e}")
            self.session.rollback()
            return None

    def update_last_login(self, user_id: UUID, login_time: Optional[datetime] = None) -> bool:
        """
        更新用户最后登录时间

        Args:
            user_id: 用户ID（UUID对象）
            login_time: 登录时间（可选，默认为当前时间）

        Returns:
            bool: 更新是否成功
        """
        try:
            # 使用UUIDConverter进行类型转换
            user_id_str = UUIDConverter.to_string(user_id)

            # 如果没有提供登录时间，使用当前时间
            if login_time is None:
                login_time = datetime.now(timezone.utc)

            statement = (
                update(Auth)
                .where(Auth.id == user_id_str)
                .values(
                    last_login_at=login_time,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            self.session.execute(statement)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            self.session.rollback()
            return False

    # ===== SMS认证相关方法 =====

    def get_auth_by_phone(self, phone: str) -> Optional[Auth]:
        """
        根据手机号获取用户

        Args:
            phone: 手机号

        Returns:
            Optional[Auth]: 用户实体或None
        """
        try:
            statement = select(Auth).where(Auth.phone == phone)
            result = self.session.execute(statement).scalar()

            if result:
                logger.info(f"Found user by phone: {phone}, user_id: {result.id}")
            else:
                logger.info(f"No user found for phone: {phone}")

            return result
        except Exception as e:
            logger.error(f"Failed to get user by phone {phone}: {e}")
            return None

    def create_sms_verification(self, verification: SMSVerification) -> SMSVerification:
        """
        创建SMS验证码记录

        Args:
            verification: SMS验证码实体

        Returns:
            SMSVerification: 创建的验证码实体
        """
        try:
            self.session.add(verification)
            self.session.commit()
            self.session.refresh(verification)

            logger.info(f"Created SMS verification: {verification.id}, phone: {verification.phone}, scene: {verification.scene}")
            return verification
        except Exception as e:
            logger.error(f"Failed to create SMS verification: {e}")
            self.session.rollback()
            raise

    def get_latest_verification(self, phone: str) -> Optional[SMSVerification]:
        """
        获取指定手机号的最新验证码

        Args:
            phone: 手机号

        Returns:
            Optional[SMSVerification]: 最新的验证码实体或None
        """
        try:
            statement = (
                select(SMSVerification)
                .where(SMSVerification.phone == phone)
                .order_by(desc(SMSVerification.created_at))
                .limit(1)
            )
            result = self.session.execute(statement).scalar()

            if result:
                logger.info(f"Found latest verification for phone: {phone}, created_at: {result.created_at}")

            return result
        except Exception as e:
            logger.error(f"Failed to get latest verification for phone {phone}: {e}")
            return None

    def get_latest_unverified(self, phone: str, scene: str) -> Optional[SMSVerification]:
        """
        获取指定手机号和场景的最新未验证验证码

        Args:
            phone: 手机号
            scene: 使用场景

        Returns:
            Optional[SMSVerification]: 最新的未验证验证码或None
        """
        try:
            statement = (
                select(SMSVerification)
                .where(
                    and_(
                        SMSVerification.phone == phone,
                        SMSVerification.scene == scene,
                        SMSVerification.verified == False
                    )
                )
                .order_by(desc(SMSVerification.created_at))
                .limit(1)
            )
            result = self.session.execute(statement).scalar()

            if result:
                logger.info(f"Found latest unverified verification for phone: {phone}, scene: {scene}")

            return result
        except Exception as e:
            logger.error(f"Failed to get latest unverified verification for phone {phone}, scene {scene}: {e}")
            return None

    def count_today_sends(self, phone: str) -> int:
        """
        统计指定手机号今日发送次数

        Args:
            phone: 手机号

        Returns:
            int: 今日发送次数
        """
        try:
            # 获取今日开始时间
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            statement = (
                select(SMSVerification)
                .where(
                    and_(
                        SMSVerification.phone == phone,
                        SMSVerification.created_at >= today
                    )
                )
            )
            results = self.session.execute(statement).scalars().all()
            count = len(results)

            logger.info(f"Counted {count} SMS sends for phone {phone} today")
            return count
        except Exception as e:
            logger.error(f"Failed to count today SMS sends for phone {phone}: {e}")
            return 0

    def update_verification(self, verification: SMSVerification) -> SMSVerification:
        """
        更新SMS验证码记录

        Args:
            verification: 要更新的验证码实体

        Returns:
            SMSVerification: 更新后的验证码实体
        """
        try:
            self.session.merge(verification)
            self.session.commit()
            self.session.refresh(verification)

            logger.info(f"Updated SMS verification: {verification.id}, verified: {verification.verified}")
            return verification
        except Exception as e:
            logger.error(f"Failed to update SMS verification {verification.id}: {e}")
            self.session.rollback()
            raise


class AuditRepository:
    """
    简化的审计日志Repository

    专注于AuthLog实体的基础操作：
    - 创建审计日志

    移除的功能：
    - 复杂查询和统计
    - 日期范围查询
    - 操作类型查询
    """

    def __init__(self, session: Session):
        self.session = session

    def create_log(
        self,
        user_id: Optional[UUID],
        action: str,
        result: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> Optional[AuthLog]:
        """
        创建审计日志

        Args:
            user_id: 用户ID（可为空，用于游客操作）
            action: 操作类型（login, register, upgrade, token_refresh等）
            result: 操作结果（success, failure, error）
            details: 详细信息
            ip_address: IP地址
            user_agent: 用户代理
            device_id: 设备ID（已弃用但保留用于日志）
            error_code: 错误代码

        Returns:
            Optional[AuthLog]: 创建的审计日志实体，失败时返回None
        """
        try:
            # 增强UUID类型检查和转换
            user_id_str = None
            if user_id is not None:
                if not isinstance(user_id, UUID):
                    logger.error(f"Invalid user_id type in audit log: {type(user_id)}, value: {user_id}")
                    # 尝试转换，但不抛出异常（审计日志应该记录所有操作）
                    try:
                        user_id_str = str(UUID(user_id))
                    except Exception:
                        user_id_str = str(user_id)
                        logger.warning(f"Using fallback string conversion for user_id: {user_id_str}")
                else:
                    user_id_str = UUIDConverter.to_string(user_id)

            log = AuthLog(
                user_id=user_id_str,
                action=action,
                result=result,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id,
                error_code=error_code
            )

            self.session.add(log)
            self.session.commit()
            self.session.refresh(log)

            logger.info(f"Created audit log: {log.id}, user_id: {user_id_str}, action: {action}, result: {result}")
            return log
        except Exception as e:
            logger.error(f"Failed to create auth log: {e}")
            self.session.rollback()
            return None

    

# ===== 删除的Repository注释 =====
# 以下Repository已被删除，原因：
# - SMSRepository: 移除短信验证功能
# - TokenRepository: 移除令牌黑名单功能
# - SessionRepository: 移除会话管理功能
# - UserRepository: 合并简化为AuthRepository