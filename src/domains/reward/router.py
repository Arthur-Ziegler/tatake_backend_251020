"""Reward领域API路由"""

import logging
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlmodel import Session

from .service import RewardService
from src.domains.points.service import PointsService
from .schemas import (
    RewardCatalogResponse,
    MyRewardsResponse,
    RewardRedeemRequest,
    RewardRedeemResponse,
    PointsBalanceResponse,
    PointsTransactionsResponse,
    RedeemRecipeRequest,
    RedeemRecipeResponse,
    AvailableRecipe,
    AvailableRecipesResponse,
    RecipeMaterial,
    RecipeReward,
    RewardTransactionsResponse
)
from src.domains.auth.schemas import UnifiedResponse
from .exceptions import RewardException
from src.api.dependencies import get_current_user_id
from src.database import SessionDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rewards", tags=["奖励系统"])
points_router = APIRouter(prefix="/points", tags=["积分系统"])


# ===== 奖品API =====

@router.get("/catalog", response_model=UnifiedResponse[RewardCatalogResponse], summary="获取奖品目录", description="获取系统中所有可用奖品的完整目录，包括奖品名称、描述、价值和兑换条件。")
async def get_reward_catalog(
    session: SessionDep
) -> UnifiedResponse[RewardCatalogResponse]:
    """获取所有可用奖品目录"""
    try:
        points_service = PointsService(session)
        service = RewardService(session, points_service)
        catalog_data = service.get_reward_catalog()

        # 构建响应数据模型
        response_data = RewardCatalogResponse(
            rewards=catalog_data["rewards"],
            total_count=catalog_data["total_count"]
        )

        return UnifiedResponse(code=200, data=response_data, message="success")
    except Exception as e:
        logger.error(f"获取奖品目录失败: {e}")
        return UnifiedResponse(code=500, data=None, message="获取奖品目录失败")


