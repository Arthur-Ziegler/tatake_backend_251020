"""Top3领域API路由 - 微服务代理模式

将Top3管理功能代理到Task微服务(localhost:20252)，
保持API路径、响应格式、认证方式完全不变。

替换的端点（2个）：
1. POST /tasks/special/top3 → 直接代理设置（免费）
2. GET /tasks/special/top3/{date} → 代理查询

设计原则：
1. 代理模式：保持API路径完全不变
2. 免费设置：Top3设置不消耗积分
3. 简化流程：直接代理到微服务
4. 格式转换：微服务格式 → 本地格式

作者：TaKeKe团队
版本：2.0.0（微服务代理 - 免费版本）
"""

import logging
from uuid import UUID
from datetime import date

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlmodel import Session

from src.core.uuid_converter import UUIDConverter

# 导入微服务客户端
from src.services.task_microservice_client import call_task_service, TaskMicroserviceError
from .schemas import SetTop3Request, Top3Response, GetTop3Response
from .exceptions import Top3Exception
from .database import get_top3_session
from src.api.schemas import UnifiedResponse

from src.api.dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks/special/top3", tags=["Top3管理"])


def validate_date_parameter(date_str: str) -> str:
    """
    验证日期参数格式

    Args:
        date_str (str): 日期字符串

    Returns:
        str: 验证通过的日期字符串

    Raises:
        HTTPException: 日期格式无效时抛出400错误
    """
    try:
        date.fromisoformat(date_str)
        return date_str
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="日期格式无效，请使用YYYY-MM-DD格式"
        )




@router.post(
    "",
    response_model=UnifiedResponse[Top3Response],
    summary="设置Top3任务",
    description="""
    设置每日Top3重要任务，免费设置。

    **业务规则：**
    - 每天只能设置一次Top3任务
    - 必须选择1-3个任务
    - 免费设置，不消耗积分
    - 只有完成Top3任务才能参与抽奖

    **请求参数：**
    - date: 目标日期，格式为YYYY-MM-DD
    - task_ids: 任务ID列表，必须是有效的UUID格式，长度为1-3个

    **响应：**
    - 成功时返回Top3设置详情
    - 失败时返回相应的错误信息
    """,
    responses={
        200: {
            "description": "设置成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": {
                            "date": "2025-01-15",
                            "task_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                            "points_consumed": 0,
                            "remaining_balance": None
                        },
                        "message": "success"
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "data": None,
                        "message": "无效的UUID格式: invalid-uuid"
                    }
                }
            }
        },
        409: {
            "description": "当天已设置Top3",
            "content": {
                "application/json": {
                    "example": {
                        "code": 409,
                        "data": None,
                        "message": "该日期已设置Top3任务"
                    }
                }
            }
        }
    }
)
async def set_top3(
    request: SetTop3Request,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_top3_session)
) -> UnifiedResponse[Top3Response]:
    """
    设置Top3任务 - 微服务代理（免费）

    业务流程：
    1. 直接调用微服务设置Top3
    2. 返回设置结果
    """
    try:
        logger.info(f"设置Top3 API调用(微服务代理): user_id={user_id}, date={request.date}")

        # 直接调用微服务设置Top3
        try:
            # 适配请求数据给微服务
            request_dict = request.model_dump()

            microservice_response = await call_task_service(
                method="POST",
                path="tasks/special/top3",
                user_id=str(user_id),
                data=request_dict
            )

            # 检查微服务调用结果
            if microservice_response["code"] != 200:
                return UnifiedResponse[Top3Response](
                    code=microservice_response["code"],
                    data=None,
                    message=microservice_response["message"]
                )

            # 构造响应数据（免费设置）
            top3_data = microservice_response["data"]
            top3_response = Top3Response(
                date=top3_data.get("date", request.date),
                task_ids=top3_data.get("task_ids", request.task_ids),
                points_consumed=0,
                remaining_balance=None
            )

            return UnifiedResponse[Top3Response](
                code=200,
                data=top3_response,
                message="success"
            )

        except TaskMicroserviceError as e:
            logger.error(f"微服务调用失败: {e}")
            return UnifiedResponse[Top3Response](
                code=e.status_code,
                data=None,
                message=e.message
            )

    except Exception as e:
        logger.error(f"设置Top3异常: {e}")
        return UnifiedResponse[Top3Response](
            code=500,
            data=None,
            message="设置Top3失败"
        )


@router.get(
    "/{date}",
    response_model=UnifiedResponse[GetTop3Response],
    summary="获取Top3任务",
    description="""
    获取用户指定日期的Top3任务列表。

    **功能说明：**
    - 返回指定日期设置的Top3任务
    - 如果当天未设置Top3，返回空列表
    - 显示消耗的积分和设置时间

    **路径参数：**
    - date: 查询日期，格式为YYYY-MM-DD

    **响应：**
    - 成功时返回Top3任务详情
    - 包含任务ID列表、消耗积分、创建时间等信息
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "data": {
                            "date": "2025-01-15",
                            "task_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                            "points_consumed": 0,
                            "created_at": "2025-01-15T10:30:00Z"
                        },
                        "message": "success"
                    }
                }
            }
        },
        400: {
            "description": "日期格式错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "data": None,
                        "message": "日期格式无效，请使用YYYY-MM-DD格式"
                    }
                }
            }
        }
    }
)
async def get_top3(
    date: str = Depends(validate_date_parameter),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_top3_session)
) -> UnifiedResponse[GetTop3Response]:
    """
    获取指定日期的Top3任务 - 微服务代理

    通过微服务代理获取Top3任务信息。
    """
    try:
        logger.info(f"获取Top3 API调用(微服务代理): user_id={user_id}, date={date}")

        # 调用微服务
        microservice_response = await call_task_service(
            method="GET",
            path=f"tasks/special/top3/{date}",
            user_id=str(user_id)
        )

        # 检查微服务调用结果
        if microservice_response["code"] != 200:
            return UnifiedResponse[GetTop3Response](
                code=microservice_response["code"],
                data=None,
                message=microservice_response["message"]
            )

        # 构造响应数据
        top3_data = microservice_response["data"]
        get_top3_response = GetTop3Response(
            date=top3_data.get("date", date),
            task_ids=top3_data.get("task_ids", []),
            points_consumed=0,  # 免费设置
            created_at=top3_data.get("created_at")
        )

        return UnifiedResponse[GetTop3Response](
            code=200,
            data=get_top3_response,
            message="success"
        )

    except TaskMicroserviceError as e:
        logger.error(f"微服务调用失败: {e}")
        return UnifiedResponse[GetTop3Response](
            code=e.status_code,
            data=None,
            message=e.message
        )
    except Exception as e:
        logger.error(f"获取Top3失败: {e}")
        return UnifiedResponse[GetTop3Response](
            code=500,
            data=None,
            message="获取Top3失败"
        )