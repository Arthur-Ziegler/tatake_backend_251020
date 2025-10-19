"""
专注服务模块

该模块实现专注会话管理相关的业务逻辑，包括专注会话的创建、暂停、恢复、完成等操作。
采用番茄钟工作法（25分钟专注+5分钟休息），支持灵活的会话管理和统计分析。

设计原则：
1. 强制任务关联：专注会话必须绑定具体任务
2. 状态管理：严格的会话状态流转控制
3. 数据记录：完整的专注数据记录和统计分析
4. 用户体验：支持暂停、恢复等灵活操作
5. 激励机制：专注完成后的积分奖励

核心功能：
- 专注会话创建和管理
- 会话状态转换（进行中、暂停、完成等）
- 专注统计和趋势分析
- 连续专注天数计算
- 任务关联专注记录
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .base import BaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    DuplicateResourceException,
    InsufficientBalanceException
)
from src.models.focus import FocusSession
from src.models.enums import SessionType


class FocusService(BaseService):
    """
    专注服务类

    处理专注会话管理相关的所有业务逻辑，包括会话创建、状态管理、
    统计分析等核心功能。采用番茄钟工作法，提供完整的专注体验。

    Attributes:
        _user_repo: 用户数据访问对象
        _task_repo: 任务数据访问对象
        _focus_repo: 专注数据访问对象
        _reward_repo: 奖励数据访问对象
    """

    def __init__(self, user_repo, task_repo, focus_repo, reward_repo=None, **kwargs):
        """
        初始化专注服务

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            **kwargs: 其他参数传递给父类
        """
        super().__init__(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo,
            **kwargs
        )

        # 番茄钟配置（默认25分钟专注+5分钟休息）
        self.default_focus_duration = 25  # 分钟
        self.default_break_duration = 5   # 分钟

    # ==================== 专注会话管理 ====================

    def start_focus_session(
        self,
        user_id: str,
        task_id: str,
        planned_duration_minutes: Optional[int] = None,
        session_type: str = "focus"
    ) -> Dict[str, Any]:
        """
        开始专注会话

        创建新的专注会话，必须绑定具体任务。
        支持自定义专注时长和会话类型。

        Args:
            user_id: 用户ID
            task_id: 任务ID
            planned_duration_minutes: 计划专注时长（分钟），默认25分钟
            session_type: 会话类型（focus/break）

        Returns:
            创建的专注会话信息

        Raises:
            ResourceNotFoundException: 当用户或任务不存在时
            ValidationException: 当参数无效时
            BusinessException: 当存在活跃会话时
        """
        try:
            self._log_info("开始专注会话", {
                "user_id": user_id,
                "task_id": task_id,
                "planned_duration": planned_duration_minutes,
                "session_type": session_type
            })

            # 验证用户存在
            self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 验证任务存在且属于该用户
            task = self._check_resource_exists(
                self.get_task_repository(),
                task_id,
                "任务"
            )

            if task.user_id != user_id:
                raise ValidationException(
                    message="任务不属于当前用户",
                    details={"task_id": task_id, "user_id": user_id}
                )

            # 检查是否有活跃的专注会话
            active_session = self._get_active_session(user_id)
            if active_session:
                raise BusinessException(
                    error_code="SERVICE_ACTIVE_SESSION_EXISTS",
                    message="用户已有活跃的专注会话",
                    user_message="请先完成或暂停当前的专注会话",
                    details={"active_session_id": active_session.id}
                )

            # 验证会话类型
            if session_type not in ["focus", "break"]:
                raise ValidationException(
                    message="无效的会话类型",
                    details={"session_type": session_type, "valid_types": ["focus", "break"]}
                )

            # 设置默认专注时长
            if planned_duration_minutes is None:
                planned_duration_minutes = self.default_focus_duration if session_type == "focus" else self.default_break_duration

            # 验证专注时长
            if planned_duration_minutes <= 0 or planned_duration_minutes > 480:  # 最长8小时
                raise ValidationException(
                    message="专注时长必须在1-480分钟之间",
                    details={"planned_duration": planned_duration_minutes}
                )

            # 创建专注会话
            session_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "task_id": task_id,
                "session_type": session_type,
                "planned_duration_minutes": planned_duration_minutes,
                "actual_duration_minutes": 0,
                "status": "in_progress",
                "start_time": datetime.now(),
                "end_time": None,
                "pause_time": None,
                "resume_time": None,
                "interruptions_count": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }

            created_session = self.get_focus_repository().create(session_data)

            # 更新任务状态为进行中（如果是专注会话）
            if session_type == "focus" and task.status.value in ["pending", "cancelled"]:
                task_update_data = {
                    "status": "in_progress",
                    "updated_at": datetime.now()
                }
                self.get_task_repository().update(task_id, task_update_data)

            result = self._session_to_dict(created_session)

            self._log_info("专注会话创建成功", {
                "session_id": created_session.id,
                "user_id": user_id,
                "task_id": task_id,
                "planned_duration": planned_duration_minutes
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "start_focus_session", {
                "user_id": user_id,
                "task_id": task_id
            })

    def get_focus_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取专注会话详情

        获取指定专注会话的详细信息，包括当前状态和进度。

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            专注会话详细信息

        Raises:
            ResourceNotFoundException: 当会话不存在时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("获取专注会话详情", {
                "session_id": session_id,
                "user_id": user_id
            })

            # 获取会话信息
            session = self._check_resource_exists(
                self.get_focus_repository(),
                session_id,
                "专注会话"
            )

            # 验证用户权限
            if session.user_id != user_id:
                raise AuthorizationException(
                    required_permission="focus:read",
                    user_id=user_id,
                    resource_id=session_id
                )

            # 计算会话进度
            progress_info = self._calculate_session_progress(session)

            # 构建完整会话信息
            result = self._session_to_dict(session)
            result["progress"] = progress_info

            self._log_info("专注会话详情获取成功", {
                "session_id": session_id,
                "user_id": user_id
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_focus_session", {
                "session_id": session_id,
                "user_id": user_id
            })

    def pause_focus_session(self, session_id: str, user_id: str, interruption_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        暂停专注会话

        暂停正在进行的专注会话，记录暂停时间和原因。

        Args:
            session_id: 会话ID
            user_id: 用户ID
            interruption_reason: 中断原因（可选）

        Returns:
            暂停后的会话状态

        Raises:
            ResourceNotFoundException: 当会话不存在时
            ValidationException: 当会话状态不允许暂停时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("暂停专注会话", {
                "session_id": session_id,
                "user_id": user_id,
                "interruption_reason": interruption_reason
            })

            # 获取会话信息
            session = self._check_resource_exists(
                self.get_focus_repository(),
                session_id,
                "专注会话"
            )

            # 验证用户权限
            if session.user_id != user_id:
                raise AuthorizationException(
                    required_permission="focus:pause",
                    user_id=user_id,
                    resource_id=session_id
                )

            # 验证会话状态
            if session.status != "in_progress":
                raise ValidationException(
                    message="只有进行中的会话可以暂停",
                    details={"current_status": session.status}
                )

            # 更新会话状态
            update_data = {
                "status": "paused",
                "pause_time": datetime.now(),
                "interruptions_count": session.interruptions_count + 1,
                "updated_at": datetime.now()
            }

            if interruption_reason:
                update_data["interruption_reason"] = interruption_reason

            paused_session = self.get_focus_repository().update(session_id, update_data)

            result = self._session_to_dict(paused_session)

            self._log_info("专注会话暂停成功", {
                "session_id": session_id,
                "user_id": user_id,
                "interruptions_count": paused_session.interruptions_count
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "pause_focus_session", {
                "session_id": session_id,
                "user_id": user_id
            })

    def resume_focus_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        恢复专注会话

        恢复暂停的专注会话，继续专注计时。

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            恢复后的会话状态

        Raises:
            ResourceNotFoundException: 当会话不存在时
            ValidationException: 当会话状态不允许恢复时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("恢复专注会话", {
                "session_id": session_id,
                "user_id": user_id
            })

            # 获取会话信息
            session = self._check_resource_exists(
                self.get_focus_repository(),
                session_id,
                "专注会话"
            )

            # 验证用户权限
            if session.user_id != user_id:
                raise AuthorizationException(
                    required_permission="focus:resume",
                    user_id=user_id,
                    resource_id=session_id
                )

            # 验证会话状态
            if session.status != "paused":
                raise ValidationException(
                    message="只有暂停的会话可以恢复",
                    details={"current_status": session.status}
                )

            # 更新会话状态
            update_data = {
                "status": "in_progress",
                "resume_time": datetime.now(),
                "updated_at": datetime.now()
            }

            resumed_session = self.get_focus_repository().update(session_id, update_data)

            result = self._session_to_dict(resumed_session)

            self._log_info("专注会话恢复成功", {
                "session_id": session_id,
                "user_id": user_id
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "resume_focus_session", {
                "session_id": session_id,
                "user_id": user_id
            })

    def complete_focus_session(
        self,
        session_id: str,
        user_id: str,
        mood_feedback: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        完成专注会话

        完成专注会话，记录实际专注时长、心情反馈等，
        计算并发放专注奖励。

        Args:
            session_id: 会话ID
            user_id: 用户ID
            mood_feedback: 心情反馈
            notes: 会话备注（可选）

        Returns:
            完成结果和奖励信息

        Raises:
            ResourceNotFoundException: 当会话不存在时
            ValidationException: 当参数无效或会话状态不允许完成时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("完成专注会话", {
                "session_id": session_id,
                "user_id": user_id,
                "mood_feedback": mood_feedback
            })

            # 获取会话信息
            session = self._check_resource_exists(
                self.get_focus_repository(),
                session_id,
                "专注会话"
            )

            # 验证用户权限
            if session.user_id != user_id:
                raise AuthorizationException(
                    required_permission="focus:complete",
                    user_id=user_id,
                    resource_id=session_id
                )

            # 验证会话状态
            if session.status not in ["in_progress", "paused"]:
                raise ValidationException(
                    message="只有进行中或暂停的会话可以完成",
                    details={"current_status": session.status}
                )

            # 验证心情反馈
            if not mood_feedback or len(mood_feedback.strip()) == 0:
                raise ValidationException(
                    message="心情反馈不能为空",
                    details={"mood_feedback": mood_feedback}
                )

            # 计算实际专注时长
            end_time = datetime.now()
            actual_duration_minutes = self._calculate_actual_duration(session, end_time)

            # 计算专注奖励
            rewards = self._calculate_focus_rewards(session, actual_duration_minutes)

            # 更新会话状态
            update_data = {
                "status": "completed",
                "end_time": end_time,
                "actual_duration_minutes": actual_duration_minutes,
                "mood_feedback": mood_feedback.strip(),
                "notes": notes.strip() if notes else None,
                "updated_at": datetime.now()
            }

            completed_session = self.get_focus_repository().update(session_id, update_data)

            # 发放专注奖励
            if rewards["points"] > 0 or rewards["fragments"] > 0:
                self._grant_focus_rewards(user_id, session_id, rewards)

            # 更新连续专注天数
            streak_info = self._update_focus_streak(user_id)

            # 构建结果
            result = {
                "session": self._session_to_dict(completed_session),
                "rewards": rewards,
                "streak_info": streak_info
            }

            self._log_info("专注会话完成成功", {
                "session_id": session_id,
                "user_id": user_id,
                "actual_duration": actual_duration_minutes,
                "points_awarded": rewards["points"],
                "fragments_awarded": rewards["fragments"]
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "complete_focus_session", {
                "session_id": session_id,
                "user_id": user_id
            })

    # ==================== 专注记录查询 ====================

    def get_user_focus_sessions(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取用户专注记录

        获取用户的专注会话记录，支持日期范围筛选和分页。

        Args:
            user_id: 用户ID
            start_date: 开始日期（YYYY-MM-DD格式，可选）
            end_date: 结束日期（YYYY-MM-DD格式，可选）
            limit: 结果数量限制
            offset: 偏移量

        Returns:
            专注会话记录列表

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当参数无效时
        """
        try:
            self._log_info("获取用户专注记录", {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
                "offset": offset
            })

            # 验证用户存在
            self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 验证参数
            if limit <= 0 or limit > 100:
                raise ValidationException(
                    message="结果数量限制必须在1-100之间",
                    details={"limit": limit}
                )

            if offset < 0:
                raise ValidationException(
                    message="偏移量不能为负数",
                    details={"offset": offset}
                )

            # 处理日期参数
            start_datetime = None
            end_datetime = None

            if start_date:
                try:
                    start_datetime = datetime.fromisoformat(start_date)
                except ValueError:
                    raise ValidationException(
                        message="开始日期格式无效，请使用YYYY-MM-DD格式",
                        details={"start_date": start_date}
                    )

            if end_date:
                try:
                    end_datetime = datetime.fromisoformat(end_date)
                    # 设置为当天的结束时间
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                except ValueError:
                    raise ValidationException(
                        message="结束日期格式无效，请使用YYYY-MM-DD格式",
                        details={"end_date": end_date}
                    )

            # 查询专注记录
            sessions = self.get_focus_repository().find_sessions_by_user(
                user_id=user_id,
                start_time=start_datetime,
                end_time=end_datetime,
                limit=limit,
                offset=offset
            )

            # 获取总数
            total_count = self.get_focus_repository().count_sessions_by_user(
                user_id=user_id,
                start_time=start_datetime,
                end_time=end_datetime
            )

            # 转换为字典格式
            session_list = [self._session_to_dict(session) for session in sessions]

            # 计算统计数据
            statistics = self._calculate_sessions_statistics(session_list)

            result = {
                "sessions": session_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_count": total_count,
                    "has_more": offset + limit < total_count
                },
                "statistics": statistics,
                "filter_info": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "queried_at": datetime.now().isoformat()
                }
            }

            self._log_info("用户专注记录获取成功", {
                "user_id": user_id,
                "result_count": len(session_list),
                "total_count": total_count
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_user_focus_sessions", {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            })

    def get_task_focus_sessions(
        self,
        task_id: str,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取特定任务的专注记录

        获取指定任务的所有专注会话记录。

        Args:
            task_id: 任务ID
            user_id: 用户ID
            limit: 结果数量限制
            offset: 偏移量

        Returns:
            任务的专注会话记录列表

        Raises:
            ResourceNotFoundException: 当任务不存在时
            ValidationException: 当参数无效时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("获取任务专注记录", {
                "task_id": task_id,
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            })

            # 验证任务存在且属于该用户
            task = self._check_resource_exists(
                self.get_task_repository(),
                task_id,
                "任务"
            )

            if task.user_id != user_id:
                raise AuthorizationException(
                    required_permission="task:focus_read",
                    user_id=user_id,
                    resource_id=task_id
                )

            # 验证参数
            if limit <= 0 or limit > 100:
                raise ValidationException(
                    message="结果数量限制必须在1-100之间",
                    details={"limit": limit}
                )

            if offset < 0:
                raise ValidationException(
                    message="偏移量不能为负数",
                    details={"offset": offset}
                )

            # 查询任务的专注记录
            sessions = self.get_focus_repository().find_sessions_by_task(
                task_id=task_id,
                limit=limit,
                offset=offset
            )

            # 获取总数
            total_count = self.get_focus_repository().count_sessions_by_task(task_id)

            # 转换为字典格式
            session_list = [self._session_to_dict(session) for session in sessions]

            # 计算任务专注统计
            task_statistics = self._calculate_task_focus_statistics(session_list)

            result = {
                "task_id": task_id,
                "task_title": task.title,
                "sessions": session_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_count": total_count,
                    "has_more": offset + limit < total_count
                },
                "task_statistics": task_statistics
            }

            self._log_info("任务专注记录获取成功", {
                "task_id": task_id,
                "user_id": user_id,
                "result_count": len(session_list),
                "total_count": total_count
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_task_focus_sessions", {
                "task_id": task_id,
                "user_id": user_id
            })

    def get_focus_statistics(
        self,
        user_id: str,
        period: str = "month",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取专注统计数据

        获取用户的专注统计数据，包括趋势分析、分布情况、时长统计等。

        Args:
            user_id: 用户ID
            period: 统计周期（week/month/year）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            专注统计数据

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当参数无效时
        """
        try:
            self._log_info("获取专注统计数据", {
                "user_id": user_id,
                "period": period,
                "start_date": start_date,
                "end_date": end_date
            })

            # 验证用户存在
            self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 验证统计周期
            if period not in ["week", "month", "year"]:
                raise ValidationException(
                    message="无效的统计周期",
                    details={"period": period, "valid_periods": ["week", "month", "year"]}
                )

            # 处理日期范围
            date_range = self._calculate_date_range(period, start_date, end_date)

            # 查询专注会话数据
            sessions = self.get_focus_repository().find_sessions_by_user(
                user_id=user_id,
                start_time=date_range["start"],
                end_time=date_range["end"]
            )

            # 计算统计数据
            daily_stats = self._calculate_daily_statistics(sessions)
            summary_stats = self._calculate_summary_statistics(sessions)
            trend_analysis = self._calculate_trend_analysis(daily_stats)
            time_distribution = self._calculate_time_distribution(sessions)

            result = {
                "period": {
                    "type": period,
                    "start_date": date_range["start"].isoformat(),
                    "end_date": date_range["end"].isoformat()
                },
                "daily_statistics": daily_stats,
                "summary": summary_stats,
                "trend_analysis": trend_analysis,
                "time_distribution": time_distribution
            }

            self._log_info("专注统计数据获取成功", {
                "user_id": user_id,
                "period": period,
                "total_sessions": len(sessions)
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_focus_statistics", {
                "user_id": user_id,
                "period": period
            })

    # ==================== 私有方法 ====================

    def _get_active_session(self, user_id: str) -> Optional[FocusSession]:
        """
        获取用户的活跃专注会话

        Args:
            user_id: 用户ID

        Returns:
            活跃的专注会话，如果没有则返回None
        """
        active_sessions = self.get_focus_repository().find_active_sessions(user_id)
        return active_sessions[0] if active_sessions else None

    def _calculate_session_progress(self, session: FocusSession) -> Dict[str, Any]:
        """
        计算会话进度

        Args:
            session: 专注会话对象

        Returns:
            会话进度信息
        """
        if session.status == "completed":
            return {
                "progress_percentage": 100.0,
                "elapsed_minutes": session.actual_duration_minutes,
                "remaining_minutes": 0,
                "is_completed": True
            }

        current_time = datetime.now()
        elapsed_seconds = 0

        if session.status == "in_progress":
            if session.resume_time:
                # 恢复后的时间
                elapsed_seconds += (current_time - session.resume_time).total_seconds()
            # 暂停前的时间
            if session.pause_time:
                elapsed_seconds += (session.pause_time - session.start_time).total_seconds()
            else:
                # 没有暂停过，直接计算
                elapsed_seconds += (current_time - session.start_time).total_seconds()
        elif session.status == "paused":
            # 暂停状态，只计算到暂停时间
            if session.pause_time:
                elapsed_seconds += (session.pause_time - session.start_time).total_seconds()

        elapsed_minutes = elapsed_seconds / 60
        planned_minutes = session.planned_duration_minutes

        progress_percentage = min((elapsed_minutes / planned_minutes) * 100, 100.0) if planned_minutes > 0 else 0.0
        remaining_minutes = max(planned_minutes - elapsed_minutes, 0)

        return {
            "progress_percentage": round(progress_percentage, 2),
            "elapsed_minutes": round(elapsed_minutes, 2),
            "remaining_minutes": round(remaining_minutes, 2),
            "is_completed": False
        }

    def _calculate_actual_duration(self, session: FocusSession, end_time: datetime) -> int:
        """
        计算实际专注时长（分钟）

        Args:
            session: 专注会话对象
            end_time: 结束时间

        Returns:
            实际专注时长（分钟）
        """
        total_seconds = 0

        # 计算总时间
        if session.resume_time:
            # 有恢复记录，分段计算
            # 开始到暂停的时间
            if session.pause_time:
                total_seconds += (session.pause_time - session.start_time).total_seconds()
            # 恢复到结束的时间
            total_seconds += (end_time - session.resume_time).total_seconds()
        else:
            # 没有暂停记录，直接计算
            if session.pause_time:
                total_seconds += (session.pause_time - session.start_time).total_seconds()
            else:
                total_seconds += (end_time - session.start_time).total_seconds()

        return int(total_seconds / 60)

    def _calculate_focus_rewards(self, session: FocusSession, actual_duration: int) -> Dict[str, int]:
        """
        计算专注奖励

        Args:
            session: 专注会话对象
            actual_duration: 实际专注时长（分钟）

        Returns:
            奖励信息
        """
        # 基础奖励
        base_points = max(1, actual_duration // 10)  # 每10分钟1个积分
        base_fragments = 1 if actual_duration >= 25 else 0  # 25分钟以上给1个碎片

        # 根据完成度调整奖励
        completion_rate = actual_duration / session.planned_duration_minutes
        if completion_rate >= 1.0:
            # 超额完成，额外奖励
            bonus_points = int((actual_duration - session.planned_duration_minutes) / 20)
            bonus_fragments = 1 if actual_duration >= session.planned_duration_minutes * 1.5 else 0
        else:
            # 未完成，按比例减少奖励
            base_points = int(base_points * completion_rate)
            base_fragments = 1 if completion_rate >= 0.8 and base_fragments > 0 else 0
            bonus_points = 0
            bonus_fragments = 0

        return {
            "points": base_points + bonus_points,
            "fragments": base_fragments + bonus_fragments
        }

    def _grant_focus_rewards(self, user_id: str, session_id: str, rewards: Dict[str, int]) -> None:
        """
        发放专注奖励

        Args:
            user_id: 用户ID
            session_id: 会话ID
            rewards: 奖励信息
        """
        # TODO: 调用UserService的方法来发放奖励
        # if rewards["points"] > 0:
        #     self.user_service.add_user_points(user_id, rewards["points"], f"完成专注会话 {session_id}")
        # if rewards["fragments"] > 0:
        #     self.user_service.add_user_fragments(user_id, rewards["fragments"], f"完成专注会话 {session_id}")
        pass

    def _update_focus_streak(self, user_id: str) -> Dict[str, Any]:
        """
        更新用户连续专注天数

        Args:
            user_id: 用户ID

        Returns:
            连续专注信息
        """
        # TODO: 实现连续专注天数计算逻辑
        # 这里需要查询用户最近的专注记录，计算连续天数
        return {
            "current_streak": 1,
            "best_streak": 1,
            "last_focus_date": datetime.now().date().isoformat()
        }

    def _calculate_sessions_statistics(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算会话统计数据

        Args:
            sessions: 会话列表

        Returns:
            统计信息
        """
        if not sessions:
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "total_focus_minutes": 0,
                "average_session_duration": 0.0,
                "completion_rate": 0.0
            }

        completed_sessions = [s for s in sessions if s["status"] == "completed"]
        total_minutes = sum(s.get("actual_duration_minutes", 0) for s in completed_sessions)

        return {
            "total_sessions": len(sessions),
            "completed_sessions": len(completed_sessions),
            "total_focus_minutes": total_minutes,
            "average_session_duration": total_minutes / len(completed_sessions) if completed_sessions else 0.0,
            "completion_rate": (len(completed_sessions) / len(sessions)) * 100 if sessions else 0.0
        }

    def _calculate_task_focus_statistics(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算任务专注统计

        Args:
            sessions: 专注会话列表

        Returns:
            任务专注统计
        """
        if not sessions:
            return {
                "total_sessions": 0,
                "total_focus_minutes": 0,
                "average_session_duration": 0.0,
                "completion_rate": 0.0,
                "best_session_duration": 0
            }

        completed_sessions = [s for s in sessions if s["status"] == "completed"]
        total_minutes = sum(s.get("actual_duration_minutes", 0) for s in completed_sessions)
        best_duration = max((s.get("actual_duration_minutes", 0) for s in completed_sessions), default=0)

        return {
            "total_sessions": len(sessions),
            "total_focus_minutes": total_minutes,
            "average_session_duration": total_minutes / len(completed_sessions) if completed_sessions else 0.0,
            "completion_rate": (len(completed_sessions) / len(sessions)) * 100 if sessions else 0.0,
            "best_session_duration": best_duration
        }

    def _calculate_date_range(
        self,
        period: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> Dict[str, datetime]:
        """
        计算日期范围

        Args:
            period: 统计周期
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日期范围
        """
        now = datetime.now()

        if start_date and end_date:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
        else:
            if period == "week":
                start = now - timedelta(days=7)
                end = now
            elif period == "month":
                start = now - timedelta(days=30)
                end = now
            elif period == "year":
                start = now - timedelta(days=365)
                end = now
            else:
                start = now - timedelta(days=30)
                end = now

        return {"start": start, "end": end}

    def _calculate_daily_statistics(self, sessions: List[FocusSession]) -> List[Dict[str, Any]]:
        """
        计算每日统计数据

        Args:
            sessions: 专注会话列表

        Returns:
            每日统计列表
        """
        daily_data = {}

        for session in sessions:
            date_key = session.start_time.date().isoformat()

            if date_key not in daily_data:
                daily_data[date_key] = {
                    "date": date_key,
                    "total_sessions": 0,
                    "completed_sessions": 0,
                    "focus_sessions": 0,
                    "total_focus_minutes": 0,
                    "completion_rate": 0.0,
                    "interruptions_count": 0
                }

            daily = daily_data[date_key]
            daily["total_sessions"] += 1

            if session.status == "completed":
                daily["completed_sessions"] += 1
                if session.session_type == "focus":
                    daily["focus_sessions"] += 1
                    daily["total_focus_minutes"] += session.actual_duration_minutes

            daily["interruptions_count"] += session.interruptions_count

        # 计算完成率
        for daily in daily_data.values():
            if daily["total_sessions"] > 0:
                daily["completion_rate"] = (daily["completed_sessions"] / daily["total_sessions"]) * 100

        # 按日期排序
        return sorted(daily_data.values(), key=lambda x: x["date"])

    def _calculate_summary_statistics(self, sessions: List[FocusSession]) -> Dict[str, Any]:
        """
        计算汇总统计

        Args:
            sessions: 专注会话列表

        Returns:
            汇总统计信息
        """
        if not sessions:
            return {
                "total_focus_hours": 0.0,
                "daily_average": 0.0,
                "best_day": None,
                "trend": "stable"
            }

        completed_sessions = [s for s in sessions if s.status == "completed" and s.session_type == "focus"]
        total_minutes = sum(s.actual_duration_minutes for s in completed_sessions)
        total_hours = total_minutes / 60

        # 计算日均专注时间
        date_range = (max(s.start_time.date() for s in sessions) - min(s.start_time.date() for s in sessions)).days + 1
        daily_average = total_minutes / date_range if date_range > 0 else 0

        # 找出最佳表现日
        daily_stats = self._calculate_daily_statistics(sessions)
        best_day = max(daily_stats, key=lambda x: x["total_focus_minutes"]) if daily_stats else None

        # 计算趋势
        if len(daily_stats) >= 7:
            recent_avg = sum(d["total_focus_minutes"] for d in daily_stats[-7:]) / 7
            previous_avg = sum(d["total_focus_minutes"] for d in daily_stats[-14:-7]) / 7
            if recent_avg > previous_avg * 1.1:
                trend = "improving"
            elif recent_avg < previous_avg * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "total_focus_hours": round(total_hours, 2),
            "daily_average": round(daily_average, 2),
            "best_day": {
                "date": best_day["date"] if best_day else None,
                "focus_minutes": best_day["total_focus_minutes"] if best_day else 0
            },
            "trend": trend
        }

    def _calculate_trend_analysis(self, daily_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算趋势分析

        Args:
            daily_stats: 每日统计数据

        Returns:
            趋势分析结果
        """
        if len(daily_stats) < 2:
            return {
                "trend": "stable",
                "slope": 0.0,
                "confidence": "low"
            }

        # 简单线性回归计算趋势
        focus_minutes = [d["total_focus_minutes"] for d in daily_stats]
        n = len(focus_minutes)

        sum_x = sum(range(n))
        sum_y = sum(focus_minutes)
        sum_xy = sum(i * y for i, y in enumerate(focus_minutes))
        sum_x2 = sum(i * i for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        if slope > 1:
            trend = "improving"
        elif slope < -1:
            trend = "declining"
        else:
            trend = "stable"

        confidence = "high" if n >= 30 else "medium" if n >= 7 else "low"

        return {
            "trend": trend,
            "slope": round(slope, 3),
            "confidence": confidence,
            "data_points": n
        }

    def _calculate_time_distribution(self, sessions: List[FocusSession]) -> Dict[str, Any]:
        """
        计算时间分布统计

        Args:
            sessions: 专注会话列表

        Returns:
            时间分布统计
        """
        hour_distribution = [0] * 24  # 24小时分布
        weekday_distribution = [0] * 7   # 7天分布

        for session in sessions:
            if session.start_time:
                hour = session.start_time.hour
                weekday = session.start_time.weekday()  # 0=Monday, 6=Sunday
                hour_distribution[hour] += 1
                weekday_distribution[weekday] += 1

        # 找出最佳专注时间段
        best_hour = max(range(24), key=lambda x: hour_distribution[x])
        best_weekday = max(range(7), key=lambda x: weekday_distribution[x])

        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        return {
            "hour_distribution": hour_distribution,
            "weekday_distribution": weekday_distribution,
            "best_focus_hour": f"{best_hour:02d}:00",
            "best_focus_weekday": weekday_names[best_weekday],
            "peak_hours": [i for i, count in enumerate(hour_distribution) if count == max(hour_distribution)],
            "peak_weekdays": [weekday_names[i] for i, count in enumerate(weekday_distribution) if count == max(weekday_distribution)]
        }

    def _session_to_dict(self, session: FocusSession) -> Dict[str, Any]:
        """将专注会话对象转换为字典"""
        return {
            "id": session.id,
            "user_id": session.user_id,
            "task_id": session.task_id,
            "session_type": session.session_type,
            "planned_duration_minutes": session.planned_duration_minutes,
            "actual_duration_minutes": session.actual_duration_minutes,
            "status": session.status,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "pause_time": session.pause_time.isoformat() if session.pause_time else None,
            "resume_time": session.resume_time.isoformat() if session.resume_time else None,
            "interruptions_count": session.interruptions_count,
            "mood_feedback": getattr(session, 'mood_feedback', None),
            "notes": getattr(session, 'notes', None),
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None
        }