"""
用户管理API路由

处理用户个人资料管理相关请求，包括资料查看、更新、头像上传、反馈等功能。
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer

from ..dependencies import get_current_user, get_user_service
from ..schemas import (
    UserInfoResponse,
    UserProfileUpdateRequest,
    UserAvatarResponse,
    UserFeedbackRequest,
    BaseResponse
)
from ..responses import create_success_response, create_error_response
from ..config import config

# 创建路由器
router = APIRouter(prefix="/user", tags=["用户管理"])

# HTTP Bearer认证方案
security = HTTPBearer()


@router.get("/profile", response_model=UserInfoResponse)
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    user_service = Depends(get_user_service)
):
    """
    获取用户个人资料

    根据当前用户的认证令牌返回详细的个人资料信息。

    Args:
        current_user: 当前用户信息
        user_service: 用户服务实例

    Returns:
        UserInfoResponse: 用户详细资料

    Raises:
        HTTPException: 当用户不存在或令牌无效时
    """
    try:
        # 使用用户服务获取用户资料
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # TODO: 实现用户服务获取资料方法
        # user_profile = user_service.get_user_profile(user_id)

        # 临时模拟数据
        user_profile = {
            "user_id": user_id,
            "user_type": current_user.get("user_type", "registered"),
            "is_guest": current_user.get("is_guest", False),
            "phone": None,
            "email": None,
            "display_name": None,
            "avatar_url": None,
            "bio": None,
            "preferences": {
                "theme": "light",
                "language": "zh-CN",
                "notifications": True
            },
            "statistics": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "total_focus_time": 0,
                "current_streak": 0
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow()
        }

        return create_success_response(
            data=UserInfoResponse(**user_profile),
            message="获取用户资料成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[UserProfile] 获取用户资料失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户资料失败: {str(e)}"
        )


@router.put("/profile", response_model=UserInfoResponse)
async def update_user_profile(
    request: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    user_service = Depends(get_user_service)
):
    """
    更新用户个人资料

    更新用户的基本信息，包括昵称、邮箱、个人简介等。

    Args:
        request: 用户资料更新请求
        current_user: 当前用户信息
        user_service: 用户服务实例

    Returns:
        UserInfoResponse: 更新后的用户详细资料

    Raises:
        HTTPException: 当用户不存在、验证失败或更新失败时
    """
    try:
        # 验证当前用户
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # 验证游客账号限制
        if current_user.get("is_guest"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="游客账号无法修改资料"
            )

        # TODO: 实现用户服务更新资料方法
        # updated_profile = user_service.update_user_profile(user_id, request.dict())

        # 临时模拟更新
        updated_profile = {
            "user_id": user_id,
            "user_type": current_user.get("user_type", "registered"),
            "is_guest": False,
            "phone": request.phone,
            "email": request.email,
            "display_name": request.display_name,
            "avatar_url": request.avatar_url,
            "bio": request.bio,
            "preferences": request.preferences or {
                "theme": "light",
                "language": "zh-CN",
                "notifications": True
            },
            "statistics": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "total_focus_time": 0,
                "current_streak": 0
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow()
        }

        return create_success_response(
            data=UserInfoResponse(**updated_profile),
            message="用户资料更新成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[UserProfile] 更新用户资料失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户资料失败: {str(e)}"
        )


@router.post("/avatar/upload", response_model=UserAvatarResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    user_service = Depends(get_user_service)
):
    """
    上传用户头像

    上传并设置用户头像图片。

    Args:
        file: 头像图片文件
        current_user: 当前用户信息
        user_service: 用户服务实例

    Returns:
        UserAvatarResponse: 头像上传结果

    Raises:
        HTTPException: 当文件格式错误、上传失败或用户不存在时
    """
    try:
        # 验证当前用户
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # 验证游客账号限制
        if current_user.get("is_guest"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="游客账号无法上传头像"
            )

        # 验证文件格式
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能上传图片文件"
            )

        # 验证文件大小（限制为5MB）
        if file.size and file.size > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图片文件大小不能超过5MB"
            )

        # TODO: 实现真实的文件上传逻辑
        # avatar_url = await user_service.upload_avatar(user_id, file)

        # 临时模拟上传
        file_extension = file.filename.split('.')[-1] if file.filename else 'jpg'
        avatar_filename = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        avatar_url = f"/static/avatars/{avatar_filename}"

        return create_success_response(
            data=UserAvatarResponse(
                avatar_url=avatar_url,
                filename=file.filename,
                size=file.size,
                content_type=file.content_type,
                uploaded_at=datetime.utcnow()
            ),
            message="头像上传成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[UserAvatar] 上传用户头像失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像上传失败: {str(e)}"
        )


@router.delete("/avatar", response_model=BaseResponse)
async def delete_user_avatar(
    current_user: dict = Depends(get_current_user),
    user_service = Depends(get_user_service)
):
    """
    删除用户头像

    删除用户当前的头像，恢复为默认头像。

    Args:
        current_user: 当前用户信息
        user_service: 用户服务实例

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当用户不存在或删除失败时
    """
    try:
        # 验证当前用户
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # 验证游客账号限制
        if current_user.get("is_guest"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="游客账号无法删除头像"
            )

        # TODO: 实现用户服务删除头像方法
        # await user_service.delete_avatar(user_id)

        return create_success_response(
            message="头像删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[UserAvatar] 删除用户头像失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像删除失败: {str(e)}"
        )


@router.post("/feedback", response_model=BaseResponse)
async def submit_user_feedback(
    request: UserFeedbackRequest,
    current_user: dict = Depends(get_current_user),
    user_service = Depends(get_user_service)
):
    """
    提交用户反馈

    用户提交意见反馈或bug报告。

    Args:
        request: 用户反馈请求
        current_user: 当前用户信息
        user_service: 用户服务实例

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当反馈提交失败时
    """
    try:
        # 验证当前用户
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # 验证反馈内容
        if not request.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="反馈内容不能为空"
            )

        if len(request.content) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="反馈内容不能超过2000个字符"
            )

        # TODO: 实现用户服务提交反馈方法
        # feedback_id = await user_service.submit_feedback(user_id, request.dict())

        feedback_id = str(uuid.uuid4())

        return create_success_response(
            message="反馈提交成功，感谢您的宝贵意见",
            data={
                "feedback_id": feedback_id,
                "feedback_type": request.feedback_type,
                "submitted_at": datetime.utcnow().isoformat()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[UserFeedback] 提交用户反馈失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"反馈提交失败: {str(e)}"
        )


@router.delete("/account", response_model=BaseResponse)
async def delete_user_account(
    current_user: dict = Depends(get_current_user),
    user_service = Depends(get_user_service)
):
    """
    删除用户账号

    永久删除用户账号及其所有相关数据。此操作不可逆。

    Args:
        current_user: 当前用户信息
        user_service: 用户服务实例

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当用户不存在或删除失败时
    """
    try:
        # 验证当前用户
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID无效"
            )

        # 验证游客账号
        if current_user.get("is_guest"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="游客账号无法删除"
            )

        # TODO: 实现用户服务删除账号方法
        # await user_service.delete_user_account(user_id)

        return create_success_response(
            message="账号删除成功，您的所有数据已被永久删除"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[UserAccount] 删除用户账号失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"账号删除失败: {str(e)}"
        )