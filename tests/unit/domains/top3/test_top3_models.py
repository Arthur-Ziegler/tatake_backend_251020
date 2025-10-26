"""
Top3领域模型测试

测试TaskTop3模型的功能，包括：
1. 基本模型创建和验证
2. 字段类型和约束验证
3. 关系和索引验证
4. 序列化和反序列化
5. 时间戳和日期处理

遵循模块化设计原则，专注于模型层的测试。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import date, datetime, timezone
from uuid import uuid4
from typing import List, Dict, Any

from src.domains.top3.models import TaskTop3


@pytest.mark.unit
class TestTaskTop3Model:
    """TaskTop3模型测试类"""

    def test_task_top3_creation_minimal(self):
        """测试TaskTop3最小化创建"""
        user_id = str(uuid4())
        today = date.today()
        task_ids = [
            {"task_id": str(uuid4()), "position": 1},
            {"task_id": str(uuid4()), "position": 2},
            {"task_id": str(uuid4()), "position": 3}
        ]

        task_top3 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=task_ids
        )

        assert task_top3.id is not None
        assert task_top3.user_id == user_id
        assert task_top3.top_date == today
        assert task_top3.task_ids == task_ids
        assert task_top3.points_consumed == 300  # 默认值
        assert task_top3.created_at is not None
        assert task_top3.updated_at is not None

    def test_task_top3_creation_with_custom_points(self):
        """测试自定义积分消耗的TaskTop3创建"""
        user_id = str(uuid4())
        today = date.today()
        task_ids = [
            {"task_id": str(uuid4()), "position": 1}
        ]

        task_top3 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=task_ids,
            points_consumed=500
        )

        assert task_top3.points_consumed == 500

    def test_task_top3_field_types(self):
        """测试字段类型"""
        user_id = str(uuid4())
        today = date.today()
        task_ids = [{"task_id": str(uuid4()), "position": 1}]

        task_top3 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=task_ids
        )

        # 验证字段类型
        assert isinstance(task_top3.id, str)
        assert isinstance(task_top3.user_id, str)
        assert isinstance(task_top3.top_date, date)
        assert isinstance(task_top3.task_ids, list)
        assert isinstance(task_top3.points_consumed, int)
        assert isinstance(task_top3.created_at, datetime)
        assert isinstance(task_top3.updated_at, datetime)

    def test_task_top3_task_ids_structure(self):
        """测试task_ids字段结构"""
        user_id = str(uuid4())
        today = date.today()

        # 测试不同结构的task_ids
        valid_task_ids = [
            {"task_id": str(uuid4()), "position": 1, "priority": "high"},
            {"task_id": str(uuid4()), "position": 2, "priority": "medium"},
            {"task_id": str(uuid4()), "position": 3, "priority": "low"}
        ]

        task_top3 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=valid_task_ids
        )

        assert len(task_top3.task_ids) == 3
        assert all("task_id" in item and "position" in item for item in task_top3.task_ids)

    def test_task_top3_unique_constraint_validation(self):
        """测试唯一约束验证"""
        user_id = str(uuid4())
        today = date.today()
        task_id = str(uuid4())

        # 创建两个相同的TaskTop3实例（模拟数据库约束）
        task_top3_1 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=[{"task_id": task_id, "position": 1}]
        )

        task_top3_2 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=[{"task_id": task_id, "position": 1}]
        )

        # 验证它们在内存中是不同的对象
        assert task_top3_1 is not task_top3_2
        assert task_top3_1.id != task_top3_2.id
        # 但具有相同的业务键
        assert task_top3_1.user_id == task_top3_2.user_id
        assert task_top3_1.top_date == task_top3_2.top_date

    def test_task_top3_timestamps(self):
        """测试时间戳生成"""
        before_creation = datetime.now(timezone.utc)

        task_top3 = TaskTop3(
            user_id=str(uuid4()),
            top_date=date.today(),
            task_ids=[{"task_id": str(uuid4()), "position": 1}]
        )

        after_creation = datetime.now(timezone.utc)

        assert before_creation <= task_top3.created_at <= after_creation
        assert before_creation <= task_top3.updated_at <= after_creation
        # 时间戳应该非常接近（允许微小差异）
        time_diff = abs((task_top3.updated_at - task_top3.created_at).total_seconds())
        assert time_diff < 1.0  # 小于1秒差异

    def test_task_top3_string_representation(self):
        """测试字符串表示"""
        user_id = str(uuid4())
        today = date.today()

        task_top3 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=[{"task_id": str(uuid4()), "position": 1}]
        )

        repr_str = repr(task_top3)
        assert "TaskTop3" in repr_str
        assert task_top3.id in repr_str
        assert user_id in repr_str
        # 检查日期的表示形式（可能是datetime.date对象格式）
        assert str(today) in repr_str or f"datetime.date({today.year}, {today.month}, {today.day})" in repr_str

    def test_task_top3_serialization(self):
        """测试序列化功能"""
        user_id = str(uuid4())
        today = date.today()
        task_ids = [
            {"task_id": str(uuid4()), "position": 1},
            {"task_id": str(uuid4()), "position": 2}
        ]

        task_top3 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=task_ids,
            points_consumed=400
        )

        # 测试字典化
        task_dict = task_top3.model_dump()
        assert "id" in task_dict
        assert "user_id" in task_dict
        assert "top_date" in task_dict
        assert "task_ids" in task_dict
        assert "points_consumed" in task_dict
        assert "created_at" in task_dict
        assert "updated_at" in task_dict

        assert task_dict["user_id"] == user_id
        assert task_dict["top_date"] == today
        assert task_dict["task_ids"] == task_ids
        assert task_dict["points_consumed"] == 400

        # 测试JSON序列化
        json_str = task_top3.model_dump_json()
        assert user_id in json_str
        assert str(today) in json_str

    def test_task_top3_date_validation(self):
        """测试日期验证"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        # 测试不同日期类型
        dates_to_test = [
            date.today(),
            date(2024, 1, 1),
            date(2025, 12, 31)
        ]

        for test_date in dates_to_test:
            task_top3 = TaskTop3(
                user_id=user_id,
                top_date=test_date,
                task_ids=[{"task_id": task_id, "position": 1}]
            )
            assert task_top3.top_date == test_date

    def test_task_top3_task_ids_mutability(self):
        """测试task_ids的可变性"""
        user_id = str(uuid4())
        today = date.today()
        original_task_ids = [
            {"task_id": str(uuid4()), "position": 1}
        ]

        task_top3 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=original_task_ids
        )

        # 验证原始值
        assert len(task_top3.task_ids) == 1
        assert task_top3.task_ids[0]["position"] == 1

        # 修改task_ids
        new_task_ids = [
            {"task_id": str(uuid4()), "position": 1},
            {"task_id": str(uuid4()), "position": 2}
        ]
        task_top3.task_ids = new_task_ids

        # 验证修改生效
        assert len(task_top3.task_ids) == 2
        assert task_top3.task_ids == new_task_ids

    def test_task_top3_edge_cases(self):
        """测试边界情况"""
        user_id = str(uuid4())

        # 测试负数积分
        task_top3_negative_points = TaskTop3(
            user_id=user_id,
            top_date=date.today(),
            task_ids=[{"task_id": str(uuid4()), "position": 1}],
            points_consumed=-100
        )
        assert task_top3_negative_points.points_consumed == -100

        # 测试大量task_ids
        many_task_ids = [
            {"task_id": str(uuid4()), "position": i}
            for i in range(1, 11)  # 10个任务
        ]
        task_top3_many = TaskTop3(
            user_id=user_id,
            top_date=date.today(),
            task_ids=many_task_ids
        )
        assert len(task_top3_many.task_ids) == 10

        # 测试最小值（1个任务）
        task_top3_minimal = TaskTop3(
            user_id=user_id,
            top_date=date.today(),
            task_ids=[{"task_id": str(uuid4()), "position": 1}],
            points_consumed=0
        )
        assert len(task_top3_minimal.task_ids) == 1
        assert task_top3_minimal.points_consumed == 0

    def test_task_top3_comparison(self):
        """测试TaskTop3对象比较"""
        user_id = str(uuid4())
        today = date.today()
        task_ids = [{"task_id": str(uuid4()), "position": 1}]

        task_top3_1 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=task_ids
        )

        task_top3_2 = TaskTop3(
            user_id=user_id,
            top_date=today,
            task_ids=task_ids
        )

        # 不同的对象应该不相等
        assert task_top3_1 != task_top3_2
        assert task_top3_1 is not task_top3_2

        # 但是业务键应该相同
        assert task_top3_1.user_id == task_top3_2.user_id
        assert task_top3_1.top_date == task_top3_2.top_date