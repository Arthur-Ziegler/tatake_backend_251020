"""User领域API路由 - 修复版本

修复依赖解析问题，使用正确的Annotated类型注解。
添加UUID到字符串的类型转换，确保SQLite兼容性。
"""

import logging
from uuid import UUID
from typing import Dict, Any, Annotated

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

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
from src.domains.auth.database import get_auth_db
from src.api.dependencies import get_current_user_id
from src.domains.auth.models import Auth
from src.domains.auth.repository import AuthRepository
from src.domains.user.repository import UserRepository
from src.domains.user.models import User, UserSettings, UserStats
from src.domains.points.service import PointsService
from src.domains.reward.welcome_gift_service import WelcomeGiftService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["用户管理"])


# User领域服务层 - 使用Repository模式
# 所有类型转换都在Repository层处理，Service层只使用UUID对象


@router.get("/profile", summary="获取用户信息")
async def get_user_profile(
    business_session: Annotated[Session, Depends(get_db_session)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[UserProfileResponse]:
    """获取当前用户基本信息"""
    try:
        # 使用UserRepository获取完整的用户信息（跨域查询）
        user_repo = UserRepository(business_session)
        user_data = user_repo.get_by_id_with_auth(user_id)

        if not user_data:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        auth_user = user_data["auth"]
        business_user = user_data["user"]
        stats = user_data["stats"]

        # 如果业务用户不存在，创建一个
        if not business_user:
            business_user = user_repo.create_user(user_id)

        # 构造用户信息数据（结合认证域和用户域的数据）
        user_profile = {
            "id": str(auth_user.id),
            "nickname": business_user.nickname if business_user else f"用户_{auth_user.id[:8]}",
            "avatar": business_user.avatar_url if business_user else None,
            "bio": business_user.bio if business_user else None,
            "wechat_openid": auth_user.wechat_openid,
            "is_guest": auth_user.is_guest,
            "created_at": auth_user.created_at.isoformat(),
            "last_login_at": auth_user.last_login_at.isoformat() if auth_user.last_login_at else None
        }

        return UnifiedResponse(
            code=200,
            data=user_profile,
            message="success"
        )
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="获取用户信息失败"
        )


@router.put("/profile", summary="更新用户信息")
async def update_user_profile(
    request: UpdateProfileRequest,
    business_session: Annotated[Session, Depends(get_db_session)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[UpdateProfileResponse]:
    """更新用户基本信息"""
    try:
        # 使用UserRepository进行用户数据更新
        user_repo = UserRepository(business_session)

        # 验证用户存在
        user_data = user_repo.get_by_id_with_auth(user_id)
        if not user_data or not user_data["auth"]:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 准备更新数据
        updates = {}
        updated_fields = []

        if request.nickname:
            updates["nickname"] = request.nickname
            updated_fields.append("nickname")

        if request.avatar_url:
            updates["avatar_url"] = request.avatar_url
            updated_fields.append("avatar_url")

        if request.bio:
            updates["bio"] = request.bio
            updated_fields.append("bio")

        # 执行更新（如果有需要更新的字段）
        updated_user = None
        if updates:
            updated_user = user_repo.update_user(user_id, updates)

        # 获取更新后的用户信息
        business_user = updated_user or user_data["user"]
        nickname = business_user.nickname if business_user else f"用户_{user_id[:8]}"

        # 构造更新响应数据
        update_response = {
            "id": str(user_id),
            "nickname": nickname,
            "avatar_url": business_user.avatar_url if business_user else None,
            "bio": business_user.bio if business_user else None,
            "updated_fields": updated_fields
        }

        return UnifiedResponse(
            code=200,
            data=update_response,
            message="更新成功"
        )
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="更新用户信息失败"
        )


@router.post("/welcome-gift/claim", summary="领取欢迎礼包")
async def claim_welcome_gift(
    session: Annotated[Session, Depends(get_db_session)],
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
        # 验证用户存在（使用Repository层）
        auth_repo = AuthRepository(session)
        user = auth_repo.get_by_id(user_id)

        if not user:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 初始化服务
        points_service = PointsService(session)
        welcome_gift_service = WelcomeGiftService(session, points_service)

        # 领取欢迎礼包（Repository层会处理UUID转换）
        result = welcome_gift_service.claim_welcome_gift(str(user_id))

        # 构建响应数据
        rewards_granted = [
            {
                "name": reward["name"],
                "quantity": reward["quantity"],
                "description": reward["description"]
            }
            for reward in result["rewards_granted"]
        ]

        welcome_gift_response = WelcomeGiftResponse(
            points_granted=result["points_granted"],
            rewards_granted=rewards_granted,
            transaction_group=result["transaction_group"],
            granted_at=result["granted_at"]
        )

        return UnifiedResponse(
            code=200,
            data=welcome_gift_response,
            message="success"
        )

    except Exception as e:
        logger.error(f"领取欢迎礼包失败: user_id={user_id}, error={str(e)}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"领取欢迎礼包失败: {str(e)}"
        )


@router.get("/welcome-gift/history", response_model=UnifiedResponse[WelcomeGiftHistoryResponse], summary="获取欢迎礼包历史")
async def get_welcome_gift_history(
    session: Annotated[Session, Depends(get_db_session)],
    user_id: UUID = Depends(get_current_user_id),
    limit: int = 10
) -> UnifiedResponse[WelcomeGiftHistoryResponse]:
    """
    获取用户欢迎礼包领取历史

    Args:
        user_id: 用户ID
        limit: 返回记录数量限制，默认10条
    """
    try:
        # 验证用户存在（使用Repository层）
        auth_repo = AuthRepository(session)
        user = auth_repo.get_by_id(user_id)

        if not user:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 初始化服务
        points_service = PointsService(session)
        welcome_gift_service = WelcomeGiftService(session, points_service)

        # 获取历史记录（Repository层会处理UUID转换）
        history = welcome_gift_service.get_user_gift_history(str(user_id), limit)

        # 构建响应数据
        history_items = [
            WelcomeGiftHistoryItem(
                transaction_group=item["transaction_group"],
                granted_at=item["granted_at"],
                points_granted=item["points_granted"],
                rewards_count=item["rewards_count"],
                reward_items=item["reward_items"]
            )
            for item in history
        ]

        history_response = WelcomeGiftHistoryResponse(
            history=history_items,
            total_count=len(history_items)
        )

        return UnifiedResponse(
            code=200,
            data=history_response,
            message="success"
        )

    except Exception as e:
        logger.error(f"获取欢迎礼包历史失败: user_id={user_id}, error={str(e)}")
        return UnifiedResponse(
            code=500,
            data=None,
            message=f"获取欢迎礼包历史失败: {str(e)}"
        )