"""
Focus领域数据库模块

提供Focus领域相关的数据库初始化和会话管理功能。

功能：
1. 数据库表初始化
2. 依赖注入支持
3. 连接管理

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""

import logging
from sqlmodel import Session, SQLModel
from src.database import get_db_session

from .models import FocusSession

# 配置日志
logger = logging.getLogger(__name__)


def create_focus_tables():
    """创建Focus领域相关的数据库表"""
    try:
        from src.database import get_engine
        engine = get_engine()
        FocusSession.metadata.create_all(bind=engine)
        logger.info("Focus领域数据库表创建成功")
    except Exception as e:
        logger.error(f"Focus领域数据库表创建失败: {e}")
        raise


def get_focus_session():
    """
    获取Focus领域的数据库会话

    用于FastAPI的依赖注入，确保每个API请求都有独立的数据库会话。

    Yields:
        Session: SQLModel数据库会话
    """
    session_gen = get_db_session()
    session = next(session_gen)
    try:
        yield session
    finally:
        session.close()