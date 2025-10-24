#!/usr/bin/env python3
"""
测试积分流水记录修复
"""

import uuid
from datetime import datetime, timezone

def test_points_transaction_fix():
    """测试积分流水记录是否正确创建"""
    from src.database import get_engine
    from sqlmodel import Session
    from src.domains.task.service import TaskService
    from src.domains.task.repository import TaskRepository
    from src.domains.points.service import PointsService
    from src.domains.task.models import TaskStatusConst

    engine = get_engine()
    session = Session(engine)
    try:
        # 初始化服务
        task_repository = TaskRepository(session)
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)

        user_id = str(uuid.uuid4())
        print(f"用户ID: {user_id}")

        # 获取初始积分
        initial_balance = points_service.get_balance(user_id)
        print(f"初始积分: {initial_balance}")

        # 创建任务
        task = task_repository.create({
            "user_id": user_id,
            "title": "积分流水测试任务",
            "status": TaskStatusConst.PENDING
        })
        print(f"任务创建: {task.id}")

        # 获取任务完成前的积分流水数量
        from sqlalchemy import text
        initial_transactions = session.execute(
            text("SELECT COUNT(*) as count FROM points_transactions WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).first()
        initial_count = initial_transactions.count if initial_transactions else 0
        print(f"任务完成前积分流水数量: {initial_count}")

        # 完成任务
        print(f"\n=== 完成任务 ===")
        result = task_service.complete_task(user_id, task.id)
        print(f"任务完成结果: {result}")

        # 获取任务完成后的积分
        final_balance = points_service.get_balance(user_id)
        print(f"任务完成后积分: {final_balance}")

        # 获取任务完成后的积分流水数量
        final_transactions = session.execute(
            text("SELECT COUNT(*) as count FROM points_transactions WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).first()
        final_count = final_transactions.count if final_transactions else 0
        print(f"任务完成后积分流水数量: {final_count}")

        # 验证积分流水记录
        print(f"\n=== 验证积分流水记录 ===")
        success = True

        # 检查积分是否正确增加
        expected_points = result.get('points_awarded', 0)
        actual_points_change = final_balance - initial_balance
        if actual_points_change != expected_points:
            print(f"❌ 积分增加错误: 期望{expected_points}, 实际{actual_points_change}")
            success = False
        else:
            print(f"✅ 积分增加正确: {actual_points_change}")

        # 检查流水记录数量
        expected_transaction_count = initial_count + 1
        if final_count != expected_transaction_count:
            print(f"❌ 积分流水记录数量错误: 期望{expected_transaction_count}, 实际{final_count}")
            success = False
        else:
            print(f"✅ 积分流水记录数量正确: {final_count}")

        # 检查流水记录详情
        transaction_details = session.execute(
            text("""
                SELECT id, amount, source_type, source_id, created_at
                FROM points_transactions
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"user_id": user_id}
        ).first()

        if transaction_details:
            print(f"最新流水记录: ID={transaction_details.id}, 金额={transaction_details.amount}, 来源={transaction_details.source_type}, 源ID={transaction_details.source_id}")

            # 验证流水记录内容
            if transaction_details.amount != expected_points:
                print(f"❌ 流水记录金额错误: 期望{expected_points}, 实际{transaction_details.amount}")
                success = False
            elif transaction_details.source_type != 'task_complete':
                print(f"❌ 流水记录来源类型错误: 期望task_complete, 实际{transaction_details.source_type}")
                success = False
            elif transaction_details.source_id != str(task.id):
                print(f"❌ 流水记录源ID错误: 期望{task.id}, 实际{transaction_details.source_id}")
                success = False
            else:
                print(f"✅ 流水记录内容正确")
        else:
            print(f"❌ 未找到流水记录")
            success = False

        if success:
            print(f"\n🎉 积分流水记录修复成功!")
        else:
            print(f"\n❌ 积分流水记录仍有问题")

        session.commit()
        return success

    except Exception as e:
        session.rollback()
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    test_points_transaction_fix()