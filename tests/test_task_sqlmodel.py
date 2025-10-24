"""
Task领域SQLModel测试

使用SQLModel而非直接SQL来测试Task领域功能。
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

# 导入模型
from src.domains.auth.models import Auth
from src.domains.task.models import Task


@pytest.mark.integration
def test_sqlmodel_task_creation(task_db_session):
    """使用SQLModel创建任务"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 创建任务
    task_id = str(uuid4())
    task = Task(
        id=task_id,
        user_id=auth_id,
        title="SQLModel测试任务",
        status="pending",
        priority="medium",
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(task)
    task_db_session.commit()

    # 验证任务已创建
    from sqlalchemy import text
    result = task_db_session.execute(text("SELECT COUNT(*) FROM tasks WHERE id = :id"), {"id": task_id})
    count = result.scalar()
    assert count == 1

    # 验证任务数据
    result = task_db_session.execute(text("SELECT title, status, priority, is_deleted FROM tasks WHERE id = :id"), {"id": task_id})
    data = result.fetchone()
    assert data[0] == "SQLModel测试任务"
    assert data[1] == "pending"
    assert data[2] == "medium"
    assert data[3] in [False, 0]  # SQLite可能返回False或0


@pytest.mark.integration
def test_sqlmodel_task_with_description(task_db_session):
    """使用SQLModel创建带描述的任务"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 创建带描述的任务
    task_id = str(uuid4())
    task = Task(
        id=task_id,
        user_id=auth_id,
        title="SQLModel复杂任务",
        description="这是一个使用SQLModel创建的复杂任务",
        status="in_progress",
        priority="high",
        tags=["重要", "紧急"],
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(task)
    task_db_session.commit()

    # 验证任务详情
    from sqlalchemy import text
    result = task_db_session.execute(text("SELECT title, description, status, priority, is_deleted FROM tasks WHERE id = :id"), {"id": task_id})
    task_data = result.fetchone()

    assert task_data is not None
    assert task_data[0] == "SQLModel复杂任务"
    assert task_data[1] == "这是一个使用SQLModel创建的复杂任务"
    assert task_data[2] == "in_progress"
    assert task_data[3] == "high"
    assert task_data[4] in [False, 0]  # SQLite可能返回False或0


@pytest.mark.integration
def test_sqlmodel_task_status_update(task_db_session):
    """使用SQLModel更新任务状态"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 创建任务
    task_id = str(uuid4())
    task = Task(
        id=task_id,
        user_id=auth_id,
        title="SQLModel状态测试任务",
        status="pending",
        priority="medium",
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(task)
    task_db_session.commit()

    # 更新任务状态
    task.status = "completed"
    task.updated_at = datetime.now(timezone.utc)
    task_db_session.commit()

    # 验证状态更新
    from sqlalchemy import text
    result = task_db_session.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": task_id})
    status = result.fetchone()

    assert status is not None
    assert status[0] == "completed"


@pytest.mark.integration
def test_sqlmodel_task_soft_delete(task_db_session):
    """使用SQLModel测试任务软删除"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 创建任务
    task_id = str(uuid4())
    task = Task(
        id=task_id,
        user_id=auth_id,
        title="SQLModel软删除测试任务",
        status="pending",
        priority="low",
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(task)
    task_db_session.commit()

    # 验证任务存在且未删除
    from sqlalchemy import text
    result = task_db_session.execute(text("SELECT is_deleted FROM tasks WHERE id = :id"), {"id": task_id})
    original_data = result.fetchone()
    assert original_data is not None
    assert original_data[0] in [False, 0]  # SQLite可能返回False或0

    # 软删除任务
    task.is_deleted = True
    task.updated_at = datetime.now(timezone.utc)
    task_db_session.commit()

    # 验证软删除
    result = task_db_session.execute(text("SELECT is_deleted FROM tasks WHERE id = :id"), {"id": task_id})
    deleted_data = result.fetchone()
    assert deleted_data is not None
    assert deleted_data[0] in [True, 1]  # SQLite可能返回True或1


@pytest.mark.integration
def test_sqlmodel_task_completion_percentage(task_db_session):
    """使用SQLModel测试任务完成度"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 创建带完成度的任务
    task_id = str(uuid4())
    task = Task(
        id=task_id,
        user_id=auth_id,
        title="SQLModel完成度测试任务",
        status="in_progress",
        priority="high",
        completion_percentage=75.5,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(task)
    task_db_session.commit()

    # 验证完成度
    from sqlalchemy import text
    result = task_db_session.execute(text("SELECT completion_percentage FROM tasks WHERE id = :id"), {"id": task_id})
    completion_data = result.fetchone()

    assert completion_data is not None
    assert completion_data[0] == 75.5


@pytest.mark.performance
def test_sqlmodel_batch_task_creation(task_db_session):
    """使用SQLModel测试批量任务创建性能"""
    import time

    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    start_time = time.time()

    # 批量创建任务
    tasks = []
    for i in range(10):
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            user_id=auth_id,
            title=f"SQLModel性能测试任务 #{i+1}",
            status="pending",
            priority="medium",
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        tasks.append(task)
        task_db_session.add(task)

    task_db_session.commit()

    end_time = time.time()
    execution_time = end_time - start_time

    # 验证性能合理
    assert execution_time < 1.0  # 应该在1秒内完成

    # 验证所有任务都已创建
    from sqlalchemy import text
    result = task_db_session.execute(text("SELECT COUNT(*) FROM tasks WHERE user_id = :user_id"), {"user_id": auth_id})
    task_count = result.scalar()
    assert task_count == 10


@pytest.mark.integration
def test_sqlmodel_task_priority_enum(task_db_session):
    """使用SQLModel测试任务优先级枚举"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 测试不同优先级
    priorities = ["low", "medium", "high"]
    for priority in priorities:
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            user_id=auth_id,
            title=f"SQLModel优先级测试任务-{priority}",
            status="pending",
            priority=priority,
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        task_db_session.add(task)

    task_db_session.commit()

    # 验证所有优先级都已创建
    from sqlalchemy import text
    for priority in priorities:
        result = task_db_session.execute(text("SELECT COUNT(*) FROM tasks WHERE user_id = :user_id AND priority = :priority"), {"user_id": auth_id, "priority": priority})
        count = result.scalar()
        assert count == 1


@pytest.mark.integration
def test_sqlmodel_task_status_enum(task_db_session):
    """使用SQLModel测试任务状态枚举"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 测试不同状态
    statuses = ["pending", "in_progress", "completed"]
    for status in statuses:
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            user_id=auth_id,
            title=f"SQLModel状态测试任务-{status}",
            status=status,
            priority="medium",
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        task_db_session.add(task)

    task_db_session.commit()

    # 验证所有状态都已创建
    from sqlalchemy import text
    for status in statuses:
        result = task_db_session.execute(text("SELECT COUNT(*) FROM tasks WHERE user_id = :user_id AND status = :status"), {"user_id": auth_id, "status": status})
        count = result.scalar()
        assert count == 1


@pytest.mark.integration
def test_sqlmodel_task_user_relationship(task_db_session):
    """使用SQLModel测试任务与用户的关联关系"""
    # 创建用户
    auth_id = str(uuid4())
    auth_user = Auth(
        id=auth_id,
        wechat_openid=None,
        is_guest=True,
        jwt_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    task_db_session.add(auth_user)
    task_db_session.commit()

    # 创建多个任务
    task_ids = []
    for i in range(3):
        task_id = str(uuid4())
        task_ids.append(task_id)
        task = Task(
            id=task_id,
            user_id=auth_id,
            title=f"SQLModel关联测试任务 #{i+1}",
            status="pending",
            priority="medium",
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        task_db_session.add(task)

    task_db_session.commit()

    # 验证任务已创建
    from sqlalchemy import text
    result = task_db_session.execute(text("SELECT COUNT(*) FROM tasks WHERE user_id = :user_id"), {"user_id": auth_id})
    task_count = result.scalar()
    assert task_count == 3

    # 验证用户存在
    result = task_db_session.execute(text("SELECT COUNT(*) FROM auth WHERE id = :id"), {"id": auth_id})
    user_count = result.scalar()
    assert user_count == 1

    # 验证每个任务都属于正确的用户
    for task_id in task_ids:
        result = task_db_session.execute(text("SELECT user_id FROM tasks WHERE id = :id"), {"id": task_id})
        user_id = result.fetchone()[0]
        assert user_id == auth_id