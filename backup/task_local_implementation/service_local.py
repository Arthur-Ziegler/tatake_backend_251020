"""
任务本地操作服务

提供微服务不支持的任务操作功能。
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlmodel import Session, select, and_

from src.database import get_database_connection
from .models_local import TaskOperation, TaskCompletion, FocusStatus, PomodoroCount

logger = logging.getLogger(__name__)


class TaskLocalService:
    """任务本地操作服务"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or self._get_session()
        self.logger = logging.getLogger(__name__)

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return Session(get_database_connection().get_engine())

    def record_task_operation(
        self,
        user_id: UUID,
        task_id: str,
        operation_type: str,
        operation_data: Optional[Dict[str, Any]] = None
    ) -> TaskOperation:
        """
        记录任务操作

        Args:
            user_id: 用户ID
            task_id: 任务ID
            operation_type: 操作类型 (delete, update, complete)
            operation_data: 操作数据

        Returns:
            TaskOperation: 操作记录
        """
        operation = TaskOperation(
            user_id=user_id,
            task_id=task_id,
            operation_type=operation_type,
            operation_data=json.dumps(operation_data) if operation_data else None
        )

        self.session.add(operation)
        self.session.commit()
        self.session.refresh(operation)

        self.logger.info(f"记录任务操作: {operation_type} for task {task_id} by user {user_id}")
        return operation

    def has_task_operation(
        self,
        user_id: UUID,
        task_id: str,
        operation_type: str
    ) -> bool:
        """
        检查任务操作是否已存在

        Args:
            user_id: 用户ID
            task_id: 任务ID
            operation_type: 操作类型

        Returns:
            bool: 操作是否存在
        """
        statement = select(TaskOperation).where(
            and_(
                TaskOperation.user_id == user_id,
                TaskOperation.task_id == task_id,
                TaskOperation.operation_type == operation_type
            )
        )
        result = self.session.exec(statement).first()
        return result is not None

    def record_task_completion(
        self,
        user_id: UUID,
        task_id: str,
        completion_type: str = "full",
        points_earned: int = 0,
        reward_given: Optional[str] = None,
        completion_data: Optional[Dict[str, Any]] = None
    ) -> TaskCompletion:
        """
        记录任务完成

        Args:
            user_id: 用户ID
            task_id: 任务ID
            completion_type: 完成类型
            points_earned: 获得积分
            reward_given: 奖励描述
            completion_data: 完成数据

        Returns:
            TaskCompletion: 完成记录
        """
        completion = TaskCompletion(
            user_id=user_id,
            task_id=task_id,
            completion_type=completion_type,
            points_earned=points_earned,
            reward_given=reward_given,
            completion_data=json.dumps(completion_data) if completion_data else None
        )

        self.session.add(completion)
        self.session.commit()
        self.session.refresh(completion)

        # 更新番茄钟计数
        self._update_pomodoro_count(user_id, completion_type)

        self.logger.info(f"记录任务完成: {completion_type} for task {task_id} by user {user_id}")
        return completion

    def record_focus_status(
        self,
        user_id: UUID,
        focus_status: str,
        task_id: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        status_data: Optional[Dict[str, Any]] = None
    ) -> FocusStatus:
        """
        记录专注状态

        Args:
            user_id: 用户ID
            focus_status: 专注状态
            task_id: 相关任务ID
            duration_minutes: 专注时长
            status_data: 状态数据

        Returns:
            FocusStatus: 状态记录
        """
        status = FocusStatus(
            user_id=user_id,
            task_id=task_id,
            focus_status=focus_status,
            duration_minutes=duration_minutes,
            status_data=json.dumps(status_data) if status_data else None
        )

        self.session.add(status)
        self.session.commit()
        self.session.refresh(status)

        # 如果是完成专注，更新番茄钟计数
        if focus_status == "complete" and duration_minutes and duration_minutes >= 25:
            self._update_pomodoro_count(user_id, "focus_complete")

        self.logger.info(f"记录专注状态: {focus_status} by user {user_id}")
        return status

    def get_pomodoro_count(
        self,
        user_id: UUID,
        date_filter: str = "today"
    ) -> PomodoroCount:
        """
        获取番茄钟计数

        Args:
            user_id: 用户ID
            date_filter: 日期过滤类型

        Returns:
            PomodoroCount: 番茄钟计数
        """
        statement = select(PomodoroCount).where(
            and_(
                PomodoroCount.user_id == user_id,
                PomodoroCount.date_filter == date_filter
            )
        )
        result = self.session.exec(statement).first()

        if not result:
            # 创建新的计数记录
            count = self._calculate_pomodoro_count(user_id, date_filter)
            result = PomodoroCount(
                user_id=user_id,
                date_filter=date_filter,
                count=count
            )
            self.session.add(result)
            self.session.commit()
            self.session.refresh(result)

        return result

    def _update_pomodoro_count(self, user_id: UUID, completion_type: str):
        """更新番茄钟计数"""
        # 更新今日计数
        today_count = self.get_pomodoro_count(user_id, "today")
        if completion_type in ["full", "focus_complete"]:
            today_count.count += 1
            today_count.last_updated = datetime.utcnow()

        # 更新本周计数
        week_count = self.get_pomodoro_count(user_id, "week")
        if completion_type in ["full", "focus_complete"]:
            week_count.count += 1
            week_count.last_updated = datetime.utcnow()

        # 更新本月计数
        month_count = self.get_pomodoro_count(user_id, "month")
        if completion_type in ["full", "focus_complete"]:
            month_count.count += 1
            month_count.last_updated = datetime.utcnow()

        self.session.commit()

    def _calculate_pomodoro_count(self, user_id: UUID, date_filter: str) -> int:
        """计算番茄钟计数"""
        now = datetime.utcnow()

        if date_filter == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return 0

        # 查询任务完成记录
        statement = select(TaskCompletion).where(
            and_(
                TaskCompletion.user_id == user_id,
                TaskCompletion.completed_at >= start_date,
                TaskCompletion.completion_type.in_(["full", "focus_complete"])
            )
        )
        completions = self.session.exec(statement).all()

        # 查询专注状态记录
        statement = select(FocusStatus).where(
            and_(
                FocusStatus.user_id == user_id,
                FocusStatus.created_at >= start_date,
                FocusStatus.focus_status == "complete",
                FocusStatus.duration_minutes >= 25
            )
        )
        focus_records = self.session.exec(statement).all()

        return len(completions) + len(focus_records)

    def get_task_completions(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[TaskCompletion]:
        """
        获取任务完成记录

        Args:
            user_id: 用户ID
            limit: 限制数量

        Returns:
            List[TaskCompletion]: 完成记录列表
        """
        statement = select(TaskCompletion).where(
            TaskCompletion.user_id == user_id
        ).order_by(TaskCompletion.completed_at.desc()).limit(limit)

        return self.session.exec(statement).all()

    def get_focus_history(
        self,
        user_id: UUID,
        limit: int = 20
    ) -> List[FocusStatus]:
        """
        获取专注历史记录

        Args:
            user_id: 用户ID
            limit: 限制数量

        Returns:
            List[FocusStatus]: 专注记录列表
        """
        statement = select(FocusStatus).where(
            FocusStatus.user_id == user_id
        ).order_by(FocusStatus.created_at.desc()).limit(limit)

        return self.session.exec(statement).all()