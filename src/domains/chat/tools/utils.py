"""
聊天工具辅助函数模块

提供任务管理工具所需的基础设施功能，包括Session管理、UUID转换、
日期解析和响应格式化等通用功能。

核心功能：
1. Session管理：get_task_service_context()
2. UUID转换：safe_uuid_convert()
3. 日期解析：parse_datetime()
4. 响应格式化：_success_response(), _error_response()

设计原则：
1. 简洁直接：避免过度抽象，保持代码简单易懂
2. 错误友好：提供详细的错误信息和异常处理
3. 类型安全：使用类型注解确保参数类型正确
4. 资源安全：正确管理数据库连接和事务
5. 测试驱动：所有函数都有对应的测试用例

基于LangGraph最佳实践：
- 支持上下文管理器模式
- 兼容现有DDD架构
- 提供友好的错误信息

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union, Generator
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# 导入数据库连接和服务
from src.database.connection import get_engine
from src.domains.task.service import TaskService
from src.domains.points.service import PointsService

# 配置日志
logger = logging.getLogger(__name__)


@contextmanager
def get_task_service_context() -> Generator[Dict[str, Any], None, None]:
    """
    获取任务服务上下文管理器

    创建和管理数据库Session，注入TaskService和PointsService实例，
    确保资源正确释放和事务管理。

    功能特性：
    - 自动创建数据库Session
    - 注入TaskService和PointsService
    - 异常时自动回滚事务
    - 确保Session正确关闭

    Yields:
        Dict[str, Any]: 包含以下键的上下文字典：
            - 'session': 数据库Session实例
            - 'task_service': TaskService实例
            - 'points_service': PointsService实例

    Raises:
        SQLAlchemyError: 数据库相关错误
        Exception: 其他运行时错误

    Example:
        >>> with get_task_service_context() as ctx:
        ...     task_service = ctx['task_service']
        ...     points_service = ctx['points_service']
        ...     session = ctx['session']
        ...     # 执行业务逻辑
        ...     # Session会在退出时自动关闭
    """
    session = None
    try:
        # 获取数据库引擎并创建Session
        engine = get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        logger.debug("数据库Session创建成功")

        # 创建PointsService实例
        points_service = PointsService(session)

        # 创建TaskService实例，注入PointsService
        task_service = TaskService(session, points_service)

        # 构建上下文字典
        context = {
            'session': session,
            'task_service': task_service,
            'points_service': points_service
        }

        logger.debug("任务服务上下文创建成功，返回上下文")

        # 生成上下文管理器
        yield context

    except Exception as e:
        # 发生异常时记录详细错误信息
        logger.error(f"获取任务服务上下文失败: {type(e).__name__}: {e}")

        # 如果Session已创建，尝试回滚事务
        if session is not None:
            try:
                session.rollback()
                logger.debug("事务回滚成功")
            except Exception as rollback_error:
                logger.error(f"事务回滚失败: {rollback_error}")

        # 重新抛出异常，让调用者处理
        raise

    finally:
        # 确保Session正确关闭，无论成功或异常
        if session is not None:
            try:
                session.close()
                logger.debug("数据库Session关闭成功")
            except Exception as close_error:
                logger.error(f"数据库Session关闭失败: {close_error}")


def safe_uuid_convert(uuid_input: Optional[Union[str, UUID]]) -> Optional[UUID]:
    """
    安全转换UUID格式

    将字符串或UUID对象安全转换为UUID对象，处理None值和无效格式，
    提供友好的错误信息。

    参数验证：
    - 支持UUID字符串和UUID对象
    - 处理None输入值
    - 验证UUID格式有效性

    Args:
        uuid_input (Optional[Union[str, UUID]]): 待转换的UUID值
            - UUID字符串格式：'550e8400-e29b-41d4-a716-446655440000'
            - UUID对象：直接返回
            - None：返回None

    Returns:
        Optional[UUID]: 转换后的UUID对象，输入为None时返回None

    Raises:
        ValueError: UUID格式无效时抛出，包含详细错误信息

    Example:
        >>> safe_uuid_convert("550e8400-e29b-41d4-a716-446655440000")
        UUID('550e8400-e29b-41d4-a716-446655440000')
        >>> safe_uuid_convert(None)
        None
    """
    # 处理None输入
    if uuid_input is None:
        logger.debug("UUID输入为None，返回None")
        return None

    # 如果已经是UUID对象，直接返回
    if isinstance(uuid_input, UUID):
        logger.debug(f"输入已经是UUID对象: {uuid_input}")
        return uuid_input

    # 处理字符串输入
    if isinstance(uuid_input, str):
        # 检查空字符串
        if not uuid_input.strip():
            raise ValueError("UUID不能为空字符串")

        try:
            # 尝试转换UUID
            converted_uuid = UUID(uuid_input.strip())
            logger.debug(f"UUID字符串转换成功: {uuid_input} -> {converted_uuid}")
            return converted_uuid
        except ValueError as e:
            # 提供友好的错误信息
            raise ValueError(f"无效的UUID格式: {uuid_input}") from e

    # 其他类型不支持
    raise ValueError(f"不支持的UUID输入类型: {type(uuid_input).__name__}")


def parse_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    解析日期时间字符串

    解析多种格式的日期时间字符串，支持ISO格式和时区信息，
    提供详细的错误信息用于调试。

    支持格式：
    - ISO 8601格式：'2024-12-25T10:30:00'
    - 带Z时区：'2024-12-25T10:30:00Z'
    - 带时区偏移：'2024-12-25T10:30:00+08:00'
    - 仅日期：'2024-12-25'

    Args:
        datetime_str (Optional[str]): 日期时间字符串

    Returns:
        Optional[datetime]: 解析后的datetime对象，输入为None时返回None

    Raises:
        ValueError: 日期时间格式无效时抛出，包含详细错误信息

    Example:
        >>> parse_datetime("2024-12-25T10:30:00")
        datetime.datetime(2024, 12, 25, 10, 30)
        >>> parse_datetime("2024-12-25T10:30:00Z")
        datetime.datetime(2024, 12, 25, 10, 30, tzinfo=datetime.timezone.utc)
    """
    # 处理None输入
    if datetime_str is None:
        logger.debug("日期时间输入为None，返回None")
        return None

    # 处理字符串输入
    if isinstance(datetime_str, str):
        # 检查空字符串
        if not datetime_str.strip():
            raise ValueError("日期时间字符串不能为空")

        cleaned_str = datetime_str.strip()

        try:
            # 尝试解析带时区信息的ISO格式
            if 'Z' in cleaned_str or '+' in cleaned_str or cleaned_str.endswith('UTC'):
                # 使用fromisoformat处理带时区的格式
                if cleaned_str.endswith('Z'):
                    # 将Z替换为+00:00以符合fromisoformat要求
                    iso_str = cleaned_str.replace('Z', '+00:00')
                else:
                    iso_str = cleaned_str

                parsed_datetime = datetime.fromisoformat(iso_str)
                logger.debug(f"带时区日期时间解析成功: {cleaned_str} -> {parsed_datetime}")
                return parsed_datetime

            else:
                # 尝试解析不带时区的格式
                # 支持多种分隔符和格式
                formats_to_try = [
                    '%Y-%m-%dT%H:%M:%S',      # ISO格式：2024-12-25T10:30:00
                    '%Y-%m-%d %H:%M:%S',       # 空格分隔：2024-12-25 10:30:00
                    '%Y-%m-%d',                  # 仅日期：2024-12-25
                    '%Y-%m-%dT%H:%M:%S.%f',     # 带毫秒：2024-12-25T10:30:00.123
                ]

                for fmt in formats_to_try:
                    try:
                        parsed_datetime = datetime.strptime(cleaned_str, fmt)
                        logger.debug(f"日期时间解析成功: {cleaned_str} -> {parsed_datetime} (格式: {fmt})")
                        return parsed_datetime
                    except ValueError:
                        continue

                # 如果所有格式都失败，尝试使用fromisoformat作为最后手段
                try:
                    parsed_datetime = datetime.fromisoformat(cleaned_str)
                    logger.debug(f"fromisoformat解析成功: {cleaned_str} -> {parsed_datetime}")
                    return parsed_datetime
                except ValueError:
                    pass

        except ValueError as e:
            logger.debug(f"日期时间解析失败: {cleaned_str}, 错误: {e}")

        # 所有解析尝试都失败
        raise ValueError(f"无效的日期时间格式: {datetime_str}")

    # 其他类型不支持
    raise ValueError(f"不支持的日期时间输入类型: {type(datetime_str).__name__}")


