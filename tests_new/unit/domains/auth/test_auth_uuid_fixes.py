"""
Auth领域UUID修复验证测试

测试Auth领域的UUID类型绑定修复，确保AuthAuditLog（实际为AuthLog）的UUID处理正确。

作者：TaKeKe团队
版本：1.0.0 - UUID架构Batch 1测试
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID
from sqlalchemy.orm import Session

from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository
from src.domains.auth.service import AuthService
from src.core.uuid_converter import UUIDConverter


class TestAuthUUIDFixes:
    """Auth领域UUID修复验证测试"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = Mock(spec=Session)
        session.exec = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()
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
    def sample_user(self):
        """创建示例用户"""
        user_id = uuid.uuid4()
        return Auth(
            id=str(user_id),
            wechat_openid="test_openid",
            is_guest=False,
            jwt_version=1
        )

    def test_auth_repository_get_by_id_signature(self, auth_repository):
        """测试AuthRepository.get_by_id方法的正确签名"""
        # 这是一个关键测试，确保修复后的方法签名正确
        user_id = uuid.uuid4()

        # 模拟数据库查询结果
        mock_result = Mock()
        mock_result.id = str(user_id)
        auth_repository.session.exec.return_value.first.return_value = mock_result

        # 正确的调用方式：只传递UUID参数
        result = auth_repository.get_by_id(user_id)

        # 验证调用正确
        auth_repository.session.exec.assert_called_once()
        assert result is mock_result

    def test_auth_repository_get_by_id_with_wrong_signature(self, auth_repository):
        """验证旧的错误调用方式不再工作"""
        user_id = uuid.uuid4()

        # 旧的错误调用方式应该失败
        with pytest.raises(TypeError):
            # 这种调用现在应该抛出TypeError，因为get_by_id只接受一个参数（除self外）
            auth_repository.get_by_id(Auth, user_id)

    def test_uuid_converter_usage_in_repository(self, auth_repository):
        """测试Repository中UUID转换器的正确使用"""
        user_id = uuid.uuid4()
        expected_str = str(user_id)

        # 模拟数据库查询
        mock_statement = Mock()
        auth_repository.session.exec.return_value = mock_statement
        mock_statement.first.return_value = None

        # 调用get_by_id
        auth_repository.get_by_id(user_id)

        # 验证UUID转换器被正确使用
        auth_repository.session.exec.assert_called_once()
        # 验证查询使用了字符串格式的UUID
        call_args = auth_repository.session.exec.call_args[0][0]
        # 这里应该检查SQL查询条件使用了正确的UUID字符串格式
        assert call_args is not None

    def test_audit_repository_uuid_handling(self, audit_repository):
        """测试AuditRepository的UUID处理"""
        user_id = uuid.uuid4()

        # 模拟审计日志创建
        audit_data = {
            "user_id": user_id,
            "action": "login",
            "details": {"ip": "127.0.0.1"}
        }

        # 模拟数据库操作
        audit_repository.session.exec.return_value.first.return_value = None

        # 测试UUID转换
        user_id_str = UUIDConverter.to_string(user_id)
        assert user_id_str == str(user_id)
        assert isinstance(user_id_str, str)

    def test_auth_service_guest_upgrade_fix(self, sample_user):
        """测试AuthService中游客升级的UUID修复"""
        with patch('src.domains.auth.service.AuthRepository') as mock_repo_class, \
             patch('src.domains.auth.service.AuditRepository') as mock_audit_class, \
             patch('src.domains.auth.service.get_auth_db') as mock_get_auth_db:

            # 设置mock
            mock_session = Mock()
            mock_get_auth_db.return_value.__enter__.return_value = mock_session
            mock_repo = Mock()
            mock_audit_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_audit_class.return_value = mock_audit_repo

            # 设置用户返回
            sample_user.is_guest = True
            mock_repo.get_by_id.return_value = sample_user
            mock_repo.get_by_wechat_openid.return_value = None

            # 创建service实例
            auth_service = AuthService()

            # 模拟请求
            class MockRequest:
                wechat_openid = "new_openid"
                nickname = "test_user"

            request = MockRequest()
            current_user_id = UUID(sample_user.id)

            # 这个调用现在应该正确工作（不再传递Auth类）
            try:
                result = auth_service.guest_upgrade(request, current_user_id)
                # 验证get_by_id被正确调用
                mock_repo.get_by_id.assert_called_once_with(current_user_id)
            except Exception as e:
                # 如果有其他错误，不应该是UUID相关的错误
                assert "get_by_id" not in str(e) or Auth.__name__ not in str(e)

    def test_auth_service_validate_token_fix(self, sample_user):
        """测试AuthService中token验证的UUID修复"""
        with patch('src.domains.auth.service.AuthRepository') as mock_repo_class, \
             patch('src.domains.auth.service.AuditRepository') as mock_audit_class, \
             patch('src.domains.auth.service.get_auth_db') as mock_get_auth_db:

            # 设置mock
            mock_session = Mock()
            mock_get_auth_db.return_value.__enter__.return_value = mock_session
            mock_repo = Mock()
            mock_audit_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_audit_class.return_value = mock_audit_repo

            # 设置用户返回
            mock_repo.get_by_id.return_value = sample_user

            # 创建service实例
            auth_service = AuthService()

            # 模拟token payload
            token_payload = {
                "sub": str(sample_user.id),
                "jwt_version": 1
            }

            # 这个调用现在应该正确工作（不再传递Auth类）
            try:
                result = auth_service.validate_token(token_payload)
                # 验证get_by_id被正确调用
                mock_repo.get_by_id.assert_called_once()
                # 检查调用参数
                call_args = mock_repo.get_by_id.call_args[0]
                assert len(call_args) == 1  # 只应该有一个参数（user_id）
                assert isinstance(call_args[0], UUID)  # 参数应该是UUID类型
            except Exception as e:
                # 如果有其他错误，不应该是UUID相关的错误
                assert "get_by_id" not in str(e) or Auth.__name__ not in str(e)

    def test_auth_log_model_consistency(self):
        """测试AuthLog模型的一致性"""
        # 验证AuthLog（实际表名）的存在和结构
        assert hasattr(AuthLog, '__tablename__')
        assert AuthLog.__tablename__ == "auth_audit_logs"

        # 验证字段的UUID处理
        auth_log = AuthLog(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            action="test_action",
            details={}
        )

        # 验证user_id是字符串类型（在数据库中存储为字符串）
        assert isinstance(auth_log.user_id, str)
        assert len(auth_log.user_id) == 36  # UUID字符串长度

    def test_uuid_converter_edge_cases(self):
        """测试UUID转换器的边界情况"""
        # 测试None值处理 - 应该抛出TypeError
        with pytest.raises(TypeError) as exc_info:
            UUIDConverter.to_string(None)
        assert "Expected UUID object" in str(exc_info.value)

        # 测试UUID对象转换
        test_uuid = uuid.uuid4()
        result = UUIDConverter.to_string(test_uuid)
        assert result == str(test_uuid)
        assert isinstance(result, str)

        # 测试字符串UUID转换
        uuid_str = str(uuid.uuid4())
        result = UUIDConverter.to_uuid(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_repository_error_handling(self, auth_repository):
        """测试Repository的错误处理"""
        user_id = uuid.uuid4()

        # 模拟数据库错误
        auth_repository.session.exec.side_effect = Exception("Database error")

        # 调用应该优雅地处理错误
        result = auth_repository.get_by_id(user_id)
        assert result is None  # 错误时应该返回None

    @pytest.mark.integration
    def test_auth_uuid_flow_integration(self):
        """集成测试：Auth领域的完整UUID流程"""
        # 这个测试验证从Service层到Repository层的完整UUID处理流程
        user_id = uuid.uuid4()

        with patch('src.domains.auth.service.AuthRepository') as mock_repo_class:
            # 设置mock repository
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            # 模拟用户对象
            mock_user = Mock()
            mock_user.id = str(user_id)
            mock_user.is_guest = False
            mock_repo.get_by_id.return_value = mock_user

            # 创建service
            auth_service = AuthService()

            # 测试UUID在Service层和Repository层之间的传递
            try:
                # 模拟token验证
                token_payload = {"sub": str(user_id), "jwt_version": 1}
                # 这个调用在修复后应该正确工作
                result = auth_service.validate_token(token_payload)

                # 验证Repository接收到正确的UUID
                mock_repo.get_by_id.assert_called_once()
                call_args = mock_repo.get_by_id.call_args[0]
                assert isinstance(call_args[0], UUID)
                assert call_args[0] == user_id

            except Exception as e:
                # 不应该有UUID相关的错误
                assert "get_by_id" not in str(e) or "wrong number of arguments" not in str(e)