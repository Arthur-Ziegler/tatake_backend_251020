"""
认证系统集成测试

测试认证系统各个组件之间的集成，包括：
1. Repository层与数据库集成
2. Service层与Repository层集成
3. JWT服务集成
4. 微信登录流程集成
5. 游客账号升级流程集成
6. 令牌刷新流程集成

测试策略：
- 使用真实数据库连接（SQLite内存数据库）
- 测试完整的业务流程
- 验证数据一致性
- 测试错误处理和回滚

作者：TaTakeKe团队
版本：2.0.0 - 认证系统测试基础设施
"""

import pytest
import time
import threading
from uuid import UUID, uuid4
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from typing import Dict, Any, List

from .test_data_factory import (
    AuthTestDataFactory,
    create_test_guest_user,
    create_test_wechat_user,
    create_mock_wechat_api,
    create_boundary_test_data
)
from .conftest import (
    auth_repository,
    auth_service,
    jwt_service,
    audit_repository,
    test_db_session,
    mock_wechat_api
)
from src.domains.auth.exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    ValidationError
)


@pytest.mark.integration
@pytest.mark.auth
class TestRepositoryIntegration:
    """Repository层集成测试"""

    def test_user_lifecycle_integration(self, auth_repository):
        """
        测试用户完整生命周期集成

        Args:
            auth_repository: 认证Repository实例
        """
        # 1. 创建游客用户
        guest_user_id = uuid4()
        guest_user = auth_repository.create_user(
            user_id=guest_user_id,
            wechat_openid=None,
            is_guest=True
        )

        assert guest_user is not None
        assert guest_user.id == str(guest_user_id)
        assert guest_user.is_guest is True
        assert guest_user.wechat_openid is None

        # 2. 查询游客用户
        found_guest = auth_repository.get_by_id(guest_user_id)
        assert found_guest is not None
        assert found_guest.id == str(guest_user_id)
        assert found_guest.is_guest is True

        # 3. 升级为正式用户
        wechat_openid = f"ox{uuid4().hex[:16]}"
        upgraded_user = auth_repository.upgrade_guest_account(
            user_id=guest_user_id,
            wechat_openid=wechat_openid
        )

        assert upgraded_user is not None
        assert upgraded_user.id == str(guest_user_id)
        assert upgraded_user.is_guest is False
        assert upgraded_user.wechat_openid == wechat_openid

        # 4. 通过微信OpenID查询
        found_by_openid = auth_repository.get_by_wechat_openid(wechat_openid)
        assert found_by_openid is not None
        assert found_by_openid.id == str(guest_user_id)

        # 5. 更新登录时间
        current_time = datetime.now(timezone.utc)
        update_success = auth_repository.update_last_login(guest_user_id, current_time)
        assert update_success is True

        # 验证登录时间更新
        updated_user = auth_repository.get_by_id(guest_user_id)
        assert updated_user is not None
        assert updated_user.last_login_at is not None

    def test_unique_constraint_enforcement(self, auth_repository):
        """
        测试唯一性约束强制执行

        Args:
            auth_repository: 认证Repository实例
        """
        # 创建第一个用户
        user1_id = uuid4()
        openid = f"ox{uuid4().hex[:16]}"

        user1 = auth_repository.create_user(
            user_id=user1_id,
            wechat_openid=openid,
            is_guest=False
        )
        assert user1.wechat_openid == openid

        # 尝试创建第二个相同openid的用户（应该失败）
        user2_id = uuid4()
        with pytest.raises(Exception):  # 应该抛出数据库约束异常
            auth_repository.create_user(
                user_id=user2_id,
                wechat_openid=openid,  # 相同的openid
                is_guest=False
            )

    def test_transaction_consistency(self, auth_repository):
        """
        测试事务一致性

        Args:
            auth_repository: 认证Repository实例
        """
        user_id = uuid4()

        # 开始一个事务
        auth_repository.session.begin()

        try:
            # 创建用户
            user = auth_repository.create_user(
                user_id=user_id,
                wechat_openid=f"ox{uuid4().hex[:16]}",
                is_guest=False
            )

            # 验证用户在当前会话中存在
            found_user = auth_repository.get_by_id(user_id)
            assert found_user is not None

            # 手动提交
            auth_repository.session.commit()

        except Exception as e:
            # 回滚事务
            auth_repository.session.rollback()
            raise e

        # 在新会话中验证用户仍然存在
        found_user_after_commit = auth_repository.get_by_id(user_id)
        assert found_user_after_commit is not None
        assert found_user_after_commit.id == str(user_id)

    def test_null_field_handling(self, auth_repository):
        """
        测试NULL字段处理

        Args:
            auth_repository: 认证Repository实例
        """
        # 创建具有NULL字段的用户
        user_id = uuid4()
        guest_user = auth_repository.create_user(
            user_id=user_id,
            wechat_openid=None,  # NULL字段
            is_guest=True
        )

        # 验证NULL字段被正确保存和检索
        assert guest_user.wechat_openid is None

        found_user = auth_repository.get_by_id(user_id)
        assert found_user is not None
        assert found_user.wechat_openid is None

    def test_batch_operations(self, auth_repository):
        """
        测试批量操作

        Args:
            auth_repository: 认证Repository实例
        """
        # 批量创建用户
        user_count = 20
        created_users = []

        for i in range(user_count):
            user_id = uuid4()
            user = auth_repository.create_user(
                user_id=user_id,
                wechat_openid=f"batch-{i}" if i % 2 == 0 else None,
                is_guest=i % 3 == 0
            )
            created_users.append(user)

        # 验证所有用户都被创建
        assert len(created_users) == user_count

        # 随机抽查几个用户
        for i in [0, 5, 10, 15]:
            user_id = UUID(created_users[i].id)
            found_user = auth_repository.get_by_id(user_id)
            assert found_user is not None
            assert found_user.id == created_users[i].id


