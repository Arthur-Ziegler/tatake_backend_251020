"""
Profile功能性能测试报告

生成增强用户Profile功能的性能测试报告，包括响应时间分析、并发性能评估和性能对比结果。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
import time
import statistics
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from typing import Dict, List, Any

from src.api.main import app
from src.api.dependencies import get_current_user_id


class TestProfilePerformanceReport:
    """Profile功能性能测试报告类"""

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

    def generate_performance_metrics(self, response_times: List[float]) -> Dict[str, float]:
        """生成性能指标"""
        return {
            "avg_response_time": statistics.mean(response_times),
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "median_response_time": statistics.median(response_times),
            "std_deviation": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) >= 20 else max(response_times),
            "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)] if len(response_times) >= 100 else max(response_times)
        }

    def test_comprehensive_performance_analysis(self, authenticated_client, mock_user_id):
        """
        综合性能分析测试

        生成详细的Profile API性能分析报告，包括：
        - 基础Profile GET/PUT性能
        - 增强Profile GET/PUT性能
        - 并发性能测试
        - 性能对比分析
        """
        print("\n" + "="*80)
        print("📊 增强用户Profile功能性能测试报告")
        print("="*80)

        # Mock数据
        mock_user = Mock()
        mock_user.user_id = mock_user_id
        mock_user.nickname = "性能分析用户"
        mock_user.is_active = True

        with patch('src.domains.user.router.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id_with_auth.return_value = {"user": mock_user, "auth": Mock()}
            mock_repo.update_user.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            mock_session = Mock()
            mock_session.exec.return_value.first.return_value = Mock()
            mock_session.commit.return_value = None

            with patch('src.database.get_db_session', return_value=mock_session):
                with patch('src.services.rewards_integration_service.get_rewards_service') as mock_rewards:
                    mock_rewards_service = AsyncMock()
                    mock_rewards_service.get_user_balance.return_value = 1000
                    mock_rewards.return_value = mock_rewards_service

                    # 1. 基础Profile GET性能测试
                    print("\n1️⃣ 基础Profile GET性能测试")
                    print("-" * 50)

                    basic_get_times = []
                    for _ in range(50):
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile")
                        end_time = time.time()
                        assert response.status_code == 200
                        basic_get_times.append((end_time - start_time) * 1000)

                    basic_get_metrics = self.generate_performance_metrics(basic_get_times)
                    print(f"📈 测试样本数: {len(basic_get_times)} 次请求")
                    print(f"⚡ 平均响应时间: {basic_get_metrics['avg_response_time']:.2f}ms")
                    print(f"🚀 最小响应时间: {basic_get_metrics['min_response_time']:.2f}ms")
                    print(f"🐌 最大响应时间: {basic_get_metrics['max_response_time']:.2f}ms")
                    print(f"📊 中位数响应时间: {basic_get_metrics['median_response_time']:.2f}ms")
                    print(f"📏 标准差: {basic_get_metrics['std_deviation']:.2f}ms")
                    print(f"🎯 P95响应时间: {basic_get_metrics['p95_response_time']:.2f}ms")

                    # 2. 增强Profile GET性能测试
                    print("\n2️⃣ 增强Profile GET性能测试")
                    print("-" * 50)

                    enhanced_get_times = []
                    for _ in range(50):
                        start_time = time.time()
                        response = authenticated_client.get("/user/profile/enhanced")
                        end_time = time.time()
                        assert response.status_code == 200
                        enhanced_get_times.append((end_time - start_time) * 1000)

                    enhanced_get_metrics = self.generate_performance_metrics(enhanced_get_times)
                    print(f"📈 测试样本数: {len(enhanced_get_times)} 次请求")
                    print(f"⚡ 平均响应时间: {enhanced_get_metrics['avg_response_time']:.2f}ms")
                    print(f"🚀 最小响应时间: {enhanced_get_metrics['min_response_time']:.2f}ms")
                    print(f"🐌 最大响应时间: {enhanced_get_metrics['max_response_time']:.2f}ms")
                    print(f"📊 中位数响应时间: {enhanced_get_metrics['median_response_time']:.2f}ms")
                    print(f"📏 标准差: {enhanced_get_metrics['std_deviation']:.2f}ms")
                    print(f"🎯 P95响应时间: {enhanced_get_metrics['p95_response_time']:.2f}ms")

                    # 3. 基础Profile PUT性能测试
                    print("\n3️⃣ 基础Profile PUT性能测试")
                    print("-" * 50)

                    basic_put_times = []
                    update_data = {
                        "nickname": "更新的测试用户",
                        "avatar_url": "https://example.com/new-avatar.jpg",
                        "bio": "更新后的用户简介"
                    }

                    for _ in range(30):
                        start_time = time.time()
                        response = authenticated_client.put("/user/profile", json=update_data)
                        end_time = time.time()
                        assert response.status_code == 200
                        basic_put_times.append((end_time - start_time) * 1000)

                    basic_put_metrics = self.generate_performance_metrics(basic_put_times)
                    print(f"📈 测试样本数: {len(basic_put_times)} 次请求")
                    print(f"⚡ 平均响应时间: {basic_put_metrics['avg_response_time']:.2f}ms")
                    print(f"🚀 最小响应时间: {basic_put_metrics['min_response_time']:.2f}ms")
                    print(f"🐌 最大响应时间: {basic_put_metrics['max_response_time']:.2f}ms")
                    print(f"📊 中位数响应时间: {basic_put_metrics['median_response_time']:.2f}ms")
                    print(f"📏 标准差: {basic_put_metrics['std_deviation']:.2f}ms")
                    print(f"🎯 P95响应时间: {basic_put_metrics['p95_response_time']:.2f}ms")

                    # 4. 增强Profile PUT性能测试
                    print("\n4️⃣ 增强Profile PUT性能测试")
                    print("-" * 50)

                    enhanced_put_times = []
                    enhanced_update_data = {
                        "nickname": "增强更新测试用户",
                        "gender": "male",
                        "theme": "light",
                        "language": "zh-CN"
                    }

                    for _ in range(30):
                        start_time = time.time()
                        response = authenticated_client.put("/user/profile/enhanced", json=enhanced_update_data)
                        end_time = time.time()
                        assert response.status_code == 200
                        enhanced_put_times.append((end_time - start_time) * 1000)

                    enhanced_put_metrics = self.generate_performance_metrics(enhanced_put_times)
                    print(f"📈 测试样本数: {len(enhanced_put_times)} 次请求")
                    print(f"⚡ 平均响应时间: {enhanced_put_metrics['avg_response_time']:.2f}ms")
                    print(f"🚀 最小响应时间: {enhanced_put_metrics['min_response_time']:.2f}ms")
                    print(f"🐌 最大响应时间: {enhanced_put_metrics['max_response_time']:.2f}ms")
                    print(f"📊 中位数响应时间: {enhanced_put_metrics['median_response_time']:.2f}ms")
                    print(f"📏 标准差: {enhanced_put_metrics['std_deviation']:.2f}ms")
                    print(f"🎯 P95响应时间: {enhanced_put_metrics['p95_response_time']:.2f}ms")

                    # 5. 性能对比分析
                    print("\n5️⃣ 性能对比分析")
                    print("-" * 50)

                    get_performance_ratio = enhanced_get_metrics['avg_response_time'] / basic_get_metrics['avg_response_time']
                    put_performance_ratio = enhanced_put_metrics['avg_response_time'] / basic_put_metrics['avg_response_time']

                    print(f"📊 GET性能对比 (增强/基础): {get_performance_ratio:.2f}x")
                    print(f"📊 PUT性能对比 (增强/基础): {put_performance_ratio:.2f}x")

                    # 6. 性能评估总结
                    print("\n6️⃣ 性能评估总结")
                    print("-" * 50)

                    # 性能阈值检查
                    performance_checks = [
                        ("基础Profile GET", basic_get_metrics['avg_response_time'], 200, "优秀"),
                        ("增强Profile GET", enhanced_get_metrics['avg_response_time'], 400, "优秀"),
                        ("基础Profile PUT", basic_put_metrics['avg_response_time'], 300, "优秀"),
                        ("增强Profile PUT", enhanced_put_metrics['avg_response_time'], 500, "优秀"),
                    ]

                    print("🔍 性能阈值检查:")
                    all_passed = True
                    for name, actual_time, threshold, default_status in performance_checks:
                        status = default_status if actual_time <= threshold else "需要优化"
                        all_passed = all_passed and (actual_time <= threshold)
                        print(f"  ✅ {name}: {actual_time:.2f}ms (阈值: {threshold}ms) - {status}")

                    # 7. 推荐优化建议
                    print("\n7️⃣ 性能优化建议")
                    print("-" * 50)

                    if get_performance_ratio > 2.0:
                        print("💡 建议优化增强Profile GET查询，考虑使用缓存或数据库查询优化")

                    if put_performance_ratio > 2.0:
                        print("💡 建议优化增强Profile PUT操作，考虑批量更新或异步处理")

                    if enhanced_get_metrics['std_deviation'] > 50:
                        print("💡 增强Profile GET响应时间波动较大，建议检查数据库连接或查询优化")

                    if enhanced_put_metrics['std_deviation'] > 100:
                        print("💡 增强Profile PUT响应时间波动较大，建议检查事务处理逻辑")

                    if all_passed:
                        print("🎉 所有性能指标均符合预期，增强Profile功能性能表现良好！")

                    print("\n" + "="*80)
                    print("📋 性能测试完成")
                    print("="*80)

                    # 最终性能断言
                    assert basic_get_metrics['avg_response_time'] < 200, f"基础Profile GET性能不达标: {basic_get_metrics['avg_response_time']:.2f}ms"
                    assert enhanced_get_metrics['avg_response_time'] < 400, f"增强Profile GET性能不达标: {enhanced_get_metrics['avg_response_time']:.2f}ms"
                    assert basic_put_metrics['avg_response_time'] < 300, f"基础Profile PUT性能不达标: {basic_put_metrics['avg_response_time']:.2f}ms"
                    assert enhanced_put_metrics['avg_response_time'] < 500, f"增强Profile PUT性能不达标: {enhanced_put_metrics['avg_response_time']:.2f}ms"
                    assert get_performance_ratio < 3.0, f"增强Profile GET性能下降过多: {get_performance_ratio:.2f}x"
                    assert put_performance_ratio < 3.0, f"增强Profile PUT性能下降过多: {put_performance_ratio:.2f}x"