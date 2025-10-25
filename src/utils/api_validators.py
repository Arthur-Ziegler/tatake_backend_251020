"""
API验证器工具集

提供FastAPI依赖项级别的验证功能，包括UUID格式验证、参数验证等。

作者：TaKeKe团队
版本：1.0.0 - UUID架构Batch 1
"""

import logging
from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, status, Query, Path
from fastapi.params import Depends

from .uuid_helpers import validate_uuid_string, ensure_uuid

# 配置日志
logger = logging.getLogger(__name__)


def validate_session_id(
    session_id: Annotated[str, Path(description="会话ID，必须是有效的UUID格式")]
) -> str:
    """
    FastAPI依赖项：验证session_id是否为有效的UUID格式

    Args:
        session_id: 从URL路径参数获取的会话ID

    Returns:
        str: 验证通过的会话ID（字符串格式）

    Raises:
        HTTPException: 当session_id不是有效UUID格式时抛出400错误
    """
    if not validate_uuid_string(session_id):
        logger.warning(f"无效的session_id格式: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": f"无效的会话ID格式: {session_id}。会话ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                "field": "session_id",
                "example": "550e8400-e29b-41d4-a716-446655440000"
            }
        )

    logger.debug(f"session_id验证通过: {session_id}")
    return session_id


def validate_user_id(
    user_id: Annotated[str, Query(description="用户ID，必须是有效的UUID格式")]
) -> str:
    """
    FastAPI依赖项：验证user_id是否为有效的UUID格式

    Args:
        user_id: 从查询参数获取的用户ID

    Returns:
        str: 验证通过的用户ID（字符串格式）

    Raises:
        HTTPException: 当user_id不是有效UUID格式时抛出400错误
    """
    if not validate_uuid_string(user_id):
        logger.warning(f"无效的user_id格式: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": f"无效的用户ID格式: {user_id}。用户ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                "field": "user_id",
                "example": "550e8400-e29b-41d4-a716-446655440000"
            }
        )

    logger.debug(f"user_id验证通过: {user_id}")
    return user_id


def validate_task_id(
    task_id: Annotated[str, Path(description="任务ID，必须是有效的UUID格式")]
) -> str:
    """
    FastAPI依赖项：验证task_id是否为有效的UUID格式

    Args:
        task_id: 从URL路径参数获取的任务ID

    Returns:
        str: 验证通过的任务ID（字符串格式）

    Raises:
        HTTPException: 当task_id不是有效UUID格式时抛出400错误
    """
    if not validate_uuid_string(task_id):
        logger.warning(f"无效的task_id格式: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": f"无效的任务ID格式: {task_id}。任务ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                "field": "task_id",
                "example": "550e8400-e29b-41d4-a716-446655440000"
            }
        )

    logger.debug(f"task_id验证通过: {task_id}")
    return task_id


def validate_reward_id(
    reward_id: Annotated[str, Path(description="奖励ID，必须是有效的UUID格式")]
) -> str:
    """
    FastAPI依赖项：验证reward_id是否为有效的UUID格式

    Args:
        reward_id: 从URL路径参数获取的奖励ID

    Returns:
        str: 验证通过的奖励ID（字符串格式）

    Raises:
        HTTPException: 当reward_id不是有效UUID格式时抛出400错误
    """
    if not validate_uuid_string(reward_id):
        logger.warning(f"无效的reward_id格式: {reward_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": f"无效的奖励ID格式: {reward_id}。奖励ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                "field": "reward_id",
                "example": "550e8400-e29b-41d4-a716-446655440000"
            }
        )

    logger.debug(f"reward_id验证通过: {reward_id}")
    return reward_id


# 便捷的类型别名，用于依赖注入
SessionId = Annotated[str, Depends(validate_session_id)]
UserId = Annotated[str, Depends(validate_user_id)]
TaskId = Annotated[str, Depends(validate_task_id)]
RewardId = Annotated[str, Depends(validate_reward_id)]


def validate_uuid_list(uuid_list: list, field_name: str = "uuid_list") -> bool:
    """
    验证UUID列表的有效性

    Args:
        uuid_list: UUID字符串列表
        field_name: 字段名称，用于错误消息

    Returns:
        bool: 验证是否通过

    Raises:
        HTTPException: 当列表中包含无效UUID时抛出400错误
    """
    if not isinstance(uuid_list, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": f"{field_name}必须是列表格式",
                "field": field_name,
                "expected_type": "list"
            }
        )

    invalid_uuids = []
    for uuid_str in uuid_list:
        if not validate_uuid_string(str(uuid_str)):
            invalid_uuids.append(str(uuid_str))

    if invalid_uuids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": f"{field_name}包含无效的UUID格式: {', '.join(invalid_uuids)}",
                "field": field_name,
                "invalid_values": invalid_uuids,
                "example": "550e8400-e29b-41d4-a716-446655440000"
            }
        )

    return True


class UUIDValidator:
    """
    UUID验证器类，提供更灵活的UUID验证功能
    """

    @staticmethod
    def validate_path_param(uuid_str: str, param_name: str = "id") -> str:
        """
        验证路径参数中的UUID

        Args:
            uuid_str: UUID字符串
            param_name: 参数名称

        Returns:
            str: 验证通过的UUID字符串

        Raises:
            HTTPException: UUID格式无效时
        """
        if not validate_uuid_string(uuid_str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"无效的{param_name}格式: {uuid_str}。必须是有效的UUID格式",
                    "field": param_name,
                    "value": uuid_str,
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                }
            )
        return uuid_str

    @staticmethod
    def validate_query_param(uuid_str: str, param_name: str = "id", required: bool = True) -> str:
        """
        验证查询参数中的UUID

        Args:
            uuid_str: UUID字符串
            param_name: 参数名称
            required: 是否必需

        Returns:
            str: 验证通过的UUID字符串

        Raises:
            HTTPException: UUID格式无效时
        """
        if not uuid_str and required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"缺少必需的查询参数: {param_name}",
                    "field": param_name
                }
            )

        if uuid_str and not validate_uuid_string(uuid_str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"无效的{param_name}格式: {uuid_str}。必须是有效的UUID格式",
                    "field": param_name,
                    "value": uuid_str,
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                }
            )
        return uuid_str

    @staticmethod
    def validate_body_field(uuid_value, field_name: str, required: bool = True) -> str:
        """
        验证请求体中的UUID字段

        Args:
            uuid_value: UUID值（可能是UUID对象或字符串）
            field_name: 字段名称
            required: 是否必需

        Returns:
            str: 验证通过的UUID字符串

        Raises:
            HTTPException: UUID格式无效时
        """
        if uuid_value is None and required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"缺少必需的字段: {field_name}",
                    "field": field_name
                }
            )

        if uuid_value is not None:
            try:
                uuid_obj = ensure_uuid(uuid_value)
                return str(uuid_obj)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": 400,
                        "message": f"无效的{field_name}格式: {uuid_value}。必须是有效的UUID格式",
                        "field": field_name,
                        "value": str(uuid_value),
                        "example": "550e8400-e29b-41d4-a716-446655440000"
                    }
                )

        return uuid_value


# 便捷实例
uuid_validator = UUIDValidator()