def _success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
    """
    构建成功响应格式

    创建统一格式的成功响应，包含数据、时间戳和可选消息。

    响应格式：
    {
        "success": true,
        "data": data,
        "message": message (可选),
        "timestamp": "2024-12-25T10:30:00Z"
    }

    Args:
        data (Any, optional): 响应数据，默认为None
        message (str, optional): 成功消息，默认为None

    Returns:
        Dict[str, Any]: 格式化的成功响应

    Example:
        >>> _success_response({"task_id": "123"})
        {'success': True, 'data': {'task_id': '123'}, 'timestamp': '2024-12-25T10:30:00Z'}
    """
    # 获取当前UTC时间戳
    timestamp = datetime.now(timezone.utc).isoformat()

    # 构建响应字典
    response = {
        "success": True,
        "data": data,
        "timestamp": timestamp
    }

    # 添加可选消息
    if message is not None:
        response["message"] = message

    logger.debug(f"成功响应构建完成: {response}")
    return response


def _error_response(message: str, code: str = None, details: Any = None) -> Dict[str, Any]:
    """
    构建错误响应格式

    创建统一格式的错误响应，包含错误信息、错误代码和详细信息。

    响应格式：
    {
        "success": false,
        "error": message,
        "error_code": code (可选),
        "details": details (可选),
        "timestamp": "2024-12-25T10:30:00Z"
    }

    Args:
        message (str): 错误消息，不能为空
        code (str, optional): 错误代码，默认为None
        details (Any, optional): 错误详细信息，默认为None

    Returns:
        Dict[str, Any]: 格式化的错误响应

    Raises:
        ValueError: 错误消息为空或None时抛出

    Example:
        >>> _error_response("任务不存在", "TASK_NOT_FOUND")
        {'success': False, 'error': '任务不存在', 'error_code': 'TASK_NOT_FOUND', 'timestamp': '2024-12-25T10:30:00Z'}
    """
    # 验证错误消息
    if not message or not message.strip():
        raise ValueError("错误消息不能为空")

    # 获取当前UTC时间戳
    timestamp = datetime.now(timezone.utc).isoformat()

    # 构建响应字典
    response = {
        "success": False,
        "error": message.strip(),
        "timestamp": timestamp
    }

    # 添加可选错误代码
    if code is not None:
        response["error_code"] = code

    # 添加可选详细信息
    if details is not None:
        response["details"] = details

    logger.debug(f"错误响应构建完成: {response}")
    return response


# 导出所有公共函数
__all__ = [
    'get_task_service_context',
    'safe_uuid_convert',
    'parse_datetime',
    '_success_response',
    '_error_response'
]