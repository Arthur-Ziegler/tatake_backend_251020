"""
任务查询工具测试套件

测试驱动开发（TDD）：先编写测试，再验证功能实现。
本文件包含对 chat/tools/task_query.py 中所有工具函数的全面测试。

测试覆盖范围：
1. query_tasks工具：条件查询任务列表
2. get_task_detail工具：获取任务详情
3. 参数验证函数
4. 错误处理和边界情况
5. 工具集成和响应格式

设计原则：
1. 每个测试用例独立运行，使用Mock隔离依赖
2. 覆盖正常情况、边界情况和异常情况
3. 验证返回的JSON格式正确性
4. 测试LangChain工具装饰器的正确性

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from typing import Dict, Any, List

# 测试用例专用的logger
logger = logging.getLogger(__name__)

# 导入要测试的模块
from src.domains.chat.tools.task_query import (
    query_tasks,
    get_task_detail,
    validate_query_parameters,
    validate_task_id,
    get_tool_info,
    AVAILABLE_TOOLS
)


class TestQueryTasks:
    """测试 query_tasks 工具函数"""

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_basic_success(self, mock_context):
        """测试基本查询成功场景"""
        # 模拟服务上下文
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-1",
                "title": "测试任务1",
                "status": "pending",
                "priority": "medium"
            },
            {
                "id": "task-2",
                "title": "测试任务2",
                "status": "completed",
                "priority": "high"
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = query_tasks()

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "data" in result_data
        assert "tasks" in result_data["data"]
        assert "pagination" in result_data["data"]
        assert len(result_data["data"]["tasks"]) == 2
        assert result_data["data"]["pagination"]["limit"] == 20
        assert result_data["data"]["pagination"]["offset"] == 0

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="placeholder",
            status=None,
            parent_id=None,
            limit=20,
            offset=0
        )

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_with_status_filter(self, mock_context):
        """测试带状态筛选的查询"""
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-1",
                "title": "已完成任务",
                "status": "completed",
                "priority": "high"
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = query_tasks(status="completed", limit=10)

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]["tasks"]) == 1
        assert result_data["data"]["tasks"][0]["status"] == "completed"

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="placeholder",
            status="completed",
            parent_id=None,
            limit=10,
            offset=0
        )

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_with_parent_id(self, mock_context):
        """测试带父任务ID筛选的查询"""
        parent_id = str(uuid4())
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "child-task-1",
                "title": "子任务1",
                "status": "pending",
                "parent_id": parent_id
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = query_tasks(parent_id=parent_id)

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]["tasks"]) == 1

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="placeholder",
            status=None,
            parent_id=parent_id,
            limit=20,
            offset=0
        )

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_with_pagination(self, mock_context):
        """测试分页查询"""
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {"id": f"task-{i}", "title": f"任务{i}"} for i in range(1, 6)
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = query_tasks(limit=5, offset=10)

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]["tasks"]) == 5
        assert result_data["data"]["pagination"]["limit"] == 5
        assert result_data["data"]["pagination"]["offset"] == 10

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="placeholder",
            status=None,
            parent_id=None,
            limit=5,
            offset=10
        )

    def test_query_tasks_invalid_limit(self):
        """测试无效的limit参数"""
        # 测试limit为0
        result = query_tasks(limit=0)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in result_data

        # 测试limit超过100
        result = query_tasks(limit=101)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in result_data

    def test_query_tasks_negative_offset(self):
        """测试负数offset参数"""
        result = query_tasks(offset=-1)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in result_data

    def test_query_tasks_invalid_parent_id(self):
        """测试无效的父任务ID"""
        result = query_tasks(parent_id="invalid-uuid")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in result_data

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_empty_result(self, mock_context):
        """测试空结果查询"""
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = []

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = query_tasks()

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]["tasks"]) == 0
        assert result_data["data"]["pagination"]["count"] == 0

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_service_exception(self, mock_context):
        """测试服务异常处理"""
        mock_context.side_effect = Exception("数据库连接失败")

        # 调用工具
        result = query_tasks()

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "QUERY_FAILED" in result_data


class TestGetTaskDetail:
    """测试 get_task_detail 工具函数"""

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_get_task_detail_success(self, mock_context):
        """测试成功获取任务详情"""
        task_id = str(uuid4())
        expected_task = {
            "id": task_id,
            "title": "测试任务",
            "description": "这是一个测试任务",
            "status": "pending",
            "priority": "high",
            "created_at": "2024-12-25T10:30:00Z"
        }

        mock_task_service = Mock()
        mock_task_service.get_task.return_value = expected_task

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = get_task_detail(task_id)

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["data"]["task"] == expected_task
        assert "获取成功" in result_data["message"]

        # 验证服务调用参数
        mock_task_service.get_task.assert_called_once_with(
            task_id=UUID(task_id),
            user_id="placeholder"
        )

    def test_get_task_detail_empty_task_id(self):
        """测试空任务ID"""
        result = get_task_detail("")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in result_data

    def test_get_task_detail_none_task_id(self):
        """测试None任务ID"""
        result = get_task_detail(None)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in result_data

    def test_get_task_detail_whitespace_task_id(self):
        """测试只包含空白的任务ID"""
        result = get_task_detail("   ")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in result_data

    def test_get_task_detail_invalid_uuid_format(self):
        """测试无效的UUID格式"""
        invalid_ids = [
            "invalid-uuid",
            "123-456-789",
            "not-a-uuid-at-all",
            "550e8400-e29b-41d4-a716-44665544000"  # 缺少一段
        ]

        for invalid_id in invalid_ids:
            result = get_task_detail(invalid_id)
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "INVALID_PARAMETERS" in result_data

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_get_task_detail_task_not_found(self, mock_context):
        """测试任务不存在"""
        task_id = str(uuid4())

        mock_task_service = Mock()
        mock_task_service.get_task.side_effect = Exception("任务不存在")

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = get_task_detail(task_id)

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "GET_DETAIL_FAILED" in result_data

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_get_task_detail_permission_denied(self, mock_context):
        """测试权限不足"""
        task_id = str(uuid4())

        mock_task_service = Mock()
        mock_task_service.get_task.side_effect = Exception("无权限访问此任务")

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = get_task_detail(task_id)

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "GET_DETAIL_FAILED" in result_data

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_get_task_detail_context_exception(self, mock_context):
        """测试上下文异常"""
        mock_context.side_effect = Exception("上下文创建失败")

        # 调用工具
        result = get_task_detail(str(uuid4()))

        # 验证结果
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "GET_DETAIL_FAILED" in result_data


class TestValidateQueryParameters:
    """测试查询参数验证函数"""

    def test_validate_query_parameters_valid_basic(self):
        """测试有效的基本参数"""
        assert validate_query_parameters(None, None, 20, 0) is True

    def test_validate_query_parameters_valid_with_status(self):
        """测试带有效状态的参数"""
        valid_statuses = ['pending', 'completed', 'cancelled', 'in_progress']
        for status in valid_statuses:
            assert validate_query_parameters(status, None, 20, 0) is True

    def test_validate_query_parameters_valid_with_parent_id(self):
        """测试带有效父任务ID的参数"""
        parent_id = str(uuid4())
        assert validate_query_parameters(None, parent_id, 20, 0) is True

    def test_validate_query_parameters_invalid_limit_zero(self):
        """测试无效的limit（0）"""
        assert validate_query_parameters(None, None, 0, 0) is False

    def test_validate_query_parameters_invalid_limit_negative(self):
        """测试无效的limit（负数）"""
        assert validate_query_parameters(None, None, -1, 0) is False

    def test_validate_query_parameters_invalid_limit_too_large(self):
        """测试无效的limit（超过100）"""
        assert validate_query_parameters(None, None, 101, 0) is False

    def test_validate_query_parameters_invalid_offset_negative(self):
        """测试无效的offset（负数）"""
        assert validate_query_parameters(None, None, 20, -1) is False

    def test_validate_query_parameters_invalid_status(self):
        """测试无效的状态"""
        invalid_statuses = ['invalid', 'unknown', 'wrong', '']
        for status in invalid_statuses:
            assert validate_query_parameters(status, None, 20, 0) is False

    def test_validate_query_parameters_invalid_parent_id(self):
        """测试无效的父任务ID"""
        invalid_parent_ids = ['invalid-uuid', '123-456-789', '']
        for parent_id in invalid_parent_ids:
            assert validate_query_parameters(None, parent_id, 20, 0) is False


class TestValidateTaskId:
    """测试任务ID验证函数"""

    def test_validate_task_id_valid_uuid_string(self):
        """测试有效的UUID字符串"""
        task_id = str(uuid4())
        assert validate_task_id(task_id) is True

    def test_validate_task_id_empty_string(self):
        """测试空字符串"""
        assert validate_task_id("") is False

    def test_validate_task_id_none(self):
        """测试None"""
        assert validate_task_id(None) is False

    def test_validate_task_id_whitespace_only(self):
        """测试只包含空白的字符串"""
        assert validate_task_id("   ") is False
        assert validate_task_id("\t\n") is False

    def test_validate_task_id_invalid_format(self):
        """测试无效格式"""
        invalid_ids = [
            "invalid-uuid",
            "123-456-789",
            "not-a-uuid",
            "550e8400-e29b-41d4-a716-44665544000",  # 缺少一段
            "g50e8400-e29b-41d4-a716-446655440000"  # 包含非法字符
        ]

        for invalid_id in invalid_ids:
            assert validate_task_id(invalid_id) is False


class TestGetToolInfo:
    """测试工具信息函数"""

    def test_get_tool_info_structure(self):
        """测试工具信息结构"""
        info = get_tool_info()

        assert isinstance(info, dict)
        assert "tools" in info
        assert isinstance(info["tools"], list)
        assert len(info["tools"]) == 2  # query_tasks 和 get_task_detail

    def test_get_tool_info_query_tasks_info(self):
        """测试query_tasks工具信息"""
        info = get_tool_info()
        query_tasks_info = None

        for tool in info["tools"]:
            if tool["name"] == "query_tasks":
                query_tasks_info = tool
                break

        assert query_tasks_info is not None
        assert query_tasks_info["name"] == "query_tasks"
        assert "查询任务列表" in query_tasks_info["description"]
        assert "parameters" in query_tasks_info
        assert "examples" in query_tasks_info

        # 检查参数定义
        params = query_tasks_info["parameters"]
        assert "status" in params
        assert "parent_id" in params
        assert "limit" in params
        assert "offset" in params

    def test_get_tool_info_get_task_detail_info(self):
        """测试get_task_detail工具信息"""
        info = get_tool_info()
        get_task_detail_info = None

        for tool in info["tools"]:
            if tool["name"] == "get_task_detail":
                get_task_detail_info = tool
                break

        assert get_task_detail_info is not None
        assert get_task_detail_info["name"] == "get_task_detail"
        assert "获取任务详情" in get_task_detail_info["description"]
        assert "parameters" in get_task_detail_info
        assert "examples" in get_task_detail_info

        # 检查参数定义
        params = get_task_detail_info["parameters"]
        assert "task_id" in params
        assert params["task_id"]["required"] is True


class TestAvailableTools:
    """测试可用工具列表"""

    def test_available_tools_structure(self):
        """测试可用工具列表结构"""
        assert isinstance(AVAILABLE_TOOLS, list)
        assert len(AVAILABLE_TOOLS) == 2

        # 验证工具类型
        for tool in AVAILABLE_TOOLS:
            assert hasattr(tool, 'name')  # LangChain工具属性
            assert hasattr(tool, 'description')  # LangChain工具属性
            assert hasattr(tool, 'args')  # LangChain工具属性

    def test_available_tools_names(self):
        """测试工具名称"""
        tool_names = [tool.name for tool in AVAILABLE_TOOLS]
        assert "query_tasks" in tool_names
        assert "get_task_detail" in tool_names

    def test_available_tools_invoke_interface(self):
        """测试工具调用接口"""
        # 验证工具具有LangChain工具的标准接口
        for tool in AVAILABLE_TOOLS:
            assert hasattr(tool, 'invoke')  # 应该有invoke方法
            assert callable(tool.invoke)  # invoke应该是可调用的


class TestJsonResponseFormat:
    """测试JSON响应格式"""

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_success_response_json_format(self, mock_context):
        """测试成功响应的JSON格式"""
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = []

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        result = query_tasks()

        # 验证可以解析为JSON
        parsed_result = json.loads(result)

        # 验证必要字段
        assert "success" in parsed_result
        assert "data" in parsed_result
        assert "message" in parsed_result
        assert "timestamp" in parsed_result

        # 验证字段类型
        assert isinstance(parsed_result["success"], bool)
        assert isinstance(parsed_result["data"], dict)
        assert isinstance(parsed_result["message"], str)
        assert isinstance(parsed_result["timestamp"], str)

    def test_error_response_json_format(self):
        """测试错误响应的JSON格式"""
        result = query_tasks(limit=-1)  # 会触发参数错误

        # 验证可以解析为JSON
        parsed_result = json.loads(result)

        # 验证错误响应字段
        assert parsed_result["success"] is False
        assert "error" in parsed_result
        assert "error_code" in parsed_result
        assert "timestamp" in parsed_result


# 性能测试
class TestPerformance:
    """性能测试"""

    def test_parameter_validation_performance(self):
        """测试参数验证性能"""
        import time

        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            validate_query_parameters("completed", str(uuid4()), 20, 0)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        assert avg_time < 0.001, f"参数验证平均时间过长: {avg_time}秒"

    def test_task_id_validation_performance(self):
        """测试任务ID验证性能"""
        import time

        task_id = str(uuid4())
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            validate_task_id(task_id)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        assert avg_time < 0.001, f"任务ID验证平均时间过长: {avg_time}秒"


# 集成测试
class TestIntegration:
    """集成测试"""

    def test_tool_integration_with_langchain(self):
        """测试与LangChain的集成"""
        # 验证工具可以被LangChain正确识别
        for tool in AVAILABLE_TOOLS:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'args')

            # 验证工具可以被序列化（LangGraph需要）
            try:
                tool_json = {
                    'name': tool.name,
                    'description': tool.description,
                    'args': tool.args
                }
                assert isinstance(tool_json, dict)
            except Exception as e:
                pytest.fail(f"工具序列化失败: {e}")

    def test_error_handling_consistency(self):
        """测试错误处理的一致性"""
        # 测试各种错误情况的响应格式一致性
        error_scenarios = [
            lambda: query_tasks(limit=-1),
            lambda: query_tasks(limit=101),
            lambda: query_tasks(offset=-1),
            lambda: query_tasks(parent_id="invalid"),
            lambda: get_task_detail(""),
            lambda: get_task_detail(None),
            lambda: get_task_detail("invalid-uuid")
        ]

        for scenario in error_scenarios:
            try:
                result = scenario()
                parsed_result = json.loads(result)

                # 验证错误响应格式一致性
                assert parsed_result["success"] is False
                assert "error" in parsed_result
                assert "timestamp" in parsed_result
            except Exception as e:
                pytest.fail(f"错误处理一致性测试失败: {e}")