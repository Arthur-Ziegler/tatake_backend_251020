"""
任务域简单测试

验证基础功能正常工作
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, Session, select

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst


class TestTaskSimple:
    """任务简单测试"""

    @pytest.fixture
    def in_memory_db(self):
        """内存数据库fixture"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        return engine

    @pytest.fixture
    def db_session(self, in_memory_db):
        """数据库会话fixture"""
        Task.metadata.create_all(in_memory_db)
        with Session(in_memory_db) as session:
            yield session

    def test_create_task_simple(self, db_session):
        """测试创建简单任务"""
        # 创建任务
        user_id = uuid4()
        task = Task(
            user_id=user_id,
            title="测试任务"
        )

        # 保存到数据库
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # 验证结果
        assert task.id is not None
        assert isinstance(task.id, UUID)
        assert task.user_id == user_id
        assert task.title == "测试任务"
        assert task.status == TaskStatusConst.PENDING
        assert task.priority == TaskPriorityConst.MEDIUM
        assert task.completion_percentage == 0.0
        assert task.is_deleted is False

    def test_task_fields(self, db_session):
        """测试任务字段"""
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        task = Task(
            user_id=user_id,
            title="完整字段测试",
            description="这是一个描述",
            status=TaskStatusConst.IN_PROGRESS,
            priority=TaskPriorityConst.HIGH,
            completion_percentage=75.5,
            tags=["工作", "重要"],
            due_date=now
        )

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # 验证所有字段
        assert task.title == "完整字段测试"
        assert task.description == "这是一个描述"
        assert task.status == TaskStatusConst.IN_PROGRESS
        assert task.priority == TaskPriorityConst.HIGH
        assert task.completion_percentage == 75.5
        assert task.tags == ["工作", "重要"]
        # SQLite不保存时区信息，所以需要比较不带时区的datetime
        assert task.due_date.replace(tzinfo=None) == now.replace(tzinfo=None)

    def test_task_parent_child(self, db_session):
        """测试父子任务关系"""
        user_id = uuid4()

        # 创建父任务
        parent_task = Task(
            user_id=user_id,
            title="父任务"
        )
        db_session.add(parent_task)
        db_session.commit()

        # 创建子任务
        child_task = Task(
            user_id=user_id,
            parent_id=parent_task.id,
            title="子任务"
        )
        db_session.add(child_task)
        db_session.commit()

        # 验证关系
        assert child_task.parent_id == parent_task.id
        assert parent_task.parent_id is None

        # 查询验证
        parent_query = db_session.exec(select(Task).where(Task.id == parent_task.id)).first()
        children_query = db_session.exec(select(Task).where(Task.parent_id == parent_task.id)).all()

        assert parent_query is not None
        assert len(children_query) == 1
        assert children_query[0].id == child_task.id

    def test_task_to_dict(self, db_session):
        """测试任务转字典"""
        user_id = uuid4()
        service_uuid = uuid4()
        task = Task(
            user_id=user_id,
            title="字典转换测试",
            description="测试描述",
            tags=["测试"],
            service_ids=[service_uuid]
        )

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)  # 确保从数据库重新加载

        # 转换为字典
        task_dict = task.to_dict()

        # 验证转换结果
        assert isinstance(task_dict, dict)
        assert task_dict["id"] == str(task.id)
        assert task_dict["user_id"] == str(user_id)
        assert task_dict["title"] == "字典转换测试"
        assert task_dict["description"] == "测试描述"
        assert task_dict["tags"] == ["测试"]
        assert isinstance(task_dict["service_ids"], list)
        assert len(task_dict["service_ids"]) == 1
        assert isinstance(task_dict["service_ids"][0], str)
        assert task_dict["service_ids"][0] == str(service_uuid)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])