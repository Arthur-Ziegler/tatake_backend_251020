"""
零Bug测试体系 - 专注系统测试数据工厂

提供专注系统相关的测试数据生成，包括专注会话、操作记录等。
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from .base import BaseFactory, register_factory


@register_factory("focus_session")
class FocusSessionFactory(BaseFactory):
    """专注会话工厂"""

    DEFAULTS = {
        "id": "",
        "user_id": "",
        "task_id": None,
        "start_time": None,
        "end_time": None,
        "duration_minutes": 25,
        "status": "completed",
        "distraction_count": 0,
        "quality_score": 8,
        "notes": "",
        "created_at": None,
    }

    REQUIRED_FIELDS = ["user_id", "start_time", "duration_minutes"]

    STATUSES = ["planned", "active", "completed", "interrupted", "cancelled"]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建专注会话数据"""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        start_time = timestamp - timedelta(minutes=cls._generate_int(5, 120))

        defaults = cls._merge_data(cls.DEFAULTS, {
            "id": session_id,
            "user_id": overrides.get("user_id", f"user_{uuid.uuid4().hex[:8]}"),
            "task_id": overrides.get("task_id"),
            "start_time": start_time,
            "end_time": start_time + timedelta(minutes=cls._generate_int(15, 90)),
            "duration_minutes": cls._generate_int(15, 90),
            "status": cls._generate_choice(cls.STATUSES),
            "distraction_count": cls._generate_int(0, 10),
            "quality_score": cls._generate_int(1, 10),
            "notes": f"专注会话备注_{session_id[:8]}",
            "created_at": timestamp,
        })

        session_data = cls._merge_data(defaults, overrides)
        cls.validate_data(session_data)
        return session_data


@register_factory("focus_operation")
class FocusOperationFactory(BaseFactory):
    """专注操作工厂"""

    DEFAULTS = {
        "id": "",
        "session_id": "",
        "user_id": "",
        "operation_type": "",
        "timestamp": None,
        "metadata": {},
    }

    REQUIRED_FIELDS = ["session_id", "user_id", "operation_type"]

    OPERATION_TYPES = ["start", "pause", "resume", "end", "distraction", "milestone"]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建专注操作数据"""
        operation_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        defaults = cls._merge_data(cls.DEFAULTS, {
            "id": operation_id,
            "session_id": overrides.get("session_id", str(uuid.uuid4())),
            "user_id": overrides.get("user_id", f"user_{uuid.uuid4().hex[:8]}"),
            "operation_type": cls._generate_choice(cls.OPERATION_TYPES),
            "timestamp": timestamp,
            "metadata": {
                "source": "test_factory",
                "operation_id": operation_id[:8]
            }
        })

        operation_data = cls._merge_data(defaults, overrides)
        cls.validate_data(operation_data)
        return operation_data