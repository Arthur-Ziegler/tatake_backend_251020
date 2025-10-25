"""
Reward领域Service层 v2.0

基于纯SQL聚合查询实现奖励系统核心功能。

核心功能：
1. 奖品目录查询：获取可用奖品列表
2. 奖品兑换：使用积分兑换奖品，创建流水记录
3. 库存管理：通过悲观锁确保库存原子性
4. 事务组管理：兑换操作的多个记录通过transaction_group关联

设计原则：
1. 纯SQL聚合：不使用缓存，保持简单实现
2. 悲观锁机制：关键操作使用SELECT FOR UPDATE
3. 流水记录：所有变动通过reward_transactions表记录
4. 事务边界：关键操作使用事务确保一致性

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from uuid import UUID, uuid4
from contextlib import contextmanager
import random

from sqlmodel import Session, select, text
from sqlalchemy.exc import SQLAlchemyError

from .models import Reward, RewardTransaction, RewardRecipe
from .exceptions import RewardNotFoundException, InsufficientPointsException
from src.config.game_config import reward_config, TransactionSource
from .repository import RewardRepository, RecipeRepository
from src.utils.uuid_helpers import ensure_str


class RewardService:
    """
    奖励系统服务层

    提供奖品兑换、库存管理和Top3抽奖功能。
    所有操作基于纯SQL聚合查询，确保数据一致性。
    """

    def __init__(self, session: Session, points_service):
        """
        初始化奖励服务

        Args:
            session (Session): 数据库会话
            points_service: PointsService实例，用于积分操作
        """
        self.session = session
        self.points_service = points_service
        self.reward_repository = RewardRepository(session)
        self.recipe_repository = RecipeRepository(session)
        self.logger = logging.getLogger(__name__)

    def get_available_rewards(self) -> List[Dict[str, Any]]:
        """
        获取可用奖品列表

        查询库存大于0的可用奖品，按类型分组。

        Returns:
            List[Dict[str, Any]]: 奖品列表
        """
        self.logger.info("Getting available rewards")

        try:
            result = self.session.execute(
                text("""
                    SELECT
                        id, name, description, category, image_url,
                        cost_type, cost_value, stock_quantity,
                        created_at, updated_at
                    FROM rewards
                    WHERE stock_quantity > 0
                    AND is_active = true
                    ORDER BY category, name
                """)
            ).fetchall()

            rewards = [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "description": row[2],
                    "category": row[3],
                    "image_url": row[4],
                    "cost_type": row[5],
                    "cost_value": row[6],
                    "stock_quantity": row[7],
                    "created_at": row[8],
                    "updated_at": row[9]
                }
                for row in result
            ]

            self.logger.info(f"Retrieved {len(rewards)} available rewards")
            return rewards

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting available rewards: {e}")
            raise

    def get_reward_catalog(self) -> Dict[str, Any]:
        """
        获取奖品目录

        返回符合RewardCatalogResponse schema格式的奖品目录。

        Returns:
            Dict[str, Any]: 奖品目录响应数据
        """
        try:
            rewards = self.get_available_rewards()

            # 转换为RewardResponse格式
            reward_responses = []
            for reward in rewards:
                reward_responses.append({
                    "id": reward["id"],
                    "name": reward["name"],
                    "icon": reward["image_url"],
                    "description": reward["description"],
                    "is_exchangeable": reward["stock_quantity"] > 0
                })

            return {
                "rewards": reward_responses,
                "total_count": len(reward_responses)
            }

        except Exception as e:
            self.logger.error(f"Error getting reward catalog: {e}")
            raise

    def redeem_reward(self, user_id: Union[str, UUID], reward_id: str) -> Dict[str, Any]:
        """
        兑换奖品

        使用悲观锁确保库存原子性：
        1. 锁定奖品记录
        2. 检查库存和用户积分
        3. 扣减库存和积分
        4. 创建兑换记录

        Args:
            user_id (str): 用户ID
            reward_id (str): 奖品ID

        Returns:
            Dict[str, Any]: 兑换结果

        Raises:
            RewardNotFoundException: 奖品不存在
            InsufficientPointsException: 积分不足
            Exception: 其他错误
        """
        user_id_str = ensure_str(user_id)
        self.logger.info(f"User {user_id_str} redeeming reward {reward_id}")

        try:
            with self.transaction_scope():
                # 1. 锁定奖品记录
                reward_result = self.session.execute(
                    text("""
                        SELECT id, name, cost_type, cost_value, stock_quantity
                        FROM rewards
                        WHERE id = :reward_id FOR UPDATE
                    """),
                    {"reward_id": reward_id}
                ).first()

                if not reward_result:
                    raise RewardNotFoundException(f"奖品不存在: {reward_id}")

                reward_id_db, name, cost_type, cost_value, stock_quantity = reward_result

                if stock_quantity <= 0:
                    raise Exception("奖品库存不足")

                # 2. 检查用户积分
                current_balance = self.points_service.calculate_balance(user_id_str)

                required_points = cost_value if cost_type == "points" else 0

                if current_balance < required_points:
                    raise InsufficientPointsException(
                        f"积分不足，当前: {current_balance}, 需要: {required_points}",
                        required_points=required_points,
                        current_points=current_balance
                    )

                # 3. 执行兑换操作
                transaction_group = str(uuid4())

                # 扣减库存
                self.session.execute(
                    text("UPDATE rewards SET stock_quantity = stock_quantity - 1 WHERE id = :reward_id"),
                    {"reward_id": reward_id}
                )

                # 扣减积分
                if required_points > 0:
                    self.points_service.add_points(
                        user_id_str, -required_points, "reward_redemption", str(reward_id)
                    )

                # 创建兑换记录
                redemption_record = RewardTransaction(
                    user_id=user_id_str,
                    reward_id=reward_id,
                    source_type="redemption",
                    source_id=reward_id,
                    quantity=1,  # 兑换获得1个奖品
                    transaction_group=transaction_group,
                    created_at=datetime.now(timezone.utc)
                )

                self.session.add(redemption_record)
                self.session.flush()

                result = {
                    "success": True,
                    "reward": {
                        "id": reward_id_db,
                        "name": name,
                        "cost_type": cost_type,
                        "cost_value": cost_value
                    },
                    "transaction_group": transaction_group,
                    "points_deducted": required_points,
                    "message": f"成功兑换奖品: {name}"
                }

                self.logger.info(f"Successfully redeemed reward {reward_id} for user {user_id_str}")
                return result

        except (RewardNotFoundException, InsufficientPointsException):
            # 业务异常，重新抛出
            self.logger.warning(f"Redemption failed for user {user_id_str}, reward {reward_id}: {e}")
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error redeeming reward {reward_id} for user {user_id_str}: {e}")
            raise Exception(f"数据库错误: {e}")

    def top3_lottery(self, user_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        Top3抽奖

        实现v3 API方案中的Top3抽奖逻辑：
        - 50%概率获得所有Top3奖品
        - 50%概率获得50积分

        Args:
            user_id (str): 用户ID

        Returns:
            Dict[str, Any]: 抽奖结果
        """
        user_id_str = ensure_str(user_id)
        self.logger.info(f"User {user_id_str} participating in Top3 lottery")

        try:
            with self.transaction_scope():
                # 获取所有可用的奖品（不限category）
                available_rewards = self.session.execute(
                    text("""
                        SELECT id, name, description, image_url
                        FROM rewards
                        WHERE stock_quantity > 0
                        AND is_active = true
                        ORDER BY name
                    """)
                ).fetchall()

                # 50%概率中奖
                is_winner = random.random() < 0.5

                if is_winner and available_rewards:
                    # 中奖且有可用奖品：随机选择一个
                    prize = random.choice(available_rewards)
                    prize_id = prize[0]

                    # 扣减库存
                    self.session.execute(
                        text("UPDATE rewards SET stock_quantity = stock_quantity - 1 WHERE id = :prize_id"),
                        {"prize_id": prize_id}
                    )

                    # 创建中奖记录
                    transaction_group = str(uuid4())
                    lottery_record = RewardTransaction(
                        user_id=user_id_str,
                        reward_id=prize_id,
                        source_type="lottery_reward",
                        source_id=user_id_str,  # 使用用户ID作为来源ID
                        quantity=1,  # 中奖获得1个奖品
                        transaction_group=transaction_group,
                        created_at=datetime.now(timezone.utc)
                    )

                    self.session.add(lottery_record)
                    self.session.flush()

                    result = {
                        "success": True,
                        "type": "reward",
                        "reward": {
                            "id": str(prize_id),
                            "name": prize[1],
                            "description": prize[2],
                            "image_url": prize[3]
                        },
                        "message": "恭喜中奖！获得奖品"
                    }

                    self.logger.info(f"User {user_id_str} won Top3 lottery, prize: {prize_id}")
                    return result

                else:
                    # 未中奖：发放配置的积分数量（默认100）
                    lottery_config = reward_config.get_top3_lottery_config()
                    consolation_points = lottery_config["points_amount"]

                    # 创建事务组ID用于关联
                    transaction_group = str(uuid4())
                    self.points_service.add_points(
                        user_id=user_id_str,
                        amount=consolation_points,
                        source_type=TransactionSource.LOTTERY_POINTS,
                        source_id=user_id_str,  # 使用用户ID作为来源ID
                        transaction_group=transaction_group
                    )

                    result = {
                        "success": True,
                        "type": "points",
                        "amount": consolation_points,
                        "message": f"未中奖，获得{consolation_points}积分安慰奖"
                    }

                    self.logger.info(f"User {user_id_str} lost Top3 lottery, got {consolation_points} points")
                    return result

        except Exception as e:
            self.logger.error(f"Error in Top3 lottery for user {user_id_str}: {e}")
            raise Exception(f"抽奖错误: {e}")

    def get_reward_transactions(self, user_id: Union[str, UUID], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户奖励流水记录

        Args:
            user_id (str): 用户ID
            limit (int): 限制数量
            offset (int): 偏移数量

        Returns:
            List[Dict[str, Any]]: 交易记录
        """
        user_id_str = ensure_str(user_id)
        self.logger.info(f"Getting reward transactions for user {user_id_str}")

        try:
            result = self.session.execute(
                text("""
                    SELECT
                        rt.id, rt.reward_id, r.name as reward_name,
                        rt.source_type, rt.source_id, rt.quantity,
                        rt.transaction_group, rt.created_at
                    FROM reward_transactions rt
                    JOIN rewards r ON rt.reward_id = r.id
                    WHERE rt.user_id = :user_id
                    ORDER BY rt.created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                {
                    "user_id": user_id_str,
                    "limit": limit,
                    "offset": offset
                }
            ).fetchall()

            transactions = [
                {
                    "id": str(row[0]),
                    "reward_id": str(row[1]) if row[1] else None,
                    "reward_name": row[2],
                    "source_type": row[3],
                    "source_id": row[4],
                    "quantity": row[5],
                    "transaction_group": row[6],
                    "created_at": row[7]
                }
                for row in result
            ]

            self.logger.info(f"Retrieved {len(transactions)} reward transactions for user {user_id_str}")
            return transactions

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting reward transactions for user {user_id_str}: {e}")
            raise

    @contextmanager
    def transaction_scope(self):
        """
        简化的事务管理器

        使用上下文管理器确保关键操作的原子性。
        """
        self.logger.debug("Starting reward transaction scope")

        try:
            with self.session.begin():
                yield self.session
                self.logger.debug("Reward transaction committed successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Reward transaction failed: {e}")
            self.session.rollback()
            raise
        finally:
            self.logger.debug("Reward transaction scope ended")

    def compose_rewards(self, user_id: Union[str, UUID], recipe_id: str) -> Dict[str, Any]:
        """
        配方合成奖品

        实现配方合成的核心逻辑：
        1. 验证配方存在性和可用性
        2. 检查用户材料是否充足
        3. 验证配方材料要求
        4. 扣除材料并发放结果奖品
        5. 记录所有流水记录（事务组关联）

        Args:
            user_id (str): 用户ID
            recipe_id (str): 配方ID

        Returns:
            Dict[str, Any]: 合成结果，包含消耗的材料和获得的奖品

        Raises:
            Exception: 配方不存在、材料不足、数据库错误等
        """
        user_id_str = ensure_str(user_id)
        self.logger.info(f"User {user_id_str} composing recipe {recipe_id}")

        try:
            with self.transaction_scope():
                # 1. 获取配方详情
                recipe_detail = self.recipe_repository.get_recipe_with_details(recipe_id)
                if not recipe_detail:
                    raise Exception(f"配方不存在或已禁用: {recipe_id}")

                recipe = recipe_detail["recipe"]
                result_reward = recipe_detail["result_reward"]
                materials_required = recipe["materials"]

                if not materials_required:
                    raise Exception(f"配方材料配置为空: {recipe_id}")

                # 2. 获取用户当前材料
                user_materials = self.reward_repository.get_user_materials(user_id_str)
                user_materials_dict = {
                    material["reward_id"]: material["quantity"]
                    for material in user_materials
                }

                # 3. 验证材料是否充足
                insufficient_materials = []
                for material in materials_required:
                    required_id = material["reward_id"]
                    required_quantity = material["quantity"]

                    current_quantity = user_materials_dict.get(required_id, 0)
                    if current_quantity < required_quantity:
                        # 获取材料名称用于错误信息
                        material_name = "未知材料"
                        for material_info in user_materials:
                            if material_info["reward_id"] == required_id:
                                material_name = material_info["reward_name"]
                                break

                        insufficient_materials.append({
                            "reward_id": required_id,
                            "reward_name": material_name,
                            "required": required_quantity,
                            "current": current_quantity
                        })

                if insufficient_materials:
                    raise Exception(
                        f"材料不足，无法合成。缺少材料: {insufficient_materials}"
                    )

                # 4. 生成事务组ID
                transaction_group = str(uuid4())

                # 5. 扣除材料
                for material in materials_required:
                    material_id = material["reward_id"]
                    material_quantity = material["quantity"]

                    # 创建材料消耗记录
                    consume_record = RewardTransaction(
                        user_id=user_id,
                        reward_id=material_id,
                        source_type="recipe_consume",
                        source_id=recipe_id,
                        quantity=-material_quantity,  # 负数表示消耗
                        transaction_group=transaction_group,
                        created_at=datetime.now(timezone.utc)
                    )
                    self.session.add(consume_record)

                # 6. 发放结果奖品
                result_record = RewardTransaction(
                    user_id=user_id,
                    reward_id=result_reward["id"],
                    source_type="recipe_produce",
                    source_id=recipe_id,
                    quantity=1,  # 配方合成通常只产出1个
                    transaction_group=transaction_group,
                    created_at=datetime.now(timezone.utc)
                )
                self.session.add(result_record)

                # 立即刷新到数据库
                self.session.flush()

                # 7. 构建返回结果
                result = {
                    "success": True,
                    "recipe_id": recipe_id,
                    "recipe_name": recipe["name"],
                    "result_reward": {
                        "id": result_reward["id"],
                        "name": result_reward["name"],
                        "description": result_reward["description"],
                        "image_url": result_reward["image_url"],
                        "category": result_reward["category"]
                    },
                    "materials_consumed": [
                        {
                            "reward_id": material["reward_id"],
                            "quantity": material["quantity"]
                        }
                        for material in materials_required
                    ],
                    "transaction_group": transaction_group,
                    "message": f"成功合成奖品: {result_reward['name']}"
                }

                self.logger.info(
                    f"Successfully composed recipe {recipe_id} for user {user_id}, "
                    f"result: {result_reward['id']}, transaction_group: {transaction_group}"
                )

                return result

        except Exception as e:
            self.logger.error(f"Error composing recipe {recipe_id} for user {user_id_str}: {e}")
            raise

    def get_user_materials(self, user_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """
        获取用户材料列表（用于前端展示）

        Args:
            user_id (str): 用户ID

        Returns:
            List[Dict[str, Any]]: 用户材料列表
        """
        try:
            user_id_str = ensure_str(user_id)
            return self.reward_repository.get_user_materials(user_id_str)
        except Exception as e:
            self.logger.error(f"Error getting user materials for {user_id_str}: {e}")
            raise

    def get_available_recipes(self) -> List[Dict[str, Any]]:
        """
        获取可用配方列表

        Returns:
            List[Dict[str, Any]]: 可用配方列表
        """
        try:
            return self.recipe_repository.get_available_recipes()
        except Exception as e:
            self.logger.error(f"Error getting available recipes: {e}")
            raise

    def get_my_rewards(self, user_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        获取用户拥有的所有奖品

        Args:
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 包含用户奖品列表的字典

        Raises:
            Exception: 查询失败时抛出异常
        """
        try:
            # 获取用户的所有奖励交易记录
            reward_transactions = self.get_reward_transactions(user_id)

            # 按奖励ID分组并计算数量
            reward_counts = {}
            for transaction in reward_transactions:
                reward_id = transaction.get("reward_id")
                if reward_id and reward_id != "points":
                    reward_counts[reward_id] = reward_counts.get(reward_id, 0) + 1

            # 获取奖品详细信息
            rewards = []
            for reward_id, quantity in reward_counts.items():
                try:
                    reward_detail = self.reward_repository.get_reward_by_id(reward_id)
                    if reward_detail:
                        rewards.append({
                            "id": reward_detail["id"],
                            "name": reward_detail["name"],
                            "icon": reward_detail.get("image_url"),
                            "description": reward_detail.get("description"),
                            "is_exchangeable": reward_detail.get("stock_quantity", 0) > 0
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to get reward detail for {reward_id}: {e}")
                    continue

            return {
                "rewards": rewards,
                "total_types": len(rewards)
            }
        except Exception as e:
            user_id_str = ensure_str(user_id)
            self.logger.error(f"Error getting my rewards for user {user_id_str}: {e}")
            raise