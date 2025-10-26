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

        # v4：删除LOTTERY_REWARD_POOL环境变量处理，改为数据库动态获取

        return default_config

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（v4重构：简化配置）"""
        return {
            # 基础奖励配置
            "normal_task_points": 2,
            "top3_cost_points": 300,

            # Top3抽奖配置
            "top3_lottery_points_probability": 0.5,
            "top3_lottery_reward_probability": 0.5,
            "top3_lottery_points_amount": 100,  # v4：保留此配置，用于安慰奖积分

            # v4：删除以下配置项，改为数据库动态管理
            # - lottery_reward_pool：从rewards表动态获取is_active=true的奖品
            # - default_rewards：通过数据库管理奖品
            # - default_recipes：通过数据库管理配方
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

    # v4：向后兼容方法（临时解决方案）
    def get_default_rewards(self) -> List[Dict[str, Any]]:
        """
        v4兼容方法：返回空列表，因为现在使用数据库动态管理

        Returns:
            List[Dict[str, Any]]: 空列表（v4中不再使用静态配置）
        """
        # v4：改为数据库动态管理，返回空列表
        return []

    def get_default_recipes(self) -> List[Dict[str, Any]]:
        """
        v4兼容方法：返回空列表，因为现在使用数据库动态管理

        Returns:
            List[Dict[str, Any]]: 空列表（v4中不再使用静态配置）
        """
        # v4：改为数据库动态管理，返回空列表
        return []

    def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        v4兼容方法：返回None，因为现在使用数据库动态管理

        Args:
            recipe_id (str): 配方ID

        Returns:
            Optional[Dict[str, Any]]: None（v4中不再使用静态配置）
        """
        # v4：改为数据库动态管理，返回None
        return None

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

    # v4：删除get_recipe_by_id方法，使用RecipeRepository.get_recipe_with_details()

    def validate_config(self) -> bool:
        """验证配置的有效性（v4简化版）"""
        try:
            # v4：只验证必要的配置项
            # 验证积分数值为正数
            if self.get_normal_task_points() <= 0:
                raise ValueError("普通任务积分必须大于0")

            if self.get_top3_cost_points() <= 0:
                raise ValueError("Top3设置成本必须大于0")

            # 验证Top3抽奖配置
            lottery_config = self.get_top3_lottery_config()
            if not 0 <= lottery_config["points_probability"] <= 1:
                raise ValueError("Top3抽奖积分概率必须在0-1之间")

            if not 0 <= lottery_config["reward_probability"] <= 1:
                raise ValueError("Top3抽奖奖品概率必须在0-1之间")

            if lottery_config["points_amount"] < 0:
                raise ValueError("Top3抽奖安慰奖积分不能为负数")

            # v4：不再验证以下项目，因为改为数据库动态管理
            # - 抽奖奖品池（通过数据库查询验证）
            # - 基础奖品配置（通过数据库模型验证）
            # - 兑换配方配置（通过数据库模型验证）

            return True

        except Exception as e:
            print(f"游戏化配置验证失败: {e}")
            return False


# 全局配置实例
reward_config = RewardConfig()