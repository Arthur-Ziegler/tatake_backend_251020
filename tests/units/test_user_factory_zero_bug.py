"""
零Bug测试体系 - 用户工厂单元测试

测试用户数据工厂的正确性、唯一性和数据一致性。

这是零Bug测试体系的示例测试，展示了如何编写标准化、
可维护的单元测试。

测试原则：
1. AAA模式：Arrange-Act-Assert
2. 数据隔离：每个测试独立运行
3. 确定性：相同输入产生相同输出
4. 完整覆盖：测试所有关键功能
"""

import pytest
from datetime import datetime, timezone

from tests.factories.users import UserFactory, AuthLogFactory, UserFactoryManager
from tests.conftest_zero_bug import ZeroBugTestConfig


class TestUserFactory:
    """用户工厂测试类"""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_user_with_default_data(self, test_helper):
        """
        测试：使用默认数据创建用户

        期望：
        - 用户数据包含所有必需字段
        - 字段值类型正确
        - 时间戳为当前时间
        """
        # Arrange - 准备阶段
        expected_fields = ["wechat_openid", "username", "email", "is_guest", "is_active"]

        # Act - 执行阶段
        start_time = datetime.now(timezone.utc)
        user_data = UserFactory.create()

        # Assert - 断言阶段
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        # 验证必填字段
        for field in expected_fields:
            assert field in user_data, f"用户数据应包含字段: {field}"
            assert user_data[field] is not None, f"字段 {field} 不应为空"

        # 验证数据类型
        assert isinstance(user_data["wechat_openid"], str)
        assert isinstance(user_data["username"], str)
        assert isinstance(user_data["email"], str)
        assert isinstance(user_data["is_guest"], bool)
        assert isinstance(user_data["is_active"], bool)

        # 验证时间戳
        assert isinstance(user_data["created_at"], datetime)
        assert isinstance(user_data["updated_at"], datetime)
        assert user_data["created_at"] >= start_time

    @pytest.mark.unit
    def test_create_user_with_overrides(self, test_helper):
        """
        测试：使用覆盖数据创建用户

        期望：
        - 覆盖字段生效
        - 默认字段保持默认值
        - 数据验证通过
        """
        # Arrange
        overrides = {
            "username": "custom_user",
            "email": "custom@test.com",
            "is_vip": True,
            "level": 5
        }

        # Act
        start_time = datetime.now(timezone.utc)
        user_data = UserFactory.create(**overrides)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        # 验证覆盖字段
        assert user_data["username"] == "custom_user"
        assert user_data["email"] == "custom@test.com"
        assert user_data["is_vip"] is True
        assert user_data["level"] == 5

        # 验证默认字段仍然存在
        assert user_data["wechat_openid"] is not None
        assert user_data["is_guest"] is False

    @pytest.mark.unit
    def test_create_guest_user(self, test_helper):
        """
        测试：创建游客用户

        期望：
        - is_guest为True
        - is_verified为False
        - is_vip为False
        - level为0
        """
        # Act
        start_time = datetime.now(timezone.utc)
        guest_user = UserFactory.create_guest()

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert guest_user["is_guest"] is True
        assert guest_user["is_verified"] is False
        assert guest_user["is_vip"] is False
        assert guest_user["level"] == 0

    @pytest.mark.unit
    def test_create_registered_user(self, test_helper):
        """
        测试：创建注册用户

        期望：
        - is_guest为False
        - is_verified为True
        - is_active为True
        - level大于等于1
        - points大于等于0
        """
        # Act
        start_time = datetime.now(timezone.utc)
        registered_user = UserFactory.create_registered()

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert registered_user["is_guest"] is False
        assert registered_user["is_verified"] is True
        assert registered_user["is_active"] is True
        assert registered_user["level"] >= 1
        assert registered_user["points"] >= 0

    @pytest.mark.unit
    def test_create_vip_user(self, test_helper):
        """
        测试：创建VIP用户

        期望：
        - is_vip为True
        - level大于等于5
        - points大于等于500
        """
        # Act
        start_time = datetime.now(timezone.utc)
        vip_user = UserFactory.create_vip()

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert vip_user["is_vip"] is True
        assert vip_user["level"] >= 5
        assert vip_user["points"] >= 500

    @pytest.mark.unit
    def test_create_user_uniqueness(self, test_helper):
        """
        测试：用户数据的唯一性

        期望：
        - 多次创建的用户数据唯一
        - wechat_openid唯一
        - username唯一
        """
        # Act
        start_time = datetime.now(timezone.utc)
        users = UserFactory.create_batch(5)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        # 提取唯一字段
        openids = [user["wechat_openid"] for user in users]
        usernames = [user["username"] for user in users]

        # 验证唯一性
        assert len(set(openids)) == len(openids), "wechat_openid应唯一"
        assert len(set(usernames)) == len(usernames), "username应唯一"

    @pytest.mark.unit
    def test_create_user_with_points(self, test_helper):
        """
        测试：创建带指定积分的用户

        期望：
        - points为指定值
        - total_points_earned为指定值
        """
        # Arrange
        test_points = 888

        # Act
        start_time = datetime.now(timezone.utc)
        user = UserFactory.create_with_points(test_points)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert user["points"] == test_points
        assert user["total_points_earned"] == test_points

    @pytest.mark.unit
    def test_create_batch_with_levels(self, test_helper):
        """
        测试：创建不同等级的用户批次

        期望：
        - 创建指定数量的用户
        - 用户等级在1-10之间
        - 积分与等级匹配
        """
        # Arrange
        batch_size = 20

        # Act
        start_time = datetime.now(timezone.utc)
        users = UserFactory.create_batch_with_levels(batch_size)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)
        assert len(users) == batch_size

        for user in users:
            assert 1 <= user["level"] <= 10
            assert user["points"] == user["level"] * 100
            assert user["total_points_earned"] == user["points"]

    @pytest.mark.unit
    def test_user_data_validation(self, test_helper):
        """
        测试：用户数据验证

        期望：
        - 缺少必填字段时抛出异常
        - 数据格式正确时验证通过
        """
        # 测试缺少必填字段
        with pytest.raises(ValueError, match="必填字段"):
            incomplete_data = {"username": "test"}
            UserFactory.validate_data(incomplete_data)

        # 测试完整数据验证通过
        complete_data = UserFactory.create()
        assert UserFactory.validate_data(complete_data) is True

    @pytest.mark.unit
    def test_factory_schema(self, test_helper):
        """
        测试：工厂模式信息

        期望：
        - 返回正确的模式信息
        - 包含默认数据和配置
        """
        # Act
        start_time = datetime.now(timezone.utc)
        schema = UserFactory.get_schema()

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert "defaults" in schema
        assert "model_class" in schema
        assert "auto_unique" in schema
        assert "required_fields" in schema

        assert schema["auto_unique"] is True
        assert "wechat_openid" in schema["required_fields"]


