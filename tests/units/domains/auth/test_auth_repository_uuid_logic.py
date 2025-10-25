"""
AuthRepository UUID转换逻辑完善测试

测试AuthRepository中UUID转换逻辑的完善情况，确保类型安全和错误处理。

作者：TaKeKe团队
版本：1.0.0 - UUID架构Batch 1测试
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository
from src.core.uuid_converter import UUIDConverter


class TestAuthRepositoryUUIDLogic:
    """AuthRepository UUID转换逻辑测试"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = Mock(spec=Session)
        session.exec = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()
        session.rollback = Mock()
        return session

    @pytest.fixture
    def auth_repository(self, mock_session):
        """创建AuthRepository实例"""
        return AuthRepository(mock_session)

    @pytest.fixture
    def audit_repository(self, mock_session):
        """创建AuditRepository实例"""
        return AuditRepository(mock_session)

    @pytest.fixture
    def sample_user_uuid(self):
        """创建示例用户UUID"""
        return uuid.uuid4()

    def test_get_by_id_enhanced_type_validation(self, auth_repository, sample_user_uuid):
        """测试get_by_id方法的增强类型验证"""
        # 模拟数据库查询成功
        mock_result = Mock()
        mock_result.id = str(sample_user_uuid)
        auth_repository.session.exec.return_value.first.return_value = mock_result

        # 正确的UUID类型调用
        result = auth_repository.get_by_id(sample_user_uuid)
        assert result is mock_result
        auth_repository.session.exec.assert_called_once()

        # 验证UUID转换被正确使用
        call_args = auth_repository.session.exec.call_args[0][0]
        assert call_args is not None

    def test_get_by_id_raises_type_error(self, auth_repository):
        """测试get_by_id方法对错误类型的处理"""
        # 测试各种错误的输入类型
        invalid_inputs = [
            "string_uuid",  # 字符串而不是UUID对象
            12345,  # 整数
            {"id": "uuid"},  # 字典
            ["uuid"],  # 列表
            None,  # None值
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises(TypeError) as exc_info:
                auth_repository.get_by_id(invalid_input)

            # 验证错误消息包含类型信息
            assert "user_id must be UUID object" in str(exc_info.value)

    def test_get_by_id_database_error_handling(self, auth_repository, sample_user_uuid):
        """测试get_by_id方法的数据库错误处理"""
        # 模拟数据库错误
        auth_repository.session.exec.side_effect = Exception("Database connection failed")

        # 应该优雅地处理错误并返回None
        result = auth_repository.get_by_id(sample_user_uuid)
        assert result is None

    def test_audit_repository_uuid_validation(self, audit_repository, sample_user_uuid):
        """测试AuditRepository的UUID验证和转换"""
        # 模拟数据库操作成功
        audit_repository.session.add.return_value = None
        audit_repository.session.commit.return_value = None
        audit_repository.session.refresh.return_value = None

        # 创建审计日志
        result = audit_repository.create_log(
            user_id=sample_user_uuid,
            action="test_action",
            result="success",
            details="test details",
            ip_address="127.0.0.1"
        )

        # 验证返回了审计日志对象
        assert result is not None
        # 验证结果是AuthLog类型（真实的模型对象）
        from src.domains.auth.models import AuthLog
        assert isinstance(result, AuthLog)

        # 验证数据库操作被调用
        audit_repository.session.add.assert_called_once()
        audit_repository.session.commit.assert_called_once()

    def test_audit_repository_invalid_uuid_handling(self, audit_repository):
        """测试AuditRepository对无效UUID的处理"""
        # 模拟数据库操作成功
        audit_repository.session.add.return_value = None
        audit_repository.session.commit.return_value = None
        audit_repository.session.refresh.return_value = None

        # 测试各种无效的UUID类型
        invalid_uuids = [
            "invalid_uuid_string",
            12345,
            {"id": "uuid"},
            ["uuid_list"],
            uuid.uuid4().bytes  # bytes而不是UUID对象
        ]

        for invalid_uuid in invalid_uuids:
            # 应该能够处理而不抛出异常（审计日志应该记录所有操作）
            result = audit_repository.create_log(
                user_id=invalid_uuid,
                action="test_action",
                result="success",
                details="test details"
            )

            # 验证数据库操作仍然被调用
            audit_repository.session.add.assert_called()
            audit_repository.session.commit.assert_called()

    def test_audit_repository_none_user_id(self, audit_repository):
        """测试AuditRepository对None user_id的处理"""
        # 模拟数据库操作成功
        audit_repository.session.add.return_value = None
        audit_repository.session.commit.return_value = None
        audit_repository.session.refresh.return_value = None

        # None user_id应该被正确处理（游客操作）
        result = audit_repository.create_log(
            user_id=None,
            action="guest_action",
            result="success",
            details="Guest user operation"
        )

        # 验证返回了审计日志对象
        assert result is not None

    def test_audit_repository_database_error_handling(self, audit_repository, sample_user_uuid):
        """测试AuditRepository的数据库错误处理"""
        # 模拟数据库错误
        audit_repository.session.add.side_effect = Exception("Database constraint violation")

        # 应该优雅地处理错误并返回None
        result = audit_repository.create_log(
            user_id=sample_user_uuid,
            action="test_action",
            result="success"
        )

        assert result is None
        # 验证回滚被调用
        audit_repository.session.rollback.assert_called_once()

    def test_uuid_converter_integration(self):
        """测试UUIDConverter的集成使用"""
        test_uuid = uuid.uuid4()

        # 测试UUIDConverter的to_string方法
        result = UUIDConverter.to_string(test_uuid)
        assert result == str(test_uuid)
        assert isinstance(result, str)
        assert len(result) == 36  # UUID字符串长度

        # 测试UUIDConverter的to_uuid方法
        result_uuid = UUIDConverter.to_uuid(str(test_uuid))
        assert result_uuid == test_uuid
        assert isinstance(result_uuid, UUID)

        # 测试无效的UUID字符串转换
        with pytest.raises(ValueError):
            UUIDConverter.to_uuid("invalid_uuid_string")

    def test_uuid_converter_error_types(self):
        """测试UUIDConverter的错误类型处理"""
        # 测试to_string方法的类型检查
        with pytest.raises(TypeError):
            UUIDConverter.to_string("string_uuid")

        with pytest.raises(TypeError):
            UUIDConverter.to_string(12345)

        with pytest.raises(TypeError):
            UUIDConverter.to_string(None)

    def test_auth_repository_batch_operations(self, auth_repository):
        """测试AuthRepository的批量操作UUID处理"""
        user_ids = [uuid.uuid4() for _ in range(3)]

        # 模拟批量查询
        def mock_exec_side_effect(statement):
            # 模拟返回不同的结果
            if "test_user_1" in str(statement):
                mock_result = Mock()
                mock_result.id = str(user_ids[0])
                return Mock(first=lambda: mock_result)
            return Mock(first=lambda: None)

        auth_repository.session.exec.side_effect = mock_exec_side_effect

        # 测试批量获取用户
        results = []
        for user_id in user_ids:
            result = auth_repository.get_by_id(user_id)
            results.append(result)

        # 验证所有查询都被执行
        assert auth_repository.session.exec.call_count == 3

    def test_audit_repository_comprehensive_logging(self, audit_repository, sample_user_uuid):
        """测试AuditRepository的综合日志记录"""
        audit_repository.session.add.return_value = None
        audit_repository.session.commit.return_value = None
        audit_repository.session.refresh.return_value = None

        # 模拟审计日志对象
        mock_log = Mock()
        mock_log.id = str(uuid.uuid4())
        audit_repository.session.refresh.return_value = mock_log

        # 创建各种类型的审计日志
        actions = ["login", "register", "upgrade", "token_refresh", "logout"]
        results = []

        for action in actions:
            result = audit_repository.create_log(
                user_id=sample_user_uuid,
                action=action,
                result="success",
                details=f"Test {action} operation"
            )
            results.append(result)

        # 验证所有操作都被记录
        assert len(results) == len(actions)
        # 验证数据库操作被正确调用
        assert audit_repository.session.add.call_count == len(actions)
        assert audit_repository.session.commit.call_count == len(actions)

    def test_uuid_edge_cases(self, auth_repository, audit_repository):
        """测试UUID的边界情况"""
        # 测试各种边界UUID值
        edge_case_uuids = [
            uuid.uuid4(),
            uuid.UUID(int=0),  # 最小UUID
            uuid.UUID(int=2**128 - 1),  # 最大UUID
            uuid.uuid5(uuid.NAMESPACE_DNS, "example.com"),  # UUID5
        ]

        for test_uuid in edge_case_uuids:
            # 测试AuthRepository
            mock_result = Mock()
            mock_result.id = str(test_uuid)
            auth_repository.session.exec.return_value.first.return_value = mock_result

            result = auth_repository.get_by_id(test_uuid)
            assert result is not None

            # 测试AuditRepository
            audit_result = audit_repository.create_log(
                user_id=test_uuid,
                action="edge_case_test",
                result="success"
            )
            assert audit_result is not None

    @pytest.mark.integration
    def test_uuid_consistency_across_repositories(self, auth_repository, audit_repository):
        """集成测试：确保Repository之间的UUID处理一致性"""
        test_uuid = uuid.uuid4()
        test_uuid_str = str(test_uuid)

        # 模拟用户创建
        mock_user = Mock()
        mock_user.id = test_uuid_str
        auth_repository.session.exec.return_value.first.return_value = mock_user

        # 模拟审计日志创建
        mock_log = Mock()
        mock_log.id = str(uuid.uuid4())
        audit_repository.session.refresh.return_value = mock_log

        # 执行操作序列
        user = auth_repository.get_by_id(test_uuid)
        audit_log = audit_repository.create_log(
            user_id=test_uuid,
            action="integration_test",
            result="success"
        )

        # 验证UUID一致性
        assert user is not None
        assert audit_log is not None
        # 用户ID应该在整个流程中保持一致
        # (在Repository层转换为字符串，但在数据库中是一致的)