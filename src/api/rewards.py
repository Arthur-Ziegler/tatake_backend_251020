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
from ..services.reward_mock_service import get_reward_mock_service
from ..api.config import config

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
    4.1 查看我的奖品 - 微服务代理 (Mock模式)

    注意：当前使用Mock实现，等待奖励服务完成后切换到真实微服务
    """
    try:
        logger.info(f"查看我的奖品API调用: user_id={user_id}")

        # 检查是否启用Mock模式
        if not config.reward_service_enabled:
            logger.info("使用Mock奖励服务")
            mock_service = get_reward_mock_service()
            mock_response = await mock_service.get_my_prizes(str(user_id))

            return UnifiedResponse(
                code=200,
                data=mock_response,
                message="获取奖品列表成功 (Mock数据)"
            )

        # 调用真实微服务
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
    4.2 查看我的积分 - 微服务代理 (Mock模式)

    注意：当前使用Mock实现，等待奖励服务完成后切换到真实微服务
    """
    try:
        logger.info(f"查看我的积分API调用: user_id={user_id}")

        # 检查是否启用Mock模式
        if not config.reward_service_enabled:
            logger.info("使用Mock奖励服务")
            mock_service = get_reward_mock_service()
            mock_response = await mock_service.get_my_points(str(user_id))

            return UnifiedResponse(
                code=200,
                data=mock_response,
                message="获取积分信息成功 (Mock数据)"
            )

        # 调用真实微服务
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
    4.3 充值界面（兑换奖品） - 微服务代理 (Mock模式)

    注意：当前使用Mock实现，等待奖励服务完成后切换到真实微服务
    """
    try:
        logger.info(f"兑换奖品API调用: user_id={user_id}, code={request.code}")

        # 检查是否启用Mock模式
        if not config.reward_service_enabled:
            logger.info("使用Mock奖励服务")
            mock_service = get_reward_mock_service()
            mock_response = await mock_service.redeem_prize(str(user_id), request.code)

            if mock_response.get("success", False):
                return UnifiedResponse(
                    code=200,
                    data=mock_response,
                    message=f"兑换成功 (Mock数据)"
                )
            else:
                return UnifiedResponse(
                    code=400,
                    data=None,
                    message=mock_response.get("message", "兑换失败")
                )

        # 调用真实微服务
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


# 添加奖励系统相关的额外接口（基于docs/API完整文档.md）

@router.get("/catalog", response_model=UnifiedResponse[Dict[str, Any]], summary="获取奖品目录")
async def get_reward_catalog_endpoint(
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    4.4 获取奖品目录 - Mock模式

    返回所有可用的奖品列表，包括积分价值和分类信息。
    """
    try:
        logger.info(f"获取奖品目录API调用: user_id={user_id}")

        # 使用Mock服务
        mock_service = get_reward_mock_service()
        catalog_response = await mock_service.get_reward_catalog()

        return UnifiedResponse(
            code=200,
            data=catalog_response,
            message="获取奖品目录成功 (Mock数据)"
        )

    except Exception as e:
        logger.error(f"获取奖品目录异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.get("/recipes", response_model=UnifiedResponse[Dict[str, Any]], summary="获取奖品配方")
async def get_reward_recipes_endpoint(
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    4.5 获取奖品配方 - Mock模式

    返回所有可用的奖品合成配方，包括所需材料和产出结果。
    """
    try:
        logger.info(f"获取奖品配方API调用: user_id={user_id}")

        # 使用Mock服务
        mock_service = get_reward_mock_service()
        recipes_response = await mock_service.get_reward_recipes()

        return UnifiedResponse(
            code=200,
            data=recipes_response,
            message="获取奖品配方成功 (Mock数据)"
        )

    except Exception as e:
        logger.error(f"获取奖品配方异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )


@router.post("/recipes/{recipe_id}/redeem", response_model=UnifiedResponse[Dict[str, Any]], summary="合成奖品")
async def craft_reward_endpoint(
    recipe_id: str,
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[Dict[str, Any]]:
    """
    4.6 合成奖品 - Mock模式

    使用指定的配方合成奖品，会检查材料是否足够并扣除相应材料。
    """
    try:
        logger.info(f"合成奖品API调用: user_id={user_id}, recipe_id={recipe_id}")

        # 使用Mock服务
        mock_service = get_reward_mock_service()
        craft_response = await mock_service.craft_reward(str(user_id), recipe_id)

        if craft_response.get("success", False):
            return UnifiedResponse(
                code=200,
                data=craft_response,
                message="合成成功 (Mock数据)"
            )
        else:
            return UnifiedResponse(
                code=400,
                data=None,
                message=craft_response.get("message", "合成失败")
            )

    except Exception as e:
        logger.error(f"合成奖品异常: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="内部服务器错误"
        )