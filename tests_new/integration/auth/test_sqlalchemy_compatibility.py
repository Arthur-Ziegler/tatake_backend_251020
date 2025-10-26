"""
SQLAlchemy版本兼容性测试

测试认证系统与不同SQLAlchemy版本的兼容性，确保：
1. Session API正确使用
2. 数据库操作正常工作
3. 查询语法兼容性
4. 事务处理正确

作者：TaTakeKe团队
版本：2.0.0 - 认证系统测试基础设施
"""

import pytest
from sqlmodel import select, Session
from sqlalchemy import text
from uuid import uuid4
from datetime import datetime, timezone

# 使用绝对导入
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from tests.integration.auth.conftest import (
    auth_repository,
    test_db_session,
    test_data_factory,
    sample_auth_user,
    sample_guest_user
)

# 创建TestDataFactory
class TestDataFactory:
    """测试数据工厂"""
    pass


@pytest.mark.integration
@pytest.mark.auth
class TestSQLAlchemyCompatibility:
    """SQLAlchemy版本兼容性测试"""

    def test_session_api_compatibility(self, test_db_session: Session):
        """
        测试Session API兼容性

        Args:
            test_db_session: 测试数据库会话
        """
        # 测试execute方法可用性
        stmt = select(text("1"))
        result = test_db_session.execute(stmt).first()
        assert result is not None
        assert result[0] == 1

        # 测试commit和rollback方法
        test_db_session.commit()
        test_db_session.rollback()  # 应该不会出错

    def test_repository_session_compatibility(self, auth_repository):
        """
        测试Repository层Session兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 测试用户ID类型处理
        user_id = uuid4()

        # 创建用户应该成功
        user = auth_repository.create_user(
            user_id=user_id,
            wechat_openid="test-openid",
            is_guest=True
        )

        assert user.id == str(user_id)
        assert user.is_guest is True
        assert user.wechat_openid == "test-openid"

        # 测试查询用户
        found_user = auth_repository.get_by_id(user_id)
        assert found_user is not None
        assert found_user.id == str(user_id)
        assert found_user.is_guest is True

    def test_select_statement_compatibility(self, auth_repository):
        """
        测试SELECT语句兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 创建测试用户
        user_id = uuid4()
        user = auth_repository.create_user(
            user_id=user_id,
            wechat_openid="test-openid",
            is_guest=False
        )

        # 测试SELECT查询
        from src.domains.auth.models import Auth

        stmt = select(Auth).where(Auth.id == str(user_id))
        row_result = auth_repository.session.execute(stmt).first()

        assert row_result is not None
        result = row_result[0]  # 从Row对象中提取Auth实体
        assert result.id == str(user_id)
        assert result.is_guest is False

    def test_text_statement_compatibility(self, test_db_session: Session):
        """
        测试原始SQL语句兼容性

        Args:
            test_db_session: 测试数据库会话
        """
        # 测试表结构查询
        result = test_db_session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='auth'"
        )).first()

        assert result is not None
        assert "auth" in result[0]

        # 测试计数查询
        count_result = test_db_session.execute(text(
            "SELECT COUNT(*) FROM auth"
        )).scalar()

        assert isinstance(count_result, int)
        assert count_result >= 0

    def test_transaction_compatibility(self, auth_repository):
        """
        测试事务处理兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        user_id = uuid4()

        # 测试成功的事务
        user = auth_repository.create_user(
            user_id=user_id,
            wechat_openid="transaction-test",
            is_guest=True
        )

        # 验证数据已提交
        found_user = auth_repository.get_by_id(user_id)
        assert found_user is not None
        assert found_user.wechat_openid == "transaction-test"

        # 测试失败的事务回滚
        user_id_2 = uuid4()

        try:
            # 创建用户
            auth_repository.create_user(
                user_id=user_id_2,
                wechat_openid="rollback-test",
                is_guest=False
            )

            # 手动触发回滚
            auth_repository.session.rollback()

            # 验证数据已回滚
            found_user_2 = auth_repository.get_by_id(user_id_2)
            assert found_user_2 is None

        except Exception as e:
            auth_repository.session.rollback()
            raise

    def test_session_lifecycle_compatibility(self, test_db_session: Session):
        """
        测试会话生命周期兼容性

        Args:
            test_db_session: 测试数据库会话
        """
        # 测试会话状态
        assert not test_db_session.in_transaction()

        # 开始事务
        test_db_session.begin()
        assert test_db_session.in_transaction()

        # 执行查询
        test_db_session.execute(text("SELECT 1"))

        # 提交事务
        test_db_session.commit()
        assert not test_db_session.in_transaction()

    def test_datetime_field_compatibility(self, auth_repository):
        """
        测试日期时间字段兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        user_id = uuid4()
        current_time = datetime.now(timezone.utc)

        # 创建用户
        user = auth_repository.create_user(
            user_id=user_id,
            wechat_openid="datetime-test",
            is_guest=True
        )

        # 更新登录时间
        auth_repository.update_last_login(user_id, current_time)

        # 验证时间字段
        found_user = auth_repository.get_by_id(user_id)
        assert found_user is not None
        assert found_user.last_login_at is not None
        assert isinstance(found_user.last_login_at, datetime)

    def test_boolean_field_compatibility(self, auth_repository):
        """
        测试布尔字段兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 测试游客用户
        guest_id = uuid4()
        guest = auth_repository.create_user(
            user_id=guest_id,
            wechat_openid=None,
            is_guest=True
        )
        assert guest.is_guest is True

        # 测试正式用户
        regular_id = uuid4()
        regular = auth_repository.create_user(
            user_id=regular_id,
            wechat_openid="regular-test",
            is_guest=False
        )
        assert regular.is_guest is False

        # 测试查询过滤
        from src.domains.auth.models import Auth

        stmt = select(Auth).where(Auth.is_guest == True)
        guest_row_results = auth_repository.session.execute(stmt).all()

        # 从Row对象列表中提取Auth实体列表
        guest_results = [row[0] for row in guest_row_results]

        assert len(guest_results) >= 1
        assert all(user.is_guest for user in guest_results)

    def test_unique_constraint_compatibility(self, auth_repository):
        """
        测试唯一性约束兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        openid = "unique-test-openid"

        # 创建第一个用户
        user1_id = uuid4()
        user1 = auth_repository.create_user(
            user_id=user1_id,
            wechat_openid=openid,
            is_guest=False
        )
        assert user1.wechat_openid == openid

        # 尝试创建第二个相同openid的用户（应该失败）
        user2_id = uuid4()
        with pytest.raises(Exception):
            auth_repository.create_user(
                user_id=user2_id,
                wechat_openid=openid,
                is_guest=False
            )

    def test_index_compatibility(self, auth_repository):
        """
        测试索引兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 创建测试数据
        users = []
        for i in range(5):
            user_id = uuid4()
            user = auth_repository.create_user(
                user_id=user_id,
                wechat_openid=f"index-test-{i}",
                is_guest=i % 2 == 0
            )
            users.append(user)

        # 测试微信OpenID索引查询
        from src.domains.auth.models import Auth

        stmt = select(Auth).where(Auth.wechat_openid == "index-test-2")
        row_result = auth_repository.session.execute(stmt).first()
        assert row_result is not None
        result = row_result[0]  # 从Row对象中提取Auth实体
        assert result.wechat_openid == "index-test-2"

        # 测试游客状态索引查询
        stmt = select(Auth).where(Auth.is_guest == True)
        guest_row_results = auth_repository.session.execute(stmt).all()
        guest_results = [row[0] for row in guest_row_results]  # 提取Auth实体列表
        assert len(guest_results) >= 2
        assert all(user.is_guest for user in guest_results)


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.boundary
class TestSQLAlchemyBoundaryConditions:
    """SQLAlchemy边界条件测试"""

    def test_empty_database_compatibility(self, auth_repository):
        """
        测试空数据库兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 查询不存在的用户
        non_existent_id = uuid4()
        result = auth_repository.get_by_id(non_existent_id)
        assert result is None

        # 查询不存在的微信OpenID
        result = auth_repository.get_by_wechat_openid("non-existent-openid")
        assert result is None

        # 统计空数据库
        from src.domains.auth.models import Auth
        stmt = select(Auth)
        results = auth_repository.session.execute(stmt).all()
        assert len(results) == 0

    def test_large_data_compatibility(self, auth_repository):
        """
        测试大数据量兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 批量创建用户
        user_count = 100
        users = []

        for i in range(user_count):
            user_id = uuid4()
            user = auth_repository.create_user(
                user_id=user_id,
                wechat_openid=f"bulk-test-{i}",
                is_guest=i % 2 == 0
            )
            users.append(user)

        # 验证所有用户都被创建
        assert len(users) == user_count

        # 测试分页查询（如果有实现）
        from src.domains.auth.models import Auth
        stmt = select(Auth).limit(10)
        page_results = auth_repository.session.execute(stmt).all()
        assert len(page_results) == 10

        # 测试计数查询
        count_stmt = select(Auth)
        total_count = len(auth_repository.session.execute(count_stmt).all())
        assert total_count == user_count

    def test_special_characters_compatibility(self, auth_repository):
        """
        测试特殊字符兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 测试包含特殊字符的微信OpenID
        special_openids = [
            "test-with-dashes",
            "test_with_underscores",
            "test.with.dots",
            "测试中文字符",
            "test@special#chars",
            "test space"
        ]

        for openid in special_openids:
            user_id = uuid4()
            user = auth_repository.create_user(
                user_id=user_id,
                wechat_openid=openid,
                is_guest=False
            )

            # 验证可以正确查询
            found_user = auth_repository.get_by_wechat_openid(openid)
            assert found_user is not None
            assert found_user.wechat_openid == openid

    def test_null_values_compatibility(self, auth_repository):
        """
        测试NULL值兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 创建游客用户（微信OpenID为NULL）
        guest_id = uuid4()
        guest_user = auth_repository.create_user(
            user_id=guest_id,
            wechat_openid=None,
            is_guest=True
        )

        # 验证NULL值处理
        assert guest_user.wechat_openid is None

        # 查询NULL值
        from src.domains.auth.models import Auth
        stmt = select(Auth).where(Auth.wechat_openid.is_(None))
        null_row_results = auth_repository.session.execute(stmt).all()
        null_results = [row[0] for row in null_row_results]  # 提取Auth实体列表

        assert len(null_results) >= 1
        assert all(user.wechat_openid is None for user in null_results)

    def test_extreme_values_compatibility(self, auth_repository):
        """
        测试极值兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        # 测试长字符串
        long_openid = "a" * 100
        user_id = uuid4()
        user = auth_repository.create_user(
            user_id=user_id,
            wechat_openid=long_openid,
            is_guest=False
        )

        found_user = auth_repository.get_by_wechat_openid(long_openid)
        assert found_user is not None
        assert found_user.wechat_openid == long_openid

        # 测试空字符串
        empty_openid = ""
        try:
            user_id_2 = uuid4()
            user_2 = auth_repository.create_user(
                user_id=user_id_2,
                wechat_openid=empty_openid,
                is_guest=False
            )
        except Exception:
            # 某些数据库可能不允许空字符串作为唯一约束
            pass

    def test_concurrent_operations_compatibility(self, auth_repository):
        """
        测试并发操作兼容性

        Args:
            auth_repository: 认证Repository实例
        """
        import threading
        import time

        results = []
        errors = []

        def worker_task(worker_id: int):
            try:
                for i in range(5):
                    user_id = uuid4()
                    user = auth_repository.create_user(
                        user_id=user_id,
                        wechat_openid=f"concurrent-{worker_id}-{i}",
                        is_guest=i % 2 == 0
                    )
                    results.append((worker_id, user.id))

                    # 添加小延迟模拟真实场景
                    time.sleep(0.001)

            except Exception as e:
                errors.append((worker_id, str(e)))

        # 创建多个工作线程
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=worker_task, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发操作出现错误: {errors}"
        assert len(results) == 15  # 3个线程 × 5个操作