"""
User领域Repository层 - UUID类型安全实现

提供统一的用户数据访问接口，在Repository层处理UUID类型转换。
Service层只需要处理UUID对象，Repository层负责与数据库的交互。

Repository职责:
- UserRepository: 管理用户实体的基础CRUD操作，处理UUID转换
- 封装AuthRepository操作，提供用户领域的统一接口

设计原则:
- 类型隔离：Service层使用UUID，Repository层处理字符串转换
- 统一接口：提供一致的用户操作方法
- 错误处理：封装数据库操作异常
- 复用AuthRepository：避免重复实现基础认证功能

作者：TaKeKe团队
版本：2.0.0 - UUID架构统一版
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlmodel import Session, select
from src.domains.auth.repository import AuthRepository
from src.domains.auth.models import Auth
from src.utils.uuid_helpers import uuid_converter

logger = logging.getLogger(__name__)


class UserRepository:
    """
    用户Repository类

    封装AuthRepository，提供用户领域的统一接口。
    Repository层负责UUID转换，Service层只处理UUID对象。
    """

    def __init__(self, session: Session):
        self.session = session
        self.auth_repo = AuthRepository(session)

    def get_by_id(self, user_id: UUID) -> Optional[Auth]:
        """
        根据ID获取用户

        注意：Repository层接受UUID参数，内部转换为字符串进行数据库查询。

        Args:
            user_id (UUID): 用户ID（UUID对象）

        Returns:
            Optional[Auth]: 用户实体，如果不存在则返回None

        Raises:
            Exception: 数据库操作失败
        """
        try:
            # 转换UUID为字符串格式进行数据库查询
            user_id_str = uuid_converter.to_db_format(user_id)

            # 调用AuthRepository进行查询
            user = self.auth_repo.get_by_id(user_id)

            logger.debug(f"查询用户: {user_id_str}, 结果: {user is not None}")
            return user

        except Exception as e:
            logger.error(f"查询用户失败: {e}")
            raise Exception(f"查询用户失败: {str(e)}")

    def get_by_wechat_openid(self, wechat_openid: str) -> Optional[Auth]:
        """
        根据微信OpenID获取用户

        Args:
            wechat_openid (str): 微信OpenID

        Returns:
            Optional[Auth]: 用户实体，如果不存在则返回None

        Raises:
            Exception: 数据库操作失败
        """
        try:
            user = self.auth_repo.get_by_wechat_openid(wechat_openid)
            logger.debug(f"通过微信OpenID查询用户: {wechat_openid}, 结果: {user is not None}")
            return user

        except Exception as e:
            logger.error(f"通过微信OpenID查询用户失败: {e}")
            raise Exception(f"查询用户失败: {str(e)}")

    def create_guest_user(self) -> Auth:
        """
        创建游客用户

        Returns:
            Auth: 创建的游客用户实体

        Raises:
            Exception: 创建用户失败
        """
        try:
            user = self.auth_repo.create_guest_user()
            logger.info(f"创建游客用户成功: {user.id}")
            return user

        except Exception as e:
            logger.error(f"创建游客用户失败: {e}")
            raise Exception(f"创建游客用户失败: {str(e)}")

    def create_wechat_user(self, wechat_openid: str, nickname: Optional[str] = None) -> Auth:
        """
        创建微信用户

        Args:
            wechat_openid (str): 微信OpenID
            nickname (Optional[str]): 用户昵称

        Returns:
            Auth: 创建的微信用户实体

        Raises:
            Exception: 创建用户失败
        """
        try:
            user = self.auth_repo.create_wechat_user(wechat_openid, nickname)
            logger.info(f"创建微信用户成功: {user.id}")
            return user

        except Exception as e:
            logger.error(f"创建微信用户失败: {e}")
            raise Exception(f"创建微信用户失败: {str(e)}")

    def upgrade_guest_to_wechat(self, user_id: UUID, wechat_openid: str, nickname: Optional[str] = None) -> bool:
        """
        将游客用户升级为微信用户

        Args:
            user_id (UUID): 用户ID
            wechat_openid (str): 微信OpenID
            nickname (Optional[str]): 用户昵称

        Returns:
            bool: 升级成功返回True，失败返回False

        Raises:
            Exception: 升级用户失败
        """
        try:
            # 转换UUID为字符串格式
            user_id_str = uuid_converter.to_db_format(user_id)

            # 调用AuthRepository进行升级
            success = self.auth_repo.upgrade_guest_to_wechat(user_id, wechat_openid, nickname)

            if success:
                logger.info(f"游客用户升级成功: {user_id_str} -> 微信用户")
            else:
                logger.warning(f"游客用户升级失败: {user_id_str}")

            return success

        except Exception as e:
            logger.error(f"升级游客用户失败: {e}")
            raise Exception(f"升级用户失败: {str(e)}")

    def update_last_login(self, user_id: UUID) -> bool:
        """
        更新用户最后登录时间

        Args:
            user_id (UUID): 用户ID

        Returns:
            bool: 更新成功返回True，失败返回False

        Raises:
            Exception: 更新失败
        """
        try:
            # 转换UUID为字符串格式
            user_id_str = uuid_converter.to_db_format(user_id)

            # 调用AuthRepository进行更新
            success = self.auth_repo.update_last_login(user_id)

            if success:
                logger.debug(f"更新用户最后登录时间成功: {user_id_str}")
            else:
                logger.warning(f"更新用户最后登录时间失败: {user_id_str}")

            return success

        except Exception as e:
            logger.error(f"更新用户最后登录时间失败: {e}")
            raise Exception(f"更新用户登录时间失败: {str(e)}")

    def user_exists(self, user_id: UUID) -> bool:
        """
        检查用户是否存在

        Args:
            user_id (UUID): 用户ID

        Returns:
            bool: 存在返回True，不存在返回False

        Raises:
            Exception: 查询失败
        """
        try:
            user = self.get_by_id(user_id)
            return user is not None

        except Exception as e:
            logger.error(f"检查用户存在性失败: {e}")
            raise Exception(f"检查用户存在性失败: {str(e)}")

    def get_user_count(self) -> int:
        """
        获取用户总数

        Returns:
            int: 用户总数

        Raises:
            Exception: 查询失败
        """
        try:
            # 查询Auth表中的用户总数
            statement = select(Auth)
            result = self.session.exec(statement).all()
            count = len(result)

            logger.debug(f"获取用户总数: {count}")
            return count

        except Exception as e:
            logger.error(f"获取用户总数失败: {e}")
            raise Exception(f"获取用户总数失败: {str(e)}")