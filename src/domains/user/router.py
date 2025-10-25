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
from src.api.dependencies import get_current_user_id
from src.domains.auth.models import Auth
from src.domains.auth.repository import AuthRepository
from src.domains.points.service import PointsService
from src.domains.reward.welcome_gift_service import WelcomeGiftService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["用户管理"])


# User领域服务层 - 使用Repository模式
# 所有类型转换都在Repository层处理，Service层只使用UUID对象


@router.get("/profile", summary="获取用户信息")
async def get_user_profile(
    session: Annotated[Session, Depends(get_db_session)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[UserProfileResponse]:
    """获取当前用户基本信息"""
    try:
        # 使用Repository层获取用户，Service层只处理UUID对象
        auth_repo = AuthRepository(session)
        user = auth_repo.get_by_id(user_id)

        if not user:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 构造用户信息数据（只使用Auth模型中存在的字段）
        user_profile = {
            "id": str(user.id),
            "nickname": f"用户_{user.id[:8]}",  # 生成默认昵称
            "avatar": None,  # Auth模型中没有avatar字段
            "wechat_openid": user.wechat_openid,
            "is_guest": user.is_guest,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
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
    session: Annotated[Session, Depends(get_db_session)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[UpdateProfileResponse]:
    """更新用户基本信息"""
    try:
        # 使用Repository层获取用户，Service层只处理UUID对象
        auth_repo = AuthRepository(session)
        user = auth_repo.get_by_id(user_id)

        if not user:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 注意：Auth模型中没有nickname字段，暂时返回默认昵称
        # 在未来的版本中可以考虑扩展Auth模型或创建独立的User模型
        updated_fields = []
        if request.nickname:
            # 暂时无法更新昵称，因为Auth模型中没有该字段
            # 这里可以记录日志或在未来版本中实现
            logger.info(f"User requested nickname update to '{request.nickname}', but Auth model doesn't support nickname field")
            updated_fields.append("nickname_requested")

        # 构造更新响应数据
        update_response = {
            "id": str(user.id),
            "nickname": f"用户_{user.id[:8]}",  # 返回默认昵称
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