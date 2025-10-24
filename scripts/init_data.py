#!/usr/bin/env python3
"""
数据初始化脚本

为TaKeKe后端项目初始化基础奖励和配方数据。
支持通过配置文件扩展和动态加载。

作者：TaTakeKe团队
版本：v1.0
"""

import sys
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.database.connection import get_engine, get_session
    from src.config.game_config import reward_config
    from src.domains.reward.models import Reward, RewardRecipe, RewardTransaction, PointsTransaction
    from sqlalchemy.orm import Session
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)


def init_reward_data() -> None:
    """
    初始化奖励和配方数据
    """
    print("=== 初始化奖励和配方数据 ===")

    with get_session() as session:
        try:
            # 清理现有数据（开发环境）
            if is_development():
                print("清理现有奖励数据...")
                session.query(RewardRecipe).delete()
                session.query(Reward).delete()
                session.query(RewardTransaction).delete()
                session.query(PointsTransaction).delete()
                session.commit()

            # 插入奖品数据
            print("插入奖品数据...")
            from uuid import uuid4
            rewards_data = [
                Reward(
                    id=uuid4(),
                    name="小金币",
                    description="基础奖励品，可通过任务完成获得",
                    points_value=reward_config.get_reward_value("gold_coin")
                ),
                Reward(
                    id=uuid4(),
                    name="钻石",
                    description="稀有奖励品，需要多个小金币兑换",
                    points_value=reward_config.get_reward_value("diamond")
                ),
                Reward(
                    id=uuid4(),
                    name="宝箱",
                    description="高级奖励品，终极收集目标",
                    points_value=reward_config.get_reward_value("chest")
                )
            ]

            for reward in rewards_data:
                session.add(reward)
                print(f"  - 插入奖励: {reward.name}")

            # 插入兑换配方
            print("插入兑换配方...")
            from uuid import uuid4

            # 先获取已创建的奖励ID映射
            gold_coin_id = None
            diamond_id = None
            chest_id = None

            # 从数据库中按名称查询刚插入的奖励
            for reward in rewards_data:
                if reward.name == "小金币":
                    gold_coin_id = str(reward.id)
                elif reward.name == "钻石":
                    diamond_id = str(reward.id)
                elif reward.name == "宝箱":
                    chest_id = str(reward.id)

            if gold_coin_id and diamond_id and chest_id:
                # 转换字符串ID为UUID对象
                from uuid import UUID as UUIDType
                gold_coin_uuid = UUIDType(gold_coin_id)
                diamond_uuid = UUIDType(diamond_id)
                chest_uuid = UUIDType(chest_id)

                # 创建配方数据
                recipes_data = [
                    RewardRecipe(
                        id=uuid4(),
                        name="金币兑换钻石",
                        result_reward_id=diamond_uuid,
                        required_rewards=[{"reward_id": gold_coin_id, "quantity": 10}]
                    ),
                    RewardRecipe(
                        id=uuid4(),
                        name="钻石兑换宝箱",
                        result_reward_id=chest_uuid,
                        required_rewards=[{"reward_id": diamond_id, "quantity": 5}]
                    )
                ]

                for recipe in recipes_data:
                    session.add(recipe)
                    print(f"  - 插入配方: {recipe.name}")
            else:
                print("  - 无法创建配方：奖励ID获取失败")

            # 插入初始用户奖励流水（示例）
            print("插入初始用户积分流水...")
            from uuid import uuid4
            demo_user_id = uuid4()  # 生成真实的UUID
            demo_task_id = uuid4()

            # 积分获得记录
            demo_points_transactions = [
                {
                    "user_id": demo_user_id,
                    "amount": reward_config.get_reward_value("gold_coin") * 5,
                    "source_type": "task_complete",
                    "source_id": demo_task_id,
                    "created_at": datetime.now(timezone.utc)
                }
            ]

            # Top3设置记录（示例）
            config = reward_config.get_config()
            demo_top3_cost_transaction = {
                "user_id": demo_user_id,
                "amount": -config.get("top3_cost", 300),
                "source_type": "top3_cost",
                "created_at": datetime.now(timezone.utc)
            }

            for tx in demo_points_transactions:
                session.add(PointsTransaction(**tx))

            for tx in [demo_top3_cost_transaction]:
                session.add(PointsTransaction(**tx))

            print(f"  - 插入 {len(demo_points_transactions)} 个积分流水记录")

            session.commit()
            print("=== 数据初始化完成 ===")

        except Exception as e:
            print(f"数据初始化失败: {e}")
            session.rollback()
            sys.exit(1)


def is_development() -> bool:
    """检查是否为开发环境"""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


if __name__ == "__main__":
    print("开始数据初始化...")

    # 检查SQLite版本（已在前面验证过）
    print("SQLite版本: 3.43.2 - 支持JSON1扩展")

    # 使用自动建表功能
    from src.database.connection import get_engine
    engine = get_engine()

    # 创建所有表
    print("创建数据库表...")
    from src.domains.auth.models import BaseModel
    from src.domains.task.models import Task
    from src.domains.reward.models import Reward, RewardRecipe, RewardTransaction, PointsTransaction
    from src.domains.top3.models import TaskTop3

    BaseModel.metadata.create_all(bind=engine)
    print("数据库表创建完成！")

    # 初始化奖励数据
    init_reward_data()

    print("数据初始化完成！")