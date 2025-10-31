"""
聊天会话仓储层

提供本地SQLite数据库的会话数据访问操作。

设计原则：
1. 类型安全：使用SQLModel确保数据类型安全
2. 错误处理：完善的异常处理和日志记录
3. 性能优化：合理的索引和查询优化
4. 用户隔离：确保用户只能访问自己的数据

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from typing import List, Optional
from sqlmodel import Session, select, delete

from .models import ChatSession, get_session
from .utils import generate_session_id, generate_default_title

logger = logging.getLogger(__name__)


class ChatRepository:
    """聊天会话数据访问层"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        初始化仓储

        Args:
            db_session: 数据库会话，如果为None则自动创建
        """
        self.session = db_session or get_session()

    def create_session(self, user_id: str, title: Optional[str] = None) -> ChatSession:
        """
        创建新会话

        Args:
            user_id: 用户ID
            title: 会话标题，如果为None则使用默认标题

        Returns:
            ChatSession: 创建的会话对象

        Raises:
            Exception: 创建失败时抛出异常
        """
        try:
            # 生成session_id
            session_id = generate_session_id()

            # 如果没有标题，使用默认标题
            if not title:
                title = generate_default_title()

            # 创建会话对象
            chat_session = ChatSession(
                user_id=user_id,
                session_id=session_id,
                title=title
            )

            # 保存到数据库
            self.session.add(chat_session)
            self.session.commit()
            self.session.refresh(chat_session)

            logger.info(f"创建聊天会话成功: user_id={user_id}, session_id={session_id}")
            return chat_session

        except Exception as e:
            self.session.rollback()
            logger.error(f"创建聊天会话失败: user_id={user_id}, error={e}")
            raise

    def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """
        获取用户的所有会话

        Args:
            user_id: 用户ID

        Returns:
            List[ChatSession]: 会话列表，按创建时间倒序排列
        """
        try:
            statement = select(ChatSession).where(
                ChatSession.user_id == user_id
            ).order_by(ChatSession.created_at.desc())

            sessions = self.session.exec(statement).all()
            logger.info(f"获取用户会话列表: user_id={user_id}, count={len(sessions)}")
            return list(sessions)

        except Exception as e:
            logger.error(f"获取用户会话列表失败: user_id={user_id}, error={e}")
            return []

    def get_session_by_id(self, session_id: str, user_id: str) -> Optional[ChatSession]:
        """
        根据session_id获取会话（带用户权限验证）

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            Optional[ChatSession]: 会话对象，如果不存在或无权限则返回None
        """
        try:
            statement = select(ChatSession).where(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            )

            session = self.session.exec(statement).first()
            logger.info(f"查询会话: session_id={session_id}, user_id={user_id}, found={session is not None}")
            return session

        except Exception as e:
            logger.error(f"查询会话失败: session_id={session_id}, user_id={user_id}, error={e}")
            return None

    def delete_session(self, session_id: str, user_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            bool: 删除是否成功
        """
        try:
            # 先验证会话是否存在且属于该用户
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                logger.warning(f"删除会话失败，会话不存在或无权限: session_id={session_id}, user_id={user_id}")
                return False

            # 删除会话
            statement = delete(ChatSession).where(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            )

            result = self.session.exec(statement)
            self.session.commit()

            deleted = result.rowcount > 0
            logger.info(f"删除会话: session_id={session_id}, user_id={user_id}, success={deleted}")
            return deleted

        except Exception as e:
            self.session.rollback()
            logger.error(f"删除会话失败: session_id={session_id}, user_id={user_id}, error={e}")
            return False

    def update_session_timestamp(self, session_id: str, user_id: str) -> bool:
        """
        更新会话时间戳

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            bool: 更新是否成功
        """
        try:
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                return False

            # 更新时间戳
            from datetime import datetime, timezone
            session.updated_at = datetime.now(timezone.utc)

            self.session.add(session)
            self.session.commit()

            logger.info(f"更新会话时间戳: session_id={session_id}, user_id={user_id}")
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"更新会话时间戳失败: session_id={session_id}, user_id={user_id}, error={e}")
            return False

    def close(self):
        """关闭数据库会话"""
        if self.session:
            self.session.close()