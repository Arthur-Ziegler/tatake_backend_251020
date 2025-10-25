"""User领域API路由 - UUID类型安全版本

实现UUID类型安全验证和422错误响应。
使用UserService层处理业务逻辑，Repository层处理UUID转换。

功能特性:
- UUID格式验证
- 422错误响应
- 完整的Swagger UUID文档
- UUID类型安全

作者：TaKeKe团队
版本：2.0.0 - UUID架构统一版
"""

import logging
from uuid import UUID
from typing import Dict, Any, Annotated

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session

from .schemas import (
    UserProfileResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
    WelcomeGiftResponse,
    WelcomeGiftHistoryResponse,
    WelcomeGiftHistoryItem
)
from src.domains.auth.schemas import UnifiedResponse
from src.database import get_db_session
from src.api.dependencies import get_current_user_id
from src.domains.user.service import UserService
from src.domains.user.repository import UserRepository
from src.domains.points.service import PointsService
from src.domains.reward.welcome_gift_service import WelcomeGiftService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["用户管理"])


def get_user_service(session: Session) -> UserService:
    """获取UserService实例"""
    user_repo = UserRepository(session)
    return UserService(user_repo)


def get_points_service(session: Session) -> PointsService:
    """获取PointsService实例"""
    return PointsService(session)


def get_welcome_gift_service(session: Session, points_service: PointsService) -> WelcomeGiftService:
    """获取WelcomeGiftService实例"""
    return WelcomeGiftService(session, points_service)


def validate_uuid_parameter(uuid_value: str, parameter_name: str = "UUID") -> UUID:
    """
    验证UUID参数格式

    Args:
        uuid_value (str): UUID字符串值
        parameter_name (str): 参数名称，用于错误消息

    Returns:
        UUID: 验证后的UUID对象

    Raises:
        HTTPException: UUID格式无效时返回422错误
    """
    try:
        from uuid import UUID
        return UUID(uuid_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": f"{parameter_name}格式无效",
                "message": f"{parameter_name}必须是36字符UUID格式，如：550e8400-e29b-41d4-a716-446655440000",
                "example": "550e8400-e29b-41d4-a716-446655440000"
            }
        )


@router.get("/profile",
            response_model=UnifiedResponse[UserProfileResponse],
            summary="获取用户信息",
            description="获取当前用户基本信息",
            responses={
                200: {
                    "description": "成功获取用户信息",
                    "content": {
                        "application/json": {
                            "example": {
                                "code": 200,
                                "data": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "nickname": "用户_550e8400",
                                    "avatar": None,
                                    "wechat_openid": "o6_bmjrPTlm6d2jXaA7m4",
                                    "is_guest": False,
                                    "created_at": "2024-01-01T10:00:00Z",
                                    "last_login_at": "2024-01-15T14:30:00Z"
                                },
                                "message": "success"
                            }
                        }
                    }
                },
                401: {"description": "未授权"},
                404: {"description": "用户不存在"},
                422: {
                    "description": "UUID格式无效",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": {
                                    "error": "user_id格式无效",
                                    "message": "user_id必须是36字符UUID格式，如：550e8400-e29b-41d4-a716-446655440000",
                                    "example": "550e8400-e29b-41d4-a716-446655440000"
                                }
                            }
                        }
                    }
                }
            })
async def get_user_profile(
    session: Annotated[Session, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[UserProfileResponse]:
    """
    获取当前用户基本信息

    JWT解析的user_id会自动转换为UUID对象，如果格式无效会返回422错误。
    """
    try:
        # 使用UserService获取用户资料
        result = user_service.get_user_profile(user_id)

        if result["success"]:
            return UnifiedResponse(
                code=200,
                data=result["data"],
                message=result["message"]
            )
        else:
            # 处理业务错误
            error_code = result.get("code", 500)
            if error_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )

    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.put("/profile",
            response_model=UnifiedResponse[UpdateProfileResponse],
            summary="更新用户信息",
            description="更新用户基本信息",
            responses={
                200: {"description": "更新成功"},
                401: {"description": "未授权"},
                404: {"description": "用户不存在"},
                422: {"description": "UUID格式无效"}
            })
async def update_user_profile(
    request: UpdateProfileRequest,
    session: Annotated[Session, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[UpdateProfileResponse]:
    """更新用户基本信息"""
    try:
        # 使用UserService更新用户资料
        result = user_service.update_user_profile(user_id, request)

        if result["success"]:
            return UnifiedResponse(
                code=200,
                data=result["data"],
                message=result["message"]
            )
        else:
            # 处理业务错误
            error_code = result.get("code", 500)
            if error_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )

    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败"
        )


@router.post("/welcome-gift/claim",
             response_model=UnifiedResponse[WelcomeGiftResponse],
             summary="领取欢迎礼包",
             description="领取用户欢迎礼包",
             responses={
                 200: {"description": "领取成功"},
                 401: {"description": "未授权"},
                 404: {"description": "用户不存在"},
                 422: {"description": "UUID格式无效"}
             })
async def claim_welcome_gift(
    session: Annotated[Session, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    points_service: Annotated[PointsService, Depends(get_points_service)],
    welcome_gift_service: Annotated[WelcomeGiftService, Depends(lambda s, ps: get_welcome_gift_service(s, ps))],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[WelcomeGiftResponse]:
    """
    领取用户欢迎礼包

    发放内容：
    - 1000积分
    - 积分加成卡x3（+50%积分，有效期1小时）
    - 专注道具x10（立即完成专注会话）
    - 时间管理券x5（延长任务截止时间1天）

    特性：
    - 可重复领取，无防刷限制
    - 完整流水记录
    - 事务性发放
    """
    try:
        # 使用UserService领取欢迎礼包
        result = user_service.claim_welcome_gift(user_id, points_service, welcome_gift_service)

        if result["success"]:
            return UnifiedResponse(
                code=200,
                data=result["data"],
                message=result["message"]
            )
        else:
            # 处理业务错误
            error_code = result.get("code", 500)
            if error_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )

    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        logger.error(f"领取欢迎礼包失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="领取欢迎礼包失败"
        )


@router.get("/welcome-gift/history",
            response_model=UnifiedResponse[WelcomeGiftHistoryResponse],
            summary="获取欢迎礼包历史",
            description="获取用户欢迎礼包领取历史",
            responses={
                200: {"description": "获取成功"},
                401: {"description": "未授权"},
                404: {"description": "用户不存在"},
                422: {"description": "UUID格式无效"}
            })
async def get_welcome_gift_history(
    session: Annotated[Session, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    points_service: Annotated[PointsService, Depends(get_points_service)],
    welcome_gift_service: Annotated[WelcomeGiftService, Depends(lambda s, ps: get_welcome_gift_service(s, ps))],
    user_id: UUID = Depends(get_current_user_id),
    limit: int = 10
) -> UnifiedResponse[WelcomeGiftHistoryResponse]:
    """
    获取用户欢迎礼包领取历史

    Args:
        user_id: 用户ID（从JWT解析，自动转换为UUID）
        limit: 返回记录数量限制，默认10条
    """
    try:
        # 使用UserService获取历史记录
        result = user_service.get_welcome_gift_history(user_id, points_service, welcome_gift_service, limit)

        if result["success"]:
            return UnifiedResponse(
                code=200,
                data=result["data"],
                message=result["message"]
            )
        else:
            # 处理业务错误
            error_code = result.get("code", 500)
            if error_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )

    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        logger.error(f"获取欢迎礼包历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取欢迎礼包历史失败"
        )