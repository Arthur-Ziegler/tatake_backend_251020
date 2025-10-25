"""
聊天工具测试基础设施

提供统一的测试基础设施，包括Mock工具、测试配置、
工具响应验证器等，用于所有聊天工具测试。

核心功能：
1. 统一的Mock策略和工具类
2. 工具调用日志和验证
3. JSON响应格式验证
4. 参数验证和错误处理
5. 测试数据工厂

设计原则：
1. 模块化：每个功能独立模块，便于复用
2. 可扩展：易于添加新工具测试
3. 统一性：所有工具测试使用相同的接口
4. 详细验证：完整的输入输出验证

作者：TaKeKe团队
版本：1.0.0
"""

import json
import logging
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

# 配置日志
logger = logging.getLogger(__name__)


class ToolCallLogger:
    """工具调用日志记录器"""

    def __init__(self):
        self.calls = []

    def log_call(self, tool_name: str, parameters: Dict[str, Any]) -> None:
        """记录工具调用"""
        call_info = {
            'tool_name': tool_name,
            'parameters': parameters,
            'timestamp': str(uuid4())[:8]  # 简短时间戳
        }
        self.calls.append(call_info)
        logger.info(f"🔧 工具调用: {tool_name}({len(parameters)}个参数)")

    def get_calls(self) -> List[Dict[str, Any]]:
        """获取所有调用记录"""
        return self.calls

    def clear(self) -> None:
        """清空调用记录"""
        self.calls.clear()
        logger.info("🧹 工具调用记录已清空")


class MockToolServiceContext:
    """Mock工具服务上下文"""

    def __init__(self):
        self.session = Mock()
        self.task_service = Mock()
        self.points_service = Mock()

    def get_services(self):
        """获取服务实例"""
        return {
            'session': self.session,
            'task_service': self.task_service,
            'points_service': self.points_service
        }


class ToolResponseValidator:
    """工具响应验证器"""

    @staticmethod
    def validate_success_response(response: str) -> bool:
        """验证成功响应格式"""
        try:
            data = json.loads(response)
            return (
                isinstance(data, dict) and
                data.get('success') is True and
                'data' in data and
                'timestamp' in data
            )
        except json.JSONDecodeError:
            logger.error(f"❌ 响应JSON解析失败: {response}")
            return False

    @staticmethod
    def validate_error_response(response: str) -> bool:
        """验证错误响应格式"""
        try:
            data = json.loads(response)
            return (
                isinstance(data, dict) and
                data.get('success') is False and
                'error' in data and
                'timestamp' in data
            )
        except json.JSONDecodeError:
            logger.error(f"❌ 响应JSON解析失败: {response}")
            return False


class ToolTestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_valid_task_id() -> str:
        """创建有效的任务ID"""
        return str(uuid.uuid4())

    @staticmethod
    def create_invalid_task_id() -> str:
        """创建无效的任务ID"""
        return "invalid-task-id"

    @staticmethod
    def create_valid_user_id() -> str:
        """创建有效的用户ID"""
        return "test-user-123"

    @staticmethod
    def create_sample_task_data() -> Dict[str, Any]:
        """创建示例任务数据"""
        return {
            'id': str(uuid.uuid4()),
            'title': '测试任务',
            'description': '这是一个测试任务',
            'status': 'pending',
            'priority': 'medium'
        }


class ChatToolsTestConfig:
    """聊天工具测试配置"""

    # 工具列表
    TOOL_LIST = [
        'sesame_opener',
        'calculator',
        'query_tasks',
        'get_task_detail',
        'create_task',
        'update_task',
        'delete_task',
        'search_tasks',
        'batch_create_subtasks'
    ]

    # 测试用户配置
    TEST_USER_ID = 'test-user-123'
    TEST_SESSION_ID = 'test-session-456'

    # 模拟响应配置
    MOCK_SUCCESS_RESPONSE = '{"success": true, "data": {"task_id": "test-123"}, "timestamp": "2024-01-01T00:00:00Z"}'
    MOCK_ERROR_RESPONSE = '{"success": false, "error": "参数验证失败", "error_code": "VALIDATION_ERROR", "timestamp": "2024-01-01T00:00:00Z"}'


# 导出所有公共类和函数
__all__ = [
    'ToolCallLogger',
    'MockToolServiceContext',
    'ToolResponseValidator',
    'ToolTestDataFactory',
    'ChatToolsTestConfig'
]