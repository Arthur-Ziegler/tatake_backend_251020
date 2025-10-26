#!/usr/bin/env python3
"""
测试Top3迁移到主数据库的功能
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from datetime import date
from uuid import uuid4

from src.domains.top3.database import get_top3_session
from src.domains.top3.repository import Top3Repository
from src.domains.top3.service import Top3Service
from src.domains.top3.models import TaskTop3

def test_top3_table_creation():
    """测试Top3表创建和基本操作"""
    print("🔍 测试Top3表创建和基本操作...")

    try:
        with get_top3_session() as session:
            # 创建Repository
            repo = Top3Repository(session)

            # 测试用户ID
            test_user_id = uuid4()
            test_date = date.today()

            print(f"✅ 测试用户ID: {test_user_id}")
            print(f"✅ 测试日期: {test_date}")

            # 测试查询（应该为空）
            existing = repo.get_by_user_and_date(test_user_id, test_date)
            if existing is None:
                print("✅ 空查询测试通过")
            else:
                print(f"❌ 空查询失败，找到记录: {existing}")
                return False

            # 测试创建Top3记录
            task_ids = ["task1", "task2", "task3"]
            top3 = repo.create(test_user_id, test_date, task_ids)

            if top3:
                print("✅ 创建Top3记录成功")
                print(f"   - ID: {top3.id}")
                print(f"   - 用户ID: {top3.user_id}")
                print(f"   - 日期: {top3.top_date}")
                print(f"   - 任务IDs: {top3.task_ids}")
                print(f"   - 消耗积分: {top3.points_consumed}")
            else:
                print("❌ 创建Top3记录失败")
                return False

            # 测试查询（应该找到记录）
            existing = repo.get_by_user_and_date(test_user_id, test_date)
            if existing:
                print("✅ 查询创建的记录成功")
            else:
                print("❌ 查询创建的记录失败")
                return False

            # 清理测试数据
            session.delete(top3)
            session.commit()
            print("✅ 清理测试数据成功")

            return True

    except Exception as e:
        print(f"❌ Top3表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_top3_service():
    """测试Top3Service功能"""
    print("\n🔍 测试Top3Service功能...")

    try:
        with get_top3_session() as session:
            # 创建Service
            service = Top3Service(session)

            # 测试用户ID
            test_user_id = uuid4()
            test_date = date.today()

            print(f"✅ 测试用户ID: {test_user_id}")

            # 测试获取不存在的Top3
            result = service.get_top3(test_user_id, test_date.isoformat())
            if result and result.get("task_ids") == []:
                print("✅ 获取不存在的Top3测试通过")
            else:
                print(f"❌ 获取不存在的Top3失败: {result}")
                return False

            print("✅ Top3Service基本功能测试通过")
            return True

    except Exception as e:
        print(f"❌ Top3Service测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_consistency():
    """测试数据库一致性"""
    print("\n🔍 测试数据库一致性...")

    try:
        # 检查主数据库中是否有Top3表
        from src.database.connection import get_database_connection
        connection = get_database_connection()

        with connection.get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='task_top3'"))
            tables = result.fetchall()

            if tables:
                print("✅ Top3表存在于主数据库中")

                # 检查表结构
                result = session.execute(text("PRAGMA table_info(task_top3)"))
                columns = result.fetchall()

                required_columns = ['id', 'user_id', 'top_date', 'task_ids', 'points_consumed', 'created_at']
                found_columns = [col[1] for col in columns]

                missing_columns = set(required_columns) - set(found_columns)
                if not missing_columns:
                    print("✅ Top3表结构完整")
                    print(f"   找到列: {found_columns}")
                else:
                    print(f"❌ Top3表缺少列: {missing_columns}")
                    return False
            else:
                print("❌ Top3表不存在于主数据库中")
                return False

        return True

    except Exception as e:
        print(f"❌ 数据库一致性测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始Top3迁移功能测试...")
    print("=" * 50)

    test1 = test_top3_table_creation()
    test2 = test_top3_service()
    test3 = test_database_consistency()

    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print(f"   Top3表创建: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"   Top3Service: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"   数据库一致性: {'✅ 通过' if test3 else '❌ 失败'}")

    if all([test1, test2, test3]):
        print("\n🎉 Top3迁移功能测试全部通过！")
        sys.exit(0)
    else:
        print("\n💥 Top3迁移功能测试失败")
        sys.exit(1)