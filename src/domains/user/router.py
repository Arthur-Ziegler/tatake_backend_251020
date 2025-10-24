"""User领域API路由"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlmodel import Session, select

from .schemas import UserProfileResponse, UpdateProfileRequest, FeedbackRequest
from .database import get_user_session

from src.api.dependencies import get_current_user_id
from src.domains.auth.models import Auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.get("/profile", response_model=dict, summary="获取用户信息")
async def get_user_profile(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
):
    """获取当前用户基本信息"""
    try:
        user = session.get(Auth, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return {
            "code": 200,
            "data": {
                "id": str(user.id),
                "nickname": user.nickname,
                "avatar": user.avatar,
                "wechat_openid": user.wechat_openid,
                "is_guest": user.is_guest,
                "created_at": user.created_at.isoformat(),
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            },
            "message": "success"
        }
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户信息失败")


@router.put("/profile", response_model=dict, summary="更新用户信息")
async def update_user_profile(
    request: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
):
    """更新用户基本信息"""
    try:
        user = session.get(Auth, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 更新昵称
        if request.nickname:
            user.nickname = request.nickname

        session.add(user)
        session.commit()
        session.refresh(user)

        return {
            "code": 200,
            "data": {
                "id": str(user.id),
                "nickname": user.nickname,
                "updated_fields": ["nickname"] if request.nickname else []
            },
            "message": "更新成功"
        }
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(status_code=500, detail="更新用户信息失败")


@router.post("/avatar", response_model=dict, summary="上传用户头像")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
):
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

        return {
            "code": 200,
            "data": {
                "avatar_url": avatar_url,
                "message": "头像上传成功（占位实现）"
            },
            "message": "success"
        }
    except Exception as e:
        logger.error(f"上传头像失败: {e}")
        raise HTTPException(status_code=500, detail="上传头像失败")


@router.post("/feedback", response_model=dict, summary="提交用户反馈")
async def submit_feedback(
    request: FeedbackRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_user_session)
):
    """
    提交用户反馈

    注：当前为占位实现，实际需要存储到数据库
    """
    try:
        # TODO: 创建Feedback表并存储反馈
        logger.info(f"用户反馈: user_id={user_id}, type={request.type}, title={request.title}")

        return {
            "code": 200,
            "data": {
                "feedback_id": str(user_id),  # 占位ID
                "status": "pending",
                "message": "反馈已提交，我们会尽快处理"
            },
            "message": "success"
        }
    except Exception as e:
        logger.error(f"提交反馈失败: {e}")
        raise HTTPException(status_code=500, detail="提交反馈失败")
