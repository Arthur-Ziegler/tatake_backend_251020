"""
测试数据工厂

提供统一的测试数据生成功能，包括：
1. UUID数据生成
2. 用户数据生成
3. 任务数据生成
4. 业务对象生成

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum


class TestDataFactory:
    """测试数据工厂类"""

    @staticmethod
    def uuid() -> str:
        """生成UUID字符串"""
        return str(uuid.uuid4())

    @staticmethod
    def uuids(count: int = 3) -> List[str]:
        """生成多个UUID字符串"""
        return [TestDataFactory.uuid() for _ in range(count)]

    @staticmethod
    def user_data(**overrides) -> Dict[str, Any]:
        """生成用户测试数据"""
        default_data = {
            "id": TestDataFactory.uuid(),
            "username": "test_user",
            "email": "test@example.com",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def task_data(**overrides) -> Dict[str, Any]:
        """生成任务测试数据"""
        default_data = {
            "id": TestDataFactory.uuid(),
            "title": "测试任务",
            "description": "这是一个测试任务",
            "status": "pending",
            "priority": "medium",
            "user_id": TestDataFactory.uuid(),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def session_data(**overrides) -> Dict[str, Any]:
        """生成会话测试数据"""
        default_data = {
            "id": TestDataFactory.uuid(),
            "user_id": TestDataFactory.uuid(),
            "title": "测试会话",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def reward_data(**overrides) -> Dict[str, Any]:
        """生成奖励测试数据"""
        default_data = {
            "id": TestDataFactory.uuid(),
            "name": "测试奖励",
            "description": "这是一个测试奖励",
            "points_value": 100,
            "category": "basic",
            "is_active": True
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def focus_session_data(**overrides) -> Dict[str, Any]:
        """生成专注会话测试数据"""
        default_data = {
            "id": TestDataFactory.uuid(),
            "user_id": TestDataFactory.uuid(),
            "title": "专注会话",
            "start_time": datetime.now(timezone.utc),
            "end_time": None,
            "duration_minutes": 25,
            "is_completed": False
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def top3_data(**overrides) -> Dict[str, Any]:
        """生成Top3测试数据"""
        default_data = {
            "id": TestDataFactory.uuid(),
            "user_id": TestDataFactory.uuid(),
            "title": "Top3项目",
            "description": "这是一个Top3项目",
            "priority": 1,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def points_transaction_data(**overrides) -> Dict[str, Any]:
        """生成积分交易测试数据"""
        default_data = {
            "id": TestDataFactory.uuid(),
            "user_id": TestDataFactory.uuid(),
            "points": 10,
            "transaction_type": "task_complete",
            "description": "任务完成奖励",
            "created_at": datetime.now(timezone.utc)
        }
        default_data.update(overrides)
        return default_data


class MockResponse:
    """模拟响应类"""

    def __init__(self, data: Any = None, status_code: int = 200):
        self.data = data
        self.status_code = status_code

    def json(self) -> Any:
        return self.data

    @property
    def text(self) -> str:
        return str(self.data)


class MockSession:
    """模拟数据库会话"""

    def __init__(self):
        self.committed = False
        self.rollbacked = False
        self.closed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rollbacked = True

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MockEngine:
    """模拟数据库引擎"""

    def __init__(self):
        self.url = Mock()
        self.url.driver = "sqlite"

    def connect(self):
        return Mock()

    def dispose(self):
        pass


# 便捷实例
factory = TestDataFactory()