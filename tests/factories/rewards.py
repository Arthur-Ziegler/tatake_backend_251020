"""
零Bug测试体系 - 奖励系统测试数据工厂

提供奖励相关的测试数据生成，包括奖励、用户奖励、配方等。

设计原则：
1. 覆盖所有奖励类型和状态
2. 确保奖励数据一致性
3. 支持奖励兑换和库存管理
4. 自动生成关联数据
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import BaseFactory, register_factory


@register_factory("reward")
class RewardFactory(BaseFactory):
    """奖励测试数据工厂"""

    DEFAULTS = {
        "id": "",
        "name": "",
        "description": "",
        "type": "physical",
        "points_cost": 100,
        "stock_quantity": 50,
        "image_url": "",
        "is_active": True,
        "category": "general",
        "created_at": None,
        "updated_at": None,
    }

    REQUIRED_FIELDS = ["name", "points_cost", "stock_quantity"]

    REWARD_TYPES = ["physical", "digital", "coupon", "experience"]
    CATEGORIES = ["electronics", "books", "food", "travel", "entertainment", "general"]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建奖励数据"""
        reward_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        defaults = cls._merge_data(cls.DEFAULTS, {
            "id": reward_id,
            "name": f"测试奖励_{reward_id[:8]}",
            "description": f"测试奖励{reward_id[:8]}的详细描述",
            "type": cls._generate_choice(cls.REWARD_TYPES),
            "points_cost": cls._generate_int(10, 1000),
            "stock_quantity": cls._generate_int(1, 100),
            "image_url": f"https://rewards.test.com/{reward_id[:12]}.jpg",
            "category": cls._generate_choice(cls.CATEGORIES),
            "created_at": timestamp,
            "updated_at": timestamp,
        })

        reward_data = cls._merge_data(defaults, overrides)
        cls.validate_data(reward_data)
        return reward_data





@register_factory("recipe")
class RecipeFactory(BaseFactory):
    """奖励配方工厂"""

    DEFAULTS = {
        "id": "",
        "name": "",
        "description": "",
        "required_points": 100,
        "required_level": 1,
        "reward_ids": [],
        "is_active": True,
        "created_at": None,
    }

    REQUIRED_FIELDS = ["name", "required_points", "reward_ids"]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建配方数据"""
        recipe_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # 生成奖励ID列表
        reward_count = cls._generate_int(1, 3)
        reward_ids = [str(uuid.uuid4()) for _ in range(reward_count)]

        defaults = cls._merge_data(cls.DEFAULTS, {
            "id": recipe_id,
            "name": f"测试配方_{recipe_id[:8]}",
            "description": f"测试配方{recipe_id[:8]}的详细描述",
            "required_points": cls._generate_int(50, 500),
            "required_level": cls._generate_int(1, 10),
            "reward_ids": reward_ids,
            "is_active": True,
            "created_at": timestamp,
        })

        recipe_data = cls._merge_data(defaults, overrides)
        cls.validate_data(recipe_data)
        return recipe_data