"""
聊天会话数据模型

定义本地SQLite数据库中的聊天会话表结构，只存储会话基本信息。

设计原则：
1. 极简化设计：只存储必要的会话信息
2. 本地SQLite数据库：独立于微服务
3. 自动时间戳：创建和更新时间自动管理
4. 用户隔离：每个用户只能访问自己的会话

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session
import os

# 数据库文件路径
DATABASE_URL = "sqlite:///chat_sessions.db"


class ChatSession(SQLModel, table=True):
    """聊天会话表"""

    __tablename__ = "chat_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, description="用户ID")
    session_id: str = Field(unique=True, index=True, description="会话ID")
    title: str = Field(description="会话标题")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="更新时间")

    class Config:
        # SQLite配置
        table_name = "chat_sessions"


# 创建数据库引擎
engine = create_engine(DATABASE_URL, echo=False)


def create_database():
    """创建数据库表"""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """获取数据库会话"""
    return Session(engine)


# 初始化数据库
def init_chat_database():
    """初始化聊天数据库"""
    try:
        create_database()
        print("✅ 聊天数据库初始化完成")
    except Exception as e:
        print(f"❌ 聊天数据库初始化失败: {e}")
        raise