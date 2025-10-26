"""
UUID架构集成测试

测试新的UUID架构（服务层UUID + 数据层转换）的完整性和正确性。
这个测试套件确保整个系统在类型转换方面的一致性。

测试覆盖：
1. Repository层UUID转换
2. Service层UUID处理
3. 端到端API流程
4. 数据一致性验证
5. 错误处理机制
"""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from sqlmodel import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domains.auth.models import Auth, AuthLog
from src.domains.auth.repository import AuthRepository, AuditRepository
from src.core.uuid_converter import UUIDConverter
from src.database import get_db_session


class TestUUIDConverterIntegration:
    """UUID转换器集成测试"""

    def test_uuid_string_roundtrip_conversion(self):
        """测试UUID对象和字符串的双向转换"""
        # 生成UUID对象
        original_uuid = uuid4()

        # 转换为字符串
        uuid_str = UUIDConverter.to_string(original_uuid)
        assert isinstance(uuid_str, str)
        assert len(uuid_str) == 36
        assert UUIDConverter.is_valid_uuid_string(uuid_str)

        # 转换回UUID对象
        converted_uuid = UUIDConverter.to_uuid(uuid_str)
        assert isinstance(converted_uuid, UUID)
        assert converted_uuid == original_uuid

    def test_batch_uuid_conversion(self):
        """测试批量UUID转换"""
        # 创建UUID对象列表
        uuid_objects = [uuid4() for _ in range(5)]

        # 批量转换为字符串
        uuid_strings = UUIDConverter.batch_to_string(uuid_objects)
        assert len(uuid_strings) == 5
        assert all(isinstance(s, str) for s in uuid_strings)
        assert all(UUIDConverter.is_valid_uuid_string(s) for s in uuid_strings)

        # 批量转换回UUID对象
        converted_objects = UUIDConverter.batch_to_uuid(uuid_strings)
        assert len(converted_objects) == 5
        assert all(isinstance(u, UUID) for u in converted_objects)
        assert converted_objects == uuid_objects

    def test_uuid_converter_error_handling(self):
        """测试UUID转换器的错误处理"""
        # 测试无效UUID字符串
        with pytest.raises(ValueError):
            UUIDConverter.to_uuid("invalid-uuid-string")

        # 测试无效类型
        with pytest.raises(TypeError):
            UUIDConverter.to_string(12345)

        # 测试安全转换
        result = UUIDConverter.safe_to_string("invalid-uuid", default="fallback")
        assert result == "fallback"

        result = UUIDConverter.safe_to_uuid("invalid-uuid", default=None)
        assert result is None


