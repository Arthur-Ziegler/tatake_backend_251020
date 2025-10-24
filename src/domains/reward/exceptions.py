"""Reward领域异常定义"""

from typing import List, Dict
from fastapi import status


class RewardException(Exception):
    """奖励系统基础异常"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class RewardNotFoundException(RewardException):
    """奖品不存在"""
    def __init__(self, reward_id: str):
        super().__init__(
            detail=f"奖品不存在: {reward_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class RecipeNotFoundException(RewardException):
    """兑换配方不存在"""
    def __init__(self, recipe_id: str):
        super().__init__(
            detail=f"兑换配方不存在: {recipe_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class InsufficientRewardsException(RewardException):
    """奖品数量不足"""
    def __init__(self, message: str, required_materials: List[Dict] = None):
        self.required_materials = required_materials or []
        super().__init__(
            detail=f"奖品数量不足: {message}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InsufficientPointsException(RewardException):
    """积分不足"""
    def __init__(self, required: int, current: int):
        super().__init__(
            detail=f"积分不足，需要{required}积分，当前{current}积分",
            status_code=status.HTTP_400_BAD_REQUEST
        )
