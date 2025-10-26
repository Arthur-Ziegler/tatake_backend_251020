"""
User领域UUID架构测试

测试UserService、UserRepository和User Router的UUID类型安全实现。
确保所有组件正确使用UUID参数，实现完整的UUID类型转换。

作者：TaKeKe团队
版本：2.0.0 - UUID架构统一版
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlmodel import Session

from src.domains.user.service import UserService
from src.domains.user.repository import UserRepository
from src.domains.user.schemas import UpdateProfileRequest
from src.domains.auth.models import Auth
from src.domains.points.service import PointsService
from src.domains.reward.welcome_gift_service import WelcomeGiftService


class TestUserRepositoryUUID:
    """UserRepository UUID转换测试类"""

    def test_get_by_id_uuid_conversion(self, user_repository: UserRepository):
        """测试get_by_id方法的UUID转换逻辑"""
        # Arrange
        user_id = uuid4()
        # 创建用户数据
        user = Auth(
            id=str(user_id),
            wechat_openid="test_openid",
            is_guest=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        user_repository.session.add(user)
        user_repository.session.commit()

        # Act - 使用UUID参数查询
        result = user_repository.get_by_id(user_id)

        # Assert
        assert result is not None
        assert result.id == str(user_id)  # 存储为字符串
        assert result.wechat_openid == "test_openid"

    def test_get_by_id_invalid_uuid(self, user_repository: UserRepository):
        """测试get_by_id方法处理无效UUID"""
        # Arrange - 使用不存在的UUID
        user_id = uuid4()

        # Act
        result = user_repository.get_by_id(user_id)

        # Assert
        assert result is None

    def test_create_guest_user_uuid(self, user_repository: UserRepository):
        """测试创建游客用户的UUID处理"""
        # Act
        result = user_repository.create_guest_user()

        # Assert
        assert result is not None
        assert result.is_guest is True
        assert isinstance(result.id, str)
        # 验证可以转换为有效的UUID
        UUID(result.id)  # 如果无效会抛出异常

    def test_create_wechat_user_uuid(self, user_repository: UserRepository):
        """测试创建微信用户的UUID处理"""
        # Arrange
        wechat_openid = "test_wechat_openid"
        nickname = "测试用户"

        # Act
        result = user_repository.create_wechat_user(wechat_openid, nickname)

        # Assert
        assert result is not None
        assert result.is_guest is False
        assert result.wechat_openid == wechat_openid
        assert isinstance(result.id, str)

    def test_upgrade_guest_to_wechat_uuid(self, user_repository: UserRepository):
        """测试升级游客用户的UUID转换"""
        # Arrange
        guest_user = user_repository.create_guest_user()
        guest_id = UUID(guest_user.id)
        wechat_openid = "upgrade_wechat_openid"

        # Act
        result = user_repository.upgrade_guest_to_wechat(guest_id, wechat_openid)

        # Assert
        assert result is True

        # 验证升级结果
        updated_user = user_repository.get_by_id(guest_id)
        assert updated_user is not None
        assert updated_user.is_guest is False
        assert updated_user.wechat_openid == wechat_openid

    def test_update_last_login_uuid(self, user_repository: UserRepository):
        """测试更新最后登录时间的UUID处理"""
        # Arrange
        user = user_repository.create_wechat_user("test_openid")
        user_id = UUID(user.id)

        # Act
        result = user_repository.update_last_login(user_id)

        # Assert
        assert result is True

        # 验证更新结果
        updated_user = user_repository.get_by_id(user_id)
        assert updated_user is not None
        assert updated_user.last_login_at is not None

    def test_user_exists_uuid(self, user_repository: UserRepository):
        """测试用户存在性检查的UUID处理"""
        # Arrange
        user = user_repository.create_wechat_user("exists_test_openid")
        user_id = UUID(user.id)

        # Act & Assert
        assert user_repository.user_exists(user_id) is True

        # 测试不存在的用户
        non_existent_id = uuid4()
        assert user_repository.user_exists(non_existent_id) is False

    def test_get_user_count_uuid(self, user_repository: UserRepository):
        """测试获取用户总数的UUID兼容性"""
        # Arrange
        initial_count = user_repository.get_user_count()

        # Act - 创建用户
        user_repository.create_wechat_user("count_test_openid")
        user_repository.create_guest_user()

        # Assert
        final_count = user_repository.get_user_count()
        assert final_count == initial_count + 2


class TestUserServiceUUID:
    """UserService UUID类型安全测试类"""

    def test_get_user_profile_uuid_parameters(self, user_service: UserService):
        """测试get_user_profile方法使用UUID参数"""
        # Arrange
        user_id = uuid4()
        # 注意：这个测试需要用户存在，实际使用中应该先创建用户

        # Act & Assert - 验证UUID类型检查
        with pytest.raises(ValueError):
            user_service.get_user_profile("invalid-uuid-string")

        with pytest.raises(ValueError):
            user_service.get_user_profile(123456)

        # 有效UUID应该不会抛出类型错误（可能会抛出业务错误）
        try:
            result = user_service.get_user_profile(user_id)
            # 用户不存在是正常的业务错误
            assert result["success"] is False
            assert result["code"] == 404
        except ValueError:
            pytest.fail("有效UUID不应该抛出ValueError")

    def test_update_user_profile_uuid_parameters(self, user_service: UserService):
        """测试update_user_profile方法使用UUID参数"""
        # Arrange
        user_id = uuid4()
        request = UpdateProfileRequest(nickname="新昵称")

        # Act & Assert - 验证UUID类型检查
        with pytest.raises(ValueError):
            user_service.update_user_profile("invalid-uuid-string", request)

        with pytest.raises(ValueError):
            user_service.update_user_profile(123456, request)

        # 有效UUID测试
        try:
            result = user_service.update_user_profile(user_id, request)
            # 用户不存在是正常的业务错误
            assert result["success"] is False
            assert result["code"] == 404
        except ValueError:
            pytest.fail("有效UUID不应该抛出ValueError")

    def test_claim_welcome_gift_uuid_parameters(self, user_service: UserService,
                                                  points_service: PointsService,
                                                  welcome_gift_service: WelcomeGiftService):
        """测试claim_welcome_gift方法使用UUID参数"""
        # Arrange
        user_id = uuid4()

        # Act & Assert - 验证UUID类型检查
        with pytest.raises(ValueError):
            user_service.claim_welcome_gift("invalid-uuid-string", points_service, welcome_gift_service)

        with pytest.raises(ValueError):
            user_service.claim_welcome_gift(123456, points_service, welcome_gift_service)

        # 有效UUID测试
        try:
            result = user_service.claim_welcome_gift(user_id, points_service, welcome_gift_service)
            # 用户不存在是正常的业务错误
            assert result["success"] is False
            assert result["code"] == 404
        except ValueError:
            pytest.fail("有效UUID不应该抛出ValueError")

    def test_get_welcome_gift_history_uuid_parameters(self, user_service: UserService,
                                                      points_service: PointsService,
                                                      welcome_gift_service: WelcomeGiftService):
        """测试get_welcome_gift_history方法使用UUID参数"""
        # Arrange
        user_id = uuid4()

        # Act & Assert - 验证UUID类型检查
        with pytest.raises(ValueError):
            user_service.get_welcome_gift_history("invalid-uuid-string", points_service, welcome_gift_service)

        with pytest.raises(ValueError):
            user_service.get_welcome_gift_history(123456, points_service, welcome_gift_service)

        # 有效UUID测试
        try:
            result = user_service.get_welcome_gift_history(user_id, points_service, welcome_gift_service)
            # 用户不存在是正常的业务错误
            assert result["success"] is False
            assert result["code"] == 404
        except ValueError:
            pytest.fail("有效UUID不应该抛出ValueError")

    def test_create_guest_user_uuid_type_safety(self, user_service: UserService):
        """测试create_guest_user方法的类型安全性"""
        # Act
        result = user_service.create_guest_user()

        # Assert
        assert result["success"] is True
        assert "data" in result
        assert "id" in result["data"]
        # 验证返回的ID是有效的UUID字符串
        UUID(result["data"]["id"])

    def test_user_exists_uuid_validation(self, user_service: UserService):
        """测试user_exists方法的UUID验证"""
        # Arrange
        user_id = uuid4()

        # Act & Assert - 验证UUID类型检查
        with pytest.raises(ValueError):
            user_service.user_exists("invalid-uuid-string")

        with pytest.raises(ValueError):
            user_service.user_exists(123456)

        # 有效UUID测试
        result = user_service.user_exists(user_id)
        assert isinstance(result, bool)


class TestUserUUIDIntegration:
    """User领域UUID集成测试类"""

    def test_jwt_to_uuid_conversion_flow(self, session: Session):
        """测试JWT到UUID的转换流程"""
        # Arrange
        user_repo = UserRepository(session)
        user_service = UserService(user_repo)

        # 创建用户
        user = user_repo.create_wechat_user("jwt_test_openid", "测试用户")
        user_id = UUID(user.id)

        # Act & Assert - 模拟JWT解析后的UUID传递
        profile_result = user_service.get_user_profile(user_id)
        exists_result = user_service.user_exists(user_id)

        assert profile_result["success"] is False  # 没有实现完整业务逻辑
        assert profile_result["code"] == 404  # 但UUID类型检查通过

        assert exists_result is True  # 用户存在检查通过

    def test_cross_domain_uuid_passing(self, session: Session):
        """测试跨领域UUID传递"""
        # Arrange
        user_repo = UserRepository(session)
        user_service = UserService(user_repo)

        # 创建用户
        user = user_repo.create_wechat_user("cross_domain_test", "跨领域用户")
        user_id = UUID(user.id)

        # Act - 在不同方法间传递UUID
        exists = user_service.user_exists(user_id)
        profile = user_service.get_user_profile(user_id)

        # Assert - UUID在所有方法间正确传递
        assert isinstance(user_id, UUID)
        assert exists is True
        assert profile["success"] is False  # 业务逻辑问题，不是UUID问题
        assert profile["code"] == 404

    def test_uuid_format_validation_error_response(self, user_service: UserService):
        """测试UUID格式验证的错误响应"""
        # Arrange
        invalid_uuids = [
            "invalid-uuid",
            "123-456-789",
            "",
            "short-uuid",
            123456,
            {"id": "not-uuid"}
        ]

        # Act & Assert - 所有无效UUID都应该返回400错误
        for invalid_uuid in invalid_uuids:
            result = user_service.get_user_profile(invalid_uuid)
            assert result["success"] is False
            assert result["code"] == 400
            assert "UUID" in result["error"] or "类型" in result["error"]

    def test_uuid_to_string_conversion_consistency(self, user_repository: UserRepository):
        """测试UUID到字符串转换的一致性"""
        # Arrange
        user = user_repository.create_wechat_user("consistency_test", "一致性测试")
        user_id = UUID(user.id)

        # Act
        retrieved_user = user_repository.get_by_id(user_id)
        exists = user_repository.user_exists(user_id)

        # Assert - UUID在所有操作中保持一致
        assert retrieved_user is not None
        assert retrieved_user.id == str(user_id)  # 存储为字符串
        assert exists is True

        # 验证可以重新转换为UUID
        converted_back = UUID(retrieved_user.id)
        assert converted_back == user_id