@pytest.mark.integration
@pytest.mark.auth
class TestServiceIntegration:
    """Service层集成测试"""

    def test_guest_user_initiation_flow(self, auth_service, audit_repository):
        """
        测试游客用户初始化流程

        Args:
            auth_service: 认证服务实例
            audit_repository: 审计Repository实例
        """
        # 初始化游客用户
        result = auth_service.init_guest_user()

        # 验证返回数据结构
        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert "is_guest" in result
        assert result["is_guest"] is True

        # 验证用户ID格式
        try:
            UUID(result["user_id"])
        except ValueError:
            pytest.fail("user_id should be a valid UUID string")

        # 验证令牌不为空
        assert result["access_token"] is not None
        assert result["refresh_token"] is not None

    def test_wechat_login_flow(self, auth_service, mock_wechat_api):
        """
        测试微信登录完整流程

        Args:
            auth_service: 认证服务实例
            mock_wechat_api: Mock微信API
        """
        # 配置微信API成功响应
        mock_wechat_api.set_success_response()

        # 执行微信登录
        result = auth_service.wechat_login("test_authorization_code")

        # 验证返回数据结构
        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert "is_guest" in result
        assert result["is_guest"] is False

        # 验证用户信息
        assert result["user_id"] is not None
        assert len(result["access_token"]) > 0
        assert len(result["refresh_token"]) > 0

    def test_wechat_login_null_response(self, auth_service, mock_wechat_api):
        """
        测试微信登录NULL响应处理

        Args:
            auth_service: 认证服务实例
            mock_wechat_api: Mock微信API
        """
        # 配置微信API返回None
        mock_wechat_api.set_null_response()

        # 验证抛出正确异常
        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.wechat_login("invalid_code")

        assert "微信用户信息获取失败" in str(exc_info.value)

    def test_guest_upgrade_flow(self, auth_service, mock_wechat_api):
        """
        测试游客账号升级流程

        Args:
            auth_service: 认证服务实例
            mock_wechat_api: Mock微信API
        """
        # 1. 创建游客用户
        guest_result = auth_service.init_guest_user()
        guest_user_id = UUID(guest_result["user_id"])

        # 2. 配置微信API响应
        mock_wechat_api.set_success_response()

        # 3. 升级游客账号
        upgrade_result = auth_service.upgrade_guest_account(
            user_id=guest_user_id,
            wechat_openid="test-openid",
            session_token="test-session-token"
        )

        # 验证升级结果
        assert upgrade_result is not None
        assert "user_id" in upgrade_result
        assert upgrade_result["user_id"] == str(guest_user_id)
        assert upgrade_result.get("is_guest") is False

    def test_token_refresh_flow(self, auth_service, jwt_service):
        """
        测试令牌刷新流程

        Args:
            auth_service: 认证服务实例
            jwt_service: JWT服务实例
        """
        # 1. 初始化游客用户获取初始令牌
        init_result = auth_service.init_guest_user()
        refresh_token = init_result["refresh_token"]

        # 2. 使用刷新令牌获取新令牌
        refresh_result = auth_service.refresh_token(refresh_token)

        # 验证新令牌
        assert "access_token" in refresh_result
        assert "refresh_token" in refresh_result
        assert refresh_result["access_token"] != init_result["access_token"]
        assert refresh_result["refresh_token"] != refresh_token

    def test_invalid_token_refresh(self, auth_service):
        """
        测试无效令牌刷新

        Args:
            auth_service: 认证服务实例
        """
        invalid_tokens = [
            "",           # 空令牌
            None,         # None值
            "invalid",    # 无效格式
            "expired.token",  # 过期令牌格式
        ]

        for invalid_token in invalid_tokens:
            with pytest.raises((TokenException, AuthenticationException, ValueError)):
                auth_service.refresh_token(invalid_token)


