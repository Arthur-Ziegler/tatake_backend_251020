"""
欢迎礼包服务

实现用户欢迎礼包的发放功能，包括：
1. 1000积分发放
2. 固定礼物组合发放（积分加成卡x3、专注道具x10、时间管理券x5）
3. 可重复领取
4. 完整的流水记录

设计原则：
1. 简单可靠：直接调用PointsService和RewardService
2. 事务安全：确保积分和奖励发放的原子性
3. 可重复：无防刷限制，支持重复领取
4. 详细记录：完整的流水记录追踪

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from uuid import UUID, uuid4

from sqlmodel import Session, select, func
from sqlalchemy.exc import SQLAlchemyError

from .models import RewardTransaction
from .repository import RewardRepository
from src.domains.points.models import PointsTransaction
from src.domains.points.service import PointsService
from src.utils.uuid_helpers import ensure_str

# 配置日志
logger = logging.getLogger(__name__)


class WelcomeGiftService:
    """
    欢迎礼包服务

    负责处理用户欢迎礼包的发放，包括积分和奖励物品。
    支持可重复领取，每次都发放固定的礼包内容。
    """

    # 定义固定礼包内容
    GIFT_POINTS = 1000  # 1000积分
    GIFT_REWARDS = [
        {"name": "积分加成卡", "quantity": 3, "description": "+50%积分，有效期1小时"},
        {"name": "专注道具", "quantity": 10, "description": "立即完成专注会话"},
        {"name": "时间管理券", "quantity": 5, "description": "延长任务截止时间1天"}
    ]

    def __init__(self, session: Session, points_service: PointsService):
        """
        初始化欢迎礼包服务

        Args:
            session: 数据库会话
            points_service: 积分服务实例
        """
        self.session = session
        self.points_service = points_service
        self.reward_repository = RewardRepository(session)

    def claim_welcome_gift(self, user_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        领取欢迎礼包

        发放1000积分和固定奖励组合，支持重复领取。

        Args:
            user_id: 用户ID，支持字符串和UUID对象

        Returns:
            包含发放结果的字典
            {
                "points_granted": 1000,
                "rewards_granted": [
                    {"name": "积分加成卡", "quantity": 3, "description": "..."},
                    {"name": "专注道具", "quantity": 10, "description": "..."},
                    {"name": "时间管理券", "quantity": 5, "description": "..."}
                ],
                "transaction_group": "unique_group_id",
                "granted_at": "2025-10-25T07:06:06.167332+00:00"
            }

        Raises:
            SQLAlchemyError: 数据库操作失败
        """
        # 使用UUID工具确保类型安全
        user_id_str = ensure_str(user_id)

        try:
            # 生成事务组ID，用于关联本次礼包发放的所有操作
            transaction_group = f"welcome_gift_{user_id_str}_{uuid4().hex[:8]}"

            logger.info(f"开始为用户 {user_id_str} 发放欢迎礼包，事务组: {transaction_group}")

            # 1. 发放1000积分
            self._grant_points(user_id_str, transaction_group)

            # 2. 发放固定奖励
            rewards_granted = self._grant_rewards(user_id_str, transaction_group)

            # 3. 立即flush，写入数据库但不提交
            self.session.flush()

            # 4. 验证数据写入
            verify_count = self.session.execute(
                select(func.count()).select_from(RewardTransaction)
                .where(RewardTransaction.user_id == user_id_str)
                .where(RewardTransaction.source_type == "welcome_gift")
            ).scalar()

            if verify_count == 0:
                self.session.rollback()
                raise Exception(f"奖励数据写入验证失败，应写入{len(self.GIFT_REWARDS)}条，实际0条")

            logger.info(f"奖励数据写入验证成功：{verify_count}条记录")

            # 5. 提交事务
            self.session.commit()
            logger.info(f"欢迎礼包发放成功，用户: {user_id_str}, 积分: {self.GIFT_POINTS}, 奖励: {len(rewards_granted)}种")

            result = {
                "points_granted": self.GIFT_POINTS,
                "rewards_granted": rewards_granted,
                "transaction_group": transaction_group,
                "granted_at": datetime.now(timezone.utc).isoformat()
            }

            return result

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"欢迎礼包发放失败，用户: {user_id_str}, 错误: {str(e)}")
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"欢迎礼包发放出现意外错误，用户: {user_id_str}, 错误: {str(e)}")
            raise

    def _grant_points(self, user_id: str, transaction_group: str) -> None:
        """
        发放积分

        Args:
            user_id: 用户ID
            transaction_group: 事务组ID
        """
        points_transaction = PointsTransaction(
            user_id=user_id,
            amount=self.GIFT_POINTS,
            source_type="welcome_gift",
            source_id=transaction_group,
            created_at=datetime.now(timezone.utc)
        )

        self.session.add(points_transaction)
        # 不需要立即提交，让外层事务管理

    def _grant_rewards(self, user_id: str, transaction_group: str) -> List[Dict[str, Any]]:
        """
        发放奖励物品

        Args:
            user_id: 用户ID
            transaction_group: 事务组ID

        Returns:
            发放的奖励列表
        """
        rewards_granted = []

        for reward_item in self.GIFT_REWARDS:
            # 创建奖励流水记录
            reward_transaction = RewardTransaction(
                user_id=user_id,
                reward_id=self._get_reward_id_by_name(reward_item["name"]),
                source_type="welcome_gift",
                source_id=transaction_group,
                quantity=reward_item["quantity"],
                transaction_group=transaction_group,
                created_at=datetime.now(timezone.utc)
            )

            self.session.add(reward_transaction)

            # 添加到返回列表
            rewards_granted.append({
                "name": reward_item["name"],
                "quantity": reward_item["quantity"],
                "description": reward_item["description"]
            })

        return rewards_granted

    def _get_reward_id_by_name(self, reward_name: str) -> str:
        """
        根据奖励名称获取奖励ID

        这里使用固定ID映射，确保测试和实际运行的一致性。
        在实际部署时，这些ID应该通过数据库查询或配置文件获取。

        Args:
            reward_name: 奖励名称

        Returns:
            奖励ID
        """
        # 固定的奖励ID映射表
        reward_id_mapping = {
            "积分加成卡": "points_bonus_card",
            "专注道具": "focus_item",
            "时间管理券": "time_management_coupon"
        }

        reward_id = reward_id_mapping.get(reward_name)
        if not reward_id:
            # 如果映射表中没有，生成一个基于名称的ID
            reward_id = f"reward_{reward_name.lower().replace(' ', '_')}"

        return reward_id

    def get_user_gift_history(self, user_id: Union[str, UUID], limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用户礼包领取历史

        Args:
            user_id: 用户ID
            limit: 返回记录数量限制

        Returns:
            礼包领取历史列表
        """
        user_id_str = ensure_str(user_id)
        try:
            # 查询积分流水记录
            points_query = select(PointsTransaction).where(
                PointsTransaction.user_id == user_id_str,
                PointsTransaction.source_type == "welcome_gift"
            ).order_by(PointsTransaction.created_at.desc()).limit(limit)

            points_transactions = self.session.exec(points_query).all()

            # 构建历史记录
            history = []
            for points_tx in points_transactions:
                # 获取同事务组的奖励记录
                rewards_query = select(RewardTransaction).where(
                    RewardTransaction.user_id == user_id_str,
                    RewardTransaction.transaction_group == points_tx.source_id
                )
                reward_transactions = self.session.exec(rewards_query).all()

                # 计算奖励总数
                total_rewards = sum(tx.quantity for tx in reward_transactions)

                history.append({
                    "transaction_group": points_tx.source_id,
                    "granted_at": points_tx.created_at.isoformat(),
                    "points_granted": points_tx.amount,
                    "rewards_count": total_rewards,
                    "reward_items": [
                        {
                            "reward_id": tx.reward_id,
                            "quantity": tx.quantity
                        }
                        for tx in reward_transactions
                    ]
                })

            return history

        except SQLAlchemyError as e:
            logger.error(f"获取礼包历史失败，用户: {user_id_str}, 错误: {str(e)}")
            return []

    def get_gift_statistics(self) -> Dict[str, Any]:
        """
        获取欢迎礼包统计信息

        Returns:
            统计信息字典
        """
        try:
            # 统计总发放次数
            points_count_query = select(PointsTransaction).where(
                PointsTransaction.source_type == "welcome_gift"
            )
            points_transactions = self.session.exec(points_count_query).all()

            # 统计总积分发放量
            total_points_granted = sum(tx.amount for tx in points_transactions)

            # 统计总奖励发放量
            rewards_count_query = select(RewardTransaction).where(
                RewardTransaction.source_type == "welcome_gift"
            )
            reward_transactions = self.session.exec(rewards_count_query).all()

            total_rewards_granted = sum(tx.quantity for tx in reward_transactions)

            # 统计领取用户数（去重）
            unique_users = set(tx.user_id for tx in points_transactions)

            return {
                "total_claims": len(points_transactions),
                "unique_users": len(unique_users),
                "total_points_granted": total_points_granted,
                "total_rewards_granted": total_rewards_granted,
                "average_points_per_user": total_points_granted / len(unique_users) if unique_users else 0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

        except SQLAlchemyError as e:
            logger.error(f"获取礼包统计失败，错误: {str(e)}")
            return {
                "total_claims": 0,
                "unique_users": 0,
                "total_points_granted": 0,
                "total_rewards_granted": 0,
                "average_points_per_user": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }