"""
零Bug测试体系 - Top3系统测试数据工厂

提供Top3系统相关的测试数据生成。
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import BaseFactory, register_factory


@register_factory("top3_task")
class Top3TaskFactory(BaseFactory):
    """Top3任务工厂"""

    DEFAULTS = {
        "id": "",
        "user_id": "",
        "task_id": "",
        "priority_rank": 1,
        "selection_date": None,
        "is_active": True,
        "completion_status": "pending",
        "created_at": None,
        "updated_at": None,
    }

    REQUIRED_FIELDS = ["user_id", "task_id", "priority_rank"]

    COMPLETION_STATUSES = ["pending", "in_progress", "completed", "cancelled"]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建Top3任务数据"""
        top3_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        defaults = cls._merge_data(cls.DEFAULTS, {
            "id": top3_id,
            "user_id": overrides.get("user_id", f"user_{uuid.uuid4().hex[:8]}"),
            "task_id": overrides.get("task_id", str(uuid.uuid4())),
            "priority_rank": cls._generate_int(1, 3),
            "selection_date": timestamp.date(),
            "is_active": True,
            "completion_status": cls._generate_choice(cls.COMPLETION_STATUSES),
            "created_at": timestamp,
            "updated_at": timestamp,
        })

        top3_data = cls._merge_data(defaults, overrides)
        cls.validate_data(top3_data)
        return top3_data