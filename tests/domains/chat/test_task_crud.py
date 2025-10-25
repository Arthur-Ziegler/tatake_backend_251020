"""
任务CRUD工具测试套件

测试聊天任务CRUD工具功能，包括：
1. create_task - 创建任务工具
2. update_task - 更新任务工具
3. delete_task - 删除任务工具

测试重点：
- 工具参数验证（UUID、日期时间等）
- 数据库操作验证
- 事务处理
- 错误处理和恢复
- JSON响应格式验证
- 边界条件测试

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

# 导入测试基础设施
from .test_chat_tools_infrastructure import (
    ToolCallLogger,
    MockToolServiceContext,
    ToolResponseValidator,
    ToolTestDataFactory,
    ChatToolsTestConfig
)

# 导入要测试的CRUD工具
from src.domains.chat.tools.task_crud import (
    create_task,
    update_task,
    delete_task,
    AVAILABLE_TOOLS as CRUD_AVAILABLE_TOOLS
)

# 导入相关的模型和Schema
from src.domains.chat.models import ChatState
from src.domains.task.schemas import CreateTaskRequest, UpdateTaskRequest
from src.domains.task.models import Task, TaskStatus

# 配置日志
logger = logging.getLogger(__name__)


class TestTaskCrudTools:
    """任务CRUD工具测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.call_logger = ToolCallLogger()
        self.service_context = MockToolServiceContext()

        # Mock服务上下文
        self.mock_task_service = self.service_context['task_service']
        self.mock_points_service = self.service_context['points_service']

    def teardown_method(self):
        """清理测试方法"""
        self.call_logger.clear()

    def _create_mock_task(self) -> Task:
        """创建Mock任务对象"""
        return Task(
            id=str(uuid.uuid4()),
            title="测试任务",
            description="这是一个测试任务",
            status=TaskStatus.PENDING,
            priority="medium",
            user_id="test-user-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            tags=[],
            service_ids=[],
            completion_percentage=0.0,
            is_deleted=False
        )

    def _mock_task_service_for_create(self, task_data: dict):
        """Mock创建任务服务"""
        mock_service = self.service_context['task_service']
        mock_service.create_task.return_value = {
            "id": str(uuid.uuid4()),
            "title": task_data.get("title"),
            "description": task_data.get("description"),
            "status": task_data.get("status", "pending"),
            "priority": task_data.get("priority", "medium"),
            "user_id": task_data.get("user_id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tags": task_data.get("tags", []),
            "service_ids": task_data.get("service_ids", []),
            "completion_percentage": 0.0,
            "is_deleted": False
        }
        return mock_service

    def test_create_task_success(self, mock_context):
        """测试创建任务成功场景"""
        logger.info("🔄 测试create_task成功场景...")

        # 准备测试数据
        test_task_data = ToolTestDataFactory.create_sample_task_data()

        # Mock服务返回值
        mock_service = self._mock_task_service_for_create(test_task_data)

        # 调用工具
        result = create_task.invoke({
            'title': test_task_data['title'],
            'description': test_task_data['description'],
            'status': test_task_data['status'],
            'priority': test_task_data['priority'],
            'tags': '重要,测试',
            'due_date': '2024-12-31T23:59:59Z',
            'user_id': ChatToolsTestConfig.TEST_USER_ID
        })

        # 验证响应
        assert ToolResponseValidator.validate_success_response(result), "创建任务响应验证失败"

        # 验证服务调用
        self.mock_task_service.create_task.assert_called_once()
        call_args = self.mock_task_service.create_task.call_args[0]

        assert call_args[0][0] == test_task_data['title'], "标题参数不正确"
        assert call_args[0][1] == test_task_data['description'], "描述参数不正确"
        assert call_args[0][2] == test_task_data['status'], "状态参数不正确"
        assert call_args[0][3] == test_task_data['priority'], "优先级参数不正确"
        assert call_args[0][4] == test_task_data['user_id'], "用户ID参数不正确"
        assert call_args[0][6] == '2024-12-31T23:59:59Z', "截止日期参数不正确"
        assert call_args[0][7] == test_task_data['tags'], "标签参数不正确"

        # 验证调用日志
        calls = self.call_logger.get_calls()
        assert len(calls) == 1, "应该有一次工具调用"
        assert calls[0]['tool_name'] == 'create_task', "工具名称不正确"

        logger.info(f"✅ create_task成功场景测试通过")

    def test_create_task_invalid_uuid(self, mock_context):
        """测试创建任务无效UUID场景"""
        logger.info("🔄 测试create_task无效UUID场景...")

        test_data = ToolTestDataFactory.create_sample_task_data()
        test_data['user_id'] = ToolTestDataFactory.create_invalid_task_id()

        # 调用工具
        result = create_task.invoke({
            'title': test_task_data['title'],
            'user_id': test_data['user_id']
        })

        # 验证响应
        assert not ToolResponseValidator.validate_success_response(result), "应该返回错误响应"
        assert ToolResponseValidator.validate_error_response(result), "错误响应格式不正确"

        # 验证错误类型
        assert "VALIDATION_ERROR" in result, "应该返回验证错误"

        logger.info(f"✅ create_task无效UUID场景测试通过")

    def test_create_task_service_exception(self, mock_context):
        """测试创建任务服务异常场景"""
        logger.info("🔄 测试create_task服务异常场景...")

        # Mock服务抛出异常
        mock_service = self.service_context['task_service']
        mock_service.create_task.side_effect = Exception("数据库连接失败")

        # 调用工具
        result = create_task.invoke({
            'title': '测试任务',
            'user_id': ChatToolsTestConfig.TEST_USER_ID
        })

        # 验证响应
        assert not ToolResponseValidator.validate_success_response(result), "应该返回错误响应"
        assert ToolResponseValidator.validate_error_response(result), "错误响应格式不正确"

        # 验证错误类型
        assert "SERVICE_ERROR" in result, "应该返回服务错误"

        logger.info(f"✅ create_task服务异常场景测试通过")

    def test_update_task_success(self, mock_context):
        """测试更新任务成功场景"""
        logger.info("🔄 测试update_task成功场景...")

        # 先创建一个任务
        original_task = self._create_mock_task()
        mock_service = self.service_context['task_service']
        mock_service.get_task.return_value = original_task

        # 准备更新数据
        update_data = {
            'title': '更新后的测试任务',
            'description': '更新后的任务描述',
            'status': 'in_progress'
        }

        # 调用工具
        result = update_task.invoke({
            'task_id': original_task.id,
            'title': update_data['title'],
            'description': update_data['description'],
            'status': update_data['status'],
            'user_id': ChatToolsTestConfig.TEST_USER_ID
        })

        # 验证响应
        assert ToolResponseValidator.validate_success_response(result), "更新任务响应验证失败"

        # 验证服务调用
        mock_service.get_task.assert_called_once()
        mock_service.update_task_with_tree_structure.assert_called_once()

        # 验证调用日志
        calls = self.call_logger.get_calls()
        assert len(calls) == 2, "应该有两次工具调用"

        logger.info(f"✅ update_task成功场景测试通过")

    def test_update_task_not_found(self, mock_context):
        """测试更新任务不存在场景"""
        logger.info("🔄 测试update_task任务不存在场景...")

        test_task_id = str(uuid.uuid4())
        update_data = {'title': '更新的任务'}

        # 调用工具
        result = update_task.invoke({
            'task_id': test_task_id,
            'title': update_data['title'],
            'user_id': ChatToolsTestConfig.TEST_USER_ID
        })

        # 验证响应
        assert not ToolResponseValidator.validate_success_response(result), "应该返回错误响应"
        assert ToolResponseValidator.validate_error_response(result), "错误响应格式不正确"
        assert "TASK_NOT_FOUND" in result, "应该返回任务不存在错误"

        logger.info(f"✅ update_task任务不存在场景测试通过")

    def test_delete_task_success(self, mock_context):
        """测试删除任务成功场景"""
        logger.info("🔄 测试delete_task成功场景...")

        # 先创建一个任务
        original_task = self._create_mock_task()
        mock_service = self.service_context['task_service']
        mock_service.get_task.return_value = original_task
        mock_service.delete_task.return_value = {
            "deleted_task_id": original_task.id,
            "deleted_subtasks_count": 0
        }

        # 调用工具
        result = delete_task.invoke({
            'task_id': original_task.id,
            'user_id': ChatToolsTestConfig.TEST_USER_ID
        })

        # 验证响应
        assert ToolResponseValidator.validate_success_response(result), "删除任务响应验证失败"

        # 验证服务调用
        mock_service.delete_task.assert_called_once()

        # 验证调用日志
        calls = self.call_logger.get_calls()
        assert len(calls) == 2, "应该有两次工具调用（创建+删除）"

        logger.info(f"✅ delete_task成功场景测试通过")

    def run_all_tests(self):
        """运行所有任务CRUD工具测试"""
        try:
            logger.info("🔄 开始运行任务CRUD工具测试...")

            # 测试创建任务
            self.test_create_task_success(self.mock_context)
            self.test_create_task_invalid_uuid(self.mock_context)
            self.test_create_task_service_exception(self.mock_context)

            # 测试更新任务
            self.test_update_task_success(self.mock_context)
            self.test_update_task_not_found(self.mock_context)

            # 测试删除任务
            self.test_delete_task_success(self.mock_context)

            logger.info("✅ 所有任务CRUD工具测试通过")
            return True

        except Exception as e:
            logger.error(f"❌ 任务CRUD工具测试失败: {e}")
            return False


if __name__ == "__main__":
    """运行所有任务CRUD工具测试"""
    test_instance = TestTaskCrudTools()

    try:
        # 运行测试
        success = test_instance.run_all_tests()

        if success:
            print("🎉 所有任务CRUD工具测试通过！")
        else:
            print("❌ 任务CRUD工具测试失败！")

    except Exception as e:
        print(f"💥 测试执行异常: {e}")