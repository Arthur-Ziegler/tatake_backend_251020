"""
零Bug测试体系 - 任务测试数据工厂

提供任务相关的测试数据生成，包括基础任务、子任务、任务完成记录等。

设计原则：
1. 支持任务层级结构（父任务、子任务）
2. 覆盖所有任务状态和优先级
3. 确保任务时间逻辑正确
4. 支持不同类型的任务场景
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseFactory, register_factory


@register_factory("task")
class TaskFactory(BaseFactory):
    """任务测试数据工厂

    生成符合业务需求的任务测试数据，支持层级结构、状态流转等。
    """

    # 任务默认数据
    DEFAULTS = {
        "id": "",                    # 任务ID
        "title": "",                 # 任务标题
        "description": "",           # 任务描述
        "status": "pending",         # 任务状态
        "priority": "medium",        # 优先级
        "user_id": "",               # 用户ID
        "parent_id": None,           # 父任务ID
        "completion_percentage": 0,  # 完成百分比
        "estimated_hours": 2.0,      # 预估工时
        "actual_hours": 0.0,         # 实际工时
        "tags": [],                  # 标签
        "due_date": None,            # 截止日期
        "created_at": None,          # 创建时间
        "updated_at": None,          # 更新时间
        "completed_at": None,        # 完成时间
        "is_deleted": False,         # 是否删除
        "difficulty": "medium",      # 难度
        "category": "general",       # 分类
        "metadata": {},              # 元数据
    }

    # 必填字段
    REQUIRED_FIELDS = ["title", "user_id", "status"]

    # 任务状态
    STATUSES = [
        "pending", "in_progress", "completed", "cancelled", "on_hold", "review"
    ]

    # 优先级
    PRIORITIES = ["low", "medium", "high", "urgent"]

    # 难度
    DIFFICULTIES = ["easy", "medium", "hard", "expert"]

    # 分类
    CATEGORIES = [
        "work", "study", "personal", "health", "finance",
        "relationship", "hobby", "general"
    ]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建任务数据

        Args:
            **overrides: 覆盖字段

        Returns:
            任务数据字典
        """
        # 生成基础数据
        task_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # 生成唯一标题
        title = f"测试任务_{task_id[:8]}"
        description = f"这是测试任务{task_id[:8]}的详细描述"

        # 生成截止日期（7天后）
        due_date = timestamp + timedelta(days=cls._generate_int(1, 30))

        # 构建默认数据
        defaults = cls._merge_data(cls.DEFAULTS, {
            "id": task_id,
            "title": cls._ensure_unique("title", title),
            "description": description,
            "status": cls._generate_choice(cls.STATUSES),
            "priority": cls._generate_choice(cls.PRIORITIES),
            "difficulty": cls._generate_choice(cls.DIFFICULTIES),
            "category": cls._generate_choice(cls.CATEGORIES),
            "tags": cls._generate_tags(),
            "completion_percentage": cls._calculate_completion_percentage(
                overrides.get("status", "pending")
            ),
            "estimated_hours": cls._generate_float(0.5, 40.0, 1),
            "actual_hours": cls._generate_float(0.0, 50.0, 1),
            "due_date": due_date,
            "created_at": timestamp,
            "updated_at": timestamp,
            "metadata": {
                "source": "test_factory",
                "version": "1.0",
                "test_id": task_id[:8]
            }
        })

        # 如果用户ID未提供，生成一个
        if "user_id" not in defaults:
            defaults["user_id"] = f"user_{uuid.uuid4().hex[:8]}"

        # 应用覆盖数据
        task_data = cls._merge_data(defaults, overrides)

        # 重新计算完成百分比
        if "status" in overrides:
            task_data["completion_percentage"] = cls._calculate_completion_percentage(
                task_data["status"]
            )

        # 设置完成时间
        if task_data["status"] == "completed" and not task_data.get("completed_at"):
            task_data["completed_at"] = timestamp
            task_data["actual_hours"] = max(task_data["actual_hours"], 0.1)

        # 数据验证
        cls.validate_data(task_data)

        return task_data

    @classmethod
    def _generate_tags(cls) -> List[str]:
        """生成任务标签

        Returns:
            标签列表
        """
        all_tags = [
            "工作", "学习", "生活", "健康", "财务", "人际关系",
            "爱好", "紧急", "重要", "长期", "短期", "项目",
            "日常", "会议", "文档", "开发", "测试", "部署"
        ]
        num_tags = cls._generate_int(1, 4)
        return [cls._generate_choice(all_tags) for _ in range(num_tags)]

    @classmethod
    def _calculate_completion_percentage(cls, status: str) -> int:
        """根据状态计算完成百分比

        Args:
            status: 任务状态

        Returns:
            完成百分比
        """
        status_mapping = {
            "pending": 0,
            "in_progress": cls._generate_int(10, 80),
            "review": cls._generate_int(80, 95),
            "completed": 100,
            "cancelled": 0,
            "on_hold": cls._generate_int(0, 50)
        }
        return status_mapping.get(status, 0)

    @classmethod
    def create_pending(cls, **overrides: Any) -> Dict[str, Any]:
        """创建待办任务

        Args:
            **overrides: 覆盖字段

        Returns:
            待办任务数据
        """
        return cls.create(
            status="pending",
            completion_percentage=0,
            **overrides
        )

    @classmethod
    def create_in_progress(cls, **overrides: Any) -> Dict[str, Any]:
        """创建进行中任务

        Args:
            **overrides: 覆盖字段

        Returns:
            进行中任务数据
        """
        return cls.create(
            status="in_progress",
            completion_percentage=cls._generate_int(10, 80),
            **overrides
        )

    @classmethod
    def create_completed(cls, **overrides: Any) -> Dict[str, Any]:
        """创建已完成任务

        Args:
            **overrides: 覆盖字段

        Returns:
            已完成任务数据
        """
        return cls.create(
            status="completed",
            completion_percentage=100,
            **overrides
        )

    @classmethod
    def create_subtask(cls, parent_id: str, **overrides: Any) -> Dict[str, Any]:
        """创建子任务

        Args:
            parent_id: 父任务ID
            **overrides: 覆盖字段

        Returns:
            子任务数据
        """
        return cls.create(
            parent_id=parent_id,
            title=f"子任务_{uuid.uuid4().hex[:8]}",
            estimated_hours=cls._generate_float(0.5, 8.0, 1),
            **overrides
        )

    @classmethod
    def create_task_hierarchy(cls, user_id: str, depth: int = 3, breadth: int = 2) -> Dict[str, Any]:
        """创建任务层级结构

        Args:
            user_id: 用户ID
            depth: 层级深度
            breadth: 每层广度

        Returns:
            任务层级数据
        """
        # 创建根任务
        root_task = cls.create(
            user_id=user_id,
            title=f"根任务_{uuid.uuid4().hex[:8]}",
            status="in_progress",
            priority="high"
        )

        all_tasks = [root_task]

        # 创建子任务层级
        def create_subtasks(parent_task: Dict[str, Any], current_depth: int):
            if current_depth <= 0:
                return

            for i in range(breadth):
                subtask = cls.create_subtask(
                    parent_id=parent_task["id"],
                    user_id=user_id,
                    title=f"子任务_L{current_depth}_{i}_{uuid.uuid4().hex[:6]}"
                )
                all_tasks.append(subtask)

                # 递归创建更深层级
                if current_depth > 1:
                    create_subtasks(subtask, current_depth - 1)

        create_subtasks(root_task, depth)

        return {
            "root_task": root_task,
            "all_tasks": all_tasks,
            "total_count": len(all_tasks)
        }

    @classmethod
    def create_batch_with_statuses(cls, count: int, user_id: str = None) -> List[Dict[str, Any]]:
        """创建不同状态的任务批次

        Args:
            count: 创建数量
            user_id: 用户ID

        Returns:
            任务列表
        """
        tasks = []
        for i in range(count):
            # 循环分配不同状态
            status_index = i % len(cls.STATUSES)
            status = cls.STATUSES[status_index]

            overrides = {"status": status}
            if user_id:
                overrides["user_id"] = user_id

            task = cls.create(**overrides)
            tasks.append(task)

        return tasks

    @classmethod
    def create_overdue_task(cls, days_overdue: int = 5, **overrides: Any) -> Dict[str, Any]:
        """创建过期任务

        Args:
            days_overdue: 过期天数
            **overrides: 覆盖字段

        Returns:
            过期任务数据
        """
        past_date = datetime.now(timezone.utc) - timedelta(days=days_overdue)
        return cls.create(
            due_date=past_date,
            status="pending",
            priority="urgent",
            **overrides
        )

    @classmethod
    def create_urgent_task(cls, **overrides: Any) -> Dict[str, Any]:
        """创建紧急任务

        Args:
            **overrides: 覆盖字段

        Returns:
            紧急任务数据
        """
        return cls.create(
            priority="urgent",
            difficulty="hard",
            estimated_hours=cls._generate_float(2.0, 16.0, 1),
            **overrides
        )


