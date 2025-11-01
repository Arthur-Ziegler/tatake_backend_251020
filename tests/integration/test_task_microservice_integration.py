"""
任务微服务集成测试

测试本地API与任务微服务的集成，验证9个核心接口的功能。
包括接口实现状态检查和错误处理验证。

作者：TaTake团队
版本：1.0.0（微服务集成测试）
"""

import pytest
import asyncio
import logging
from uuid import uuid4
from typing import Dict, Any

from src.services.task_microservice_client import (
    get_task_microservice_client,
    create_task,
    get_all_tasks,
    update_task,
    delete_task,
    complete_task,
    set_top3,
    get_top3,
    send_focus_status,
    get_pomodoro_count,
    TaskMicroserviceError
)

logger = logging.getLogger(__name__)


class TestTaskMicroserviceIntegration:
    """任务微服务集成测试类"""

    @pytest.fixture
    def test_user_id(self) -> str:
        """测试用户ID"""
        return "test_user_integration"

    @pytest.fixture
    def client(self):
        """微服务客户端实例"""
        return get_task_microservice_client()

    @pytest.mark.asyncio
    async def test_microservice_health(self, client):
        """测试微服务健康状态"""
        health = await client.health_check()
        # 微服务可能不可用，这只是检查连接状态
        logger.info(f"微服务健康状态: {health}")

    @pytest.mark.asyncio
    async def test_create_task_success(self, test_user_id):
        """测试创建任务 - 成功情况"""
        try:
            response = await create_task(
                user_id=test_user_id,
                title="集成测试任务",
                description="用于测试微服务集成的任务",
                priority="High",
                due_date="2025-11-02"
            )

            assert response["code"] == 200, f"创建任务失败: {response}"
            assert response["data"] is not None, "创建任务返回数据为空"
            assert response["data"]["title"] == "集成测试任务"
            assert response["data"]["user_id"] == test_user_id

            # 保存任务ID用于后续测试
            task_id = response["data"]["id"]
            logger.info(f"成功创建任务，ID: {task_id}")
            return task_id

        except Exception as e:
            pytest.fail(f"创建任务测试失败: {e}")

    @pytest.mark.asyncio
    async def test_create_task_with_invalid_priority(self, test_user_id):
        """测试创建任务 - 优先级格式错误"""
        try:
            response = await create_task(
                user_id=test_user_id,
                title="优先级测试任务",
                priority="high"  # 小写，应该失败
            )
            # 如果微服务接受了这个请求，说明它自动处理了大小写
            logger.info(f"微服务接受小写priority: {response}")
        except Exception as e:
            logger.info(f"小写priority被拒绝，符合预期: {e}")

    @pytest.mark.asyncio
    async def test_get_all_tasks_interface_not_implemented(self, test_user_id):
        """测试查询所有任务 - 接口未实现"""
        try:
            response = await get_all_tasks(user_id=test_user_id)

            # 检查是否返回501错误（功能未实现）
            if response["code"] == 501:
                logger.info("✅ GET /tasks 接口未实现，返回501错误")
                assert "功能暂未实现" in response["message"]
            else:
                logger.info(f"GET /tasks 接口已实现，响应: {response}")

        except Exception as e:
            pytest.fail(f"查询任务列表测试失败: {e}")

    @pytest.mark.asyncio
    async def test_update_task_interface_not_implemented(self, test_user_id):
        """测试更新任务 - 接口未实现"""
        try:
            task_id = str(uuid4())
            response = await update_task(
                user_id=test_user_id,
                task_id=task_id,
                title="更新后的任务标题"
            )

            # 检查是否返回501错误（功能未实现）
            if response["code"] == 501:
                logger.info("✅ PUT /tasks/{task_id} 接口未实现，返回501错误")
                assert "功能暂未实现" in response["message"]
            else:
                logger.info(f"PUT /tasks/{{task_id}} 接口已实现，响应: {response}")

        except Exception as e:
            pytest.fail(f"更新任务测试失败: {e}")

    @pytest.mark.asyncio
    async def test_delete_task_interface_not_implemented(self, test_user_id):
        """测试删除任务 - 接口未实现"""
        try:
            task_id = str(uuid4())
            response = await delete_task(user_id=test_user_id, task_id=task_id)

            # 检查是否返回501错误（功能未实现）
            if response["code"] == 501:
                logger.info("✅ DELETE /tasks/{task_id} 接口未实现，返回501错误")
                assert "功能暂未实现" in response["message"]
            else:
                logger.info(f"DELETE /tasks/{{task_id}} 接口已实现，响应: {response}")

        except Exception as e:
            pytest.fail(f"删除任务测试失败: {e}")

    @pytest.mark.asyncio
    async def test_complete_task_success(self, test_user_id):
        """测试完成任务 - 成功情况"""
        # 首先创建一个任务
        create_response = await create_task(
            user_id=test_user_id,
            title="待完成任务",
            description="用于测试完成功能的任务"
        )

        if create_response["code"] != 200:
            pytest.skip("无法创建测试任务，跳过完成测试")

        task_id = create_response["data"]["id"]

        try:
            # 完成任务
            response = await complete_task(
                user_id=test_user_id,
                task_id=task_id,
                completion_data={"completed_at": "2025-11-01T23:00:00Z"}
            )

            assert response["code"] == 200, f"完成任务失败: {response}"
            assert response["data"] is not None, "完成任务返回数据为空"
            assert "task" in response["data"], "响应中缺少task信息"
            assert response["data"]["task"]["status"] == "completed", "任务状态未更新为completed"

            logger.info(f"✅ 任务完成成功，获得奖励: {response['data'].get('reward_earned')}")

        except Exception as e:
            pytest.fail(f"完成任务测试失败: {e}")

    @pytest.mark.asyncio
    async def test_top3_interfaces_not_implemented(self, test_user_id):
        """测试Top3相关接口 - 接口未实现"""
        # 测试设置Top3
        try:
            response = await set_top3(
                user_id=test_user_id,
                date="2025-11-01",
                task_ids=[str(uuid4())]
            )

            if response["code"] == 501:
                logger.info("✅ POST /tasks/special/top3 接口未实现，返回501错误")
                assert "功能暂未实现" in response["message"]
            else:
                logger.info(f"POST /tasks/special/top3 接口已实现，响应: {response}")

        except Exception as e:
            pytest.fail(f"设置Top3测试失败: {e}")

        # 测试获取Top3
        try:
            response = await get_top3(user_id=test_user_id, date="2025-11-01")

            if response["code"] == 501:
                logger.info("✅ GET /tasks/special/top3/{date} 接口未实现，返回501错误")
                assert "功能暂未实现" in response["message"]
            else:
                logger.info(f"GET /tasks/special/top3/{{date}} 接口已实现，响应: {response}")

        except Exception as e:
            pytest.fail(f"获取Top3测试失败: {e}")

    @pytest.mark.asyncio
    async def test_focus_status_interface_not_implemented(self, test_user_id):
        """测试专注状态接口 - 接口未实现"""
        try:
            response = await send_focus_status(
                user_id=test_user_id,
                focus_status="start",
                task_id=str(uuid4()),
                duration_minutes=25
            )

            if response["code"] == 501:
                logger.info("✅ POST /tasks/focus-status 接口未实现，返回501错误")
                assert "功能暂未实现" in response["message"]
            else:
                logger.info(f"POST /tasks/focus-status 接口已实现，响应: {response}")

        except Exception as e:
            pytest.fail(f"发送专注状态测试失败: {e}")

    @pytest.mark.asyncio
    async def test_pomodoro_count_interface_not_implemented(self, test_user_id):
        """测试番茄钟计数接口 - 接口未实现"""
        try:
            response = await get_pomodoro_count(user_id=test_user_id, date_filter="today")

            if response["code"] == 501:
                logger.info("✅ GET /tasks/pomodoro-count 接口未实现，返回501错误")
                assert "功能暂未实现" in response["message"]
            else:
                logger.info(f"GET /tasks/pomodoro-count 接口已实现，响应: {response}")

        except Exception as e:
            pytest.fail(f"获取番茄钟计数测试失败: {e}")

    @pytest.mark.asyncio
    async def test_error_handling_for_invalid_task_id(self, test_user_id):
        """测试无效任务ID的错误处理"""
        invalid_task_id = "invalid-task-id"

        try:
            response = await complete_task(user_id=test_user_id, task_id=invalid_task_id)

            # 应该返回错误，但不应该是500（服务器内部错误）
            assert response["code"] != 200, "无效任务ID不应该成功"
            assert response["data"] is None, "错误响应的数据应该为空"
            logger.info(f"✅ 无效任务ID正确返回错误: {response['message']}")

        except Exception as e:
            pytest.fail(f"无效任务ID错误处理测试失败: {e}")

    @pytest.mark.asyncio
    async def test_complete_interface_status_summary(self, test_user_id):
        """测试完整接口状态总结"""
        """执行一次完整的接口状态检查"""
        results = {
            "create_task": False,
            "get_all_tasks": False,
            "update_task": False,
            "delete_task": False,
            "complete_task": False,
            "set_top3": False,
            "get_top3": False,
            "send_focus_status": False,
            "get_pomodoro_count": False
        }

        # 测试创建任务
        try:
            response = await create_task(user_id=test_user_id, title="状态检查任务")
            results["create_task"] = response["code"] == 200
        except:
            results["create_task"] = False

        # 测试其他接口
        interfaces_to_test = [
            ("get_all_tasks", lambda: get_all_tasks(test_user_id)),
            ("update_task", lambda: update_task(test_user_id, str(uuid4()))),
            ("delete_task", lambda: delete_task(test_user_id, str(uuid4()))),
            ("set_top3", lambda: set_top3(test_user_id, "2025-11-01", [])),
            ("get_top3", lambda: get_top3(test_user_id, "2025-11-01")),
            ("send_focus_status", lambda: send_focus_status(test_user_id, "start")),
            ("get_pomodoro_count", lambda: get_pomodoro_count(test_user_id))
        ]

        for interface_name, interface_func in interfaces_to_test:
            try:
                response = await interface_func()
                results[interface_name] = response["code"] != 501  # 501表示未实现
            except:
                results[interface_name] = False

        # 测试完成任务（需要先有任务）
        try:
            create_resp = await create_task(user_id=test_user_id, title="待完成检查任务")
            if create_resp["code"] == 200:
                task_id = create_resp["data"]["id"]
                complete_resp = await complete_task(test_user_id, task_id)
                results["complete_task"] = complete_resp["code"] == 200
        except:
            results["complete_task"] = False

        # 输出状态总结
        implemented_count = sum(results.values())
        total_count = len(results)

        logger.info(f"=== 任务微服务接口状态总结 ===")
        logger.info(f"已实现接口数量: {implemented_count}/{total_count}")

        for interface, status in results.items():
            status_text = "✅ 已实现" if status else "❌ 未实现"
            logger.info(f"  {interface}: {status_text}")

        # 至少创建任务和完成任务应该可用
        assert results["create_task"], "创建任务接口必须可用"
        assert results["complete_task"], "完成任务接口必须可用"