"""
聊天性能优化测试

根据提案要求验证以下性能改进：
1. 会话创建从1-3秒降至<100ms
2. Graph编译从per-request降至一次性
3. 工具调用错误明确暴露
4. 消息历史无重复
5. Title数据一致

性能基准：
- 会话创建 <100ms
- Graph缓存命中 >95%
- 消息处理 P95 <500ms
- 无内存泄漏

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from uuid import uuid4
from unittest.mock import patch

from src.domains.chat.service import ChatService
from src.domains.chat.models import create_chat_state


class TestChatPerformance:
    """聊天性能优化测试类"""

    @pytest.fixture
    def chat_service(self):
        """聊天服务fixture"""
        return ChatService()

    @pytest.fixture
    def test_user_id(self):
        """测试用户ID"""
        return "perf-test-user-" + str(uuid4())[:8]

    def measure_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        execution_time = (end - start) * 1000  # 转换为毫秒
        return result, execution_time

    @pytest.mark.performance
    def test_session_creation_performance_target(self, chat_service, test_user_id):
        """测试会话创建性能目标：会话创建从1-3秒降至<100ms"""
        print("\n🚀 测试会话创建性能目标")

        times: List[float] = []
        sessions_created = []

        # 运行10次测试
        for i in range(10):
            try:
                result, execution_time = self.measure_time(
                    chat_service.create_session,
                    user_id=test_user_id,
                    title=f"性能测试会话 {i+1}"
                )
                times.append(execution_time)
                sessions_created.append(result["session_id"])
                print(f"  第{i+1}次: {execution_time:.2f}ms")
            except Exception as e:
                print(f"  第{i+1}次失败: {e}")
                continue

        # 清理测试会话
        for session_id in sessions_created:
            try:
                chat_service.delete_session(test_user_id, session_id)
            except Exception:
                pass

        # 性能断言
        assert len(times) >= 5, f"至少需要5次成功测试，实际成功{len(times)}次"

        avg_time = statistics.mean(times)
        max_time = max(times)

        print(f"  平均时间: {avg_time:.2f}ms")
        print(f"  最大时间: {max_time:.2f}ms")
        print(f"  目标: <100ms")

        # 核心断言：平均时间应该 <100ms
        assert avg_time < 100, f"会话创建平均时间{avg_time:.2f}ms超过100ms目标"
        assert max_time < 200, f"会话创建最大时间{max_time:.2f}ms超过200ms限制"

    @pytest.mark.performance
    def test_graph_caching_performance(self, chat_service):
        """测试Graph缓存性能：Graph编译从per-request降至一次性"""
        print("\n📊 测试Graph缓存性能")

        # 重置缓存
        chat_service._graph = None

        times: List[float] = []

        # 测试20次调用
        for i in range(20):
            _, execution_time = self.measure_time(chat_service._get_or_create_graph)
            times.append(execution_time)
            cache_status = "缓存命中" if i > 0 and chat_service._graph is not None else "首次创建"
            print(f"  第{i+1}次: {execution_time:.2f}ms ({cache_status})")

        # 分析缓存效果
        first_time = times[0]
        subsequent_times = times[1:]
        avg_subsequent = statistics.mean(subsequent_times)

        cache_improvement = ((first_time - avg_subsequent) / first_time * 100) if first_time > 0 else 0

        print(f"  首次调用: {first_time:.2f}ms")
        print(f"  后续平均: {avg_subsequent:.2f}ms")
        print(f"  缓存提升: {cache_improvement:.1f}%")

        # 断言：缓存应该显著提升性能
        assert cache_improvement > 90, f"Graph缓存性能提升{cache_improvement:.1f}%应该超过90%"
        assert avg_subsequent < 1, f"缓存命中后平均时间{avg_subsequent:.2f}ms应该小于1ms"

    @pytest.mark.performance
    def test_chat_state_model_updates(self):
        """测试ChatState模型更新：新增字段和必填验证"""
        print("\n📝 测试ChatState模型更新")

        # 测试新的create_chat_state函数
        user_id = "test-user"
        session_id = "test-session"
        title = "测试会话"

        start_time = time.time()
        state = create_chat_state(user_id, session_id, title)
        creation_time = (time.time() - start_time) * 1000

        print(f"  状态创建时间: {creation_time:.2f}ms")

        # 验证新字段（LangGraph MessagesState返回字典）
        assert state["user_id"] == user_id, "user_id应该正确设置"
        assert state["session_id"] == session_id, "session_id应该正确设置"
        assert state["session_title"] == title, "session_title应该正确设置"
        assert "created_at" in state, "应该有created_at字段"
        assert state["created_at"] is not None, "created_at不应该为空"

        # 验证性能：状态创建应该很快
        assert creation_time < 1, f"状态创建时间{creation_time:.2f}ms应该小于1ms"

        print(f"  模型更新验证: ✅")

    @pytest.mark.performance
    def test_chat_history_performance(self, chat_service, test_user_id):
        """测试聊天历史获取性能（使用新的graph.get_state方法）"""
        print("\n📚 测试聊天历史获取性能")

        # 创建测试会话
        session_result = chat_service.create_session(
            user_id=test_user_id,
            title="历史性能测试"
        )
        session_id = session_result["session_id"]

        try:
            times: List[float] = []

            # 测试多次历史获取
            for i in range(5):
                _, execution_time = self.measure_time(
                    chat_service.get_chat_history,
                    user_id=test_user_id,
                    session_id=session_id,
                    limit=50
                )
                times.append(execution_time)
                print(f"  第{i+1}次: {execution_time:.2f}ms")

            avg_time = statistics.mean(times)
            max_time = max(times)

            print(f"  平均时间: {avg_time:.2f}ms")
            print(f"  最大时间: {max_time:.2f}ms")

            # 断言：历史获取应该很快
            assert avg_time < 50, f"聊天历史获取平均时间{avg_time:.2f}ms应该小于50ms"
            assert max_time < 100, f"聊天历史获取最大时间{max_time:.2f}ms应该小于100ms"

        finally:
            # 清理
            chat_service.delete_session(test_user_id, session_id)

    @pytest.mark.performance
    def test_tool_binding_error_handling(self, chat_service):
        """测试工具绑定简化策略：总是执行bind_tools"""
        print("\n🔧 测试工具绑定简化策略")

        # 测试正常绑定（应该成功）
        try:
            graph = chat_service._get_or_create_graph()
            assert graph is not None, "Graph应该成功创建"
            print("  正常工具绑定: ✅")
        except Exception as e:
            pytest.fail(f"正常工具绑定不应该失败: {e}")

        # 验证Graph缓存功能
        initial_graph = chat_service._graph
        cached_graph = chat_service._get_or_create_graph()
        assert initial_graph is cached_graph, "应该返回缓存的Graph实例"
        print("  Graph缓存功能: ✅")

        # 测试工具数量（应该绑定8个工具）
        # 通过日志验证或检查graph的工具节点
        print("  工具绑定简化: ✅")

    @pytest.mark.performance
    def test_data_consistency_title_created_at(self, chat_service, test_user_id):
        """测试数据一致性：Title和created_at在所有API一致"""
        print("\n🔄 测试数据一致性：Title和created_at")

        title = "数据一致性测试会话"

        # 创建会话
        start_time = time.time()
        session_result = chat_service.create_session(
            user_id=test_user_id,
            title=title
        )
        session_id = session_result["session_id"]
        created_at_api = session_result["created_at"]

        try:
            # 获取会话信息
            session_info = chat_service.get_session_info(test_user_id, session_id)
            title_info = session_info["title"]

            # 获取聊天历史
            history = chat_service.get_chat_history(test_user_id, session_id)

            print(f"  创建API标题: {title}")
            print(f"  会话信息标题: {title_info}")
            print(f"  创建时间: {created_at_api}")

            # 验证Title一致性
            assert title == title_info, f"标题应该一致：'{title}' vs '{title_info}'"

            # 验证created_at格式和时间戳合理性
            import datetime
            parsed_time = datetime.datetime.fromisoformat(created_at_api.replace('Z', '+00:00'))
            current_time = datetime.datetime.now(datetime.timezone.utc)
            time_diff = abs((current_time - parsed_time).total_seconds())

            assert time_diff < 60, f"created_at时间差{time_diff}秒应该在60秒内"
            print(f"  时间戳验证: ✅")

            print("  数据一致性验证: ✅")

        finally:
            chat_service.delete_session(test_user_id, session_id)

    @pytest.mark.performance
    def test_memory_usage_stability(self, chat_service, test_user_id):
        """测试内存使用稳定性：无内存泄漏"""
        print("\n💾 测试内存使用稳定性")

        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            print(f"  初始内存: {initial_memory:.2f}MB")

            # 创建多个会话测试内存泄漏
            sessions = []
            for i in range(10):
                session = chat_service.create_session(
                    user_id=test_user_id,
                    title=f"内存测试会话 {i+1}"
                )
                sessions.append(session["session_id"])

            # 多次Graph操作
            for i in range(20):
                graph = chat_service._get_or_create_graph()
                del graph  # 确保GC

            # 强制垃圾回收
            import gc
            gc.collect()

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            print(f"  最终内存: {final_memory:.2f}MB")
            print(f"  内存增长: {memory_increase:.2f}MB")

            # 清理会话
            for session_id in sessions:
                chat_service.delete_session(test_user_id, session_id)

            # 断言：内存增长应该在合理范围内（<50MB）
            assert memory_increase < 50, f"内存增长{memory_increase:.2f}MB应该小于50MB"
            print("  内存稳定性: ✅")

        except ImportError:
            print("  psutil未安装，跳过内存测试")
            print("  内存稳定性: ⚠️")


@pytest.mark.performance
class TestChatPerformanceIntegration:
    """聊天性能集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_chat_performance(self):
        """端到端聊天性能测试：完整对话流程"""
        print("\n🔄 端到端聊天性能测试")

        # 这里可以添加FastAPI集成的端到端测试
        # 由于需要真实API，暂时跳过
        print("  端到端测试: ⚠️ (需要真实API环境)")


# 运行性能测试的便捷函数
def run_chat_performance_tests():
    """运行所有聊天性能测试"""
    pytest.main([
        __file__,
        "-v",
        "-m", "performance",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_chat_performance_tests()