"""Top3领域数据库配置

使用主数据库连接，确保数据一致性。
"""

from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session

from src.database import get_database_connection


@contextmanager
def get_top3_session() -> Generator[Session, None, None]:
    """
    获取Top3领域数据库会话

    使用主数据库连接，确保与任务域的数据一致性。
    """
    connection = get_database_connection()
    with connection.get_session() as session:
        yield session
