"""User领域API路由 - 简化版本

简化用户管理接口，删除欢迎礼包功能，合并重复接口。
使用主数据库连接，确保用户数据可以正确查询。
"""

import logging
from uuid import UUID
from typing import Dict, Any, Annotated
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from .schemas import (
    UserProfileResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
    EnhancedUserProfileResponse,
    EnhancedUpdateProfileRequest
)
from src.api.schemas import UnifiedResponse
from src.database import get_db_session
from src.api.dependencies import get_current_user_id
from src.domains.user.repository import UserRepository
from src.domains.user.models import User, UserSettings, UserStats
from src.services.rewards_integration_service import get_rewards_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["用户管理"])


# User领域服务层 - 使用Repository模式
# 所有类型转换都在Repository层处理，Service层只使用UUID对象


@router.get("/profile", summary="获取用户信息")
async def get_user_profile(
    business_session: Annotated[Session, Depends(get_db_session)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[EnhancedUserProfileResponse]:
    """
    获取当前用户信息

    包含完整的用户资料信息、偏好设置和积分余额。
    直接查询主数据库，确保用户数据可以正确获取。
    """
    try:
        # 直接查询用户数据
        user_stmt = select(User).where(User.user_id == user_id)
        user = business_session.exec(user_stmt).first()

        if not user:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 查询用户设置
        settings_stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        user_settings = business_session.exec(settings_stmt).first()

        # 查询用户统计
        stats_stmt = select(UserStats).where(UserStats.user_id == user_id)
        user_stats = business_session.exec(stats_stmt).first()

        # 获取积分余额（异步调用奖励服务）
        try:
            rewards_service = get_rewards_service()
            points_balance = await rewards_service.get_user_balance(str(user_id))
        except Exception as e:
            logger.warning(f"获取积分余额失败: {e}")
            points_balance = 0

        # 构造用户信息数据
        user_profile = EnhancedUserProfileResponse(
            # 基础字段
            id=str(user_id),
            nickname=user.nickname if user.nickname else f"用户_{str(user_id)[:8]}",
            avatar=user.avatar_url if user.avatar_url else None,
            bio=user.bio if user.bio else None,
            wechat_openid=None,  # 从JWT token获取
            is_guest=False,      # 从JWT token获取
            is_active=user.is_active if user else True,
            created_at=user.created_at.isoformat() if user and user.created_at else "2025-01-01T00:00:00Z",
            last_login_at=None,  # 从JWT token获取

            # 个人信息字段
            gender=user.gender if user.gender else None,
            birthday=user.birthday.isoformat() if user and user.birthday else None,

            # 偏好设置字段
            theme=user_settings.theme if user_settings else "light",
            language=user_settings.language if user_settings else "zh-CN",

            # 业务相关字段
            points_balance=points_balance,
            stats={
                "tasks_completed": user_stats.tasks_completed if user_stats else 0,
                "total_points": user_stats.total_points if user_stats else 0,
                "login_count": user_stats.login_count if user_stats else 0,
                "last_active_at": user_stats.last_active_at.isoformat() if user_stats and user_stats.last_active_at else None
            } if user_stats else None
        )

        logger.info(f"获取用户信息成功: user_id={user_id}, nickname={user_profile.nickname}")

        return UnifiedResponse(
            code=200,
            data=user_profile,
            message="success"
        )

    except Exception as e:
        logger.error(f"获取用户信息失败: user_id={user_id}, error={str(e)}")
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
        nickname = business_user.nickname if business_user else f"用户_{str(user_id)[:8]}"

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


@router.put("/profile/enhanced", summary="增强更新用户信息")
async def update_enhanced_user_profile(
    request: EnhancedUpdateProfileRequest,
    business_session: Annotated[Session, Depends(get_db_session)],
    user_id: UUID = Depends(get_current_user_id)
) -> UnifiedResponse[dict]:
    """
    更新用户增强信息

    支持更新基础用户信息、个人信息和偏好设置。
    包含事务性更新，确保数据一致性。
    """
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

        business_user = user_data["user"]

        # 准备更新数据
        user_updates = {}
        settings_updates = {}
        updated_fields = []

        # 处理基础用户信息字段
        if request.nickname:
            user_updates["nickname"] = request.nickname
            updated_fields.append("nickname")

        if request.avatar_url:
            user_updates["avatar_url"] = request.avatar_url
            updated_fields.append("avatar_url")

        if request.bio:
            user_updates["bio"] = request.bio
            updated_fields.append("bio")

        # 处理新增个人信息字段
        if request.gender:
            # 验证性别值
            valid_genders = ["male", "female", "other"]
            if request.gender not in valid_genders:
                return UnifiedResponse(
                    code=400,
                    data=None,
                    message=f"性别值无效，支持的值: {valid_genders}"
                )
            user_updates["gender"] = request.gender
            updated_fields.append("gender")

        if request.birthday:
            # 验证生日格式
            try:
                birthday = datetime.fromisoformat(request.birthday.replace('Z', '+00:00')).date()
                user_updates["birthday"] = birthday
                updated_fields.append("birthday")
            except ValueError:
                return UnifiedResponse(
                    code=400,
                    data=None,
                    message="生日格式无效，请使用ISO格式 (YYYY-MM-DD)"
                )

        # 处理偏好设置字段
        if request.theme:
            # 验证主题值
            valid_themes = ["light", "dark", "auto", "system"]
            if request.theme not in valid_themes:
                return UnifiedResponse(
                    code=400,
                    data=None,
                    message=f"主题值无效，支持的值: {valid_themes}"
                )
            settings_updates["theme"] = request.theme
            updated_fields.append("theme")

        if request.language:
            # 验证语言格式
            import re
            if not re.match(r'^[a-z]{2}-[A-Z]{2}$', request.language):
                return UnifiedResponse(
                    code=400,
                    data=None,
                    message="语言格式无效，请使用ISO格式 (例如: zh-CN, en-US)"
                )
            settings_updates["language"] = request.language
            updated_fields.append("language")

        # 开始事务性更新
        try:
            # 更新用户基础信息
            updated_user = None
            if user_updates:
                updated_user = user_repo.update_user(user_id, user_updates)

            # 更新或创建用户设置
            if settings_updates:
                from sqlmodel import select
                from src.domains.user.models import UserSettings

                # 查询现有设置
                settings_stmt = select(UserSettings).where(UserSettings.user_id == user_id)
                user_settings = business_session.exec(settings_stmt).first()

                if user_settings:
                    # 更新现有设置
                    for field, value in settings_updates.items():
                        setattr(user_settings, field, value)
                    user_settings.updated_at = datetime.utcnow()
                else:
                    # 创建新设置
                    user_settings = UserSettings(
                        user_id=user_id,
                        **settings_updates
                    )
                    business_session.add(user_settings)

            # 提交事务
            business_session.commit()

            # 获取更新后的用户信息
            final_user = updated_user or business_user

            # 构造更新响应数据
            update_response = {
                "id": str(user_id),
                "nickname": final_user.nickname if final_user else f"用户_{str(user_id)[:8]}",
                "avatar_url": final_user.avatar_url if final_user else None,
                "bio": final_user.bio if final_user else None,
                "gender": final_user.gender if final_user else None,
                "birthday": final_user.birthday.isoformat() if final_user and final_user.birthday else None,
                "theme": settings_updates.get("theme"),
                "language": settings_updates.get("language"),
                "updated_fields": updated_fields,
                "updated_at": datetime.utcnow().isoformat()
            }

            logger.info(f"用户增强信息更新成功: user_id={user_id}, fields={updated_fields}")

            return UnifiedResponse(
                code=200,
                data=update_response,
                message="更新成功"
            )

        except Exception as e:
            # 回滚事务
            business_session.rollback()
            raise e

    except Exception as e:
        logger.error(f"更新用户增强信息失败: user_id={user_id}, error={str(e)}")
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

    说明：
    JWT token已经验证了用户身份和有效性，无需数据库二次验证
    """
    try:

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

    说明：
    JWT token已经验证了用户身份和有效性，无需数据库二次验证
    """
    try:

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