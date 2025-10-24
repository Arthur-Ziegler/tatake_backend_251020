"""
Points领域异常类

定义积分系统相关的自定义异常。

异常类型：
1. PointsNotFoundException: 积分记录未找到
2. PointsInsufficientException: 积分不足异常

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

from typing import Optional
from uuid import UUID


class PointsException(Exception):
    """积分系统基础异常"""
    pass


class PointsNotFoundException(PointsException):
    """积分记录未找到异常

    当查询的积分记录不存在时抛出。
    """
    def __init__(self, message: str, points_id: Optional[UUID] = None):
        super().__init__(message)
        self.points_id = points_id


class PointsInsufficientException(PointsException):
    """积分不足异常

    当用户积分不足时抛出。
    """
    def __init__(self, message: str, required_points: int = None, current_points: int = None):
        super().__init__(message)
        self.required_points = required_points
        self.current_points = current_points