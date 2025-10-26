#!/usr/bin/env python3
"""
简单测试数据库连接修复
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)  # 强制重新加载

from src.database.connection import DatabaseConnection
from sqlmodel import Session, select, text
from src.domains.auth.models import Auth

def test_new_connection():
    """直接创建新的数据库连接实例"""
    print("🔍 测试新的数据库连接实例...")
    print(f"📋 DATABASE_URL: {os.getenv('DATABASE_URL')}")
    print(f"📋 AUTH_DATABASE_URL: {os.getenv('AUTH_DATABASE_URL')}")

    # 创建新的连接实例，不传递参数让类自己处理优先级
    db_connection = DatabaseConnection()
    print(f"📋 数据库URL: {db_connection.database_url}")

    # 使用sqlalchemy直接连接数据库
    engine = db_connection.get_engine()
    with Session(engine) as session:
        try:
            # 检查表结构
            result = session.execute(text("PRAGMA table_info(auth)")).fetchall()
            columns = [row[1] for row in result]
            print(f"📋 Auth表字段: {columns}")

            # 检查是否有phone字段
            has_phone = 'phone' in columns
            print(f"📋 是否有phone字段: {has_phone}")

            # 查询测试用户
            test_user_id = "ba48caa9-a2f4-4638-9efe-39d0a86e583c"
            statement = select(Auth).where(Auth.id == test_user_id)
            user = session.exec(statement).first()

            if user:
                print(f"✅ 找到用户: {user.id}")
                print(f"   - phone: {user.phone}")
                print(f"   - wechat_openid: {user.wechat_openid}")
                print(f"   - is_guest: {user.is_guest}")
                return True
            else:
                print(f"❌ 未找到用户: {test_user_id}")

                # 列出所有用户
                all_users = session.exec(select(Auth)).all()
                print(f"📋 数据库中共有 {len(all_users)} 个用户:")
                for u in all_users[:5]:  # 只显示前5个
                    print(f"   - {u.id}: phone={u.phone}, guest={u.is_guest}")

        except Exception as e:
            print(f"❌ 数据库操作失败: {e}")
            return False

    return False

if __name__ == "__main__":
    success = test_new_connection()
    if success:
        print("\n✅ 数据库连接修复成功！")
    else:
        print("\n❌ 数据库连接修复失败")
        sys.exit(1)