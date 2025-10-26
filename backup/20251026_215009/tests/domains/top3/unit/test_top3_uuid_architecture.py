"""
Top3领域UUID架构单元测试

测试Top3Service和Top3Repository的UUID处理，确保：
1. UUIDConverter的正确使用
2. 参数验证和错误处理
3. 类型安全和一致性
4. 与其他领域Service的UUID兼容性

遵循TDD原则：先写测试→最小实现→优化重构

作者：TaKeKe团队
版本：1.0.0 - Top3领域UUID架构重构
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from fastapi import HTTPException

from src.domains.top3.service import Top3Service
from src.domains.top3.repository import Top3Repository
from src.domains.top3.schemas import SetTop3Request, Top3Response, GetTop3Response
from src.domains.top3.models import TaskTop3
from src.domains.top3.exceptions import Top3AlreadyExistsException, Top3NotFoundException
from src.domains.top3.router import validate_date_parameter
from src.domains.points.service import PointsService
from src.domains.task.repository import TaskRepository
from src.domains.task.exceptions import TaskNotFoundException
from src.core.uuid_converter import UUIDConverter
from tests.conftest import test_db_session


@pytest.mark.unit
class TestTop3UUIDArchitecture:
    """Top3领域UUID架构测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        pass

    def test_uuid_converter_string_conversion(self):
        """测试UUIDConverter字符串转换功能"""
        uuid_obj = uuid4()
        result = UUIDConverter.ensure_string(uuid_obj)

        # 验证转换结果
        assert isinstance(result, str)
        assert len(result) == 36  # UUID字符串长度
        assert result.count('-') == 4  # UUID格式验证

    def test_uuid_converter_uuid_conversion(self):
        """测试UUIDConverter UUID对象转换功能"""
        uuid_str = str(uuid4())
        result = UUIDConverter.ensure_uuid(uuid_str)

        # 验证转换结果
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_validate_date_parameter_success(self):
        """测试日期参数验证成功"""
        valid_dates = [
            "2025-01-15",
            "2024-12-31",
            "2023-02-28"
        ]

        for date_str in valid_dates:
            result = validate_date_parameter(date_str)
            assert result == date_str

    def test_validate_date_parameter_failure(self):
        """测试日期参数验证失败"""
        invalid_dates = [
            "2025-13-01",  # 无效月份
            "2025-01-32",  # 无效日期
            "2025/01/15",  # 错误格式
            "15-01-2025",  # 错误格式
            "invalid-date"
        ]

        for invalid_date in invalid_dates:
            with pytest.raises(HTTPException) as exc_info:
                validate_date_parameter(invalid_date)
            assert exc_info.value.status_code == 400
            assert "日期格式无效" in str(exc_info.value.detail)

    def test_set_top3_request_validation_success(self, test_db_session):
        """测试SetTop3Request验证成功"""
        valid_request_data = {
            "date": "2025-01-15",
            "task_ids": [
                str(uuid4()),
                str(uuid4()),
                str(uuid4())
            ]
        }

        request = SetTop3Request(**valid_request_data)

        # 验证数据
        assert request.date == "2025-01-15"
        assert len(request.task_ids) == 3
        for task_id in request.task_ids:
            assert UUIDConverter.is_valid_uuid_string(task_id)

    def test_set_top3_request_validation_invalid_uuid(self, test_db_session):
        """测试SetTop3Request UUID验证失败"""
        invalid_request_data = {
            "date": "2025-01-15",
            "task_ids": [
                str(uuid4()),
                "invalid-uuid-format",
                str(uuid4())
            ]
        }

        with pytest.raises(ValueError) as exc_info:
            SetTop3Request(**invalid_request_data)
        assert "无效的UUID格式" in str(exc_info.value)

    def test_set_top3_request_validation_invalid_task_count(self, test_db_session):
        """测试SetTop3Request任务数量验证失败"""
        # 测试空任务列表
        with pytest.raises(ValueError) as exc_info:
            SetTop3Request(date="2025-01-15", task_ids=[])
        assert "task_ids必须包含1-3个任务" in str(exc_info.value)

        # 测试过多任务
        with pytest.raises(ValueError) as exc_info:
            SetTop3Request(
                date="2025-01-15",
                task_ids=[str(uuid4()) for _ in range(4)]
            )
        assert "task_ids必须包含1-3个任务" in str(exc_info.value)

    def test_top3_service_set_top3_uuid_handling(self, test_db_session):
        """测试Top3Service.set_top3的UUID处理"""
        user_id = uuid4()
        task_ids = [str(uuid4()) for _ in range(2)]

        # Mock依赖服务
        mock_points_service = Mock(spec=PointsService)
        mock_points_service.get_balance.return_value = 500
        mock_task_repo = Mock(spec=TaskRepository)
        mock_task_repo.get_by_id.return_value = Mock(user_id=str(user_id))

        service = Top3Service(test_db_session, mock_points_service)
        service.task_repo = mock_task_repo

        request = SetTop3Request(
            date="2025-01-15",
            task_ids=task_ids
        )

        with patch.object(service.top3_repo, 'get_by_user_and_date', return_value=None), \
             patch.object(service.top3_repo, 'create') as mock_create:

            mock_create.return_value = Mock(
                top_date=date.fromisoformat("2025-01-15"),
                task_ids=[{"task_id": task_id, "position": i + 1} for i, task_id in enumerate(task_ids)],
                points_consumed=300,
                created_at=datetime.now(timezone.utc)
            )

            result = service.set_top3(user_id, request)

            # 验证UUID转换正确
            assert isinstance(result, dict)
            assert "date" in result
            assert "task_ids" in result
            assert "points_consumed" in result

    def test_top3_service_get_top3_uuid_handling(self, test_db_session):
        """测试Top3Service.get_top3的UUID处理"""
        user_id = uuid4()
        date_str = "2025-01-15"

        service = Top3Service(test_db_session)

        # Mock空结果
        with patch.object(service.top3_repo, 'get_by_user_and_date', return_value=None):
            result = service.get_top3(user_id, date_str)

            # 验证返回空响应
            assert result["date"] == date_str
            assert result["task_ids"] == []
            assert result["points_consumed"] == 0
            assert result["created_at"] is None

    def test_top3_repository_uuid_handling(self, test_db_session):
        """测试Top3Repository的UUID处理"""
        repo = Top3Repository(test_db_session)
        user_id = uuid4()
        target_date = date.fromisoformat("2025-01-15")
        task_ids = [str(uuid4()), str(uuid4())]

        # 测试create方法
        with patch.object(test_db_session, 'add'), \
             patch.object(test_db_session, 'commit'), \
             patch.object(test_db_session, 'refresh'):

            created_top3 = repo.create(user_id, target_date, task_ids)

            # 验证UUID转换
            assert created_top3.user_id == UUIDConverter.ensure_string(user_id)
            assert created_top3.top_date == target_date
            assert len(created_top3.task_ids) == 2

    def test_top3_repository_get_by_user_and_date_uuid_support(self, test_db_session):
        """测试Top3Repository支持UUID和字符串输入"""
        repo = Top3Repository(test_db_session)
        user_id_uuid = uuid4()
        user_id_str = str(user_id_uuid)
        target_date = date.fromisoformat("2025-01-15")

        # 创建模拟的TaskTop3对象
        mock_top3 = Mock(spec=TaskTop3)
        mock_top3.user_id = user_id_str
        mock_top3.top_date = target_date

        with patch.object(test_db_session, 'execute') as mock_execute:
            mock_execute.return_value.scalars.return_value.first.return_value = mock_top3

            # 测试UUID输入
            result_uuid = repo.get_by_user_and_date(user_id_uuid, target_date)
            assert result_uuid == mock_top3

            # 测试字符串输入
            result_str = repo.get_by_user_and_date(user_id_str, target_date)
            assert result_str == mock_top3

    def test_top3_service_is_task_in_today_top3_uuid_handling(self, test_db_session):
        """测试Top3Service.is_task_in_today_top3的UUID处理"""
        user_id_str = str(uuid4())
        task_id_str = str(uuid4())

        service = Top3Service(test_db_session)

        # Mock空结果
        with patch.object(service.top3_repo, 'get_by_user_and_date', return_value=None):
            result = service.is_task_in_today_top3(user_id_str, task_id_str)
            assert result is False

    def test_uuid_converter_error_handling(self):
        """测试UUIDConverter错误处理"""
        # 测试无效UUID字符串
        invalid_uuids = [
            "invalid-uuid",
            "12345",
            "not-a-uuid",
            "short-uuid",
            "",
            None
        ]

        for invalid_uuid in invalid_uuids:
            if invalid_uuid is None:
                with pytest.raises(TypeError):
                    UUIDConverter.ensure_string(invalid_uuid)
            else:
                with pytest.raises((TypeError, ValueError)):
                    UUIDConverter.ensure_uuid(invalid_uuid)

    def test_top3_service_exception_handling_with_uuid(self, test_db_session):
        """测试Top3Service异常处理中的UUID处理"""
        user_id = uuid4()

        service = Top3Service(test_db_session)

        # 测试TaskNotFoundException中的UUID处理
        request = SetTop3Request(
            date="2025-01-15",
            task_ids=[str(uuid4())]
        )

        with patch.object(service.top3_repo, 'get_by_user_and_date', return_value=None), \
             patch('src.domains.top3.service.PointsService') as mock_points_class:

            mock_points_service = Mock()
            mock_points_service.get_balance.return_value = 500
            mock_points_class.return_value = mock_points_service

            # Mock task repository to raise exception
            with patch.object(service, 'task_repo') as mock_task_repo:
                mock_task_repo.get_by_id.return_value = None

                with pytest.raises(TaskNotFoundException):
                    service.set_top3(user_id, request)

    def test_integration_uuid_flow_between_services(self, test_db_session):
        """测试Service间UUID流转的集成"""
        user_id = uuid4()
        task_id = uuid4()

        # 创建真实的服务对象测试UUID流转
        points_service = PointsService(test_db_session)
        service = Top3Service(test_db_session, points_service)

        # 添加积分到用户账户
        points_service.add_points(
            user_id=user_id,
            amount=500,
            source_type="test_top3"
        )

        # 验证余额查询支持UUID
        balance = points_service.get_balance(user_id)
        assert balance == 500

        # 验证Top3服务可以使用UUID查询用户积分
        balance_via_top3 = service.points_service.get_balance(user_id)
        assert balance_via_top3 == 500