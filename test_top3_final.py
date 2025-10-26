#!/usr/bin/env python3
"""
最终版Top3测试 - 专注于验证Top3域迁移后的核心功能
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from datetime import date
from uuid import uuid4

from src.domains.top3.database import get_top3_session
from src.domains.top3.service import Top3Service
from src.domains.top3.repository import Top3Repository

def test_top3_repository():
    """测试Top3Repository基本功能"""
    print("🔍 测试Top3Repository基本功能...")

    try:
        with get_top3_session() as session:
            repo = Top3Repository(session)

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

            # 测试任务检查功能
            is_in_top3 = repo.is_task_in_today_top3(test_user_id, "task1")
            if is_in_top3:
                print("✅ 任务在今日Top3检查通过")
            else:
                print("❌ 任务在今日Top3检查失败")
                return False

            # 清理测试数据
            session.delete(top3)
            session.commit()
            print("✅ 清理测试数据成功")

            return True

    except Exception as e:
        print(f"❌ Top3Repository测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_top3_service_basic():
    """测试Top3Service基本功能（不依赖其他服务）"""
    print("\n🔍 测试Top3Service基本功能...")

    try:
        with get_top3_session() as session:
            service = Top3Service(session)

            test_user_id = uuid4()
            target_date = date.today().isoformat()

            print(f"✅ 测试用户ID: {test_user_id}")

            # 测试获取不存在的Top3
            result = service.get_top3(test_user_id, target_date)
            if result and result.get("task_ids") == []:
                print("✅ 获取不存在的Top3测试通过")
            else:
                print(f"❌ 获取不存在的Top3失败: {result}")
                return False

            # 测试检查任务是否在今日Top3中（没有设置Top3）
            is_in_top3 = service.is_task_in_today_top3(str(test_user_id), "test-task")
            if not is_in_top3:
                print("✅ 未设置Top3时的任务检查通过")
            else:
                print("❌ 未设置Top3时的任务检查失败")
                return False

            print("✅ Top3Service基本功能测试通过")
            return True

    except Exception as e:
        print(f"❌ Top3Service基本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_integration():
    """测试数据库集成"""
    print("\n🔍 测试数据库集成...")

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

                # 检查数据
                result = session.execute(text("SELECT COUNT(*) FROM task_top3"))
                count = result.scalar()
                print(f"✅ Top3表中有 {count} 条记录")

            else:
                print("❌ Top3表不存在于主数据库中")
                return False

        return True

    except Exception as e:
        print(f"❌ 数据库集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_migration_success():
    """验证迁移成功的关键指标"""
    print("\n🔍 验证迁移成功的关键指标...")

    try:
        # 1. 检查Top3表是否在主数据库中
        from src.database.connection import get_database_connection
        connection = get_database_connection()

        with connection.get_session() as session:
            from sqlalchemy import text

            # 检查表存在
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='task_top3'"))
            tables = result.fetchall()

            if not tables:
                print("❌ Top3表未成功迁移到主数据库")
                return False
            print("✅ Top3表已成功迁移到主数据库")

            # 2. 检查是否使用相同的数据库文件
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('tasks', 'points_transactions') LIMIT 2"))
            main_tables = result.fetchall()

            if len(main_tables) >= 2:
                print("✅ 确认Top3与任务、积分表在同一个数据库中")
            else:
                print("❌ 无法确认Top3与主表在同一数据库中")
                return False

            # 3. 检查Top3表是否可以正常操作
            test_user_id = str(uuid4())
            test_date = date.today()

            # 插入测试数据
            session.execute(text("""
                INSERT INTO task_top3 (user_id, top_date, task_ids, points_consumed, created_at)
                VALUES (:user_id, :top_date, :task_ids, :points_consumed, :created_at)
            """), {
                'user_id': test_user_id,
                'top_date': test_date,
                'task_ids': '[{"task_id": "test1", "position": 1}]',
                'points_consumed': 300,
                'created_at': test_date
            })
            session.commit()

            # 查询测试数据
            result = session.execute(text("SELECT * FROM task_top3 WHERE user_id = :user_id"), {'user_id': test_user_id})
            record = result.fetchone()

            if record:
                print("✅ Top3表读写操作正常")

                # 清理测试数据
                session.execute(text("DELETE FROM task_top3 WHERE user_id = :user_id"), {'user_id': test_user_id})
                session.commit()
                print("✅ 测试数据清理完成")
            else:
                print("❌ Top3表读写操作失败")
                return False

        print("✅ 所有迁移成功指标验证通过")
        return True

    except Exception as e:
        print(f"❌ 迁移成功验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始最终版Top3功能测试...")
    print("=" * 50)

    test1 = test_top3_repository()
    test2 = test_top3_service_basic()
    test3 = test_database_integration()
    test4 = test_migration_success()

    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print(f"   Top3Repository功能: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"   Top3Service基本功能: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"   数据库集成: {'✅ 通过' if test3 else '❌ 失败'}")
    print(f"   迁移成功验证: {'✅ 通过' if test4 else '❌ 失败'}")

    if all([test1, test2, test3, test4]):
        print("\n🎉 Top3迁移功能测试全部通过！")
        print("✅ Top3域已成功迁移到主数据库")
        print("✅ 数据一致性得到保障")
        print("✅ 核心功能正常运行")
        sys.exit(0)
    else:
        print("\n💥 Top3迁移功能测试失败")
        sys.exit(1)