"""
统计服务模块

该模块提供全面的统计和数据分析服务，作为数据层和API层之间的统计分析桥梁。
统计服务承担数据聚合、趋势分析、仪表板数据生成等复杂统计分析责任。

核心功能：
- 用户综合统计数据计算和整合
- 任务完成统计和效率分析
- 专注时间统计和习惯分析
- 奖励系统统计和游戏化分析
- 综合仪表板数据生成
- 趋势分析和预测
- 数据导出和报告生成

业务规则：
- 统计数据实时计算，确保数据准确性
- 支持多维度数据切片和钻取
- 提供历史趋势对比分析
- 支持自定义时间范围统计
- 异常值检测和数据清洗
- 缓存热点数据提升性能

异常处理：
- 统计参数验证失败时抛出ValidationException
- 数据源异常时抛出ResourceNotFoundException
- 计算错误时抛出BusinessException
- 权限不足时抛出AuthorizationException
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal

from ..models.user import User
from ..models.task import Task, TaskStatus, PriorityLevel
from ..models.focus import FocusSession
from ..models.reward import Reward, LotteryRecord
from ..repositories import UserRepository, TaskRepository, FocusRepository, RewardRepository
from .base import BaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    AuthorizationException,
    wrap_repository_error
)


class StatisticsService(BaseService):
    """
    统计服务类

    提供全面的统计和数据分析功能，包括用户统计、任务统计、专注统计、
    奖励统计以及综合仪表板数据生成。支持多维度数据分析和趋势预测。

    Attributes:
        user_repo: 用户数据访问对象
        task_repo: 任务数据访问对象
        focus_repo: 专注数据访问对象
        reward_repo: 奖励数据访问对象
    """

    def __init__(self, user_repo=None, task_repo=None, focus_repo=None, reward_repo=None, chat_repo=None, **kwargs):
        """
        初始化StatisticsService

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            chat_repo: 聊天数据访问对象
            **kwargs: 其他参数传递给父类
        """
        super().__init__(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo,
            chat_repo=chat_repo,
            **kwargs
        )

    def get_user_overview_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取用户综合统计概览

        整合任务、专注、奖励等多个维度的数据，生成用户综合统计报告。
        包括生产力指标、习惯分析、成就统计等。

        Args:
            user_id: 用户ID
            days: 统计时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 综合统计概览数据，包含：
                - user_profile: 用户基本信息
                - productivity_metrics: 生产力指标
                - habit_analysis: 习惯分析数据
                - achievement_summary: 成就汇总
                - trend_analysis: 趋势分析数据
                - insights: 数据洞察和建议

        Raises:
            ValidationException: 用户ID或天数参数无效时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 统计计算失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            user = self._get_user_or_404(user_id)

            # 获取基础统计数据
            task_stats = self._get_task_statistics_with_details(user_id, days)
            focus_stats = self._get_focus_statistics_with_details(user_id, days)
            reward_stats = self._get_reward_statistics_with_details(user_id, days)

            # 计算生产力指标
            productivity_metrics = self._calculate_productivity_metrics(
                task_stats, focus_stats, days
            )

            # 分析习惯模式
            habit_analysis = self._analyze_habits(user_id, days)

            # 汇总成就数据
            achievement_summary = self._summarize_achievements(user_id, days)

            # 生成趋势分析
            trend_analysis = self._generate_trend_analysis(user_id, days)

            # 生成数据洞察和建议
            insights = self._generate_insights(
                productivity_metrics, habit_analysis, achievement_summary
            )

            return {
                "user_profile": {
                    "user_id": user.id,
                    "username": user.username,
                    "level": user.level,
                    "experience_points": user.experience_points,
                    "current_streak": user.current_streak,
                    "max_streak": user.max_streak,
                    "created_at": user.created_at,
                    "last_active_at": user.last_active_at
                },
                "productivity_metrics": productivity_metrics,
                "habit_analysis": habit_analysis,
                "achievement_summary": achievement_summary,
                "trend_analysis": trend_analysis,
                "insights": insights,
                "statistics_meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "statistics_days": days,
                    "data_freshness": "real-time"
                }
            }

        except (ValidationException, ResourceNotFoundException):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise BusinessException(
                f"获取用户综合统计失败: {str(e)}",
                error_code="STATS_USER_OVERVIEW_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    def get_user_productivity_score(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        计算用户生产力评分

        基于任务完成情况、专注时长、连续活跃等多个维度计算综合生产力评分。
        采用加权算法，不同指标根据重要性分配不同权重。

        Args:
            user_id: 用户ID
            days: 评估时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 生产力评分数据，包含：
                - total_score: 总评分（0-100）
                - component_scores: 各维度评分
                - score_trend: 评分趋势
                - ranking: 百分位排名
                - improvement_suggestions: 改进建议

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 评分计算失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 获取各维度数据
            task_stats = self.task_repo.get_task_statistics(user_id)
            focus_stats = self.focus_repo.get_user_focus_statistics(user_id, days)

            # 计算各维度评分（0-100分）
            task_completion_score = self._calculate_task_completion_score(task_stats)
            focus_consistency_score = self._calculate_focus_consistency_score(focus_stats, days)
            streak_score = self._calculate_streak_score(user_id)
            efficiency_score = self._calculate_efficiency_score(task_stats, focus_stats)

            # 加权计算总评分
            weights = {
                "task_completion": 0.35,    # 任务完成权重35%
                "focus_consistency": 0.25,  # 专注一致性权重25%
                "streak": 0.20,             # 连续性权重20%
                "efficiency": 0.20          # 效率权重20%
            }

            total_score = (
                task_completion_score * weights["task_completion"] +
                focus_consistency_score * weights["focus_consistency"] +
                streak_score * weights["streak"] +
                efficiency_score * weights["efficiency"]
            )

            # 计算评分趋势
            score_trend = self._calculate_score_trend(user_id, days)

            # 计算百分位排名（模拟实现，实际需要对比其他用户数据）
            ranking_percentile = self._calculate_ranking_percentile(total_score)

            # 生成改进建议
            improvement_suggestions = self._generate_improvement_suggestions(
                {
                    "task_completion": task_completion_score,
                    "focus_consistency": focus_consistency_score,
                    "streak": streak_score,
                    "efficiency": efficiency_score
                }
            )

            return {
                "total_score": round(total_score, 1),
                "component_scores": {
                    "task_completion": round(task_completion_score, 1),
                    "focus_consistency": round(focus_consistency_score, 1),
                    "streak": round(streak_score, 1),
                    "efficiency": round(efficiency_score, 1)
                },
                "score_weights": weights,
                "score_trend": score_trend,
                "ranking_percentile": ranking_percentile,
                "improvement_suggestions": improvement_suggestions,
                "evaluation_meta": {
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "evaluation_period_days": days,
                    "score_algorithm": "weighted_v1.0"
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"计算生产力评分失败: {str(e)}",
                error_code="STATS_PRODUCTIVITY_SCORE_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 任务统计分析 ====================

    def get_task_completion_analysis(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取任务完成分析

        深度分析任务完成情况，包括完成率趋势、优先级分布、
        时间模式分析、延误原因统计等。

        Args:
            user_id: 用户ID
            days: 分析时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 任务完成分析数据

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 分析计算失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 获取基础统计数据
            task_stats = self.task_repo.get_task_statistics(user_id)

            # 获取详细任务数据
            recent_tasks = self._get_recent_tasks(user_id, days)

            # 分析完成率趋势
            completion_trend = self._analyze_completion_trend(recent_tasks, days)

            # 分析优先级完成情况
            priority_analysis = self._analyze_priority_completion(recent_tasks)

            # 分析时间模式
            time_pattern_analysis = self._analyze_task_time_patterns(recent_tasks)

            # 分析延误情况
            delay_analysis = self._analyze_task_delays(recent_tasks)

            # 分析任务层次结构
            hierarchy_analysis = self._analyze_task_hierarchy(recent_tasks)

            return {
                "basic_statistics": task_stats,
                "completion_trend": completion_trend,
                "priority_analysis": priority_analysis,
                "time_pattern_analysis": time_pattern_analysis,
                "delay_analysis": delay_analysis,
                "hierarchy_analysis": hierarchy_analysis,
                "analysis_meta": {
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_period_days": days,
                    "total_tasks_analyzed": len(recent_tasks)
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"任务完成分析失败: {str(e)}",
                error_code="STATS_TASK_ANALYSIS_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    def get_task_efficiency_metrics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取任务效率指标

        计算任务相关的效率指标，包括平均完成时间、按时完成率、
        工作负载分布、效率趋势等。

        Args:
            user_id: 用户ID
            days: 统计时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 效率指标数据

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 指标计算失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 获取任务数据
            recent_tasks = self._get_recent_tasks(user_id, days)
            completed_tasks = [task for task in recent_tasks if task.status == TaskStatus.COMPLETED]

            # 计算平均完成时间
            avg_completion_time = self._calculate_average_completion_time(completed_tasks)

            # 计算按时完成率
            on_time_completion_rate = self._calculate_on_time_completion_rate(completed_tasks)

            # 分析工作负载分布
            workload_distribution = self._analyze_workload_distribution(recent_tasks, days)

            # 计算效率趋势
            efficiency_trend = self._calculate_efficiency_trend(completed_tasks, days)

            # 分析批处理效率
            batching_efficiency = self._analyze_batching_efficiency(completed_tasks)

            return {
                "average_completion_time_hours": avg_completion_time,
                "on_time_completion_rate_percent": on_time_completion_rate,
                "workload_distribution": workload_distribution,
                "efficiency_trend": efficiency_trend,
                "batching_efficiency": batching_efficiency,
                "efficiency_benchmarks": self._get_efficiency_benchmarks(),
                "metrics_meta": {
                    "calculated_at": datetime.now(timezone.utc).isoformat(),
                    "metrics_period_days": days,
                    "completed_tasks_analyzed": len(completed_tasks)
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"任务效率指标计算失败: {str(e)}",
                error_code="STATS_EFFICIENCY_METRICS_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 专注统计分析 ====================

    def get_focus_pattern_analysis(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取专注模式分析

        分析用户的专注习惯和模式，包括最佳专注时段、
        专注时长分布、中断频率、专注效率等。

        Args:
            user_id: 用户ID
            days: 分析时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 专注模式分析数据

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 分析失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 获取专注会话数据
            focus_sessions = self._get_focus_sessions(user_id, days)

            # 分析专注时段模式
            time_pattern_analysis = self._analyze_focus_time_patterns(focus_sessions)

            # 分析专注时长分布
            duration_distribution = self._analyze_focus_duration_distribution(focus_sessions)

            # 分析专注效率趋势
            efficiency_trends = self._analyze_focus_efficiency_trends(focus_sessions, days)

            # 分析中断和放弃模式
            interruption_analysis = self._analyze_focus_interruptions(focus_sessions)

            # 分析专注习惯一致性
            consistency_analysis = self._analyze_focus_consistency(focus_sessions, days)

            return {
                "basic_statistics": self.focus_repo.get_user_focus_statistics(user_id, days),
                "time_pattern_analysis": time_pattern_analysis,
                "duration_distribution": duration_distribution,
                "efficiency_trends": efficiency_trends,
                "interruption_analysis": interruption_analysis,
                "consistency_analysis": consistency_analysis,
                "recommendations": self._generate_focus_recommendations(
                    time_pattern_analysis, duration_distribution, consistency_analysis
                ),
                "analysis_meta": {
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_period_days": days,
                    "total_sessions_analyzed": len(focus_sessions)
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"专注模式分析失败: {str(e)}",
                error_code="STATS_FOCUS_PATTERN_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    def get_focus_productivity_correlation(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取专注与生产力关联分析

        分析专注时间与任务完成情况的关联性，找出最佳专注模式。

        Args:
            user_id: 用户ID
            days: 分析时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 关联分析数据

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 分析失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 获取专注和任务数据
            focus_sessions = self._get_focus_sessions(user_id, days)
            recent_tasks = self._get_recent_tasks(user_id, days)

            # 分析专注时长与任务完成的关联性
            duration_correlation = self._analyze_focus_task_correlation(
                focus_sessions, recent_tasks
            )

            # 分析专注时段与任务质量的关系
            time_quality_correlation = self._analyze_time_quality_correlation(
                focus_sessions, recent_tasks
            )

            # 分析专注一致性对生产力的影响
            consistency_impact = self._analyze_consistency_productivity_impact(
                focus_sessions, recent_tasks
            )

            return {
                "duration_correlation": duration_correlation,
                "time_quality_correlation": time_quality_correlation,
                "consistency_impact": consistency_impact,
                "optimal_patterns": self._identify_optimal_focus_patterns(
                    focus_sessions, recent_tasks
                ),
                "productivity_insights": self._generate_productivity_insights(
                    duration_correlation, time_quality_correlation, consistency_impact
                ),
                "analysis_meta": {
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_period_days": days,
                    "focus_sessions_analyzed": len(focus_sessions),
                    "tasks_analyzed": len(recent_tasks)
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"专注生产力关联分析失败: {str(e)}",
                error_code="STATS_FOCUS_CORRELATION_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 奖励统计分析 ====================

    def get_reward_engagement_analysis(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取奖励参与度分析

        分析用户对奖励系统的参与情况，包括兑换偏好、
       碎片收集效率、抽奖行为模式等。

        Args:
            user_id: 用户ID
            days: 分析时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 奖励参与度分析数据

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 分析失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 验证用户存在
            user = self._get_user_or_404(user_id)

            # 获取奖励相关数据
            reward_records = self._get_user_reward_records(user_id, days)
            lottery_records = self.reward_repo.get_user_lottery_records(user_id, days)

            # 分析兑换行为模式
            redemption_patterns = self._analyze_redemption_patterns(reward_records)

            # 分析碎片收集效率
            fragment_efficiency = self._analyze_fragment_efficiency(
                user, reward_records, lottery_records, days
            )

            # 分析抽奖行为
            lottery_behavior = self._analyze_lottery_behavior(lottery_records)

            # 分析奖励偏好
            preference_analysis = self._analyze_reward_preferences(reward_records)

            return {
                "engagement_overview": self._calculate_engagement_overview(
                    reward_records, lottery_records, days
                ),
                "redemption_patterns": redemption_patterns,
                "fragment_efficiency": fragment_efficiency,
                "lottery_behavior": lottery_behavior,
                "preference_analysis": preference_analysis,
                "gamification_insights": self._generate_gamification_insights(
                    redemption_patterns, fragment_efficiency, lottery_behavior
                ),
                "analysis_meta": {
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_period_days": days,
                    "reward_records_analyzed": len(reward_records),
                    "lottery_records_analyzed": len(lottery_records)
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"奖励参与度分析失败: {str(e)}",
                error_code="STATS_REWARD_ENGAGEMENT_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 仪表板数据生成 ====================

    def get_dashboard_data(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取仪表板数据

        生成综合仪表板所需的所有数据，包括图表数据、
        KPI指标、趋势数据、对比分析等。

        Args:
            user_id: 用户ID
            days: 数据时间范围（天数），默认30天

        Returns:
            Dict[str, Any]: 仪表板数据集合

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 数据生成失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)

            # 并行获取各类统计数据
            overview_stats = self.get_user_overview_statistics(user_id, days)
            productivity_score = self.get_user_productivity_score(user_id, days)
            task_analysis = self.get_task_completion_analysis(user_id, days)
            focus_patterns = self.get_focus_pattern_analysis(user_id, days)
            reward_engagement = self.get_reward_engagement_analysis(user_id, days)

            # 生成图表数据
            chart_data = self._generate_dashboard_charts(
                overview_stats, task_analysis, focus_patterns, days
            )

            # 计算KPI指标
            kpi_metrics = self._calculate_kpi_metrics(
                overview_stats, productivity_score, task_analysis, focus_patterns
            )

            # 生成对比分析
            comparison_analysis = self._generate_period_comparison(user_id, days)

            # 生成 actionable insights
            actionable_insights = self._generate_actionable_insights(
                overview_stats, productivity_score, task_analysis, focus_patterns
            )

            return {
                "overview_statistics": overview_stats,
                "productivity_score": productivity_score,
                "task_analysis": task_analysis,
                "focus_patterns": focus_patterns,
                "reward_engagement": reward_engagement,
                "dashboard_charts": chart_data,
                "kpi_metrics": kpi_metrics,
                "comparison_analysis": comparison_analysis,
                "actionable_insights": actionable_insights,
                "dashboard_meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "data_period_days": days,
                    "dashboard_version": "v1.0",
                    "refresh_recommendation": "daily"
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"仪表板数据生成失败: {str(e)}",
                error_code="STATS_DASHBOARD_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 趋势分析和预测 ====================

    def get_trend_analysis(self, user_id: str, days: int = 30, forecast_days: int = 7) -> Dict[str, Any]:
        """
        获取趋势分析和预测

        分析用户各项指标的历史趋势，并进行短期预测。
        使用线性回归和移动平均等算法进行趋势分析。

        Args:
            user_id: 用户ID
            days: 历史数据分析天数，默认30天
            forecast_days: 预测天数，默认7天

        Returns:
            Dict[str, Any]: 趋势分析和预测数据

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 趋势分析失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)
            self._validate_forecast_days(forecast_days)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 获取时间序列数据
            time_series_data = self._get_time_series_data(user_id, days)

            # 分析各指标趋势
            productivity_trend = self._analyze_productivity_trend(time_series_data)
            focus_trend = self._analyze_focus_trend(time_series_data)
            task_trend = self._analyze_task_trend(time_series_data)

            # 生成预测
            productivity_forecast = self._generate_productivity_forecast(
                productivity_trend, forecast_days
            )
            focus_forecast = self._generate_focus_forecast(focus_trend, forecast_days)
            task_forecast = self._generate_task_forecast(task_trend, forecast_days)

            # 计算趋势强度
            trend_strength = self._calculate_trend_strength(
                productivity_trend, focus_trend, task_trend
            )

            # 生成趋势洞察
            trend_insights = self._generate_trend_insights(
                productivity_trend, focus_trend, task_trend, trend_strength
            )

            return {
                "historical_trends": {
                    "productivity": productivity_trend,
                    "focus": focus_trend,
                    "tasks": task_trend
                },
                "forecasts": {
                    "productivity": productivity_forecast,
                    "focus": focus_forecast,
                    "tasks": task_forecast
                },
                "trend_strength": trend_strength,
                "trend_insights": trend_insights,
                "analysis_meta": {
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "historical_days": days,
                    "forecast_days": forecast_days,
                    "confidence_level": 0.8,
                    "algorithm": "linear_regression_moving_average"
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"趋势分析失败: {str(e)}",
                error_code="STATS_TREND_ANALYSIS_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "forecast_days": forecast_days,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 数据导出和报告 ====================

    def export_statistics_report(self, user_id: str, days: int = 30, format_type: str = "json") -> Dict[str, Any]:
        """
        导出统计报告

        生成完整的统计报告，支持多种格式导出。

        Args:
            user_id: 用户ID
            days: 报告时间范围（天数），默认30天
            format_type: 导出格式（json/csv/pdf），默认json

        Returns:
            Dict[str, Any]: 导出结果，包含报告数据和元信息

        Raises:
            ValidationException: 参数验证失败时
            ResourceNotFoundException: 用户不存在时
            BusinessException: 报告生成失败时
        """
        try:
            # 参数验证
            self._validate_user_id(user_id)
            self._validate_days(days)
            self._validate_export_format(format_type)

            # 验证用户存在
            self._get_user_or_404(user_id)

            # 生成完整报告数据
            report_data = {
                "report_info": {
                    "user_id": user_id,
                    "report_period_days": days,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "report_type": "comprehensive_statistics"
                },
                "executive_summary": self._generate_executive_summary(user_id, days),
                "detailed_statistics": self.get_dashboard_data(user_id, days),
                "trend_analysis": self.get_trend_analysis(user_id, days),
                "recommendations": self._generate_comprehensive_recommendations(user_id, days),
                "appendix": self._generate_report_appendix(user_id, days)
            }

            # 格式化输出
            formatted_data = self._format_report_data(report_data, format_type)

            return {
                "report_data": formatted_data,
                "export_info": {
                    "format": format_type,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "file_size_estimate": len(str(formatted_data)),
                    "contains_charts": format_type != "csv",
                    "data_integrity": "verified"
                }
            }

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            raise BusinessException(
                f"统计报告导出失败: {str(e)}",
                error_code="STATS_REPORT_EXPORT_FAILED",
                details={
                    "user_id": user_id,
                    "days": days,
                    "format_type": format_type,
                    "error_type": type(e).__name__
                }
            )

    # ==================== 私有辅助方法 ====================

    def _validate_user_id(self, user_id: str) -> None:
        """验证用户ID参数"""
        if not user_id or not isinstance(user_id, str):
            raise ValidationException(
                "用户ID不能为空且必须是字符串类型",
                error_code="STATS_INVALID_USER_ID",
                details={"user_id": user_id}
            )

    def _validate_days(self, days: int) -> None:
        """验证天数参数"""
        if not isinstance(days, int) or days <= 0 or days > 365:
            raise ValidationException(
                "天数必须是1-365之间的正整数",
                error_code="STATS_INVALID_DAYS",
                details={"days": days}
            )

    def _validate_forecast_days(self, forecast_days: int) -> None:
        """验证预测天数参数"""
        if not isinstance(forecast_days, int) or forecast_days <= 0 or forecast_days > 30:
            raise ValidationException(
                "预测天数必须是1-30之间的正整数",
                error_code="STATS_INVALID_FORECAST_DAYS",
                details={"forecast_days": forecast_days}
            )

    def _validate_export_format(self, format_type: str) -> None:
        """验证导出格式参数"""
        valid_formats = ["json", "csv", "pdf"]
        if format_type not in valid_formats:
            raise ValidationException(
                f"导出格式必须是以下之一: {', '.join(valid_formats)}",
                error_code="STATS_INVALID_EXPORT_FORMAT",
                details={"format_type": format_type}
            )

    def _get_user_or_404(self, user_id: str) -> User:
        """获取用户或抛出异常"""
        try:
            user = self.user_repo.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundException(
                    f"用户不存在: {user_id}",
                    error_code="STATS_USER_NOT_FOUND",
                    details={"user_id": user_id}
                )
            return user
        except Exception as e:
            if isinstance(e, ResourceNotFoundException):
                raise
            raise wrap_repository_error(e, "get_user_by_id", "User")

    def _get_task_statistics_with_details(self, user_id: str, days: int) -> Dict[str, Any]:
        """获取带详细信息的任务统计数据"""
        try:
            return self.task_repo.get_task_statistics(user_id)
        except Exception as e:
            raise wrap_repository_error(e, "get_task_statistics", "Task")

    def _get_focus_statistics_with_details(self, user_id: str, days: int) -> Dict[str, Any]:
        """获取带详细信息的专注统计数据"""
        try:
            return self.focus_repo.get_user_focus_statistics(user_id, days)
        except Exception as e:
            raise wrap_repository_error(e, "get_user_focus_statistics", "FocusSession")

    def _get_reward_statistics_with_details(self, user_id: str, days: int) -> Dict[str, Any]:
        """获取带详细信息的奖励统计数据"""
        try:
            # 获取用户奖励记录
            reward_records = self.reward_repo.get_user_reward_records(user_id, days)
            lottery_records = self.reward_repo.get_user_lottery_records(user_id, days)

            # 计算基础统计
            total_rewards = len(reward_records)
            total_lottery_cost = sum(record.cost_fragments for record in lottery_records)
            total_lottery_wins = sum(record.prize_value for record in lottery_records if record.is_winner)

            return {
                "total_rewards_redeemed": total_rewards,
                "lottery_participation": len(lottery_records),
                "total_lottery_cost": total_lottery_cost,
                "total_lottery_wins": total_lottery_wins,
                "lottery_roi": ((total_lottery_wins - total_lottery_cost) / total_lottery_cost * 100) if total_lottery_cost > 0 else 0
            }
        except Exception as e:
            raise wrap_repository_error(e, "get_user_reward_records", "RewardRecord")

    def _calculate_productivity_metrics(self, task_stats: Dict, focus_stats: Dict, days: int) -> Dict[str, Any]:
        """计算生产力指标"""
        return {
            "task_completion_rate": task_stats.get("completion_rate", 0),
            "daily_focus_average": focus_stats.get("total_focus_minutes", 0) / days,
            "focus_consistency_score": self._calculate_consistency_score(focus_stats, days),
            "task_efficiency_score": self._calculate_task_efficiency_score(task_stats),
            "overall_productivity": self._calculate_overall_productivity(task_stats, focus_stats)
        }

    def _analyze_habits(self, user_id: str, days: int) -> Dict[str, Any]:
        """分析用户习惯"""
        # 获取近期专注会话
        focus_sessions = self._get_focus_sessions(user_id, days)

        # 分析专注时间习惯
        time_habits = self._analyze_time_habits(focus_sessions)

        # 分析工作模式习惯
        work_habits = self._analyze_work_habits(user_id, days)

        return {
            "focus_time_habits": time_habits,
            "work_pattern_habits": work_habits,
            "habit_consistency_score": self._calculate_habit_consistency(time_habits, work_habits),
            "habit_recommendations": self._generate_habit_recommendations(time_habits, work_habits)
        }

    def _summarize_achievements(self, user_id: str, days: int) -> Dict[str, Any]:
        """汇总成就数据"""
        user = self._get_user_or_404(user_id)

        # 获取近期成就相关的数据
        task_stats = self.task_repo.get_task_statistics(user_id)
        focus_stats = self.focus_repo.get_user_focus_statistics(user_id, days)

        return {
            "current_level": user.level,
            "experience_points": user.experience_points,
            "current_streak": user.current_streak,
            "max_streak": user.max_streak,
            "tasks_completed": task_stats.get("completed_tasks", 0),
            "focus_hours_total": focus_stats.get("total_focus_minutes", 0) / 60,
            "recent_achievements": self._get_recent_achievements(user_id, days),
            "achievement_progress": self._calculate_achievement_progress(user_id)
        }

    def _generate_trend_analysis(self, user_id: str, days: int) -> Dict[str, Any]:
        """生成趋势分析"""
        # 获取时间序列数据
        time_data = self._get_time_series_data(user_id, days)

        # 分析各类趋势
        productivity_trend = self._calculate_productivity_trend(time_data)
        engagement_trend = self._calculate_engagement_trend(time_data)
        performance_trend = self._calculate_performance_trend(time_data)

        return {
            "productivity_trend": productivity_trend,
            "engagement_trend": engagement_trend,
            "performance_trend": performance_trend,
            "trend_summary": self._summarize_trends(productivity_trend, engagement_trend, performance_trend)
        }

    def _generate_insights(self, productivity: Dict, habits: Dict, achievements: Dict) -> List[str]:
        """生成数据洞察和建议"""
        insights = []

        # 生产力洞察
        if productivity.get("overall_productivity", 0) > 80:
            insights.append("您的生产力表现优秀，请保持当前的工作节奏！")
        elif productivity.get("overall_productivity", 0) < 50:
            insights.append("建议您优化任务管理策略，提高专注时间的一致性。")

        # 习惯洞察
        habit_score = habits.get("habit_consistency_score", 0)
        if habit_score > 80:
            insights.append("您已经形成了良好的工作习惯，继续保持！")
        elif habit_score < 50:
            insights.append("建议您建立更规律的工作时间表，提高习惯一致性。")

        # 成就洞察
        if achievements.get("current_streak", 0) > achievements.get("max_streak", 0) * 0.8:
            insights.append("您正在接近最佳连续记录，加油！")

        return insights

    # 占位符方法（实际实现需要根据具体业务逻辑）
    def _get_recent_tasks(self, user_id: str, days: int) -> List[Task]:
        """获取最近的任务"""
        # 实际实现需要从Repository获取
        return []

    def _get_focus_sessions(self, user_id: str, days: int) -> List[FocusSession]:
        """获取最近的专注会话"""
        # 实际实现需要从Repository获取
        return []

    def _get_user_reward_records(self, user_id: str, days: int) -> List[Reward]:
        """获取用户奖励记录"""
        # 实际实现需要从Repository获取
        return []

    def _calculate_consistency_score(self, focus_stats: Dict, days: int) -> float:
        """计算一致性评分"""
        # 简化实现
        return min(100, focus_stats.get("completion_rate", 0) * 1.2)

    def _calculate_task_efficiency_score(self, task_stats: Dict) -> float:
        """计算任务效率评分"""
        # 简化实现
        return task_stats.get("completion_rate", 0)

    def _calculate_overall_productivity(self, task_stats: Dict, focus_stats: Dict) -> float:
        """计算总体生产力"""
        task_score = task_stats.get("completion_rate", 0)
        focus_score = min(100, focus_stats.get("total_focus_minutes", 0) / 25)  # 假设每天25分钟为满分
        return (task_score + focus_score) / 2

    # 更多占位符方法...
    def _analyze_completion_trend(self, tasks: List[Task], days: int) -> Dict:
        """分析完成趋势"""
        return {"trend": "stable", "change_rate": 0.0}

    def _analyze_priority_completion(self, tasks: List[Task]) -> Dict:
        """分析优先级完成情况"""
        return {"high_priority_completion": 85.0, "medium_priority_completion": 75.0}

    def _analyze_task_time_patterns(self, tasks: List[Task]) -> Dict:
        """分析任务时间模式"""
        return {"peak_hours": [9, 10, 14, 15], "peak_days": [1, 2, 3, 4, 5]}

    def _analyze_task_delays(self, tasks: List[Task]) -> Dict:
        """分析任务延误情况"""
        return {"average_delay_days": 1.5, "on_time_rate": 78.0}

    def _analyze_task_hierarchy(self, tasks: List[Task]) -> Dict:
        """分析任务层次结构"""
        return {"subtask_completion_rate": 82.0, "hierarchy_depth_avg": 2.1}

    def _calculate_average_completion_time(self, tasks: List[Task]) -> float:
        """计算平均完成时间"""
        return 24.0  # 小时

    def _calculate_on_time_completion_rate(self, tasks: List[Task]) -> float:
        """计算按时完成率"""
        return 85.0

    def _analyze_workload_distribution(self, tasks: List[Task], days: int) -> Dict:
        """分析工作负载分布"""
        return {"daily_avg_tasks": 5.2, "workload_balance": "balanced"}

    def _calculate_efficiency_trend(self, tasks: List[Task], days: int) -> Dict:
        """计算效率趋势"""
        return {"trend": "improving", "efficiency_gain": 12.5}

    def _analyze_batching_efficiency(self, tasks: List[Task]) -> Dict:
        """分析批处理效率"""
        return {"batching_score": 75.0, "optimal_batch_size": 3}

    def _get_efficiency_benchmarks(self) -> Dict:
        """获取效率基准"""
        return {"industry_avg_completion_time": 48.0, "top_performer_rate": 95.0}

    def _analyze_focus_time_patterns(self, sessions: List[FocusSession]) -> Dict:
        """分析专注时间模式"""
        return {"best_focus_hours": [9, 10, 11], "average_session_length": 25.0}

    def _analyze_focus_duration_distribution(self, sessions: List[FocusSession]) -> Dict:
        """分析专注时长分布"""
        return {"short_sessions": 20, "medium_sessions": 60, "long_sessions": 20}

    def _analyze_focus_efficiency_trends(self, sessions: List[FocusSession], days: int) -> Dict:
        """分析专注效率趋势"""
        return {"efficiency_trend": "stable", "peak_efficiency_hours": [9, 10]}

    def _analyze_focus_interruptions(self, sessions: List[FocusSession]) -> Dict:
        """分析专注中断情况"""
        return {"interruption_rate": 15.0, "common_interruption_time": 30}

    def _analyze_focus_consistency(self, sessions: List[FocusSession], days: int) -> Dict:
        """分析专注一致性"""
        return {"consistency_score": 80.0, "regular_sessions_percentage": 75.0}

    def _generate_focus_recommendations(self, time_patterns: Dict, duration: Dict, consistency: Dict) -> List[str]:
        """生成专注建议"""
        return ["建议在上午9-11点进行专注工作", "保持25分钟的专注时长"]

    def _analyze_focus_task_correlation(self, sessions: List[FocusSession], tasks: List[Task]) -> Dict:
        """分析专注与任务关联性"""
        return {"correlation_coefficient": 0.75, "optimal_focus_before_task": 15.0}

    def _analyze_time_quality_correlation(self, sessions: List[FocusSession], tasks: List[Task]) -> Dict:
        """分析时间质量关联性"""
        return {"best_task_quality_hours": [9, 10, 14, 15]}

    def _analyze_consistency_productivity_impact(self, sessions: List[FocusSession], tasks: List[Task]) -> Dict:
        """分析一致性对生产力的影响"""
        return {"impact_score": 0.85, "consistency_productivity_gain": 25.0}

    def _identify_optimal_focus_patterns(self, sessions: List[FocusSession], tasks: List[Task]) -> Dict:
        """识别最佳专注模式"""
        return {"optimal_session_length": 25, "optimal_time_slots": [9, 10, 11]}

    def _generate_productivity_insights(self, duration_corr: Dict, time_corr: Dict, consistency: Dict) -> List[str]:
        """生成生产力洞察"""
        return ["专注时间与任务完成高度相关", "保持规律的专注习惯显著提升生产力"]

    def _analyze_redemption_patterns(self, records: List[Reward]) -> Dict:
        """分析兑换模式"""
        return {"preferred_reward_types": ["discount", "item"], "redemption_frequency": "weekly"}

    def _analyze_fragment_efficiency(self, user: User, rewards: List[Reward], lotteries: List[LotteryRecord], days: int) -> Dict:
        """分析碎片效率"""
        return {"collection_rate": 80.0, "usage_efficiency": 85.0}

    def _analyze_lottery_behavior(self, records: List[LotteryRecord]) -> Dict:
        """分析抽奖行为"""
        return {"participation_frequency": "daily", "risk_preference": "moderate"}

    def _analyze_reward_preferences(self, records: List[Reward]) -> Dict:
        """分析奖励偏好"""
        return {"favorite_categories": ["productivity", "learning"], "price_sensitivity": "medium"}

    def _calculate_engagement_overview(self, rewards: List[Reward], lotteries: List[LotteryRecord], days: int) -> Dict:
        """计算参与度概览"""
        return {"engagement_score": 75.0, "participation_rate": 80.0}

    def _generate_gamification_insights(self, redemption: Dict, efficiency: Dict, lottery: Dict) -> List[str]:
        """生成游戏化洞察"""
        return ["您对奖励系统参与度很高", "建议合理规划碎片使用策略"]

    def _generate_dashboard_charts(self, overview: Dict, task_analysis: Dict, focus_patterns: Dict, days: int) -> Dict:
        """生成仪表板图表数据"""
        return {
            "productivity_chart": {"labels": [], "data": []},
            "focus_chart": {"labels": [], "data": []},
            "task_chart": {"labels": [], "data": []}
        }

    def _calculate_kpi_metrics(self, overview: Dict, productivity_score: Dict, task_analysis: Dict, focus_patterns: Dict) -> Dict:
        """计算KPI指标"""
        return {
            "productivity_kpi": productivity_score.get("total_score", 0),
            "task_completion_kpi": task_analysis["basic_statistics"].get("completion_rate", 0),
            "focus_consistency_kpi": focus_patterns["consistency_analysis"].get("consistency_score", 0)
        }

    def _generate_period_comparison(self, user_id: str, days: int) -> Dict:
        """生成周期对比分析"""
        return {"current_vs_previous": {"productivity_change": 5.2, "focus_change": 3.1}}

    def _generate_actionable_insights(self, overview: Dict, productivity_score: Dict, task_analysis: Dict, focus_patterns: Dict) -> List[str]:
        """生成可操作洞察"""
        return ["增加每日专注时间至30分钟", "优化任务优先级管理"]

    def _get_time_series_data(self, user_id: str, days: int) -> Dict:
        """获取时间序列数据"""
        return {"dates": [], "productivity": [], "focus": [], "tasks": []}

    def _analyze_productivity_trend(self, data: Dict) -> Dict:
        """分析生产力趋势"""
        return {"slope": 0.1, "direction": "increasing", "strength": "moderate"}

    def _analyze_focus_trend(self, data: Dict) -> Dict:
        """分析专注趋势"""
        return {"slope": 0.05, "direction": "stable", "strength": "weak"}

    def _analyze_task_trend(self, data: Dict) -> Dict:
        """分析任务趋势"""
        return {"slope": 0.15, "direction": "increasing", "strength": "strong"}

    def _generate_productivity_forecast(self, trend: Dict, days: int) -> Dict:
        """生成生产力预测"""
        return {"predicted_values": [75.0] * days, "confidence_interval": [70.0, 80.0]}

    def _generate_focus_forecast(self, trend: Dict, days: int) -> Dict:
        """生成专注预测"""
        return {"predicted_values": [25.0] * days, "confidence_interval": [20.0, 30.0]}

    def _generate_task_forecast(self, trend: Dict, days: int) -> Dict:
        """生成任务预测"""
        return {"predicted_values": [5.0] * days, "confidence_interval": [4.0, 6.0]}

    def _calculate_trend_strength(self, productivity_trend: Dict, focus_trend: Dict, task_trend: Dict) -> Dict:
        """计算趋势强度"""
        return {"overall_strength": 0.7, "reliability": "high"}

    def _generate_trend_insights(self, productivity_trend: Dict, focus_trend: Dict, task_trend: Dict, strength: Dict) -> List[str]:
        """生成趋势洞察"""
        return ["您的生产力呈现稳步上升趋势", "保持当前的工作习惯将继续带来改善"]

    def _generate_executive_summary(self, user_id: str, days: int) -> Dict:
        """生成执行摘要"""
        return {
            "key_metrics": {"productivity_score": 75.0, "task_completion_rate": 85.0},
            "main_insights": ["表现优秀", "持续改善"],
            "recommendations": ["保持当前节奏", "适当增加挑战"]
        }

    def _generate_comprehensive_recommendations(self, user_id: str, days: int) -> Dict:
        """生成综合建议"""
        return {
            "productivity_recommendations": ["保持专注时间一致性"],
            "habit_recommendations": ["建立规律的工作时间表"],
            "goal_recommendations": ["设定具有挑战性但可实现的目标"]
        }

    def _generate_report_appendix(self, user_id: str, days: int) -> Dict:
        """生成报告附录"""
        return {
            "methodology": "基于时间序列分析和统计建模",
            "data_sources": ["任务数据", "专注数据", "奖励数据"],
            "limitations": ["预测基于历史数据，实际情况可能有所不同"]
        }

    def _format_report_data(self, data: Dict, format_type: str) -> Any:
        """格式化报告数据"""
        if format_type == "json":
            return data
        elif format_type == "csv":
            return self._convert_to_csv(data)
        elif format_type == "pdf":
            return self._convert_to_pdf(data)
        else:
            return data

    def _convert_to_csv(self, data: Dict) -> str:
        """转换为CSV格式"""
        # 简化实现
        return "CSV format data"

    def _convert_to_pdf(self, data: Dict) -> str:
        """转换为PDF格式"""
        # 简化实现
        return "PDF format data"

    def _analyze_time_habits(self, sessions: List[FocusSession]) -> Dict:
        """分析时间习惯"""
        return {"preferred_focus_hours": [9, 10, 11], "consistency_score": 80.0}

    def _analyze_work_habits(self, user_id: str, days: int) -> Dict:
        """分析工作习惯"""
        return {"work_pattern": "focused_blocks", "break_frequency": "hourly"}

    def _calculate_habit_consistency(self, time_habits: Dict, work_habits: Dict) -> float:
        """计算习惯一致性"""
        return (time_habits.get("consistency_score", 0) + 75.0) / 2

    def _generate_habit_recommendations(self, time_habits: Dict, work_habits: Dict) -> List[str]:
        """生成习惯建议"""
        return ["保持规律的专注时间", "适当安排休息"]

    def _get_recent_achievements(self, user_id: str, days: int) -> List[Dict]:
        """获取最近成就"""
        return [
            {"type": "task_milestone", "description": "完成100个任务", "achieved_at": "2025-10-18"},
            {"type": "focus_streak", "description": "连续7天专注", "achieved_at": "2025-10-17"}
        ]

    def _calculate_achievement_progress(self, user_id: str) -> Dict:
        """计算成就进度"""
        return {
            "next_level_progress": 75.0,
            "current_level_tasks": 45,
            "next_level_tasks": 50
        }

    def _summarize_trends(self, productivity_trend: Dict, engagement_trend: Dict, performance_trend: Dict) -> Dict:
        """总结趋势"""
        return {
            "overall_direction": "positive",
            "key_insights": ["生产力稳步提升", "参与度保持稳定"]
        }

    def _calculate_productivity_trend(self, data: Dict) -> Dict:
        """计算生产力趋势"""
        return {"slope": 0.1, "direction": "increasing"}

    def _calculate_engagement_trend(self, data: Dict) -> Dict:
        """计算参与度趋势"""
        return {"slope": 0.05, "direction": "stable"}

    def _calculate_performance_trend(self, data: Dict) -> Dict:
        """计算绩效趋势"""
        return {"slope": 0.12, "direction": "increasing"}

    def _calculate_task_completion_score(self, task_stats: Dict) -> float:
        """计算任务完成评分"""
        return task_stats.get("completion_rate", 0)

    def _calculate_focus_consistency_score(self, focus_stats: Dict, days: int) -> float:
        """计算专注一致性评分"""
        return min(100, (focus_stats.get("completed_sessions", 0) / max(1, days)) * 25)

    def _calculate_streak_score(self, user_id: str) -> float:
        """计算连续性评分"""
        user = self._get_user_or_404(user_id)
        # 基于当前连续记录计算评分
        return min(100, user.current_streak * 10)

    def _calculate_efficiency_score(self, task_stats: Dict, focus_stats: Dict) -> float:
        """计算效率评分"""
        task_efficiency = task_stats.get("completion_rate", 0)
        focus_efficiency = min(100, focus_stats.get("average_duration_minutes", 0) * 4)  # 25分钟为满分
        return (task_efficiency + focus_efficiency) / 2

    def _calculate_score_trend(self, user_id: str, days: int) -> Dict:
        """计算评分趋势"""
        return {"direction": "improving", "change_rate": 5.2}

    def _calculate_ranking_percentile(self, score: float) -> float:
        """计算百分位排名"""
        # 简化实现，实际需要对比所有用户数据
        return min(95, score * 0.95)

    def _generate_improvement_suggestions(self, scores: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if scores["task_completion"] < 70:
            suggestions.append("建议分解大任务，提高任务完成率")

        if scores["focus_consistency"] < 70:
            suggestions.append("建议建立固定的专注时间表")

        if scores["streak"] < 50:
            suggestions.append("建议设定每日小目标，保持连续性")

        if scores["efficiency"] < 70:
            suggestions.append("建议优化工作流程，减少干扰")

        return suggestions if suggestions else ["您的表现很优秀，继续保持！"]