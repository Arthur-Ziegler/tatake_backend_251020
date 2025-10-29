"""
认证API依赖注入系统

使用微服务JWT token验证机制，确保所有API都有正确的用户认证。
"""

import os
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from src.services.auth.jwt_validator import validate_jwt_token

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    从JWT令牌中获取当前用户ID

    使用微服务JWT验证器进行令牌验证。
    用于需要认证的端点。
    如果令牌无效，抛出HTTPException。
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # 使用微服务JWT验证器验证令牌
        payload = await validate_jwt_token(credentials.credentials)

        # 验证令牌类型
        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌类型错误"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌中缺少用户ID"
            )

        return UUID(user_id)

    except HTTPException:
        # 重新抛出HTTPException
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user_id_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UUID]:
    """
    可选的用户认证依赖

    如果提供了有效token则返回用户ID，否则返回None。
    用于某些场景下可选认证的端点。
    """
    if not credentials:
        return None

    try:
        # 使用微服务JWT验证器验证令牌
        payload = await validate_jwt_token(credentials.credentials)

        # 验证令牌类型
        if payload.get("token_type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        return UUID(user_id)

    except Exception:
        # 任何验证错误都返回None，而不是抛出异常
        return None


# 可选认证依赖
async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict | None:
    """获取当前用户信息（可选）"""
    if not credentials:
        return None

    try:
        return await get_current_user_id(credentials)
    except HTTPException:
        return None


# 用户权限验证依赖
# TODO: 修复权限验证逻辑，当前current_user是UUID不是dict
# async def require_user_type(required_type: str):
#     """要求特定用户类型的依赖工厂函数"""
#     async def dependency(current_user: UUID = Depends(get_current_user_id)):
#         if current_user["user_type"] != required_type:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail=f"需要{required_type}权限"
#             )
#         return current_user
#     return dependency


# 分页依赖
def get_pagination_params(
    page: int = 1,
    limit: int = 20,
    max_limit: int = 100
) -> dict:
    """获取分页参数的FastAPI依赖"""
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
    q: str | None = None,
    sort: str = "created_at",
    order: str = "desc"
) -> dict:
    """获取搜索参数的FastAPI依赖"""
    if order not in ["asc", "desc"]:
        order = "desc"

    return {
        "query": q,
        "sort": sort,
        "order": order
    }


# 初始化和清理函数（简化版本）
async def initialize_dependencies():
    """初始化依赖注入系统（简化版本）"""
    # 暂时不需要初始化任何东西
    pass


async def cleanup_dependencies():
    """清理依赖注入系统（简化版本）"""
    # 暂时不需要清理任何东西
    pass