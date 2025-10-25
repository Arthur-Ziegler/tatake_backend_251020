"""
User领域API路由 - 完全重构版本

彻底移除所有可能的泛型使用，确保API参数正确。
"""

import logging
from uuid import UUID
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from .schemas import UserProfileResponse, UpdateProfileRequest
from src.database import SessionDep
from src.api.dependencies import get_current_user_id
from src.domains.auth.models import Auth
from src.domains.points.service import PointsService
from src.domains.reward.welcome_gift_service import WelcomeGiftService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.get("/profile", summary="获取用户信息")
async def get_user_profile(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(SessionDep)
) -> Dict[str, Any]:
    """获取当前用户基本信息"""
    try:
        user = session.get(Auth, user_id)
        if not user:
            return {
                "code": 404,
                "data": None,
                "message": "用户不存在"
            }

        # 构造用户信息数据
        user_profile = {
            "id": str(user.id),
            "nickname": user.nickname,
            "avatar": user.avatar,
            "wechat_openid": user.wechat_openid,
            "is_guest": user.is_guest,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
        }

        return {
            "code": 200,
            "data": user_profile,
            "message": "success"
        }
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return {
            "code": 500,
            "data": None,
            "message": "获取用户信息失败"
        }


@router.put("/profile", summary="更新用户信息")
async def update_user_profile(
    request: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(SessionDep)
) -> Dict[str, Any]:
    """更新用户基本信息"""
    try:
        user = session.get(Auth, user_id)
        if not user:
            return {
                "code": 404,
                "data": None,
                "message": "用户不存在"
            }

        # 更新昵称
        updated_fields = []
        if request.nickname:
            user.nickname = request.nickname
            updated_fields.append("nickname")

        session.add(user)
        session.commit()
        session.refresh(user)

        # 构造更新响应数据
        update_response = {
            "id": str(user.id),
            "nickname": user.nickname,
            "updated_fields": updated_fields
        }

        return {
            "code": 200,
            "data": update_response,
            "message": "更新成功"
        }
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        return {
            "code": 500,
            "data": None,
            "message": "更新用户信息失败"
        }


@router.post("/welcome-gift/claim", summary="领取欢迎礼包")
async def claim_welcome_gift(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(SessionDep)
) -> Dict[str, Any]:
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
        # 初始化服务
        points_service = PointsService(session)
        welcome_gift_service = WelcomeGiftService(session, points_service)

        # 领取欢迎礼包
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

        return {
            "code": 200,
            "data": {
                "points_granted": result["points_granted"],
                "rewards_granted": rewards_granted,
                "transaction_group": result["transaction_group"],
                "granted_at": result["granted_at"]
            },
            "message": "success"
        }

    except Exception as e:
        logger.error(f"领取欢迎礼包失败: user_id={user_id}, error={str(e)}")
        return {
            "code": 500,
            "data": None,
            "message": f"领取欢迎礼包失败: {str(e)}"
        }


@router.get("/welcome-gift/history", summary="获取欢迎礼包历史")
async def get_welcome_gift_history(
    user_id: UUID = Depends(get_current_user_id),
    limit: int = 10,
    session: Session = Depends(SessionDep)
) -> Dict[str, Any]:
    """
    获取用户欢迎礼包领取历史

    Args:
        user_id: 用户ID
        limit: 返回记录数量限制，默认10条
    """
    try:
        # 初始化服务
        points_service = PointsService(session)
        welcome_gift_service = WelcomeGiftService(session, points_service)

        # 获取历史记录
        history = welcome_gift_service.get_user_gift_history(str(user_id), limit)

        # 构建响应数据
        history_items = [
            {
                "transaction_group": item["transaction_group"],
                "granted_at": item["granted_at"],
                "points_granted": item["points_granted"],
                "rewards_count": item["rewards_count"],
                "reward_items": item["reward_items"]
            }
            for item in history
        ]

        return {
            "code": 200,
            "data": {
                "history": history_items,
                "total_count": len(history_items)
            },
            "message": "success"
        }

    except Exception as e:
        logger.error(f"获取欢迎礼包历史失败: user_id={user_id}, error={str(e)}")
        return {
            "code": 500,
            "data": None,
            "message": f"获取欢迎礼包历史失败: {str(e)}"
        }