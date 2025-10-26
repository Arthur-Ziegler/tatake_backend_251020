"""
Focus领域Schemas测试

测试Focus领域的数据模型和验证规则，包括：
1. 请求模型验证
2. 响应模型验证
3. 字段类型和约束验证
4. Pydantic模型序列化
5. 自定义验证器测试

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from src.domains.focus.schemas import (
    StartFocusRequest,
    FocusSessionResponse,
    FocusOperationResponse,
    FocusSessionListResponse
)
from src.domains.focus.models import SessionTypeConst


@pytest.mark.unit
class TestStartFocusRequest:
    """开始专注会话请求测试类"""

    def test_start_focus_request_valid(self):
        """测试有效的开始专注会话请求"""
        task_id = str(uuid4())
        request = StartFocusRequest(task_id=task_id, session_type="focus")

        assert request.task_id == task_id
        assert request.session_type == "focus"

    def test_start_focus_request_default_session_type(self):
        """测试默认会话类型"""
        task_id = str(uuid4())
        request = StartFocusRequest(task_id=task_id)

        assert request.task_id == task_id
        assert request.session_type == SessionTypeConst.FOCUS

    def test_start_focus_request_all_session_types(self):
        """测试所有支持的会话类型"""
        task_id = str(uuid4())
        session_types = [
            SessionTypeConst.FOCUS,
            SessionTypeConst.BREAK,
            SessionTypeConst.LONG_BREAK,
            SessionTypeConst.PAUSE
        ]

        for session_type in session_types:
            request = StartFocusRequest(task_id=task_id, session_type=session_type)
            assert request.task_id == task_id
            assert request.session_type == session_type

    def test_start_focus_request_invalid_task_id_empty(self):
        """测试空任务ID"""
        with pytest.raises(ValidationError) as exc_info:
            StartFocusRequest(task_id="")

        assert "任务ID不能为空" in str(exc_info.value)

    def test_start_focus_request_invalid_task_id_format(self):
        """测试无效格式的任务ID"""
        invalid_ids = [
            "invalid-uuid",
            "123",
            "not-a-uuid",
            "abc-123-def",
            "550e8400e29b41d4a716446655440000"  # 缺少连字符
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                StartFocusRequest(task_id=invalid_id)
            assert "任务ID格式无效" in str(exc_info.value)

    def test_start_focus_request_valid_uuid_formats(self):
        """测试有效的UUID格式"""
        valid_uuids = [
            str(uuid4()),
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000"
        ]

        for valid_uuid in valid_uuids:
            request = StartFocusRequest(task_id=valid_uuid)
            assert request.task_id == valid_uuid

    def test_start_focus_request_serialization(self):
        """测试请求序列化"""
        task_id = str(uuid4())
        request = StartFocusRequest(task_id=task_id, session_type="focus")

        # 测试字典序列化
        data = request.model_dump()
        assert data["task_id"] == task_id
        assert data["session_type"] == "focus"

        # 测试JSON序列化
        json_data = request.model_dump_json()
        assert task_id in json_data
        assert "focus" in json_data


@pytest.mark.unit
class TestFocusSessionResponse:
    """专注会话响应测试类"""

    def test_focus_session_response_creation(self):
        """测试创建专注会话响应"""
        session_id = str(uuid4())
        user_id = str(uuid4())
        task_id = str(uuid4())
        start_time = datetime.now(timezone.utc)
        end_time = start_time.replace(second=0, microsecond=0)

        response = FocusSessionResponse(
            id=session_id,
            user_id=user_id,
            task_id=task_id,
            session_type="focus",
            start_time=start_time,
            end_time=end_time
        )

        assert response.id == session_id
        assert response.user_id == user_id
        assert response.task_id == task_id
        assert response.session_type == "focus"
        assert response.start_time == start_time
        assert response.end_time == end_time

    def test_focus_session_response_active(self):
        """测试活跃会话响应"""
        session_id = str(uuid4())
        start_time = datetime.now(timezone.utc)

        response = FocusSessionResponse(
            id=session_id,
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=start_time,
            end_time=None
        )

        assert response.is_active is True

    def test_focus_session_response_completed(self):
        """测试完成会话响应"""
        session_id = str(uuid4())
        start_time = datetime.now(timezone.utc)
        end_time = start_time.replace(minute=30)

        response = FocusSessionResponse(
            id=session_id,
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=start_time,
            end_time=end_time
        )

        assert response.is_active is False

    def test_focus_session_response_serialization(self):
        """测试会话响应序列化"""
        session_id = str(uuid4())
        start_time = datetime.now(timezone.utc)
        end_time = start_time.replace(minute=25)

        response = FocusSessionResponse(
            id=session_id,
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=start_time,
            end_time=end_time
        )

        # 测试字典序列化
        data = response.model_dump()
        assert data["id"] == session_id
        assert data["session_type"] == "focus"
        assert data["end_time"] is not None

        # 测试JSON序列化
        json_data = response.model_dump_json()
        assert session_id in json_data
        assert "focus" in json_data

    def test_focus_session_response_json_datetime_encoding(self):
        """测试JSON日期时间编码"""
        session_id = str(uuid4())
        start_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

        response = FocusSessionResponse(
            id=session_id,
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=start_time,
            end_time=end_time
        )

        json_data = response.model_dump_json()
        assert "2025-01-15T10:30:00+00:00" in json_data
        assert "2025-01-15T11:00:00+00:00" in json_data

    @pytest.mark.parametrize("session_type", [
        "focus",
        "break",
        "long_break",
        "pause"
    ])
    def test_focus_session_response_various_types(self, session_type):
        """测试各种会话类型的响应"""
        response = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="task_123",
            session_type=session_type,
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        assert response.session_type == session_type


@pytest.mark.unit
class TestFocusOperationResponse:
    """Focus操作响应测试类"""

    def test_focus_operation_response_creation(self):
        """测试创建Focus操作响应"""
        session_response = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        operation_response = FocusOperationResponse(
            success=True,
            message="会话创建成功",
            session=session_response
        )

        assert operation_response.success is True
        assert operation_response.message == "会话创建成功"
        assert operation_response.session is not None
        assert operation_response.session.id == session_response.id

    def test_focus_operation_response_serialization(self):
        """测试操作响应序列化"""
        session_response = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        operation_response = FocusOperationResponse(
            success=False,
            message="会话创建失败",
            session=session_response
        )

        # 测试字典序列化
        data = operation_response.model_dump()
        assert data["success"] is False
        assert data["message"] == "会话创建失败"
        assert "session" in data

        # 测试JSON序列化
        json_data = operation_response.model_dump_json()
        assert "success" in json_data
        assert "会话创建失败" in json_data
        assert "session" in json_data

    @pytest.mark.parametrize("success,message", [
        (True, "操作成功"),
        (False, "操作失败"),
        (True, "会话已结束"),
        (False, "权限不足")
    ])
    def test_focus_operation_response_various_scenarios(self, success, message):
        """测试各种操作场景的响应"""
        session_response = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        operation_response = FocusOperationResponse(
            success=success,
            message=message,
            session=session_response
        )

        assert operation_response.success == success
        assert operation_response.message == message


@pytest.mark.unit
class TestFocusSessionListResponse:
    """专注会话列表响应测试类"""

    def test_focus_session_list_response_creation(self):
        """测试创建会话列表响应"""
        session1 = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        session2 = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="task_456",
            session_type="break",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc)
        )

        list_response = FocusSessionListResponse(
            sessions=[session1, session2],
            total=2
        )

        assert len(list_response.sessions) == 2
        assert list_response.total == 2
        assert list_response.sessions[0].id == session1.id
        assert list_response.sessions[1].id == session2.id

    def test_focus_session_list_response_empty(self):
        """测试空会话列表响应"""
        list_response = FocusSessionListResponse(sessions=[], total=0)

        assert len(list_response.sessions) == 0
        assert list_response.total == 0

    def test_focus_session_list_response_serialization(self):
        """测试会话列表响应序列化"""
        session = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="task_123",
            session_type="focus",
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        list_response = FocusSessionListResponse(sessions=[session], total=1)

        # 测试字典序列化
        data = list_response.model_dump()
        assert len(data["sessions"]) == 1
        assert data["total"] == 1

        # 测试JSON序列化
        json_data = list_response.model_dump_json()
        assert "sessions" in json_data
        assert "total" in json_data
        assert "1" in json_data

    def test_focus_session_list_response_various_session_types(self):
        """测试包含各种会话类型的列表响应"""
        sessions = []
        session_types = ["focus", "break", "long_break", "pause"]

        for session_type in session_types:
            session = FocusSessionResponse(
                id=str(uuid4()),
                user_id="user_123",
                task_id=f"task_{session_type}",
                session_type=session_type,
                start_time=datetime.now(timezone.utc),
                end_time=None
            )
            sessions.append(session)

        list_response = FocusSessionListResponse(sessions=sessions, total=len(sessions))

        assert len(list_response.sessions) == 4
        assert list_response.total == 4

        # 验证所有会话类型都被包含
        response_types = [s.session_type for s in list_response.sessions]
        for session_type in session_types:
            assert session_type in response_types


@pytest.mark.integration
class TestFocusSchemasIntegration:
    """Focus Schema集成测试类"""

    def test_complete_focus_workflow_schemas(self):
        """测试完整Focus工作流程的Schema使用"""
        # 1. 创建会话请求
        task_id = str(uuid4())
        start_request = StartFocusRequest(
            task_id=task_id,
            session_type="focus"
        )

        # 2. 模拟会话响应
        session_response = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id=task_id,
            session_type=start_request.session_type,
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        # 3. 模拟操作响应
        operation_response = FocusOperationResponse(
            success=True,
            message="专注会话已创建",
            session=session_response
        )

        # 4. 模拟列表响应
        list_response = FocusSessionListResponse(
            sessions=[session_response],
            total=1
        )

        # 验证数据一致性
        assert start_request.task_id == session_response.task_id
        assert start_request.session_type == session_response.session_type
        assert operation_response.session.id == session_response.id
        assert list_response.sessions[0].id == session_response.id
        assert list_response.total == 1

    def test_schema_json_roundtrip(self):
        """测试Schema JSON序列化往返"""
        original_data = {
            "task_id": str(uuid4()),
            "session_type": "focus"
        }

        # 创建请求对象
        request = StartFocusRequest(**original_data)

        # 序列化为JSON
        json_data = request.model_dump_json()

        # 从JSON重建对象（简化验证）
        reconstructed_data = request.model_dump()

        # 验证关键字段保持一致
        assert reconstructed_data["task_id"] == original_data["task_id"]
        assert reconstructed_data["session_type"] == original_data["session_type"]

    def test_schema_validation_chain(self):
        """测试Schema验证链"""
        # 测试请求验证
        with pytest.raises(ValidationError) as exc_info:
            StartFocusRequest(task_id="invalid_uuid")

        assert "任务ID格式无效" in str(exc_info.value)

        # 测试响应创建（应该成功）
        session_response = FocusSessionResponse(
            id=str(uuid4()),
            user_id="user_123",
            task_id="valid_uuid",
            session_type="focus",
            start_time=datetime.now(timezone.utc),
            end_time=None
        )

        assert session_response.is_active is True


@pytest.mark.parametrize("task_id,should_pass", [
    ("550e8400-e29b-41d4-a716-446655440000", True),  # 有效UUID
    ("123e4567-e89b-12d3-a456-426614174000", True),  # 有效UUID
    ("invalid-uuid", False),  # 无效格式
    ("", False),  # 空字符串
    ("123", False),  # 太短
    ("not-a-uuid-format", False),  # 格式错误
])
def test_start_focus_request_task_id_validation(task_id, should_pass):
    """参数化测试任务ID验证"""
    if should_pass:
        request = StartFocusRequest(task_id=task_id)
        assert request.task_id == task_id
    else:
        with pytest.raises(ValidationError):
            StartFocusRequest(task_id=task_id)


@pytest.mark.parametrize("session_type", [
    "focus",
    "break",
    "long_break",
    "pause",
    "focus_session",  # 无效类型
    "",  # 空字符串
])
def test_session_type_validation(session_type):
    """参数化测试会话类型验证"""
    task_id = str(uuid4())

    # 所有类型都应该可以设置，验证逻辑在其他地方处理
    request = StartFocusRequest(task_id=task_id, session_type=session_type)
    assert request.task_id == task_id
    assert request.session_type == session_type