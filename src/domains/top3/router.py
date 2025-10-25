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

from src.api.dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks/special/top3", tags=["Top3管理"])


@router.post("", response_model=dict, summary="设置Top3任务")
async def set_top3(
    request: SetTop3Request,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_top3_session)
):
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
        result = service.set_top3(user_id, request)
        return {
            "code": 200,
            "data": result.model_dump(),
            "message": "Top3设置成功"
        }
    except Top3Exception as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error(f"设置Top3失败: {e}")
        raise HTTPException(status_code=500, detail="设置Top3失败")


@router.get("/{date}", response_model=dict, summary="获取Top3任务")
async def get_top3(
    date: str,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_top3_session)
):
    """获取指定日期的Top3任务"""
    try:
        points_service = PointsService(session)
        service = Top3Service(session, points_service)
        result = service.get_top3(user_id, date)
        return {
            "code": 200,
            "data": result.model_dump(),
            "message": "success"
        }
    except Top3Exception as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error(f"获取Top3失败: {e}")
        raise HTTPException(status_code=500, detail="获取Top3失败")
