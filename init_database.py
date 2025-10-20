#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database.connection import get_database_connection
from src.models import BaseSQLModel

async def init_database():
    """初始化数据库表结构"""
    # 获取数据库连接
    db_connection = get_database_connection()
    engine = db_connection.get_engine()

    if engine:
        # 使用SQLModel的metadata来创建表（checkfirst避免重复创建）
        BaseSQLModel.metadata.create_all(engine, checkfirst=True)
        print("✓ 数据库表创建/验证成功")
    else:
        print("✗ 无法获取数据库引擎")

if __name__ == "__main__":
    asyncio.run(init_database())