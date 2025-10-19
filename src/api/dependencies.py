"""
依赖注入模块

定义FastAPI的依赖注入函数，用于提供数据库连接、
服务实例等依赖项。
"""

from typing import Optional, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..services import (
    AuthService,
    UserService,
    TaskService,
    FocusService,
    RewardService,
    StatisticsService,
    ChatService
)
from ..repositories import (
    UserRepository,
    TaskRepository,
    FocusRepository,
    RewardRepository,
    ChatRepository
)
from .middleware.auth import verify_token
from .config import config


# HTTP Bearer认证方案
security = HTTPBearer()


# 数据库连接依赖
def get_database():
    """获取数据库连接"""
    # TODO: 实现数据库连接逻辑
    pass


# Redis连接依赖
def get_redis():
    """获取Redis连接"""
    # TODO: 实现Redis连接逻辑
    pass


# 用户认证依赖
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """获取当前用户信息"""
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("user_id")
        user_type = payload.get("user_type", "user")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的用户信息"
            )

        return {
            "user_id": user_id,
            "user_type": user_type,
            "token_exp": payload.get("exp")
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )


# 可选认证依赖
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """获取当前用户信息（可选）"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# 用户权限验证依赖
async def require_user_type(required_type: str):
    """要求特定用户类型的依赖"""
    async def dependency(current_user: dict = Depends(get_current_user)):
        if current_user["user_type"] != required_type:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要{required_type}权限"
            )
        return current_user

    return dependency


# Repository依赖
def get_user_repository() -> UserRepository:
    """获取用户Repository实例"""
    # TODO: 实现Repository创建逻辑
    pass


def get_task_repository() -> TaskRepository:
    """获取任务Repository实例"""
    # TODO: 实现Repository创建逻辑
    pass


def get_focus_repository() -> FocusRepository:
    """获取专注Repository实例"""
    # TODO: 实现Repository创建逻辑
    pass


def get_reward_repository() -> RewardRepository:
    """获取奖励Repository实例"""
    # TODO: 实现Repository创建逻辑
    pass


def get_chat_repository() -> ChatRepository:
    """获取对话Repository实例"""
    # TODO: 实现Repository创建逻辑
    pass


# Service依赖
def get_auth_service() -> AuthService:
    """获取认证Service实例"""
    # TODO: 实现Service创建逻辑
    user_repo = get_user_repository()
    return AuthService(user_repo)


def get_user_service() -> UserService:
    """获取用户Service实例"""
    # TODO: 实现Service创建逻辑
    user_repo = get_user_repository()
    return UserService(user_repo)


def get_task_service() -> TaskService:
    """获取任务Service实例"""
    # TODO: 实现Service创建逻辑
    user_repo = get_user_repository()
    task_repo = get_task_repository()
    return TaskService(user_repo, task_repo)


def get_focus_service() -> FocusService:
    """获取专注Service实例"""
    # TODO: 实现Service创建逻辑
    user_repo = get_user_repository()
    task_repo = get_task_repository()
    focus_repo = get_focus_repository()
    return FocusService(user_repo, task_repo, focus_repo)


def get_reward_service() -> RewardService:
    """获取奖励Service实例"""
    # TODO: 实现Service创建逻辑
    user_repo = get_user_repository()
    reward_repo = get_reward_repository()
    return RewardService(user_repo, reward_repo)


def get_statistics_service() -> StatisticsService:
    """获取统计Service实例"""
    # TODO: 实现Service创建逻辑
    user_repo = get_user_repository()
    task_repo = get_task_repository()
    focus_repo = get_focus_repository()
    reward_repo = get_reward_repository()
    return StatisticsService(user_repo, task_repo, focus_repo, reward_repo)


def get_chat_service() -> ChatService:
    """获取对话Service实例"""
    # TODO: 实现Service创建逻辑
    user_repo = get_user_repository()
    task_repo = get_task_repository()
    chat_repo = get_chat_repository()
    return ChatService(user_repo, task_repo, chat_repo)


# 分页依赖
def get_pagination_params(
    page: int = 1,
    limit: int = 20,
    max_limit: int = 100
) -> dict:
    """获取分页参数"""
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    if limit > max_limit:
        limit = max_limit

    offset = (page - 1) * limit

    return {
        "page": page,
        "limit": limit,
        "offset": offset
    }


# 搜索依赖
def get_search_params(
    q: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc"
) -> dict:
    """获取搜索参数"""
    if order not in ["asc", "desc"]:
        order = "desc"

    return {
        "query": q,
        "sort": sort,
        "order": order
    }


# 文件上传依赖
def get_file_upload_config():
    """获取文件上传配置"""
    return {
        "max_file_size": config.max_file_size,
        "allowed_file_types": config.allowed_file_types
    }