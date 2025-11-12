"""
奖励API路由 - 微服务代理模式

提供3个核心奖励接口的微服务代理：
1. 查看我的奖品
2. 查看我的积分
3. 充值界面（兑换奖品）

作者：TaTake团队
版本：2.0.0（纯微服务）
"""

from typing import Dict, Any
from uuid import UUID
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services.reward_microservice_client import RewardMicroserviceClient, get_reward_client
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


@router.get("/prizes", response_model=UnifiedResponse[Dict[str, Any]], summary="查看我的奖品")
async def get_my_prizes_endpoint(
    user_id: UUID = Depends(get_current_user_id),
    client: RewardMicroserviceClient = Depends(get_reward_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """4.1 查看我的奖品 - 微服务代理"""
    try:
        logger.info(f"查看我的奖品API调用: user_id={user_id}")
        response = await client.get_prizes(str(user_id))

        return UnifiedResponse(
            code=200,
            data=response,
            message="获取奖品列表成功"
        )
    except Exception as e:
        logger.error(f"查看我的奖品异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/points", response_model=UnifiedResponse[Dict[str, Any]], summary="查看我的积分")
async def get_my_points_endpoint(
    user_id: UUID = Depends(get_current_user_id),
    client: RewardMicroserviceClient = Depends(get_reward_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """4.2 查看我的积分 - 微服务代理"""
    try:
        logger.info(f"查看我的积分API调用: user_id={user_id}")
        response = await client.get_points(str(user_id))

        return UnifiedResponse(
            code=200,
            data=response,
            message="获取积分信息成功"
        )
    except Exception as e:
        logger.error(f"查看我的积分异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redeem", response_model=UnifiedResponse[Dict[str, Any]], summary="充值界面（兑换奖品）")
async def redeem_prize_endpoint(
    request: RedeemPrizeRequest,
    user_id: UUID = Depends(get_current_user_id),
    client: RewardMicroserviceClient = Depends(get_reward_client)
) -> UnifiedResponse[Dict[str, Any]]:
    """4.3 充值界面（兑换奖品） - 微服务代理"""
    try:
        logger.info(f"兑换奖品API调用: user_id={user_id}, code={request.code}")
        response = await client.redeem(str(user_id), request.code)

        # 检查微服务响应格式
        if not isinstance(response, dict):
            logger.error(f"Reward微服务响应格式异常: {response}")
            raise HTTPException(status_code=500, detail="Reward微服务响应格式异常")

        # 直接透传微服务的响应，包括真实的业务状态码和消息
        # 不再硬编码code=200和message="兑换成功"
        business_code = response.get("code", 500)
        business_message = response.get("message", "兑换处理完成")
        business_data = response.get("data")

        logger.info(f"兑换奖品结果: code={business_code}, message={business_message}")

        return UnifiedResponse(
            code=business_code,
            message=business_message,
            data=business_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"兑换奖品异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))