@router.get("/my-rewards", response_model=UnifiedResponse[MyRewardsResponse], summary="获取我的奖品", description="获取当前用户拥有的所有奖品及数量，包括通过任务完成和兑换获得的奖品。")
async def get_my_rewards(
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[MyRewardsResponse]:
    """获取当前用户拥有的所有奖品"""
    try:
        points_service = PointsService(session)
        service = RewardService(session, points_service)
        rewards_data = service.get_my_rewards(user_id)

        # 构建响应数据模型
        response_data = MyRewardsResponse(
            rewards=rewards_data["rewards"],
            total_types=rewards_data["total_types"]
        )

        return UnifiedResponse(code=200, data=response_data, message="success")
    except Exception as e:
        logger.error(f"获取我的奖品失败: {e}")
        return UnifiedResponse(code=500, data=None, message="获取我的奖品失败")


@router.get("/my-rewards/transactions", response_model=UnifiedResponse[RewardTransactionsResponse], summary="获取奖品流水", description="获取当前用户的奖品获得和消耗流水记录，支持分页查询。")
async def get_reward_transactions(
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量")
) -> UnifiedResponse[RewardTransactionsResponse]:
    """获取当前用户的奖品流水记录"""
    try:
        points_service = PointsService(session)
        service = RewardService(session, points_service)
        
        # 获取流水记录
        offset = (page - 1) * page_size
        transactions = service.get_reward_transactions(user_id, limit=page_size, offset=offset)
        
        # 计算各奖品余额汇总
        balance_summary = {}
        for transaction in transactions:
            reward_id = transaction.get("reward_id")
            quantity = transaction.get("quantity", 0)
            if reward_id and reward_id != "points":
                balance_summary[reward_id] = balance_summary.get(reward_id, 0) + quantity
        
        # 构建响应数据
        response_data = RewardTransactionsResponse(
            transactions=transactions,
            total_count=len(transactions),  # 简化实现，实际应该查询总数
            balance_summary=balance_summary
        )

        return UnifiedResponse(code=200, data=response_data, message="success")
    except Exception as e:
        logger.error(f"获取奖品流水失败: {e}")
        return UnifiedResponse(code=500, data=None, message="获取奖品流水失败")


@router.post("/exchange/{reward_id}", response_model=UnifiedResponse[RewardRedeemResponse], summary="积分兑换奖品")
async def exchange_reward_with_points(
    reward_id: str,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[RewardRedeemResponse]:
    """使用积分兑换奖品"""
    try:
        points_service = PointsService(session)
        service = RewardService(session, points_service)
        redeem_data = service.redeem_reward(str(user_id), reward_id)

        # 构建响应数据模型
        response_data = RewardRedeemResponse(
            success=redeem_data["success"],
            result_reward=redeem_data["result_reward"],
            consumed_rewards=redeem_data["consumed_rewards"],
            message=redeem_data["message"]
        )

        return UnifiedResponse(code=200, data=response_data, message="success")
    except RewardException as e:
        return UnifiedResponse(code=e.status_code, data=None, message=e.detail)
    except Exception as e:
        logger.error(f"积分兑换奖品失败: {e}")
        return UnifiedResponse(code=500, data=None, message="积分兑换奖品失败")


# ===== 积分API =====

@points_router.get("/my-points", summary="获取积分余额")
async def get_points_balance_my_points(
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
):
    """获取当前用户积分余额 - v3 API路径"""
    try:
        points_service = PointsService(session)
        balance = points_service.get_balance(str(user_id))

        # 计算统计数据
        transactions = points_service.get_transactions(str(user_id), limit=1000)
        total_earned = sum(t['amount'] for t in transactions if t['amount'] > 0)
        total_spent = abs(sum(t['amount'] for t in transactions if t['amount'] < 0))

        return {
            "code": 200,
            "data": {
                "current_balance": balance,
                "total_earned": total_earned,
                "total_spent": total_spent
            },
            "message": "获取积分余额成功"
        }
    except Exception as e:
        logger.error(f"获取积分余额失败: {e}")
        raise HTTPException(status_code=500, detail="获取积分余额失败")


  
@points_router.get("/transactions", summary="获取积分流水")
async def get_points_transactions(
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量")
):
    """获取当前用户积分流水记录"""
    try:
        points_service = PointsService(session)
        transactions = points_service.get_transactions(str(user_id), limit=page_size, offset=(page-1)*page_size)

        # 获取当前余额
        balance = points_service.get_balance(str(user_id))

        # 转换数据库模型为响应模型
        transaction_responses = []
        for transaction in transactions:
            transaction_responses.append({
                "id": transaction["id"],
                "amount": transaction["amount"],
                "source": transaction["source_type"],
                "related_task_id": transaction["source_id"],
                "created_at": transaction["created_at"].isoformat() if isinstance(transaction["created_at"], datetime) else transaction["created_at"]
            })

        transactions_data = PointsTransactionsResponse(
            transactions=transaction_responses,
            total_count=len(transactions),  # 简化实现，实际应该查询总数
            balance=balance
        )

        # 使用标准响应格式
        from src.api.response_utils import StandardResponse
        return StandardResponse.success(
            data=transactions_data.dict(),
            message="获取积分流水成功"
        )
    except Exception as e:
        logger.error(f"获取积分流水失败: {e}")
        from src.api.response_utils import StandardResponse
        return StandardResponse.server_error("获取积分流水失败")




@router.get("/recipes", response_model=UnifiedResponse[AvailableRecipesResponse], summary="获取可用配方")
async def get_available_recipes(
    session: SessionDep
) -> UnifiedResponse[AvailableRecipesResponse]:
    """
    获取所有可用的配方列表

    返回系统中所有可用的配方及其材料要求。

    Args:
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[AvailableRecipesResponse]: 可用配方列表响应
    """
    try:
        logger.info("获取可用配方列表")

        # 创建奖励服务
        points_service = PointsService(session)
        reward_service = RewardService(session, points_service)

        # 获取可用配方
        recipes_data = reward_service.get_available_recipes()

        # 构建响应数据
        available_recipes = []
        for recipe in recipes_data:
            # 处理materials字段，可能是字符串格式的JSON
            materials = recipe["materials"]
            if isinstance(materials, str):
                import json
                try:
                    materials = json.loads(materials)
                except json.JSONDecodeError:
                    materials = []
            elif not isinstance(materials, list):
                materials = []

            recipe_materials = [
                RecipeMaterial(
                    reward_id=material.get("reward_id", ""),
                    reward_name=material.get("reward_name", "未知材料"),
                    quantity=material.get("quantity", 0)
                )
                for material in materials
            ]

            available_recipes.append(
                AvailableRecipe(
                    id=recipe["id"],
                    name=recipe["name"],
                    result_reward_id=recipe["result_reward_id"],
                    result_reward_name=recipe["result_reward_name"],
                    result_image_url=recipe["result_image_url"],
                    materials=recipe_materials,
                    created_at=recipe["created_at"]
                )
            )

        response_data = AvailableRecipesResponse(
            recipes=available_recipes,
            total_count=len(available_recipes)
        )

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=response_data,
            message="获取可用配方成功"
        )

    except Exception as e:
        logger.error(f"获取可用配方失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="获取可用配方失败"
        )


@router.post("/recipes/{recipe_id}/redeem",
              response_model=UnifiedResponse[RedeemRecipeResponse],
              summary="配方合成奖品")
async def redeem_recipe(
    recipe_id: str,
    request: RedeemRecipeRequest,
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[RedeemRecipeResponse]:
    """
    使用配方合成奖品

    业务流程：
    1. 验证配方存在性和可用性
    2. 检查用户材料是否充足
    3. 扣除材料并发放结果奖品
    4. 记录所有流水记录（事务组关联）
    5. 返回合成结果

    注意事项：
    - 材料不足会导致合成失败
    - 所有操作在事务中执行，确保数据一致性
    - 合成成功后材料会被扣除，无法恢复

    Args:
        recipe_id (str): 配方ID
        request (RedeemRecipeRequest): 配方合成请求（空请求体）
        user_id (UUID): 当前用户ID（从JWT token中获取）
        session (Session): 数据库会话

    Returns:
        UnifiedResponse[RedeemRecipeResponse]: 配方合成结果响应
    """
    try:
        logger.info(f"配方合成API调用: recipe_id={recipe_id}, user_id={user_id}")

        # 创建奖励服务
        points_service = PointsService(session)
        reward_service = RewardService(session, points_service)

        # 执行配方合成业务流程
        result = reward_service.compose_rewards(str(user_id), recipe_id)

        # 构建响应数据
        response_data = RedeemRecipeResponse(
            success=result["success"],
            recipe_id=result["recipe_id"],
            recipe_name=result["recipe_name"],
            result_reward=RecipeReward(
                id=result["result_reward"]["id"],
                name=result["result_reward"]["name"],
                description=result["result_reward"]["description"],
                image_url=result["result_reward"]["image_url"],
                category=result["result_reward"]["category"]
            ),
            materials_consumed=[
                RecipeMaterial(
                    reward_id=material["reward_id"],
                    reward_name="",  # 材料名称在响应中可选
                    quantity=material["quantity"]
                )
                for material in result["materials_consumed"]
            ],
            transaction_group=result["transaction_group"],
            message=result["message"]
        )

        # 返回成功响应
        return UnifiedResponse(
            code=200,
            data=response_data,
            message=result["message"]
        )

    except Exception as e:
        logger.error(f"配方合成失败: {e}")
        return UnifiedResponse(
            code=400,
            data=None,
            message=str(e)
        )
