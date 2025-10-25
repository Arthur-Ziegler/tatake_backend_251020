"""User领域数据库配置"""

from sqlmodel import Session, create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine


# 数据库配置
USER_DATABASE_URL = "sqlite:///./tatake_user.db"

# 创建同步引擎
engine = create_engine(
    USER_DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
    }
)


def get_user_session():
    """获取User领域数据库会话"""
    with Session(engine) as session:
        yield session
