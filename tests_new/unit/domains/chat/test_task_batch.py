"""
聊天工具批量操作测试套件

测试驱动开发（TDD）：先编写测试，再实现功能。
本文件包含对 task_batch.py 中批量创建子任务工具的全面测试。

测试覆盖范围：
1. 批量创建子工具：batch_create_subtasks()
2. 全部成功场景
3. 部分失败场景
4. 父任务不存在场景
5. 返回格式正确性验证

设计原则：
1. 每个测试用例独立运行，不依赖其他测试
2. 覆盖正常情况、边界情况和异常情况
3. 使用清晰的测试数据和期望结果
4. 验证错误处理的完整性和友好性
5. Mock外部依赖，确保测试单元化

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Dict, Any, List

# 测试用例专用的logger
logger = logging.getLogger(__name__)


class TestBatchCreateSubtasks:
    """测试 batch_create_subtasks 函数"""

    @patch('src.domains.chat.tools.task_batch.get_task_service_context')
    @patch('src.domains.chat.tools.task_batch.safe_uuid_convert')
    def test_batch_create_subtasks_all_success(self, mock_uuid_convert, mock_context):
        """测试批量创建子任务全部成功场景"""
        # 导入要测试的函数
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 设置Mock数据
        parent_id = str(uuid4())
        user_id = str(uuid4())
        mock_parent_uuid = uuid4()
        mock_user_uuid = uuid4()

        # 设置UUID转换Mock
        mock_uuid_convert.side_effect = lambda x, required=False: (
            mock_parent_uuid if x == parent_id else
            mock_user_uuid if x == user_id else
            None
        )

        # 设置子任务数据
        subtasks = [
            {"title": "子任务1", "description": "描述1"},
            {"title": "子任务2", "description": "描述2"},
            {"title": "子任务3", "description": "描述3"}
        ]

        # Mock服务上下文
        mock_task_service = Mock()
        mock_session = Mock()
        mock_context.return_value.__enter__.return_value = {
            'session': mock_session,
            'task_service': mock_task_service,
            'points_service': Mock()
        }

        # Mock父任务存在
        mock_task_service.get_task_by_id.return_value = {
            'id': str(mock_parent_uuid),
            'title': '父任务',
            'user_id': str(mock_user_uuid)
        }

        # Mock创建任务成功
        def mock_create_task(request, user_uuid):
            return {
                'id': str(uuid4()),
                'title': request.title,
                'description': request.description,
                'parent_id': request.parent_id,
                'user_id': user_uuid,
                'state': request.status or 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }

        mock_task_service.create_task.side_effect = mock_create_task

        # 执行测试
        result = batch_create_subtasks_core(parent_id, subtasks, user_id)

        # 验证结果
        assert isinstance(result, dict)
        assert result['success'] is True
        assert 'data' in result
        assert 'created' in result['data']
        assert 'failed' in result['data']
        assert len(result['data']['created']) == 3
        assert len(result['data']['failed']) == 0

        # 验证每个创建的子任务
        for i, created_task in enumerate(result['data']['created']):
            assert created_task['title'] == subtasks[i]['title']
            assert created_task['description'] == subtasks[i]['description']
            assert 'id' in created_task

        # 验证服务调用
        assert mock_task_service.get_task_by_id.called
        assert mock_task_service.create_task.call_count == 3

    @patch('src.domains.chat.tools.task_batch.get_task_service_context')
    @patch('src.domains.chat.tools.task_batch.safe_uuid_convert')
    def test_batch_create_subtasks_partial_failure(self, mock_uuid_convert, mock_context):
        """测试批量创建子任务部分失败场景"""
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 设置Mock数据
        parent_id = str(uuid4())
        user_id = str(uuid4())
        mock_parent_uuid = uuid4()
        mock_user_uuid = uuid4()

        mock_uuid_convert.side_effect = lambda x, required=False: (
            mock_parent_uuid if x == parent_id else
            mock_user_uuid if x == user_id else
            None
        )

        # 设置子任务数据
        subtasks = [
            {"title": "子任务1", "description": "描述1"},
            {"title": "子任务2", "description": "描述2"},
            {"title": "子任务3", "description": "描述3"}
        ]

        # Mock服务上下文
        mock_task_service = Mock()
        mock_session = Mock()
        mock_context.return_value.__enter__.return_value = {
            'session': mock_session,
            'task_service': mock_task_service,
            'points_service': Mock()
        }

        # Mock父任务存在
        mock_task_service.get_task_by_id.return_value = {
            'id': str(mock_parent_uuid),
            'title': '父任务',
            'user_id': str(mock_user_uuid)
        }

        # Mock创建任务：第1、3个成功，第2个失败
        def mock_create_task(request, user_uuid):
            if request.title == "子任务2":
                raise Exception("创建失败：标题重复")
            return {
                'id': str(uuid4()),
                'title': request.title,
                'description': request.description,
                'parent_id': request.parent_id,
                'user_id': user_uuid,
                'state': request.status or 'pending',
                'created_at': datetime.now(timezone.utc).isoformat()
            }

        mock_task_service.create_task.side_effect = mock_create_task

        # 执行测试
        result = batch_create_subtasks_core(parent_id, subtasks, user_id)

        # 验证结果
        assert isinstance(result, dict)
        assert result['success'] is True  # 整体成功，因为是部分成功
        assert 'data' in result
        assert 'created' in result['data']
        assert 'failed' in result['data']
        assert len(result['data']['created']) == 2
        assert len(result['data']['failed']) == 1

        # 验证失败的任务信息
        failed_task = result['data']['failed'][0]
        assert failed_task['title'] == "子任务2"
        assert 'error' in failed_task
        assert "创建失败：标题重复" in failed_task['error']

    @patch('src.domains.chat.tools.task_batch.get_task_service_context')
    @patch('src.domains.chat.tools.task_batch.safe_uuid_convert')
    def test_batch_create_subtasks_parent_not_found(self, mock_uuid_convert, mock_context):
        """测试父任务不存在场景"""
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 设置Mock数据
        parent_id = str(uuid4())
        user_id = str(uuid4())
        mock_parent_uuid = uuid4()
        mock_user_uuid = uuid4()

        mock_uuid_convert.side_effect = lambda x, required=False: (
            mock_parent_uuid if x == parent_id else
            mock_user_uuid if x == user_id else
            None
        )

        # 设置子任务数据
        subtasks = [
            {"title": "子任务1", "description": "描述1"}
        ]

        # Mock服务上下文
        mock_task_service = Mock()
        mock_session = Mock()
        mock_context.return_value.__enter__.return_value = {
            'session': mock_session,
            'task_service': mock_task_service,
            'points_service': Mock()
        }

        # Mock父任务不存在
        mock_task_service.get_task_by_id.return_value = None

        # 执行测试
        result = batch_create_subtasks_core(parent_id, subtasks, user_id)

        # 验证结果
        assert isinstance(result, dict)
        assert result['success'] is False
        assert 'error' in result
        assert "父任务不存在" in result['error']
        assert 'error_code' in result
        assert result['error_code'] == 'PARENT_TASK_NOT_FOUND'

    @patch('src.domains.chat.tools.task_batch.get_task_service_context')
    @patch('src.domains.chat.tools.task_batch.safe_uuid_convert')
    def test_batch_create_subtasks_empty_subtasks(self, mock_uuid_convert, mock_context):
        """测试空子任务列表场景"""
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 设置Mock数据
        parent_id = str(uuid4())
        user_id = str(uuid4())
        mock_parent_uuid = uuid4()
        mock_user_uuid = uuid4()

        mock_uuid_convert.side_effect = lambda x, required=False: (
            mock_parent_uuid if x == parent_id else
            mock_user_uuid if x == user_id else
            None
        )

        # Mock服务上下文
        mock_task_service = Mock()
        mock_session = Mock()
        mock_context.return_value.__enter__.return_value = {
            'session': mock_session,
            'task_service': mock_task_service,
            'points_service': Mock()
        }

        # Mock父任务存在
        mock_task_service.get_task_by_id.return_value = {
            'id': str(mock_parent_uuid),
            'title': '父任务',
            'user_id': str(mock_user_uuid)
        }

        # 执行测试：空子任务列表
        result = batch_create_subtasks_core(parent_id, [], user_id)

        # 验证结果
        assert isinstance(result, dict)
        assert result['success'] is True
        assert 'data' in result
        assert result['data']['created'] == []
        assert result['data']['failed'] == []
        assert result['data']['total'] == 0

        # 验证没有调用创建任务
        assert not mock_task_service.create_task.called

    @patch('src.domains.chat.tools.task_batch.get_task_service_context')
    @patch('src.domains.chat.tools.task_batch.safe_uuid_convert')
    def test_batch_create_subtasks_permission_denied(self, mock_uuid_convert, mock_context):
        """测试权限不足场景（用户不是父任务的拥有者）"""
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 设置Mock数据
        parent_id = str(uuid4())
        user_id = str(uuid4())
        other_user_id = str(uuid4())
        mock_parent_uuid = uuid4()
        mock_user_uuid = uuid4()
        mock_other_user_uuid = uuid4()

        mock_uuid_convert.side_effect = lambda x, required=False: (
            mock_parent_uuid if x == parent_id else
            mock_user_uuid if x == user_id else
            mock_other_user_uuid if x == other_user_id else
            None
        )

        # 设置子任务数据
        subtasks = [
            {"title": "子任务1", "description": "描述1"}
        ]

        # Mock服务上下文
        mock_task_service = Mock()
        mock_session = Mock()
        mock_context.return_value.__enter__.return_value = {
            'session': mock_session,
            'task_service': mock_task_service,
            'points_service': Mock()
        }

        # Mock父任务存在，但属于其他用户
        mock_task_service.get_task_by_id.return_value = {
            'id': str(mock_parent_uuid),
            'title': '父任务',
            'user_id': str(mock_other_user_uuid)  # 其他用户的ID
        }

        # 执行测试
        result = batch_create_subtasks_core(parent_id, subtasks, user_id)

        # 验证结果
        assert isinstance(result, dict)
        assert result['success'] is False
        assert 'error' in result
        assert "权限不足" in result['error']
        assert 'error_code' in result
        assert result['error_code'] == 'PERMISSION_DENIED'

    def test_batch_create_subtasks_invalid_subtask_format(self):
        """测试无效子任务格式"""
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 设置Mock数据
        parent_id = str(uuid4())
        user_id = str(uuid4())

        # 设置无效格式的子任务数据
        invalid_subtasks = [
            "invalid_string_format",  # 字符串而非字典
            {"description": "缺少title"},  # 缺少必需的title字段
            {"title": "", "description": "空标题"}  # 空标题
        ]

        # Mock UUID转换
        with patch('src.domains.chat.tools.task_batch.safe_uuid_convert') as mock_uuid_convert:
            mock_uuid_convert.return_value = uuid4()

            # Mock上下文
            with patch('src.domains.chat.tools.task_batch.get_task_service_context') as mock_context:
                mock_task_service = Mock()
                mock_context.return_value.__enter__.return_value = {
                    'session': Mock(),
                    'task_service': mock_task_service,
                    'points_service': Mock()
                }

                # Mock父任务存在
                mock_task_service.get_task_by_id.return_value = {
                    'id': str(uuid4()),
                    'title': '父任务',
                    'user_id': str(uuid4())
                }

                # 执行测试
                result = batch_create_subtasks_core(parent_id, invalid_subtasks, user_id)

                # 验证结果
                assert isinstance(result, dict)
                assert result['success'] is False
                assert 'error' in result
                assert "子任务格式无效" in result['error']


class TestBatchCreateSubtasksIntegration:
    """批量创建子任务集成测试"""

    def test_response_format_consistency(self):
        """测试响应格式一致性"""
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 测试成功响应格式
        with patch('src.domains.chat.tools.task_batch.get_task_service_context') as mock_context, \
             patch('src.domains.chat.tools.task_batch.safe_uuid_convert') as mock_uuid_convert:

            # 设置Mock
            mock_uuid_convert.return_value = uuid4()
            mock_task_service = Mock()
            mock_task_service.get_task_by_id.return_value = {
                'id': str(uuid4()),
                'title': '父任务',
                'user_id': str(uuid4())
            }
            mock_context.return_value.__enter__.return_value = {
                'session': Mock(),
                'task_service': mock_task_service,
                'points_service': Mock()
            }

            # 执行测试
            result = batch_create_subtasks_core(str(uuid4()), [], str(uuid4()))

            # 验证响应格式一致性
            assert 'timestamp' in result
            assert isinstance(result['timestamp'], str)

            # 验证时间戳格式
            try:
                datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                pytest.fail("时间戳格式无效")

    def test_error_handling_comprehensive(self):
        """测试全面的错误处理"""
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 测试各种错误场景
        error_scenarios = [
            # (parent_id, subtasks, user_id, expected_error_pattern)
            (None, [{"title": "test"}], str(uuid4()), "父任务ID不能为空"),
            (str(uuid4()), [{"title": "test"}], None, "用户ID不能为空"),
            (str(uuid4()), [{"title": "test"}], "invalid_uuid", "无效的用户ID格式"),
        ]

        for parent_id, subtasks, user_id, expected_error in error_scenarios:
            with patch('src.domains.chat.tools.task_batch.safe_uuid_convert') as mock_uuid_convert:
                # 设置UUID转换抛出异常
                if "invalid_uuid" in str(user_id):
                    mock_uuid_convert.side_effect = ValueError("无效的UUID格式")
                elif parent_id is None or user_id is None:
                    mock_uuid_convert.return_value = None
                else:
                    mock_uuid_convert.return_value = uuid4()

                result = batch_create_subtasks_core(parent_id, subtasks, user_id)

                assert result['success'] is False
                assert expected_error in result['error']


# 性能测试
class TestBatchCreateSubtasksPerformance:
    """批量创建子任务性能测试"""

    def test_large_batch_performance(self):
        """测试大批量子任务创建性能"""
        import time
        from src.domains.chat.tools.task_batch import batch_create_subtasks_core

        # 创建大量子任务
        large_subtasks = [
            {"title": f"子任务{i}", "description": f"描述{i}"}
            for i in range(100)
        ]

        start_time = time.time()

        with patch('src.domains.chat.tools.task_batch.get_task_service_context') as mock_context, \
             patch('src.domains.chat.tools.task_batch.safe_uuid_convert') as mock_uuid_convert:

            # 设置Mock
            mock_uuid_convert.return_value = uuid4()
            mock_task_service = Mock()
            mock_task_service.get_task_by_id.return_value = {
                'id': str(uuid4()),
                'title': '父任务',
                'user_id': str(uuid4())
            }

            # Mock快速创建
            def mock_create_task(request, user_uuid):
                return {'id': str(uuid4()), 'title': request.title}

            mock_task_service.create_task.side_effect = mock_create_task
            mock_context.return_value.__enter__.return_value = {
                'session': Mock(),
                'task_service': mock_task_service,
                'points_service': Mock()
            }

            result = batch_create_subtasks_core(str(uuid4()), large_subtasks, str(uuid4()))

        end_time = time.time()
        execution_time = end_time - start_time

        # 验证性能要求（应该在合理时间内完成）
        assert execution_time < 2.0, f"批量创建100个子任务耗时过长: {execution_time}秒"
        assert result['success'] is True
        assert len(result['data']['created']) == 100