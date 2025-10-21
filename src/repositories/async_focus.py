"""
异步专注Repository实现

提供专注相关的异步数据访问层操作，封装专注业务逻辑查询。
继承自AsyncBaseRepository，专注于专注特有的业务场景。

功能特性：
1. 异步专注会话查询（按用户、状态、时间范围查询）
2. 异步专注会话状态管理（开始、暂停、完成、取消）
3. 异步专注统计和分析（专注时长、效率分析等）
4. 异步业务逻辑封装（状态验证、时间计算等）
5. 异步专注记录管理（创建、更新、删除专注记录）

设计原则：
1. 单一责任：专注于专注相关的数据访问
2. 异步优先：所有数据库操作都是异步的
3. 查询封装：复杂业务查询封装在Repository方法中
4. 异常统一：使用统一的异常处理机制
5. 类型安全：强类型参数和返回值
6. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建异步专注Repository
    >>> focus_repo = AsyncFocusRepository(async_session)
    >>>
    >>> # 异步查找用户的所有专注会话
    >>> sessions = await focus_repo.find_by_user("user123")
    >>>
    >>> # 异步开始专注会话
    >>> active_session = await focus_repo.start_focus_session("user123", 25)
    >>>
    >>> # 异步完成专注会话
    >>> completed_session = await focus_repo.complete_focus_session("session123")
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError

# 导入异步基础Repository和异常类
from src.repositories.async_base import (
    AsyncBaseRepository,
    AsyncRepositoryError,
    AsyncRepositoryValidationError,
    AsyncRepositoryNotFoundError
)
from src.models.focus import FocusSession
from src.models.enums import FocusStatus


class AsyncFocusRepository(AsyncBaseRepository[FocusSession]):
    """
    异步专注Repository类

    提供专注相关的异步数据库操作，封装专注业务逻辑查询。
    继承自AsyncBaseRepository，专注于专注特有的业务场景。

    Attributes:
        session: SQLAlchemy异步会话对象
        model: FocusSession模型类
    """

    def __init__(self, session: AsyncSession):
        """
        初始化异步专注Repository

        Args:
            session: SQLAlchemy异步会话对象
        """
        super().__init__(session, FocusSession)

    async def find_by_user(
        self,
        user_id: str,
        status: Optional[FocusStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[FocusSession]:
        """
        查找用户的所有专注会话

        Args:
            user_id: 用户ID
            status: 专注状态过滤
            start_date: 开始日期过滤
            end_date: 结束日期过滤
            limit: 结果数量限制

        Returns:
            专注会话列表

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 构建查询
            statement = select(FocusSession).where(FocusSession.user_id == user_id)

            # 状态过滤
            if status:
                statement = statement.where(FocusSession.status == status)

            # 日期范围过滤
            if start_date:
                statement = statement.where(FocusSession.started_at >= start_date)
            if end_date:
                statement = statement.where(FocusSession.started_at <= end_date)

            # 按开始时间倒序排列
            statement = statement.order_by(desc(FocusSession.started_at))

            # 限制结果数量
            if limit:
                statement = statement.limit(limit)

            # 执行查询
            result = await self.session.exec(statement)
            sessions = list(result.all())

            return sessions

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询用户专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询用户专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def start_focus_session(
        self,
        user_id: str,
        planned_duration_minutes: int,
        task_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> FocusSession:
        """
        开始专注会话

        Args:
            user_id: 用户ID
            planned_duration_minutes: 计划专注时长（分钟）
            task_id: 关联任务ID（可选）
            notes: 专注备注（可选）

        Returns:
            创建的专注会话对象

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")
            if not planned_duration_minutes or planned_duration_minutes <= 0:
                raise AsyncRepositoryValidationError("计划专注时长必须大于0")

            # 检查是否有进行中的专注会话
            active_session = await self.find_active_session(user_id)
            if active_session:
                raise AsyncRepositoryValidationError(
                    f"用户已有进行中的专注会话: {active_session.id}"
                )

            now = datetime.now(timezone.utc)
            session_data = {
                "user_id": user_id,
                "task_id": task_id,
                "planned_duration_minutes": planned_duration_minutes,
                "status": FocusStatus.ACTIVE,
                "started_at": now,
                "notes": notes
            }

            return await self.create(session_data)

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"开始专注会话失败: {str(e)}",
                operation="create",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"开始专注会话时发生未知错误: {str(e)}",
                operation="create",
                model_name=self.model_name
            )

    async def find_active_session(self, user_id: str) -> Optional[FocusSession]:
        """
        查找用户当前活跃的专注会话

        Args:
            user_id: 用户ID

        Returns:
            活跃的专注会话，不存在时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.status == FocusStatus.ACTIVE
                )
            ).order_by(desc(FocusSession.started_at))

            result = await self.session.exec(statement)
            return result.first()

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询活跃专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询活跃专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def pause_focus_session(self, session_id: str) -> Optional[FocusSession]:
        """
        暂停专注会话

        Args:
            session_id: 专注会话ID

        Returns:
            暂停后的专注会话，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")

            # 查找会话
            session = await self.get_by_id(session_id)
            if not session:
                return None

            if session.status != FocusStatus.ACTIVE:
                raise AsyncRepositoryValidationError("只有活跃的会话才能暂停")

            # 计算当前专注时长
            now = datetime.now(timezone.utc)
            current_duration_seconds = int((now - session.started_at).total_seconds())

            update_data = {
                "status": FocusStatus.PAUSED,
                "paused_at": now,
                "actual_duration_seconds": current_duration_seconds,
                "updated_at": now
            }

            return await self.update(session_id, update_data)

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"暂停专注会话失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"暂停专注会话时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def resume_focus_session(self, session_id: str) -> Optional[FocusSession]:
        """
        恢复专注会话

        Args:
            session_id: 专注会话ID

        Returns:
            恢复后的专注会话，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")

            # 查找会话
            session = await self.get_by_id(session_id)
            if not session:
                return None

            if session.status != FocusStatus.PAUSED:
                raise AsyncRepositoryValidationError("只有暂停的会话才能恢复")

            now = datetime.now(timezone.utc)
            update_data = {
                "status": FocusStatus.ACTIVE,
                "resumed_at": now,
                "updated_at": now
            }

            return await self.update(session_id, update_data)

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"恢复专注会话失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"恢复专注会话时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def complete_focus_session(self, session_id: str) -> Optional[FocusSession]:
        """
        完成专注会话

        Args:
            session_id: 专注会话ID

        Returns:
            完成后的专注会话，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")

            # 查找会话
            session = await self.get_by_id(session_id)
            if not session:
                return None

            if session.status == FocusStatus.COMPLETED:
                return session  # 已经完成

            if session.status not in [FocusStatus.ACTIVE, FocusStatus.PAUSED]:
                raise AsyncRepositoryValidationError("只有活跃或暂停的会话才能完成")

            # 计算实际专注时长
            now = datetime.now(timezone.utc)
            if session.status == FocusStatus.ACTIVE:
                # 从活跃状态完成
                actual_duration = int((now - session.started_at).total_seconds())
            else:
                # 从暂停状态完成，使用已有时长
                actual_duration = session.actual_duration_seconds or 0

            update_data = {
                "status": FocusStatus.COMPLETED,
                "completed_at": now,
                "actual_duration_seconds": actual_duration,
                "updated_at": now
            }

            return await self.update(session_id, update_data)

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"完成专注会话失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"完成专注会话时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def cancel_focus_session(self, session_id: str, reason: Optional[str] = None) -> Optional[FocusSession]:
        """
        取消专注会话

        Args:
            session_id: 专注会话ID
            reason: 取消原因

        Returns:
            取消后的专注会话，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")

            # 查找会话
            session = await self.get_by_id(session_id)
            if not session:
                return None

            if session.status in [FocusStatus.COMPLETED, FocusStatus.CANCELLED]:
                return session  # 已经是终态

            # 计算实际专注时长
            now = datetime.now(timezone.utc)
            if session.status == FocusStatus.ACTIVE:
                actual_duration = int((now - session.started_at).total_seconds())
            else:
                actual_duration = session.actual_duration_seconds or 0

            update_data = {
                "status": FocusStatus.CANCELLED,
                "cancelled_at": now,
                "actual_duration_seconds": actual_duration,
                "cancel_reason": reason,
                "updated_at": now
            }

            return await self.update(session_id, update_data)

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"取消专注会话失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"取消专注会话时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def get_focus_statistics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取用户专注统计信息

        Args:
            user_id: 用户ID
            start_date: 统计开始日期
            end_date: 统计结束日期

        Returns:
            包含专注统计信息的字典

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 基础过滤条件
            base_filter = FocusSession.user_id == user_id

            # 日期范围过滤
            if start_date:
                base_filter = and_(base_filter, FocusSession.started_at >= start_date)
            if end_date:
                base_filter = and_(base_filter, FocusSession.started_at <= end_date)

            # 总会话数
            total_result = await self.session.exec(
                select(func.count()).select_from(FocusSession).where(base_filter)
            )
            total_sessions = total_result.scalar() or 0

            # 按状态统计
            status_result = await self.session.exec(
                select(FocusSession.status, func.count()).select_from(FocusSession)
                .where(base_filter).group_by(FocusSession.status)
            )
            status_counts = dict(status_result.all())

            # 总专注时长（秒）
            duration_result = await self.session.exec(
                select(func.sum(FocusSession.actual_duration_seconds)).select_from(FocusSession)
                .where(and_(base_filter, FocusSession.actual_duration_seconds.isnot(None)))
            )
            total_duration = duration_result.scalar() or 0

            # 平均专注时长
            completed_sessions = status_counts.get(FocusStatus.COMPLETED, 0)
            avg_duration = (total_duration / completed_sessions) if completed_sessions > 0 else 0

            # 今日专注统计
            today = datetime.now(timezone.utc).date()
            today_filter = and_(base_filter, func.date(FocusSession.started_at) == today)

            today_sessions_result = await self.session.exec(
                select(func.count()).select_from(FocusSession).where(today_filter)
            )
            today_sessions = today_sessions_result.scalar() or 0

            today_duration_result = await self.session.exec(
                select(func.sum(FocusSession.actual_duration_seconds)).select_from(FocusSession)
                .where(and_(today_filter, FocusSession.actual_duration_seconds.isnot(None)))
            )
            today_duration = today_duration_result.scalar() or 0

            # 本周专注统计
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            week_filter = and_(base_filter, FocusSession.started_at >= week_ago)

            week_sessions_result = await self.session.exec(
                select(func.count()).select_from(FocusSession).where(week_filter)
            )
            week_sessions = week_sessions_result.scalar() or 0

            week_duration_result = await self.session.exec(
                select(func.sum(FocusSession.actual_duration_seconds)).select_from(FocusSession)
                .where(and_(week_filter, FocusSession.actual_duration_seconds.isnot(None)))
            )
            week_duration = week_duration_result.scalar() or 0

            return {
                "total_sessions": total_sessions,
                "by_status": status_counts,
                "total_duration_seconds": total_duration,
                "total_duration_minutes": total_duration // 60,
                "average_duration_seconds": int(avg_duration),
                "average_duration_minutes": int(avg_duration // 60),
                "today": {
                    "sessions": today_sessions,
                    "duration_seconds": today_duration,
                    "duration_minutes": today_duration // 60
                },
                "week": {
                    "sessions": week_sessions,
                    "duration_seconds": week_duration,
                    "duration_minutes": week_duration // 60
                },
                "completion_rate": (
                    (status_counts.get(FocusStatus.COMPLETED, 0) / total_sessions * 100)
                    if total_sessions > 0 else 0
                )
            }

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"获取专注统计失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取专注统计时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def __repr__(self) -> str:
        """
        返回Repository的字符串表示

        Returns:
            Repository的描述信息
        """
        return f"{self.__class__.__name__}(model={self.model_name})"


# 导出相关类
__all__ = [
    "AsyncFocusRepository"
]