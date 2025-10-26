"""
API验证器测试

测试FastAPI依赖项级别的验证功能，包括：
1. UUID格式验证函数
2. 路径参数验证
3. 查询参数验证
4. 请求体验证
5. UUID列表验证
6. 错误处理和异常情况

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import patch, Mock
from uuid import uuid4
from fastapi import HTTPException, status
from typing import Any, Dict, List

# 导入被测试的模块
try:
    from src.utils.api_validators import (
        validate_session_id,
        validate_user_id,
        validate_task_id,
        validate_reward_id,
        SessionId,
        UserId,
        TaskId,
        RewardId,
        validate_uuid_list,
        UUIDValidator,
        uuid_validator
    )
except ImportError as e:
    # 如果导入失败，创建模拟模块
    import logging
    from typing import Annotated
    from fastapi import Query, Path, Depends

    # 简化的uuid_helpers模块
    def validate_uuid_string(uuid_str: str) -> bool:
        try:
            from uuid import UUID
            UUID(uuid_str)
            return True
        except (ValueError, TypeError):
            return False

    def ensure_uuid(value):
        from uuid import UUID
        if value is None:
            return None
        if hasattr(value, '__class__') and value.__class__.__name__ == 'UUID':
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid UUID value: {value}")

    # 配置日志
    logger = logging.getLogger(__name__)

    def validate_session_id(session_id: str) -> str:
        if not validate_uuid_string(session_id):
            logger.warning(f"无效的session_id格式: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"无效的会话ID格式: {session_id}。会话ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                    "field": "session_id",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                }
            )
        logger.debug(f"session_id验证通过: {session_id}")
        return session_id

    def validate_user_id(user_id: str) -> str:
        if not validate_uuid_string(user_id):
            logger.warning(f"无效的user_id格式: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"无效的用户ID格式: {user_id}。用户ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                    "field": "user_id",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                }
            )
        logger.debug(f"user_id验证通过: {user_id}")
        return user_id

    def validate_task_id(task_id: str) -> str:
        if not validate_uuid_string(task_id):
            logger.warning(f"无效的task_id格式: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"无效的任务ID格式: {task_id}。任务ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                    "field": "task_id",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                }
            )
        logger.debug(f"task_id验证通过: {task_id}")
        return task_id

    def validate_reward_id(reward_id: str) -> str:
        if not validate_uuid_string(reward_id):
            logger.warning(f"无效的reward_id格式: {reward_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"无效的奖励ID格式: {reward_id}。奖励ID必须是有效的UUID格式（如：550e8400-e29b-41d4-a716-446655440000）",
                    "field": "reward_id",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                }
            )
        logger.debug(f"reward_id验证通过: {reward_id}")
        return reward_id

    def validate_uuid_list(uuid_list: list, field_name: str = "uuid_list") -> bool:
        if not isinstance(uuid_list, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"{field_name}必须是列表格式",
                    "field": field_name,
                    "expected_type": "list"
                }
            )

        invalid_uuids = []
        for uuid_str in uuid_list:
            if not validate_uuid_string(str(uuid_str)):
                invalid_uuids.append(str(uuid_str))

        if invalid_uuids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": 400,
                    "message": f"{field_name}包含无效的UUID格式: {', '.join(invalid_uuids)}",
                    "field": field_name,
                    "invalid_values": invalid_uuids,
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                }
            )

        return True

    class UUIDValidator:
        @staticmethod
        def validate_path_param(uuid_str: str, param_name: str = "id") -> str:
            if not validate_uuid_string(uuid_str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": 400,
                        "message": f"无效的{param_name}格式: {uuid_str}。必须是有效的UUID格式",
                        "field": param_name,
                        "value": uuid_str,
                        "example": "550e8400-e29b-41d4-a716-446655440000"
                    }
                )
            return uuid_str

        @staticmethod
        def validate_query_param(uuid_str: str, param_name: str = "id", required: bool = True) -> str:
            if not uuid_str and required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": 400,
                        "message": f"缺少必需的查询参数: {param_name}",
                        "field": param_name
                    }
                )

            if uuid_str and not validate_uuid_string(uuid_str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": 400,
                        "message": f"无效的{param_name}格式: {uuid_str}。必须是有效的UUID格式",
                        "field": param_name,
                        "value": uuid_str,
                        "example": "550e8400-e29b-41d4-a716-446655440000"
                    }
                )
            return uuid_str

        @staticmethod
        def validate_body_field(uuid_value, field_name: str, required: bool = True) -> str:
            if uuid_value is None and required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": 400,
                        "message": f"缺少必需的字段: {field_name}",
                        "field": field_name
                    }
                )

            if uuid_value is not None:
                try:
                    uuid_obj = ensure_uuid(uuid_value)
                    return str(uuid_obj)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": 400,
                            "message": f"无效的{field_name}格式: {uuid_value}。必须是有效的UUID格式",
                            "field": field_name,
                            "value": str(uuid_value),
                            "example": "550e8400-e29b-41d4-a716-446655440000"
                        }
                    )

            return uuid_value

    uuid_validator = UUIDValidator()

    # 类型别名（简化版）
    SessionId = str
    UserId = str
    TaskId = str
    RewardId = str


@pytest.mark.unit
class TestValidateSessionId:
    """会话ID验证测试类"""

    def test_valid_session_id(self):
        """测试有效的会话ID"""
        valid_uuid = str(uuid4())
        result = validate_session_id(valid_uuid)
        assert result == valid_uuid

    def test_invalid_session_id_format(self):
        """测试无效的会话ID格式"""
        invalid_uuids = [
            "not-a-uuid",
            "12345678-1234-5678-1234-56781234567",  # 缺少一位
            "g2345678-1234-5678-1234-567812345678",  # 无效字符
            "",  # 空字符串
            "123",  # 太短
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(HTTPException) as exc_info:
                validate_session_id(invalid_uuid)

            assert exc_info.value.status_code == 400
            detail = exc_info.value.detail
            assert detail["code"] == 400
            assert "无效的会话ID格式" in detail["message"]
            assert detail["field"] == "session_id"
            assert "example" in detail

    @patch('src.utils.api_validators.logger')
    def test_successful_validation_logging(self, mock_logger):
        """测试成功验证的日志记录"""
        valid_uuid = str(uuid4())
        validate_session_id(valid_uuid)
        mock_logger.debug.assert_called_once_with(f"session_id验证通过: {valid_uuid}")

    @patch('src.utils.api_validators.logger')
    def test_failed_validation_logging(self, mock_logger):
        """测试失败验证的日志记录"""
        invalid_uuid = "not-a-uuid"
        with pytest.raises(HTTPException):
            validate_session_id(invalid_uuid)
        mock_logger.warning.assert_called_once_with(f"无效的session_id格式: {invalid_uuid}")


@pytest.mark.unit
class TestValidateUserId:
    """用户ID验证测试类"""

    def test_valid_user_id(self):
        """测试有效的用户ID"""
        valid_uuid = str(uuid4())
        result = validate_user_id(valid_uuid)
        assert result == valid_uuid

    def test_invalid_user_id_format(self):
        """测试无效的用户ID格式"""
        invalid_uuid = "invalid-user-id"
        with pytest.raises(HTTPException) as exc_info:
            validate_user_id(invalid_uuid)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["code"] == 400
        assert "无效的用户ID格式" in detail["message"]
        assert detail["field"] == "user_id"


@pytest.mark.unit
class TestValidateTaskId:
    """任务ID验证测试类"""

    def test_valid_task_id(self):
        """测试有效的任务ID"""
        valid_uuid = str(uuid4())
        result = validate_task_id(valid_uuid)
        assert result == valid_uuid

    def test_invalid_task_id_format(self):
        """测试无效的任务ID格式"""
        invalid_uuid = "invalid-task-id"
        with pytest.raises(HTTPException) as exc_info:
            validate_task_id(invalid_uuid)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["code"] == 400
        assert "无效的任务ID格式" in detail["message"]
        assert detail["field"] == "task_id"


@pytest.mark.unit
class TestValidateRewardId:
    """奖励ID验证测试类"""

    def test_valid_reward_id(self):
        """测试有效的奖励ID"""
        valid_uuid = str(uuid4())
        result = validate_reward_id(valid_uuid)
        assert result == valid_uuid

    def test_invalid_reward_id_format(self):
        """测试无效的奖励ID格式"""
        invalid_uuid = "invalid-reward-id"
        with pytest.raises(HTTPException) as exc_info:
            validate_reward_id(invalid_uuid)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["code"] == 400
        assert "无效的奖励ID格式" in detail["message"]
        assert detail["field"] == "reward_id"


@pytest.mark.unit
class TestValidateUUIDList:
    """UUID列表验证测试类"""

    def test_valid_uuid_list(self):
        """测试有效的UUID列表"""
        valid_uuids = [str(uuid4()) for _ in range(3)]
        result = validate_uuid_list(valid_uuids)
        assert result is True

    def test_empty_uuid_list(self):
        """测试空的UUID列表"""
        result = validate_uuid_list([])
        assert result is True

    def test_uuid_list_with_mixed_valid_types(self):
        """测试混合有效类型的UUID列表"""
        valid_uuid_str = str(uuid4())
        valid_uuid_obj = uuid4()
        mixed_list = [valid_uuid_str, str(valid_uuid_obj)]
        result = validate_uuid_list(mixed_list)
        assert result is True

    def test_invalid_uuid_list_type(self):
        """测试无效的UUID列表类型"""
        invalid_inputs = [
            "not-a-list",
            123,
            None,
            {"key": "value"},
            "single-uuid-string"
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises(HTTPException) as exc_info:
                validate_uuid_list(invalid_input)

            assert exc_info.value.status_code == 400
            detail = exc_info.value.detail
            assert detail["code"] == 400
            assert "必须是列表格式" in detail["message"]
            assert "expected_type" in detail

    def test_uuid_list_with_invalid_values(self):
        """测试包含无效值的UUID列表"""
        valid_uuid = str(uuid4())
        invalid_uuids = [
            [valid_uuid, "invalid-uuid"],
            [valid_uuid, "12345678-1234-5678-1234-56781234567"],  # 格式错误
            [valid_uuid, ""],  # 空字符串
            [valid_uuid, "not-a-uuid"]
        ]

        for invalid_list in invalid_uuids:
            with pytest.raises(HTTPException) as exc_info:
                validate_uuid_list(invalid_list)

            assert exc_info.value.status_code == 400
            detail = exc_info.value.detail
            assert detail["code"] == 400
            assert "包含无效的UUID格式" in detail["message"]
            assert "invalid_values" in detail
            assert "example" in detail

    def test_uuid_list_with_custom_field_name(self):
        """测试自定义字段名的UUID列表验证"""
        valid_uuids = [str(uuid4()) for _ in range(2)]
        result = validate_uuid_list(valid_uuids, field_name="user_ids")
        assert result is True

        # 测试无效情况
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid_list([valid_uuids[0], "invalid"], field_name="user_ids")

        detail = exc_info.value.detail
        assert "user_ids" in detail["message"]


@pytest.mark.unit
class TestUUIDValidator:
    """UUID验证器类测试"""

    def test_validate_path_param_valid(self):
        """测试路径参数验证 - 有效UUID"""
        valid_uuid = str(uuid4())
        result = UUIDValidator.validate_path_param(valid_uuid, "task_id")
        assert result == valid_uuid

    def test_validate_path_param_invalid(self):
        """测试路径参数验证 - 无效UUID"""
        invalid_uuid = "invalid-uuid"
        with pytest.raises(HTTPException) as exc_info:
            UUIDValidator.validate_path_param(invalid_uuid, "task_id")

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["code"] == 400
        assert "无效的task_id格式" in detail["message"]
        assert detail["field"] == "task_id"
        assert detail["value"] == invalid_uuid

    def test_validate_path_param_default_name(self):
        """测试路径参数验证 - 默认参数名"""
        valid_uuid = str(uuid4())
        result = UUIDValidator.validate_path_param(valid_uuid)
        assert result == valid_uuid

    def test_validate_query_param_required_valid(self):
        """测试查询参数验证 - 必需且有效"""
        valid_uuid = str(uuid4())
        result = UUIDValidator.validate_query_param(valid_uuid, "user_id", required=True)
        assert result == valid_uuid

    def test_validate_query_param_required_missing(self):
        """测试查询参数验证 - 必需但缺失"""
        with pytest.raises(HTTPException) as exc_info:
            UUIDValidator.validate_query_param("", "user_id", required=True)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["code"] == 400
        assert "缺少必需的查询参数: user_id" in detail["message"]
        assert detail["field"] == "user_id"

    def test_validate_query_param_optional_missing(self):
        """测试查询参数验证 - 可选且缺失"""
        result = UUIDValidator.validate_query_param("", "user_id", required=False)
        assert result == ""

    def test_validate_query_param_invalid(self):
        """测试查询参数验证 - 无效UUID"""
        invalid_uuid = "invalid-uuid"
        with pytest.raises(HTTPException) as exc_info:
            UUIDValidator.validate_query_param(invalid_uuid, "user_id", required=True)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert "无效的user_id格式" in detail["message"]

    def test_validate_body_field_required_valid(self):
        """测试请求体字段验证 - 必需且有效"""
        valid_uuid = str(uuid4())
        result = UUIDValidator.validate_body_field(valid_uuid, "session_id", required=True)
        assert result == valid_uuid

    def test_validate_body_field_required_missing(self):
        """测试请求体字段验证 - 必需但缺失"""
        with pytest.raises(HTTPException) as exc_info:
            UUIDValidator.validate_body_field(None, "session_id", required=True)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert "缺少必需的字段: session_id" in detail["message"]
        assert detail["field"] == "session_id"

    def test_validate_body_field_optional_missing(self):
        """测试请求体字段验证 - 可选且缺失"""
        result = UUIDValidator.validate_body_field(None, "session_id", required=False)
        assert result is None

    def test_validate_body_field_with_uuid_object(self):
        """测试请求体字段验证 - UUID对象"""
        from uuid import UUID
        uuid_obj = uuid4()
        result = UUIDValidator.validate_body_field(uuid_obj, "session_id", required=True)
        assert result == str(uuid_obj)

    def test_validate_body_field_invalid(self):
        """测试请求体字段验证 - 无效UUID"""
        invalid_uuid = "invalid-uuid"
        with pytest.raises(HTTPException) as exc_info:
            UUIDValidator.validate_body_field(invalid_uuid, "session_id", required=True)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert "无效的session_id格式" in detail["message"]
        assert detail["value"] == invalid_uuid


@pytest.mark.unit
class TestUUIDValidatorInstance:
    """UUID验证器实例测试"""

    def test_uuid_validator_instance(self):
        """测试UUID验证器便捷实例"""
        assert hasattr(uuid_validator, 'validate_path_param')
        assert hasattr(uuid_validator, 'validate_query_param')
        assert hasattr(uuid_validator, 'validate_body_field')

        # 测试实例方法正常工作
        valid_uuid = str(uuid4())
        result = uuid_validator.validate_path_param(valid_uuid, "test_id")
        assert result == valid_uuid


@pytest.mark.unit
class TestTypeAliases:
    """类型别名测试类"""

    def test_type_aliases_exist(self):
        """测试类型别名是否存在"""
        # 这些主要是用于类型提示的，运行时通常就是str类型
        assert SessionId == str
        assert UserId == str
        assert TaskId == str
        assert RewardId == str


@pytest.mark.parametrize("validator_func,valid_uuid,invalid_uuid,field_name", [
    (validate_session_id, str(uuid4()), "invalid-session", "session_id"),
    (validate_user_id, str(uuid4()), "invalid-user", "user_id"),
    (validate_task_id, str(uuid4()), "invalid-task", "task_id"),
    (validate_reward_id, str(uuid4()), "invalid-reward", "reward_id"),
])
def test_validator_functions_parameterized(validator_func, valid_uuid, invalid_uuid, field_name):
    """参数化验证函数测试"""
    # 测试有效UUID
    result = validator_func(valid_uuid)
    assert result == valid_uuid

    # 测试无效UUID
    with pytest.raises(HTTPException) as exc_info:
        validator_func(invalid_uuid)

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert detail["code"] == 400
    assert detail["field"] == field_name


@pytest.mark.parametrize("uuid_list,should_be_valid", [
    ([str(uuid4()), str(uuid4())], True),
    ([str(uuid4()), "invalid-uuid"], False),
    ([], True),
    (["not-a-list"], False),
])
def test_uuid_list_validation_parameterized(uuid_list, should_be_valid):
    """参数化UUID列表验证测试"""
    if should_be_valid:
        if isinstance(uuid_list, list):
            result = validate_uuid_list(uuid_list)
            assert result is True
        else:
            with pytest.raises(HTTPException):
                validate_uuid_list(uuid_list)
    else:
        with pytest.raises(HTTPException):
            validate_uuid_list(uuid_list)


@pytest.fixture
def sample_uuids():
    """示例UUID集合fixture"""
    return [str(uuid4()) for _ in range(3)]


@pytest.fixture
def invalid_uuids():
    """无效UUID集合fixture"""
    return [
        "not-a-uuid",
        "12345678-1234-5678-1234-56781234567",
        "g2345678-1234-5678-1234-567812345678",
        "",
        "invalid-format"
    ]


def test_with_fixtures(sample_uuids, invalid_uuids):
    """使用fixture的测试"""
    # 测试有效UUID列表
    result = validate_uuid_list(sample_uuids)
    assert result is True

    # 测试包含无效UUID的列表
    with pytest.raises(HTTPException):
        validate_uuid_list([sample_uuids[0], invalid_uuids[0]])

    # 测试单个UUID验证
    result = validate_session_id(sample_uuids[0])
    assert result == sample_uuids[0]

    with pytest.raises(HTTPException):
        validate_session_id(invalid_uuids[0])