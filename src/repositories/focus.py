"""
专注Repository实现

提供专注相关的数据访问层操作，封装专注业务逻辑查询。
继承自BaseRepository，专注于专注系统特有的业务场景。

功能特性：
1. 专注会话管理（开始、结束、暂停、恢复、取消会话）
2. 专注会话查询（按用户、类型、状态、时间范围查询）
3. 专注统计分析（总时长、完成率、日均专注等）
4. 专注模板管理（创建、应用、删除模板）
5. 休息记录管理（添加、查询、完成休息）

设计原则：
1. 单一责任：专注于专注相关的数据访问
2. 查询封装：复杂业务查询封装在Repository方法中
3. 异常统一：使用统一的异常处理机制
4. 类型安全：强类型参数和返回值
5. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建专注Repository
    >>> focus_repo = FocusRepository(session)
    >>>
    >>> # 开始专注会话
    >>> active_session = focus_repo.start_focus_session("user123", 25)
    >>>
    >>> # 完成专注会话
    >>> completed_session = focus_repo.complete_session(active_session.id)
    >>>
    >>> # 获取用户专注统计
    >>> stats = focus_repo.get_user_focus_statistics("user123")
    >>> print(f"今日专注: {stats['today_minutes']}分钟")
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlmodel import Session, select, and_, or_, func, desc, text
from sqlalchemy.exc import SQLAlchemyError

# 导入基础Repository和异常类
from src.repositories.base import BaseRepository, RepositoryError, RepositoryValidationError, RepositoryNotFoundError
from src.models.focus import FocusSession, FocusSessionBreak, FocusSessionTemplate
from src.models.enums import SessionType


class FocusRepository(BaseRepository[FocusSession]):
    """
    专注Repository类

    提供专注相关的数据库操作，封装专注业务逻辑查询。
    继承自BaseRepository，专注于专注系统特有的业务场景。

    Attributes:
        session: SQLAlchemy会话对象
        model: FocusSession模型类
    """

    def __init__(self, session: Session):
        """
        初始化FocusRepository

        Args:
            session: SQLAlchemy会话对象
        """
        super().__init__(session, FocusSession)

    # ==================== 专注会话查询方法 ====================

    def find_by_user(self, user_id: str) -> List[FocusSession]:
        """
        根据用户ID查找专注会话

        Args:
            user_id: 用户ID

        Returns:
            List[FocusSession]: 用户的专注会话列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> focus_repo = FocusRepository(session)
            >>> sessions = focus_repo.find_by_user("user123")
            >>> print(f"用户共有 {len(sessions)} 个专注会话")
            "用户共有 10 个专注会话"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 构建查询：查找用户的所有专注会话，按创建时间倒序
            statement = select(FocusSession).where(
                FocusSession.user_id == user_id
            ).order_by(FocusSession.created_at.desc())

            # 执行查询
            sessions = self.session.exec(statement).all()

            return list(sessions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据用户ID查找专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据用户ID查找专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_session_type(self, user_id: str, session_type: SessionType) -> List[FocusSession]:
        """
        根据会话类型查找专注会话

        Args:
            user_id: 用户ID
            session_type: 会话类型

        Returns:
            List[FocusSession]: 指定类型的专注会话列表

        Raises:
            RepositoryValidationError: 参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(session_type, SessionType):
                raise RepositoryValidationError("会话类型参数必须是SessionType枚举类型")

            # 构建查询
            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.session_type == session_type
                )
            ).order_by(FocusSession.created_at.desc())

            # 执行查询
            sessions = self.session.exec(statement).all()

            return list(sessions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据会话类型查找专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据会话类型查找专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_active_sessions(self, user_id: str) -> List[FocusSession]:
        """
        查找活跃的专注会话（已开始但未结束）

        Args:
            user_id: 用户ID

        Returns:
            List[FocusSession]: 活跃的专注会话列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 构建查询：查找已开始但未结束的会话
            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.started_at.isnot(None),
                    FocusSession.ended_at.is_(None),
                    FocusSession.is_completed == False
                )
            ).order_by(FocusSession.started_at.desc())

            # 执行查询
            sessions = self.session.exec(statement).all()

            return list(sessions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找活跃专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找活跃专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_completed_sessions(self, user_id: str, days: int = 30) -> List[FocusSession]:
        """
        查找已完成的专注会话

        Args:
            user_id: 用户ID
            days: 查找最近多少天内的会话，默认30天

        Returns:
            List[FocusSession]: 已完成的专注会话列表

        Raises:
            RepositoryValidationError: 参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(days, int) or days <= 0:
                raise RepositoryValidationError("天数参数必须是正整数")

            # 计算时间阈值
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 构建查询
            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.is_completed == True,
                    FocusSession.ended_at >= threshold_date
                )
            ).order_by(desc(FocusSession.ended_at))

            # 执行查询
            sessions = self.session.exec(statement).all()

            return list(sessions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找已完成专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找已完成专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_user_today_sessions(self, user_id: str) -> List[FocusSession]:
        """
        查找用户今日的专注会话

        Args:
            user_id: 用户ID

        Returns:
            List[FocusSession]: 今日专注会话列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 获取今日开始时间（UTC时区）
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            # 构建查询
            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.created_at >= today_start
                )
            ).order_by(FocusSession.created_at.desc())

            # 执行查询
            sessions = self.session.exec(statement).all()

            return list(sessions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找用户今日专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找用户今日专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_user_sessions_by_date_range(self, user_id: str, start_date: datetime, end_date: datetime) -> List[FocusSession]:
        """
        查找用户指定日期范围内的专注会话

        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[FocusSession]: 指定日期范围内的专注会话列表

        Raises:
            RepositoryValidationError: 参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
                raise RepositoryValidationError("开始日期和结束日期参数必须是datetime类型")

            if start_date >= end_date:
                raise RepositoryValidationError("开始日期必须早于结束日期")

            # 确保时区一致
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            # 构建查询
            statement = select(FocusSession).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.created_at >= start_date,
                    FocusSession.created_at <= end_date
                )
            ).order_by(FocusSession.created_at.desc())

            # 执行查询
            sessions = self.session.exec(statement).all()

            return list(sessions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找指定日期范围专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找指定日期范围专注会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    # ==================== 专注会话管理方法 ====================

    def start_focus_session(self, user_id: str, duration_minutes: int, task_id: str = None) -> FocusSession:
        """
        开始专注会话

        Args:
            user_id: 用户ID
            duration_minutes: 专注时长（分钟）
            task_id: 可选的关联任务ID

        Returns:
            FocusSession: 创建的专注会话

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时

        Example:
            >>> focus_repo = FocusRepository(session)
            >>> session = focus_repo.start_focus_session("user123", 25)
            >>> print(f"开始专注会话: {session.id}")
            "开始专注会话: 123e4567-e89b-12d3-a456-426614174000"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(duration_minutes, int) or duration_minutes <= 0:
                raise RepositoryValidationError("专注时长必须是正整数")

            if duration_minutes > 480:  # 最长8小时
                raise RepositoryValidationError("专注时长不能超过480分钟（8小时）")

            if task_id is not None and not isinstance(task_id, str):
                raise RepositoryValidationError("任务ID参数必须是字符串类型或None")

            # 创建专注会话数据
            session_data = {
                "session_type": SessionType.FOCUS,
                "duration_minutes": duration_minutes,
                "started_at": datetime.now(timezone.utc),
                "user_id": user_id,
                "task_id": task_id,
                "is_completed": False
            }

            # 使用基类的create方法
            return self.create(session_data)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"开始专注会话失败: {str(e)}",
                operation="create",
                model_name=self.model_name
            )

    def complete_session(self, session_id: str) -> FocusSession:
        """
        完成专注会话

        Args:
            session_id: 会话ID

        Returns:
            FocusSession: 完成后的专注会话

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryNotFoundError: 会话不存在时
            RepositoryError: 数据库操作错误时

        Example:
            >>> focus_repo = FocusRepository(session)
            >>> completed_session = focus_repo.complete_session("session123")
            >>> print(f"会话已完成: {completed_session.is_completed}")
            "会话已完成: True"
        """
        try:
            # 参数验证
            if not session_id or not isinstance(session_id, str):
                raise RepositoryValidationError("会话ID参数不能为空且必须是字符串类型")

            # 查找会话
            session = self.get_by_id(session_id)
            if session is None:
                raise RepositoryNotFoundError(f"未找到ID为 {session_id} 的专注会话")

            # 检查会话状态
            if session.is_completed:
                raise RepositoryValidationError(f"会话 {session_id} 已经完成，无需重复操作")

            if not session.started_at:
                raise RepositoryValidationError(f"会话 {session_id} 尚未开始，无法完成")

            # 计算实际专注时长
            now = datetime.now(timezone.utc)
            actual_duration = int((now - session.started_at).total_seconds() / 60)

            # 构建更新数据
            update_data = {
                "ended_at": now,
                "duration_minutes": actual_duration,
                "is_completed": True
            }

            # 更新会话
            return self.update(session_id, update_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"完成专注会话失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    def pause_session(self, session_id: str) -> FocusSession:
        """
        暂停专注会话

        Args:
            session_id: 会话ID

        Returns:
            FocusSession: 暂停后的专注会话

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryNotFoundError: 会话不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not session_id or not isinstance(session_id, str):
                raise RepositoryValidationError("会话ID参数不能为空且必须是字符串类型")

            # 查找会话
            session = self.get_by_id(session_id)
            if session is None:
                raise RepositoryNotFoundError(f"未找到ID为 {session_id} 的专注会话")

            # 检查会话状态
            if session.is_completed:
                raise RepositoryValidationError(f"会话 {session_id} 已完成，无法暂停")

            if session.ended_at:
                raise RepositoryValidationError(f"会话 {session_id} 已结束，无法暂停")

            # TODO: 这里可以添加暂停逻辑，比如记录暂停时间等
            # 目前简单返回会话，表示暂停成功

            return session

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"暂停专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def resume_session(self, session_id: str) -> FocusSession:
        """
        恢复专注会话

        Args:
            session_id: 会话ID

        Returns:
            FocusSession: 恢复后的专注会话

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryNotFoundError: 会话不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not session_id or not isinstance(session_id, str):
                raise RepositoryValidationError("会话ID参数不能为空且必须是字符串类型")

            # 查找会话
            session = self.get_by_id(session_id)
            if session is None:
                raise RepositoryNotFoundError(f"未找到ID为 {session_id} 的专注会话")

            # 检查会话状态
            if session.is_completed:
                raise RepositoryValidationError(f"会话 {session_id} 已完成，无法恢复")

            if session.ended_at:
                raise RepositoryValidationError(f"会话 {session_id} 已结束，无法恢复")

            # TODO: 这里可以添加恢复逻辑，比如调整开始时间等
            # 目前简单返回会话，表示恢复成功

            return session

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"恢复专注会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def cancel_session(self, session_id: str) -> FocusSession:
        """
        取消专注会话

        Args:
            session_id: 会话ID

        Returns:
            FocusSession: 取消后的专注会话

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryNotFoundError: 会话不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not session_id or not isinstance(session_id, str):
                raise RepositoryValidationError("会话ID参数不能为空且必须是字符串类型")

            # 查找会话
            session = self.get_by_id(session_id)
            if session is None:
                raise RepositoryNotFoundError(f"未找到ID为 {session_id} 的专注会话")

            # 检查会话状态
            if session.is_completed:
                raise RepositoryValidationError(f"会话 {session_id} 已完成，无法取消")

            # 构建更新数据
            update_data = {
                "ended_at": datetime.now(timezone.utc),
                "is_completed": False  # 取消的会话不算完成
            }

            # 更新会话
            return self.update(session_id, update_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"取消专注会话失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    # ==================== 专注统计方法 ====================

    def get_user_focus_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取用户专注统计信息

        Args:
            user_id: 用户ID
            days: 统计最近多少天，默认30天

        Returns:
            Dict[str, Any]: 专注统计信息字典

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(days, int) or days <= 0:
                raise RepositoryValidationError("天数参数必须是正整数")

            # 计算时间阈值
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 统计总专注时长（分钟）
            total_minutes_query = select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.is_completed == True,
                    FocusSession.ended_at >= threshold_date
                )
            )
            total_minutes = self.session.exec(total_minutes_query).one() or 0

            # 统计完成会话数
            completed_sessions_query = select(func.count(FocusSession.id)).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.is_completed == True,
                    FocusSession.ended_at >= threshold_date
                )
            )
            completed_sessions = self.session.exec(completed_sessions_query).one() or 0

            # 统计总会话数
            total_sessions_query = select(func.count(FocusSession.id)).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.created_at >= threshold_date
                )
            )
            total_sessions = self.session.exec(total_sessions_query).one() or 0

            # 统计今日专注时长
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_minutes_query = select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.is_completed == True,
                    FocusSession.ended_at >= today_start
                )
            )
            today_minutes = self.session.exec(today_minutes_query).one() or 0

            # 计算完成率
            completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0

            # 计算平均专注时长
            avg_duration = (total_minutes / completed_sessions) if completed_sessions > 0 else 0

            return {
                "total_focus_minutes": int(total_minutes),
                "completed_sessions": int(completed_sessions),
                "total_sessions": int(total_sessions),
                "completion_rate": round(completion_rate, 2),
                "today_minutes": int(today_minutes),
                "average_duration_minutes": round(avg_duration, 2),
                "statistics_days": days
            }

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取用户专注统计信息失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"获取用户专注统计信息时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def get_daily_focus_summary(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取用户每日专注摘要

        Args:
            user_id: 用户ID
            days: 获取最近多少天的摘要，默认7天

        Returns:
            List[Dict[str, Any]]: 每日专注摘要列表

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(days, int) or days <= 0:
                raise RepositoryValidationError("天数参数必须是正整数")

            daily_summaries = []

            # 逐日统计
            for i in range(days):
                date = datetime.now(timezone.utc).date() - timedelta(days=i)
                date_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
                date_end = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)

                # 统计当日专注时长
                daily_minutes_query = select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
                    and_(
                        FocusSession.user_id == user_id,
                        FocusSession.is_completed == True,
                        FocusSession.ended_at >= date_start,
                        FocusSession.ended_at <= date_end
                    )
                )
                daily_minutes = self.session.exec(daily_minutes_query).one() or 0

                # 统计当日完成会话数
                daily_sessions_query = select(func.count(FocusSession.id)).where(
                    and_(
                        FocusSession.user_id == user_id,
                        FocusSession.is_completed == True,
                        FocusSession.ended_at >= date_start,
                        FocusSession.ended_at <= date_end
                    )
                )
                daily_sessions = self.session.exec(daily_sessions_query).one() or 0

                daily_summaries.append({
                    "date": date.isoformat(),
                    "focus_minutes": int(daily_minutes),
                    "completed_sessions": int(daily_sessions),
                    "focus_hours": round(daily_minutes / 60, 2)
                })

            return list(reversed(daily_summaries))  # 按时间正序返回

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取每日专注摘要失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"获取每日专注摘要时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def get_weekly_focus_summary(self, user_id: str, weeks: int = 4) -> List[Dict[str, Any]]:
        """
        获取用户每周专注摘要

        Args:
            user_id: 用户ID
            weeks: 获取最近多少周的摘要，默认4周

        Returns:
            List[Dict[str, Any]]: 每周专注摘要列表

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(weeks, int) or weeks <= 0:
                raise RepositoryValidationError("周数参数必须是正整数")

            weekly_summaries = []

            # 逐周统计
            for i in range(weeks):
                # 计算周的起始和结束时间（周一到周日）
                today = datetime.now(timezone.utc).date()
                week_start = today - timedelta(days=today.weekday() + 7 * i)
                week_end = week_start + timedelta(days=6)

                week_start_datetime = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
                week_end_datetime = datetime.combine(week_end, datetime.max.time()).replace(tzinfo=timezone.utc)

                # 统计当周专注时长
                weekly_minutes_query = select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
                    and_(
                        FocusSession.user_id == user_id,
                        FocusSession.is_completed == True,
                        FocusSession.ended_at >= week_start_datetime,
                        FocusSession.ended_at <= week_end_datetime
                    )
                )
                weekly_minutes = self.session.exec(weekly_minutes_query).one() or 0

                # 统计当周完成会话数
                weekly_sessions_query = select(func.count(FocusSession.id)).where(
                    and_(
                        FocusSession.user_id == user_id,
                        FocusSession.is_completed == True,
                        FocusSession.ended_at >= week_start_datetime,
                        FocusSession.ended_at <= week_end_datetime
                    )
                )
                weekly_sessions = self.session.exec(weekly_sessions_query).one() or 0

                weekly_summaries.append({
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "focus_minutes": int(weekly_minutes),
                    "completed_sessions": int(weekly_sessions),
                    "focus_hours": round(weekly_minutes / 60, 2),
                    "daily_average_minutes": round(weekly_minutes / 7, 2)
                })

            return list(reversed(weekly_summaries))  # 按时间正序返回

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取每周专注摘要失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"获取每周专注摘要时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def get_monthly_focus_summary(self, user_id: str, months: int = 6) -> List[Dict[str, Any]]:
        """
        获取用户每月专注摘要

        Args:
            user_id: 用户ID
            months: 获取最近多少月的摘要，默认6个月

        Returns:
            List[Dict[str, Any]]: 每月专注摘要列表

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(months, int) or months <= 0:
                raise RepositoryValidationError("月数参数必须是正整数")

            monthly_summaries = []

            # 逐月统计
            for i in range(months):
                # 计算月的起始和结束时间
                today = datetime.now(timezone.utc).date()
                first_day = today.replace(day=1) - timedelta(days=30 * i)

                # 找到下个月的第一天
                if first_day.month == 12:
                    next_month_first = first_day.replace(year=first_day.year + 1, month=1)
                else:
                    next_month_first = first_day.replace(month=first_day.month + 1)

                month_end = next_month_first - timedelta(days=1)

                month_start_datetime = datetime.combine(first_day, datetime.min.time()).replace(tzinfo=timezone.utc)
                month_end_datetime = datetime.combine(month_end, datetime.max.time()).replace(tzinfo=timezone.utc)

                # 统计当月专注时长
                monthly_minutes_query = select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
                    and_(
                        FocusSession.user_id == user_id,
                        FocusSession.is_completed == True,
                        FocusSession.ended_at >= month_start_datetime,
                        FocusSession.ended_at <= month_end_datetime
                    )
                )
                monthly_minutes = self.session.exec(monthly_minutes_query).one() or 0

                # 统计当月完成会话数
                monthly_sessions_query = select(func.count(FocusSession.id)).where(
                    and_(
                        FocusSession.user_id == user_id,
                        FocusSession.is_completed == True,
                        FocusSession.ended_at >= month_start_datetime,
                        FocusSession.ended_at <= month_end_datetime
                    )
                )
                monthly_sessions = self.session.exec(monthly_sessions_query).one() or 0

                # 计算月天数
                days_in_month = (month_end - first_day).days + 1

                monthly_summaries.append({
                    "month": first_day.strftime("%Y-%m"),
                    "month_name": first_day.strftime("%Y年%m月"),
                    "focus_minutes": int(monthly_minutes),
                    "completed_sessions": int(monthly_sessions),
                    "focus_hours": round(monthly_minutes / 60, 2),
                    "daily_average_minutes": round(monthly_minutes / days_in_month, 2),
                    "days_in_month": days_in_month
                })

            return list(reversed(monthly_summaries))  # 按时间正序返回

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取每月专注摘要失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"获取每月专注摘要时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    # ==================== 专注模板方法 ====================

    def create_template(self, user_id: str, name: str, focus_duration: int, break_duration: int = None, **kwargs) -> FocusSessionTemplate:
        """
        创建专注模板

        Args:
            user_id: 用户ID
            name: 模板名称
            focus_duration: 专注时长（分钟）
            break_duration: 休息时长（分钟），可选
            **kwargs: 其他模板参数

        Returns:
            FocusSessionTemplate: 创建的专注模板

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时

        Example:
            >>> focus_repo = FocusRepository(session)
            >>> template = focus_repo.create_template(
            ...     user_id="user123",
            ...     name="番茄工作法",
            ...     focus_duration=25,
            ...     break_duration=5
            ... )
            >>> print(f"创建模板: {template.id}")
            "创建模板: 123e4567-e89b-12d3-a456-426614174000"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not name or not isinstance(name, str):
                raise RepositoryValidationError("模板名称参数不能为空且必须是字符串类型")

            if not isinstance(focus_duration, int) or focus_duration <= 0:
                raise RepositoryValidationError("专注时长必须是正整数")

            if focus_duration > 480:
                raise RepositoryValidationError("专注时长不能超过480分钟（8小时）")

            if break_duration is not None and (not isinstance(break_duration, int) or break_duration < 0):
                raise RepositoryValidationError("休息时长必须是非负整数或None")

            # 创建模板数据
            template_data = {
                "user_id": user_id,
                "name": name,
                "focus_duration": focus_duration,
                "break_duration": break_duration,
                **kwargs
            }

            # 直接创建FocusSessionTemplate实例
            template = FocusSessionTemplate(**template_data)

            # 保存到数据库
            self.session.add(template)
            self.session.commit()
            self.session.refresh(template)

            return template

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(
                f"创建专注模板失败: {str(e)}",
                operation="create",
                model_name="FocusSessionTemplate"
            )
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(
                f"创建专注模板时发生未知错误: {str(e)}",
                operation="create",
                model_name="FocusSessionTemplate"
            )

    def apply_template(self, template_id: str, user_id: str = None) -> FocusSession:
        """
        应用专注模板创建新的专注会话

        Args:
            template_id: 模板ID
            user_id: 用户ID，如果不提供则从模板中获取

        Returns:
            FocusSession: 创建的专注会话

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryNotFoundError: 模板不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not template_id or not isinstance(template_id, str):
                raise RepositoryValidationError("模板ID参数不能为空且必须是字符串类型")

            # 查找模板
            template = self.session.get(FocusSessionTemplate, template_id)
            if template is None:
                raise RepositoryNotFoundError(f"未找到ID为 {template_id} 的专注模板")

            # 确定用户ID
            target_user_id = user_id or template.user_id
            if not target_user_id:
                raise RepositoryValidationError("无法确定目标用户ID")

            # 创建专注会话
            session_data = {
                "session_type": SessionType.FOCUS,
                "duration_minutes": template.focus_duration,
                "user_id": target_user_id,
                "is_completed": False
            }

            # 使用基类的create方法
            return self.create(session_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"应用专注模板失败: {str(e)}",
                operation="create",
                model_name=self.model_name
            )

    def find_user_templates(self, user_id: str) -> List[FocusSessionTemplate]:
        """
        查找用户的专注模板

        Args:
            user_id: 用户ID

        Returns:
            List[FocusSessionTemplate]: 用户的专注模板列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(FocusSessionTemplate).where(
                FocusSessionTemplate.user_id == user_id
            ).order_by(FocusSessionTemplate.created_at.desc())

            # 执行查询
            templates = self.session.exec(statement).all()

            return list(templates)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找用户专注模板失败: {str(e)}",
                operation="read",
                model_name="FocusSessionTemplate"
            )
        except Exception as e:
            raise RepositoryError(
                f"查找用户专注模板时发生未知错误: {str(e)}",
                operation="read",
                model_name="FocusSessionTemplate"
            )

    def delete_template(self, template_id: str) -> bool:
        """
        删除专注模板

        Args:
            template_id: 模板ID

        Returns:
            bool: 删除成功返回True

        Raises:
            RepositoryValidationError: 模板ID参数无效时
            RepositoryNotFoundError: 模板不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not template_id or not isinstance(template_id, str):
                raise RepositoryValidationError("模板ID参数不能为空且必须是字符串类型")

            # 查找模板
            template = self.session.get(FocusSessionTemplate, template_id)
            if template is None:
                raise RepositoryNotFoundError(f"未找到ID为 {template_id} 的专注模板")

            # 删除模板
            self.session.delete(template)
            self.session.commit()

            return True

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(
                f"删除专注模板失败: {str(e)}",
                operation="delete",
                model_name="FocusSessionTemplate"
            )
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(
                f"删除专注模板时发生未知错误: {str(e)}",
                operation="delete",
                model_name="FocusSessionTemplate"
            )

    # ==================== 休息记录方法 ====================

    def add_break(self, session_id: str, break_duration: int, break_type: SessionType = SessionType.BREAK) -> FocusSessionBreak:
        """
        添加休息记录

        Args:
            session_id: 专注会话ID
            break_duration: 休息时长（分钟）
            break_type: 休息类型，默认为短休息

        Returns:
            FocusSessionBreak: 创建的休息记录

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryNotFoundError: 专注会话不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not session_id or not isinstance(session_id, str):
                raise RepositoryValidationError("会话ID参数不能为空且必须是字符串类型")

            if not isinstance(break_duration, int) or break_duration <= 0:
                raise RepositoryValidationError("休息时长必须是正整数")

            if break_duration > 60:  # 最长1小时休息
                raise RepositoryValidationError("休息时长不能超过60分钟")

            # 查找专注会话
            session = self.get_by_id(session_id)
            if session is None:
                raise RepositoryNotFoundError(f"未找到ID为 {session_id} 的专注会话")

            # 创建休息记录数据
            break_data = {
                "focus_session_id": session_id,
                "break_type": break_type,
                "duration_minutes": break_duration,
                "started_at": datetime.now(timezone.utc)
            }

            # 直接创建FocusSessionBreak实例
            break_record = FocusSessionBreak(**break_data)

            # 保存到数据库
            self.session.add(break_record)
            self.session.commit()
            self.session.refresh(break_record)

            return break_record

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(
                f"添加休息记录失败: {str(e)}",
                operation="create",
                model_name="FocusSessionBreak"
            )
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(
                f"添加休息记录时发生未知错误: {str(e)}",
                operation="create",
                model_name="FocusSessionBreak"
            )

    def find_session_breaks(self, session_id: str) -> List[FocusSessionBreak]:
        """
        查找专注会话的休息记录

        Args:
            session_id: 专注会话ID

        Returns:
            List[FocusSessionBreak]: 休息记录列表

        Raises:
            RepositoryValidationError: 会话ID参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not session_id or not isinstance(session_id, str):
                raise RepositoryValidationError("会话ID参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(FocusSessionBreak).where(
                FocusSessionBreak.focus_session_id == session_id
            ).order_by(FocusSessionBreak.started_at.asc())

            # 执行查询
            breaks = self.session.exec(statement).all()

            return list(breaks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找休息记录失败: {str(e)}",
                operation="read",
                model_name="FocusSessionBreak"
            )
        except Exception as e:
            raise RepositoryError(
                f"查找休息记录时发生未知错误: {str(e)}",
                operation="read",
                model_name="FocusSessionBreak"
            )

    def complete_break(self, break_id: str) -> FocusSessionBreak:
        """
        完成休息记录

        Args:
            break_id: 休息记录ID

        Returns:
            FocusSessionBreak: 完成后的休息记录

        Raises:
            RepositoryValidationError: 休息记录ID参数无效时
            RepositoryNotFoundError: 休息记录不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not break_id or not isinstance(break_id, str):
                raise RepositoryValidationError("休息记录ID参数不能为空且必须是字符串类型")

            # 查找休息记录
            break_record = self.session.get(FocusSessionBreak, break_id)
            if break_record is None:
                raise RepositoryNotFoundError(f"未找到ID为 {break_id} 的休息记录")

            # 检查休息记录状态
            if break_record.ended_at:
                raise RepositoryValidationError(f"休息记录 {break_id} 已经结束，无需重复操作")

            # 构建更新数据
            now = datetime.now(timezone.utc)
            actual_duration = int((now - break_record.started_at).total_seconds() / 60)

            update_data = {
                "ended_at": now,
                "duration_minutes": actual_duration
            }

            # 更新休息记录
            for key, value in update_data.items():
                setattr(break_record, key, value)

            self.session.commit()
            self.session.refresh(break_record)

            return break_record

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(
                f"完成休息记录失败: {str(e)}",
                operation="update",
                model_name="FocusSessionBreak"
            )
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(
                f"完成休息记录时发生未知错误: {str(e)}",
                operation="update",
                model_name="FocusSessionBreak"
            )


# 导出FocusRepository类
__all__ = ["FocusRepository"]