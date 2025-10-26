#!/usr/bin/env python3
"""
简化版Top3Service测试，专注于验证迁移后的功能
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from datetime import date
from uuid import uuid4
from sqlalchemy import text

from src.domains.top3.database import get_top3_session
from src.domains.top3.service import Top3Service
from src.domains.top3.schemas import SetTop3Request
from src.domains.points.service import PointsService

def test_top3_basic_operations():
    """测试Top3基本操作"""
    print("🔍 测试Top3基本操作...")

    try:
        with get_top3_session() as session:
            # 创建服务
            points_service = PointsService(session)
            top3_service = Top3Service(session)

            # 创建测试用户
            test_user_id = uuid4()
            print(f"✅ 测试用户ID: {test_user_id}")

            # 添加积分
            points_service.add_points(
                user_id=test_user_id,
                amount=1000,
                source_type="test",
                source_id=test_user_id,
                transaction_group=test_user_id
            )
            print("✅ 添加积分成功")

            # 手动插入一些任务记录用于测试（不依赖TaskService）
            # 创建一些模拟的任务ID
            task_id1 = uuid4()
            task_id2 = uuid4()
            task_id3 = uuid4()

            # 直接插入任务记录到数据库
            session.execute(text("""
                INSERT INTO tasks (id, user_id, title, description, status, priority, is_deleted, created_at, updated_at)
                VALUES (:id, :user_id, :title, :description, :status, :priority, :is_deleted, :created_at, :updated_at)
            """), {
                'id': str(task_id1),
                'user_id': str(test_user_id),
                'title': '测试任务1',
                'description': '测试任务描述1',
                'status': 'pending',
                'priority': 'high',
                'is_deleted': False,
                'created_at': '2025-10-26 19:02:00',
                'updated_at': '2025-10-26 19:02:00'
            })

            session.execute(text("""
                INSERT INTO tasks (id, user_id, title, description, status, priority, is_deleted, created_at, updated_at)
                VALUES (:id, :user_id, :title, :description, :status, :priority, :is_deleted, :created_at, :updated_at)
            """), {
                'id': str(task_id2),
                'user_id': str(test_user_id),
                'title': '测试任务2',
                'description': '测试任务描述2',
                'status': 'pending',
                'priority': 'medium',
                'is_deleted': False,
                'created_at': '2025-10-26 19:02:00',
                'updated_at': '2025-10-26 19:02:00'
            })

            session.execute(text("""
                INSERT INTO tasks (id, user_id, title, description, status, priority, is_deleted, created_at, updated_at)
                VALUES (:id, :user_id, :title, :description, :status, :priority, :is_deleted, :created_at, :updated_at)
            """), {
                'id': str(task_id3),
                'user_id': str(test_user_id),
                'title': '测试任务3',
                'description': '测试任务描述3',
                'status': 'pending',
                'priority': 'low',
                'is_deleted': False,
                'created_at': '2025-10-26 19:02:00',
                'updated_at': '2025-10-26 19:02:00'
            })
            session.commit()
            print("✅ 创建测试任务成功")

            # 测试设置Top3
            target_date = date.today().isoformat()
            request = SetTop3Request(
                date=target_date,
                task_ids=[str(task_id1), str(task_id2), str(task_id3)]
            )

            result = top3_service.set_top3(test_user_id, request)
            if result:
                print("✅ 设置Top3成功")
                print(f"   - 日期: {result['date']}")
                print(f"   - 任务数: {len(result['task_ids'])}")
                print(f"   - 消耗积分: {result['points_consumed']}")
                print(f"   - 剩余积分: {result['remaining_balance']}")
            else:
                print("❌ 设置Top3失败")
                return False

            # 测试获取Top3
            get_result = top3_service.get_top3(test_user_id, target_date)
            if get_result and len(get_result['task_ids']) == 3:
                print("✅ 获取Top3成功")
                print(f"   - 任务数: {len(get_result['task_ids'])}")
            else:
                print("❌ 获取Top3失败")
                return False

            # 测试检查任务是否在今日Top3中
            is_in_top3 = top3_service.is_task_in_today_top3(
                str(test_user_id),
                str(task_id1)
            )
            if is_in_top3:
                print("✅ 任务在今日Top3检查通过")
            else:
                print("❌ 任务在今日Top3检查失败")
                return False

            # 清理测试数据
            session.execute(text("DELETE FROM task_top3 WHERE user_id = :user_id"), {'user_id': str(test_user_id)})
            session.execute(text("DELETE FROM tasks WHERE user_id = :user_id"), {'user_id': str(test_user_id)})
            session.execute(text("DELETE FROM points_transactions WHERE user_id = :user_id"), {'user_id': str(test_user_id)})
            session.commit()
            print("✅ 清理测试数据成功")

            return True

    except Exception as e:
        print(f"❌ Top3基本操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_top3_transaction():
    """测试Top3事务处理"""
    print("\n🔍 测试Top3事务处理...")

    try:
        with get_top3_session() as session:
            points_service = PointsService(session)
            top3_service = Top3Service(session)

            test_user_id = uuid4()

            # 添加积分
            points_service.add_points(
                user_id=test_user_id,
                amount=1000,
                source_type="test",
                source_id=test_user_id,
                transaction_group=test_user_id
            )

            # 创建一个任务
            task_id = uuid4()
            session.execute(text("""
                INSERT INTO tasks (id, user_id, title, description, status, priority, is_deleted, created_at, updated_at)
                VALUES (:id, :user_id, :title, :description, :status, :priority, :is_deleted, :created_at, :updated_at)
            """), {
                'id': str(task_id),
                'user_id': str(test_user_id),
                'title': '事务测试任务',
                'description': '用于测试事务的任务',
                'status': 'pending',
                'priority': 'high',
                'is_deleted': False,
                'created_at': '2025-10-26 19:02:00',
                'updated_at': '2025-10-26 19:02:00'
            })
            session.commit()

            print(f"✅ 初始积分余额: {points_service.get_balance(test_user_id)}")

            # 尝试设置Top3但故意触发异常（使用无效的任务ID）
            target_date = date.today().isoformat()
            request = SetTop3Request(
                date=target_date,
                task_ids=[str(task_id), "invalid-task-id"]  # 包含无效任务ID
            )

            try:
                top3_service.set_top3(test_user_id, request)
                print("❌ 事务回滚测试失败 - 应该抛出异常")
                return False
            except Exception as e:
                print(f"✅ 事务回滚测试通过 - 正确抛出异常: {type(e).__name__}")

                # 检查积分是否没有扣除
                final_balance = points_service.get_balance(test_user_id)
                if final_balance == 1000:
                    print("✅ 事务回滚验证通过 - 积分未扣除")
                else:
                    print(f"❌ 事务回滚验证失败 - 积分被错误扣除: {final_balance}")
                    return False

                # 检查Top3记录是否没有创建
                top3_result = top3_service.get_top3(test_user_id, target_date)
                if len(top3_result['task_ids']) == 0:
                    print("✅ 事务回滚验证通过 - Top3记录未创建")
                else:
                    print("❌ 事务回滚验证失败 - Top3记录被错误创建")
                    return False

            # 清理测试数据
            session.execute(text("DELETE FROM tasks WHERE user_id = :user_id"), {'user_id': str(test_user_id)})
            session.execute(text("DELETE FROM points_transactions WHERE user_id = :user_id"), {'user_id': str(test_user_id)})
            session.commit()
            print("✅ 清理测试数据成功")

            return True

    except Exception as e:
        print(f"❌ Top3事务处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始简化版Top3功能测试...")
    print("=" * 50)

    test1 = test_top3_basic_operations()
    test2 = test_top3_transaction()

    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print(f"   Top3基本操作: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"   Top3事务处理: {'✅ 通过' if test2 else '❌ 失败'}")

    if all([test1, test2]):
        print("\n🎉 Top3功能测试全部通过！")
        sys.exit(0)
    else:
        print("\n💥 Top3功能测试失败")
        sys.exit(1)