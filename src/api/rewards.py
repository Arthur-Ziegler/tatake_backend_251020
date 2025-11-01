"""
奖励API路由 - 微服务代理模式

提供3个核心奖励接口的微服务代理：
1. 查看我的奖品
2. 查看我的积分
3. 充值界面（兑换奖品）

作者：TaTake团队
版本：1.0.0（微服务代理）
"""

from typing import Dict, Any, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services.reward_microservice_client import (
    RewardMicroserviceError,
    get_my_prizes, get_my_points, redeem_prize
)

from .schemas import UnifiedResponse
from .dependencies import get_current_user_id

# 配置日志
logger = logging.getLogger(__name__)


# 请求模型
class RedeemPrizeRequest(BaseModel):
    """兑换奖品请求"""
    code: str = Field(..., min_length=1, max_length=100, description="兑换码")


# ==================== API端点实现 ====================

router = APIRouter(prefix="/rewards", tags=["奖励系统"])


def create_error_response(status_code: int, message: str) -> UnifiedResponse:
    """创建错误响应"""
    return UnifiedResponse(
        code=status_code,
        data=None,
        message=message
    )


@router.get("/prizes", response_model=UnifiedResponse[Dict[str, Any]], summary="查看我的奖品")
async def get_my_prizes_endpoint(
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    4.1 查看我的奖品 - 微服务代理
    """
    try:
        logger.info(f"查看我的奖品API调用: user_id={user_id}")

        # 调用微服务便捷方法
        microservice_response = await get_my_prizes(str(user_id))

        return UnifiedResponse(
            code=200,
            data=microservice_response,
            message="获取奖品列表成功"
        )

    except RewardMicroserviceError as e:
        logger.error(f"奖励微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"查看我的奖品异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.get("/points", response_model=UnifiedResponse[Dict[str, Any]], summary="查看我的积分")
async def get_my_points_endpoint(
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    4.2 查看我的积分 - 微服务代理
    """
    try:
        logger.info(f"查看我的积分API调用: user_id={user_id}")

        # 调用微服务便捷方法
        microservice_response = await get_my_points(str(user_id))

        return UnifiedResponse(
            code=200,
            data=microservice_response,
            message="获取积分信息成功"
        )

    except RewardMicroserviceError as e:
        logger.error(f"奖励微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"查看我的积分异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.post("/redeem", response_model=UnifiedResponse[Dict[str, Any]], summary="充值界面（兑换奖品）")
async def redeem_prize_endpoint(
    request: RedeemPrizeRequest,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    4.3 充值界面（兑换奖品） - 微服务代理
    """
    try:
        logger.info(f"兑换奖品API调用: user_id={user_id}, code={request.code}")

        # 调用微服务便捷方法
        microservice_response = await redeem_prize(
            user_id=str(user_id),
            redemption_code=request.code
        )

        return UnifiedResponse(
            code=200,
            data=microservice_response,
            message="兑换成功"
        )

    except RewardMicroserviceError as e:
        logger.error(f"奖励微服务调用失败: {e}")
        return UnifiedResponse(
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"兑换奖品异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )