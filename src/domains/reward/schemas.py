"""Reward领域Schema定义"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ===== 奖品相关 =====

class RewardResponse(BaseModel):
    """奖品响应"""
    id: str
    name: str
    icon: Optional[str]
    description: Optional[str]
    is_exchangeable: bool


class RewardCatalogResponse(BaseModel):
    """奖品目录响应"""
    rewards: List[RewardResponse]
    total_count: int




class MyRewardsResponse(BaseModel):
    """我的奖品响应"""
    rewards: List[RewardResponse]
    total_types: int


# ===== 兑换相关 =====

class RewardRedeemRequest(BaseModel):
    """兑换奖品请求"""
    recipe_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="配方ID")


class RewardRedeemResponse(BaseModel):
    """兑换奖品响应"""
    success: bool
    result_reward: RewardResponse
    consumed_rewards: List[Dict[str, Any]]  # [{"reward": {...}, "quantity": 10}]
    message: str


# ===== 积分相关 =====

class PointsBalanceResponse(BaseModel):
    """积分余额响应"""
    current_balance: int
    total_earned: int
    total_spent: int


class PointsTransactionResponse(BaseModel):
    """积分流水响应"""
    id: str
    amount: int
    source: str
    related_task_id: Optional[str]
    created_at: str


class PointsTransactionsResponse(BaseModel):
    """积分流水列表响应"""
    transactions: List[PointsTransactionResponse]
    total_count: int
    balance: int


# ===== 任务完成奖励 =====

class LotteryResult(BaseModel):
    """抽奖结果"""
    type: str  # "points" | "reward"
    amount: Optional[int] = None  # 积分数量
    reward: Optional[RewardResponse] = None  # 奖品


class TaskCompleteResponse(BaseModel):
    """任务完成响应"""
    task_id: str
    status: str
    lottery_result: Optional[LotteryResult]
    message: str


# ===== 配方合成相关 =====

class RedeemRecipeRequest(BaseModel):
    """
    配方兑换请求Schema

    用于配方合成操作的API请求。

    设计说明：
    - 配方ID从URL路径参数获取
    - 用户ID从JWT token中自动提取
    - 请求体为空，简化API调用
    """
    model_config = {"extra": "forbid"}

    # 请求体为空，所有必要信息从URL和JWT获取


class RecipeMaterial(BaseModel):
    """配方材料"""
    reward_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="奖品ID")
    reward_name: str = Field(...,
        example="魔法药剂", description="奖品名称")
    quantity: int = Field(..., ge=1, description="材料数量", example=2)


class RecipeReward(BaseModel):
    """配方奖品信息"""
    id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="奖品ID")
    name: str = Field(...,
        example="神秘宝箱", description="奖品名称")
    description: Optional[str] = Field(None,
        example="包含随机奖励的神秘宝箱", description="奖品描述")
    image_url: Optional[str] = Field(None,
        example="https://example.com/reward.jpg", description="奖品图片URL")
    category: str = Field(...,
        example="稀有", description="奖品类别")


class RedeemRecipeResponse(BaseModel):
    """
    配方兑换响应Schema

    用于返回配方合成操作的详细结果。

    字段说明：
    - success: 操作是否成功
    - recipe_id: 配方ID
    - recipe_name: 配方名称
    - result_reward: 合成结果奖品
    - materials_consumed: 消耗的材料列表
    - transaction_group: 事务组ID，用于追踪关联操作
    - message: 操作结果描述
    """
    success: bool = Field(...,
        example=True, description="操作是否成功")
    recipe_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="配方ID")
    recipe_name: Optional[str] = Field(None,
        example="初级合成配方", description="配方名称")
    result_reward: RecipeReward = Field(...,
        description="合成结果奖品")
    materials_consumed: List[RecipeMaterial] = Field(...,
        description="消耗的材料列表")
    transaction_group: Optional[str] = Field(None,
        example="txn_group_12345", description="事务组ID")
    message: str = Field(...,
        example="配方合成成功", description="操作结果描述")


class UserMaterial(BaseModel):
    """用户材料"""
    reward_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="奖品ID")
    reward_name: str = Field(...,
        example="魔法药剂", description="奖品名称")
    image_url: Optional[str] = Field(None,
        example="https://example.com/potion.jpg", description="奖品图片URL")
    quantity: int = Field(..., ge=0, example=5, description="拥有数量")


class UserMaterialsResponse(BaseModel):
    """用户材料列表响应"""
    materials: List[UserMaterial] = Field(...,
        description="用户材料列表")
    total_types: int = Field(...,
        example=15, description="材料种类总数")


class AvailableRecipe(BaseModel):
    """可用配方"""
    id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440000", description="配方ID")
    name: str = Field(...,
        example="初级合成配方", description="配方名称")
    result_reward_id: str = Field(...,
        example="550e8400-e29b-41d4-a716-446655440001", description="结果奖品ID")
    result_reward_name: str = Field(...,
        example="神秘宝箱", description="结果奖品名称")
    result_image_url: Optional[str] = Field(None,
        example="https://example.com/chest.jpg", description="结果奖品图片")
    materials: List[RecipeMaterial] = Field(...,
        description="所需材料列表")
    created_at: datetime = Field(...,
        example="2024-01-15T10:30:00Z", description="创建时间")


class AvailableRecipesResponse(BaseModel):
    """可用配方列表响应"""
    recipes: List[AvailableRecipe] = Field(...,
        description="可用配方列表")
    total_count: int = Field(...,
        example=25, description="可用配方总数")


