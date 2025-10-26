"""
数据库测试助手

提供数据库相关的测试工具函数和类。

作者：TaTakeKe团队
版本：1.0.0 - 数据库测试助手
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlmodel import SQLModel


class DatabaseHelper:
    """数据库测试助手类"""
    
    @staticmethod
    def create_in_memory_session() -> Session:
        """创建内存数据库会话用于测试"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(engine)
        return Session(engine)
    
    @staticmethod
    def clean_tables(session: Session, table_names: Optional[List[str]] = None) -> None:
        """清理指定表的数据"""
        if table_names is None:
            return
        
        for table_name in table_names:
            session.execute(text(f"DELETE FROM {table_name}"))
        session.commit()
    
    @staticmethod
    def get_table_row_count(session: Session, table_name: str) -> int:
        """获取表的行数"""
        result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()
    
    @staticmethod
    def table_exists(session: Session, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
                {"table_name": table_name}
            )
            return result.scalar() is not None
        except Exception:
            return False