#!/usr/bin/env python3
# 验证统一数据库配置的测试脚本

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import get_session
from src.domains.auth.models import Auth
from sqlmodel import select

def test_unified_database():
    print("🧪 测试统一数据库配置...")

    def with_session(func):
        def wrapper(*args, **kwargs):
            session_gen = get_session()
            session = next(session_gen)
            try:
                result = func(session, *args, **kwargs)
            finally:
                try:
                    next(session_gen)
                except StopIteration:
                    pass
            return result
        return wrapper

    @with_session
    def check_users(session):
        statement = select(Auth)
        users = session.exec(statement).all()
        print(f"主数据库中用户总数: {len(users)}")

        for user in users:
            print(f"  用户: {user.id}, 游客: {user.is_guest}")

        return len(users) > 0

    return check_users()

if __name__ == "__main__":
    success = test_unified_database()
    if success:
        print("✅ 统一数据库配置验证成功！")
    else:
        print("❌ 统一数据库配置验证失败，可能需要重启服务")