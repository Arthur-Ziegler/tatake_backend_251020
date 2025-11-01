"""
任务本地操作数据库初始化

创建和管理本地任务操作相关的数据库表。
"""

import logging
from sqlmodel import SQLModel

from src.database import get_database_connection
from .models_local import TaskOperation, TaskCompletion, FocusStatus, PomodoroCount

logger = logging.getLogger(__name__)


def create_task_local_tables():
    """
    创建任务本地操作相关的数据库表

    这些表用于存储微服务不支持的功能：
    - task_operations: 任务操作记录（删除、更新等）
    - task_completions: 任务完成记录
    - focus_status_records: 专注状态记录
    - pomodoro_counts: 番茄钟计数
    """
    try:
        engine = get_database_connection().get_engine()

        # 创建所有表
        SQLModel.metadata.create_all(engine, tables=[
            TaskOperation.__table__,
            TaskCompletion.__table__,
            FocusStatus.__table__,
            PomodoroCount.__table__
        ])

        logger.info("任务本地操作数据库表创建成功")

    except Exception as e:
        logger.error(f"创建任务本地操作数据库表失败: {e}")
        raise


def initialize_task_local_database():
    """
    初始化任务本地操作数据库

    在应用启动时调用，确保所有必要的表都已创建。
    """
    logger.info("开始初始化任务本地操作数据库")
    create_task_local_tables()
    logger.info("任务本地操作数据库初始化完成")