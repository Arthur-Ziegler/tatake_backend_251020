"""User领域数据库配置"""

from sqlmodel import Session
from src.api.database import engine


def get_user_session():
    """获取User领域数据库会话"""
    with Session(engine) as session:
        yield session
