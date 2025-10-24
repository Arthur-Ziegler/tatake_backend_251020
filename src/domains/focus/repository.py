"""
Focus领域Repository层

提供FocusSession实体的数据访问操作，封装所有数据库相关的逻辑。

Repository职责：
1. 封装数据库操作细节
2. 提供类型安全的数据访问方法
3. 处理自动关闭逻辑
4. 管理会话查询

设计原则：
1. 极简化：只提供必要的数据操作方法
2. 自动化：内置自动关闭逻辑，简化业务层处理
3. 类型安全：使用SQLModel确保类型安全
4. 性能优化：合理使用索引和查询

核心方法：
- create(): 创建会话（包含自动关闭逻辑）
- get_by_id(): 根据ID获取会话
- get_active_session(): 获取用户的进行中会话
- complete_session(): 完成会话
- get_user_sessions(): 获取用户会话列表

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlmodel import select, update, func, and_, desc
from sqlmodel import Session

from .models import FocusSession

# 配置日志
logger = logging.getLogger(__name__)


class FocusRepository:
    """
    专注会话数据访问Repository

    提供极简的会话数据操作，内置自动关闭逻辑：
    - 创建新会话时自动关闭用户未完成的会话
    - 提供便捷的活跃会话查询方法
    - 支持基本的会话生命周期管理
    """

    def __init__(self, session: Session):
        """
        初始化Repository

        Args:
            session: SQLModel数据库会话
        """
        self.session = session

    def create(self, focus_session: FocusSession) -> FocusSession:
        """
        创建新的专注会话

        自动关闭逻辑：
        1. 查询用户当前未完成的会话
        2. 如果存在，设置其end_time为当前时间
        3. 创建新的会话

        Args:
            focus_session: 要创建的会话对象

        Returns:
            创建后的会话对象

        Raises:
            Exception: 数据库操作失败
        """
        try:
            # 查找并关闭用户未完成的会话
            active_session = self.get_active_session(focus_session.user_id)
            if active_session:
                active_session.end_time = datetime.now(timezone.utc)
                self.session.add(active_session)
                logger.info(f"自动关闭会话 {active_session.id} for user {focus_session.user_id}")

            # 创建新会话
            self.session.add(focus_session)
            self.session.commit()
            self.session.refresh(focus_session)

            logger.info(f"创建新会话 {focus_session.id} for user {focus_session.user_id}")
            return focus_session

        except Exception as e:
            self.session.rollback()
            logger.error(f"创建会话失败: {e}")
            raise

    def get_by_id(self, session_id: str) -> Optional[FocusSession]:
        """
        根据ID获取会话

        Args:
            session_id: 会话ID

        Returns:
            会话对象或None
        """
        try:
            statement = select(FocusSession).where(FocusSession.id == session_id)
            return self.session.execute(statement).first()
        except Exception as e:
            logger.error(f"查询会话失败 {session_id}: {e}")
            return None

    def get_active_session(self, user_id: str) -> Optional[FocusSession]:
        """
        获取用户的进行中会话

        查询end_time为NULL的会话，表示正在进行中。

        Args:
            user_id: 用户ID

        Returns:
            进行中的会话对象或None
        """
        try:
            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.end_time.is_(None)
                )
            )
            return self.session.execute(statement).first()
        except Exception as e:
            logger.error(f"查询活跃会话失败 {user_id}: {e}")
            return None

    def complete_session(self, session_id: str, user_id: str) -> Optional[FocusSession]:
        """
        完成会话

        设置会话的end_time为当前时间。

        Args:
            session_id: 会话ID
            user_id: 用户ID（用于权限验证）

        Returns:
            完成后的会话对象或None
        """
        try:
            # 获取会话并验证权限
            session = self.get_by_id(session_id)
            if not session or session.user_id != user_id:
                logger.warning(f"会话不存在或无权限 {session_id} for user {user_id}")
                return None

            # 完成会话
            session.end_time = datetime.now(timezone.utc)
            self.session.add(session)
            self.session.commit()
            self.session.refresh(session)

            logger.info(f"完成会话 {session_id} for user {user_id}")
            return session

        except Exception as e:
            self.session.rollback()
            logger.error(f"完成会话失败 {session_id}: {e}")
            return None

    def get_user_sessions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        session_type: Optional[str] = None
    ) -> tuple[List[FocusSession], int]:
        """
        获取用户会话列表

        支持分页和会话类型过滤，按时间倒序排列。

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页大小
            session_type: 会话类型过滤（可选）

        Returns:
            (会话列表, 总记录数)
        """
        try:
            # 构建查询条件
            conditions = [FocusSession.user_id == user_id]
            if session_type:
                conditions.append(FocusSession.session_type == session_type)

            # 查询总数
            count_statement = select(func.count(FocusSession.id)).where(and_(*conditions))
            total = self.session.execute(count_statement).scalar_one()

            # 查询分页数据
            offset = (page - 1) * page_size
            statement = (
                select(FocusSession)
                .where(and_(*conditions))
                .order_by(desc(FocusSession.start_time))
                .offset(offset)
                .limit(page_size)
            )
            sessions = self.session.execute(statement).scalars().all()

            logger.info(f"查询用户会话列表 {user_id}: {len(sessions)}/{total}")
            return list(sessions), total

        except Exception as e:
            logger.error(f"查询用户会话列表失败 {user_id}: {e}")
            return [], 0

    def get_sessions_by_task(
        self,
        user_id: str,
        task_id: str
    ) -> List[FocusSession]:
        """
        获取特定任务的会话列表

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            该任务的会话列表
        """
        try:
            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.task_id == task_id
                )
            ).order_by(desc(FocusSession.start_time))
            sessions = self.session.execute(statement).scalars().all()
            return list(sessions)

        except Exception as e:
            logger.error(f"查询任务会话失败 {user_id}/{task_id}: {e}")
            return []