@register_factory("task_completion")
class TaskCompletionFactory(BaseFactory):
    """任务完成记录工厂

    生成任务完成时的详细记录，包括时间、工时、质量评分等。
    """

    DEFAULTS = {
        "task_id": "",              # 任务ID
        "user_id": "",              # 用户ID
        "completed_at": None,       # 完成时间
        "actual_hours": 0.0,        # 实际工时
        "quality_score": 5,         # 质量评分 (1-10)
        "difficulty_rating": 5,     # 难度评分 (1-10)
        "satisfaction_rating": 5,   # 满意度评分 (1-10)
        "notes": "",                # 完成备注
        "earned_points": 0,         # 获得积分
        "completion_type": "normal", # 完成类型
    }

    REQUIRED_FIELDS = ["task_id", "user_id"]

    COMPLETION_TYPES = ["normal", "early", "late", "perfect", "minimal"]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建任务完成记录

        Args:
            **overrides: 覆盖字段

        Returns:
            完成记录数据
        """
        timestamp = datetime.now(timezone.utc)

        defaults = cls._merge_data(cls.DEFAULTS, {
            "task_id": overrides.get("task_id", str(uuid.uuid4())),
            "user_id": overrides.get("user_id", f"user_{uuid.uuid4().hex[:8]}"),
            "completed_at": timestamp,
            "actual_hours": cls._generate_float(0.1, 20.0, 1),
            "quality_score": cls._generate_int(1, 10),
            "difficulty_rating": cls._generate_int(1, 10),
            "satisfaction_rating": cls._generate_int(1, 10),
            "notes": f"任务完成备注_{uuid.uuid4().hex[:8]}",
            "earned_points": cls._calculate_earned_points(
                overrides.get("quality_score", 5),
                overrides.get("difficulty_rating", 5)
            ),
            "completion_type": cls._generate_choice(cls.COMPLETION_TYPES)
        })

        completion_data = cls._merge_data(defaults, overrides)
        cls.validate_data(completion_data)

        return completion_data

    @classmethod
    def _calculate_earned_points(cls, quality_score: int, difficulty_score: int) -> int:
        """计算获得积分

        Args:
            quality_score: 质量评分
            difficulty_score: 难度评分

        Returns:
            获得积分
        """
        base_points = 10
        quality_multiplier = quality_score / 10.0
        difficulty_multiplier = difficulty_score / 10.0

        return int(base_points * quality_multiplier * difficulty_multiplier)


class TaskFactoryManager:
    """任务工厂管理器

    提供高级的任务数据创建和管理功能。
    """

    @staticmethod
    def create_user_workflow(user_id: str, num_tasks: int = 10) -> Dict[str, Any]:
        """创建用户工作流数据

        Args:
            user_id: 用户ID
            num_tasks: 任务数量

        Returns:
            用户工作流数据
        """
        # 创建不同状态的任务
        pending_count = int(num_tasks * 0.3)
        in_progress_count = int(num_tasks * 0.2)
        completed_count = num_tasks - pending_count - in_progress_count

        tasks = []

        # 待办任务
        for _ in range(pending_count):
            tasks.append(TaskFactory.create_pending(user_id=user_id))

        # 进行中任务
        for _ in range(in_progress_count):
            tasks.append(TaskFactory.create_in_progress(user_id=user_id))

        # 已完成任务
        for _ in range(completed_count):
            task = TaskFactory.create_completed(user_id=user_id)
            tasks.append(task)

        return {
            "user_id": user_id,
            "tasks": tasks,
            "statistics": {
                "total": len(tasks),
                "pending": pending_count,
                "in_progress": in_progress_count,
                "completed": completed_count
            }
        }

    @staticmethod
    def create_project_tasks(project_name: str, num_tasks: int = 20) -> Dict[str, Any]:
        """创建项目任务集

        Args:
            project_name: 项目名称
            num_tasks: 任务数量

        Returns:
            项目任务数据
        """
        project_id = str(uuid.uuid4())
        tasks = []

        # 创建根任务
        root_task = TaskFactory.create(
            title=f"项目：{project_name}",
            description=f"{project_name}项目的根任务",
            priority="high",
            category="work"
        )
        tasks.append(root_task)

        # 创建子任务
        for i in range(num_tasks - 1):
            task = TaskFactory.create_subtask(
                parent_id=root_task["id"],
                title=f"{project_name} - 子任务{i+1}",
                category="work",
                user_id=root_task["user_id"]
            )
            tasks.append(task)

        return {
            "project_id": project_id,
            "project_name": project_name,
            "root_task": root_task,
            "all_tasks": tasks,
            "task_count": len(tasks)
        }