"""Top3系统API路由器

实现v3文档中定义的Top3系统API，包括：
- 设置Top3任务
- 查询Top3任务

使用统一的响应格式，支持300积分消耗机制。
"""

import logging
from datetime import date
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session

from .service import Top3Service
from .schemas import SetTop3Request, Top3Response, GetTop3Response
from src.database import SessionDep
from src.api.dependencies import get_current_user_id
from src.api.schemas import UnifiedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks/special", tags=["Top3管理"])


@router.post("/top3", response_model=UnifiedResponse[Top3Response], summary="设置Top3任务")
async def set_top3(
    request: SetTop3Request,
    session: SessionDep,
    user_id: str = Depends(get_current_user_id)
) -> UnifiedResponse[Top3Response]:
    """
    设置每日Top3重要任务

    业务规则：
    - 消耗300积分
    - 每天只能设置一次
    - 支持1-3个任务
    - 需要包含位置信息

    Args:
        request: Top3设置请求
        user_id: 用户ID（暂时使用默认值）
        session: 数据库会话
    """
    try:
        # 修复UUID类型问题 - service层期望字符串UUID
        from src.domains.points.service import PointsService
        points_service = PointsService(session)
        service = Top3Service(session, points_service)
        result_dict = service.set_top3(user_id, request)  # service返回完整字典

        # 直接使用service返回的数据，不做任何转换
        return UnifiedResponse(
            code=200,
            data=result_dict,  # 直接使用service返回的字典
            message="Top3设置成功"
        )
    except Exception as e:
        logger.error(f"设置Top3失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="设置Top3失败"
        )


@router.get("/top3/{target_date}", response_model=UnifiedResponse[GetTop3Response], summary="查看指定日期Top3")
async def get_top3(
    target_date: str,
    session: SessionDep,
    user_id: str = Depends(get_current_user_id)
) -> UnifiedResponse[GetTop3Response]:
    """
    查看指定日期的Top3任务

    Args:
        target_date: 日期字符串，格式YYYY-MM-DD
        user_id: 用户ID（暂时使用默认值）
        session: 数据库会话
    """
    try:
        # 修复UUID类型问题 - service层期望字符串UUID
        from src.domains.points.service import PointsService
        points_service = PointsService(session)
        service = Top3Service(session, points_service)
        result_dict = service.get_top3(user_id, target_date)  # service返回完整字典

        # 直接使用service返回的数据，不做任何转换
        return UnifiedResponse(
            code=200,
            data=result_dict,  # 直接使用service返回的字典
            message="获取Top3成功"
        )
    except Exception as e:
        logger.error(f"获取Top3失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="获取Top3失败"
        )