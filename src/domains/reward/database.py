"""
奖励系统数据库初始化模块

实现从.env配置初始化奖品和配方数据的功能：
1. 从game_config读取默认奖品和配方配置
2. 按name检查奖品是否存在，不存在则创建（自动生成UUID）
3. 配方的result_reward_id通过name查询转换为UUID
4. materials保持字符串ID格式（name），运行时查询转换
5. 支持重复初始化（幂等性）

设计原则：
1. 幂等性：重复初始化不会创建重复数据
2. 字符串ID即名称：.env中配置的字符串ID就是奖品名称
3. 自动UUID：数据库主键使用自动生成的UUID
4. 事务安全：初始化过程使用事务保护

作者：TaTakeKe团队
版本：v1.0（Day4实施）
"""

import logging
from typing import Dict, Any, List
from uuid import uuid4

from sqlmodel import Session, select

from .models import Reward, RewardRecipe
from src.config.game_config import RewardConfig
from src.database import get_db_session

logger = logging.getLogger(__name__)


def initialize_reward_database(session: Session) -> None:
    """
    从.env配置初始化奖品和配方数据

    策略：
    1. .env中字符串ID就是奖品名称（如"gold_coin" -> "小金币"）
    2. 自动生成UUID作为主键
    3. 按name检查是否已存在，不存在则创建
    4. 配方的result_reward_id通过name查询转换为UUID
    5. materials保持字符串ID格式（name）

    Args:
        session (Session): 数据库会话
    """
    try:
        logger.info("开始初始化奖励系统数据库")

        config = RewardConfig()

        # 1. 初始化奖品
        _initialize_rewards(session, config)

        # 2. 初始化配方
        _initialize_recipes(session, config)

        # 提交事务
        session.commit()
        logger.info("奖励系统数据库初始化完成")

    except Exception as e:
        session.rollback()
        logger.error(f"奖励系统数据库初始化失败: {e}")
        raise


def _initialize_rewards(session: Session, config: RewardConfig) -> None:
    """初始化奖品数据"""
    logger.info("开始初始化奖品数据")

    rewards_data = config.get_default_rewards()
    created_count = 0

    for reward_data in rewards_data:
        # 检查奖品是否已存在（按name查找）
        existing = session.execute(
            select(Reward).where(Reward.name == reward_data["name"])
        ).scalar_one_or_none()

        if existing:
            logger.debug(f"奖品已存在，跳过: {reward_data['name']}")
            continue

        # 创建新奖品
        reward = Reward(
            id=str(uuid4()),  # 自动生成UUID并转换为字符串
            name=reward_data["name"],
            description=reward_data["description"],
            points_value=reward_data["points_value"],
            category=reward_data["category"],
            is_active=reward_data["is_active"],
            cost_type="points",  # 默认使用积分成本类型
            cost_value=reward_data["points_value"],  # 成本价值等于积分价值
            image_url=None,  # 默认无图片
            stock_quantity=0  # 默认无库存限制
        )

        session.add(reward)
        created_count += 1
        logger.info(f"创建奖品: {reward.name} (UUID: {reward.id})")

    logger.info(f"奖品初始化完成，新创建 {created_count} 个奖品")


def _initialize_recipes(session: Session, config: RewardConfig) -> None:
    """初始化配方数据"""
    logger.info("开始初始化配方数据")

    recipes_data = config.get_default_recipes()
    created_count = 0

    for recipe_data in recipes_data:
        # 检查配方是否已存在（按name查找）
        existing = session.execute(
            select(RewardRecipe).where(RewardRecipe.name == recipe_data["name"])
        ).scalar_one_or_none()

        if existing:
            logger.debug(f"配方已存在，跳过: {recipe_data['name']}")
            continue

        # 查询result_reward的UUID（通过name查找）
        result_reward = session.execute(
            select(Reward).where(Reward.name == recipe_data["result_reward_id"])
        ).scalar_one_or_none()

        if not result_reward:
            logger.error(f"配方目标奖品不存在: {recipe_data['result_reward_id']}")
            continue

        # 创建新配方
        recipe = RewardRecipe(
            id=str(uuid4()),
            name=recipe_data["name"],
            result_reward_id=result_reward.id,  # UUID字符串
            materials=recipe_data["materials"],  # 保持字符串ID格式
            is_active=recipe_data["is_active"]
        )

        session.add(recipe)
        created_count += 1
        logger.info(f"创建配方: {recipe.name} -> {result_reward.name}")

    logger.info(f"配方初始化完成，新创建 {created_count} 个配方")


def verify_initialization(session: Session) -> Dict[str, int]:
    """
    验证初始化结果

    Args:
        session (Session): 数据库会话

    Returns:
        Dict[str, int]: 奖品和配方数量统计
    """
    reward_count = session.execute(select(Reward)).count()
    recipe_count = session.execute(select(RewardRecipe)).count()

    return {
        "rewards": reward_count,
        "recipes": recipe_count
    }


def get_reward_by_name(session: Session, name: str) -> Reward:
    """
    根据名称查询奖品（运行时转换字符串ID到UUID）

    Args:
        session (Session): 数据库会话
        name (str): 奖品名称

    Returns:
        Reward: 奖品对象

    Raises:
        ValueError: 奖品不存在
    """
    reward = session.execute(
        select(Reward).where(Reward.name == name)
    ).scalar_one_or_none()

    if not reward:
        raise ValueError(f"奖品不存在: {name}")

    return reward


# 向后兼容的函数
def get_reward_session():
    """获取奖励领域数据库会话（向后兼容）"""
    from src.database import get_db_session
    return get_db_session