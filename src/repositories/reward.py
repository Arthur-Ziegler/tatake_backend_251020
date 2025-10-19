"""
奖励Repository实现

提供奖励相关的数据访问层操作，封装奖励业务逻辑查询。
继承自BaseRepository，专注于奖励系统特有的业务场景。

功能特性：
1. 奖励管理（查询、兑换、状态管理）
2. 用户碎片管理（余额查询、交易记录、碎片发放）
3. 抽奖系统（抽奖记录、中奖概率、奖品统计）
4. 积分流水（交易记录、余额统计、历史查询）
5. 奖励规则管理（规则验证、自动发放）

设计原则：
1. 单一责任：专注于奖励相关的数据访问
2. 查询封装：复杂业务查询封装在Repository方法中
3. 异常统一：使用统一的异常处理机制
4. 类型安全：强类型参数和返回值
5. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建奖励Repository
    >>> reward_repo = RewardRepository(session)
    >>>
    >>> # 查找可用奖励
    >>> rewards = reward_repo.find_available_rewards()
    >>>
    >>> # 兑换奖励
    >>> success = reward_repo.redeem_reward("user123", "reward456")
    >>>
    >>> # 发放碎片奖励
    >>> reward_repo.award_fragments("user123", 50, "专注奖励")
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
import random

from sqlmodel import Session, select, and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

# 导入基础Repository和异常类
from src.repositories.base import BaseRepository, RepositoryError, RepositoryValidationError, RepositoryNotFoundError
from src.models.reward import Reward, RewardRule, UserFragment, LotteryRecord, PointsTransaction
from src.models.enums import RewardType, RewardStatus, TransactionType


class RewardRepository(BaseRepository[Reward]):
    """
    奖励Repository类

    提供奖励相关的数据库操作，封装奖励业务逻辑查询。
    继承自BaseRepository，专注于奖励系统特有的业务场景。

    Attributes:
        session: SQLAlchemy会话对象
        model: Reward模型类
    """

    def __init__(self, session: Session):
        """
        初始化RewardRepository

        Args:
            session: SQLAlchemy会话对象
        """
        super().__init__(session, Reward)

    # ==================== 奖励查询方法 ====================

    def find_available_rewards(self) -> List[Reward]:
        """
        查找所有可用的奖励

        Returns:
            List[Reward]: 可用奖励列表

        Raises:
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> rewards = reward_repo.find_available_rewards()
            >>> print(f"共有 {len(rewards)} 个可用奖励")
            "共有 15 个可用奖励"
        """
        try:
            # 构建查询：查找激活状态的奖励，按价格排序
            statement = select(Reward).where(Reward.is_active == True).order_by(Reward.cost_fragments.asc())

            # 执行查询
            rewards = self.session.exec(statement).all()

            return list(rewards)

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找可用奖励失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找可用奖励时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_reward_type(self, reward_type: RewardType) -> List[Reward]:
        """
        根据奖励类型查找奖励

        Args:
            reward_type: 奖励类型

        Returns:
            List[Reward]: 指定类型的奖励列表

        Raises:
            RepositoryValidationError: 奖励类型参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> badges = reward_repo.find_by_reward_type(RewardType.BADGE)
            >>> print(f"共有 {len(badges)} 个徽章奖励")
            "共有 8 个徽章奖励"
        """
        try:
            # 参数验证
            if not isinstance(reward_type, RewardType):
                raise RepositoryValidationError("奖励类型参数必须是RewardType枚举类型")

            # 构建查询
            statement = select(Reward).where(
                and_(
                    Reward.reward_type == reward_type,
                    Reward.is_active == True
                )
            ).order_by(Reward.cost_fragments.asc())

            # 执行查询
            rewards = self.session.exec(statement).all()

            return list(rewards)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据类型查找奖励失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据类型查找奖励时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_status(self, status: RewardStatus) -> List[Reward]:
        """
        根据状态查找奖励

        Args:
            status: 奖励状态

        Returns:
            List[Reward]: 指定状态的奖励列表

        Raises:
            RepositoryValidationError: 状态参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not isinstance(status, RewardStatus):
                raise RepositoryValidationError("奖励状态参数必须是RewardStatus枚举类型")

            # 构建查询
            statement = select(Reward).where(Reward.status == status).order_by(Reward.created_at.desc())

            # 执行查询
            rewards = self.session.exec(statement).all()

            return list(rewards)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据状态查找奖励失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据状态查找奖励时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_rewards_by_price_range(self, min_price: int, max_price: int) -> List[Reward]:
        """
        根据价格范围查找奖励

        Args:
            min_price: 最低价格
            max_price: 最高价格

        Returns:
            List[Reward]: 指定价格范围内的奖励列表

        Raises:
            RepositoryValidationError: 价格参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not isinstance(min_price, int) or min_price < 0:
                raise RepositoryValidationError("最低价格必须是非负整数")

            if not isinstance(max_price, int) or max_price < 0:
                raise RepositoryValidationError("最高价格必须是非负整数")

            if min_price > max_price:
                raise RepositoryValidationError("最低价格不能高于最高价格")

            # 构建查询
            statement = select(Reward).where(
                and_(
                    Reward.is_active == True,
                    Reward.cost_fragments >= min_price,
                    Reward.cost_fragments <= max_price
                )
            ).order_by(Reward.cost_fragments.asc())

            # 执行查询
            rewards = self.session.exec(statement).all()

            return list(rewards)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据价格范围查找奖励失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据价格范围查找奖励时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    # ==================== 奖励兑换方法 ====================

    def redeem_reward(self, user_id: str, reward_id: str) -> Optional[PointsTransaction]:
        """
        兑换奖励

        Args:
            user_id: 用户ID
            reward_id: 奖励ID

        Returns:
            Optional[PointsTransaction]: 兑换交易记录，失败时返回None

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryNotFoundError: 奖励不存在时
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> transaction = reward_repo.redeem_reward("user123", "reward456")
            >>> if transaction:
            ...     print(f"兑换成功，交易ID: {transaction.id}")
            "兑换成功，交易ID: 123e4567-e89b-12d3-a456-426614174000"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not reward_id or not isinstance(reward_id, str):
                raise RepositoryValidationError("奖励ID参数不能为空且必须是字符串类型")

            # 查找奖励
            reward = self.get_by_id(reward_id)
            if reward is None:
                raise RepositoryNotFoundError(f"未找到ID为 {reward_id} 的奖励")

            # 检查奖励是否可用
            if not reward.is_active:
                raise RepositoryValidationError(f"奖励 {reward_id} 不可用")

            # 验证用户余额
            if not self.validate_user_balance(user_id, reward.cost_fragments):
                raise RepositoryValidationError(f"用户 {user_id} 碎片余额不足，需要 {reward.cost_fragments} 个碎片")

            # 创建兑换交易记录
            transaction_data = {
                "user_id": user_id,
                "transaction_type": TransactionType.SPEND,
                "amount": -reward.cost_fragments,
                "reason": f"兑换奖励: {reward.name}",
                "related_reward_id": reward_id
            }

            return self.create_points_transaction(
                user_id=user_id,
                transaction_type=TransactionType.SPEND,
                amount=-reward.cost_fragments,
                reason=f"兑换奖励: {reward.name}",
                related_reward_id=reward_id
            )

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"兑换奖励失败: {str(e)}",
                operation="create",
                model_name="PointsTransaction"
            )

    def validate_user_balance(self, user_id: str, required_fragments: int) -> bool:
        """
        验证用户碎片余额

        Args:
            user_id: 用户ID
            required_fragments: 需要的碎片数量

        Returns:
            bool: 余额充足返回True，否则返回False

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(required_fragments, int) or required_fragments < 0:
                raise RepositoryValidationError("所需碎片数量必须是非负整数")

            # 获取用户余额
            current_balance = self.get_user_fragment_balance(user_id)

            return current_balance >= required_fragments

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"验证用户余额失败: {str(e)}",
                operation="read",
                model_name="UserFragment"
            )

    def get_user_redeemed_rewards(self, user_id: str) -> List[PointsTransaction]:
        """
        获取用户已兑换的奖励记录

        Args:
            user_id: 用户ID

        Returns:
            List[PointsTransaction]: 兑换记录列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(PointsTransaction).where(
                and_(
                    PointsTransaction.user_id == user_id,
                    PointsTransaction.transaction_type == TransactionType.SPEND,
                    PointsTransaction.related_reward_id.isnot(None)
                )
            ).order_by(PointsTransaction.created_at.desc())

            # 执行查询
            transactions = self.session.exec(statement).all()

            return list(transactions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取用户兑换记录失败: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )
        except Exception as e:
            raise RepositoryError(
                f"获取用户兑换记录时发生未知错误: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )

    # ==================== 用户碎片管理方法 ====================

    def get_user_fragment_balance(self, user_id: str) -> int:
        """
        获取用户碎片余额

        Args:
            user_id: 用户ID

        Returns:
            int: 用户碎片余额，如果没有记录则返回0

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> balance = reward_repo.get_user_fragment_balance("user123")
            >>> print(f"用户碎片余额: {balance}")
            "用户碎片余额: 150"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(UserFragment).where(UserFragment.user_id == user_id)

            # 执行查询
            user_fragment = self.session.exec(statement).first()

            return user_fragment.fragment_count if user_fragment else 0

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取用户碎片余额失败: {str(e)}",
                operation="read",
                model_name="UserFragment"
            )
        except Exception as e:
            raise RepositoryError(
                f"获取用户碎片余额时发生未知错误: {str(e)}",
                operation="read",
                model_name="UserFragment"
            )

    def award_fragments(self, user_id: str, amount: int, reason: str) -> Optional[UserFragment]:
        """
        发放碎片给用户

        Args:
            user_id: 用户ID
            amount: 碎片数量
            reason: 发放原因

        Returns:
            Optional[UserFragment]: 更新后的用户碎片记录

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> user_fragment = reward_repo.award_fragments("user123", 50, "专注奖励")
            >>> print(f"发放成功，当前余额: {user_fragment.fragment_count}")
            "发放成功，当前余额: 150"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(amount, int) or amount <= 0:
                raise RepositoryValidationError("碎片数量必须是正整数")

            if not reason or not isinstance(reason, str):
                raise RepositoryValidationError("发放原因不能为空且必须是字符串类型")

            # 查找现有用户碎片记录
            statement = select(UserFragment).where(UserFragment.user_id == user_id)
            user_fragment = self.session.exec(statement).first()

            if user_fragment:
                # 更新现有记录
                user_fragment.fragment_count += amount
                user_fragment.updated_at = datetime.now(timezone.utc)
            else:
                # 创建新记录
                user_fragment = UserFragment(
                    user_id=user_id,
                    fragment_count=amount
                )
                self.session.add(user_fragment)

            # 提交事务
            self.session.commit()
            self.session.refresh(user_fragment)

            # 创建收入交易记录
            self.create_points_transaction(
                user_id=user_id,
                transaction_type=TransactionType.EARN,
                amount=amount,
                reason=reason
            )

            return user_fragment

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(
                f"发放碎片失败: {str(e)}",
                operation="create_or_update",
                model_name="UserFragment"
            )
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(
                f"发放碎片时发生未知错误: {str(e)}",
                operation="create_or_update",
                model_name="UserFragment"
            )

    def get_user_transaction_history(self, user_id: str, days: int = 30) -> List[PointsTransaction]:
        """
        获取用户积分交易历史

        Args:
            user_id: 用户ID
            days: 查询最近多少天的记录，默认30天

        Returns:
            List[PointsTransaction]: 交易记录列表

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

            # 构建查询
            statement = select(PointsTransaction).where(
                and_(
                    PointsTransaction.user_id == user_id,
                    PointsTransaction.created_at >= threshold_date
                )
            ).order_by(PointsTransaction.created_at.desc())

            # 执行查询
            transactions = self.session.exec(statement).all()

            return list(transactions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取用户交易历史失败: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )
        except Exception as e:
            raise RepositoryError(
                f"获取用户交易历史时发生未知错误: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )

    # ==================== 抽奖管理方法 ====================

    def draw_lottery(self, user_id: str, cost_fragments: int) -> Optional[LotteryRecord]:
        """
        进行抽奖

        Args:
            user_id: 用户ID
            cost_fragments: 消耗的碎片数量

        Returns:
            Optional[LotteryRecord]: 抽奖记录，失败时返回None

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> lottery_record = reward_repo.draw_lottery("user123", 10)
            >>> if lottery_record:
            ...     print(f"抽奖结果: {lottery_record.is_winner}")
            "抽奖结果: True"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(cost_fragments, int) or cost_fragments <= 0:
                raise RepositoryValidationError("消耗碎片数量必须是正整数")

            # 验证用户余额
            if not self.validate_user_balance(user_id, cost_fragments):
                raise RepositoryValidationError(f"用户 {user_id} 碎片余额不足，需要 {cost_fragments} 个碎片")

            # 简化的抽奖逻辑：10%中奖率
            is_winner = random.random() < 0.1

            # 扣除碎片
            self.create_points_transaction(
                user_id=user_id,
                transaction_type=TransactionType.SPEND,
                amount=-cost_fragments,
                reason="抽奖消费"
            )

            # 创建抽奖记录
            lottery_data = {
                "user_id": user_id,
                "cost_fragments": cost_fragments,
                "is_winner": is_winner,
                "prize_name": "幸运奖励" if is_winner else "谢谢参与",
                "prize_value": cost_fragments * 2 if is_winner else 0
            }

            lottery_record = LotteryRecord(**lottery_data)
            self.session.add(lottery_record)
            self.session.commit()
            self.session.refresh(lottery_record)

            # 如果中奖，发放奖励
            if is_winner:
                self.award_fragments(user_id, lottery_record.prize_value, "抽奖奖励")

            return lottery_record

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(
                f"抽奖失败: {str(e)}",
                operation="create",
                model_name="LotteryRecord"
            )
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(
                f"抽奖时发生未知错误: {str(e)}",
                operation="create",
                model_name="LotteryRecord"
            )

    def get_user_lottery_records(self, user_id: str, days: int = 30) -> List[LotteryRecord]:
        """
        获取用户抽奖记录

        Args:
            user_id: 用户ID
            days: 查询最近多少天的记录，默认30天

        Returns:
            List[LotteryRecord]: 抽奖记录列表

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

            # 构建查询
            statement = select(LotteryRecord).where(
                and_(
                    LotteryRecord.user_id == user_id,
                    LotteryRecord.created_at >= threshold_date
                )
            ).order_by(LotteryRecord.created_at.desc())

            # 执行查询
            lottery_records = self.session.exec(statement).all()

            return list(lottery_records)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取用户抽奖记录失败: {str(e)}",
                operation="read",
                model_name="LotteryRecord"
            )
        except Exception as e:
            raise RepositoryError(
                f"获取用户抽奖记录时发生未知错误: {str(e)}",
                operation="read",
                model_name="LotteryRecord"
            )

    def get_lottery_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取抽奖统计信息

        Args:
            days: 统计最近多少天的数据，默认30天

        Returns:
            Dict[str, Any]: 抽奖统计信息字典

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not isinstance(days, int) or days <= 0:
                raise RepositoryValidationError("天数参数必须是正整数")

            # 计算时间阈值
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 统计总抽奖次数
            total_draws_query = select(func.count(LotteryRecord.id)).where(
                LotteryRecord.created_at >= threshold_date
            )
            total_draws = self.session.exec(total_draws_query).one() or 0

            # 统计中奖次数
            wins_query = select(func.count(LotteryRecord.id)).where(
                and_(
                    LotteryRecord.created_at >= threshold_date,
                    LotteryRecord.is_winner == True
                )
            )
            total_wins = self.session.exec(wins_query).one() or 0

            # 统计总消耗碎片
            total_cost_query = select(func.coalesce(func.sum(LotteryRecord.cost_fragments), 0)).where(
                LotteryRecord.created_at >= threshold_date
            )
            total_cost = self.session.exec(total_cost_query).one() or 0

            # 统计总奖励碎片
            total_prize_query = select(func.coalesce(func.sum(LotteryRecord.prize_value), 0)).where(
                LotteryRecord.created_at >= threshold_date
            )
            total_prize = self.session.exec(total_prize_query).one() or 0

            # 计算中奖率
            win_rate = (total_wins / total_draws * 100) if total_draws > 0 else 0

            # 计算收益率
            profit_rate = ((total_prize - total_cost) / total_cost * 100) if total_cost > 0 else 0

            return {
                "total_draws": int(total_draws),
                "total_wins": int(total_wins),
                "win_rate": round(win_rate, 2),
                "total_cost_fragments": int(total_cost),
                "total_prize_fragments": int(total_prize),
                "profit_fragments": int(total_prize - total_cost),
                "profit_rate": round(profit_rate, 2),
                "statistics_days": days
            }

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取抽奖统计失败: {str(e)}",
                operation="read",
                model_name="LotteryRecord"
            )
        except Exception as e:
            raise RepositoryError(
                f"获取抽奖统计时发生未知错误: {str(e)}",
                operation="read",
                model_name="LotteryRecord"
            )

    # ==================== 积分流水方法 ====================

    def create_points_transaction(self, user_id: str, transaction_type: TransactionType, amount: int, reason: str, related_reward_id: str = None) -> PointsTransaction:
        """
        创建积分交易记录

        Args:
            user_id: 用户ID
            transaction_type: 交易类型
            amount: 交易数量
            reason: 交易原因
            related_reward_id: 关联的奖励ID，可选

        Returns:
            PointsTransaction: 创建的交易记录

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> transaction = reward_repo.create_points_transaction(
            ...     user_id="user123",
            ...     transaction_type=TransactionType.EARN,
            ...     amount=50,
            ...     reason="专注奖励"
            ... )
            >>> print(f"交易记录ID: {transaction.id}")
            "交易记录ID: 123e4567-e89b-12d3-a456-426614174000"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(transaction_type, TransactionType):
                raise RepositoryValidationError("交易类型参数必须是TransactionType枚举类型")

            if not isinstance(amount, int):
                raise RepositoryValidationError("交易数量必须是整数类型")

            if not reason or not isinstance(reason, str):
                raise RepositoryValidationError("交易原因不能为空且必须是字符串类型")

            # 创建交易记录
            transaction_data = {
                "user_id": user_id,
                "transaction_type": transaction_type,
                "amount": amount,
                "reason": reason,
                "related_reward_id": related_reward_id
            }

            transaction = PointsTransaction(**transaction_data)
            self.session.add(transaction)
            self.session.commit()
            self.session.refresh(transaction)

            return transaction

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(
                f"创建积分交易记录失败: {str(e)}",
                operation="create",
                model_name="PointsTransaction"
            )
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(
                f"创建积分交易记录时发生未知错误: {str(e)}",
                operation="create",
                model_name="PointsTransaction"
            )

    def get_user_points_history(self, user_id: str, days: int = 30) -> List[PointsTransaction]:
        """
        获取用户积分交易历史

        Args:
            user_id: 用户ID
            days: 查询最近多少天的记录，默认30天

        Returns:
            List[PointsTransaction]: 交易记录列表

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

            # 构建查询
            statement = select(PointsTransaction).where(
                and_(
                    PointsTransaction.user_id == user_id,
                    PointsTransaction.created_at >= threshold_date
                )
            ).order_by(PointsTransaction.created_at.desc())

            # 执行查询
            transactions = self.session.exec(statement).all()

            return list(transactions)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取用户积分历史失败: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )
        except Exception as e:
            raise RepositoryError(
                f"获取用户积分历史时发生未知错误: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )

    def get_user_points_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取用户积分统计摘要

        Args:
            user_id: 用户ID
            days: 统计最近多少天的数据，默认30天

        Returns:
            Dict[str, Any]: 积分统计信息字典

        Raises:
            RepositoryValidationError: 参数验证失败时
            RepositoryError: 数据库操作错误时

        Example:
            >>> reward_repo = RewardRepository(session)
            >>> summary = reward_repo.get_user_points_summary("user123")
            >>> print(f"当前余额: {summary['current_balance']}")
            "当前余额: 150"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not isinstance(days, int) or days <= 0:
                raise RepositoryValidationError("天数参数必须是正整数")

            # 计算时间阈值
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 统计总收入
            earned_query = select(func.coalesce(func.sum(PointsTransaction.points_change), 0)).where(
                and_(
                    PointsTransaction.user_id == user_id,
                    PointsTransaction.transaction_type == TransactionType.EARN,
                    PointsTransaction.created_at >= threshold_date
                )
            )
            total_earned = self.session.exec(earned_query).one() or 0

            # 统计总支出
            spent_query = select(func.coalesce(func.sum(func.abs(PointsTransaction.points_change)), 0)).where(
                and_(
                    PointsTransaction.user_id == user_id,
                    PointsTransaction.transaction_type == TransactionType.SPEND,
                    PointsTransaction.created_at >= threshold_date
                )
            )
            total_spent = self.session.exec(spent_query).one() or 0

            # 获取当前余额
            current_balance = self.get_user_fragment_balance(user_id)

            # 统计交易次数
            transaction_count_query = select(func.count(PointsTransaction.id)).where(
                and_(
                    PointsTransaction.user_id == user_id,
                    PointsTransaction.created_at >= threshold_date
                )
            )
            transaction_count = self.session.exec(transaction_count_query).one() or 0

            return {
                "total_earned": int(total_earned),
                "total_spent": int(total_spent),
                "current_balance": int(current_balance),
                "net_change": int(total_earned - total_spent),
                "transaction_count": int(transaction_count),
                "average_transaction": round((total_earned + total_spent) / transaction_count, 2) if transaction_count > 0 else 0,
                "statistics_days": days
            }

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取用户积分统计失败: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )
        except Exception as e:
            raise RepositoryError(
                f"获取用户积分统计时发生未知错误: {str(e)}",
                operation="read",
                model_name="PointsTransaction"
            )


# 导出RewardRepository类
__all__ = ["RewardRepository"]