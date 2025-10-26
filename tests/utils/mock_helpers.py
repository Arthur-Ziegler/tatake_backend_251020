"""
测试模拟助手

提供测试中常用的模拟对象和工具
"""

from unittest.mock import Mock
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class MockHelper:
    """测试模拟助手类"""

    @staticmethod
    def create_mock_user(overrides: Optional[Dict[str, Any]] = None) -> Mock:
        """创建模拟用户"""
        user = Mock()
        user.id = str(uuid4())
        user.wechat_nickname = "测试用户"
        user.wechat_openid = str(uuid4())
        user.is_guest = False

        if overrides:
            for key, value in overrides.items():
                setattr(user, key, value)

        return user

    @staticmethod
    def create_mock_task(overrides: Optional[Dict[str, Any]] = None) -> Mock:
        """创建模拟任务"""
        task = Mock()
        task.id = uuid4()
        task.user_id = uuid4()
        task.title = "测试任务"
        task.status = "pending"
        task.priority = "medium"
        task.completion_percentage = 0.0
        task.is_deleted = False

        if overrides:
            for key, value in overrides.items():
                setattr(task, key, value)

        return task