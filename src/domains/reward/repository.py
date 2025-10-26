"""Reward领域Repository层"""

import random
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlmodel import Session, select, func
from src.core.uuid_converter import UUIDConverter

from .models import Reward, RewardRecipe, RewardTransaction, PointsTransaction
from .exceptions import (
    RewardNotFoundException,
    RecipeNotFoundException,
    InsufficientRewardsException
)


class RewardRepository:
    """奖品仓储"""

    def __init__(self, session: Session):
        self.session = session

    def get_all_rewards(self) -> List[Reward]:
        """获取所有奖品"""
        statement = select(Reward)
        return list(self.session.execute(statement).scalars().all())

    def get_reward_by_id(self, reward_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取奖品（返回字典格式）"""
        from sqlalchemy import text

        try:
            result = self.session.execute(
                text("""
                    SELECT id, name, description, image_url, category, points_value, is_active
                    FROM rewards
                    WHERE id = :reward_id
                """),
                {"reward_id": reward_id}
            ).first()

            if not result:
                return None

            return {
                "id": str(result[0]),
                "name": result[1],
                "description": result[2],
                "image_url": result[3],
                "category": result[4],
                "points_value": result[5],
                "is_active": bool(result[6])
            }

        except Exception as e:
            raise Exception(f"获取奖品详情失败: {e}")

    def get_random_reward(self) -> Optional[Reward]:
        """随机获取一个可兑换的奖品（v4：所有奖品都可兑换）"""
        statement = select(Reward).where(Reward.is_active == True)
        rewards = list(self.session.execute(statement).scalars().all())
        return random.choice(rewards) if rewards else None

    def get_user_rewards(self, user_id: UUID) -> List[RewardTransaction]:
        """获取用户所有奖励流水记录"""
        statement = select(RewardTransaction).where(
            RewardTransaction.user_id == UUIDConverter.to_string(user_id),
            RewardTransaction.quantity > 0  # 只获取获得的奖励
        ).order_by(RewardTransaction.created_at.desc())
        return list(self.session.execute(statement).scalars().all())

    def get_user_reward_balance(self, user_id: UUID, reward_id: str) -> int:
        """获取用户指定奖励的余额"""
        from sqlalchemy import text

        result = self.session.execute(
            text("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM reward_transactions
                WHERE user_id = :user_id AND reward_id = :reward_id
            """),
            {"user_id": UUIDConverter.to_string(user_id), "reward_id": reward_id}
        ).scalar()

        return result or 0

    


