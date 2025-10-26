#!/usr/bin/env python3
"""
生产环境完整流程测试

模拟用户从注册到使用欢迎礼包的真实流程
找出数据持久化问题的根本原因
"""

import sys
import os
import asyncio
import httpx
from httpx import ASGITransport
from uuid import uuid4
import tempfile

# 使用生产环境的数据库配置
temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
temp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"
os.environ["DEBUG"] = "false"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import get_session
from src.domains.auth.repository import AuthRepository
from src.domains.auth.models import Auth
from sqlmodel import select
from src.api.main import app

def with_session(func):
    """数据库会话装饰器"""
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
def initialize_database(session):
    """初始化数据库"""
    print("🔧 初始化生产环境数据库...")

    # 导入所有模型
    from src.domains.auth.models import Auth, AuthLog, SMSVerification
    from src.domains.user.models import User, UserSettings, UserStats

    # 创建所有表
    from sqlmodel import SQLModel
    engine = session.bind
    SQLModel.metadata.create_all(engine, checkfirst=True)

    print("✅ 数据库初始化完成")

@with_session
def check_database_status(session):
    """检查数据库状态"""
    print("📊 检查数据库状态...")

    try:
        statement = select(Auth)
        users = session.exec(statement).all()
        print(f"数据库中用户总数: {len(users)}")

        for user in users:
            print(f"👤 用户: {user.id}, 游客: {user.is_guest}, 创建时间: {user.created_at}")

        return len(users)

    except Exception as e:
        print(f"❌ 检查数据库状态失败: {e}")
        import traceback
        traceback.print_exc()
        return 0

async def test_complete_flow():
    """测试完整的用户注册和使用流程"""
    print("🚀 开始完整流程测试...")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # 1. 游客初始化
            print("\n1️⃣ 游客初始化...")
            auth_response = await client.post("/auth/guest/init")
            print(f"状态码: {auth_response.status_code}")

            if auth_response.status_code != 200:
                print(f"❌ 游客初始化失败: {auth_response.text}")
                return False

            auth_data = auth_response.json()
            print(f"✅ 游客初始化成功: {auth_data}")

            # 提取JWT token和用户ID
            access_token = auth_data.get("data", {}).get("access_token")
            if not access_token:
                print("❌ 未获取到access_token")
                return False

            # 解析JWT获取用户ID
            import base64
            import json
            jwt_parts = access_token.split('.')
            if len(jwt_parts) != 3:
                print("❌ JWT格式无效")
                return False

            payload_part = jwt_parts[1]
            padding = len(payload_part) % 4
            if padding:
                payload_part += '=' * (4 - padding)

            try:
                payload_bytes = base64.urlsafe_b64decode(payload_part)
                payload_str = payload_bytes.decode('utf-8')
                payload = json.loads(payload_str)
                user_id = payload.get('sub')
                print(f"📋 JWT中的用户ID: {user_id}")
            except Exception as e:
                print(f"❌ JWT解析失败: {e}")
                return False

            # 2. 设置认证头
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # 3. 测试用户profile接口
            print("\n2️⃣ 测试用户profile接口...")
            profile_response = await client.get("/user/profile", headers=headers)
            print(f"Profile状态码: {profile_response.status_code}")

            if profile_response.status_code != 200:
                print(f"❌ Profile接口失败: {profile_response.text}")
                return False

            profile_data = profile_response.json()
            print(f"✅ Profile接口成功: {profile_data.get('data', {}).get('id')}")

            # 4. 测试积分查询接口
            print("\n3️⃣ 测试积分查询接口...")
            points_response = await client.get("/points/my-points", headers=headers)
            print(f"Points状态码: {points_response.status_code}")

            if points_response.status_code != 200:
                print(f"❌ 积分查询失败: {points_response.text}")
                return False

            points_data = points_response.json()
            print(f"✅ 积分查询成功: {points_data.get('data', {}).get('current_points')}")

            # 5. 测试欢迎礼包接口（关键测试）
            print("\n4️⃣ 测试欢迎礼包接口...")
            gift_response = await client.post("/user/welcome-gift/claim", headers=headers)
            print(f"欢迎礼包状态码: {gift_response.status_code}")
            print(f"欢迎礼包响应: {gift_response.text}")

            if gift_response.status_code != 200:
                print(f"❌ 欢迎礼包接口失败")
                # 检查是否是"用户不存在"错误
                if "用户不存在" in gift_response.text:
                    print("🎯 确认问题：用户不存在错误")
                    return False
                return False

            gift_data = gift_response.json()
            print(f"✅ 欢迎礼包接口成功: {gift_data}")

            return True

        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

@with_session
def final_database_check(session):
    """最终数据库检查"""
    print("\n🔍 最终数据库检查...")

    try:
        statement = select(Auth)
        users = session.exec(statement).all()
        print(f"最终用户总数: {len(users)}")

        for user in users:
            print(f"👤 最终用户: {user.id}, 游客: {user.is_guest}")

        return len(users) > 0

    except Exception as e:
        print(f"❌ 最终数据库检查失败: {e}")
        return False

def cleanup():
    """清理测试文件"""
    try:
        os.unlink(temp_db.name)
        print("🧹 测试文件清理完成")
    except:
        pass

async def main():
    """主测试函数"""
    print("🚀 开始生产环境完整流程测试")

    try:
        # 1. 初始化数据库
        initialize_database()

        # 2. 检查初始状态
        initial_count = check_database_status()
        print(f"初始用户数量: {initial_count}")

        # 3. 执行完整流程测试
        success = await test_complete_flow()

        # 4. 最终数据库检查
        final_has_users = final_database_check()

        print("\n🎯 测试结果分析:")
        print(f"✅ 流程成功: {success}")
        print(f"✅ 数据库有数据: {final_has_users}")

        if success and final_has_users:
            print("🎉 生产环境流程测试通过！")
            return True
        elif not success and not final_has_users:
            print("❌ 确认问题：数据持久化失败，用户注册后数据未保存")
            return False
        else:
            print("❌ 异常情况：流程成功但数据库无数据，或数据库有数据但流程失败")
            return False

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)