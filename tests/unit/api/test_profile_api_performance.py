"""
Profile API性能验证测试

专门针对增强Profile功能的API性能验证，包括响应时间测试和并发性能测试。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
import time
import statistics
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.dependencies import get_current_user_id


class TestProfileAPIPerformance:
    """Profile API性能验证测试类"""

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

    def test_basic_profile_get_performance(self, authenticated_client, mock_user_id):
        """
        测试基础Profile GET API性能

        Given: 模拟用户数据和认证客户端
        When: 多次调用GET /user/profile
        Then: 响应时间应该在可接受范围内
        """
        # Mock基础用户数据
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "性能测试用户"
        mock_user.avatar_url = "https://example.com/performance-avatar.jpg"
        mock_user.bio = "性能测试用户简介"
        mock_user.created_at = "2025-01-01T00:00:00Z"

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo_class.return_value = mock_repo

            # 执行性能测试
            response_times = []
            request_count = 20

            for i in range(request_count):
                start_time = time.time()
                response = authenticated_client.get("/user/profile")
                end_time = time.time()

                assert response.status_code == 200
                response_times.append((end_time - start_time) * 1000)  # 转换为毫秒

            # 性能分析
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)

            # 性能断言
            assert avg_response_time < 200, f"基础Profile GET平均响应时间应小于200ms，实际: {avg_response_time:.2f}ms"
            assert max_response_time < 500, f"基础Profile GET最大响应时间应小于500ms，实际: {max_response_time:.2f}ms"

            print(f"基础Profile GET性能统计:")
            print(f"  平均响应时间: {avg_response_time:.2f}ms")
            print(f"  最大响应时间: {max_response_time:.2f}ms")
            print(f"  最小响应时间: {min_response_time:.2f}ms")

    def test_enhanced_profile_get_performance(self, authenticated_client, mock_user_id):
        """
        测试增强Profile GET API性能

        Given: 模拟用户数据和认证客户端
        When: 多次调用GET /user/profile/enhanced
        Then: 响应时间应该在可接受范围内
        """
        # Mock增强用户数据
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "增强性能测试用户"
        mock_user.avatar_url = "https://example.com/enhanced-avatar.jpg"
        mock_user.bio = "增强性能测试用户简介"
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

                    # 执行性能测试
                    response_times = []
                    request_count = 20

                    for i in range(request_count):
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile/enhanced")
                        end_time = time.time()

                        assert response.status_code == 200
                        response_times.append((end_time - start_time) * 1000)

                    # 性能分析
                    avg_response_time = statistics.mean(response_times)
                    max_response_time = max(response_times)
                    min_response_time = min(response_times)

                    # 增强Profile的响应时间阈值稍高
                    assert avg_response_time < 400, f"增强Profile GET平均响应时间应小于400ms，实际: {avg_response_time:.2f}ms"
                    assert max_response_time < 800, f"增强Profile GET最大响应时间应小于800ms，实际: {max_response_time:.2f}ms"

                    print(f"增强Profile GET性能统计:")
                    print(f"  平均响应时间: {avg_response_time:.2f}ms")
                    print(f"  最大响应时间: {max_response_time:.2f}ms")
                    print(f"  最小响应时间: {min_response_time:.2f}ms")

    def test_basic_profile_put_performance(self, authenticated_client, mock_user_id):
        """
        测试基础Profile PUT API性能

        Given: 模拟用户数据和认证客户端
        When: 多次调用PUT /user/profile
        Then: 响应时间应该在可接受范围内
        """
        # Mock用户更新操作
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "更新测试用户"
        mock_user.avatar_url = "https://example.com/updated-avatar.jpg"
        mock_user.bio = "更新后的用户简介"

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo.update_user.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            # 执行性能测试
            response_times = []
            request_count = 15

            update_data = {
                "nickname": "更新后的测试用户",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "更新后的用户简介"
            }

            for i in range(request_count):
                start_time = time.time()
                response = authenticated_client.put("/user/profile", json=update_data)
                end_time = time.time()

                assert response.status_code == 200
                response_times.append((end_time - start_time) * 1000)

            # 性能分析
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)

            # 更新操作的响应时间阈值
            assert avg_response_time < 300, f"基础Profile PUT平均响应时间应小于300ms，实际: {avg_response_time:.2f}ms"
            assert max_response_time < 600, f"基础Profile PUT最大响应时间应小于600ms，实际: {max_response_time:.2f}ms"

            print(f"基础Profile PUT性能统计:")
            print(f"  平均响应时间: {avg_response_time:.2f}ms")
            print(f"  最大响应时间: {max_response_time:.2f}ms")
            print(f"  最小响应时间: {min_response_time:.2f}ms")

    def test_enhanced_profile_put_performance(self, authenticated_client, mock_user_id):
        """
        测试增强Profile PUT API性能

        Given: 模拟用户数据和认证客户端
        When: 多次调用PUT /user/profile/enhanced
        Then: 响应时间应该在可接受范围内
        """
        # Mock用户更新操作
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "增强更新测试用户"
        mock_user.gender = "female"
        mock_user.birthday = "1985-08-20"

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo.update_user.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            mock_session = Mock()
            mock_session.exec.return_value.first.return_value = Mock()
            mock_session.commit.return_value = None

            with patch('src.database.get_db_session', return_value=mock_session):
                # 执行性能测试
                response_times = []
                request_count = 15

                update_data = {
                    "nickname": "更新后的增强测试用户",
                    "gender": "male",
                    "theme": "light",
                    "language": "zh-CN"
                }

                for i in range(request_count):
                    start_time = time.time()
                    response = authenticated_client.put("/user/profile/enhanced", json=update_data)
                    end_time = time.time()

                    assert response.status_code == 200
                    response_times.append((end_time - start_time) * 1000)

                # 性能分析
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)

                # 增强更新操作的响应时间阈值
                assert avg_response_time < 500, f"增强Profile PUT平均响应时间应小于500ms，实际: {avg_response_time:.2f}ms"
                assert max_response_time < 1000, f"增强Profile PUT最大响应时间应小于1000ms，实际: {max_response_time:.2f}ms"

                print(f"增强Profile PUT性能统计:")
                print(f"  平均响应时间: {avg_response_time:.2f}ms")
                print(f"  最大响应时间: {max_response_time:.2f}ms")
                print(f"  最小响应时间: {min_response_time:.2f}ms")

    def test_profile_concurrent_performance(self, authenticated_client, mock_user_id):
        """
        测试Profile API并发性能

        Given: 模拟用户数据和认证客户端
        When: 并发调用Profile API
        Then: 并发请求的响应时间应该保持稳定
        """
        import threading
        import queue

        # Mock用户数据
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
                    threads_per_request = 3
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

                    # 并发请求的响应时间阈值
                    assert avg_response_time < 800, f"并发平均响应时间应小于800ms，实际: {avg_response_time:.2f}ms"
                    assert max_response_time < 1500, f"并发最大响应时间应小于1500ms，实际: {max_response_time:.2f}ms"

                    # 打印并发性能统计
                    total_time = (total_end_time - total_start_time) * 1000
                    print(f"并发请求性能统计:")
                    print(f"  并发请求数: {concurrent_requests * threads_per_request}")
                    print(f"  总耗时: {total_time:.2f}ms")
                    print(f"  平均响应时间: {avg_response_time:.2f}ms")
                    print(f"  最大响应时间: {max_response_time:.2f}ms")
                    print(f"  吞吐量: {len(successful_requests) / (total_time / 1000):.2f} 请求/秒")

    def test_performance_comparison_basic_vs_enhanced(self, authenticated_client, mock_user_id):
        """
        测试基础Profile与增强Profile的性能对比

        Given: 模拟用户数据和认证客户端
        When: 分别调用基础和增强Profile API
        Then: 性能差异应该在可接受范围内
        """
        # Mock基础用户数据
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "对比测试用户"
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

                    # 测试基础Profile性能
                    basic_times = []
                    for _ in range(20):
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile")
                        end_time = time.time()
                        assert response.status_code == 200
                        basic_times.append((end_time - start_time) * 1000)

                    # 测试增强Profile性能
                    enhanced_times = []
                    for _ in range(20):
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile/enhanced")
                        end_time = time.time()
                        assert response.status_code == 200
                        enhanced_times.append((end_time - start_time) * 1000)

                    # 性能分析
                    basic_avg = statistics.mean(basic_times)
                    enhanced_avg = statistics.mean(enhanced_times)
                    performance_ratio = enhanced_avg / basic_avg

                    # 性能对比断言
                    assert basic_avg < 200, f"基础Profile平均响应时间应小于200ms，实际: {basic_avg:.2f}ms"
                    assert enhanced_avg < 400, f"增强Profile平均响应时间应小于400ms，实际: {enhanced_avg:.2f}ms"
                    assert performance_ratio < 3.0, f"增强Profile性能不应超过基础Profile的3倍，实际比例: {performance_ratio:.2f}"

                    print(f"基础Profile vs 增强Profile性能对比:")
                    print(f"  基础Profile平均响应时间: {basic_avg:.2f}ms")
                    print(f"  增强Profile平均响应时间: {enhanced_avg:.2f}ms")
                    print(f"  性能比例 (增强/基础): {performance_ratio:.2f}")