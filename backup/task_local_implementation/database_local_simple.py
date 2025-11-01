"""
任务本地操作数据库初始化（简化版）

直接使用SQLAlchemy创建表，避免SQLModel的外键问题。
"""

import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from src.database import get_database_connection

logger = logging.getLogger(__name__)

# 创建基础模型类
Base = declarative_base()


class TaskOperation(Base):
    """任务操作表"""
    __tablename__ = "task_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False)
    task_id = Column(String(255), nullable=False)
    operation_type = Column(String(50), nullable=False)
    operation_data = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())


class TaskCompletion(Base):
    """任务完成记录表"""
    __tablename__ = "task_completions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False)
    task_id = Column(String(255), nullable=False)
    completion_type = Column(String(50), nullable=False)
    points_earned = Column(Integer, nullable=False, default=0)
    reward_given = Column(String(255), nullable=True)
    completion_data = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=False, default=func.now())


class FocusStatus(Base):
    """专注状态记录表"""
    __tablename__ = "focus_status_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False)
    task_id = Column(String(255), nullable=True)
    focus_status = Column(String(50), nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    status_data = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())


class PomodoroCount(Base):
    """番茄钟计数表"""
    __tablename__ = "pomodoro_counts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False)
    date_filter = Column(String(20), nullable=False)
    count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, nullable=False, default=func.now())


def create_task_local_tables_simple():
    """
    创建任务本地操作相关的数据库表（简化版）

    这些表用于存储微服务不支持的功能：
    - task_operations: 任务操作记录（删除、更新等）
    - task_completions: 任务完成记录
    - focus_status_records: 专注状态记录
    - pomodoro_counts: 番茄钟计数
    """
    try:
        engine = get_database_connection().get_engine()

        # 创建所有表
        Base.metadata.create_all(engine, tables=[
            TaskOperation.__table__,
            TaskCompletion.__table__,
            FocusStatus.__table__,
            PomodoroCount.__table__
        ])

        logger.info("任务本地操作数据库表创建成功（简化版）")

    except Exception as e:
        logger.error(f"创建任务本地操作数据库表失败（简化版）: {e}")
        raise


def initialize_task_local_database_simple():
    """
    初始化任务本地操作数据库（简化版）

    在应用启动时调用，确保所有必要的表都已创建。
    """
    logger.info("开始初始化任务本地操作数据库（简化版）")
    create_task_local_tables_simple()
    logger.info("任务本地操作数据库初始化完成（简化版）")