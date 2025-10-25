"""
Top3系统API路由器

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
from src.domains.auth.schemas import UnifiedResponse

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
        service = Top3Service(session)
        result = service.set_top3(UUID(user_id), request)

        # 转换为v3文档格式，处理两种数据格式
        top3_tasks = []
        for idx, task_info in enumerate(result.task_ids):
            if isinstance(task_info, dict):
                # 新格式：{"task_id": "uuid", "position": 1}
                top3_tasks.append({
                    "position": task_info.get("position", idx + 1),
                    "task_id": task_info["task_id"]
                })
            else:
                # 旧格式：直接是task_id字符串
                top3_tasks.append({
                    "position": idx + 1,
                    "task_id": task_info
                })

        response_data = {
            "date": result.date,
            "top3_tasks": top3_tasks,
            "points_consumed": result.points_consumed,
            "remaining_balance": 0  # TODO: 需要从积分服务获取实际余额
        }

        return UnifiedResponse(
            code=200,
            data=response_data,
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
        service = Top3Service(session)
        result = service.get_top3(str(user_id), target_date)

        # 转换为v3文档格式，处理两种数据格式
        top3_tasks = []
        for idx, task_info in enumerate(result.task_ids):
            if isinstance(task_info, dict):
                # 新格式：{"task_id": "uuid", "position": 1}
                top3_tasks.append({
                    "position": task_info.get("position", idx + 1),
                    "task_id": task_info["task_id"]
                })
            else:
                # 旧格式：直接是task_id字符串
                top3_tasks.append({
                    "position": idx + 1,
                    "task_id": task_info
                })

        response_data = {
            "date": result.date,
            "top3_tasks": top3_tasks
        }

        return UnifiedResponse(
            code=200,
            data=response_data,
            message="获取Top3成功"
        )
    except Exception as e:
        logger.error(f"获取Top3失败: {e}")
        return UnifiedResponse(
            code=500,
            data=None,
            message="获取Top3失败"
        )