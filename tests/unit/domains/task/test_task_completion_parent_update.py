"""
Task父任务完成度递归更新测试套件

测试TaskService中新增的父任务完成度自动更新功能：
1. TaskRepository.get_all_leaf_tasks方法测试
2. TaskService.update_parent_completion_percentage方法测试
3. TaskService.complete_task集成测试（包含递归更新）
4. 多层任务树的递归更新测试
5. 边界条件和异常场景测试

遵循TDD原则，专注于递归更新业务逻辑验证。

作者：TaTakeKe团队
版本：2.0.0 - Phase 2实施
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.service import TaskService
from src.domains.task.repository import TaskRepository
from src.domains.points.service import PointsService
from src.domains.task.exceptions import TaskNotFoundException, TaskPermissionDeniedException


@pytest.mark.unit
class TestTaskParentCompletionUpdate:
    """Task父任务完成度更新测试类"""

    def test_get_all_leaf_tasks_basic(self, task_db_session):
        """测试获取叶子任务的基本功能"""
        # 创建Repository实例
        task_repo = TaskRepository(task_db_session)

        # 创建测试用户
        user_id = str(uuid4())

        # 创建任务树结构：
        # root1
        # ├── child1.1 (叶子)
        # ├── child1.2 (叶子)
        # └── child1.3
        #     └── grandchild1.3.1 (叶子)
        # root2 (叶子)

        # 创建根任务
        root1 = task_repo.create({
            "user_id": user_id,
            "title": "根任务1",
            "status": TaskStatusConst.PENDING
        })

        root2 = task_repo.create({
            "user_id": user_id,
            "title": "根任务2（叶子）",
            "status": TaskStatusConst.PENDING
        })

        # 创建第一层子任务
        child1_1 = task_repo.create({
            "user_id": user_id,
            "title": "子任务1.1（叶子）",
            "status": TaskStatusConst.PENDING,
            "parent_id": root1.id
        })

        child1_2 = task_repo.create({
            "user_id": user_id,
            "title": "子任务1.2（叶子）",
            "status": TaskStatusConst.PENDING,
            "parent_id": root1.id
        })

        child1_3 = task_repo.create({
            "user_id": user_id,
            "title": "子任务1.3",
            "status": TaskStatusConst.PENDING,
            "parent_id": root1.id
        })

        # 创建第二层子任务
        grandchild = task_repo.create({
            "user_id": user_id,
            "title": "孙子任务1.3.1（叶子）",
            "status": TaskStatusConst.PENDING,
            "parent_id": child1_3.id
        })

        # 获取所有叶子任务
        leaf_tasks = task_repo.get_all_leaf_tasks(user_id)

        # 验证结果：应该有3个叶子任务（child1.1, child1.2, grandchild, root2）
        leaf_ids = [task.id for task in leaf_tasks]
        expected_leaf_ids = [child1_1.id, child1_2.id, grandchild.id, root2.id]

        assert len(leaf_tasks) == 4, f"期望4个叶子任务，实际获得{len(leaf_tasks)}个"

        for expected_id in expected_leaf_ids:
            assert expected_id in leaf_ids, f"叶子任务 {expected_id} 应该在结果中"

        # 验证非叶子任务不在结果中
        non_leaf_ids = [root1.id, child1_3.id]
        for non_leaf_id in non_leaf_ids:
            assert non_leaf_id not in leaf_ids, f"非叶子任务 {non_leaf_id} 不应该在结果中"

    def test_get_all_leaf_tasks_with_deleted(self, task_db_session):
        """测试叶子任务查询中的软删除过滤"""
        task_repo = TaskRepository(task_db_session)
        user_id = str(uuid4())

        # 创建任务结构
        parent = task_repo.create({
            "user_id": user_id,
            "title": "父任务",
            "status": TaskStatusConst.PENDING
        })

        leaf1 = task_repo.create({
            "user_id": user_id,
            "title": "叶子任务1",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        leaf2 = task_repo.create({
            "user_id": user_id,
            "title": "叶子任务2（已删除）",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        # 软删除一个叶子任务
        leaf2.is_deleted = True
        task_db_session.commit()

        # 不包含已删除任务的查询
        leaf_tasks_active = task_repo.get_all_leaf_tasks(user_id, include_deleted=False)
        leaf_ids_active = [task.id for task in leaf_tasks_active]

        assert len(leaf_tasks_active) == 1, f"期望1个活跃叶子任务，实际获得{len(leaf_tasks_active)}个"
        assert leaf1.id in leaf_ids_active, "活跃的叶子任务应该在结果中"
        assert leaf2.id not in leaf_ids_active, "已删除的叶子任务不应该在结果中"

        # 包含已删除任务的查询
        leaf_tasks_all = task_repo.get_all_leaf_tasks(user_id, include_deleted=True)
        leaf_ids_all = [task.id for task in leaf_tasks_all]

        assert len(leaf_tasks_all) == 2, f"期望2个叶子任务（包含已删除），实际获得{len(leaf_tasks_all)}个"
        assert leaf1.id in leaf_ids_all, "活跃的叶子任务应该在结果中"
        assert leaf2.id in leaf_ids_all, "已删除的叶子任务应该在结果中"

    def test_update_parent_completion_percentage_basic(self, task_service, task_repository):
        """测试基本父任务完成度更新"""
        user_id = str(uuid4())

        # 创建任务树：
        # parent
        # ├── child1
        # └── child2

        parent = task_repository.create({
            "user_id": user_id,
            "title": "父任务",
            "status": TaskStatusConst.PENDING
        })

        child1 = task_repository.create({
            "user_id": user_id,
            "title": "子任务1",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        child2 = task_repository.create({
            "user_id": user_id,
            "title": "子任务2",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        # 完成一个子任务
        task_service.complete_task(user_id, child1.id)

        # 验证父任务完成度更新
        updated_parent = task_repository.get_by_id(parent.id, user_id)
        expected_percentage = 50.0  # 1/2 * 100

        assert updated_parent.completion_percentage == expected_percentage, \
            f"父任务完成度应该是{expected_percentage}%，实际是{updated_parent.completion_percentage}%"

    def test_update_parent_completion_percentage_multiple_levels(self, task_service, task_repository):
        """测试多层任务树的递归更新"""
        user_id = str(uuid4())

        # 创建三层任务树：
        # grandparent
        # └── parent
        #     ├── child1
        #     └── child2

        grandparent = task_repository.create({
            "user_id": user_id,
            "title": "祖父任务",
            "status": TaskStatusConst.PENDING
        })

        parent = task_repository.create({
            "user_id": user_id,
            "title": "父任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": grandparent.id
        })

        child1 = task_repository.create({
            "user_id": user_id,
            "title": "子任务1",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        child2 = task_repository.create({
            "user_id": user_id,
            "title": "子任务2",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        # 完成一个子任务
        task_service.complete_task(user_id, child1.id)

        # 验证直接父任务完成度
        updated_parent = task_repository.get_by_id(parent.id, user_id)
        assert updated_parent.completion_percentage == 50.0, \
            f"父任务完成度应该是50.0%，实际是{updated_parent.completion_percentage}%"

        # 验证祖父任务完成度
        updated_grandparent = task_repository.get_by_id(grandparent.id, user_id)
        assert updated_grandparent.completion_percentage == 50.0, \
            f"祖父任务完成度应该是50.0%，实际是{updated_grandparent.completion_percentage}%"

        # 完成第二个子任务
        task_service.complete_task(user_id, child2.id)

        # 验证所有父任务都达到100%
        final_parent = task_repository.get_by_id(parent.id, user_id)
        final_grandparent = task_repository.get_by_id(grandparent.id, user_id)

        assert final_parent.completion_percentage == 100.0, "父任务完成度应该是100%"
        assert final_grandparent.completion_percentage == 100.0, "祖父任务完成度应该是100%"

    def test_update_parent_completion_percentage_no_parent(self, task_service, task_repository):
        """测试没有父任务的叶子任务完成"""
        user_id = str(uuid4())

        # 创建独立的叶子任务
        leaf_task = task_repository.create({
            "user_id": user_id,
            "title": "独立任务",
            "status": TaskStatusConst.PENDING
        })

        # 完成任务（应该不会抛出异常）
        result = task_service.complete_task(user_id, leaf_task.id)

        assert result["success"] is True, "独立任务应该能正常完成"
        assert result["points_awarded"] > 0, "应该获得积分"

    def test_update_parent_completion_percentage_empty_parent(self, task_service, task_repository):
        """测试父任务没有子任务的情况"""
        user_id = str(uuid4())

        # 创建父任务（暂时是叶子）
        parent = task_repository.create({
            "user_id": user_id,
            "title": "父任务",
            "status": TaskStatusConst.PENDING
        })

        # 为父任务添加子任务
        child = task_repository.create({
            "user_id": user_id,
            "title": "子任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        # 手动删除子任务（模拟异常情况）
        child.is_deleted = True
        task_repository.session.commit()

        # 尝试更新父任务完成度
        result = task_service.update_parent_completion_percentage(user_id, child.id)

        # 应该处理没有子任务的情况
        assert result["success"] is True, "更新应该成功"

        # 验证父任务完成度为0
        updated_parent = task_repository.get_by_id(parent.id, user_id)
        assert updated_parent.completion_percentage == 0.0, "没有子任务的父任务完成度应该是0%"

    def test_complete_task_with_parent_update_integration(self, task_service, task_repository):
        """测试任务完成与父任务更新的集成"""
        user_id = str(uuid4())

        # 创建三层任务树
        root = task_repository.create({
            "user_id": user_id,
            "title": "根任务",
            "status": TaskStatusConst.PENDING
        })

        parent = task_repository.create({
            "user_id": user_id,
            "title": "中间任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": root.id
        })

        leaf = task_repository.create({
            "user_id": user_id,
            "title": "叶子任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        # 获取初始积分
        initial_points = task_service.points_service.get_balance(user_id)

        # 完成叶子任务
        result = task_service.complete_task(user_id, leaf.id)

        # 验证任务完成成功
        assert result["success"] is True, "任务完成应该成功"
        assert result["points_awarded"] > 0, "应该获得积分"

        # 验证积分增加
        final_points = task_service.points_service.get_balance(user_id)
        assert final_points > initial_points, "积分应该增加"

        # 验证父任务完成度自动更新
        updated_parent = task_repository.get_by_id(parent.id, user_id)
        updated_root = task_repository.get_by_id(root.id, user_id)

        assert updated_parent.completion_percentage == 100.0, "直接父任务完成度应该是100%"
        assert updated_root.completion_percentage == 100.0, "根任务完成度应该是100%"

    def test_parent_update_with_different_users(self, task_service, task_repository):
        """测试不同用户的任务不会互相影响完成度更新"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())

        # 用户1的任务树
        user1_parent = task_repository.create({
            "user_id": user1_id,
            "title": "用户1的父任务",
            "status": TaskStatusConst.PENDING
        })

        user1_child = task_repository.create({
            "user_id": user1_id,
            "title": "用户1的子任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": user1_parent.id
        })

        # 用户2的任务树
        user2_parent = task_repository.create({
            "user_id": user2_id,
            "title": "用户2的父任务",
            "status": TaskStatusConst.PENDING
        })

        user2_child = task_repository.create({
            "user_id": user2_id,
            "title": "用户2的子任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": user2_parent.id
        })

        # 完成用户1的任务
        task_service.complete_task(user1_id, user1_child.id)

        # 验证只有用户1的父任务更新了
        updated_user1_parent = task_repository.get_by_id(user1_parent.id, user1_id)
        updated_user2_parent = task_repository.get_by_id(user2_parent.id, user2_id)

        assert updated_user1_parent.completion_percentage == 100.0, "用户1的父任务应该更新"
        assert updated_user2_parent.completion_percentage == 0.0, "用户2的父任务不应该更新"

    def test_parent_update_error_handling(self, task_service, task_repository):
        """测试父任务更新时的错误处理"""
        user_id = str(uuid4())

        # 创建任务树
        parent = task_repository.create({
            "user_id": user_id,
            "title": "父任务",
            "status": TaskStatusConst.PENDING
        })

        child = task_repository.create({
            "user_id": user_id,
            "title": "子任务",
            "status": TaskStatusConst.PENDING,
            "parent_id": parent.id
        })

        # 手动破坏数据库连接（模拟错误）
        # 这里我们测试即使父任务更新失败，任务完成本身也应该成功
        original_method = task_service.update_parent_completion_percentage

        def mock_failing_update(user_id, task_id):
            raise Exception("模拟数据库连接失败")

        # 临时替换方法以模拟失败
        task_service.update_parent_completion_percentage = mock_failing_update

        try:
            # 完成子任务
            result = task_service.complete_task(user_id, child.id)

            # 任务完成应该成功，即使父任务更新失败
            assert result["success"] is True, "任务完成应该成功"
            assert result["points_awarded"] > 0, "应该获得积分"

        finally:
            # 恢复原方法
            task_service.update_parent_completion_percentage = original_method