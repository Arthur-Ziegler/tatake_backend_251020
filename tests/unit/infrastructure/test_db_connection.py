#!/usr/bin/env python3
"""
测试数据库连接修复的脚本

验证用户域是否正确连接到认证数据库
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import get_database_connection
from src.domains.auth.models import Auth
from sqlmodel import Session, select
from uuid import UUID

def test_database_connection():
    """测试数据库连接修复"""
    print("🔍 测试数据库连接修复...")

    # 1. 检查数据库连接配置
    db_connection = get_database_connection()
    print(f"📋 数据库URL: {db_connection.database_url}")

    # 2. 检查auth表结构
    with db_connection.get_session() as session:
        try:
            # 检查表结构
            result = session.exec("PRAGMA table_info(auth)").all()
            columns = [row[1] for row in result]
            print(f"📋 Auth表字段: {columns}")

            # 检查是否有phone字段
            has_phone = 'phone' in columns
            print(f"📋 是否有phone字段: {has_phone}")

            # 3. 查询测试用户
            test_user_id = "ba48caa9-a2f4-4638-9efe-39d0a86e583c"
            statement = select(Auth).where(Auth.id == test_user_id)
            user = session.exec(statement).first()

            if user:
                print(f"✅ 找到用户: {user.id}")
                print(f"   - phone: {user.phone}")
                print(f"   - wechat_openid: {user.wechat_openid}")
                print(f"   - is_guest: {user.is_guest}")
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

    return True

def test_uuid_conversion():
    """测试UUID转换"""
    print("\n🔍 测试UUID转换...")

    from src.core.uuid_converter import UUIDConverter

    test_uuid_str = "ba48caa9-a2f4-4638-9efe-39d0a86e583c"
    test_uuid_obj = UUID(test_uuid_str)

    # 测试转换
    converted_str = UUIDConverter.to_string(test_uuid_obj)
    converted_uuid = UUIDConverter.to_uuid(test_uuid_str)

    print(f"✅ UUID -> 字符串: {converted_str}")
    print(f"✅ 字符串 -> UUID: {converted_uuid}")
    print(f"✅ 转换一致性: {converted_str == test_uuid_str and converted_uuid == test_uuid_obj}")

if __name__ == "__main__":
    print("🚀 开始数据库连接修复验证...")

    success = test_database_connection()
    test_uuid_conversion()

    if success:
        print("\n✅ 数据库连接修复验证完成")
    else:
        print("\n❌ 数据库连接修复验证失败")
        sys.exit(1)