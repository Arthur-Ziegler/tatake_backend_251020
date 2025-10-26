"""
Top3域模型严格单元测试

对TaskTop3模型进行全面测试，包括字段验证、方法调用、边界条件等。

作者：TaKeKe团队
版本：2.0.0 - 严格单元测试
"""

import pytest
from datetime import datetime, timezone, date
from typing import Dict, Any, List
from uuid import uuid4

from src.domains.top3.models import TaskTop3
from tests.unit.domains.top3.conftest_strict import Top3TestDataFactory


@pytest.mark.unit
@pytest.mark.model
@pytest.mark.top3
class TestTaskTop3Model:
    """TaskTop3模型测试类"""

    def test_top3_creation_with_minimal_data(self, sample_user_id: str):
        """测试使用最小数据创建TaskTop3"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids
        )

        assert top3.id is not None
        assert top3.user_id == sample_user_id
        assert top3.top_date == date.today()
        assert len(top3.task_ids) == 1
        assert isinstance(top3.created_at, datetime)
        assert isinstance(top3.updated_at, datetime)

    def test_top3_creation_with_full_data(self, base_top3_data: Dict[str, Any]):
        """测试使用完整数据创建TaskTop3"""
        full_data = {
            **base_top3_data,
            "id": str(uuid4())
        }

        top3 = TaskTop3(**full_data)

        assert top3.id == full_data["id"]
        assert top3.user_id == full_data["user_id"]
        assert top3.top_date == date.fromisoformat(full_data["top_date"])
        assert top3.task_ids == full_data["task_ids"]
        assert top3.points_consumed == full_data["points_consumed"]
        assert top3.remaining_balance == full_data["remaining_balance"]

    def test_top3_field_validation(self, sample_user_id: str):
        """测试TaskTop3字段验证"""
        # 测试必填字段
        with pytest.raises(Exception):  # SQLModel验证异常
            TaskTop3()  # 缺少user_id

        with pytest.raises(Exception):
            TaskTop3(user_id=sample_user_id)  # 缺少top_date

        with pytest.raises(Exception):
            TaskTop3(
                user_id=sample_user_id,
                top_date=date.today()
            )  # 缺少task_ids

        # 测试task_ids格式
        with pytest.raises(Exception):
            TaskTop3(
                user_id=sample_user_id,
                top_date=date.today(),
                task_ids=[]  # 空列表
            )

        # 测试无效的task_ids格式
        with pytest.raises(Exception):
            TaskTop3(
                user_id=sample_user_id,
                top_date=date.today(),
                task_ids=["invalid_format"]  # 应该是字典列表
            )

    def test_top3_default_values(self, sample_user_id: str, sample_task_ids: List[str]):
        """测试TaskTop3默认值"""
        task_ids = [
            {"task_id": task_id, "added_at": datetime.now(timezone.utc).isoformat()}
            for task_id in sample_task_ids[:3]
        ]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids
        )

        assert top3.points_consumed == 5  # 默认消耗5积分
        assert top3.remaining_balance == 0  # 默认余额为0

    def test_top3_task_ids_structure(self, sample_user_id: str, sample_task_ids: List[str]):
        """测试TaskTop3的task_ids结构"""
        task_ids = [
            {"task_id": task_id, "added_at": datetime.now(timezone.utc).isoformat()}
            for task_id in sample_task_ids[:3]
        ]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids,
            points_consumed=10
        )

        assert len(top3.task_ids) == 3
        for i, task_id_obj in enumerate(top3.task_ids):
            assert "task_id" in task_id_obj
            assert "added_at" in task_id_obj
            assert task_id_obj["task_id"] == sample_task_ids[i]

    def test_top3_date_fields(self, sample_user_id: str, current_date: date):
        """测试日期字段"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=current_date,
            task_ids=task_ids
        )

        assert top3.top_date == current_date
        assert isinstance(top3.created_at, datetime)
        assert isinstance(top3.updated_at, datetime)

    def test_top3_points_fields(self, sample_user_id: str):
        """测试积分字段"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids,
            points_consumed=15,
            remaining_balance=85
        )

        assert top3.points_consumed == 15
        assert top3.remaining_balance == 85

    def test_top3_to_dict(self, sample_top3: TaskTop3):
        """测试TaskTop3.to_dict方法"""
        result = sample_top3.dict()

        assert isinstance(result, dict)
        assert result["id"] == sample_top3.id
        assert result["user_id"] == sample_top3.user_id
        assert result["top_date"] == sample_top3.top_date
        assert result["task_ids"] == sample_top3.task_ids
        assert result["points_consumed"] == sample_top3.points_consumed
        assert result["remaining_balance"] == sample_top3.remaining_balance

    def test_top3_repr(self, sample_top3: TaskTop3):
        """测试TaskTop3.__repr__方法"""
        repr_str = repr(sample_top3)

        assert isinstance(repr_str, str)
        assert sample_top3.id in repr_str
        assert sample_top3.user_id in repr_str
        assert str(sample_top3.top_date) in repr_str

    @pytest.mark.parametrize("task_count", [1, 2, 3])
    def test_top3_valid_task_counts(self, sample_user_id: str, sample_task_ids: List[str], task_count: int):
        """测试有效任务数量"""
        task_ids = [
            {"task_id": task_id, "added_at": datetime.now(timezone.utc).isoformat()}
            for task_id in sample_task_ids[:task_count]
        ]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids
        )

        assert len(top3.task_ids) == task_count

    @pytest.mark.parametrize("task_count", [0, 4, 5])
    def test_top3_invalid_task_counts(self, sample_user_id: str, sample_task_ids: List[str], task_count: int):
        """测试无效任务数量"""
        if task_count == 0:
            task_ids = []
        else:
            task_ids = [
                {"task_id": task_id, "added_at": datetime.now(timezone.utc).isoformat()}
                for task_id in sample_task_ids[:task_count]
            ]

        with pytest.raises(Exception):
            TaskTop3(
                user_id=sample_user_id,
                top_date=date.today(),
                task_ids=task_ids
            )

    def test_top3_task_ids_with_added_at(self, sample_user_id: str, sample_task_ids: List[str]):
        """测试task_ids中的added_at字段"""
        base_time = datetime.now(timezone.utc)
        task_ids = []

        for i, task_id in enumerate(sample_task_ids[:3]):
            added_time = base_time.replace(minute=base_time.minute + i)
            task_ids.append({
                "task_id": task_id,
                "added_at": added_time.isoformat()
            })

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids
        )

        # 验证时间戳顺序
        for i in range(len(top3.task_ids) - 1):
            current_time = datetime.fromisoformat(top3.task_ids[i]["added_at"])
            next_time = datetime.fromisoformat(top3.task_ids[i + 1]["added_at"])
            assert current_time <= next_time

    def test_top3_negative_points_consumed(self, sample_user_id: str):
        """测试负数积分消耗"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        with pytest.raises(Exception):
            TaskTop3(
                user_id=sample_user_id,
                top_date=date.today(),
                task_ids=task_ids,
                points_consumed=-5  # 负数
            )

    def test_top3_negative_remaining_balance(self, sample_user_id: str):
        """测试负数剩余余额"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        with pytest.raises(Exception):
            TaskTop3(
                user_id=sample_user_id,
                top_date=date.today(),
                task_ids=task_ids,
                remaining_balance=-10  # 负数
            )

    def test_top3_uuid_generation(self, sample_user_id: str):
        """测试UUID自动生成"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        top3_1 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids
        )

        top3_2 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=[{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]
        )

        assert top3_1.id is not None
        assert top3_2.id is not None
        assert top3_1.id != top3_2.id
        assert isinstance(top3_1.id, str)
        assert isinstance(top3_2.id, str)

    def test_top3_automatic_timestamps(self, sample_user_id: str, current_datetime: datetime):
        """测试自动时间戳"""
        task_ids = [{"task_id": str(uuid4()), "added_at": current_datetime.isoformat()}]

        before_creation = datetime.now(timezone.utc)

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids
        )

        after_creation = datetime.now(timezone.utc)

        assert top3.created_at >= before_creation
        assert top3.created_at <= after_creation
        assert top3.updated_at >= before_creation
        assert top3.updated_at <= after_creation
        assert top3.created_at == top3.updated_at

    def test_top3_edge_cases(self, sample_user_id: str):
        """测试TaskTop3边界情况"""
        # 测试最大任务数量
        max_task_ids = [
            {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}
            for _ in range(3)
        ]

        top3_max = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=max_task_ids
        )
        assert len(top3_max.task_ids) == 3

        # 测试特殊字符在task_id中
        special_task_id = "task_with-special_chars_123"
        top3_special = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=[{"task_id": special_task_id, "added_at": datetime.now(timezone.utc).isoformat()}]
        )
        assert top3_special.task_ids[0]["task_id"] == special_task_id

    def test_top3_field_types(self, sample_top3: TaskTop3):
        """测试TaskTop3字段类型"""
        assert isinstance(sample_top3.id, str)
        assert isinstance(sample_top3.user_id, str)
        assert isinstance(sample_top3.top_date, date)
        assert isinstance(sample_top3.task_ids, list)
        assert isinstance(sample_top3.points_consumed, int)
        assert isinstance(sample_top3.remaining_balance, int)
        assert isinstance(sample_top3.created_at, datetime)
        assert isinstance(sample_top3.updated_at, datetime)

        # 验证task_ids内部结构
        for task_id_obj in sample_top3.task_ids:
            assert isinstance(task_id_obj, dict)
            assert "task_id" in task_id_obj
            assert "added_at" in task_id_obj
            assert isinstance(task_id_obj["task_id"], str)
            assert isinstance(task_id_obj["added_at"], str)

    def test_top3_date_consistency(self, sample_user_id: str, current_date: date):
        """测试日期一致性"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=current_date,
            task_ids=task_ids
        )

        # 验证top_date是date类型
        assert isinstance(top3.top_date, date)
        assert top3.top_date == current_date

        # 验证created_at和updated_at是datetime类型且日期匹配
        assert top3.created_at.date() == current_date
        assert top3.updated_at.date() == current_date

    @pytest.mark.slow
    def test_top3_bulk_creation_performance(self, top3_test_data_factory: Top3TestDataFactory, performance_tracker):
        """测试批量创建Top3的性能"""
        performance_tracker.start()

        top3_list = []
        for i in range(1000):
            top3 = top3_test_data_factory.create_top3()
            top3_list.append(top3)

        performance_tracker.stop()

        assert len(top3_list) == 1000
        assert performance_tracker.get_duration() < 1.0  # 应该在1秒内完成
        assert all(isinstance(top3.id, str) for top3 in top3_list)


@pytest.mark.unit
@pytest.mark.model
@pytest.mark.top3
class TestTaskTop3ModelConstants:
    """TaskTop3模型常量测试类"""

    def test_top3_default_points_consumed(self, sample_user_id: str):
        """测试默认积分消耗常量"""
        task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]

        top3 = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=task_ids
        )

        # 验证默认积分消耗
        assert top3.points_consumed >= 1  # 至少消耗1积分
        assert top3.points_consumed <= 20  # 最多消耗20积分

    def test_top3_task_count_limits(self, sample_user_id: str):
        """测试任务数量限制"""
        # 测试最小任务数量
        min_task_ids = [{"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}]
        top3_min = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=min_task_ids
        )
        assert len(top3_min.task_ids) >= 1

        # 测试最大任务数量
        max_task_ids = [
            {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}
            for _ in range(3)
        ]
        top3_max = TaskTop3(
            user_id=sample_user_id,
            top_date=date.today(),
            task_ids=max_task_ids
        )
        assert len(top3_max.task_ids) <= 3


@pytest.mark.unit
@pytest.mark.model
@pytest.mark.top3
class TestTaskTop3ModelRelationships:
    """TaskTop3模型关系测试类"""

    def test_top3_user_relationship(self, sample_top3: TaskTop3, sample_user_id: str):
        """测试Top3与用户的关系"""
        assert sample_top3.user_id == sample_user_id
        assert isinstance(sample_top3.user_id, str)
        assert len(sample_top3.user_id) > 0

    def test_top3_task_relationships(self, sample_top3: TaskTop3, sample_task_ids: List[str]):
        """测试Top3与任务的关系"""
        top3_task_ids = [task_obj["task_id"] for task_obj in sample_top3.task_ids]

        # 验证任务ID格式
        for task_id in top3_task_ids:
            assert isinstance(task_id, str)
            assert len(task_id) > 0

        # 验证任务数量
        assert 1 <= len(top3_task_ids) <= 3

    def test_top3_temporal_relationships(self, sample_top3: TaskTop3, current_date: date):
        """测试Top3的时间关系"""
        # 验证日期逻辑
        assert sample_top3.top_date <= current_date
        assert sample_top3.created_at.date() <= current_date
        assert sample_top3.updated_at.date() <= current_date

        # 验证创建和更新时间关系
        assert sample_top3.created_at <= sample_top3.updated_at