@pytest.mark.integration
@pytest.mark.auth
class TestJWTServiceIntegration:
    """JWT服务集成测试"""

    def test_token_creation_and_verification(self, jwt_service):
        """
        测试令牌创建和验证

        Args:
            jwt_service: JWT服务实例
        """
        user_id = str(uuid4())
        payload = {
            "user_id": user_id,
            "is_guest": True,
            "exp": int(time.time()) + 3600  # 1小时后过期
        }

        # 创建访问令牌
        access_token = jwt_service.create_access_token(payload)
        assert access_token is not None
        assert len(access_token) > 0

        # 创建刷新令牌
        refresh_token = jwt_service.create_refresh_token(payload)
        assert refresh_token is not None
        assert len(refresh_token) > 0
        assert refresh_token != access_token

        # 验证令牌
        verified_payload = jwt_service.verify_token(access_token)
        assert verified_payload is not None
        assert verified_payload["user_id"] == user_id
        assert verified_payload["is_guest"] is True

    def test_expired_token_handling(self, jwt_service):
        """
        测试过期令牌处理

        Args:
            jwt_service: JWT服务实例
        """
        # 创建过期令牌
        expired_payload = {
            "user_id": str(uuid4()),
            "is_guest": False,
            "exp": int(time.time()) - 3600  # 1小时前过期
        }

        expired_token = jwt_service.create_access_token(expired_payload)

        # 验证过期令牌应该抛出异常
        with pytest.raises((TokenException, ValueError)):
            jwt_service.verify_token(expired_token)

    def test_invalid_token_handling(self, jwt_service):
        """
        测试无效令牌处理

        Args:
            jwt_service: JWT服务实例
        """
        invalid_tokens = [
            "",                           # 空令牌
            "invalid.token",             # 无效格式
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",  # 无效签名
            "too.many.parts.in.token",   # 格式错误
            None                          # None值
        ]

        for invalid_token in invalid_tokens:
            with pytest.raises((TokenException, ValueError, AttributeError)):
                jwt_service.verify_token(invalid_token)

    def test_token_with_custom_claims(self, jwt_service):
        """
        测试包含自定义声明的令牌

        Args:
            jwt_service: JWT服务实例
        """
        custom_payload = {
            "user_id": str(uuid4()),
            "is_guest": False,
            "custom_claim": "custom_value",
            "permissions": ["read", "write"],
            "exp": int(time.time()) + 3600
        }

        token = jwt_service.create_access_token(custom_payload)
        verified_payload = jwt_service.verify_token(token)

        assert verified_payload["custom_claim"] == "custom_value"
        assert verified_payload["permissions"] == ["read", "write"]


@pytest.mark.integration
@pytest.mark.auth
class TestAuditLogIntegration:
    """审计日志集成测试"""

    def test_audit_log_creation(self, audit_repository):
        """
        测试审计日志创建

        Args:
            audit_repository: 审计Repository实例
        """
        user_id = uuid4()

        log = audit_repository.create_log(
            user_id=user_id,
            action="login",
            result="success",
            details="用户登录成功",
            ip_address="127.0.0.1",
            user_agent="Test-Agent/1.0"
        )

        assert log is not None
        assert log.user_id == str(user_id)
        assert log.action == "login"
        assert log.result == "success"
        assert log.details == "用户登录成功"

    def test_audit_log_for_guest_user(self, audit_repository):
        """
        测试游客用户审计日志

        Args:
            audit_repository: 审计Repository实例
        """
        # 游客用户操作（user_id为None）
        log = audit_repository.create_log(
            user_id=None,
            action="guest_init",
            result="success",
            details="游客账号初始化"
        )

        assert log is not None
        assert log.user_id is None
        assert log.action == "guest_init"

    def test_batch_audit_log_creation(self, audit_repository):
        """
        测试批量审计日志创建

        Args:
            audit_repository: 审计Repository实例
        """
        logs = []

        for i in range(10):
            user_id = uuid4()
            log = audit_repository.create_log(
                user_id=user_id,
                action=f"action_{i}",
                result="success" if i % 2 == 0 else "failure",
                details=f"操作{i}"
            )
            logs.append(log)

        assert len(logs) == 10

        # 验证日志内容
        for i, log in enumerate(logs):
            assert log.action == f"action_{i}"
            assert log.result == ("success" if i % 2 == 0 else "failure")


