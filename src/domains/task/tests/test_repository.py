"""
Task Repository层测试

测试TaskRepository的所有方法，确保数据访问层的正确性。

测试覆盖：
1. 基础CRUD操作
2. 复杂查询操作
3. 父子关系查询
4. 软删除和级联删除
5. 异常处理

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlmodel import Session

from src.domains.task.repository import TaskRepository
from src.domains.task.models import Task, TaskStatus, TaskPriority
from src.domains.task.exceptions import TaskDatabaseException
from src.domains.auth.models import Auth


class TestTaskRepository:
    """TaskRepository测试类"""

    def test_create_task_success(self, test_db_session: Session, test_user: Auth, test_task_data: dict):
        """测试成功创建任务"""
        # 准备测试数据
        task_data = test_task_data.copy()
        task_data['user_id'] = test_user.id

        # 执行操作
        repository = TaskRepository(test_db_session)
        task = repository.create(task_data)

        # 验证结果
        assert task.id is not None
        assert task.title == task_data['title']
        assert task.user_id == test_user.id
        assert task.status == task_data['status']
        assert task.priority == task_data['priority']
        assert task.is_deleted is False
        assert task.created_at is not None
        assert task.updated_at is not None

    def test_get_by_id_success(self, test_db_session: Session, test_task: Task):
        """测试成功根据ID获取任务"""
        # 执行操作
        repository = TaskRepository(test_db_session)
        found_task = repository.get_by_id(test_task.id, test_task.user_id)

        # 验证结果
        assert found_task is not None
        assert found_task.id == test_task.id
        assert found_task.title == test_task.title

    def test_get_by_id_not_found(self, test_db_session: Session, test_user: Auth):
        """测试获取不存在的任务"""
        # 执行操作
        repository = TaskRepository(test_db_session)
        found_task = repository.get_by_id(uuid4(), test_user.id)

        # 验证结果
        assert found_task is None

    def test_get_by_id_wrong_user(self, test_db_session: Session, test_task: Task, test_user_list: list[Auth]):
        """测试获取其他用户的任务"""
        # 获取另一个用户
        other_user = test_user_list[1]

        # 执行操作
        repository = TaskRepository(test_db_session)
        found_task = repository.get_by_id(test_task.id, other_user.id)

        # 验证结果
        assert found_task is None

    def test_get_by_id_include_deleted(self, test_db_session: Session, test_task: Task):
        """测试获取已删除的任务"""
        # 软删除任务
        repository = TaskRepository(test_db_session)
        repository.soft_delete(test_task.id, test_task.user_id)

        # 不包含已删除任务
        found_task = repository.get_by_id(test_task.id, test_task.user_id, include_deleted=False)
        assert found_task is None

        # 包含已删除任务
        found_task = repository.get_by_id(test_task.id, test_task.user_id, include_deleted=True)
        assert found_task is not None
        assert found_task.is_deleted is True

    def test_update_task_success(self, test_db_session: Session, test_task: Task):
        """测试成功更新任务"""
        # 准备更新数据
        update_data = {
            'title': '更新后的标题',
            'status': TaskStatus.COMPLETED,
            'priority': TaskPriority.HIGH
        }

        # 执行操作
        repository = TaskRepository(test_db_session)
        updated_task = repository.update(test_task.id, test_task.user_id, update_data)

        # 验证结果
        assert updated_task is not None
        assert updated_task.title == update_data['title']
        assert updated_task.status == update_data['status']
        assert updated_task.priority == update_data['priority']
        assert updated_task.updated_at > test_task.updated_at

    def test_update_task_not_found(self, test_db_session: Session, test_user: Auth):
        """测试更新不存在的任务"""
        # 准备更新数据
        update_data = {'title': '更新后的标题'}

        # 执行操作
        repository = TaskRepository(test_db_session)
        updated_task = repository.update(uuid4(), test_user.id, update_data)

        # 验证结果
        assert updated_task is None

    def test_soft_delete_success(self, test_db_session: Session, test_task: Task):
        """测试成功软删除任务"""
        # 执行操作
        repository = TaskRepository(test_db_session)
        success = repository.soft_delete(test_task.id, test_task.user_id)

        # 验证结果
        assert success is True

        # 检查任务状态
        deleted_task = repository.get_by_id(test_task.id, test_task.user_id, include_deleted=True)
        assert deleted_task.is_deleted is True

    def test_soft_delete_not_found(self, test_db_session: Session, test_user: Auth):
        """测试软删除不存在的任务"""
        # 执行操作
        repository = TaskRepository(test_db_session)
        success = repository.soft_delete(uuid4(), test_user.id)

        # 验证结果
        assert success is False

    def test_get_children_success(self, test_db_session: Session, test_task_tree: dict):
        """测试获取子任务列表"""
        root_task = test_task_tree['root']

        # 执行操作
        repository = TaskRepository(test_db_session)
        children = repository.get_children(root_task.id, root_task.user_id)

        # 验证结果
        assert len(children) == 2
        child_titles = [child.title for child in children]
        assert '子任务1' in child_titles
        assert '子任务2' in child_titles

    def test_get_children_no_children(self, test_db_session: Session, test_task_tree: dict):
        """测试获取叶子任务的子任务"""
        grandchild1 = test_task_tree['grandchild1']

        # 执行操作
        repository = TaskRepository(test_db_session)
        children = repository.get_children(grandchild1.id, grandchild1.user_id)

        # 验证结果
        assert len(children) == 0

    def test_get_list_with_filters(self, test_db_session: Session, test_task_list: list[Task], test_user: Auth):
        """测试带筛选条件的任务列表查询"""
        # 执行操作
        repository = TaskRepository(test_db_session)

        # 按状态筛选
        result = repository.get_list(
            user_id=test_user.id,
            filters={'status': [TaskStatus.PENDING]},
            pagination={'page': 1, 'page_size': 10}
        )
        assert len(result['tasks']) >= 1
        for task in result['tasks']:
            assert task.status == TaskStatus.PENDING

        # 按优先级筛选
        result = repository.get_list(
            user_id=test_user.id,
            filters={'priority': [TaskPriority.HIGH]},
            pagination={'page': 1, 'page_size': 10}
        )
        assert len(result['tasks']) >= 1
        for task in result['tasks']:
            assert task.priority == TaskPriority.HIGH

    def test_get_list_with_search(self, test_db_session: Session, test_task_list: list[Task], test_user: Auth):
        """测试搜索功能"""
        # 执行操作
        repository = TaskRepository(test_db_session)

        # 搜索标题
        result = repository.get_list(
            user_id=test_user.id,
            filters={'search': '任务'},
            pagination={'page': 1, 'page_size': 10}
        )
        assert len(result['tasks']) >= 1

        # 搜索不存在的关键词
        result = repository.get_list(
            user_id=test_user.id,
            filters={'search': '不存在的任务'},
            pagination={'page': 1, 'page_size': 10}
        )
        assert len(result['tasks']) == 0

    def test_get_list_with_pagination(self, test_db_session: Session, test_task_list: list[Task], test_user: Auth):
        """测试分页功能"""
        # 执行操作
        repository = TaskRepository(test_db_session)

        # 第一页
        result1 = repository.get_list(
            user_id=test_user.id,
            pagination={'page': 1, 'page_size': 2}
        )
        assert len(result1['tasks']) == 2
        assert result1['pagination']['current_page'] == 1
        assert result1['pagination']['has_next'] is True

        # 第二页
        result2 = repository.get_list(
            user_id=test_user.id,
            pagination={'page': 2, 'page_size': 2}
        )
        assert len(result2['tasks']) >= 1
        assert result2['pagination']['current_page'] == 2

    def test_find_by_title_exact_match(self, test_db_session: Session, test_task: Task, test_user: Auth):
        """测试精确标题搜索"""
        # 执行操作
        repository = TaskRepository(test_db_session)
        found_tasks = repository.find_by_title(
            user_id=test_user.id,
            title=test_task.title,
            exact_match=True
        )

        # 验证结果
        assert len(found_tasks) == 1
        assert found_tasks[0].id == test_task.id

    def test_find_by_title_partial_match(self, test_db_session: Session, test_task: Task, test_user: Auth):
        """测试模糊标题搜索"""
        # 执行操作
        repository = TaskRepository(test_db_session)
        found_tasks = repository.find_by_title(
            user_id=test_user.id,
            title=test_task.title[:3],  # 使用前3个字符
            exact_match=False
        )

        # 验证结果
        assert len(found_tasks) >= 1
        assert any(task.id == test_task.id for task in found_tasks)

    def test_count_by_status(self, test_db_session: Session, test_task_list: list[Task], test_user: Auth):
        """测试按状态统计"""
        # 执行操作
        repository = TaskRepository(test_db_session)
        status_count = repository.count_by_status(test_user.id)

        # 验证结果
        assert isinstance(status_count, dict)
        assert 'pending' in status_count
        assert 'in_progress' in status_count
        assert 'completed' in status_count
        assert all(isinstance(count, int) for count in status_count.values())

    def test_database_exception_handling(self, test_db_session: Session):
        """测试数据库异常处理"""
        # 执行一个会导致数据库异常的操作
        repository = TaskRepository(test_db_session)

        # 尝试插入无效数据
        invalid_data = {
            'user_id': 'invalid_uuid',  # 无效的UUID格式
            'title': '测试任务'
        }

        # 验证异常被正确抛出
        with pytest.raises(TaskDatabaseException):
            repository.create(invalid_data)