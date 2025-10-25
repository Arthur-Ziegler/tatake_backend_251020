"""
聊天工具集成测试套件

测试驱动开发（TDD）：先编写测试，再实现功能。
本文件包含对所有8个聊天工具的集成测试，验证工具协同工作能力。

测试覆盖范围：
1. 完整工作流程：创建任务->查询任务->搜索任务->批量操作->删除任务
2. 工具链式调用：多个工具按序调用的场景
3. 复杂业务场景：模拟真实用户使用场景
4. 错误恢复：工具调用失败时的恢复机制
5. 性能集成：多个工具调用的整体性能
6. LangGraph集成：在LangGraph环境中的工具调用

8个工具列表：
1. sesame_opener - 芝麻开门工具
2. calculator - 计算器工具
3. query_tasks - 任务查询工具
4. get_task_detail - 任务详情工具
5. create_task - 创建任务工具
6. update_task - 更新任务工具
7. delete_task - 删除任务工具
8. search_tasks - 搜索任务工具
9. batch_create_subtasks - 批量创建子任务工具

设计原则：
1. 端到端测试：模拟完整用户工作流程
2. 真实场景：基于实际使用场景设计测试用例
3. 工具协作：验证工具间的数据传递和状态管理
4. 错误处理：测试整个工具链的错误处理能力
5. 性能验证：确保集成后的性能满足要求

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import logging
import json
import time
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Dict, Any, List

# 导入测试基础设施
from .test_chat_tools_infrastructure import (
    ToolCallLogger,
    MockToolServiceContext,
    ToolResponseValidator,
    ToolTestDataFactory,
    ChatToolsTestConfig
)

# 导入所有工具
from src.domains.chat.tools.sesame_opener import sesame_opener
from src.domains.chat.tools.calculator import calculator
from src.domains.chat.tools.task_query import query_tasks, get_task_detail
from src.domains.chat.tools.task_crud import create_task, update_task, delete_task
from src.domains.chat.tools.task_search import search_tasks
from src.domains.chat.tools.task_batch import batch_create_subtasks

# 测试用例专用的logger
logger = logging.getLogger(__name__)


class TestCompleteWorkflow:
    """测试完整的任务管理工作流程"""

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_complete_task_lifecycle(self, mock_context):
        """测试完整的任务生命周期：创建->查询->更新->搜索->删除"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        # 1. 创建任务
        logger.info("🔄 步骤1：创建任务")
        task_data = {
            'title': '集成测试任务',
            'description': '这是一个完整的集成测试任务',
            'priority': 'high',
            'status': 'pending',
            'user_id': user_id
        }

        created_task = {
            'id': str(uuid4()),
            'title': task_data['title'],
            'description': task_data['description'],
            'status': task_data['status'],
            'priority': task_data['priority'],
            'user_id': user_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        task_service.create_task.return_value = created_task

        create_result = create_task.invoke(task_data)
        create_data = json.loads(create_result)

        assert ToolResponseValidator.validate_success_response(create_result), "创建任务失败"
        task_id = create_data['data']['task']['id']
        logger.info(f"✅ 任务创建成功，ID: {task_id}")

        # 2. 查询任务列表
        logger.info("🔄 步骤2：查询任务列表")
        task_service.get_tasks.return_value = [created_task]

        query_result = query_tasks.invoke({'user_id': user_id})
        query_data = json.loads(query_result)

        assert ToolResponseValidator.validate_success_response(query_result), "查询任务失败"
        assert len(query_data['data']['tasks']) == 1
        assert query_data['data']['tasks'][0]['id'] == task_id
        logger.info(f"✅ 任务查询成功，找到1个任务")

        # 3. 获取任务详情
        logger.info("🔄 步骤3：获取任务详情")
        task_service.get_task.return_value = created_task

        detail_result = get_task_detail.invoke({'task_id': task_id, 'user_id': user_id})
        detail_data = json.loads(detail_result)

        assert ToolResponseValidator.validate_success_response(detail_result), "获取任务详情失败"
        assert detail_data['data']['task']['id'] == task_id
        logger.info(f"✅ 任务详情获取成功")

        # 4. 更新任务
        logger.info("🔄 步骤4：更新任务")
        updated_task = created_task.copy()
        updated_task['status'] = 'in_progress'
        updated_task['description'] = '已更新的任务描述'

        task_service.update_task_with_tree_structure.return_value = updated_task

        update_result = update_task.invoke({
            'task_id': task_id,
            'status': 'in_progress',
            'description': '已更新的任务描述',
            'user_id': user_id
        })
        update_data = json.loads(update_result)

        assert ToolResponseValidator.validate_success_response(update_result), "更新任务失败"
        assert update_data['data']['task']['status'] == 'in_progress'
        logger.info(f"✅ 任务更新成功")

        # 5. 搜索任务
        logger.info("🔄 步骤5：搜索任务")
        task_service.get_tasks.return_value = [updated_task]

        search_result = search_tasks.invoke({
            'query': '集成测试',
            'limit': 10,
            'state': None,
            'user_id': user_id  # 注意：search_tasks的实现中user_id处理可能不同
        })
        search_data = json.loads(search_result)

        assert search_data['success'] is True, "搜索任务失败"
        assert len(search_data['tasks']) >= 1
        logger.info(f"✅ 任务搜索成功，找到{len(search_data['tasks'])}个任务")

        # 6. 删除任务
        logger.info("🔄 步骤6：删除任务")
        task_service.delete_task.return_value = {
            'deleted_task_id': task_id,
            'deleted_subtasks_count': 0
        }

        delete_result = delete_task.invoke({'task_id': task_id, 'user_id': user_id})
        delete_data = json.loads(delete_result)

        assert ToolResponseValidator.validate_success_response(delete_result), "删除任务失败"
        assert delete_data['data']['deleted_task_id'] == task_id
        logger.info(f"✅ 任务删除成功")

        logger.info("🎉 完整任务生命周期测试通过！")

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_task_decomposition_workflow(self, mock_context):
        """测试任务分解工作流程：创建父任务->批量创建子任务->管理子任务"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        # 1. 创建父任务
        logger.info("🔄 步骤1：创建父任务")
        parent_task = {
            'id': str(uuid4()),
            'title': '项目开发',
            'description': '开发一个完整的项目',
            'status': 'pending',
            'priority': 'high',
            'user_id': user_id,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        task_service.create_task.return_value = parent_task
        task_service.get_task_by_id.return_value = parent_task

        create_result = create_task.invoke({
            'title': '项目开发',
            'description': '开发一个完整的项目',
            'priority': 'high',
            'user_id': user_id
        })

        assert ToolResponseValidator.validate_success_response(create_result)
        parent_id = parent_task['id']
        logger.info(f"✅ 父任务创建成功，ID: {parent_id}")

        # 2. 批量创建子任务
        logger.info("🔄 步骤2：批量创建子任务")
        subtasks = [
            {"title": "需求分析", "description": "分析用户需求"},
            {"title": "系统设计", "description": "设计系统架构"},
            {"title": "编码实现", "description": "编写代码实现功能"},
            {"title": "测试验证", "description": "进行功能测试"}
        ]

        created_subtasks = []
        for i, subtask in enumerate(subtasks):
            created_subtasks.append({
                'id': str(uuid4()),
                'title': subtask['title'],
                'description': subtask['description'],
                'status': 'pending',
                'parent_id': parent_id,
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat()
            })

        task_service.create_task.side_effect = created_subtasks

        batch_result = batch_create_subtasks.invoke({
            'parent_id': parent_id,
            'subtasks': subtasks,
            'user_id': user_id
        })
        batch_data = json.loads(batch_result)

        assert batch_data['success'] is True
        assert batch_data['data']['total'] == 4
        assert batch_data['data']['success_count'] == 4
        assert len(batch_data['data']['created']) == 4
        logger.info(f"✅ 批量创建子任务成功，创建{batch_data['data']['success_count']}个子任务")

        # 3. 查询子任务
        logger.info("🔄 步骤3：查询子任务")
        all_tasks = [parent_task] + created_subtasks
        task_service.get_tasks.return_value = all_tasks

        query_result = query_tasks.invoke({'user_id': user_id})
        query_data = json.loads(query_result)

        assert ToolResponseValidator.validate_success_response(query_result)
        assert len(query_data['data']['tasks']) == 5  # 1个父任务 + 4个子任务
        logger.info(f"✅ 查询到所有任务，共{len(query_data['data']['tasks'])}个")

        # 4. 搜索特定子任务
        logger.info("🔄 步骤4：搜索子任务")
        design_tasks = [task for task in all_tasks if '设计' in task['title']]
        task_service.get_tasks.return_value = design_tasks

        search_result = search_tasks.invoke({
            'query': '设计',
            'limit': 10,
            'state': None,
            'user_id': user_id
        })
        search_data = json.loads(search_result)

        assert search_data['success'] is True
        assert len(search_data['tasks']) >= 1
        logger.info(f"✅ 搜索到设计相关任务{len(search_data['tasks'])}个")

        logger.info("🎉 任务分解工作流程测试通过！")


class TestToolChaining:
    """测试工具链式调用"""

    def test_sesame_opener_calculator_chain(self):
        """测试芝麻开门+计算器工具链"""

        # 1. 芝麻开门验证
        logger.info("🔄 步骤1：芝麻开门工具验证")
        sesame_result = sesame_opener.invoke({'command': '芝麻开门'})
        assert ToolResponseValidator.validate_success_response(sesame_result)
        logger.info("✅ 芝麻开门工具调用成功")

        # 2. 计算器工具链式调用
        logger.info("🔄 步骤2：计算器工具链")
        calculations = [
            ('10 + 5', '15'),
            ('20 * 3', '60'),
            ('100 / 4', '25.0'),
            ('50 - 15', '35')
        ]

        for expression, expected in calculations:
            calc_result = calculator.invoke({'expression': expression})
            assert ToolResponseValidator.validate_success_response(calc_result)
            calc_data = json.loads(calc_result)
            assert expected in calc_data['data']
            logger.info(f"✅ 计算 {expression} = {expected}")

        logger.info("🎉 芝麻开门+计算器工具链测试通过！")

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_task_management_tool_chain(self, mock_context):
        """测试任务管理工具链"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        # 创建多个相关任务
        tasks = []
        for i in range(3):
            task = {
                'id': str(uuid4()),
                'title': f'任务{i+1}',
                'description': f'第{i+1}个任务的描述',
                'status': 'pending',
                'priority': 'medium',
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            tasks.append(task)

        # 工具链：创建->查询->更新->搜索
        logger.info("🔄 任务管理工具链测试")

        # 1. 批量创建
        task_service.create_task.side_effect = tasks
        created_ids = []

        for i, task in enumerate(tasks):
            create_result = create_task.invoke({
                'title': task['title'],
                'description': task['description'],
                'user_id': user_id
            })
            assert ToolResponseValidator.validate_success_response(create_result)
            create_data = json.loads(create_result)
            created_ids.append(create_data['data']['task']['id'])
            logger.info(f"✅ 创建任务{i+1}: {task['title']}")

        # 2. 查询所有任务
        task_service.get_tasks.return_value = tasks
        query_result = query_tasks.invoke({'user_id': user_id})
        assert ToolResponseValidator.validate_success_response(query_result)
        query_data = json.loads(query_result)
        assert len(query_data['data']['tasks']) == 3
        logger.info("✅ 查询到3个任务")

        # 3. 批量更新状态
        for i, task_id in enumerate(created_ids):
            updated_task = tasks[i].copy()
            updated_task['status'] = 'completed'
            task_service.update_task_with_tree_structure.return_value = updated_task

            update_result = update_task.invoke({
                'task_id': task_id,
                'status': 'completed',
                'user_id': user_id
            })
            assert ToolResponseValidator.validate_success_response(update_result)
            logger.info(f"✅ 更新任务{i+1}状态为已完成")

        # 4. 搜索已完成的任务
        completed_tasks = [task for task in tasks if task['status'] == 'completed']
        task_service.get_tasks.return_value = completed_tasks

        search_result = search_tasks.invoke({
            'query': '已完成',
            'limit': 10,
            'state': 'completed',
            'user_id': user_id
        })
        search_data = json.loads(search_result)
        assert search_data['success'] is True
        logger.info("✅ 搜索到已完成任务")

        logger.info("🎉 任务管理工具链测试通过！")


class TestErrorHandlingAndRecovery:
    """测试错误处理和恢复机制"""

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_partial_failure_recovery(self, mock_context):
        """测试部分失败时的恢复机制"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        # 模拟部分创建失败的场景
        logger.info("🔄 测试部分失败恢复机制")

        subtasks = [
            {"title": "任务1", "description": "第一个任务"},
            {"title": "任务2", "description": "第二个任务"},
            {"title": "任务3", "description": "第三个任务"}
        ]

        parent_task = {
            'id': str(uuid4()),
            'title': '父任务',
            'user_id': user_id,
            'status': 'pending'
        }

        task_service.get_task_by_id.return_value = parent_task

        # 模拟第2个任务创建失败
        def mock_create_task(request, user_uuid):
            if request.title == "任务2":
                raise Exception("模拟创建失败")
            return {
                'id': str(uuid4()),
                'title': request.title,
                'description': request.description,
                'status': 'pending',
                'user_id': str(user_uuid),
                'created_at': datetime.now(timezone.utc).isoformat()
            }

        task_service.create_task.side_effect = mock_create_task

        # 执行批量创建
        batch_result = batch_create_subtasks.invoke({
            'parent_id': parent_task['id'],
            'subtasks': subtasks,
            'user_id': user_id
        })
        batch_data = json.loads(batch_result)

        # 验证部分成功处理
        assert batch_data['success'] is True  # 工具整体成功
        assert batch_data['data']['total'] == 3
        assert batch_data['data']['success_count'] == 2
        assert batch_data['data']['failure_count'] == 1
        assert len(batch_data['data']['created']) == 2
        assert len(batch_data['data']['failed']) == 1

        logger.info(f"✅ 部分失败恢复测试：成功{batch_data['data']['success_count']}个，失败{batch_data['data']['failure_count']}个")

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_cascading_error_handling(self, mock_context):
        """测试级联错误处理"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        logger.info("🔄 测试级联错误处理")

        # 1. 任务不存在时的错误处理
        task_service.get_task.return_value = None

        detail_result = get_task_detail.invoke({
            'task_id': str(uuid4()),
            'user_id': user_id
        })
        detail_data = json.loads(detail_result)

        assert detail_data['success'] is False
        assert 'TASK_NOT_FOUND' in str(detail_data)
        logger.info("✅ 任务不存在错误处理正确")

        # 2. 无效参数错误处理
        calc_result = calculator.invoke({'expression': 'invalid math'})
        calc_data = json.loads(calc_result)

        assert calc_data['success'] is False
        assert 'CALCULATION_ERROR' in str(calc_data)
        logger.info("✅ 计算器错误处理正确")

        # 3. 权限错误处理
        task_service.get_task_by_id.return_value = {
            'id': str(uuid4()),
            'title': '其他用户的任务',
            'user_id': str(uuid4())  # 不同的用户ID
        }

        batch_result = batch_create_subtasks.invoke({
            'parent_id': str(uuid4()),
            'subtasks': [{"title": "测试任务"}],
            'user_id': user_id
        })
        batch_data = json.loads(batch_result)

        assert batch_data['success'] is False
        assert 'PERMISSION_DENIED' in str(batch_data)
        logger.info("✅ 权限错误处理正确")

        logger.info("🎉 级联错误处理测试通过！")


class TestPerformanceIntegration:
    """集成性能测试"""

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_high_volume_operations(self, mock_context):
        """测试大量操作的性能"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        logger.info("🔄 高性能操作测试")

        # 创建大量任务
        start_time = time.time()
        created_tasks = []

        for i in range(50):
            task = {
                'id': str(uuid4()),
                'title': f'性能测试任务{i+1}',
                'description': f'第{i+1}个性能测试任务',
                'status': 'pending',
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            created_tasks.append(task)

        task_service.create_task.side_effect = created_tasks

        # 批量创建
        for i, task in enumerate(created_tasks):
            create_result = create_task.invoke({
                'title': task['title'],
                'description': task['description'],
                'user_id': user_id
            })
            assert ToolResponseValidator.validate_success_response(create_result)

        create_time = time.time() - start_time
        logger.info(f"✅ 创建50个任务耗时: {create_time:.2f}秒")

        # 批量查询
        start_time = time.time()
        task_service.get_tasks.return_value = created_tasks

        query_result = query_tasks.invoke({'user_id': user_id})
        query_time = time.time() - start_time

        assert ToolResponseValidator.validate_success_response(query_result)
        logger.info(f"✅ 查询50个任务耗时: {query_time:.2f}秒")

        # 批量搜索
        start_time = time.time()
        task_service.get_tasks.return_value = created_tasks[:25]  # 返回部分结果

        search_result = search_tasks.invoke({
            'query': '性能测试',
            'limit': 100,
            'state': None,
            'user_id': user_id
        })
        search_time = time.time() - start_time

        assert json.loads(search_result)['success'] is True
        logger.info(f"✅ 搜索任务耗时: {search_time:.2f}秒")

        # 性能断言
        assert create_time < 5.0, f"创建性能不达标: {create_time}秒"
        assert query_time < 1.0, f"查询性能不达标: {query_time}秒"
        assert search_time < 1.0, f"搜索性能不达标: {search_time}秒"

        logger.info("🎉 高性能操作测试通过！")


class TestRealWorldScenarios:
    """真实世界使用场景测试"""

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_project_management_scenario(self, mock_context):
        """测试项目管理场景"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        logger.info("🔄 项目管理场景测试")

        # 场景：用户管理一个软件开发项目

        # 1. 创建主项目任务
        project_task = {
            'id': str(uuid4()),
            'title': '开发电商平台',
            'description': '开发一个完整的B2C电商平台',
            'status': 'pending',
            'priority': 'high',
            'user_id': user_id,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        task_service.create_task.return_value = project_task
        task_service.get_task_by_id.return_value = project_task

        create_result = create_task.invoke({
            'title': '开发电商平台',
            'description': '开发一个完整的B2C电商平台',
            'priority': 'high',
            'user_id': user_id
        })
        assert ToolResponseValidator.validate_success_response(create_result)
        project_id = project_task['id']
        logger.info("✅ 创建主项目任务")

        # 2. 分解为子任务
        phases = [
            {"title": "需求分析", "description": "收集和分析用户需求"},
            {"title": "系统设计", "description": "设计系统架构和数据库"},
            {"title": "前端开发", "description": "开发用户界面"},
            {"title": "后端开发", "description": "开发API和业务逻辑"},
            {"title": "测试部署", "description": "系统测试和部署上线"}
        ]

        phase_tasks = []
        for phase in phases:
            phase_task = {
                'id': str(uuid4()),
                'title': phase['title'],
                'description': phase['description'],
                'status': 'pending',
                'parent_id': project_id,
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            phase_tasks.append(phase_task)

        task_service.create_task.side_effect = phase_tasks

        batch_result = batch_create_subtasks.invoke({
            'parent_id': project_id,
            'subtasks': phases,
            'user_id': user_id
        })
        batch_data = json.loads(batch_result)
        assert batch_data['success'] is True
        assert batch_data['data']['success_count'] == 5
        logger.info("✅ 创建5个项目阶段")

        # 3. 查询项目进度
        all_tasks = [project_task] + phase_tasks
        task_service.get_tasks.return_value = all_tasks

        query_result = query_tasks.invoke({'user_id': user_id})
        assert ToolResponseValidator.validate_success_response(query_result)
        logger.info("✅ 查询项目整体进度")

        # 4. 搜索特定阶段
        dev_tasks = [task for task in all_tasks if '开发' in task['title']]
        task_service.get_tasks.return_value = dev_tasks

        search_result = search_tasks.invoke({
            'query': '开发',
            'limit': 10,
            'state': None,
            'user_id': user_id
        })
        search_data = json.loads(search_result)
        assert search_data['success'] is True
        assert len(search_data['tasks']) >= 2
        logger.info("✅ 搜索开发相关任务")

        # 5. 更新阶段状态
        for task in phase_tasks[:2]:  # 标记前两个阶段为完成
            task['status'] = 'completed'
            task_service.update_task_with_tree_structure.return_value = task

            update_result = update_task.invoke({
                'task_id': task['id'],
                'status': 'completed',
                'user_id': user_id
            })
            assert ToolResponseValidator.validate_success_response(update_result)

        logger.info("✅ 更新项目阶段状态")

        # 6. 使用计算器计算进度
        calc_result = calculator.invoke({'expression': '2 / 5 * 100'})
        calc_data = json.loads(calc_result)
        assert ToolResponseValidator.validate_success_response(calc_result)
        logger.info(f"✅ 项目进度计算: {calc_data['data']}%")

        logger.info("🎉 项目管理场景测试通过！")

    def test_user_interaction_scenario(self):
        """测试用户交互场景"""

        logger.info("🔄 用户交互场景测试")

        # 场景：用户使用聊天助手进行任务管理

        # 1. 用户先进行芝麻开门验证
        sesame_result = sesame_opener.invoke({'command': '芝麻开门'})
        assert ToolResponseValidator.validate_success_response(sesame_result)
        logger.info("✅ 用户通过芝麻开门验证")

        # 2. 用户进行一些计算
        calculations = [
            ('8 * 5', None),  # 工作时间计算
            ('40 * 25', None),  # 周薪计算
            ('1600 / 4', None)  # 月薪计算
        ]

        for expr, _ in calculations:
            calc_result = calculator.invoke({'expression': expr})
            assert ToolResponseValidator.validate_success_response(calc_result)
            calc_data = json.loads(calc_result)
            logger.info(f"✅ 计算结果: {calc_data['data']}")

        logger.info("🎉 用户交互场景测试通过！")


class TestLangGraphIntegration:
    """LangGraph集成测试"""

    @patch('src.domains.chat.tools.utils.get_task_service_context')
    def test_tool_langgraph_compatibility(self, mock_context):
        """测试工具与LangGraph的兼容性"""

        user_id = ChatToolsTestConfig.TEST_USER_ID
        task_service = Mock()
        mock_context.return_value.__enter__.return_value = {
            'task_service': task_service,
            'points_service': Mock()
        }

        logger.info("🔄 LangGraph兼容性测试")

        # 测试所有工具的@tool装饰器兼容性
        tools_to_test = [
            (sesame_opener, {'command': '芝麻开门'}),
            (calculator, {'expression': '10 + 20'}),
            (query_tasks, {'user_id': user_id}),
            (get_task_detail, {'task_id': str(uuid4()), 'user_id': user_id}),
            (search_tasks, {'query': '测试', 'limit': 10, 'state': None}),
            (batch_create_subtasks, {
                'parent_id': str(uuid4()),
                'subtasks': [{'title': '测试子任务'}],
                'user_id': user_id
            })
        ]

        for tool, args in tools_to_test:
            try:
                # 设置mock返回值
                if hasattr(tool, 'name') and 'task' in tool.name:
                    if 'create' in tool.name:
                        task_service.create_task.return_value = {
                            'id': str(uuid4()),
                            'title': '测试任务',
                            'user_id': user_id,
                            'created_at': datetime.now(timezone.utc).isoformat()
                        }
                    elif 'query' in tool.name:
                        task_service.get_tasks.return_value = []
                    elif 'detail' in tool.name:
                        task_service.get_task.return_value = None
                    elif 'batch' in tool.name:
                        task_service.get_task_by_id.return_value = {
                            'id': str(uuid4()),
                            'user_id': user_id
                        }
                        task_service.create_task.return_value = {
                            'id': str(uuid4()),
                            'title': '子任务',
                            'user_id': user_id
                        }

                result = tool.invoke(args)

                # 验证返回值是字符串（LangGraph要求）
                assert isinstance(result, str), f"{tool.name} 返回值不是字符串"

                # 尝试解析JSON（大部分工具返回JSON）
                try:
                    parsed = json.loads(result)
                    assert isinstance(parsed, dict), f"{tool.name} 返回的JSON不是字典"
                except json.JSONDecodeError:
                    # 某些工具可能返回非JSON字符串，这也是可以接受的
                    pass

                logger.info(f"✅ {tool.name} LangGraph兼容性测试通过")

            except Exception as e:
                logger.error(f"❌ {tool.name} LangGraph兼容性测试失败: {e}")
                raise

        logger.info("🎉 所有工具LangGraph兼容性测试通过！")


if __name__ == "__main__":
    """运行所有集成测试"""
    import sys

    test_classes = [
        TestCompleteWorkflow,
        TestToolChaining,
        TestErrorHandlingAndRecovery,
        TestPerformanceIntegration,
        TestRealWorldScenarios,
        TestLangGraphIntegration
    ]

    passed_tests = 0
    total_tests = len(test_classes)

    for test_class in test_classes:
        try:
            print(f"\n🔄 运行 {test_class.__name__} 测试...")
            test_instance = test_class()

            # 运行该类中的所有测试方法
            methods = [method for method in dir(test_instance) if method.startswith('test_')]
            for method_name in methods:
                method = getattr(test_instance, method_name)
                method()

            print(f"✅ {test_class.__name__} 测试通过")
            passed_tests += 1

        except Exception as e:
            print(f"❌ {test_class.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n📊 集成测试结果: {passed_tests}/{total_tests} 通过")

    if passed_tests == total_tests:
        print("🎉 所有集成测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分集成测试失败！")
        sys.exit(1)