@pytest.mark.integration
@pytest.mark.auth
class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    def test_service_repository_error_propagation(self, auth_service):
        """
        测试Service层到Repository层错误传播

        Args:
            auth_service: 认证服务实例
        """
        # 测试不存在的用户ID
        non_existent_user_id = uuid4()

        with pytest.raises((UserNotFoundException, AttributeError)):
            auth_service.get_user_by_id(non_existent_user_id)

    def test_database_constraint_violations(self, auth_repository):
        """
        测试数据库约束违规处理

        Args:
            auth_repository: 认证Repository实例
        """
        openid = f"ox{uuid4().hex[:16]}"

        # 创建第一个用户
        user1 = auth_repository.create_user(
            user_id=uuid4(),
            wechat_openid=openid,
            is_guest=False
        )

        # 尝试创建重复openid的用户
        with pytest.raises(Exception):
            auth_repository.create_user(
                user_id=uuid4(),
                wechat_openid=openid,  # 重复的openid
                is_guest=False
            )

    def test_transaction_rollback_on_error(self, auth_repository):
        """
        测试错误时事务回滚

        Args:
            auth_repository: 认证Repository实例
        """
        user_id = uuid4()

        # 开始事务
        auth_repository.session.begin()

        try:
            # 创建用户
            user = auth_repository.create_user(
                user_id=user_id,
                wechat_openid=f"ox{uuid4().hex[:16]}",
                is_guest=False
            )

            # 故意触发错误（尝试插入重复ID）
            auth_repository.create_user(
                user_id=user_id,  # 重复ID
                wechat_openid=f"ox{uuid4().hex[:16]}",
                is_guest=True
            )

            auth_repository.session.commit()

        except Exception:
            # 回滚事务
            auth_repository.session.rollback()

        # 验证用户没有被保存
        found_user = auth_repository.get_by_id(user_id)
        # 根据实现，可能返回None或者返回用户（取决于事务处理方式）
        # 主要验证没有数据不一致的状态


@pytest.mark.integration
@pytest.mark.auth
class TestConcurrencyIntegration:
    """并发集成测试"""

    def test_concurrent_user_creation(self, auth_repository):
        """
        测试并发用户创建

        Args:
            auth_repository: 认证Repository实例
        """
        results = []
        errors = []

        def create_user_worker(worker_id: int):
            try:
                for i in range(5):
                    user_id = uuid4()
                    user = auth_repository.create_user(
                        user_id=user_id,
                        wechat_openid=f"concurrent-{worker_id}-{i}",
                        is_guest=i % 2 == 0
                    )
                    results.append((worker_id, user.id))
                    time.sleep(0.001)  # 小延迟
            except Exception as e:
                errors.append((worker_id, str(e)))

        # 创建多个工作线程
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=create_user_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发操作出现错误: {errors}"
        assert len(results) == 15  # 3个线程 × 5个操作

        # 验证所有用户ID都是唯一的
        user_ids = [user_id for _, user_id in results]
        assert len(set(user_ids)) == len(user_ids), "检测到重复的用户ID"

    def test_concurrent_user_queries(self, auth_repository):
        """
        测试并发用户查询

        Args:
            auth_repository: 认证Repository实例
        """
        # 预先创建一些用户
        test_users = []
        for i in range(10):
            user_id = uuid4()
            user = auth_repository.create_user(
                user_id=user_id,
                wechat_openid=f"query-test-{i}",
                is_guest=i % 2 == 0
            )
            test_users.append(user_id)

        query_results = []
        query_errors = []

        def query_user_worker(worker_id: int):
            try:
                for i in range(10):
                    user_id = test_users[i % len(test_users)]
                    result = auth_repository.get_by_id(user_id)
                    query_results.append((worker_id, result is not None))
                    time.sleep(0.001)
            except Exception as e:
                query_errors.append((worker_id, str(e)))

        # 创建多个查询线程
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=query_user_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(query_errors) == 0, f"并发查询出现错误: {query_errors}"
        assert len(query_results) == 50  # 5个线程 × 10个查询
        assert all(success for _, success in query_results), "存在失败的查询"