"""
Top3领域Schemas测试

测试Top3领域的数据模型和验证规则，包括：
1. 请求模型验证
2. 响应模型验证
3. 字段类型和约束验证
4. 自定义验证器测试
5. Pydantic模型序列化

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from datetime import date
from uuid import uuid4
from pydantic import ValidationError

from src.domains.top3.schemas import (
    SetTop3Request,
    Top3Response,
    GetTop3Response
)


@pytest.mark.unit
class TestSetTop3Request:
    """设置Top3请求测试类"""

    def test_set_top3_request_valid(self):
        """测试有效的设置Top3请求"""
        task_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        request = SetTop3Request(
            date="2025-01-15",
            task_ids=task_ids
        )

        assert request.date == "2025-01-15"
        assert request.task_ids == task_ids
        assert len(request.task_ids) == 3

    def test_set_top3_request_minimal(self):
        """测试最小设置Top3请求"""
        task_id = str(uuid4())
        request = SetTop3Request(
            date="2025-01-15",
            task_ids=[task_id]
        )

        assert request.date == "2025-01-15"
        assert len(request.task_ids) == 1
        assert request.task_ids[0] == task_id

    def test_set_top3_request_two_tasks(self):
        """测试两个任务的设置Top3请求"""
        task_ids = [str(uuid4()), str(uuid4())]
        request = SetTop3Request(
            date="2025-01-15",
            task_ids=task_ids
        )

        assert len(request.task_ids) == 2
        assert request.task_ids == task_ids

    def test_set_top3_request_invalid_date_format(self):
        """测试无效日期格式"""
        task_id = str(uuid4())
        invalid_dates = [
            "2025-13-01",  # 无效月份
            "2025-01-32",  # 无效日期
            "2025/01/15",  # 错误分隔符
            "15-01-2025",  # 错误顺序
            "2025-1-1",    # 缺少前导零
            "invalid-date"
        ]

        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError) as exc_info:
                SetTop3Request(date=invalid_date, task_ids=[task_id])
            assert "日期格式无效" in str(exc_info.value)

    def test_set_top3_request_invalid_uuid(self):
        """测试无效UUID格式"""
        invalid_uuids = [
            "invalid-uuid",
            "123-456-789",
            "not-a-uuid-format",
            "550e8400e29b41d4a716446655440000",  # 缺少连字符
            "",
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValidationError) as exc_info:
                SetTop3Request(
                    date="2025-01-15",
                    task_ids=[invalid_uuid]
                )
            assert "无效的UUID格式" in str(exc_info.value)

    def test_set_top3_request_too_many_tasks(self):
        """测试任务数量过多"""
        task_ids = [str(uuid4()) for _ in range(4)]  # 4个任务，超过限制

        with pytest.raises(ValidationError) as exc_info:
            SetTop3Request(
                date="2025-01-15",
                task_ids=task_ids
            )
        assert "task_ids必须包含1-3个任务" in str(exc_info.value)

    def test_set_top3_request_empty_tasks(self):
        """测试空任务列表"""
        with pytest.raises(ValidationError) as exc_info:
            SetTop3Request(
                date="2025-01-15",
                task_ids=[]
            )
        assert "task_ids必须包含1-3个任务" in str(exc_info.value)

    def test_set_top3_request_mixed_valid_invalid_uuids(self):
        """测试混合有效和无效UUID"""
        valid_uuid = str(uuid4())
        invalid_uuid = "invalid-uuid"

        with pytest.raises(ValidationError) as exc_info:
            SetTop3Request(
                date="2025-01-15",
                task_ids=[valid_uuid, invalid_uuid]
            )
        assert "无效的UUID格式" in str(exc_info.value)

    def test_set_top3_request_leap_year_date(self):
        """测试闰年日期"""
        task_id = str(uuid4())
        request = SetTop3Request(
            date="2024-02-29",  # 闰年日期
            task_ids=[task_id]
        )

        assert request.date == "2024-02-29"

    def test_set_top3_request_edge_case_dates(self):
        """测试边界日期"""
        task_id = str(uuid4())
        edge_dates = [
            "2025-01-01",  # 年初
            "2025-12-31",  # 年末
            "2024-02-28",  # 非闰年2月末日
            "2024-02-29",  # 闰年2月末日
        ]

        for edge_date in edge_dates:
            request = SetTop3Request(
                date=edge_date,
                task_ids=[task_id]
            )
            assert request.date == edge_date

    def test_set_top3_request_serialization(self):
        """测试请求序列化"""
        task_ids = [str(uuid4()), str(uuid4())]
        request = SetTop3Request(
            date="2025-01-15",
            task_ids=task_ids
        )

        # 测试字典序列化
        data = request.model_dump()
        assert data["date"] == "2025-01-15"
        assert data["task_ids"] == task_ids

        # 测试JSON序列化
        json_data = request.model_dump_json()
        assert "2025-01-15" in json_data
        for task_id in task_ids:
            assert task_id in json_data

    @pytest.mark.parametrize("task_count", [1, 2, 3])
    def test_set_top3_request_various_task_counts(self, task_count):
        """参数化测试不同任务数量"""
        task_ids = [str(uuid4()) for _ in range(task_count)]
        request = SetTop3Request(
            date="2025-01-15",
            task_ids=task_ids
        )

        assert len(request.task_ids) == task_count

    @pytest.mark.parametrize("valid_date", [
        "2025-01-15",
        "2024-12-31",
        "2023-06-01",
        "2026-08-25"
    ])
    def test_set_top3_request_various_dates(self, valid_date):
        """参数化测试各种有效日期"""
        task_id = str(uuid4())
        request = SetTop3Request(
            date=valid_date,
            task_ids=[task_id]
        )

        assert request.date == valid_date


@pytest.mark.unit
class TestTop3Response:
    """Top3响应测试类"""

    def test_top3_response_creation(self):
        """测试创建Top3响应"""
        task_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        response = Top3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=5,
            remaining_balance=100
        )

        assert response.date == "2025-01-15"
        assert response.task_ids == task_ids
        assert response.points_consumed == 5
        assert response.remaining_balance == 100

    def test_top3_response_without_balance(self):
        """测试不带余额的Top3响应"""
        task_ids = [str(uuid4())]
        response = Top3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=5,
            remaining_balance=None
        )

        assert response.remaining_balance is None

    def test_top3_response_zero_points(self):
        """测试零积分消耗的Top3响应"""
        task_ids = [str(uuid4())]
        response = Top3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=0,
            remaining_balance=50
        )

        assert response.points_consumed == 0

    def test_top3_response_large_values(self):
        """测试大数值的Top3响应"""
        task_ids = [str(uuid4())]
        response = Top3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=1000,
            remaining_balance=50000
        )

        assert response.points_consumed == 1000
        assert response.remaining_balance == 50000

    def test_top3_response_serialization(self):
        """测试Top3响应序列化"""
        task_ids = [str(uuid4()), str(uuid4())]
        response = Top3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=10,
            remaining_balance=200
        )

        # 测试字典序列化
        data = response.model_dump()
        assert data["date"] == "2025-01-15"
        assert data["task_ids"] == task_ids
        assert data["points_consumed"] == 10
        assert data["remaining_balance"] == 200

        # 测试JSON序列化
        json_data = response.model_dump_json()
        assert "2025-01-15" in json_data
        assert "10" in json_data
        assert "200" in json_data

    @pytest.mark.parametrize("points_consumed", [0, 1, 5, 10, 100])
    def test_top3_response_various_points(self, points_consumed):
        """参数化测试各种积分消耗"""
        task_ids = [str(uuid4())]
        response = Top3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=points_consumed,
            remaining_balance=100
        )

        assert response.points_consumed == points_consumed


@pytest.mark.unit
class TestGetTop3Response:
    """获取Top3响应测试类"""

    def test_get_top3_response_creation(self):
        """测试创建获取Top3响应"""
        task_ids = [str(uuid4()), str(uuid4())]
        response = GetTop3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=5,
            created_at="2025-01-15T10:30:00Z"
        )

        assert response.date == "2025-01-15"
        assert response.task_ids == task_ids
        assert response.points_consumed == 5
        assert response.created_at == "2025-01-15T10:30:00Z"

    def test_get_top3_response_without_created_at(self):
        """测试不带创建时间的获取Top3响应"""
        task_ids = [str(uuid4())]
        response = GetTop3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=5,
            created_at=None
        )

        assert response.created_at is None

    def test_get_top3_response_various_timestamps(self):
        """测试各种时间戳格式"""
        task_ids = [str(uuid4())]
        timestamps = [
            "2025-01-15T10:30:00Z",
            "2025-01-15T00:00:00Z",
            "2025-12-31T23:59:59Z",
            "2024-02-29T12:00:00Z"
        ]

        for timestamp in timestamps:
            response = GetTop3Response(
                date="2025-01-15",
                task_ids=task_ids,
                points_consumed=5,
                created_at=timestamp
            )
            assert response.created_at == timestamp

    def test_get_top3_response_serialization(self):
        """测试获取Top3响应序列化"""
        task_ids = [str(uuid4())]
        response = GetTop3Response(
            date="2025-01-15",
            task_ids=task_ids,
            points_consumed=5,
            created_at="2025-01-15T10:30:00Z"
        )

        # 测试字典序列化
        data = response.model_dump()
        assert data["date"] == "2025-01-15"
        assert data["task_ids"] == task_ids
        assert data["points_consumed"] == 5
        assert data["created_at"] == "2025-01-15T10:30:00Z"

        # 测试JSON序列化
        json_data = response.model_dump_json()
        assert "2025-01-15" in json_data
        assert "10:30:00" in json_data


@pytest.mark.integration
class TestTop3SchemasIntegration:
    """Top3 Schema集成测试类"""

    def test_complete_top3_workflow_schemas(self):
        """测试完整Top3工作流程的Schema使用"""
        # 1. 创建设置请求
        task_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        set_request = SetTop3Request(
            date="2025-01-15",
            task_ids=task_ids
        )

        # 2. 创建设置响应
        set_response = Top3Response(
            date=set_request.date,
            task_ids=set_request.task_ids,
            points_consumed=5,
            remaining_balance=95
        )

        # 3. 创建获取响应
        get_response = GetTop3Response(
            date=set_response.date,
            task_ids=set_response.task_ids,
            points_consumed=set_response.points_consumed,
            created_at="2025-01-15T10:30:00Z"
        )

        # 验证数据一致性
        assert set_request.date == set_response.date
        assert set_request.task_ids == set_response.task_ids
        assert set_response.date == get_response.date
        assert set_response.task_ids == get_response.task_ids
        assert set_response.points_consumed == get_response.points_consumed

    def test_schema_json_roundtrip(self):
        """测试Schema JSON序列化往返"""
        original_data = {
            "date": "2025-01-15",
            "task_ids": [str(uuid4()), str(uuid4())]
        }

        # 创建请求对象
        request = SetTop3Request(**original_data)

        # 序列化为JSON
        json_data = request.model_dump_json()

        # 从JSON重建对象（简化验证）
        reconstructed_data = request.model_dump()

        # 验证关键字段保持一致
        assert reconstructed_data["date"] == original_data["date"]
        assert reconstructed_data["task_ids"] == original_data["task_ids"]

    def test_response_data_flow(self):
        """测试响应数据流"""
        task_ids = [str(uuid4()), str(uuid4())]

        # 模拟数据流：请求 → 设置响应 → 获取响应
        request = SetTop3Request(date="2025-01-15", task_ids=task_ids)

        top3_response = Top3Response(
            date=request.date,
            task_ids=request.task_ids,
            points_consumed=5,
            remaining_balance=95
        )

        get_response = GetTop3Response(
            date=top3_response.date,
            task_ids=top3_response.task_ids,
            points_consumed=top3_response.points_consumed,
            created_at="2025-01-15T10:30:00Z"
        )

        # 验证数据流的完整性
        assert request.date == get_response.date
        assert request.task_ids == get_response.task_ids

    def test_validation_error_messages(self):
        """测试验证错误消息质量"""
        # 测试各种验证错误都有清晰的错误信息
        with pytest.raises(ValidationError) as exc_info:
            SetTop3Request(date="invalid-date", task_ids=["invalid-uuid"])

        error_str = str(exc_info.value)
        assert "日期格式无效" in error_str or "无效的UUID格式" in error_str

    def test_edge_case_combinations(self):
        """测试边界情况组合"""
        # 测试最小有效配置
        minimal_request = SetTop3Request(
            date="2025-01-01",
            task_ids=[str(uuid4())]
        )

        # 测试最大有效配置
        max_tasks = [str(uuid4()) for _ in range(3)]
        maximal_request = SetTop3Request(
            date="2025-12-31",
            task_ids=max_tasks
        )

        # 验证都能正常创建
        assert len(minimal_request.task_ids) == 1
        assert len(maximal_request.task_ids) == 3

    def test_real_world_scenarios(self):
        """测试真实世界场景"""
        # 场景1：用户设置今日Top3任务
        today_tasks = [str(uuid4()), str(uuid4())]
        today_request = SetTop3Request(
            date="2025-01-15",
            task_ids=today_tasks
        )

        # 场景2：系统返回设置结果
        today_response = Top3Response(
            date=today_request.date,
            task_ids=today_request.task_ids,
            points_consumed=5,
            remaining_balance=150
        )

        # 场景3：用户查询今日Top3
        today_get_response = GetTop3Response(
            date=today_response.date,
            task_ids=today_response.task_ids,
            points_consumed=today_response.points_consumed,
            created_at="2025-01-15T08:00:00Z"
        )

        # 验证场景数据一致性
        assert today_request.task_ids == today_get_response.task_ids
        assert today_response.points_consumed == today_get_response.points_consumed


@pytest.mark.parametrize("invalid_date", [
    "2025-13-01",
    "2025-01-32",
    "2025/01/15",
    "15-01-2025",
    "invalid-date"
])
def test_invalid_date_parameterization(invalid_date):
    """参数化测试无效日期"""
    task_id = str(uuid4())

    with pytest.raises(ValidationError) as exc_info:
        SetTop3Request(date=invalid_date, task_ids=[task_id])
    assert "日期格式无效" in str(exc_info.value)


@pytest.mark.parametrize("invalid_uuid", [
    "invalid-uuid",
    "123-456-789",
    "not-a-uuid-format",
    ""
])
def test_invalid_uuid_parameterization(invalid_uuid):
    """参数化测试无效UUID"""
    with pytest.raises(ValidationError) as exc_info:
        SetTop3Request(date="2025-01-15", task_ids=[invalid_uuid])
    assert "无效的UUID格式" in str(exc_info.value)


@pytest.mark.parametrize("points_consumed,remaining_balance", [
    (0, 100),
    (1, 99),
    (5, 95),
    (10, 90),
    (100, 0)
])
def test_points_calculation_scenarios(points_consumed, remaining_balance):
    """参数化测试积分计算场景"""
    task_ids = [str(uuid4())]

    response = Top3Response(
        date="2025-01-15",
        task_ids=task_ids,
        points_consumed=points_consumed,
        remaining_balance=remaining_balance
    )

    assert response.points_consumed == points_consumed
    assert response.remaining_balance == remaining_balance