"""
零Bug测试体系 - 积分系统测试数据工厂

提供积分系统相关的测试数据生成。
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import BaseFactory, register_factory


@register_factory("points_transaction")
class PointsTransactionFactory(BaseFactory):
    """积分交易工厂"""

    DEFAULTS = {
        "id": "",
        "user_id": "",
        "transaction_type": "",
        "points_change": 0,
        "balance_before": 0,
        "balance_after": 0,
        "reason": "",
        "reference_id": None,
        "reference_type": "",
        "created_at": None,
    }

    REQUIRED_FIELDS = ["user_id", "transaction_type", "points_change"]

    TRANSACTION_TYPES = ["earn", "spend", "refund", "bonus", "penalty"]
    REFERENCE_TYPES = ["task_completion", "reward_redemption", "daily_bonus", "admin_adjustment"]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建积分交易数据"""
        transaction_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        points_change = overrides.get("points_change", cls._generate_int(-1000, 1000))

        defaults = cls._merge_data(cls.DEFAULTS, {
            "id": transaction_id,
            "user_id": overrides.get("user_id", f"user_{uuid.uuid4().hex[:8]}"),
            "transaction_type": cls._generate_choice(cls.TRANSACTION_TYPES),
            "points_change": points_change,
            "balance_before": cls._generate_int(0, 5000),
            "balance_after": lambda: defaults["balance_before"] + points_change,
            "reason": f"积分变动_{transaction_id[:8]}",
            "reference_id": str(uuid.uuid4()),
            "reference_type": cls._generate_choice(cls.REFERENCE_TYPES),
            "created_at": timestamp,
        })

        # 计算余额
        defaults["balance_after"] = defaults["balance_before"] + defaults["points_change"]

        transaction_data = cls._merge_data(defaults, overrides)
        cls.validate_data(transaction_data)
        return transaction_data