class TestAuthRepositoryUUIDIntegration:
    """Auth Repository UUID集成测试"""

    @pytest.fixture(scope="function")
    def test_db_session(self):
        """测试数据库会话"""
        # 创建内存数据库
        engine = create_engine("sqlite:///:memory:", echo=False)

        # 创建表
        Auth.metadata.create_all(engine)
        AuthLog.metadata.create_all(engine)

        # 创建会话
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()

    def test_repository_create_user_with_uuid(self, test_db_session):
        """测试Repository使用UUID创建用户"""
        auth_repo = AuthRepository(test_db_session)

        # 生成UUID对象
        user_uuid = uuid4()

        # 创建用户（传入UUID对象）
        user = auth_repo.create_user(
            user_id=user_uuid,
            wechat_openid="test_openid_123",
            is_guest=False
        )

        # 验证用户创建成功
        assert user is not None
        assert user.id == str(user_uuid)  # 数据库中存储为字符串
        assert user.wechat_openid == "test_openid_123"
        assert user.is_guest is False

    def test_repository_get_user_by_uuid(self, test_db_session):
        """测试Repository使用UUID获取用户"""
        auth_repo = AuthRepository(test_db_session)

        # 先创建用户
        user_uuid = uuid4()
        created_user = auth_repo.create_user(
            user_id=user_uuid,
            wechat_openid="test_openid_456",
            is_guest=True
        )

        # 使用UUID对象查询用户
        found_user = auth_repo.get_by_id(user_uuid)

        # 验证查询结果
        assert found_user is not None
        assert found_user.id == str(user_uuid)
        assert found_user.wechat_openid == "test_openid_456"
        assert found_user.is_guest is True

    def test_repository_user_not_found(self, test_db_session):
        """测试Repository查询不存在的用户"""
        auth_repo = AuthRepository(test_db_session)

        # 使用不存在的UUID查询
        non_existent_uuid = uuid4()
        found_user = auth_repo.get_by_id(non_existent_uuid)

        # 验证返回None
        assert found_user is None

    def test_repository_upgrade_guest_account(self, test_db_session):
        """测试Repository升级游客账号"""
        auth_repo = AuthRepository(test_db_session)

        # 创建游客用户
        guest_uuid = uuid4()
        guest_user = auth_repo.create_user(
            user_id=guest_uuid,
            wechat_openid=None,
            is_guest=True
        )

        # 升级为正式用户
        upgraded_user = auth_repo.upgrade_guest_account(
            user_id=guest_uuid,
            wechat_openid="wechat_upgraded_123"
        )

        # 验证升级结果
        assert upgraded_user is not None
        assert upgraded_user.is_guest is False
        assert upgraded_user.wechat_openid == "wechat_upgraded_123"

    def test_audit_repository_uuid_handling(self, test_db_session):
        """测试Audit Repository的UUID处理"""
        audit_repo = AuditRepository(test_db_session)

        # 创建用户
        auth_repo = AuthRepository(test_db_session)
        user_uuid = uuid4()
        user = auth_repo.create_user(
            user_id=user_uuid,
            wechat_openid="test_audit_user",
            is_guest=False
        )

        # 创建审计日志（传入UUID对象）
        audit_log = audit_repo.create_log(
            user_id=user_uuid,
            action="test_login",
            result="success",
            details="Test audit log",
            ip_address="127.0.0.1"
        )

        # 验证审计日志创建成功
        assert audit_log is not None
        assert audit_log.user_id == str(user_uuid)  # 数据库中存储为字符串
        assert audit_log.action == "test_login"
        assert audit_log.result == "success"

    def test_audit_repository_null_user_id(self, test_db_session):
        """测试Audit Repository处理NULL用户ID"""
        audit_repo = AuditRepository(test_db_session)

        # 创建游客操作日志（user_id为None）
        audit_log = audit_repo.create_log(
            user_id=None,  # 游客操作
            action="guest_init",
            result="success",
            details="Guest user initialization"
        )

        # 验证审计日志创建成功
        assert audit_log is not None
        assert audit_log.user_id is None
        assert audit_log.action == "guest_init"


