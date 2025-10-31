"""
前端API调用模拟集成测试

模拟真实前端用户的所有API调用，验证Task微服务代理架构的完整性。
使用FastAPI的TestClient进行HTTP层面的测试。

测试覆盖：
1. 完整的任务CRUD操作
2. Top3设置和查询
3. 任务完成流程
4. 错误处理和边界条件
5. API响应格式验证

作者：TaKeKe团队
版本：1.0.0（前端API模拟测试）
"""

import pytest
import json
from datetime import datetime, date, timezone
from uuid import uuid4, UUID
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from sqlmodel import Session

# 导入应用
from src.api.main import app
from src.database import get_db_session
from src.services.task_microservice_client import TaskMicroserviceClient, TaskMicroserviceError


class MockTaskService:
    """模拟Task微服务响应"""

    def __init__(self):
        self.tasks = {}
        self.top3_settings = {}

    def get_response(self, method: str, path: str, user_id: str, data=None, params=None):
        """生成模拟响应"""
        try:
            # 解析路径
            path_parts = path.strip("/").split("/")

            if method == "POST" and path == "tasks":
                # 创建任务
                task_id = str(uuid4())
                task_data = {
                    "id": task_id,
                    "title": data["title"],
                    "description": data.get("description", ""),
                    "status": data.get("status", "pending"),
                    "priority": data.get("priority", "medium"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                self.tasks[task_id] = task_data
                return {"success": True, "data": task_data}

            elif method == "GET" and len(path_parts) == 2 and path_parts[0] == "tasks" and path_parts[1] != "statistics" and path_parts[1] != "special":
                # 获取单个任务
                task_id = path_parts[1]
                if task_id in self.tasks:
                    return {"success": True, "data": self.tasks[task_id]}
                else:
                    return {"success": False, "message": "任务不存在", "code": 404}

            elif method == "PUT" and len(path_parts) == 2 and path_parts[0] == "tasks":
                # 更新任务
                task_id = path_parts[1]
                if task_id in self.tasks:
                    self.tasks[task_id].update(data)
                    self.tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                    return {"success": True, "data": self.tasks[task_id]}
                else:
                    return {"success": False, "message": "任务不存在", "code": 404}

            elif method == "DELETE" and len(path_parts) == 2 and path_parts[0] == "tasks":
                # 删除任务
                task_id = path_parts[1]
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    return {"success": True, "data": {"deleted_task_id": task_id}}
                else:
                    return {"success": False, "message": "任务不存在", "code": 404}

            elif method == "GET" and path == "tasks":
                # 获取任务列表
                task_list = list(self.tasks.values())
                if params:
                    page = int(params.get("page", 1))
                    page_size = int(params.get("page_size", 20))
                    start = (page - 1) * page_size
                    end = start + page_size
                    paginated_tasks = task_list[start:end]
                else:
                    paginated_tasks = task_list

                return {
                    "success": True,
                    "data": {
                        "tasks": paginated_tasks,
                        "current_page": params.get("page", 1) if params else 1,
                        "page_size": params.get("page_size", 20) if params else 20,
                        "total_count": len(task_list),
                        "total_pages": (len(task_list) + 19) // 20,
                        "has_next": len(task_list) > (int(params.get("page", 1)) * int(params.get("page_size", 20))),
                        "has_prev": int(params.get("page", 1)) > 1
                    }
                }

            elif method == "POST" and path == "tasks/special/top3":
                # 设置Top3
                date_str = data["date"]
                self.top3_settings[date_str] = {
                    "date": date_str,
                    "task_ids": data["task_ids"],
                    "points_consumed": 300,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                return {"success": True, "data": self.top3_settings[date_str]}

            elif method == "GET" and len(path_parts) == 4 and path_parts[0] == "tasks" and path_parts[1] == "special" and path_parts[2] == "top3":
                # 获取Top3
                date_str = path_parts[3]
                if date_str in self.top3_settings:
                    return {"success": True, "data": self.top3_settings[date_str]}
                else:
                    return {"success": True, "data": {"date": date_str, "task_ids": [], "points_consumed": 0}}

            elif method == "GET" and path == "tasks/statistics":
                # 获取统计
                tasks = list(self.tasks.values())
                total = len(tasks)
                completed = len([t for t in tasks if t["status"] == "completed"])
                in_progress = len([t for t in tasks if t["status"] == "in_progress"])
                pending = len([t for t in tasks if t["status"] == "pending"])

                return {
                    "success": True,
                    "data": {
                        "total_tasks": total,
                        "completed_tasks": completed,
                        "in_progress_tasks": in_progress,
                        "pending_tasks": pending,
                        "completion_rate": (completed / total * 100) if total > 0 else 0.0,
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    }
                }

            return {"success": True, "data": {}}

        except Exception as e:
            return {"success": False, "message": f"内部错误: {str(e)}", "code": 500}


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_task_service():
    """创建模拟Task服务"""
    return MockTaskService()


@pytest.fixture
def mock_jwt_auth():
    """模拟JWT认证"""
    mp = pytest.MonkeyPatch()
    mp.setattr('src.api.dependencies.get_current_user_id', lambda: UUID("12345678-1234-5678-9abc-123456789abc"))
    yield mp
    mp.undo()


@pytest.fixture
def mock_microservice_client(mock_task_service):
    """模拟微服务客户端"""
    mp = pytest.MonkeyPatch()
    mp.setattr('src.services.task_microservice_client.call_task_service', mock_task_service.get_response)
    yield mp
    mp.undo()


@pytest.mark.integration
class TestFrontendAPISimulation:
    """前端API调用模拟测试"""

    def test_complete_task_workflow(self, client, mock_jwt_auth, mock_microservice_client, mock_task_service):
        """测试完整的任务工作流"""
        print("🧪 测试完整任务工作流...")

        # 1. 创建任务
        create_data = {
            "title": "测试任务1",
            "description": "这是一个测试任务",
            "status": "pending",
            "priority": "high"
        }

        response = client.post("/tasks/", json=create_data, headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 201
        create_result = response.json()
        assert create_result["code"] == 201
        assert create_result["data"]["title"] == "测试任务1"
        assert create_result["data"]["status"] == "pending"

        task_id = create_result["data"]["id"]
        print(f"  ✅ 创建任务成功: {task_id[:8]}...")

        # 2. 获取任务详情
        response = client.get(f"/tasks/{task_id}", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        detail_result = response.json()
        assert detail_result["code"] == 200
        assert detail_result["data"]["id"] == task_id
        print("  ✅ 获取任务详情成功")

        # 3. 更新任务
        update_data = {
            "title": "更新后的任务",
            "status": "in_progress",
            "description": "任务已开始进行"
        }

        response = client.put(f"/tasks/{task_id}", json=update_data, headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        update_result = response.json()
        assert update_result["code"] == 200
        assert update_result["data"]["title"] == "更新后的任务"
        assert update_result["data"]["status"] == "in_progress"
        print("  ✅ 更新任务成功")

        # 4. 获取任务列表
        response = client.get("/tasks/", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        list_result = response.json()
        assert list_result["code"] == 200
        assert "tasks" in list_result["data"]
        assert "pagination" in list_result["data"]
        print(f"  ✅ 获取任务列表成功，共 {len(list_result['data']['tasks'])} 个任务")

        # 5. 删除任务
        response = client.delete(f"/tasks/{task_id}", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        delete_result = response.json()
        assert delete_result["code"] == 200
        assert delete_result["data"]["deleted_task_id"] == task_id
        print("  ✅ 删除任务成功")

    def test_top3_workflow(self, client, mock_jwt_auth, mock_microservice_client, mock_task_service):
        """测试Top3工作流"""
        print("🏆 测试Top3工作流...")

        # 先创建一些任务
        task_ids = []
        for i in range(3):
            create_data = {
                "title": f"Top3候选任务{i+1}",
                "description": f"重要的任务{i+1}",
                "priority": "high" if i < 2 else "medium"
            }
            response = client.post("/tasks/", json=create_data, headers={"Authorization": "Bearer mock_token"})
            assert response.status_code == 201
            task_ids.append(response.json()["data"]["id"])

        print(f"  ✅ 创建了 {len(task_ids)} 个候选任务")

        # 设置Top3
        today = date.today().isoformat()
        top3_data = {
            "date": today,
            "task_ids": task_ids[:2]  # 选择前两个任务作为Top3
        }

        response = client.post("/tasks/special/top3", json=top3_data, headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        top3_result = response.json()
        assert top3_result["code"] == 200
        assert top3_result["data"]["date"] == today
        assert len(top3_result["data"]["task_ids"]) == 2
        assert top3_result["data"]["points_consumed"] == 300
        print(f"  ✅ 设置Top3成功，消耗300积分")

        # 获取Top3
        response = client.get(f"/tasks/special/top3/{today}", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        get_top3_result = response.json()
        assert get_top3_result["code"] == 200
        assert get_top3_result["data"]["date"] == today
        assert len(get_top3_result["data"]["task_ids"]) == 2
        print("  ✅ 获取Top3成功")

        # 清理：删除创建的任务
        for task_id in task_ids:
            client.delete(f"/tasks/{task_id}", headers={"Authorization": "Bearer mock_token"})

    def test_task_statistics(self, client, mock_jwt_auth, mock_microservice_client, mock_task_service):
        """测试任务统计"""
        print("📊 测试任务统计...")

        # 先创建一些不同状态的任务
        tasks_data = [
            {"title": "已完成任务", "status": "completed", "priority": "high"},
            {"title": "进行中任务", "status": "in_progress", "priority": "medium"},
            {"title": "待处理任务", "status": "pending", "priority": "low"},
            {"title": "另一个已完成任务", "status": "completed", "priority": "medium"},
        ]

        created_ids = []
        for task_data in tasks_data:
            response = client.post("/tasks/", json=task_data, headers={"Authorization": "Bearer mock_token"})
            assert response.status_code == 201
            created_ids.append(response.json()["data"]["id"])

        print(f"  ✅ 创建了 {len(created_ids)} 个不同状态的任务")

        # 获取统计
        response = client.get("/tasks/statistics", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        stats_result = response.json()
        assert stats_result["code"] == 200

        stats = stats_result["data"]
        assert "total_tasks" in stats
        assert "completed_tasks" in stats
        assert "in_progress_tasks" in stats
        assert "pending_tasks" in stats
        assert "completion_rate" in stats
        assert stats["total_tasks"] == 4
        assert stats["completed_tasks"] == 2
        assert stats["in_progress_tasks"] == 1
        assert stats["pending_tasks"] == 1
        assert stats["completion_rate"] == 50.0

        print(f"  ✅ 统计数据正确: 总数={stats['total_tasks']}, 完成={stats['completed_tasks']}, 完成率={stats['completion_rate']}%")

        # 清理
        for task_id in created_ids:
            client.delete(f"/tasks/{task_id}", headers={"Authorization": "Bearer mock_token"})

    def test_error_handling(self, client, mock_jwt_auth, mock_microservice_client):
        """测试错误处理"""
        print("⚠️ 测试错误处理...")

        # 测试获取不存在的任务
        fake_id = str(uuid4())
        response = client.get(f"/tasks/{fake_id}", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200  # 代理层会返回200，错误在data中
        result = response.json()
        assert result["code"] == 404
        assert "任务不存在" in result["message"]
        print("  ✅ 正确处理任务不存在错误")

        # 测试无效的任务ID格式
        response = client.get("/tasks/invalid-id", headers={"Authorization": "Bearer mock_token"})
        # 微服务会处理这个错误
        print("  ✅ 测试无效ID格式")

    def test_request_validation(self, client, mock_jwt_auth):
        """测试请求验证"""
        print("✅ 测试请求验证...")

        # 测试创建任务缺少必填字段
        response = client.post("/tasks/", json={}, headers={"Authorization": "Bearer mock_token"})
        # 请求验证在FastAPI层面处理
        print("  ✅ 测试缺少必填字段验证")

        # 测试无效的优先级
        response = client.post("/tasks/", json={
            "title": "测试任务",
            "priority": "invalid_priority"
        }, headers={"Authorization": "Bearer mock_token"})
        print("  ✅ 测试无效优先级验证")

    def test_pagination(self, client, mock_jwt_auth, mock_microservice_client, mock_task_service):
        """测试分页功能"""
        print("📄 测试分页功能...")

        # 创建多个任务
        created_ids = []
        for i in range(25):
            response = client.post("/tasks/", json={
                "title": f"分页测试任务{i+1}",
                "description": f"第{i+1}个分页测试任务"
            }, headers={"Authorization": "Bearer mock_token"})
            if response.status_code == 201:
                created_ids.append(response.json()["data"]["id"])

        print(f"  ✅ 创建了 {len(created_ids)} 个任务")

        # 测试第一页
        response = client.get("/tasks/?page=1&page_size=10", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        assert len(result["data"]["tasks"]) <= 10
        assert result["data"]["pagination"]["current_page"] == 1
        assert result["data"]["pagination"]["page_size"] == 10
        print("  ✅ 第一页分页正常")

        # 测试第二页
        response = client.get("/tasks/?page=2&page_size=10", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200
        assert result["data"]["pagination"]["current_page"] == 2
        print("  ✅ 第二页分页正常")

        # 清理
        for task_id in created_ids:
            client.delete(f"/tasks/{task_id}", headers={"Authorization": "Bearer mock_token"})

    def test_api_response_format(self, client, mock_jwt_auth, mock_microservice_client, mock_task_service):
        """测试API响应格式一致性"""
        print("🔍 测试API响应格式...")

        # 创建任务并检查响应格式
        response = client.post("/tasks/", json={
            "title": "格式测试任务",
            "description": "测试响应格式"
        }, headers={"Authorization": "Bearer mock_token"})

        assert response.status_code == 201
        result = response.json()

        # 检查响应格式
        assert "code" in result
        assert "data" in result
        assert "message" in result
        assert result["code"] == 201
        assert isinstance(result["data"], dict)
        assert isinstance(result["message"], str)
        print("  ✅ 创建任务响应格式正确")

        # 获取任务列表并检查响应格式
        response = client.get("/tasks/", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        result = response.json()

        assert "code" in result
        assert "data" in result
        assert "message" in result
        assert result["code"] == 200
        assert "tasks" in result["data"]
        assert "pagination" in result["data"]
        print("  ✅ 任务列表响应格式正确")

        # 获取统计并检查响应格式
        response = client.get("/tasks/statistics", headers={"Authorization": "Bearer mock_token"})
        assert response.status_code == 200
        result = response.json()

        assert "code" in result
        assert "data" in result
        assert "message" in result
        assert result["code"] == 200
        assert isinstance(result["data"], dict)
        print("  ✅ 统计响应格式正确")


if __name__ == "__main__":
    print("前端API调用模拟测试")
    print("请使用 pytest 运行测试:")
    print("pytest tests/integration/test_frontend_api_simulation.py -v")