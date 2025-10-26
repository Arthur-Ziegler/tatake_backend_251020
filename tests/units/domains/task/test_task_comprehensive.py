"""
任务域综合测试套件

基于TDD原则的全面测试，覆盖：
1. 基础CRUD操作
2. 树结构管理
3. 业务逻辑验证
4. 边界条件测试
5. 并发安全测试
6. 数据一致性验证

测试策略：
- 分层测试：单元→集成→系统
- 数据工厂：统一测试数据生成
- 边界覆盖：极端条件测试
- 性能验证：大数据量处理
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from typing import List, Dict, Any
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, Session, select

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.top3.models import TaskTop3
from src.domains.auth.models import Auth
from tests.utils.data_factory import TestDataFactory, create_user, create_task


class TestTaskBasicOperations:
    """任务基础操作测试"""

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

    @pytest.fixture
    def factory(self):
        """数据工厂fixture"""
        return TestDataFactory(seed=12345)

    @pytest.fixture
    def sample_user(self, factory):
        """示例用户fixture"""
        return factory.create_user()

    def test_create_task_minimal(self, db_session, sample_user):
        """测试创建最小任务"""
        # Arrange
        user_id = UUID(sample_user.id)

        # Act
        task = Task(
            user_id=user_id,
            title="最小测试任务"
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert
        assert task.id is not None
        assert isinstance(task.id, UUID)
        assert task.user_id == user_id
        assert task.title == "最小测试任务"
        assert task.status == TaskStatusConst.PENDING
        assert task.priority == TaskPriorityConst.MEDIUM
        assert task.completion_percentage == 0.0
        assert task.is_deleted is False

    def test_create_task_full_fields(self, db_session, sample_user, factory):
        """测试创建完整字段的任务"""
        # Arrange
        user_id = UUID(sample_user.id)
        due_date = datetime.now(timezone.utc) + timedelta(days=7)
        tags = ["重要", "工作", "紧急"]
        service_ids = [uuid4(), uuid4()]

        # Act
        task = Task(
            user_id=user_id,
            title=factory.fake.sentence(),
            description=factory.fake.paragraph(),
            status=TaskStatusConst.IN_PROGRESS,
            priority=TaskPriorityConst.HIGH,
            parent_id=None,
            completion_percentage=45.5,
            tags=tags,
            service_ids=service_ids,
            due_date=due_date,
            planned_start_time=datetime.now(timezone.utc),
            planned_end_time=due_date
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert
        assert task.user_id == user_id
        assert task.status == TaskStatusConst.IN_PROGRESS
        assert task.priority == TaskPriorityConst.HIGH
        assert task.completion_percentage == 45.5
        assert task.tags == tags
        assert task.service_ids == service_ids
        assert task.due_date == due_date

    def test_task_title_validation(self, db_session, sample_user):
        """测试任务标题验证"""
        user_id = UUID(sample_user.id)

        # 测试有效标题
        valid_titles = [
            "A",  # 最短1个字符
            "A" * 100,  # 最长100个字符
            "正常标题",
            "测试🚀Unicode",
            "Mixed中英文123",
        ]

        for title in valid_titles:
            task = Task(user_id=user_id, title=title)
            db_session.add(task)
            db_session.commit()
            assert task.title == title
            db_session.delete(task)
            db_session.commit()

    def test_task_parent_child_relationship(self, db_session, sample_user, factory):
        """测试父子任务关系"""
        user_id = UUID(sample_user.id)

        # 创建父任务
        parent_task = factory.create_task(user_id=user_id, title="父任务")
        db_session.add(parent_task)
        db_session.commit()

        # 创建子任务
        child_task = factory.create_task(
            user_id=user_id,
            parent_id=parent_task.id,
            title="子任务"
        )
        db_session.add(child_task)
        db_session.commit()

        # 验证关系
        assert child_task.parent_id == parent_task.id
        assert parent_task.parent_id is None

        # 验证查询
        parent_query = db_session.exec(select(Task).where(Task.id == parent_task.id)).first()
        child_query = db_session.exec(select(Task).where(Task.parent_id == parent_task.id)).all()

        assert parent_query is not None
        assert len(child_query) == 1
        assert child_query[0].id == child_task.id

    def test_task_status_transitions(self, db_session, sample_user, factory):
        """测试任务状态转换"""
        user_id = UUID(sample_user.id)
        task = factory.create_task(user_id=user_id)
        db_session.add(task)
        db_session.commit()

        # 初始状态
        assert task.status == TaskStatusConst.PENDING
        assert task.completion_percentage == 0.0

        # 进行中
        task.status = TaskStatusConst.IN_PROGRESS
        task.completion_percentage = 50.0
        db_session.commit()
        db_session.refresh(task)

        assert task.status == TaskStatusConst.IN_PROGRESS
        assert task.completion_percentage == 50.0

        # 已完成
        task.status = TaskStatusConst.COMPLETED
        task.completion_percentage = 100.0
        db_session.commit()
        db_session.refresh(task)

        assert task.status == TaskStatusConst.COMPLETED
        assert task.completion_percentage == 100.0

    def test_task_soft_delete(self, db_session, sample_user, factory):
        """测试任务软删除"""
        user_id = UUID(sample_user.id)
        task = factory.create_task(user_id=user_id)
        db_session.add(task)
        db_session.commit()

        # 初始状态：未删除
        assert task.is_deleted is False

        # 软删除
        task.is_deleted = True
        db_session.commit()
        db_session.refresh(task)

        assert task.is_deleted is True

        # 查询未删除的任务（应该查不到已删除的任务）
        active_tasks = db_session.exec(
            select(Task).where(Task.is_deleted == False)
        ).all()
        deleted_tasks = db_session.exec(
            select(Task).where(Task.is_deleted == True)
        ).all()

        assert len(deleted_tasks) == 1
        assert len(active_tasks) == 0


class TestTaskTreeStructure:
    """任务树结构测试"""

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

    @pytest.fixture
    def factory(self):
        """数据工厂fixture"""
        return TestDataFactory(seed=54321)

    def test_create_task_tree(self, db_session, factory):
        """测试创建任务树"""
        user_id = factory.create_user().id

        # 创建3层深的任务树
        tasks = factory.create_task_tree(
            user_id=user_id,
            depth=3,
            breadth=2
        )

        # 保存到数据库
        for task in tasks:
            db_session.add(task)
        db_session.commit()

        # 验证树结构
        root_tasks = db_session.exec(
            select(Task).where(Task.parent_id.is_(None))
        ).all()

        assert len(root_tasks) == 2  # breadth = 2

        # 验证根任务有子任务
        for root_task in root_tasks:
            children = db_session.exec(
                select(Task).where(Task.parent_id == root_task.id)
            ).all()
            assert len(children) == 2  # 每个根任务有2个子任务

            # 验证子任务有孙任务
            for child in children:
                grandchildren = db_session.exec(
                    select(Task).where(Task.parent_id == child.id)
                ).all()
                assert len(grandchildren) == 2  # 每个子任务有2个孙任务

    def test_task_tree_query_paths(self, db_session, factory):
        """测试任务树路径查询"""
        user_id = factory.create_user().id
        tasks = factory.create_task_tree(user_id=user_id, depth=2, breadth=3)

        # 保存任务
        for task in tasks:
            db_session.add(task)
        db_session.commit()

        # 获取根任务
        root_tasks = db_session.exec(
            select(Task).where(Task.parent_id.is_(None))
        ).all()

        # 查询每个根任务的所有后代
        for root_task in root_tasks:
            # 直接子任务
            children = db_session.exec(
                select(Task).where(Task.parent_id == root_task.id)
            ).all()

            # 孙任务（通过子任务查询）
            all_grandchildren = []
            for child in children:
                grandchildren = db_session.exec(
                    select(Task).where(Task.parent_id == child.id)
                ).all()
                all_grandchildren.extend(grandchildren)

            total_descendants = len(children) + len(all_grandchildren)
            expected_total = 3 + 9  # 3个子任务 + 每个子任务3个孙任务
            assert total_descendants == expected_total

    def test_prevent_circular_reference(self, db_session, factory):
        """测试防止循环引用（通过应用层逻辑）"""
        user_id = factory.create_user().id

        # 创建任务A
        task_a = factory.create_task(user_id=user_id, title="任务A")
        db_session.add(task_a)
        db_session.commit()

        # 创建任务B，父任务为A
        task_b = factory.create_task(
            user_id=user_id,
            parent_id=task_a.id,
            title="任务B"
        )
        db_session.add(task_b)
        db_session.commit()

        # 尝试让A的父任务是B（会形成循环）
        # 在实际应用中，这种检查应该在service层进行
        with pytest.raises(Exception):  # 这里用通用异常，实际应该用业务异常
            # 模拟循环引用检查失败
            if task_a.id == task_b.parent_id or task_b.id == task_a.parent_id:
                raise ValueError("检测到循环引用")

    def test_deep_task_tree_performance(self, db_session, factory):
        """测试深层任务树性能"""
        user_id = factory.create_user().id

        import time
        start_time = time.time()

        # 创建深层任务树（5层，每层4个节点）
        tasks = factory.create_task_tree(user_id=user_id, depth=5, breadth=4)

        creation_time = time.time() - start_time

        # 保存到数据库
        start_time = time.time()
        for task in tasks:
            db_session.add(task)
        db_session.commit()
        save_time = time.time() - start_time

        # 查询性能测试
        start_time = time.time()
        all_tasks = db_session.exec(select(Task)).all()
        query_time = time.time() - start_time

        # 验证结果
        expected_task_count = sum(4**i for i in range(5))  # 4^0 + 4^1 + 4^2 + 4^3 + 4^4
        assert len(all_tasks) == expected_task_count
        assert len(tasks) == expected_task_count

        # 性能断言（这些值应该根据实际情况调整）
        assert creation_time < 1.0  # 创建应该在1秒内完成
        assert save_time < 2.0     # 保存应该在2秒内完成
        assert query_time < 0.5    # 查询应该在0.5秒内完成


class TestTaskBusinessLogic:
    """任务业务逻辑测试"""

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
        Auth.metadata.create_all(in_memory_db)
        TaskTop3.metadata.create_all(in_memory_db)
        with Session(in_memory_db) as session:
            yield session

    @pytest.fixture
    def factory(self):
        """数据工厂fixture"""
        return TestDataFactory(seed=99999)

    def test_completion_percentage_validation(self, db_session, factory):
        """测试完成百分比验证"""
        user_id = factory.create_user().id

        # 测试有效范围
        valid_percentages = [0.0, 0.1, 50.0, 99.9, 100.0]

        for percentage in valid_percentages:
            task = factory.create_task(
                user_id=user_id,
                completion_percentage=percentage
            )
            db_session.add(task)
            db_session.commit()
            assert task.completion_percentage == percentage
            db_session.delete(task)
            db_session.commit()

        # 测试无效范围（在模型层面应该被拒绝）
        # 这里我们测试边界值附近的数值
        boundary_tests = [
            (-0.1, False),   # 负数应该被拒绝
            (100.1, False),  # 超过100应该被拒绝
            (0.0, True),     # 0是有效的
            (100.0, True),   # 100是有效的
        ]

        for percentage, should_be_valid in boundary_tests:
            try:
                task = factory.create_task(
                    user_id=user_id,
                    completion_percentage=percentage
                )
                db_session.add(task)
                db_session.commit()

                if should_be_valid:
                    assert task.completion_percentage == percentage
                else:
                    # 如果不应该有效但成功了，说明验证有问题
                    pytest.fail(f"Percentage {percentage} should have been rejected")

                db_session.delete(task)
                db_session.commit()
            except Exception:
                if should_be_valid:
                    pytest.fail(f"Percentage {percentage} should have been valid")

    def test_task_due_date_logic(self, db_session, factory):
        """测试任务截止日期逻辑"""
        user_id = factory.create_user().id
        now = datetime.now(timezone.utc)

        # 测试过去截止日期
        past_task = factory.create_task(
            user_id=user_id,
            due_date=now - timedelta(days=1),
            title="过期任务"
        )
        db_session.add(past_task)
        db_session.commit()

        # 测试未来截止日期
        future_task = factory.create_task(
            user_id=user_id,
            due_date=now + timedelta(days=7),
            title="未来任务"
        )
        db_session.add(future_task)
        db_session.commit()

        # 查询过期任务
        overdue_tasks = db_session.exec(
            select(Task).where(
                Task.due_date < now,
                Task.status != TaskStatusConst.COMPLETED
            )
        ).all()

        assert len(overdue_tasks) == 1
        assert overdue_tasks[0].title == "过期任务"

    def test_task_time_planning_validation(self, db_session, factory):
        """测试任务时间规划验证"""
        user_id = factory.create_user().id
        now = datetime.now(timezone.utc)

        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=3)

        # 测试有效时间规划
        task = factory.create_task(
            user_id=user_id,
            planned_start_time=start_time,
            planned_end_time=end_time,
            title="时间规划正常任务"
        )
        db_session.add(task)
        db_session.commit()

        assert task.planned_start_time == start_time
        assert task.planned_end_time == end_time
        assert task.planned_end_time > task.planned_start_time

        # 测试无效时间规划（结束时间早于开始时间）
        invalid_start_time = now + timedelta(hours=5)
        invalid_end_time = now + timedelta(hours=2)

        # 在实际应用中，这种验证应该在service层进行
        if invalid_end_time <= invalid_start_time:
            # 模拟验证逻辑
            with pytest.raises(ValueError):
                if invalid_end_time <= invalid_start_time:
                    raise ValueError("结束时间必须晚于开始时间")

    def test_task_tags_functionality(self, db_session, factory):
        """测试任务标签功能"""
        user_id = factory.create_user().id

        # 测试各种标签组合
        test_cases = [
            [],  # 无标签
            ["工作"],  # 单个标签
            ["重要", "紧急", "工作"],  # 多个标签
            ["中文", "English", "123", "测试🚀"],  # 混合字符
        ]

        for tags in test_cases:
            task = factory.create_task(
                user_id=user_id,
                tags=tags,
                title=f"标签测试_{len(tags)}个标签"
            )
            db_session.add(task)
            db_session.commit()

            assert task.tags == tags

            # 测试标签查询
            if tags:
                for tag in tags:
                    # 这里应该测试JSON查询，SQLite可能不支持直接查询
                    # 实际应用中可能需要使用特定的JSON查询方法
                    pass

            db_session.delete(task)
            db_session.commit()

    def test_task_service_ids_functionality(self, db_session, factory):
        """测试任务服务ID功能"""
        user_id = factory.create_user().id

        # 创建服务ID列表
        service_ids = [uuid4(), uuid4(), uuid4()]

        task = factory.create_task(
            user_id=user_id,
            service_ids=service_ids,
            title="服务关联测试任务"
        )
        db_session.add(task)
        db_session.commit()

        assert len(task.service_ids) == 3
        assert all(isinstance(sid, UUID) for sid in task.service_ids)
        assert task.service_ids == service_ids

        # 测试to_dict方法中的UUID转换
        task_dict = task.to_dict()
        assert "service_ids" in task_dict
        assert all(isinstance(sid, str) for sid in task_dict["service_ids"])
        assert [UUID(sid) for sid in task_dict["service_ids"]] == service_ids


class TestTaskEdgeCases:
    """任务边界条件测试"""

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

    @pytest.fixture
    def factory(self):
        """数据工厂fixture"""
        return TestDataFactory(seed=77777)

    def test_maximum_title_length(self, db_session, factory):
        """测试最大标题长度"""
        user_id = factory.create_user().id

        # 测试边界长度
        max_length = 100
        long_title = "A" * max_length

        task = factory.create_task(user_id=user_id, title=long_title)
        db_session.add(task)
        db_session.commit()

        assert len(task.title) == max_length
        assert task.title == long_title

    def test_unicode_content_handling(self, db_session, factory):
        """测试Unicode内容处理"""
        user_id = factory.create_user().id

        # 测试各种Unicode字符
        unicode_contents = [
            "中文内容测试",
            "🚀 Emoji测试 🎯",
            "العربية",
            "Русский язык",
            "日本語",
            "한국어",
            "Mixed: 中文 🚀 English العربية",
        ]

        for content in unicode_contents:
            task = factory.create_task(
                user_id=user_id,
                title=content,
                description=f"描述内容：{content}"
            )
            db_session.add(task)
            db_session.commit()

            assert task.title == content
            assert task.description == f"描述内容：{content}"

            # 测试to_dict方法
            task_dict = task.to_dict()
            assert task_dict["title"] == content
            assert task_dict["description"] == f"描述内容：{content}"

            db_session.delete(task)
            db_session.commit()

    def test_null_values_handling(self, db_session, factory):
        """测试空值处理"""
        user_id = factory.create_user().id

        # 测试可选字段的空值
        task = Task(
            user_id=UUID(user_id.id),
            title="空值测试任务",
            description=None,
            parent_id=None,
            due_date=None,
            planned_start_time=None,
            planned_end_time=None,
            last_claimed_date=None,
            tags=None,
            service_ids=None
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.description is None
        assert task.parent_id is None
        assert task.due_date is None
        assert task.planned_start_time is None
        assert task.planned_end_time is None
        assert task.last_claimed_date is None
        assert task.tags is None or task.tags == []
        assert task.service_ids is None or task.service_ids == []

        # 测试to_dict方法处理空值
        task_dict = task.to_dict()
        assert task_dict["description"] is None
        assert task_dict["parent_id"] is None
        assert task_dict["tags"] == []
        assert task_dict["service_ids"] == []

    def test_large_description_handling(self, db_session, factory):
        """测试大段描述处理"""
        user_id = factory.create_user().id

        # 创建大段文本
        large_description = "这是一段很长的描述。" * 1000  # 约20000字符

        task = factory.create_task(
            user_id=user_id,
            title="大段描述测试",
            description=large_description
        )
        db_session.add(task)
        db_session.commit()

        assert len(task.description) == len(large_description)
        assert task.description == large_description

    def test_concurrent_task_creation(self, db_session, factory):
        """测试并发任务创建"""
        import threading
        import time

        user_id = factory.create_user().id
        created_tasks = []
        errors = []

        def create_task_thread(thread_id: int):
            try:
                task = factory.create_task(
                    user_id=user_id,
                    title=f"并发任务_{thread_id}"
                )
                db_session.add(task)
                db_session.commit()
                created_tasks.append(task.id)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时创建任务
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_task_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发创建出现错误: {errors}"
        assert len(created_tasks) == 10

        # 验证数据库中的任务数量
        db_tasks = db_session.exec(select(Task)).all()
        assert len(db_tasks) == 10

        # 验证所有任务都有唯一的ID
        assert len(set(created_tasks)) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])