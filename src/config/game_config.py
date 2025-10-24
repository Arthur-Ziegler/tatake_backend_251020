"""
游戏化系统配置管理模块

基于v3 API方案的游戏化配置管理，支持：
- 奖品配置加载
- 兑换配方管理
- 奖励参数配置
- 抽奖奖品池配置

设计原则：
1. 类型安全：使用Pydantic确保配置类型正确
2. 默认值：提供合理的默认配置
3. 环境变量：支持通过.env文件覆盖配置
4. 错误处理：详细的配置验证和错误提示

作者：TaTakeKe团队
版本：v2.0（Day3实施升级）
"""

import json
import os
from typing import Dict, Any, List, Optional
from enum import Enum
from uuid import UUID


class TransactionSource(str, Enum):
    """积分/奖励事务类型枚举（基于v3文档）"""
    TASK_COMPLETE = "task_complete"
    TASK_COMPLETE_TOP3 = "task_complete_top3"
    TOP3_COST = "top3_cost"
    LOTTERY_POINTS = "lottery_points"
    LOTTERY_REWARD = "lottery_reward"
    RECHARGE = "recharge"
    REDEMPTION = "redemption"
    MANUAL = "manual"


class RewardConfig:
    """游戏化系统配置管理类（基于v3 API方案）"""

    def __init__(self):
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从环境变量和默认值加载配置"""
        default_config = self._get_default_config()

        # 环境变量覆盖
        if os.getenv("NORMAL_TASK_POINTS"):
            default_config["normal_task_points"] = int(os.getenv("NORMAL_TASK_POINTS"))

        if os.getenv("TOP3_COST_POINTS"):
            default_config["top3_cost_points"] = int(os.getenv("TOP3_COST_POINTS"))

        if os.getenv("TOP3_LOTTERY_POINTS_PROBABILITY"):
            default_config["top3_lottery_points_probability"] = float(os.getenv("TOP3_LOTTERY_POINTS_PROBABILITY"))

        if os.getenv("TOP3_LOTTERY_POINTS_AMOUNT"):
            default_config["top3_lottery_points_amount"] = int(os.getenv("TOP3_LOTTERY_POINTS_AMOUNT"))

        if os.getenv("TOP3_LOTTERY_REWARD_PROBABILITY"):
            default_config["top3_lottery_reward_probability"] = float(os.getenv("TOP3_LOTTERY_REWARD_PROBABILITY"))

        if os.getenv("LOTTERY_REWARD_POOL"):
            try:
                default_config["lottery_reward_pool"] = json.loads(os.getenv("LOTTERY_REWARD_POOL"))
            except json.JSONDecodeError:
                print("无效的抽奖奖品池配置JSON，使用默认值")

        return default_config

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（基于v3文档）"""
        return {
            # 基础奖励配置
            "normal_task_points": 2,
            "top3_cost_points": 300,

            # Top3抽奖配置
            "top3_lottery_points_probability": 0.5,
            "top3_lottery_reward_probability": 0.5,
            "top3_lottery_points_amount": 100,

            # 抽奖奖品池配置
            "lottery_reward_pool": ["gold_coin", "diamond"],

            # 基础奖品配置
            "default_rewards": [
                {
                    "id": "gold_coin",
                    "name": "小金币",
                    "description": "基础奖品，可通过完成任务获得",
                    "points_value": 10,
                    "category": "basic",
                    "is_active": True
                },
                {
                    "id": "diamond",
                    "name": "钻石",
                    "description": "珍贵奖品，可通过小金币合成",
                    "points_value": 100,
                    "category": "premium",
                    "is_active": True
                }
            ],

            # 兑换配方配置
            "default_recipes": [
                {
                    "id": "gold_to_diamond",
                    "name": "小金币合成钻石",
                    "result_reward_id": "钻石",
                    "materials": [
                        {"reward_id": "小金币", "quantity": 10}
                    ],
                    "is_active": True
                }
            ]
        }

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config

    def get_normal_task_points(self) -> int:
        """获取普通任务积分"""
        return self._config.get("normal_task_points", 2)

    def get_top3_cost_points(self) -> int:
        """获取Top3设置成本积分"""
        return self._config.get("top3_cost_points", 300)

    def get_top3_lottery_config(self) -> Dict[str, Any]:
        """获取Top3抽奖配置"""
        return {
            "points_probability": self._config.get("top3_lottery_points_probability", 0.5),
            "reward_probability": self._config.get("top3_lottery_reward_probability", 0.5),
            "points_amount": self._config.get("top3_lottery_points_amount", 100)
        }

    def get_lottery_reward_pool(self) -> List[str]:
        """获取抽奖奖品池"""
        return self._config.get("lottery_reward_pool", ["gold_coin", "diamond"])

    def get_default_rewards(self) -> List[Dict[str, Any]]:
        """获取默认奖品列表"""
        return self._config.get("default_rewards", [])

    def get_default_recipes(self) -> List[Dict[str, Any]]:
        """获取默认兑换配方列表"""
        return self._config.get("default_recipes", [])

    def get_source_type_mapping(self) -> Dict[str, str]:
        """获取source_type枚举映射（基于v3文档）"""
        return {
            "task_complete": TransactionSource.TASK_COMPLETE,
            "task_complete_top3": TransactionSource.TASK_COMPLETE_TOP3,
            "top3_cost": TransactionSource.TOP3_COST,
            "lottery_points": TransactionSource.LOTTERY_POINTS,
            "lottery_reward": TransactionSource.LOTTERY_REWARD,
            "recharge": TransactionSource.RECHARGE,
            "redemption": TransactionSource.REDEMPTION,
            "manual": TransactionSource.MANUAL
        }

    def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取配方"""
        recipes = self.get_default_recipes()
        for recipe in recipes:
            if recipe["id"] == recipe_id:
                return recipe
        return None

    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证抽奖奖品池不为空
            if not self.get_lottery_reward_pool():
                raise ValueError("抽奖奖品池不能为空")

            # 验证基础奖励配置
            if not self.get_default_rewards():
                raise ValueError("基础奖品配置不能为空")

            # 验证兑换配方配置
            if not self.get_default_recipes():
                raise ValueError("兑换配方配置不能为空")

            # 验证积分数值为正数
            if self.get_normal_task_points() <= 0:
                raise ValueError("普通任务积分必须大于0")

            if self.get_top3_cost_points() <= 0:
                raise ValueError("Top3设置成本必须大于0")

            # 验证概率值在0-1之间
            lottery_config = self.get_top3_lottery_config()
            if not 0 <= lottery_config["points_probability"] <= 1:
                raise ValueError("Top3抽奖积分概率必须在0-1之间")

            if not 0 <= lottery_config["reward_probability"] <= 1:
                raise ValueError("Top3抽奖奖品概率必须在0-1之间")

            return True

        except Exception as e:
            print(f"游戏化配置验证失败: {e}")
            return False


# 全局配置实例
reward_config = RewardConfig()