class RecipeRepository:
    """兑换配方仓储"""

    def __init__(self, session: Session):
        self.session = session

    def get_recipe_by_id(self, recipe_id: UUID) -> Optional[RewardRecipe]:
        """根据ID获取配方"""
        return self.session.get(RewardRecipe, recipe_id)

    def get_all_recipes(self) -> List[RewardRecipe]:
        """获取所有配方"""
        statement = select(RewardRecipe)
        return list(self.session.execute(statement).scalars().all())

    def get_recipe_with_details(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        获取配方详情，包括结果奖品和材料信息

        Args:
            recipe_id (str): 配方ID

        Returns:
            Optional[Dict[str, Any]]: 配方详情，包含recipe、result_reward和materials
        """
        from sqlalchemy import text

        try:
            # 获取配方基本信息
            recipe_result = self.session.execute(
                text("""
                    SELECT id, name, result_reward_id, materials, is_active
                    FROM reward_recipes
                    WHERE id = :recipe_id AND is_active = true
                """),
                {"recipe_id": recipe_id}
            ).first()

            if not recipe_result:
                return None

            recipe_id_db, name, result_reward_id, materials, is_active = recipe_result

            # 获取结果奖品信息
            reward_result = self.session.execute(
                text("""
                    SELECT id, name, description, image_url, category
                    FROM rewards
                    WHERE id = :reward_id
                """),
                {"reward_id": result_reward_id}
            ).first()

            if not reward_result:
                raise Exception(f"配方结果奖品不存在: {result_reward_id}")

            reward_id, reward_name, reward_desc, image_url, category = reward_result

            # 构建配方详情
            recipe_detail = {
                "recipe": {
                    "id": str(recipe_id_db),
                    "name": name,
                    "result_reward_id": str(result_reward_id),
                    "materials": materials or [],
                    "is_active": bool(is_active)
                },
                "result_reward": {
                    "id": str(reward_id),
                    "name": reward_name,
                    "description": reward_desc,
                    "image_url": image_url,
                    "category": category
                }
            }

            return recipe_detail

        except Exception as e:
            raise Exception(f"获取配方详情失败: {e}")

    def get_available_recipes(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的配方列表

        Returns:
            List[Dict[str, Any]]: 可用配方列表
        """
        from sqlalchemy import text

        try:
            result = self.session.execute(
                text("""
                    SELECT
                        rr.id, rr.name, rr.result_reward_id,
                        r.name as result_reward_name, r.image_url as result_image_url,
                        rr.materials, rr.created_at
                    FROM reward_recipes rr
                    JOIN rewards r ON rr.result_reward_id = r.id
                    WHERE rr.is_active = true
                    ORDER BY rr.created_at DESC
                """)
            ).fetchall()

            recipes = []
            for row in result:
                # 使用字典式访问，避免索引问题
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else {
                    'id': row[0], 'name': row[1], 'result_reward_id': row[2],
                    'result_reward_name': row[3], 'result_image_url': row[4],
                    'materials': row[5], 'created_at': row[6]
                }

                recipes.append({
                    "id": str(row_dict.get('id')),
                    "name": row_dict.get('name') or "未命名配方",
                    "result_reward_id": str(row_dict.get('result_reward_id')),
                    "result_reward_name": row_dict.get('result_reward_name'),
                    "result_image_url": row_dict.get('result_image_url'),
                    "materials": row_dict.get('materials') or [],
                    "created_at": row_dict.get('created_at')
                })

            return recipes

        except Exception as e:
            raise Exception(f"获取可用配方列表失败: {e}")


class PointsRepository:
    """积分仓储"""

    def __init__(self, session: Session):
        self.session = session

    def get_balance(self, user_id: UUID) -> int:
        """获取用户积分余额"""
        statement = select(func.sum(PointsTransaction.amount)).where(
            PointsTransaction.user_id == UUIDConverter.to_string(user_id)
        )
        result = self.session.execute(statement).scalar()
        return result or 0

    def get_total_earned(self, user_id: UUID) -> int:
        """获取用户总收入积分"""
        statement = select(func.sum(PointsTransaction.amount)).where(
            PointsTransaction.user_id == UUIDConverter.to_string(user_id),
            PointsTransaction.amount > 0
        )
        result = self.session.execute(statement).scalar()
        return result or 0

    def get_total_spent(self, user_id: UUID) -> int:
        """获取用户总支出积分（绝对值）"""
        statement = select(func.sum(PointsTransaction.amount)).where(
            PointsTransaction.user_id == UUIDConverter.to_string(user_id),
            PointsTransaction.amount < 0
        )
        result = self.session.execute(statement).scalar()
        return abs(result) if result else 0

    def add_transaction(
        self,
        user_id: UUID,
        amount: int,
        source: str,
        related_task_id: Optional[UUID] = None
    ) -> PointsTransaction:
        """添加积分流水"""
        transaction = PointsTransaction(
            user_id=user_id,
            amount=amount,
            source=source,
            related_task_id=related_task_id
        )
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def get_transactions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[PointsTransaction]:
        """获取用户积分流水"""
        statement = (
            select(PointsTransaction)
            .where(PointsTransaction.user_id == str(user_id))
            .order_by(PointsTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.execute(statement).all())

    def count_transactions(self, user_id: UUID) -> int:
        """统计用户积分流水数量"""
        statement = select(func.count(PointsTransaction.id)).where(
            PointsTransaction.user_id == UUIDConverter.to_string(user_id)
        )
        return self.session.execute(statement).scalar() or 0

    def add_user_reward(self, user_id: UUID, reward_id: UUID, quantity: int) -> None:
        """添加用户奖励流水记录（用于抽奖）"""
        transaction = RewardTransaction(
            user_id=UUIDConverter.to_string(user_id),
            reward_id=str(reward_id),
            source_type="lottery",
            quantity=quantity,
            transaction_group=None,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(transaction)
