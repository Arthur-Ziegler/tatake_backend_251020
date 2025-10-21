"""
异步奖励Repository实现

提供奖励相关的异步数据访问层操作，封装奖励业务逻辑查询。
继承自AsyncBaseRepository，专注于奖励特有的业务场景。

功能特性：
1. 异步奖励记录查询（按用户、类型、状态查询）
2. 异步奖励发放和管理（创建、更新、删除奖励记录）
3. 异步奖励统计和分析（积分统计、奖励历史等）
4. 异步业务逻辑封装（积分计算、奖励验证等）
5. 异步用户积分管理（积分增减、积分历史记录）

设计原则：
1. 单一责任：专注于奖励相关的数据访问
2. 异步优先：所有数据库操作都是异步的
3. 查询封装：复杂业务查询封装在Repository方法中
4. 异常统一：使用统一的异常处理机制
5. 类型安全：强类型参数和返回值
6. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建异步奖励Repository
    >>> reward_repo = AsyncRewardRepository(async_session)
    >>>
    >>> # 异步查找用户的所有奖励记录
    >>> rewards = await reward_repo.find_by_user("user123")
    >>>
    >>> # 异步发放奖励
    >>> new_reward = await reward_repo.grant_reward("user123", "task_completed", 50)
    >>>
    >>> # 异步获取用户当前积分
    >>> points = await reward_repo.get_user_points("user123")
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
from src.models.reward import Reward, UserFragment
from src.models.enums import RewardType, RewardStatus


class AsyncRewardRepository(AsyncBaseRepository[Reward]):
    """
    异步奖励Repository类

    提供奖励相关的异步数据库操作，封装奖励业务逻辑查询。
    继承自AsyncBaseRepository，专注于奖励特有的业务场景。

    Attributes:
        session: SQLAlchemy异步会话对象
        model: Reward模型类
    """

    def __init__(self, session: AsyncSession):
        """
        初始化异步奖励Repository

        Args:
            session: SQLAlchemy异步会话对象
        """
        super().__init__(session, Reward)

    async def find_by_user(
        self,
        user_id: str,
        reward_type: Optional[RewardType] = None,
        status: Optional[RewardStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Reward]:
        """
        查找用户的所有奖励记录

        Args:
            user_id: 用户ID
            reward_type: 奖励类型过滤
            status: 奖励状态过滤
            start_date: 开始日期过滤
            end_date: 结束日期过滤
            limit: 结果数量限制

        Returns:
            奖励记录列表

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 构建查询
            statement = select(Reward).where(Reward.user_id == user_id)

            # 奖励类型过滤
            if reward_type:
                statement = statement.where(Reward.reward_type == reward_type)

            # 状态过滤
            if status:
                statement = statement.where(Reward.status == status)

            # 日期范围过滤
            if start_date:
                statement = statement.where(Reward.created_at >= start_date)
            if end_date:
                statement = statement.where(Reward.created_at <= end_date)

            # 按创建时间倒序排列
            statement = statement.order_by(desc(Reward.created_at))

            # 限制结果数量
            if limit:
                statement = statement.limit(limit)

            # 执行查询
            result = await self.session.exec(statement)
            rewards = list(result.all())

            return rewards

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询用户奖励记录失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询用户奖励记录时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def grant_reward(
        self,
        user_id: str,
        reward_type: RewardType,
        points: int,
        reference_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Reward:
        """
        发放奖励

        Args:
            user_id: 用户ID
            reward_type: 奖励类型
            points: 奖励积分
            reference_id: 关联记录ID（如任务ID）
            description: 奖励描述

        Returns:
            创建的奖励记录

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")
            if not isinstance(reward_type, RewardType):
                raise AsyncRepositoryValidationError("奖励类型无效")
            if points <= 0:
                raise AsyncRepositoryValidationError("奖励积分必须大于0")

            now = datetime.now(timezone.utc)
            reward_data = {
                "user_id": user_id,
                "reward_type": reward_type,
                "points": points,
                "status": RewardStatus.GRANTED,
                "reference_id": reference_id,
                "description": description,
                "granted_at": now
            }

            # 创建奖励记录
            reward = await self.create(reward_data)

            # 更新用户积分
            await self._update_user_points(user_id, points)

            return reward

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"发放奖励失败: {str(e)}",
                operation="create",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"发放奖励时发生未知错误: {str(e)}",
                operation="create",
                model_name=self.model_name
            )

    async def revoke_reward(
        self,
        reward_id: str,
        reason: Optional[str] = None
    ) -> Optional[Reward]:
        """
        撤销奖励

        Args:
            reward_id: 奖励记录ID
            reason: 撤销原因

        Returns:
            撤销后的奖励记录，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not reward_id:
                raise AsyncRepositoryValidationError("奖励记录ID不能为空")

            # 查找奖励记录
            reward = await self.get_by_id(reward_id)
            if not reward:
                return None

            if reward.status == RewardStatus.REVOKED:
                return reward  # 已经撤销

            if reward.status != RewardStatus.GRANTED:
                raise AsyncRepositoryValidationError("只有已发放的奖励才能撤销")

            # 撤销奖励
            now = datetime.now(timezone.utc)
            update_data = {
                "status": RewardStatus.REVOKED,
                "revoked_at": now,
                "revoked_reason": reason
            }

            updated_reward = await self.update(reward_id, update_data)

            # 扣除用户积分
            await self._update_user_points(reward.user_id, -reward.points)

            return updated_reward

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"撤销奖励失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"撤销奖励时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def get_user_points(self, user_id: str) -> int:
        """
        获取用户当前碎片数量

        Args:
            user_id: 用户ID

        Returns:
            用户当前碎片数量

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 查询用户碎片记录
            statement = select(UserFragment).where(UserFragment.user_id == user_id)
            result = await self.session.exec(statement)
            user_fragment = result.first()

            return user_fragment.fragment_count if user_fragment else 0

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"获取用户碎片失败: {str(e)}",
                operation="read",
                model_name="UserFragment"
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取用户碎片时发生未知错误: {str(e)}",
                operation="read",
                model_name="UserFragment"
            )

    async def get_reward_statistics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取用户奖励统计信息

        Args:
            user_id: 用户ID
            start_date: 统计开始日期
            end_date: 统计结束日期

        Returns:
            包含奖励统计信息的字典

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 基础过滤条件
            base_filter = Reward.user_id == user_id

            # 日期范围过滤
            if start_date:
                base_filter = and_(base_filter, Reward.created_at >= start_date)
            if end_date:
                base_filter = and_(base_filter, Reward.created_at <= end_date)

            # 总奖励数
            total_result = await self.session.exec(
                select(func.count()).select_from(Reward).where(base_filter)
            )
            total_rewards = total_result.scalar() or 0

            # 按类型统计
            type_result = await self.session.exec(
                select(Reward.reward_type, func.count()).select_from(Reward)
                .where(base_filter).group_by(Reward.reward_type)
            )
            type_counts = dict(type_result.all())

            # 按状态统计
            status_result = await self.session.exec(
                select(Reward.status, func.count()).select_from(Reward)
                .where(base_filter).group_by(Reward.status)
            )
            status_counts = dict(status_result.all())

            # 总获得积分
            granted_points_result = await self.session.exec(
                select(func.sum(Reward.points)).select_from(Reward).where(
                    and_(base_filter, Reward.status == RewardStatus.GRANTED)
                )
            )
            total_granted_points = granted_points_result.scalar() or 0

            # 今日奖励统计
            today = datetime.now(timezone.utc).date()
            today_filter = and_(base_filter, func.date(Reward.created_at) == today)

            today_rewards_result = await self.session.exec(
                select(func.count()).select_from(Reward).where(today_filter)
            )
            today_rewards = today_rewards_result.scalar() or 0

            today_points_result = await self.session.exec(
                select(func.sum(Reward.points)).select_from(Reward).where(
                    and_(today_filter, Reward.status == RewardStatus.GRANTED)
                )
            )
            today_points = today_points_result.scalar() or 0

            # 本周奖励统计
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            week_filter = and_(base_filter, Reward.created_at >= week_ago)

            week_rewards_result = await self.session.exec(
                select(func.count()).select_from(Reward).where(week_filter)
            )
            week_rewards = week_rewards_result.scalar() or 0

            week_points_result = await self.session.exec(
                select(func.sum(Reward.points)).select_from(Reward).where(
                    and_(week_filter, Reward.status == RewardStatus.GRANTED)
                )
            )
            week_points = week_points_result.scalar() or 0

            # 当前用户碎片
            current_fragments = await self.get_user_points(user_id)

            return {
                "current_fragments": current_fragments,
                "total_rewards": total_rewards,
                "by_type": type_counts,
                "by_status": status_counts,
                "total_granted_points": total_granted_points,
                "today": {
                    "rewards": today_rewards,
                    "points": today_points
                },
                "week": {
                    "rewards": week_rewards,
                    "points": week_points
                }
            }

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"获取奖励统计失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取奖励统计时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def _update_user_points(self, user_id: str, points_change: int) -> UserFragment:
        """
        更新用户碎片数量（内部方法）

        Args:
            user_id: 用户ID
            points_change: 碎片变化量（正数为增加，负数为减少）

        Returns:
            更新后的用户碎片记录

        Raises:
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            now = datetime.now(timezone.utc)

            # 查找现有碎片记录
            statement = select(UserFragment).where(UserFragment.user_id == user_id)
            result = await self.session.exec(statement)
            user_fragment = result.first()

            if user_fragment:
                # 更新现有记录
                if points_change > 0:
                    # 增加碎片
                    user_fragment.earn_fragments(points_change)
                else:
                    # 减少碎片
                    user_fragment.spend_fragments(abs(points_change))

                self.session.add(user_fragment)
                await self.session.commit()
                await self.session.refresh(user_fragment)

                return user_fragment
            else:
                # 创建新记录
                new_total = max(0, points_change)  # 确保碎片不为负数
                fragment_data = {
                    "user_id": user_id,
                    "fragment_count": new_total,
                    "total_earned": max(0, points_change) if points_change > 0 else 0,
                    "total_spent": 0,
                    "last_earned_at": now if points_change > 0 else None
                }

                user_fragment = UserFragment(**fragment_data)
                self.session.add(user_fragment)
                await self.session.commit()
                await self.session.refresh(user_fragment)

                return user_fragment

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"更新用户碎片失败: {str(e)}",
                operation="update",
                model_name="UserFragment"
            )
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"更新用户碎片时发生未知错误: {str(e)}",
                operation="update",
                model_name="UserFragment"
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
    "AsyncRewardRepository"
]