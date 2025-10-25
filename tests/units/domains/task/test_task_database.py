"""
Task领域数据库操作测试

测试Task领域的数据库相关操作，包括：
1. 数据库连接
2. 基础SQL操作
3. 数据库初始化

快速提升覆盖率的简单测试。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from sqlalchemy import text
from sqlmodel import Session


@pytest.mark.unit
class TestTaskDatabase:
    """Task数据库操作测试类"""

    def test_database_connection(self, test_db_session):
        """测试数据库连接"""
        assert test_db_session is not None
        assert isinstance(test_db_session, Session)

    def test_execute_simple_query(self, test_db_session):
        """测试简单SQL查询执行"""
        result = test_db_session.execute(text("SELECT 1 as test_value"))
        row = result.first()
        assert row.test_value == 1

    def test_check_tasks_table_exists(self, test_db_session):
        """检查tasks表是否存在"""
        result = test_db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        )
        row = result.first()
        assert row is not None
        assert row.name == "tasks"

    def test_check_tasks_table_columns(self, test_db_session):
        """检查tasks表的列"""
        result = test_db_session.execute(text("PRAGMA table_info(tasks)"))
        columns = result.fetchall()

        # 验证关键列存在
        column_names = [col.name for col in columns]
        expected_columns = [
            'id', 'user_id', 'title', 'description', 'status',
            'priority', 'completion_percentage', 'created_at',
            'updated_at', 'last_claimed_date'
        ]

        for expected_col in expected_columns:
            assert expected_col in column_names

    def test_insert_and_select_task(self, test_db_session):
        """测试插入和查询任务"""
        from datetime import datetime, timezone
        from uuid import uuid4

        task_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # 插入任务
        test_db_session.execute(
            text("""
                INSERT INTO tasks (id, user_id, title, status, created_at, updated_at)
                VALUES (:id, :user_id, :title, :status, :created_at, :updated_at)
            """),
            {
                "id": task_id,
                "user_id": user_id,
                "title": "数据库测试任务",
                "status": "pending",
                "created_at": now,
                "updated_at": now
            }
        )
        test_db_session.commit()

        # 查询任务
        result = test_db_session.execute(
            text("SELECT * FROM tasks WHERE id = :id"),
            {"id": task_id}
        )
        row = result.first()

        assert row is not None
        assert row.title == "数据库测试任务"
        assert row.status == "pending"
        assert row.user_id == user_id

    def test_update_task_status(self, test_db_session):
        """测试更新任务状态"""
        from datetime import datetime, timezone
        from uuid import uuid4

        # 创建任务
        task_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        test_db_session.execute(
            text("""
                INSERT INTO tasks (id, user_id, title, status, created_at, updated_at)
                VALUES (:id, :user_id, :title, :status, :created_at, :updated_at)
            """),
            {
                "id": task_id,
                "user_id": user_id,
                "title": "状态更新测试",
                "status": "pending",
                "created_at": now,
                "updated_at": now
            }
        )
        test_db_session.commit()

        # 更新状态
        updated_time = datetime.now(timezone.utc)
        test_db_session.execute(
            text("""
                UPDATE tasks
                SET status = :status, updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": task_id,
                "status": "completed",
                "updated_at": updated_time
            }
        )
        test_db_session.commit()

        # 验证更新
        result = test_db_session.execute(
            text("SELECT status, updated_at FROM tasks WHERE id = :id"),
            {"id": task_id}
        )
        row = result.first()

        assert row.status == "completed"

    def test_delete_task(self, test_db_session):
        """测试删除任务"""
        from datetime import datetime, timezone
        from uuid import uuid4

        # 创建任务
        task_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        test_db_session.execute(
            text("""
                INSERT INTO tasks (id, user_id, title, status, created_at, updated_at)
                VALUES (:id, :user_id, :title, :status, :created_at, :updated_at)
            """),
            {
                "id": task_id,
                "user_id": user_id,
                "title": "删除测试任务",
                "status": "pending",
                "created_at": now,
                "updated_at": now
            }
        )
        test_db_session.commit()

        # 验证任务存在
        result = test_db_session.execute(
            text("SELECT COUNT(*) as count FROM tasks WHERE id = :id"),
            {"id": task_id}
        )
        assert result.first().count == 1

        # 删除任务
        test_db_session.execute(
            text("DELETE FROM tasks WHERE id = :id"),
            {"id": task_id}
        )
        test_db_session.commit()

        # 验证任务已删除
        result = test_db_session.execute(
            text("SELECT COUNT(*) as count FROM tasks WHERE id = :id"),
            {"id": task_id}
        )
        assert result.first().count == 0

    def test_count_user_tasks(self, test_db_session):
        """测试统计用户任务数量"""
        from datetime import datetime, timezone
        from uuid import uuid4

        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # 创建多个任务
        for i in range(3):
            task_id = str(uuid4())
            test_db_session.execute(
                text("""
                    INSERT INTO tasks (id, user_id, title, status, created_at, updated_at)
                    VALUES (:id, :user_id, :title, :status, :created_at, :updated_at)
                """),
                {
                    "id": task_id,
                    "user_id": user_id,
                    "title": f"任务 {i+1}",
                    "status": "pending",
                    "created_at": now,
                    "updated_at": now
                }
            )
        test_db_session.commit()

        # 统计任务数量
        result = test_db_session.execute(
            text("SELECT COUNT(*) as count FROM tasks WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        count = result.first().count
        assert count == 3

    def test_transaction_rollback(self, test_db_session):
        """测试事务回滚"""
        from datetime import datetime, timezone
        from uuid import uuid4

        user_id = str(uuid4())
        task_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # 开始事务
        test_db_session.begin()

        try:
            # 插入任务
            test_db_session.execute(
                text("""
                    INSERT INTO tasks (id, user_id, title, status, created_at, updated_at)
                    VALUES (:id, :user_id, :title, :status, :created_at, :updated_at)
                """),
                {
                    "id": task_id,
                    "user_id": user_id,
                    "title": "事务测试",
                    "status": "pending",
                    "created_at": now,
                    "updated_at": now
                }
            )

            # 模拟错误
            raise ValueError("测试事务回滚")

        except ValueError:
            # 回滚事务
            test_db_session.rollback()

        # 验证任务没有被插入
        result = test_db_session.execute(
            text("SELECT COUNT(*) as count FROM tasks WHERE id = :id"),
            {"id": task_id}
        )
        count = result.first().count
        assert count == 0