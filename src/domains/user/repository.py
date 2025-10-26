"""
用户域Repository层 - 域分离架构实现

提供用户领域的数据访问接口，与认证域完全分离。
Repository层负责：
- 用户业务数据的CRUD操作
- 与认证域的数据关联
- 业务逻辑的数据封装

设计原则：
- 域分离：只操作用户域数据
- 关联查询：通过user_id与认证域关联
- 事务安全：确保数据一致性

作者：TaKeKe团队
版本：1.0.0 - 域分离架构
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from sqlmodel import Session, select, update
from sqlalchemy import and_

from .models import User, UserSettings, UserPreferences, UserStats
from src.domains.auth.repository import AuthRepository
from src.domains.auth.models import Auth

logger = logging.getLogger(__name__)


class UserRepository:
    """
    用户Repository类

    负责用户业务数据的CRUD操作，与认证域数据分离。
    """

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        根据用户ID获取用户

        Args:
            user_id (UUID): 用户ID

        Returns:
            Optional[User]: 用户实体，如果不存在则返回None
        """
        try:
            statement = select(User).where(User.user_id == user_id)
            result = self.session.execute(statement)
            row = result.first()
            if row:
                user = row[0]  # 直接从Row中获取User对象
            else:
                user = None

            logger.debug(f"查询用户: {user_id}, 结果: {user is not None}")
            return user

        except Exception as e:
            logger.error(f"查询用户失败: {e}")
            return None

    def get_by_id_with_auth(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        根据用户ID获取用户信息（包含认证数据）

        Args:
            user_id (UUID): 用户ID

        Returns:
            Optional[Dict[str, Any]]: 用户信息字典，如果不存在则返回None
        """
        try:
            # 查询用户域数据
            user = self.get_by_id(user_id)

            # 查询认证域数据
            from src.domains.auth.database import get_auth_db
            with get_auth_db() as auth_session:
                auth_repo = AuthRepository(auth_session)
                auth_user = auth_repo.get_by_id(user_id)

                # 如果认证用户不存在，返回None
                if not auth_user:
                    return None

                # 查询用户统计和设置
                stats = self.get_user_stats(user_id)
                settings = self.get_user_settings(user_id)

                return {
                    "user": user,
                    "auth": auth_user,
                    "stats": stats,
                    "settings": settings
                }

        except Exception as e:
            logger.error(f"查询用户完整信息失败: {e}")
            return None

    def create_user(self, user_id: UUID, nickname: Optional[str] = None) -> User:
        """
        创建用户

        Args:
            user_id (UUID): 用户ID（来自认证域）
            nickname (Optional[str]): 用户昵称

        Returns:
            User: 创建的用户实体

        Raises:
            Exception: 创建用户失败
        """
        try:
            # 如果没有提供昵称，使用默认昵称
            if not nickname:
                nickname = f"用户_{str(user_id)[:8]}"

            user = User(
                user_id=user_id,
                nickname=nickname
            )

            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

            # 初始化用户统计
            self.initialize_user_stats(user_id)

            logger.info(f"创建用户成功: {user_id}")
            return user

        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            self.session.rollback()
            raise

    def update_user(self, user_id: UUID, updates: Dict[str, Any]) -> Optional[User]:
        """
        更新用户信息

        Args:
            user_id (UUID): 用户ID
            updates (Dict[str, Any]): 更新的字段

        Returns:
            Optional[User]: 更新后的用户实体

        Raises:
            Exception: 更新用户失败
        """
        try:
            statement = update(User).where(User.user_id == user_id)

            # 更新时间
            updates["updated_at"] = datetime.now(timezone.utc)

            # 执行更新
            result = self.session.execute(statement, updates)

            if result.rowcount == 0:
                logger.warning(f"用户不存在: {user_id}")
                return None

            self.session.commit()

            # 返回更新后的用户
            return self.get_by_id(user_id)

        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            self.session.rollback()
            raise

    def get_user_settings(self, user_id: UUID) -> Optional[UserSettings]:
        """
        获取用户设置

        Args:
            user_id (UUID): 用户ID

        Returns:
            Optional[UserSettings]: 用户设置
        """
        try:
            statement = select(UserSettings).where(UserSettings.user_id == user_id)
            settings = self.session.execute(statement).first()
            return settings
        except Exception as e:
            logger.error(f"获取用户设置失败: {e}")
            return None

    def create_user_settings(self, user_id: UUID) -> UserSettings:
        """
        创建用户设置（默认值）

        Args:
            user_id (UUID): 用户ID

        Returns:
            UserSettings: 创建的用户设置
        """
        try:
            settings = UserSettings(user_id=user_id)
            self.session.add(settings)
            self.session.commit()
            self.session.refresh(settings)
            return settings
        except Exception as e:
            logger.error(f"创建用户设置失败: {e}")
            self.session.rollback()
            raise

    def get_user_stats(self, user_id: UUID) -> Optional[UserStats]:
        """
        获取用户统计

        Args:
            user_id (UUID): 用户ID

        Returns:
            Optional[UserStats]: 用户统计
        """
        try:
            statement = select(UserStats).where(UserStats.user_id == user_id)
            stats = self.session.execute(statement).first()
            return stats
        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return None

    def initialize_user_stats(self, user_id: UUID) -> UserStats:
        """
        初始化用户统计

        Args:
            user_id (UUID): 用户ID

        Returns:
            UserStats: 创建的用户统计
        """
        try:
            stats = UserStats(
                user_id=user_id,
                tasks_completed=0,
                total_points=0,
                login_count=0,
                last_active_at=datetime.now(timezone.utc)
            )
            self.session.add(stats)
            self.session.commit()
            self.session.refresh(stats)
            return stats
        except Exception as e:
            logger.error(f"初始化用户统计失败: {e}")
            self.session.rollback()
            raise

    def update_last_active(self, user_id: UUID) -> bool:
        """
        更新用户最后活跃时间

        Args:
            user_id (UUID): 用户ID

        Returns:
            bool: 更新成功返回True
        """
        try:
            statement = update(UserStats).where(
                UserStats.user_id == user_id
            ).values(
                last_active_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            result = self.session.execute(statement)
            self.session.commit()

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"更新最后活跃时间失败: {e}")
            return False

    def user_exists(self, user_id: UUID) -> bool:
        """
        检查用户是否存在

        Args:
            user_id (UUID): 用户ID

        Returns:
            bool: 存在返回True，不存在返回False
        """
        return self.get_by_id(user_id) is not None