"""
Task Service层测试

测试TaskService的业务逻辑，确保业务规则正确执行。

测试覆盖：
1. 任务创建业务逻辑
2. 任务更新业务逻辑
3. 循环引用检测
4. 时间范围验证
5. 级联删除逻辑

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlmodel import Session

from src.domains.task.service import TaskService
from src.domains.task.schemas import CreateTaskRequest, UpdateTaskRequest, TaskListQuery
from src.domains.task.models import TaskStatus, TaskPriority
from src.domains.task.exceptions import (
    TaskNotFoundException,
    CircularReferenceException,
    InvalidTimeRangeException
)
from src.domains.auth.models import Auth


class TestTaskService:
    """TaskService测试类"""

    def test_create_task_success(self, test_db_session: Session, test_user: Auth):
        """测试成功创建任务"""
        # 准备请求数据
        request = CreateTaskRequest(
            title="新任务",
            description="任务描述",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM
        )

        # 执行操作
        service = TaskService(test_db_session)
        response = service.create_task(request, test_user.id)

        # 验证结果
        assert response.id is not None
        assert response.title == "新任务"
        assert response.user_id == test_user.id
        assert response.status == TaskStatus.PENDING
        assert response.priority == TaskPriority.MEDIUM

    def test_create_task_with_invalid_time_range(self, test_db_session: Session, test_user: Auth):
        """测试创建任务时时间范围无效"""
        # 准备无效时间范围的请求数据
        start_time = datetime.now(timezone.utc)
        end_time = start_time - timedelta(hours=1)  # 结束时间早于开始时间

        request = CreateTaskRequest(
            title="无效时间任务",
            planned_start_time=start_time,
            planned_end_time=end_time
        )

        # 执行操作并验证异常
        service = TaskService(test_db_session)
        with pytest.raises(InvalidTimeRangeException):
            service.create_task(request, test_user.id)

    def test_get_task_success(self, test_db_session: Session, test_task: Task):
        """测试成功获取任务"""
        # 执行操作
        service = TaskService(test_db_session)
        response = service.get_task(test_task.id, test_task.user_id)

        # 验证结果
        assert response.id == test_task.id
        assert response.title == test_task.title

    def test_get_task_not_found(self, test_db_session: Session, test_user: Auth):
        """测试获取不存在的任务"""
        # 执行操作并验证异常
        service = TaskService(test_db_session)
        with pytest.raises(TaskNotFoundException):
            service.get_task(uuid4(), test_user.id)

    def test_update_task_success(self, test_db_session: Session, test_task: Task):
        """测试成功更新任务"""
        # 准备更新请求
        request = UpdateTaskRequest(
            title="更新后的标题",
            status=TaskStatus.COMPLETED
        )

        # 执行操作
        service = TaskService(test_db_session)
        response = service.update_task(test_task.id, request, test_task.user_id)

        # 验证结果
        assert response.id == test_task.id
        assert response.title == "更新后的标题"
        assert response.status == TaskStatus.COMPLETED

    def test_delete_task_success(self, test_db_session: Session, test_task: Task):
        """测试成功删除任务"""
        # 执行操作
        service = TaskService(test_db_session)
        response = service.delete_task(test_task.id, test_task.user_id)

        # 验证结果
        assert response.deleted_task_id == test_task.id
        assert response.deleted_count >= 1

    def test_get_task_list_success(self, test_db_session: Session, test_task_list: list[Task], test_user: Auth):
        """测试成功获取任务列表"""
        # 准备查询请求
        query = TaskListQuery(
            page=1,
            page_size=10,
            sort_by="created_at",
            sort_order="desc"
        )

        # 执行操作
        service = TaskService(test_db_session)
        response = service.get_task_list(query, test_user.id)

        # 验证结果
        assert len(response.tasks) > 0
        assert response.pagination.current_page == 1
        assert response.pagination.page_size == 10
        assert response.pagination.total_count > 0

    def test_check_circular_reference(self, test_db_session: Session, test_task_tree: dict, test_user: Auth):
        """测试循环引用检测"""
        root_task = test_task_tree['root']
        child_task = test_task_tree['child1']

        # 执行操作：尝试将根任务设置为子任务的子任务（会形成循环）
        service = TaskService(test_db_session)
        has_circular = service.check_circular_reference(
            task_id=root_task.id,
            new_parent_id=child_task.id,
            user_id=test_user.id
        )

        # 验证结果
        assert has_circular is True

    def test_check_no_circular_reference(self, test_db_session: Session, test_task_tree: dict, test_user: Auth):
        """测试无循环引用的情况"""
        root_task = test_task_tree['root']
        child_task = test_task_tree['child1']

        # 执行操作：将子任务设置为根任务的子任务（不会形成循环）
        service = TaskService(test_db_session)
        has_circular = service.check_circular_reference(
            task_id=child_task.id,
            new_parent_id=root_task.id,
            user_id=test_user.id
        )

        # 验证结果
        assert has_circular is False