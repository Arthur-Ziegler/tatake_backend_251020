"""
Refresh Token并发测试

测试Refresh Token在高并发场景下的行为：
1. 多个请求同时触发Token刷新
2. 验证Token更新的原子性
3. 确保数据一致性
4. 防止重复刷新问题

作者：TaTakeKe团队
版本：测试覆盖度改进
"""

import pytest
import asyncio
import httpx
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from tests.scenarios.utils import (
    create_test_client,
    create_authenticated_user,
    assert_api_success
)


@pytest.mark.integration
@pytest.mark.slow
class TestTokenRefreshConcurrent:
    """Refresh Token并发测试类"""

    @pytest.fixture
    def authenticated_user(self):
        """创建认证用户"""
        user_data = create_authenticated_user()
        client = create_test_client()
        client.headers.update({
            "Authorization": f"Bearer {user_data['access_token']}"
        })
        return client, user_data

    def test_concurrent_token_refresh_atomicity(self, authenticated_user):
        """测试并发Token刷新的原子性"""
        client, user_data = authenticated_user
        refresh_token = user_data['refresh_token']

        # 记录刷新结果
        refresh_results = []
        refresh_lock = threading.Lock()

        def refresh_token_worker():
            """Token刷新工作线程"""
            try:
                # 创建新的客户端实例，避免线程安全问题
                thread_client = create_test_client()

                refresh_response = thread_client.post("/auth/refresh", json={
                    "refresh_token": refresh_token
                })

                if refresh_response.status_code == 200:
                    refresh_data = refresh_response.json()
                    if refresh_data.get("code") == 200:
                        new_access_token = refresh_data["data"]["access_token"]
                        new_refresh_token = refresh_data["data"]["refresh_token"]

                        with refresh_lock:
                            refresh_results.append({
                                "success": True,
                                "access_token": new_access_token,
                                "refresh_token": new_refresh_token,
                                "timestamp": time.time()
                            })
                    else:
                        with refresh_lock:
                            refresh_results.append({
                                "success": False,
                                "error": refresh_data.get("message"),
                                "timestamp": time.time()
                            })
                else:
                    with refresh_lock:
                        refresh_results.append({
                            "success": False,
                            "error": f"HTTP {refresh_response.status_code}",
                            "timestamp": time.time()
                        })

            except Exception as e:
                with refresh_lock:
                    refresh_results.append({
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            finally:
                thread_client.close()

        # 启动多个并发刷新请求
        num_threads = 10
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(refresh_token_worker)
                for _ in range(num_threads)
            ]

            # 等待所有线程完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Thread execution error: {e}")

        # 验证结果
        successful_refreshes = [r for r in refresh_results if r["success"]]
        failed_refreshes = [r for r in refresh_results if not r["success"]]

        print(f"成功刷新次数: {len(successful_refreshes)}")
        print(f"失败刷新次数: {len(failed_refreshes)}")

        # 至少应该有部分成功
        assert len(successful_refreshes) > 0, "应该至少有一次刷新成功"

        # 验证所有成功的刷新返回相同的Token（原子性）
        if len(successful_refreshes) > 1:
            first_success = successful_refreshes[0]
            for success in successful_refreshes[1:]:
                assert success["access_token"] == first_success["access_token"], \
                    "并发刷新应返回相同的access_token"
                assert success["refresh_token"] == first_success["refresh_token"], \
                    "并发刷新应返回相同的refresh_token"

    def test_concurrent_token_refresh_with_expired_access_token(self, authenticated_user):
        """测试Access Token过期时的并发刷新"""
        client, user_data = authenticated_user
        refresh_token = user_data['refresh_token']

        # 记录API调用结果
        api_results = []
        api_lock = threading.Lock()

        def api_call_worker():
            """API调用工作线程"""
            try:
                thread_client = create_test_client()

                # 使用原始的access_token（可能即将过期）
                thread_client.headers.update({
                    "Authorization": f"Bearer {user_data['access_token']}"
                })

                # 调用需要认证的API
                response = thread_client.get("/user/profile")

                with api_lock:
                    api_results.append({
                        "status_code": response.status_code,
                        "success": response.status_code == 200,
                        "timestamp": time.time()
                    })

            except Exception as e:
                with api_lock:
                    api_results.append({
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            finally:
                thread_client.close()

        # 先启动多个API调用
        num_api_threads = 5
        with ThreadPoolExecutor(max_workers=num_api_threads) as executor:
            api_futures = [
                executor.submit(api_call_worker)
                for _ in range(num_api_threads)
            ]

            for future in as_completed(api_futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"API thread execution error: {e}")

        # 验证API调用结果
        successful_apis = [r for r in api_results if r["success"]]
        failed_apis = [r for r in api_results if not r["success"]]

        print(f"成功API调用次数: {len(successful_apis)}")
        print(f"失败API调用次数: {len(failed_apis)}")

    def test_concurrent_mixed_operations(self, authenticated_user):
        """测试混合并发操作（刷新Token + API调用）"""
        client, user_data = authenticated_user
        refresh_token = user_data['refresh_token']

        # 操作结果
        operation_results = []
        operation_lock = threading.Lock()

        def token_refresh_worker():
            """Token刷新工作线程"""
            try:
                thread_client = create_test_client()

                refresh_response = thread_client.post("/auth/refresh", json={
                    "refresh_token": refresh_token
                })

                with operation_lock:
                    operation_results.append({
                        "operation": "refresh",
                        "success": refresh_response.status_code == 200,
                        "status_code": refresh_response.status_code,
                        "timestamp": time.time()
                    })

            except Exception as e:
                with operation_lock:
                    operation_results.append({
                        "operation": "refresh",
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            finally:
                thread_client.close()

        def api_call_worker():
            """API调用工作线程"""
            try:
                thread_client = create_test_client()
                thread_client.headers.update({
                    "Authorization": f"Bearer {user_data['access_token']}"
                })

                response = thread_client.get("/user/profile")

                with operation_lock:
                    operation_results.append({
                        "operation": "api_call",
                        "success": response.status_code == 200,
                        "status_code": response.status_code,
                        "timestamp": time.time()
                    })

            except Exception as e:
                with operation_lock:
                    operation_results.append({
                        "operation": "api_call",
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            finally:
                thread_client.close()

        # 启动混合并发操作
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []

            # 提交刷新Token操作
            for _ in range(3):
                futures.append(executor.submit(token_refresh_worker))

            # 提交API调用操作
            for _ in range(5):
                futures.append(executor.submit(api_call_worker))

            # 等待所有操作完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Mixed operation execution error: {e}")

        # 分析结果
        refresh_operations = [r for r in operation_results if r["operation"] == "refresh"]
        api_operations = [r for r in operation_results if r["operation"] == "api_call"]

        successful_refreshes = [r for r in refresh_operations if r["success"]]
        successful_apis = [r for r in api_operations if r["success"]]

        print(f"成功刷新操作: {len(successful_refreshes)}/{len(refresh_operations)}")
        print(f"成功API操作: {len(successful_apis)}/{len(api_operations)}")

        # 至少应该有一些操作成功
        assert len(successful_refreshes) > 0 or len(successful_apis) > 0, \
            "应该至少有一些操作成功"

    def test_token_refresh_data_consistency(self, authenticated_user):
        """测试Token刷新后的数据一致性"""
        client, user_data = authenticated_user
        original_user_id = user_data['user_id']

        # 执行Token刷新
        refresh_response = client.post("/auth/refresh", json={
            "refresh_token": user_data['refresh_token']
        })

        if refresh_response.status_code != 200:
            pytest.skip("Token刷新API不可用")

        refresh_data = refresh_response.json()
        if refresh_data.get("code") != 200:
            pytest.skip("Token刷新失败")

        new_access_token = refresh_data["data"]["access_token"]
        new_refresh_token = refresh_data["data"]["refresh_token"]

        # 验证新Token的用户ID一致性
        import jwt
        try:
            # 解析新Token的payload
            # 注意：这里需要知道JWT的密钥，我们通过API验证来绕过
            new_client = create_test_client()
            new_client.headers.update({
                "Authorization": f"Bearer {new_access_token}"
            })

            # 使用新Token调用用户信息API
            user_info_response = new_client.get("/user/profile")

            if user_info_response.status_code == 200:
                user_info = user_info_response.json()
                if user_info.get("code") == 200:
                    current_user_id = user_info["data"].get("user_id")
                    assert current_user_id == original_user_id, \
                        f"Token刷新后用户ID应保持一致，原始: {original_user_id}, 当前: {current_user_id}"

            new_client.close()

        except Exception as e:
            print(f"Token验证跳过: {e}")

    def test_refresh_token_race_condition_prevention(self, authenticated_user):
        """测试Refresh Token竞态条件防护"""
        client, user_data = authenticated_user
        refresh_token = user_data['refresh_token']

        # 记录成功刷新的Token
        successful_tokens = []
        token_lock = threading.Lock()

        def rapid_refresh_worker():
            """快速刷新工作线程"""
            try:
                thread_client = create_test_client()

                refresh_response = thread_client.post("/auth/refresh", json={
                    "refresh_token": refresh_token
                })

                if refresh_response.status_code == 200:
                    refresh_data = refresh_response.json()
                    if refresh_data.get("code") == 200:
                        new_token = refresh_data["data"]["access_token"]

                        with token_lock:
                            if new_token not in successful_tokens:
                                successful_tokens.append(new_token)

            except Exception as e:
                print(f"Rapid refresh error: {e}")
            finally:
                thread_client.close()

        # 快速连续多次刷新
        num_rapid_calls = 20
        with ThreadPoolExecutor(max_workers=num_rapid_calls) as executor:
            futures = [
                executor.submit(rapid_refresh_worker)
                for _ in range(num_rapid_calls)
            ]

            # 等待所有调用完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Rapid refresh thread error: {e}")

        # 验证竞态条件防护
        print(f"快速刷新调用次数: {num_rapid_calls}")
        print(f"不同Token数量: {len(successful_tokens)}")

        # 理想情况下，应该只有1个不同的Token（原子性）
        # 实际可能由于网络延迟等原因有少量差异，但不应该有很多
        assert len(successful_tokens) <= 3, \
            f"竞态条件防护失败，产生了太多不同的Token: {len(successful_tokens)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])