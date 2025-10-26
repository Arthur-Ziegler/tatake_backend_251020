#!/usr/bin/env python3
"""
Top3表迁移到主数据库

将Top3表创建在主数据库中，确保数据一致性。
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from sqlmodel import SQLModel, create_engine
from src.domains.top3.models import TaskTop3
from src.database.connection import get_database_connection

def create_top3_table():
    """在主数据库中创建Top3表"""
    print("🚀 开始在主数据库中创建Top3表...")

    try:
        # 获取主数据库连接
        connection = get_database_connection()
        engine = connection.get_engine()

        print(f"📊 数据库连接: {engine.url}")

        # 创建Top3表
        TaskTop3.metadata.create_all(engine)

        print("✅ Top3表创建成功!")

        # 验证表是否创建成功
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "task_top3" in tables:
            print("✅ 验证Top3表存在")

            # 检查表结构
            columns = inspector.get_columns("task_top3")
            print("📋 Top3表结构:")
            for col in columns:
                print(f"   - {col['name']} ({col['type']})")

            return True
        else:
            print("❌ Top3表创建失败")
            return False

    except Exception as e:
        print(f"❌ 创建Top3表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Top3表迁移工具")
    print("=" * 40)

    success = create_top3_table()

    if success:
        print("\n🎉 Top3表迁移成功!")
        sys.exit(0)
    else:
        print("\n💥 Top3表迁移失败")
        sys.exit(1)