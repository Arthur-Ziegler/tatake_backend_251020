"""Top3领域数据库配置"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlmodel import SQLModel


# 数据库配置
TOP3_DATABASE_URL = os.getenv(
    "TOP3_DATABASE_URL",
    "sqlite:///./tatake_top3.db"
)

# 是否在控制台输出SQL语句（调试用）
TOP3_ECHO_SQL = os.getenv("TOP3_ECHO_SQL", "false").lower() == "true"

# 创建同步引擎
top3_engine = create_engine(
    TOP3_DATABASE_URL,
    echo=TOP3_ECHO_SQL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20  # 连接超时时间（秒）
    }
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=top3_engine
)

def get_top3_session():
    """获取Top3领域数据库会话"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
