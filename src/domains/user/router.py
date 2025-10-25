"""User领域API路由"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlmodel import Session, select

from .schemas import (
    UserProfileResponse,
    UpdateProfileRequest,
    FeedbackRequest,
    UpdateProfileResponse,
    AvatarUploadResponse,
    FeedbackSubmitResponse,
    UnifiedResponse
)
from .database import get_user_session

from src.api.dependencies import get_current_user_id
from src.domains.auth.models import Auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.get("/profile", response_model=UnifiedResponse[UserProfileResponse], summary="获取用户信息")
async def get_user_profile(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
) -> UnifiedResponse[UserProfileResponse]:
    """获取当前用户基本信息"""
    try:
        user = session.get(Auth, user_id)
        if not user:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 构造用户信息数据模型
        user_profile = UserProfileResponse(
            id=str(user.id),
            nickname=user.nickname,
            avatar=user.avatar,
            wechat_openid=user.wechat_openid,
            is_guest=user.is_guest,
            created_at=user.created_at.isoformat(),
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None
        )

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


@router.put("/profile", response_model=UnifiedResponse[UpdateProfileResponse], summary="更新用户信息")
async def update_user_profile(
    request: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
) -> UnifiedResponse[UpdateProfileResponse]:
    """更新用户基本信息"""
    try:
        user = session.get(Auth, user_id)
        if not user:
            return UnifiedResponse(
                code=404,
                data=None,
                message="用户不存在"
            )

        # 更新昵称
        updated_fields = []
        if request.nickname:
            user.nickname = request.nickname
            updated_fields.append("nickname")

        session.add(user)
        session.commit()
        session.refresh(user)

        # 构造更新响应数据模型
        update_response = UpdateProfileResponse(
            id=str(user.id),
            nickname=user.nickname,
            updated_fields=updated_fields
        )

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


@router.post("/avatar", response_model=UnifiedResponse[AvatarUploadResponse], summary="上传用户头像")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
) -> UnifiedResponse[AvatarUploadResponse]:
    """
    上传用户头像

    注：当前为占位实现，实际需要集成OSS存储
    """
    try:
        # TODO: 实现文件上传到OSS
        # 当前返回占位URL
        avatar_url = f"https://example.com/avatars/{user_id}.jpg"

        user = session.get(Auth, user_id)
        if user:
            user.avatar = avatar_url
            session.add(user)
            session.commit()

        # 构造头像上传响应数据模型
        avatar_response = AvatarUploadResponse(
            avatar_url=avatar_url,
            message="头像上传成功（占位实现）"
        )

        return UnifiedResponse(
            code=200,
            data=avatar_response,
            message="success"
        )
    except Exception as e:
        logger.error(f"上传头像失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="上传头像失败"
        )


@router.post("/feedback", response_model=UnifiedResponse[FeedbackSubmitResponse], summary="提交用户反馈")
async def submit_feedback(
    request: FeedbackRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
) -> UnifiedResponse[FeedbackSubmitResponse]:
    """
    提交用户反馈

    注：当前为占位实现，实际需要存储到数据库
    """
    try:
        # TODO: 创建Feedback表并存储反馈
        logger.info(f"用户反馈: user_id={user_id}, type={request.type}, title={request.title}")

        # 构造反馈提交响应数据模型
        feedback_response = FeedbackSubmitResponse(
            feedback_id=str(user_id),  # 占位ID
            status="pending",
            message="反馈已提交，我们会尽快处理"
        )

        return UnifiedResponse(
            code=200,
            data=feedback_response,
            message="success"
        )
    except Exception as e:
        logger.error(f"提交反馈失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="提交反馈失败"
        )
