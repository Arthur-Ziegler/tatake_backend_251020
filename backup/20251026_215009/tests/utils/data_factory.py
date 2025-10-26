"""
测试数据工厂

提供统一的测试数据生成功能，支持：
1. 各种域的对象创建
2. 边界条件数据生成
3. 批量数据创建
4. 关联数据管理

设计原则：
1. 工厂模式：统一的创建接口
2. 链式调用：支持关联对象创建
3. 随机性：支持可重现的随机数据
4. 边界覆盖：支持各种边界条件测试
"""

import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Union
from uuid import UUID, uuid4

from faker import Faker

# 导入相关域的模型
from src.domains.auth.models import Auth
from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.top3.models import TaskTop3

# 设置中文Faker
fake = Faker('zh_CN')


class TestDataFactory:
    """测试数据工厂"""

    def __init__(self, seed: Optional[int] = None):
        """
        初始化测试数据工厂

        Args:
            seed: 随机种子，用于可重现的测试数据
        """
        if seed:
            fake.seed_instance(seed)
            random.seed(seed)

    # === 认证域数据工厂 ===

    def create_user(self, **overrides) -> Auth:
        """
        创建测试用户

        Args:
            **overrides: 覆盖默认字段

        Returns:
            Auth: 用户对象
        """
        defaults = {
            "id": str(uuid4()),
            "wechat_openid": fake.uuid4(),
            "wechat_nickname": fake.name(),
            "wechat_avatar": fake.image_url(),
            "is_guest": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        defaults.update(overrides)
        return Auth(**defaults)

    def create_guest_user(self, **overrides) -> Auth:
        """创建游客用户"""
        defaults = {
            "id": str(uuid4()),
            "wechat_openid": fake.uuid4(),
            "wechat_nickname": f"游客_{fake.user_name()}",
            "wechat_avatar": fake.image_url(),
            "is_guest": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        defaults.update(overrides)
        return Auth(**defaults)

    # === 任务域数据工厂 ===

    def create_task(self, user_id: Optional[Union[str, UUID]] = None, **overrides) -> Task:
        """
        创建测试任务

        Args:
            user_id: 用户ID，如果不提供则自动生成
            **overrides: 覆盖默认字段

        Returns:
            Task: 任务对象
        """
        if user_id is None:
            user_id = uuid4()

        defaults = {
            "title": fake.sentence(nb_words=6),
            "description": fake.paragraph(nb_sentences=3),
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM,
            "is_deleted": False,
            "completion_percentage": 0.0,
            "tags": fake.words(nb=3),
            "service_ids": [uuid4() for _ in range(random.randint(0, 2))],
            "due_date": fake.future_date(end_date="+30d"),
            "planned_start_time": fake.date_time_this_month(),
            "planned_end_time": fake.date_time_this_month(),
        }
        defaults.update(overrides)

        # 确保user_id是UUID类型
        if isinstance(user_id, str):
            from src.core.uuid_converter import UUIDConverter
            user_id = UUIDConverter.ensure_uuid(user_id)

        return Task(user_id=user_id, **defaults)

    def create_task_tree(self, user_id: Union[str, UUID], depth: int = 3, breadth: int = 3) -> List[Task]:
        """
        创建任务树

        Args:
            user_id: 用户ID
            depth: 树的深度
            breadth: 每个节点的子节点数量

        Returns:
            List[Task]: 任务树列表，根任务在前
        """
        if isinstance(user_id, str):
            from src.core.uuid_converter import UUIDConverter
            user_id = UUIDConverter.ensure_uuid(user_id)

        tasks = []

        def _create_tree(current_depth: int, parent_id: Optional[UUID] = None) -> List[Task]:
            if current_depth <= 0:
                return []

            current_tasks = []
            for i in range(breadth):
                task = self.create_task(
                    user_id=user_id,
                    parent_id=parent_id,
                    title=f"{'  ' * (depth - current_depth)}任务 {current_depth}-{i+1}"
                )
                current_tasks.append(task)
                tasks.append(task)

                # 递归创建子任务
                children = _create_tree(current_depth - 1, task.id)

            return current_tasks

        # 创建根任务
        root_tasks = _create_tree(depth)
        return tasks

    def create_completed_task(self, user_id: Optional[Union[str, UUID]] = None, **overrides) -> Task:
        """创建已完成的任务"""
        defaults = {
            "status": TaskStatusConst.COMPLETED,
            "completion_percentage": 100.0,
            "title": f"已完成任务_{fake.sentence(nb_words=4)}",
        }
        defaults.update(overrides)
        return self.create_task(user_id=user_id, **defaults)

    def create_tasks_with_status(self, user_id: Union[str, UUID], status_counts: Dict[str, int]) -> List[Task]:
        """
        创建指定状态数量的任务

        Args:
            user_id: 用户ID
            status_counts: 状态数量字典，如 {"pending": 3, "completed": 5}

        Returns:
            List[Task]: 任务列表
        """
        tasks = []
        for status, count in status_counts.items():
            for _ in range(count):
                task = self.create_task(
                    user_id=user_id,
                    status=status,
                    title=f"{status}任务_{fake.sentence(nb_words=4)}"
                )
                tasks.append(task)
        return tasks

    # === Top3域数据工厂 ===

    def create_top3(self, user_id: Union[str, UUID],
                    task_ids: Optional[List[Union[str, UUID]]] = None,
                    target_date: Optional[datetime] = None,
                    **overrides) -> TaskTop3:
        """
        创建Top3记录

        Args:
            user_id: 用户ID
            task_ids: 任务ID列表，如果不提供则自动生成
            target_date: 目标日期，默认为今天
            **overrides: 覆盖默认字段

        Returns:
            TaskTop3: Top3记录对象
        """
        if task_ids is None:
            task_ids = [str(uuid4()) for _ in range(3)]

        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        # 转换为正确的格式
        formatted_task_ids = [
            {"task_id": str(task_id), "position": i + 1}
            for i, task_id in enumerate(task_ids)
        ]

        defaults = {
            "user_id": str(user_id),
            "top_date": target_date,
            "task_ids": formatted_task_ids,
            "points_consumed": 300,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        defaults.update(overrides)
        return TaskTop3(**defaults)

    # === 边界条件数据工厂 ===

    def create_task_with_long_title(self, user_id: Union[str, UUID], length: int = 100) -> Task:
        """创建标题长度达到边界的任务"""
        title = "A" * length
        return self.create_task(user_id=user_id, title=title)

    def create_task_with_unicode_title(self, user_id: Union[str, UUID]) -> Task:
        """创建包含Unicode字符的任务"""
        title = "测试🚀任务💡包含🎯特殊符号"
        return self.create_task(user_id=user_id, title=title)

    def create_tasks_with_due_dates(self, user_id: Union[str, UUID],
                                  start_days: int = -30,
                                  end_days: int = 30,
                                  count: int = 10) -> List[Task]:
        """
        创建具有不同截止日期的任务

        Args:
            user_id: 用户ID
            start_days: 开始天数（负数表示过去）
            end_days: 结束天数（正数表示未来）
            count: 任务数量

        Returns:
            List[Task]: 任务列表
        """
        tasks = []
        base_date = datetime.now(timezone.utc)

        for i in range(count):
            # 在时间范围内均匀分布
            days_offset = start_days + (end_days - start_days) * i / max(count - 1, 1)
            due_date = base_date + timedelta(days=int(days_offset))

            task = self.create_task(
                user_id=user_id,
                due_date=due_date,
                title=f"截止日期任务_{i+1}"
            )
            tasks.append(task)

        return tasks

    # === 批量创建工具 ===

    def create_user_with_tasks(self, task_count: int = 10,
                              completed_ratio: float = 0.3) -> tuple[Auth, List[Task]]:
        """
        创建用户及其任务

        Args:
            task_count: 任务数量
            completed_ratio: 已完成任务比例

        Returns:
            tuple: (用户, 任务列表)
        """
        user = self.create_user()

        completed_count = int(task_count * completed_ratio)
        pending_count = task_count - completed_count

        tasks = []
        # 创建已完成任务
        for _ in range(completed_count):
            task = self.create_completed_task(user_id=user.id)
            tasks.append(task)

        # 创建未完成任务
        for _ in range(pending_count):
            task = self.create_task(user_id=user.id)
            tasks.append(task)

        return user, tasks

    def create_complete_test_data(self) -> Dict[str, Any]:
        """
        创建完整的测试数据集

        Returns:
            Dict: 包含各种测试数据的字典
        """
        # 创建用户
        user1 = self.create_user(wechat_nickname="测试用户1")
        user2 = self.create_user(wechat_nickname="测试用户2")
        guest = self.create_guest_user()

        # 创建任务
        user1_tasks = self.create_tasks_with_status(user1.id, {
            TaskStatusConst.PENDING: 3,
            TaskStatusConst.IN_PROGRESS: 2,
            TaskStatusConst.COMPLETED: 5
        })

        user2_tasks = self.create_tasks_with_status(user2.id, {
            TaskStatusConst.PENDING: 2,
            TaskStatusConst.COMPLETED: 1
        })

        # 创建任务树
        task_tree = self.create_task_tree(user1.id, depth=3, breadth=2)

        # 创建Top3记录
        top3_today = self.create_top3(
            user1.id,
            [task.id for task in user1_tasks[:3]]
        )

        return {
            "users": [user1, user2, guest],
            "tasks": user1_tasks + user2_tasks + task_tree,
            "top3_records": [top3_today],
            "user1": user1,
            "user2": user2,
            "guest": guest,
            "user1_tasks": user1_tasks,
            "user2_tasks": user2_tasks,
            "task_tree": task_tree,
            "top3_today": top3_today
        }


# 便捷函数
def create_user(**overrides) -> Auth:
    """便捷函数：创建用户"""
    factory = TestDataFactory()
    return factory.create_user(**overrides)


def create_task(user_id: Optional[Union[str, UUID]] = None, **overrides) -> Task:
    """便捷函数：创建任务"""
    factory = TestDataFactory()
    return factory.create_task(user_id=user_id, **overrides)


def create_top3(user_id: Union[str, UUID], **overrides) -> TaskTop3:
    """便捷函数：创建Top3记录"""
    factory = TestDataFactory()
    return factory.create_top3(user_id=user_id, **overrides)


def create_test_dataset() -> Dict[str, Any]:
    """便捷函数：创建完整测试数据集"""
    factory = TestDataFactory()
    return factory.create_complete_test_data()