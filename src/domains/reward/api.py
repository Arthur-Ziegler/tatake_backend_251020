"""
奖励系统API路由器

实现v3文档中定义的奖励系统API，包括：
- 奖品目录API
- 我的奖品API
- 积分余额API
- 积分流水API

使用统一的响应格式，暂不依赖认证系统。
"""

import logging
from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session

from .service import RewardService
from .schemas import (
    RewardCatalogResponse,
    MyRewardsResponse,
    PointsBalanceResponse,
    PointsTransactionsResponse,
    RewardRedeemRequest
)
from src.database import SessionDep, get_db_session
from src.api.response_utils import StandardResponse, ResponseCode
from .exceptions import (
    RecipeNotFoundException,
    InsufficientRewardsException
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/rewards", tags=["奖励系统"])
points_router = APIRouter(prefix="/points", tags=["积分系统"])


# ===== 奖品API =====

@router.get("/catalog", summary="获取奖品目录")
async def get_reward_catalog(
    session: SessionDep
) -> Dict[str, Any]:
    """
    获取所有可用奖品目录

    返回系统中所有可兑换的奖品列表。
    """
    try:
        from src.domains.points.service import PointsService
        points_service = PointsService(session)
        service = RewardService(session, points_service)
        result = service.get_reward_catalog()

        return StandardResponse.success(
            data=result.model_dump(),
            message="获取奖品目录成功"
        )
    except Exception as e:
        logger.error(f"获取奖品目录失败: {e}")
        return StandardResponse.server_error("获取奖品目录失败")


@router.get("/my-rewards", summary="获取我的奖品")
async def get_my_rewards(
    session: Session = Depends(get_db_session),
    user_id: str = Query(..., description="用户ID")
) -> Dict[str, Any]:
    """
    获取当前用户拥有的所有奖品

    基于流水记录聚合计算用户拥有的奖品数量。
    """
    try:
        from src.domains.points.service import PointsService
        points_service = PointsService(session)
        service = RewardService(session, points_service)
        result = service.get_my_rewards(UUID(user_id))

        return StandardResponse.success(
            data=result.model_dump(),
            message="获取我的奖品成功"
        )
    except Exception as e:
        logger.error(f"获取我的奖品失败: {e}")
        return StandardResponse.server_error("获取我的奖品失败")


# ===== 积分API =====

@points_router.get("/my-points", summary="获取积分余额")
async def get_points_balance(
    session: Session = Depends(get_db_session),
    user_id: str = Query(..., description="用户ID")
) -> Dict[str, Any]:
    """
    获取当前用户积分余额

    按照v3文档要求，路径为/my-points而不是/balance。
    """
    try:
        from src.domains.points.service import PointsService
        points_service = PointsService(session)
        balance = points_service.get_balance(user_id)

        # 计算统计数据
        transactions = points_service.get_transactions(user_id, limit=1000)
        total_earned = sum(t.amount for t in transactions if t.amount > 0)
        total_spent = abs(sum(t.amount for t in transactions if t.amount < 0))

        return StandardResponse.success(
            data={
                "current_balance": balance,
                "total_earned": total_earned,
                "total_spent": total_spent
            },
            message="获取积分余额成功"
        )
    except Exception as e:
        logger.error(f"获取积分余额失败: {e}")
        return StandardResponse.server_error("获取积分余额失败")


@points_router.get("/transactions", summary="获取积分流水")
async def get_points_transactions(
    session: Session = Depends(get_db_session),
    user_id: str = Query(..., description="用户ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> Dict[str, Any]:
    """
    获取当前用户积分流水记录

    严格按照v3文档的分页格式返回数据。
    """
    try:
        from src.domains.points.service import PointsService
        points_service = PointsService(session)

        # 获取流水记录
        offset = (page - 1) * page_size
        transactions = points_service.get_transactions(user_id, limit=page_size, offset=offset)

        # 计算总数（简化版本，实际应该单独查询）
        total_count = len(points_service.get_transactions(user_id, limit=1000))

        return StandardResponse.success(
            data={
                "transactions": [tx.model_dump() for tx in transactions],
                "pagination": {
                    "current_page": page,
                    "total_pages": (total_count + page_size - 1) // page_size,
                    "total_count": total_count
                }
            },
            message="获取积分流水成功"
        )
    except Exception as e:
        logger.error(f"获取积分流水失败: {e}")
        return StandardResponse.server_error("获取积分流水失败")


# ===== 配方API =====

@router.get("/recipes", summary="获取兑换配方列表")
async def get_recipes(
    session: SessionDep
) -> Dict[str, Any]:
    """
    获取所有兑换配方

    返回包含完整奖品信息的配方列表：
    - result_reward详细信息（id, name, description, points_value）
    - materials详细信息（reward_id UUID, reward_name, quantity）
    """
    try:
        from src.domains.points.service import PointsService
        points_service = PointsService(session)
        service = RewardService(session, points_service)
        recipes = service.get_all_recipes_enriched()

        return StandardResponse.success(
            data={
                "recipes": recipes,
                "total_count": len(recipes)
            },
            message="获取配方列表成功"
        )
    except Exception as e:
        logger.error(f"获取配方列表失败: {e}")
        return StandardResponse.server_error("获取配方列表失败")


# ===== 兑换API =====

@router.post("/redeem", summary="奖品兑换")
async def redeem_reward(
    request: RewardRedeemRequest,
    session: SessionDep
) -> Dict[str, Any]:
    """
    奖品兑换API

    根据配方消耗材料兑换目标奖品：
    - 验证材料数量是否充足
    - 原子操作：扣除材料并给予结果奖品
    - 材料不足时返回详细错误信息
    """
    try:
        from src.domains.points.service import PointsService
        points_service = PointsService(session)
        service = RewardService(session, points_service)

        # 暂时使用固定的用户ID（简化版本，实际应从认证中获取）
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        result = service.redeem_reward(user_id, UUID(request.recipe_id))

        return StandardResponse.success(
            data=result.model_dump(),
            message="兑换成功"
        )

    except RecipeNotFoundException as e:
        logger.error(f"配方不存在: {e}")
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": e.detail,
                "data": {}
            }
        )
    except InsufficientRewardsException as e:
        logger.error(f"材料不足: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": e.detail,
                "data": {"required": e.required_materials}
            }
        )
    except Exception as e:
        logger.error(f"奖品兑换失败: {e}")
        session.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": {}
            }
        )