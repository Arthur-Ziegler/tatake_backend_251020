"""Top3领域API路由"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session

from .service import Top3Service
from src.domains.points.service import PointsService
from .schemas import SetTop3Request, Top3Response, GetTop3Response
from .exceptions import Top3Exception
from .database import get_top3_session
from src.domains.auth.schemas import UnifiedResponse

from src.api.dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks/special/top3", tags=["Top3管理"])


@router.post("", response_model=UnifiedResponse[Top3Response], summary="设置Top3任务")
async def set_top3(
    request: SetTop3Request,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_top3_session)
) -> UnifiedResponse[Top3Response]:
    """
    设置每日Top3重要任务

    规则：
    - 消耗300积分
    - 每天只能设置一次
    - 1-3个任务
    - 只有Top3任务完成才能抽奖
    """
    try:
        points_service = PointsService(session)
        service = Top3Service(session, points_service)
        result_dict = service.set_top3(user_id, request)

        # 构造Top3Response数据模型
        top3_response = Top3Response(**result_dict)

        return UnifiedResponse[Top3Response](
            code=200,
            data=top3_response,
            message="success"
        )
    except Top3Exception as e:
        return UnifiedResponse[Top3Response](
            code=e.status_code,
            data=None,
            message=e.detail
        )
    except Exception as e:
        logger.error(f"设置Top3失败: {e}")
        return UnifiedResponse[Top3Response](
            code=500,
            data=None,
            message="设置Top3失败"
        )


@router.get("/{date}", response_model=UnifiedResponse[GetTop3Response], summary="获取Top3任务")
async def get_top3(
    date: str,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_top3_session)
) -> UnifiedResponse[GetTop3Response]:
    """获取指定日期的Top3任务"""
    try:
        points_service = PointsService(session)
        service = Top3Service(session, points_service)
        result_dict = service.get_top3(user_id, date)

        # 构造GetTop3Response数据模型
        get_top3_response = GetTop3Response(**result_dict)

        return UnifiedResponse[GetTop3Response](
            code=200,
            data=get_top3_response,
            message="success"
        )
    except Top3Exception as e:
        return UnifiedResponse[GetTop3Response](
            code=e.status_code,
            data=None,
            message=e.detail
        )
    except Exception as e:
        logger.error(f"获取Top3失败: {e}")
        return UnifiedResponse[GetTop3Response](
            code=500,
            data=None,
            message="获取Top3失败"
        )
