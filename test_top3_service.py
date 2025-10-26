#!/usr/bin/env python3
"""
测试Top3Service的完整功能和事务管理
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
from src.domains.top3.schemas import SetTop3Request
from src.domains.task.service import TaskService
from src.domains.points.service import PointsService

def test_top3_service_complete():
    """测试Top3Service的完整功能"""
    print("🔍 测试Top3Service完整功能...")

    try:
        with get_top3_session() as session:
            # 创建相关服务
            points_service = PointsService(session)
            task_service = TaskService(session, points_service)
            top3_service = Top3Service(session)

            # 创建测试用户
            test_user_id = uuid4()

            print(f"✅ 测试用户ID: {test_user_id}")

            # 先为用户添加积分
            points_service.add_points(
                user_id=test_user_id,
                amount=1000,
                source_type="test",
                source_id=test_user_id,  # 提供source_id
                transaction_group=test_user_id  # 提供transaction_group
            )
            print("✅ 为用户添加1000积分")

            # 创建测试任务
            task1 = task_service.create_task(
                user_id=test_user_id,
                title="测试任务1",
                description="测试任务描述1",
                priority="high"
            )
            task2 = task_service.create_task(
                user_id=test_user_id,
                title="测试任务2",
                description="测试任务描述2",
                priority="medium"
            )
            task3 = task_service.create_task(
                user_id=test_user_id,
                title="测试任务3",
                description="测试任务描述3",
                priority="low"
            )

            print(f"✅ 创建测试任务: {task1.id}, {task2.id}, {task3.id}")

            # 测试设置Top3
            target_date = date.today().isoformat()
            request = SetTop3Request(
                date=target_date,
                task_ids=[str(task1.id), str(task2.id), str(task3.id)]
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

            # 测试重复设置（应该失败）
            try:
                top3_service.set_top3(test_user_id, request)
                print("❌ 重复设置检查失败 - 应该抛出异常")
                return False
            except Exception as e:
                print(f"✅ 重复设置检查通过 - 正确抛出异常: {type(e).__name__}")

            # 测试检查任务是否在今日Top3中
            is_in_top3 = top3_service.is_task_in_today_top3(
                str(test_user_id),
                str(task1.id)
            )
            if is_in_top3:
                print("✅ 任务在今日Top3检查通过")
            else:
                print("❌ 任务在今日Top3检查失败")
                return False

            # 清理测试数据
            # 清理Top3记录
            from src.domains.top3.repository import Top3Repository
            repo = Top3Repository(session)
            top3_record = repo.get_by_user_and_date(test_user_id, date.today())
            if top3_record:
                session.delete(top3_record)
                session.commit()

            # 清理任务
            task_service.delete_task(task1.id, test_user_id)
            task_service.delete_task(task2.id, test_user_id)
            task_service.delete_task(task3.id, test_user_id)

            print("✅ 清理测试数据成功")
            return True

    except Exception as e:
        print(f"❌ Top3Service完整功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_top3_transaction_rollback():
    """测试Top3Service事务回滚功能"""
    print("\n🔍 测试Top3Service事务回滚功能...")

    try:
        with get_top3_session() as session:
            points_service = PointsService(session)
            task_service = TaskService(session, points_service)
            top3_service = Top3Service(session)

            test_user_id = uuid4()

            # 先添加积分
            points_service.add_points(
                user_id=test_user_id,
                amount=1000,
                source_type="test",
                source_id=test_user_id,  # 提供source_id
                transaction_group=test_user_id  # 提供transaction_group
            )

            # 创建任务
            task = task_service.create_task(
                user_id=test_user_id,
                title="事务测试任务",
                description="用于测试事务的任务",
                priority="high"
            )

            print(f"✅ 初始积分余额: {points_service.get_balance(test_user_id)}")

            # 尝试设置Top3但故意触发异常
            target_date = date.today().isoformat()
            request = SetTop3Request(
                date=target_date,
                task_ids=[str(task.id), "invalid-task-id"]  # 包含无效任务ID
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
            task_service.delete_task(task.id, test_user_id)
            print("✅ 清理测试数据成功")

            return True

    except Exception as e:
        print(f"❌ Top3Service事务回滚测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始Top3Service完整功能测试...")
    print("=" * 50)

    test1 = test_top3_service_complete()
    test2 = test_top3_transaction_rollback()

    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print(f"   Top3Service完整功能: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"   Top3Service事务回滚: {'✅ 通过' if test2 else '❌ 失败'}")

    if all([test1, test2]):
        print("\n🎉 Top3Service测试全部通过！")
        sys.exit(0)
    else:
        print("\n💥 Top3Service测试失败")
        sys.exit(1)