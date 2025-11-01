"""
增强用户Profile功能性能测试

测试增强Profile API的响应时间和数据库查询性能，
验证新功能不会显著影响系统性能。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.api.main import app
from src.domains.user.models import User, UserSettings, UserStats
from src.api.dependencies import get_current_user_id
from src.domains.user.repository import UserRepository


class TestEnhancedProfilePerformance:
    """增强用户Profile功能性能测试类"""

    @pytest.fixture
    def mock_user_id(self):
        """模拟用户ID fixture"""
        return uuid4()

    @pytest.fixture
    def authenticated_client(self, mock_user_id):
        """已认证的测试客户端fixture"""
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def performance_user_data(self, mock_user_id):
        """性能测试用户数据fixture"""
        return {
            "user_id": mock_user_id,
            "nickname": "性能测试用户",
            "avatar_url": "https://example.com/performance-avatar.jpg",
            "bio": "这是一个用于性能测试的用户简介",
            "gender": "female",
            "birthday": "1985-08-20",
            "theme": "dark",
            "language": "en-US"
        }

    def test_enhanced_profile_get_response_time(self, authenticated_client, mock_user_id):
        """
        测试增强Profile GET API响应时间

        Given: 模拟用户数据和认证客户端
        When: 多次调用GET /user/profile/enhanced
        Then: 响应时间应该在可接受范围内
        """
        # Mock数据库操作
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "性能测试用户"
        mock_user.avatar_url = "https://example.com/performance-avatar.jpg"
        mock_user.bio = "性能测试用户简介"
        mock_user.gender = "female"
        mock_user.birthday = "1985-08-20"
        mock_user.is_active = True
        mock_user.created_at = "2025-01-01T00:00:00Z"

        mock_settings = Mock()
        mock_settings.theme = "dark"
        mock_settings.language = "en-US"

        mock_stats = Mock()
        mock_stats.tasks_completed = 25
        mock_stats.total_points = 1250
        mock_stats.login_count = 12
        mock_stats.last_active_at = "2025-01-01T00:00:00Z"

        # Mock依赖
        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo_class.return_value = mock_repo

            mock_session = Mock()
            mock_session.exec.return_value.first.return_value = mock_settings

            with patch('src.database.get_db_session', return_value=mock_session):
                with patch('src.services.rewards_integration_service.get_rewards_service') as mock_rewards:
                    mock_rewards_service = AsyncMock()
                    mock_rewards_service.get_user_balance.return_value = 1000
                    mock_rewards.return_value = mock_rewards_service

                    # 执行多次请求测试响应时间
                    response_times = []
                    request_count = 20

                    for i in range(request_count):
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile/enhanced")
                        end_time = time.time()

                        # 只计算成功请求的响应时间
                        if response.status_code == 200:
                            response_times.append((end_time - start_time) * 1000)  # 转换为毫秒

                    # 性能断言
                    assert len(response_times) == request_count, f"所有{request_count}个请求都应该成功"

                    avg_response_time = statistics.mean(response_times)
                    max_response_time = max(response_times)
                    min_response_time = min(response_times)

                    # 响应时间应该在合理范围内
                    assert avg_response_time < 500, f"平均响应时间应小于500ms，实际: {avg_response_time:.2f}ms"
                    assert max_response_time < 1000, f"最大响应时间应小于1000ms，实际: {max_response_time:.2f}ms"
                    assert min_response_time < 200, f"最小响应时间应小于200ms，实际: {min_response_time:.2f}ms"

                    # 打印性能统计
                    print(f"增强Profile GET性能统计:")
                    print(f"  平均响应时间: {avg_response_time:.2f}ms")
                    print(f"  最大响应时间: {max_response_time:.2f}ms")
                    print(f"  最小响应时间: {min_response_time:.2f}ms")
                    print(f"  请求次数: {len(response_times)}")

    def test_enhanced_profile_put_response_time(self, authenticated_client, mock_user_id, performance_user_data):
        """
        测试增强Profile PUT API响应时间

        Given: 模拟用户数据和认证客户端
        When: 多次调用PUT /user/profile/enhanced
        Then: 响应时间应该在可接受范围内
        """
        # Mock数据库操作
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "性能测试用户"
        mock_user.is_active = True

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo.update_user.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            mock_session = Mock()
            mock_session.exec.return_value.first.return_value = Mock()
            mock_session.commit.return_value = None
            mock_session.rollback.return_value = None

            with patch('src.database.get_db_session', return_value=mock_session):
                # 执行多次更新请求测试响应时间
                response_times = []
                request_count = 15

                update_data = {
                    "nickname": "更新后的性能测试用户",
                    "gender": "male",
                    "theme": "light",
                    "language": "zh-CN"
                }

                for i in range(request_count):
                    start_time = time.time()
                    response = authenticated_client.put("/user/profile/enhanced", json=update_data)
                    end_time = time.time()

                    # 只计算成功请求的响应时间
                    if response.status_code == 200:
                        response_times.append((end_time - start_time) * 1000)  # 转换为毫秒

                # 性能断言
                assert len(response_times) == request_count, f"所有{request_count}个请求都应该成功"

                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)

                # 更新操作的响应时间阈值稍高
                assert avg_response_time < 800, f"平均响应时间应小于800ms，实际: {avg_response_time:.2f}ms"
                assert max_response_time < 1500, f"最大响应时间应小于1500ms，实际: {max_response_time:.2f}ms"
                assert min_response_time < 300, f"最小响应时间应小于300ms，实际: {min_response_time:.2f}ms"

                # 打印性能统计
                print(f"增强Profile PUT性能统计:")
                print(f"  平均响应时间: {avg_response_time:.2f}ms")
                print(f"  最大响应时间: {max_response_time:.2f}ms")
                print(f"  最小响应时间: {min_response_time:.2f}ms")
                print(f"  请求次数: {len(response_times)}")

    def test_concurrent_requests_performance(self, authenticated_client, mock_user_id):
        """
        测试并发请求性能

        Given: 模拟用户数据和认证客户端
        When: 并发调用增强Profile API
        Then: 并发请求的响应时间应该保持稳定
        """
        import threading
        import queue

        # Mock数据库操作
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "并发测试用户"
        mock_user.is_active = True

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo_class.return_value = mock_repo

            mock_session = Mock()
            mock_session.exec.return_value.first.return_value = Mock()

            with patch('src.database.get_db_session', return_value=mock_session):
                with patch('src.services.rewards_integration_service.get_rewards_service') as mock_rewards:
                    mock_rewards_service = AsyncMock()
                    mock_rewards_service.get_user_balance.return_value = 1000
                    mock_rewards.return_value = mock_rewards_service

                    # 并发测试参数
                    concurrent_requests = 10
                    threads_per_request = 5
                    results_queue = queue.Queue()

                    def worker():
                        """工作线程函数"""
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile/enhanced")
                        end_time = time.time()

                        results_queue.put({
                            "response_time": (end_time - start_time) * 1000,
                            "status_code": response.status_code
                        })

                    # 启动并发测试
                    threads = []
                    total_start_time = time.time()

                    for _ in range(concurrent_requests):
                        for _ in range(threads_per_request):
                            thread = threading.Thread(target=worker)
                            thread.start()
                            threads.append(thread)

                    # 等待所有线程完成
                    for thread in threads:
                        thread.join()

                    total_end_time = time.time()

                    # 收集结果
                    results = []
                    while not results_queue.empty():
                        results.append(results_queue.get())

                    # 分析结果
                    successful_requests = [r for r in results if r["status_code"] == 200]
                    response_times = [r["response_time"] for r in successful_requests]

                    # 性能断言
                    assert len(successful_requests) == concurrent_requests * threads_per_request, \
                        f"所有{concurrent_requests * threads_per_request}个并发请求都应该成功"

                    avg_response_time = statistics.mean(response_times)
                    max_response_time = max(response_times)
                    min_response_time = min(response_times)

                    # 并发请求的响应时间阈值
                    assert avg_response_time < 1000, f"并发平均响应时间应小于1000ms，实际: {avg_response_time:.2f}ms"
                    assert max_response_time < 2000, f"并发最大响应时间应小于2000ms，实际: {max_response_time:.2f}ms"

                    # 打印并发性能统计
                    total_time = (total_end_time - total_start_time) * 1000
                    print(f"并发请求性能统计:")
                    print(f"  并发请求数: {concurrent_requests * threads_per_request}")
                    print(f"  总耗时: {total_time:.2f}ms")
                    print(f"  平均响应时间: {avg_response_time:.2f}ms")
                    print(f"  最大响应时间: {max_response_time:.2f}ms")
                    print(f"  最小响应时间: {min_response_time:.2f}ms")
                    print(f"  吞吐量: {len(successful_requests) / (total_time / 1000):.2f} 请求/秒")

    def test_database_query_performance(self):
        """
        测试数据库查询性能

        Given: 模拟数据库会话
        When: 执行Profile相关查询
        Then: 查询时间应该在可接受范围内
        """
        # 使用内存数据库进行性能测试
        import tempfile
        import os
        from sqlmodel import create_engine, SQLModel
        from src.database.profile_connection import ProfileDatabaseConnection

        # 创建临时数据库
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()

        try:
            db_url = f"sqlite:///{temp_db.name}"
            profile_db = ProfileDatabaseConnection(database_url=db_url, echo=False)

            # 创建测试数据
            with profile_db.get_session() as session:
                # 创建用户数据
                users = []
                for i in range(100):
                    user = User(
                        user_id=uuid4(),
                        nickname=f"性能测试用户{i}",
                        avatar_url=f"https://example.com/avatar{i}.jpg",
                        bio=f"这是第{i}个性能测试用户",
                        gender="male" if i % 2 == 0 else "female",
                        is_active=True
                    )
                    users.append(user)
                    session.add(user)

                # 创建用户设置
                settings = []
                for i, user in enumerate(users):
                    setting = UserSettings(
                        user_id=user.user_id,
                        theme="dark" if i % 3 == 0 else "light",
                        language="zh-CN" if i % 2 == 0 else "en-US"
                    )
                    settings.append(setting)
                    session.add(setting)

                # 创建用户统计
                stats = []
                for i, user in enumerate(users):
                    stat = UserStats(
                        user_id=user.user_id,
                        tasks_completed=i * 5,
                        total_points=i * 100,
                        login_count=i + 1
                    )
                    stats.append(stat)
                    session.add(stat)

                session.commit()

            # 测试查询性能
            query_times = []

            with profile_db.get_session() as session:
                # 测试用户查询
                for i in range(50):
                    start_time = time.time()
                    user = session.get(User, users[i].user_id)
                    end_time = time.time()
                    query_times.append((end_time - start_time) * 1000)

                # 测试关联查询
                for i in range(30):
                    start_time = time.time()
                    user = session.get(User, users[i].user_id)

                    # 查询用户设置
                    settings_stmt = select(UserSettings).where(UserSettings.user_id == user.user_id)
                    user_settings = session.exec(settings_stmt).first()

                    # 查询用户统计
                    stats_stmt = select(UserStats).where(UserStats.user_id == user.user_id)
                    user_stats = session.exec(stats_stmt).first()

                    end_time = time.time()
                    query_times.append((end_time - start_time) * 1000)

            # 分析查询性能
            avg_query_time = statistics.mean(query_times)
            max_query_time = max(query_times)
            min_query_time = min(query_times)

            # 查询时间断言
            assert avg_query_time < 50, f"平均查询时间应小于50ms，实际: {avg_query_time:.2f}ms"
            assert max_query_time < 100, f"最大查询时间应小于100ms，实际: {max_query_time:.2f}ms"
            assert min_query_time < 10, f"最小查询时间应小于10ms，实际: {min_query_time:.2f}ms"

            # 打印查询性能统计
            print(f"数据库查询性能统计:")
            print(f"  平均查询时间: {avg_query_time:.2f}ms")
            print(f"  最大查询时间: {max_query_time:.2f}ms")
            print(f"  最小查询时间: {min_query_time:.2f}ms")
            print(f"  查询次数: {len(query_times)}")

        finally:
            # 清理临时数据库
            try:
                os.unlink(temp_db.name)
            except OSError:
                pass

    def test_memory_usage_during_requests(self, authenticated_client, mock_user_id):
        """
        测试请求过程中的内存使用情况

        Given: 模拟用户数据和认证客户端
        When: 连续调用增强Profile API
        Then: 内存使用应该保持稳定
        """
        import psutil
        import gc

        # Mock数据库操作
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "内存测试用户"
        mock_user.is_active = True

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo_class.return_value = mock_repo

            mock_session = Mock()
            mock_session.exec.return_value.first.return_value = Mock()

            with patch('src.database.get_db_session', return_value=mock_session):
                with patch('src.services.rewards_integration_service.get_rewards_service') as mock_rewards:
                    mock_rewards_service = AsyncMock()
                    mock_rewards_service.get_user_balance.return_value = 1000
                    mock_rewards.return_value = mock_rewards_service

                    # 获取当前进程
                    process = psutil.Process()

                    # 强制垃圾回收
                    gc.collect()
                    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

                    # 执行大量请求
                    request_count = 100
                    for i in range(request_count):
                        response = authenticated_client.get("/user/profile/enhanced")
                        assert response.status_code == 200

                        # 每10个请求强制垃圾回收一次
                        if i % 10 == 0:
                            gc.collect()

                    # 最终垃圾回收
                    gc.collect()
                    final_memory = process.memory_info().rss / 1024 / 1024  # MB

                    memory_increase = final_memory - initial_memory
                    memory_increase_per_request = memory_increase / request_count

                    # 内存使用断言
                    assert memory_increase < 50, f"内存增长应小于50MB，实际: {memory_increase:.2f}MB"
                    assert memory_increase_per_request < 0.5, f"每请求内存增长应小于0.5MB，实际: {memory_increase_per_request:.3f}MB"

                    # 打印内存使用统计
                    print(f"内存使用统计:")
                    print(f"  初始内存: {initial_memory:.2f}MB")
                    print(f"  最终内存: {final_memory:.2f}MB")
                    print(f"  内存增长: {memory_increase:.2f}MB")
                    print(f"  每请求内存增长: {memory_increase_per_request:.3f}MB")
                    print(f"  请求数量: {request_count}")

    def test_large_profile_data_performance(self, authenticated_client, mock_user_id):
        """
        测试大量Profile数据的性能

        Given: 包含大量数据的用户Profile
        When: 调用增强Profile API
        Then: 应该能高效处理大数据量
        """
        # Mock包含大量数据的用户
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "大数据测试用户" * 10  # 长字符串
        mock_user.avatar_url = "https://example.com/large-avatar.jpg"
        mock_user.bio = "这是一个包含大量数据的用户简介" * 20  # 很长的简介
        mock_user.gender = "female"
        mock_user.is_active = True

        # Mock包含大量数据的设置
        mock_settings = Mock()
        mock_settings.theme = "dark"
        mock_settings.language = "en-US"

        # Mock包含大量数据的统计
        mock_stats = Mock()
        mock_stats.tasks_completed = 999999
        mock_stats.total_points = 999999999
        mock_stats.login_count = 10000

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo_class.return_value = mock_repo

            mock_session = Mock()
            mock_session.exec.return_value.first.return_value = mock_settings

            with patch('src.database.get_db_session', return_value=mock_session):
                with patch('src.services.rewards_integration_service.get_rewards_service') as mock_rewards:
                    mock_rewards_service = AsyncMock()
                    mock_rewards_service.get_user_balance.return_value = 999999999
                    mock_rewards.return_value = mock_rewards_service

                    # 测试大数据量的响应时间
                    response_times = []
                    request_count = 10

                    for i in range(request_count):
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile/enhanced")
                        end_time = time.time()

                        if response.status_code == 200:
                            response_times.append((end_time - start_time) * 1000)

                            # 验证响应数据完整性
                            data = response.json()
                            assert data["code"] == 200
                            assert "data" in data
                            profile_data = data["data"]
                            assert len(profile_data["nickname"]) > 100  # 验证长昵称
                            assert len(profile_data["bio"]) > 500  # 验证长简介

                    # 大数据量性能断言
                    assert len(response_times) == request_count, "所有大数据量请求都应该成功"

                    avg_response_time = statistics.mean(response_times)
                    max_response_time = max(response_times)

                    # 大数据量的响应时间阈值稍高
                    assert avg_response_time < 800, f"大数据量平均响应时间应小于800ms，实际: {avg_response_time:.2f}ms"
                    assert max_response_time < 1500, f"大数据量最大响应时间应小于1500ms，实际: {max_response_time:.2f}ms"

                    # 打印大数据量性能统计
                    print(f"大数据量性能统计:")
                    print(f"  平均响应时间: {avg_response_time:.2f}ms")
                    print(f"  最大响应时间: {max_response_time:.2f}ms")
                    print(f"  请求数量: {len(response_times)}")