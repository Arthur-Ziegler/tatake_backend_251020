"""
API通用Schema定义

提供所有领域模块共用的Schema定义，包括统一响应格式等。
"""

from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel, Field

# ===== 统一响应格式 =====

T = TypeVar('T')

class UnifiedResponse(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")