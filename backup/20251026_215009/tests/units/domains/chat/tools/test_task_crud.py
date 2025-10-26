"""
任务CRUD工具严格单元测试

测试任务创建、更新、删除工具的所有功能，特别关注：
1. 用户ID的正确传递和验证
2. LangGraph配置访问
3. 任务服务集成
4. 错误处理和边界情况
5. UUID转换逻辑
6. 时间解析逻辑
7. 标签处理逻辑

作者：TaTakeKe团队
版本：1.0.0 - 任务CRUD工具严格测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from uuid import UUID

from langchain_core.runnables import RunnableConfig

from src.domains.chat.tools.task_crud import (
    create_task, update_task, delete_task,
    AVAILABLE_TOOLS, get_tool_info
)
from src.domains.chat.tools.utils import (
    get_task_service_context, safe_uuid_convert,
    parse_datetime, _success_response, _error_response
)


class TestCreateTaskTool:
    """create_task工具测试"""

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_minimal_success(self, mock_context):
        """测试最小参数成功创建任务"""
        # 设置mock
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-123", "title": "Test Task"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        # 设置配置
        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 调用工具
        result = create_task("Test Task", config=config)

        # 验证调用
        mock_service.create_task.assert_called_once()
        args, kwargs = mock_service.create_task.call_args

        # 验证请求参数
        assert args[0].title == "Test Task"
        assert args[0].description is None
        assert args[0].status == "pending"
        assert args[0].priority == "medium"
        assert args[1] == UUID("550e8400-e29b-41d4-a716-446655440001")

        # 验证响应
        assert "success" in result
        assert "task-123" in result
        assert "任务创建成功" in result

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_full_parameters_success(self, mock_context):
        """测试完整参数成功创建任务"""
        # 设置mock
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-456", "title": "Full Task"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        # 设置配置
        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440002"}

        # 调用工具
        result = create_task(
            title="Full Task",
            description="A complete task description",
            status="in_progress",
            priority="high",
            parent_id="550e8400-e29b-41d4-a716-446655440003",
            tags="标签1,标签2,标签3",
            due_date="2024-12-31T23:59:59Z",
            planned_start_time="2024-12-20T09:00:00Z",
            planned_end_time="2024-12-30T18:00:00Z",
            config=config
        )

        # 验证调用
        args, kwargs = mock_service.create_task.call_args

        # 验证请求参数
        request = args[0]
        assert request.title == "Full Task"
        assert request.description == "A complete task description"
        assert request.status == "in_progress"
        assert request.priority == "high"
        assert request.parent_id == UUID("550e8400-e29b-41d4-a716-446655440003")
        assert request.tags == ["标签1", "标签2", "标签3"]
        assert request.due_date == datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        assert request.planned_start_time == datetime(2024, 12, 20, 9, 0, 0, tzinfo=timezone.utc)
        assert request.planned_end_time == datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc)

        # 验证用户ID
        assert args[1] == UUID("550e8400-e29b-41d4-a716-446655440002")

        # 验证响应
        assert "success" in result
        assert "task-456" in result

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_without_config(self, mock_context):
        """测试没有配置时的错误处理"""
        # 调用工具（不传递config）
        with pytest.raises(ValueError) as exc_info:
            create_task("Test Task")

        assert "无法获取用户ID" in str(exc_info.value)
        assert "请确保聊天系统正确传递用户信息" in str(exc_info.value)

        # 确保没有调用服务
        mock_context.assert_not_called()

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_with_empty_config(self, mock_context):
        """测试空配置时的错误处理"""
        config = RunnableConfig()
        config.configurable = {}

        with pytest.raises(ValueError) as exc_info:
            create_task("Test Task", config=config)

        assert "无法获取用户ID" in str(exc_info.value)

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_with_invalid_user_id(self, mock_context):
        """测试无效用户ID的处理"""
        config = RunnableConfig()
        config.configurable = {"user_id": "invalid-uuid"}

        with pytest.raises(ValueError) as exc_info:
            create_task("Test Task", config=config)

        assert "无效的UUID格式" in str(exc_info.value)

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_service_exception(self, mock_context):
        """测试任务服务异常处理"""
        # 设置mock抛出异常
        mock_service = Mock()
        mock_service.create_task.side_effect = Exception("Service error")

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 调用工具
        result = create_task("Test Task", config=config)

        # 验证错误响应
        assert "success" not in result
        assert "error" in result
        assert "CREATE_TASK_ERROR" in result
        assert "Service error" in result

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_tags_parsing(self, mock_context):
        """测试标签解析逻辑"""
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-789"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 测试不同的标签格式
        test_cases = [
            ("标签1,标签2", ["标签1", "标签2"]),
            (" 标签1 , 标签2 ", ["标签1", "标签2"]),  # 带空格
            ("标签1", ["标签1"]),  # 单个标签
            ("", []),  # 空标签
        ]

        for tags_input, expected_tags in test_cases:
            result = create_task("Test Task", tags=tags_input, config=config)

            # 获取调用参数
            args, kwargs = mock_service.create_task.call_args
            assert args[0].tags == expected_tags

            # 重置mock
            mock_service.reset_mock()

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_datetime_parsing(self, mock_context):
        """测试日期时间解析逻辑"""
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-datetime"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 测试不同的日期格式
        test_cases = [
            ("2024-12-31T23:59:59Z", datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
            ("2024-12-31T23:59:59", datetime(2024, 12, 31, 23, 59, 59)),
            ("2024-12-31", datetime(2024, 12, 31, 0, 0, 0)),
        ]

        for date_input, expected_date in test_cases:
            result = create_task("Test Task", due_date=date_input, config=config)

            # 获取调用参数
            args, kwargs = mock_service.create_task.call_args
            assert args[0].due_date == expected_date

            # 重置mock
            mock_service.reset_mock()


class TestUpdateTaskTool:
    """update_task工具测试"""

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_update_task_success(self, mock_context):
        """测试成功更新任务"""
        # 设置mock
        mock_service = Mock()
        mock_service.update_task_with_tree_structure.return_value = {
            "task_id": "task-123",
            "title": "Updated Task",
            "status": "completed"
        }

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 调用工具
        result = update_task(
            task_id="550e8400-e29b-41d4-a716-446655440123",
            title="Updated Task",
            status="completed",
            config=config
        )

        # 验证调用
        args, kwargs = mock_service.update_task_with_tree_structure.call_args

        # 验证任务ID
        assert args[0] == UUID("550e8400-e29b-41d4-a716-446655440123")

        # 验证更新数据
        update_request = args[1]
        assert update_request.title == "Updated Task"
        assert update_request.status == "completed"

        # 验证用户ID
        assert args[2] == UUID("550e8400-e29b-41d4-a716-446655440001")

        # 验证响应
        assert "success" in result
        assert "任务更新成功" in result

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_update_task_without_config(self, mock_context):
        """测试没有配置时的错误处理"""
        with pytest.raises(ValueError) as exc_info:
            update_task("550e8400-e29b-41d4-a716-446655440123", title="Updated")

        assert "无法获取用户ID" in str(exc_info.value)

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_update_task_invalid_task_id(self, mock_context):
        """测试无效任务ID"""
        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        with pytest.raises(ValueError) as exc_info:
            update_task("", title="Updated", config=config)

        assert "任务ID不能为空" in str(exc_info.value)

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_update_task_partial_update(self, mock_context):
        """测试部分更新"""
        mock_service = Mock()
        mock_service.update_task_with_tree_structure.return_value = {"task_id": "task-123"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 只更新标题
        update_task(
            task_id="550e8400-e29b-41d4-a716-446655440123",
            title="Only Title Updated",
            config=config
        )

        args, kwargs = mock_service.update_task_with_tree_structure.call_args
        update_request = args[1]

        # 验证只有标题被更新
        assert update_request.title == "Only Title Updated"
        assert not hasattr(update_request, 'description') or update_request.description is None
        assert not hasattr(update_request, 'status') or update_request.status is None


class TestDeleteTaskTool:
    """delete_task工具测试"""

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_delete_task_success(self, mock_context):
        """测试成功删除任务"""
        # 设置mock
        mock_service = Mock()
        mock_service.delete_task.return_value = {
            "task_id": "task-123",
            "deleted": True
        }

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 调用工具
        result = delete_task("550e8400-e29b-41d4-a716-446655440123", config=config)

        # 验证调用
        args, kwargs = mock_service.delete_task.call_args

        # 验证参数
        assert args[0] == UUID("550e8400-e29b-41d4-a716-446655440123")
        assert args[1] == UUID("550e8400-e29b-41d4-a716-446655440001")

        # 验证响应
        assert "success" in result
        assert "任务删除成功" in result
        assert "task-123" in result

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_delete_task_without_config(self, mock_context):
        """测试没有配置时的错误处理"""
        with pytest.raises(ValueError) as exc_info:
            delete_task("550e8400-e29b-41d4-a716-446655440123")

        assert "无法获取用户ID" in str(exc_info.value)

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_delete_task_invalid_task_id(self, mock_context):
        """测试无效任务ID"""
        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        with pytest.raises(ValueError) as exc_info:
            delete_task("", config=config)

        assert "任务ID不能为空" in str(exc_info.value)


class TestTaskToolsIntegration:
    """任务工具集成测试"""

    def test_available_tools_list(self):
        """测试可用工具列表"""
        assert len(AVAILABLE_TOOLS) == 3
        assert create_task in AVAILABLE_TOOLS
        assert update_task in AVAILABLE_TOOLS
        assert delete_task in AVAILABLE_TOOLS

    def test_get_tool_info(self):
        """测试工具信息获取"""
        tool_info = get_tool_info()

        assert isinstance(tool_info, dict)
        assert "tools" in tool_info
        assert len(tool_info["tools"]) == 3

        # 验证每个工具的信息
        tool_names = [tool["name"] for tool in tool_info["tools"]]
        assert "create_task" in tool_names
        assert "update_task" in tool_names
        assert "delete_task" in tool_names

        # 验证create_task工具信息
        create_tool_info = next(t for t in tool_info["tools"] if t["name"] == "create_task")
        assert "description" in create_tool_info
        assert "parameters" in create_tool_info
        assert "title" in create_tool_info["parameters"]
        assert "config" in create_tool_info["parameters"]

    def test_tool_metadata(self):
        """测试工具元数据"""
        # 验证工具有正确的装饰器属性
        assert hasattr(create_task, '__name__')
        assert create_task.__name__ == "create_task"

        assert hasattr(update_task, '__name__')
        assert update_task.__name__ == "update_task"

        assert hasattr(delete_task, '__name__')
        assert delete_task.__name__ == "delete_task"


class TestTaskToolsErrorHandling:
    """任务工具错误处理测试"""

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_context_manager_exception(self, mock_context):
        """测试上下文管理器异常"""
        # 设置mock抛出异常
        mock_context.side_effect = Exception("Context error")

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        result = create_task("Test Task", config=config)

        # 验证错误响应
        assert "success" not in result
        assert "error" in result
        assert "CREATE_TASK_ERROR" in result

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_service_validation_error(self, mock_context):
        """测试服务验证错误"""
        mock_service = Mock()
        mock_service.create_task.side_effect = ValueError("Validation error")

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        result = create_task("Test Task", config=config)

        # 验证错误响应
        assert "success" not in result
        assert "error" in result
        assert "VALIDATION_ERROR" in result
        assert "Validation error" in result

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_parent_id_uuid_conversion(self, mock_context):
        """测试父任务ID UUID转换"""
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-child"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 测试None parent_id
        result = create_task("Test Task", parent_id=None, config=config)
        args, kwargs = mock_service.create_task.call_args
        assert args[0].parent_id is None

        mock_service.reset_mock()

        # 测试有效parent_id
        result = create_task("Test Task", parent_id="550e8400-e29b-41d4-a716-446655440002", config=config)
        args, kwargs = mock_service.create_task.call_args
        assert args[0].parent_id == UUID("550e8400-e29b-41d4-a716-446655440002")


@pytest.mark.performance
class TestTaskToolsPerformance:
    """任务工具性能测试"""

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_create_task_performance(self, mock_context):
        """测试创建任务性能"""
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-perf"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        import time
        start_time = time.time()

        for i in range(100):
            create_task(f"Task {i}", config=config)

        duration = time.time() - start_time
        assert duration < 2.0, f"create_task性能测试失败: {duration:.3f}s"

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_large_tags_processing(self, mock_context):
        """测试大量标签处理性能"""
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-tags"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 创建大量标签
        large_tags = ",".join([f"标签{i}" for i in range(100)])

        import time
        start_time = time.time()

        create_task("Task with many tags", tags=large_tags, config=config)

        duration = time.time() - start_time
        assert duration < 1.0, f"大量标签处理性能测试失败: {duration:.3f}s"

        # 验证标签被正确解析
        args, kwargs = mock_service.create_task.call_args
        assert len(args[0].tags) == 100


class TestTaskToolsEdgeCases:
    """任务工具边界情况测试"""

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_empty_title(self, mock_context):
        """测试空标题"""
        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 应该能处理空标题（验证由Pydantic处理）
        result = create_task("", config=config)

        # 由于Pydantic验证可能会失败，这里主要测试我们的错误处理
        assert isinstance(result, str)

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_very_long_title(self, mock_context):
        """测试超长标题"""
        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        long_title = "A" * 1000  # 1000字符的标题

        # 应该能处理超长标题（验证由Pydantic处理）
        result = create_task(long_title, config=config)

        assert isinstance(result, str)

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_special_characters_in_tags(self, mock_context):
        """测试标签中的特殊字符"""
        mock_service = Mock()
        mock_service.create_task.return_value = {"task_id": "task-special"}

        mock_ctx = {'task_service': mock_service}
        mock_context.return_value.__enter__.return_value = mock_ctx

        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        special_tags = "标签1,标签@#,标签$%,标签^&"

        result = create_task("Task with special tags", tags=special_tags, config=config)

        # 验证特殊字符标签被正确处理
        args, kwargs = mock_service.create_task.call_args
        expected_tags = ["标签1", "标签@#", "标签$%", "标签^&"]
        assert args[0].tags == expected_tags

    @patch('src.domains.chat.tools.task_crud.get_task_service_context')
    def test_malformed_datetime(self, mock_context):
        """测试格式错误的日期时间"""
        config = RunnableConfig()
        config.configurable = {"user_id": "550e8400-e29b-41d4-a716-446655440001"}

        # 测试各种格式错误的日期时间
        malformed_dates = [
            "not-a-date",
            "2024-13-45",  # 无效日期
            "2024-12-31T25:99:99",  # 无效时间
        ]

        for malformed_date in malformed_dates:
            with pytest.raises(ValueError):
                create_task("Test Task", due_date=malformed_date, config=config)