class TestAuthLogFactory:
    """认证日志工厂测试类"""

    @pytest.mark.unit
    def test_create_auth_log_with_defaults(self, test_helper):
        """
        测试：创建默认认证日志
        """
        # Act
        start_time = datetime.now(timezone.utc)
        auth_log = AuthLogFactory.create()

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        required_fields = ["user_id", "action", "ip_address", "created_at"]
        for field in required_fields:
            assert field in auth_log
            assert auth_log[field] is not None

    @pytest.mark.unit
    def test_create_login_log(self, test_helper):
        """
        测试：创建登录日志
        """
        # Arrange
        user_id = "test_user_123"

        # Act
        start_time = datetime.now(timezone.utc)
        login_log = AuthLogFactory.create_login_log(user_id, success=True)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert login_log["user_id"] == user_id
        assert login_log["action"] == "login"
        assert login_log["success"] is True

    @pytest.mark.unit
    def test_create_batch_for_user(self, test_helper):
        """
        测试：为用户创建批量认证日志
        """
        # Arrange
        user_id = "test_user_456"
        log_count = 5

        # Act
        start_time = datetime.now(timezone.utc)
        logs = AuthLogFactory.create_batch_for_user(user_id, log_count)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert len(logs) == log_count
        for log in logs:
            assert log["user_id"] == user_id


class TestUserFactoryManager:
    """用户工厂管理器测试类"""

    @pytest.mark.unit
    def test_create_user_hierarchy(self, test_helper):
        """
        测试：创建用户层级
        """
        # Act
        start_time = datetime.now(timezone.utc)
        hierarchy = UserFactoryManager.create_user_hierarchy()

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert "guest" in hierarchy
        assert "regular" in hierarchy
        assert "vip" in hierarchy

        assert hierarchy["guest"]["is_guest"] is True
        assert hierarchy["regular"]["is_guest"] is False
        assert hierarchy["vip"]["is_vip"] is True

    @pytest.mark.unit
    def test_create_user_with_auth_history(self, test_helper):
        """
        测试：创建带认证历史的用户
        """
        # Act
        start_time = datetime.now(timezone.utc)
        user_with_history = UserFactoryManager.create_user_with_auth_history(num_logs=5)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert "user" in user_with_history
        assert "auth_logs" in user_with_history
        assert len(user_with_history["auth_logs"]) == 5

        # 验证日志属于该用户
        for log in user_with_history["auth_logs"]:
            assert log["user_id"] == user_with_history["user"]["wechat_openid"]

    @pytest.mark.unit
    def test_create_realistic_user_community(self, test_helper):
        """
        测试：创建真实用户社区
        """
        # Arrange
        community_size = 50

        # Act
        start_time = datetime.now(timezone.utc)
        community = UserFactoryManager.create_realistic_user_community(community_size)

        # Assert
        test_helper.assert_performance(start_time, ZeroBugTestConfig.MAX_TEST_TIME)

        assert len(community) == community_size

        # 统计用户类型
        guest_count = sum(1 for user in community if user["is_guest"])
        vip_count = sum(1 for user in community if user.get("is_vip"))
        registered_count = sum(1 for user in community if not user["is_guest"])

        # 验证用户分布（大致符合预期比例）
        assert vip_count > 0
        assert guest_count > 0
        assert registered_count > 0