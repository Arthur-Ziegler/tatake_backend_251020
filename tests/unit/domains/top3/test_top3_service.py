"""
Top3领域Service测试

测试Top3Service的业务逻辑，包括：
1. Top3任务设置 - 消耗积分、验证任务所有权
2. Top3查询 - 根据用户和日期查询
3. 业务规则验证 - 日期唯一性、积分检查等
4. 错误处理 - 重复设置、积分不足、任务不存在等

遵循模块化设计原则，专注于服务层业务逻辑测试。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from src.domains.top3.service import Top3Service
from src.domains.top3.models import TaskTop3
from src.domains.top3.exceptions import Top3AlreadyExistsException, Top3NotFoundException
from src.domains.task.exceptions import TaskNotFoundException
from src.domains.reward.exceptions import InsufficientPointsException
from src.domains.top3.schemas import SetTop3Request, Top3Response, GetTop3Response


@pytest.mark.unit
class TestTop3Service:
    """Top3Service测试类"""

    def test_set_top3_success(self, top3_service, sample_tasks_for_top3):
        """测试成功设置Top3任务"""
        user_id, task_ids = sample_tasks_for_top3
        today = date.today()

        request = SetTop3Request(
            date=today.isoformat(),
            task_ids=task_ids
        )

        response = top3_service.set_top3(user_id, request)

        # 验证响应
        assert response.date == today.isoformat()
        assert response.task_ids == task_ids
        assert response.points_consumed == 300
        assert response.remaining_balance == 700  # 1000 - 300

        # 验证数据库中创建了记录
        top3_record = top3_service.get_user_top3(user_id, today)
        assert top3_record is not None
        assert top3_record.user_id == str(user_id)
        assert top3_record.top_date == today
        # 验证task_ids格式正确（字典格式）
        expected_task_ids = [
            {"task_id": task_id, "position": i + 1}
            for i, task_id in enumerate(task_ids)
        ]
        assert top3_record.task_ids == expected_task_ids

    def test_set_top3_insufficient_points(self, top3_service, sample_user_with_points):
        """测试积分不足时设置Top3失败"""
        user_id = sample_user_with_points

        # 手动设置用户积分为不足的数值
        top3_service.points_service.add_points(
            user_id=user_id,
            amount=-900,  # 只剩100积分
            source_type="test_adjust"
        )

        # 创建测试任务
        task_data = {
            "user_id": str(user_id),
            "title": "测试任务",
            "description": "测试任务",
            "status": "pending",
            "priority": "medium"
        }
        task = top3_service.task_repo.create(task_data)

        request = SetTop3Request(
            date=date.today().isoformat(),
            task_ids=[str(task.id)]
        )

        with pytest.raises(InsufficientPointsException):
            top3_service.set_top3(user_id, request)

    def test_set_top3_duplicate_date(self, top3_service, created_top3_entry):
        """测试重复日期设置Top3失败"""
        user_id, top3_response, today = created_top3_entry

        # 尝试再次设置同一天的Top3
        new_task_data = {
            "user_id": str(user_id),
            "title": "新任务",
            "description": "新任务描述",
            "status": "pending",
            "priority": "medium"
        }
        new_task = top3_service.task_repo.create(new_task_data)

        request = SetTop3Request(
            date=today.isoformat(),
            task_ids=[str(new_task.id)]
        )

        with pytest.raises(Top3AlreadyExistsException):
            top3_service.set_top3(user_id, request)

    def test_set_top3_task_not_found(self, top3_service, sample_user_with_points):
        """测试任务不存在时设置Top3失败"""
        user_id = sample_user_with_points
        fake_task_id = str(uuid4())

        request = SetTop3Request(
            date=date.today().isoformat(),
            task_ids=[fake_task_id]
        )

        with pytest.raises(TaskNotFoundException):
            top3_service.set_top3(user_id, request)

    def test_set_top3_task_not_owned(self, top3_service, sample_user_with_points):
        """测试任务不属于用户时设置Top3失败"""
        user_id = sample_user_with_points

        # 创建另一个用户的任务
        other_user_id = uuid4()
        other_task_data = {
            "user_id": str(other_user_id),
            "title": "其他用户的任务",
            "description": "其他用户的任务",
            "status": "pending",
            "priority": "medium"
        }
        other_task = top3_service.task_repo.create(other_task_data)

        request = SetTop3Request(
            date=date.today().isoformat(),
            task_ids=[str(other_task.id)]
        )

        with pytest.raises(TaskNotFoundException):
            top3_service.set_top3(user_id, request)

    def test_set_top3_different_dates(self, top3_service, sample_user_with_points):
        """测试不同日期设置Top3"""
        user_id = sample_user_with_points
        today = date.today()

        # 为不同日期创建任务
        task_by_date = {}
        for i in range(3):
            test_date = today - timedelta(days=i)
            task_data = {
                "user_id": str(user_id),
                "title": f"{test_date}的任务",
                "description": f"{test_date}的任务描述",
                "status": "pending",
                "priority": "medium"
            }
            task = top3_service.task_repo.create(task_data)
            task_by_date[test_date] = str(task.id)

        # 为不同日期设置Top3
        created_top3s = []
        for test_date, task_id in task_by_date.items():
            # 额外添加积分确保足够
            if len(created_top3s) > 0:
                top3_service.points_service.add_points(
                    user_id=user_id,
                    amount=300,
                    source_type="test_extra"
                )

            request = SetTop3Request(
                date=test_date.isoformat(),
                task_ids=[task_id]
            )

            response = top3_service.set_top3(user_id, request)
            created_top3s.append(response)

        # 验证所有日期都成功创建
        assert len(created_top3s) == 3

        for top3 in created_top3s:
            retrieved = top3_service.get_user_top3(user_id, date.fromisoformat(top3.date))
            assert retrieved is not None
            assert retrieved.user_id == str(user_id)

    def test_get_top3_exists(self, top3_service, created_top3_entry):
        """测试获取存在的Top3"""
        user_id, top3_response, today = created_top3_entry

        response = top3_service.get_top3(user_id, today.isoformat())

        assert isinstance(response, GetTop3Response)
        assert response.date == today.isoformat()
        assert response.task_ids == top3_response.task_ids
        assert response.points_consumed == top3_response.points_consumed
        assert response.created_at is not None

    def test_get_top3_not_exists(self, top3_service, sample_user_with_points):
        """测试获取不存在的Top3"""
        user_id = sample_user_with_points
        today = date.today()

        response = top3_service.get_top3(user_id, today.isoformat())

        assert isinstance(response, GetTop3Response)
        assert response.date == today.isoformat()
        assert response.task_ids == []
        assert response.points_consumed == 0
        assert response.created_at is None

    def test_get_user_top3_exists(self, top3_service, created_top3_entry):
        """测试获取用户存在的Top3记录"""
        user_id, top3_response, today = created_top3_entry

        top3_record = top3_service.get_user_top3(user_id, today)

        assert top3_record is not None
        assert isinstance(top3_record, TaskTop3)
        assert top3_record.user_id == str(user_id)
        assert top3_record.top_date == today
        assert top3_record.task_ids == top3_response.task_ids

    def test_get_user_top3_not_exists(self, top3_service, sample_user_with_points):
        """测试获取用户不存在的Top3记录"""
        user_id = sample_user_with_points
        today = date.today()

        top3_record = top3_service.get_user_top3(user_id, today)

        assert top3_record is None

    def test_set_top3_with_multiple_tasks(self, top3_service, sample_user_with_points):
        """测试设置多个任务的Top3"""
        user_id = sample_user_with_points
        today = date.today()

        # 创建3个任务
        task_ids = []
        for i in range(3):
            task_data = {
                "user_id": str(user_id),
                "title": f"任务{i+1}",
                "description": f"任务{i+1}的描述",
                "status": "pending",
                "priority": "medium"
            }
            task = top3_service.task_repo.create(task_data)
            task_ids.append(str(task.id))

        request = SetTop3Request(
            date=today.isoformat(),
            task_ids=task_ids
        )

        response = top3_service.set_top3(user_id, request)

        assert len(response.task_ids) == 3
        assert response.task_ids == task_ids
        assert response.points_consumed == 300

        # 验证数据库记录
        top3_record = top3_service.get_user_top3(user_id, today)
        assert len(top3_record.task_ids) == 3
        assert top3_record.task_ids == [
            {"task_id": task_id, "position": i + 1}
            for i, task_id in enumerate(task_ids)
        ]

    def test_set_top3_points_deduction(self, top3_service, sample_user_with_points):
        """测试设置Top3时积分正确扣除"""
        user_id = sample_user_with_points

        # 检查初始积分
        initial_balance = top3_service.points_service.get_balance(user_id)
        assert initial_balance == 1000

        # 创建任务并设置Top3
        task_data = {
            "user_id": str(user_id),
            "title": "测试任务",
            "description": "测试任务",
            "status": "pending",
            "priority": "medium"
        }
        task = top3_service.task_repo.create(task_data)

        request = SetTop3Request(
            date=date.today().isoformat(),
            task_ids=[str(task.id)]
        )

        response = top3_service.set_top3(user_id, request)

        # 验证积分扣除
        final_balance = top3_service.points_service.get_balance(user_id)
        assert final_balance == initial_balance - 300
        assert response.remaining_balance == final_balance

        # 验证积分交易记录
        transactions = top3_service.points_service.get_transactions(user_id)
        assert any(t.source_type == "top3_cost" and t.amount == -300 for t in transactions)

    def test_set_top3_custom_points_consumed(self, top3_service, sample_user_with_points):
        """测试自定义积分消耗的Top3设置"""
        user_id = sample_user_with_points

        # 创建任务
        task_data = {
            "user_id": str(user_id),
            "title": "测试任务",
            "description": "测试任务",
            "status": "pending",
            "priority": "medium"
        }
        task = top3_service.task_repo.create(task_data)

        # 这里暂时无法直接修改points_consumed，因为服务层写死为300
        # 但可以验证默认值
        request = SetTop3Request(
            date=date.today().isoformat(),
            task_ids=[str(task.id)]
        )

        response = top3_service.set_top3(user_id, request)

        assert response.points_consumed == 300  # 验证默认值

    def test_set_top3_invalid_date_format(self, top3_service, sample_user_with_points):
        """测试无效日期格式"""
        user_id = sample_user_with_points

        task_data = {
            "user_id": str(user_id),
            "title": "测试任务",
            "description": "测试任务",
            "status": "pending",
            "priority": "medium"
        }
        task = top3_service.task_repo.create(task_data)

        request = SetTop3Request(
            date="invalid-date",
            task_ids=[str(task.id)]
        )

        with pytest.raises(ValueError):  # date.fromisoformat会抛出异常
            top3_service.set_top3(user_id, request)

    def test_top3_service_initialization(self, top3_service):
        """测试Top3Service初始化"""
        assert top3_service.session is not None
        assert top3_service.top3_repo is not None
        assert top3_service.reward_service is not None
        assert top3_service.points_service is not None
        assert top3_service.task_repo is not None

    def test_set_top3_complete_workflow(self, top3_service, sample_user_with_points):
        """测试完整的Top3设置工作流"""
        user_id = sample_user_with_points
        today = date.today()

        # 1. 创建任务
        tasks = []
        for i in range(3):
            task_data = {
                "user_id": str(user_id),
                "title": f"重要任务{i+1}",
                "description": f"任务{i+1}的详细描述",
                "status": "pending",
                "priority": "medium"
            }
            task = top3_service.task_repo.create(task_data)
            tasks.append(task)

        # 2. 设置Top3
        task_ids = [str(task.id) for task in tasks]
        request = SetTop3Request(
            date=today.isoformat(),
            task_ids=task_ids
        )

        response = top3_service.set_top3(user_id, request)

        # 3. 验证设置成功
        assert response.date == today.isoformat()
        assert len(response.task_ids) == 3
        assert response.points_consumed == 300

        # 4. 验证可以查询到
        top3_record = top3_service.get_user_top3(user_id, today)
        assert top3_record is not None
        assert top3_record.user_id == str(user_id)
        assert len(top3_record.task_ids) == 3

        # 5. 验证积分正确扣除
        final_balance = top3_service.points_service.get_balance(user_id)
        assert final_balance == 700  # 1000 - 300

        # 6. 验证API响应
        api_response = top3_service.get_top3(user_id, today.isoformat())
        assert api_response.task_ids == task_ids
        assert api_response.points_consumed == 300
        assert api_response.created_at is not None