class TestEndToEndUUIDFlow:
    """端到端UUID流程测试"""

    @pytest.fixture(scope="function")
    def test_db_session(self):
        """测试数据库会话"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Auth.metadata.create_all(engine)
        AuthLog.metadata.create_all(engine)

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()

    def test_complete_user_lifecycle_with_uuid(self, test_db_session):
        """测试完整的用户生命周期（使用UUID）"""
        auth_repo = AuthRepository(test_db_session)
        audit_repo = AuditRepository(test_db_session)

        # 1. 创建游客用户
        guest_uuid = uuid4()
        audit_repo.create_log(
            user_id=None,
            action="guest_init",
            result="success",
            details="Guest initialization"
        )

        guest_user = auth_repo.create_user(
            user_id=guest_uuid,
            wechat_openid=None,
            is_guest=True
        )

        # 验证游客创建
        assert guest_user is not None
        assert guest_user.is_guest is True

        # 2. 记录登录
        audit_repo.create_log(
            user_id=guest_uuid,
            action="login",
            result="success",
            details="Guest login"
        )

        # 3. 升级为正式用户
        wechat_openid = "wechat_upgrade_test"
        upgraded_user = auth_repo.upgrade_guest_account(
            user_id=guest_uuid,
            wechat_openid=wechat_openid
        )

        # 验证升级结果
        assert upgraded_user is not None
        assert upgraded_user.is_guest is False
        assert upgraded_user.wechat_openid == wechat_openid

        # 4. 记录升级操作
        audit_repo.create_log(
            user_id=guest_uuid,
            action="upgrade",
            result="success",
            details="Upgraded to registered user"
        )

        # 5. 更新最后登录时间
        login_updated = auth_repo.update_last_login(guest_uuid)
        assert login_updated is True

        # 6. 验证用户查询
        final_user = auth_repo.get_by_id(guest_uuid)
        assert final_user is not None
        assert final_user.is_guest is False
        assert final_user.wechat_openid == wechat_openid
        assert final_user.last_login_at is not None

    def test_uuid_consistency_across_layers(self, test_db_session):
        """测试UUID在各层之间的一致性"""
        auth_repo = AuthRepository(test_db_session)

        # 生成UUID对象
        original_uuid = uuid4()

        # Service层使用UUID对象
        service_layer_uuid = original_uuid

        # Repository层转换为字符串存储
        created_user = auth_repo.create_user(
            user_id=service_layer_uuid,
            wechat_openid="consistency_test",
            is_guest=False
        )

        # 验证数据库中存储的是字符串
        assert isinstance(created_user.id, str)
        assert created_user.id == str(original_uuid)

        # Repository层查询时转换回UUID对象（通过get_by_id方法的内部转换）
        found_user = auth_repo.get_by_id(service_layer_uuid)

        # 验证数据一致性
        assert found_user.id == str(original_uuid)
        assert found_user.wechat_openid == "consistency_test"

        # 验证原始UUID对象仍然有效
        assert service_layer_uuid == original_uuid

    def test_error_handling_in_uuid_operations(self, test_db_session):
        """测试UUID操作中的错误处理"""
        auth_repo = AuthRepository(test_db_session)

        # 测试查找不存在的用户
        non_existent_uuid = uuid4()
        result = auth_repo.get_by_id(non_existent_uuid)
        assert result is None

        # 测试升级不存在的用户
        upgrade_result = auth_repo.upgrade_guest_account(
            user_id=non_existent_uuid,
            wechat_openid="test_upgrade"
        )
        assert upgrade_result is None

        # 测试更新不存在用户的登录时间
        update_result = auth_repo.update_last_login(non_existent_uuid)
        assert update_result is False


class TestDatabaseConsistency:
    """数据库一致性测试"""

    @pytest.fixture(scope="function")
    def test_db_session(self):
        """测试数据库会话"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Auth.metadata.create_all(engine)
        AuthLog.metadata.create_all(engine)

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        try:
            yield session
        finally:
            session.close()

    def test_uuid_storage_format_in_database(self, test_db_session):
        """测试UUID在数据库中的存储格式"""
        auth_repo = AuthRepository(test_db_session)

        # 创建用户
        user_uuid = uuid4()
        user = auth_repo.create_user(
            user_id=user_uuid,
            wechat_openid="storage_test",
            is_guest=False
        )

        # 直接查询数据库验证存储格式
        from sqlmodel import select
        statement = select(Auth).where(Auth.id == str(user_uuid))
        db_result = test_db_session.exec(statement).first()

        # 验证数据库中存储的是字符串
        assert isinstance(db_result.id, str)
        assert db_result.id == str(user_uuid)

        # 验证字符串格式符合UUID标准
        assert UUIDConverter.is_valid_uuid_string(db_result.id)

    def test_multiple_users_uuid_uniqueness(self, test_db_session):
        """测试多个用户UUID的唯一性"""
        auth_repo = AuthRepository(test_db_session)

        # 创建多个用户
        user_uuids = [uuid4() for _ in range(5)]
        created_users = []

        for i, user_uuid in enumerate(user_uuids):
            user = auth_repo.create_user(
                user_id=user_uuid,
                wechat_openid=f"user_{i}",
                is_guest=False
            )
            created_users.append(user)

        # 验证所有用户都有唯一的ID
        stored_ids = [user.id for user in created_users]
        assert len(set(stored_ids)) == len(stored_ids)  # 确保没有重复

        # 验证每个UUID都能正确查询
        for i, user_uuid in enumerate(user_uuids):
            found_user = auth_repo.get_by_id(user_uuid)
            assert found_user is not None
            assert found_user.wechat_openid == f"user_{i}"