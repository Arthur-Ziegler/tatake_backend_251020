"""
Task领域Service测试

测试任务服务层的核心业务逻辑，包括：
1. 任务CRUD操作
2. 积分发放逻辑
3. 事务管理
4. 业务规则验证
5. 错误处理

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlmodel import Session
from src.domains.task.service import TaskService, parse_json_field
from src.domains.task.models import Task
from src.domains.task.schemas import TaskListQuery, UpdateTaskRequest
from src.domains.task.exceptions import TaskNotFoundException, TaskPermissionDeniedException


@pytest.mark.unit
class TestParseJsonField:
    """JSON字段解析工具函数测试"""

    def test_parse_json_field_none(self):
        """测试解析None值"""
        result = parse_json_field(None)
        assert result == []

    def test_parse_json_field_string_valid(self):
        """测试解析有效JSON字符串"""
        json_str = '["item1", "item2", "item3"]'
        result = parse_json_field(json_str)
        assert result == ["item1", "item2", "item3"]

    def test_parse_json_field_string_invalid(self):
        """测试解析无效JSON字符串"""
        invalid_json = "not valid json"
        result = parse_json_field(invalid_json)
        assert result == []

    def test_parse_json_field_list(self):
        """测试解析列表类型"""
        data_list = ["item1", "item2"]
        result = parse_json_field(data_list)
        assert result == ["item1", "item2"]

    def test_parse_json_field_other_type(self):
        """测试解析其他类型"""
        result = parse_json_field(123)
        assert result == []

    def test_parse_json_field_empty_string(self):
        """测试解析空字符串"""
        result = parse_json_field("")
        assert result == []


@pytest.mark.unit
class TestTaskService:
    """任务服务测试类"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = Mock(spec=Session)
        session.commit = Mock()
        session.rollback = Mock()
        return session

    @pytest.fixture
    def mock_points_service(self):
        """模拟积分服务"""
        return Mock()

    @pytest.fixture
    def task_service(self, mock_session, mock_points_service):
        """创建任务服务实例"""
        with patch('src.domains.task.service.TaskRepository'):
            return TaskService(mock_session, mock_points_service)

    @pytest.fixture
    def sample_task(self):
        """创建示例任务"""
        return Task(
            id=str(uuid4()),
            user_id="test_user_123",
            title="测试任务",
            description="这是一个测试任务",
            status="active",
            priority="medium",
            tags=["测试", "工作"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_task_service_initialization(self, task_service, mock_session, mock_points_service):
        """测试任务服务初始化"""
        assert task_service.session == mock_session
        assert task_service.points_service == mock_points_service
        assert task_service.task_repository is not None
        assert task_service.logger is not None

    def test_transaction_scope_success(self, task_service, mock_session):
        """测试事务作用域成功情况"""
        with task_service.transaction_scope():
            # 模拟一些数据库操作
            pass

        # 验证事务被提交
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    def test_transaction_scope_failure(self, task_service, mock_session):
        """测试事务作用域失败情况"""
        from sqlalchemy.exc import SQLAlchemyError

        with pytest.raises(SQLAlchemyError):
            with task_service.transaction_scope():
                raise SQLAlchemyError("Database error")

        # 验证事务被回滚
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    def test_create_task_success(self, task_service, sample_task):
        """测试创建任务成功"""
        # 模拟repository操作
        task_service.task_repository.create.return_value = sample_task

        result = task_service.create_task(
            user_id="test_user_123",
            title="测试任务",
            description="这是一个测试任务",
            priority="medium",
            tags=["测试", "工作"]
        )

        assert result is not None
        assert result.title == "测试任务"
        assert result.user_id == "test_user_123"
        task_service.task_repository.create.assert_called_once()

    def test_create_task_invalid_data(self, task_service):
        """测试创建任务无效数据"""
        with pytest.raises(Exception):
            task_service.create_task(
                user_id="",  # 无效的用户ID
                title="",    # 无效的标题
                priority="invalid_priority"  # 无效的优先级
            )

    def test_get_task_by_id_success(self, task_service, sample_task):
        """测试根据ID获取任务成功"""
        task_service.task_repository.get_by_id.return_value = sample_task

        result = task_service.get_task_by_id(sample_task.id)

        assert result is not None
        assert result.id == sample_task.id
        task_service.task_repository.get_by_id.assert_called_once_with(sample_task.id)

    def test_get_task_by_id_not_found(self, task_service):
        """测试根据ID获取任务未找到"""
        task_service.task_repository.get_by_id.return_value = None

        with pytest.raises(TaskNotFoundException):
            task_service.get_task_by_id("non_existent_id")

    def test_update_task_success(self, task_service, sample_task):
        """测试更新任务成功"""
        # 模拟获取现有任务
        task_service.task_repository.get_by_id.return_value = sample_task
        task_service.task_repository.update.return_value = sample_task

        update_data = UpdateTaskRequest(
            title="更新后的任务标题",
            description="更新后的描述",
            status="completed"
        )

        result = task_service.update_task(sample_task.id, update_data)

        assert result is not None
        task_service.task_repository.get_by_id.assert_called_once()
        task_service.task_repository.update.assert_called_once()

    def test_update_task_not_found(self, task_service):
        """测试更新任务未找到"""
        task_service.task_repository.get_by_id.return_value = None

        update_data = UpdateTaskRequest(title="更新标题")

        with pytest.raises(TaskNotFoundException):
            task_service.update_task("non_existent_id", update_data)

    def test_delete_task_success(self, task_service, sample_task):
        """测试删除任务成功"""
        task_service.task_repository.get_by_id.return_value = sample_task
        task_service.task_repository.delete.return_value = True

        result = task_service.delete_task(sample_task.id)

        assert result is True
        task_service.task_repository.get_by_id.assert_called_once()
        task_service.task_repository.delete.assert_called_once()

    def test_delete_task_not_found(self, task_service):
        """测试删除任务未找到"""
        task_service.task_repository.get_by_id.return_value = None

        with pytest.raises(TaskNotFoundException):
            task_service.delete_task("non_existent_id")

    def test_list_tasks_with_filters(self, task_service):
        """测试带过滤条件的任务列表查询"""
        query = TaskListQuery(
            user_id="test_user_123",
            status="active",
            priority="high",
            page=1,
            page_size=10
        )

        # 模拟repository返回
        mock_tasks = [Mock() for _ in range(5)]
        task_service.task_repository.list_with_filters.return_value = (mock_tasks, 5)

        result = task_service.list_tasks(query)

        assert len(result[0]) == 5
        assert result[1] == 5  # 总数
        task_service.task_repository.list_with_filters.assert_called_once()

    def test_complete_task_with_points(self, task_service, sample_task):
        """测试完成任务并发放积分"""
        task_service.task_repository.get_by_id.return_value = sample_task
        task_service.task_repository.update.return_value = sample_task

        with task_service.transaction_scope():
            result = task_service.complete_task(sample_task.id, "test_user_123")

        assert result is not None
        assert result.status == "completed"
        # 验证积分发放被调用
        task_service.points_service.award_points.assert_called_once()

    def test_complete_task_already_completed(self, task_service, sample_task):
        """测试完成已完成的任务"""
        sample_task.status = "completed"
        task_service.task_repository.get_by_id.return_value = sample_task

        # 根据业务逻辑，可能应该抛出异常或直接返回
        result = task_service.complete_task(sample_task.id, "test_user_123")

        # 验证积分不会被重复发放
        task_service.points_service.award_points.assert_not_called()

    def test_complete_task_permission_denied(self, task_service, sample_task):
        """测试完成任务权限不足"""
        sample_task.user_id = "different_user"
        task_service.task_repository.get_by_id.return_value = sample_task

        with pytest.raises(TaskPermissionDeniedException):
            task_service.complete_task(sample_task.id, "test_user_123")

    def test_get_task_statistics(self, task_service):
        """测试获取任务统计信息"""
        # 模拟repository返回统计数据
        stats = {
            "total_tasks": 100,
            "completed_tasks": 80,
            "active_tasks": 20,
            "completion_rate": 0.8
        }
        task_service.task_repository.get_statistics.return_value = stats

        result = task_service.get_task_statistics("test_user_123")

        assert result["total_tasks"] == 100
        assert result["completion_rate"] == 0.8
        task_service.task_repository.get_statistics.assert_called_once_with("test_user_123")

    def test_bulk_update_tasks_success(self, task_service):
        """测试批量更新任务成功"""
        task_ids = [str(uuid4()) for _ in range(3)]
        update_data = {"status": "completed"}

        # 模拟repository返回
        updated_count = 3
        task_service.task_repository.bulk_update.return_value = updated_count

        with task_service.transaction_scope():
            result = task_service.bulk_update_tasks(task_ids, update_data)

        assert result == updated_count
        task_service.task_repository.bulk_update.assert_called_once()

    def test_search_tasks_by_keyword(self, task_service):
        """测试关键词搜索任务"""
        keyword = "重要"
        mock_tasks = [Mock() for _ in range(2)]
        task_service.task_repository.search_by_keyword.return_value = mock_tasks

        result = task_service.search_tasks("test_user_123", keyword)

        assert len(result) == 2
        task_service.task_repository.search_by_keyword.assert_called_once_with("test_user_123", keyword)

    def test_get_task_hierarchy(self, task_service):
        """测试获取任务层级结构"""
        parent_task_id = str(uuid4())
        mock_hierarchy = {
            "parent": Mock(),
            "children": [Mock() for _ in range(2)]
        }
        task_service.task_repository.get_hierarchy.return_value = mock_hierarchy

        result = task_service.get_task_hierarchy(parent_task_id)

        assert "parent" in result
        assert "children" in result
        assert len(result["children"]) == 2
        task_service.task_repository.get_hierarchy.assert_called_once_with(parent_task_id)

    def test_validate_task_data_valid(self, task_service):
        """测试验证有效任务数据"""
        task_data = {
            "title": "有效标题",
            "description": "有效描述",
            "priority": "medium",
            "status": "active"
        }

        # 验证不应该抛出异常
        task_service._validate_task_data(task_data)  # 假设有这个私有方法

    def test_validate_task_data_invalid(self, task_service):
        """测试验证无效任务数据"""
        invalid_data = {
            "title": "",  # 无效空标题
            "priority": "invalid"  # 无效优先级
        }

        with pytest.raises(Exception):  # 具体异常类型根据实现
            task_service._validate_task_data(invalid_data)


@pytest.mark.integration
class TestTaskServiceIntegration:
    """任务服务集成测试类"""

    def test_complete_task_flow(self, task_service, sample_task):
        """测试完整任务完成流程"""
        task_service.task_repository.get_by_id.return_value = sample_task
        task_service.task_repository.update.return_value = sample_task

        # 模拟积分发放成功
        task_service.points_service.award_points.return_value = True

        with task_service.transaction_scope():
            result = task_service.complete_task(sample_task.id, sample_task.user_id)

        # 验证整个流程
        assert result.status == "completed"
        task_service.task_repository.update.assert_called()
        task_service.points_service.award_points.assert_called()

    def test_task_lifecycle(self, task_service):
        """测试任务生命周期"""
        task_id = str(uuid4())
        user_id = "test_user_123"

        # 创建任务
        new_task = Task(
            id=task_id,
            user_id=user_id,
            title="生命周期测试任务",
            status="active"
        )

        task_service.task_repository.create.return_value = new_task
        task_service.task_repository.get_by_id.return_value = new_task
        task_service.task_repository.update.return_value = new_task

        # 1. 创建任务
        created_task = task_service.create_task(user_id, "生命周期测试任务")
        assert created_task.status == "active"

        # 2. 更新任务
        update_data = UpdateTaskRequest(status="in_progress")
        updated_task = task_service.update_task(task_id, update_data)
        assert updated_task.status == "in_progress"

        # 3. 完成任务
        with task_service.transaction_scope():
            completed_task = task_service.complete_task(task_id, user_id)
            assert completed_task.status == "completed"