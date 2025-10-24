#!/usr/bin/env python3
"""
调试多级父任务更新问题
"""

import uuid
from datetime import datetime, timezone

from src.domains.task.service import TaskService
from src.domains.task.repository import TaskRepository
from src.domains.points.service import PointsService
from src.database import get_db_session
from src.domains.task.models import TaskStatusConst

def debug_parent_update():
    """调试多级父任务更新"""
    session = get_db_session()
    try:
        # 初始化服务
        task_repository = TaskRepository(session)
        points_service = PointsService(session)
        task_service = TaskService(session, points_service)

        user_id = str(uuid.uuid4())
        print(f"用户ID: {user_id}")

        # 创建三层任务树
        grandparent = task_repository.create({
            "user_id": user_id,
            "title": "祖父任务",
            "status": TaskStatusConst.PENDING
        })
        print(f"祖父任务创建: {grandparent.id}")

        parent = task_repository.create({
            "user_id": user_id,
            "title": "父任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": grandparent.id
        })
        print(f"父任务创建: {parent.id}, 父任务: {parent.parent_id}")

        child1 = task_repository.create({
            "user_id": user_id,
            "title": "子任务1",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })
        print(f"子任务1创建: {child1.id}, 父任务: {child1.parent_id}")

        child2 = task_repository.create({
            "user_id": user_id,
            "title": "子任务2",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })
        print(f"子任务2创建: {child2.id}, 父任务: {child2.parent_id}")

        print("\n=== 任务树结构 ===")
        print(f"grandparent ({grandparent.id})")
        print(f"  └── parent ({parent.id})")
        print(f"      ├── child1 ({child1.id})")
        print(f"      └── child2 ({child2.id})")

        # 完成子任务1
        print(f"\n=== 完成子任务1 ===")
        result = task_service.complete_task(user_id, child1.id)
        print(f"任务完成结果: {result}")

        # 检查父任务链
        print(f"\n=== 检查父任务链 ===")
        child1_check = task_repository.get_by_id(child1.id, user_id)
        print(f"子任务1状态: {child1_check.status}, 完成度: {child1_check.completion_percentage}")

        parent_check = task_repository.get_by_id(parent.id, user_id)
        print(f"父任务状态: {parent_check.status}, 完成度: {parent_check.completion_percentage}")

        grandparent_check = task_repository.get_by_id(grandparent.id, user_id)
        print(f"祖父任务状态: {grandparent_check.status}, 完成度: {grandparent_check.completion_percentage}")

        # 手动调用父任务更新
        print(f"\n=== 手动调用父任务更新 ===")
        parent_update_result = task_service.update_parent_completion_percentage(user_id, child1.id)
        print(f"父任务更新结果: {parent_update_result}")

        # 再次检查
        parent_check_after = task_repository.get_by_id(parent.id, user_id)
        print(f"父任务更新后: 完成度 {parent_check_after.completion_percentage}")

        grandparent_check_after = task_repository.get_by_id(grandparent.id, user_id)
        print(f"祖父任务更新后: 完成度 {grandparent_check_after.completion_percentage}")

        session.commit()

    except Exception as e:
        session.rollback()
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_parent_update()