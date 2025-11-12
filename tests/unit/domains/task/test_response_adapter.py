"""
Task响应数据适配器单元测试

测试src/domains/task/router.py中的数据适配逻辑:
- adapt_single_task_data(): 单个任务数据转换
- adapt_microservice_response_to_client(): 微服务响应适配

覆盖场景:
1. 状态映射: NOT_STARTED → pending, IN_PROGRESS → in_progress等
2. 优先级映射: HIGH → high, MEDIUM → medium等
3. 缺失字段添加: completion_percentage等
4. 多种响应格式: 单个任务、任务数组、分页任务列表

作者: TaKeKe团队
版本: 1.0.0
"""
import pytest
from datetime import datetime
from src.domains.task.router import adapt_single_task_data, adapt_microservice_response_to_client


class TestAdaptSingleTaskData:
    """测试单个任务数据适配函数"""

    # ===== 状态映射测试 =====

    def test_adapt_single_task_status_not_started(self):
        """测试状态转换: NOT_STARTED → pending"""
        task_data = {
            "id": "task_123",
            "title": "Test Task",
            "status": "NOT_STARTED"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["status"] == "pending"

    def test_adapt_single_task_status_in_progress_uppercase(self):
        """测试状态转换: IN_PROGRESS → in_progress"""
        task_data = {
            "id": "task_123",
            "status": "IN_PROGRESS"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["status"] == "in_progress"

    def test_adapt_single_task_status_todo(self):
        """测试状态转换: TODO → pending"""
        task_data = {
            "id": "task_123",
            "status": "TODO"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["status"] == "pending"

    def test_adapt_single_task_status_completed(self):
        """测试状态转换: COMPLETED → completed"""
        task_data = {
            "id": "task_123",
            "status": "COMPLETED"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["status"] == "completed"

    def test_adapt_single_task_status_lowercase_passthrough(self):
        """测试小写状态直接透传"""
        task_data = {
            "id": "task_123",
            "status": "pending"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["status"] == "pending"

    # ===== 优先级映射测试 =====

    def test_adapt_single_task_priority_high_uppercase(self):
        """测试优先级转换: HIGH → high"""
        task_data = {
            "id": "task_123",
            "priority": "HIGH"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["priority"] == "high"

    def test_adapt_single_task_priority_medium_uppercase(self):
        """测试优先级转换: MEDIUM → medium"""
        task_data = {
            "id": "task_123",
            "priority": "MEDIUM"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["priority"] == "medium"

    def test_adapt_single_task_priority_low_uppercase(self):
        """测试优先级转换: LOW → low"""
        task_data = {
            "id": "task_123",
            "priority": "LOW"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["priority"] == "low"

    def test_adapt_single_task_priority_capitalized(self):
        """测试优先级转换: High → high"""
        task_data = {
            "id": "task_123",
            "priority": "High"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["priority"] == "high"

    def test_adapt_single_task_priority_lowercase_passthrough(self):
        """测试小写优先级直接透传"""
        task_data = {
            "id": "task_123",
            "priority": "high"
        }
        adapted = adapt_single_task_data(task_data)
        assert adapted["priority"] == "high"

    # ===== 缺失字段添加测试 =====

    def test_adapt_single_task_adds_completion_percentage(self):
        """测试添加completion_percentage字段"""
        task_data = {
            "id": "task_123",
            "title": "Test Task"
        }
        adapted = adapt_single_task_data(task_data)
        assert "completion_percentage" in adapted
        assert adapted["completion_percentage"] == 0.0

    def test_adapt_single_task_adds_parent_id(self):
        """测试添加parent_id字段"""
        task_data = {
            "id": "task_123"
        }
        adapted = adapt_single_task_data(task_data)
        assert "parent_id" in adapted
        assert adapted["parent_id"] is None

    def test_adapt_single_task_adds_tags(self):
        """测试添加tags字段"""
        task_data = {
            "id": "task_123"
        }
        adapted = adapt_single_task_data(task_data)
        assert "tags" in adapted
        assert adapted["tags"] == []

    def test_adapt_single_task_adds_service_ids(self):
        """测试添加service_ids字段"""
        task_data = {
            "id": "task_123"
        }
        adapted = adapt_single_task_data(task_data)
        assert "service_ids" in adapted
        assert adapted["service_ids"] == []

    def test_adapt_single_task_adds_all_required_fields(self):
        """测试添加所有必需字段"""
        task_data = {
            "id": "task_123",
            "title": "Test Task"
        }
        adapted = adapt_single_task_data(task_data)

        # 验证所有必需字段都存在
        required_fields = [
            "parent_id",
            "tags",
            "service_ids",
            "planned_start_time",
            "planned_end_time",
            "last_claimed_date",
            "is_deleted",
            "completion_percentage"
        ]
        for field in required_fields:
            assert field in adapted, f"缺少必需字段: {field}"

    # ===== 保留现有字段测试 =====

    def test_adapt_single_task_preserves_existing_fields(self):
        """测试保留原有字段"""
        task_data = {
            "id": "task_123",
            "title": "Test Task",
            "description": "Test Description",
            "user_id": "user_456",
            "created_at": "2025-11-12T00:00:00",
            "updated_at": "2025-11-12T00:00:00"
        }
        adapted = adapt_single_task_data(task_data)

        assert adapted["id"] == "task_123"
        assert adapted["title"] == "Test Task"
        assert adapted["description"] == "Test Description"
        assert adapted["user_id"] == "user_456"
        assert adapted["created_at"] == "2025-11-12T00:00:00"
        assert adapted["updated_at"] == "2025-11-12T00:00:00"

    def test_adapt_single_task_preserves_existing_tags(self):
        """测试保留原有的tags"""
        task_data = {
            "id": "task_123",
            "tags": ["important", "urgent"]
        }
        adapted = adapt_single_task_data(task_data)

        # 不应该被覆盖为空数组
        assert adapted["tags"] == ["important", "urgent"]

    # ===== 参数化测试 =====

    @pytest.mark.parametrize("input_status,expected_status", [
        ("NOT_STARTED", "pending"),
        ("TODO", "pending"),
        ("todo", "pending"),
        ("pending", "pending"),
        ("IN_PROGRESS", "in_progress"),
        ("inprogress", "in_progress"),
        ("in_progress", "in_progress"),
        ("COMPLETED", "completed"),
        ("completed", "completed"),
    ])
    def test_status_mapping_all_variants(self, input_status, expected_status):
        """参数化测试所有状态映射变体"""
        task_data = {"id": "task_123", "status": input_status}
        adapted = adapt_single_task_data(task_data)
        assert adapted["status"] == expected_status

    @pytest.mark.parametrize("input_priority,expected_priority", [
        ("HIGH", "high"),
        ("High", "high"),
        ("high", "high"),
        ("MEDIUM", "medium"),
        ("Medium", "medium"),
        ("medium", "medium"),
        ("LOW", "low"),
        ("Low", "low"),
        ("low", "low"),
    ])
    def test_priority_mapping_all_variants(self, input_priority, expected_priority):
        """参数化测试所有优先级映射变体"""
        task_data = {"id": "task_123", "priority": input_priority}
        adapted = adapt_single_task_data(task_data)
        assert adapted["priority"] == expected_priority


class TestAdaptMicroserviceResponse:
    """测试微服务响应适配函数"""

    # ===== 单个任务格式测试 =====

    def test_adapt_response_single_task_basic(self):
        """测试单个任务格式: {"data": {"id": "xxx"}}"""
        response_data = {
            "code": 200,
            "message": "success",
            "data": {
                "id": "task_123",
                "title": "Test Task",
                "status": "NOT_STARTED",
                "priority": "HIGH"
            }
        }
        adapted = adapt_microservice_response_to_client(response_data)

        assert adapted["data"]["status"] == "pending"
        assert adapted["data"]["priority"] == "high"
        assert "completion_percentage" in adapted["data"]

    def test_adapt_response_single_task_with_all_fields(self):
        """测试单个任务包含所有字段"""
        response_data = {
            "code": 200,
            "data": {
                "id": "task_123",
                "title": "Test Task",
                "description": "Test Description",
                "status": "IN_PROGRESS",
                "priority": "MEDIUM",
                "user_id": "user_456",
                "tags": ["test"],
                "created_at": "2025-11-12T00:00:00",
                "updated_at": "2025-11-12T00:00:00"
            }
        }
        adapted = adapt_microservice_response_to_client(response_data)

        assert adapted["data"]["status"] == "in_progress"
        assert adapted["data"]["priority"] == "medium"
        assert adapted["data"]["tags"] == ["test"]
        assert "completion_percentage" in adapted["data"]

    # ===== 任务数组格式测试 =====

    def test_adapt_response_task_list_array(self):
        """测试任务数组格式: {"data": [{"id": "xxx"}]}"""
        response_data = {
            "code": 200,
            "message": "success",
            "data": [
                {"id": "task_1", "status": "NOT_STARTED", "priority": "HIGH"},
                {"id": "task_2", "status": "IN_PROGRESS", "priority": "MEDIUM"}
            ]
        }
        adapted = adapt_microservice_response_to_client(response_data)

        # 应该被包装成分页格式
        assert "tasks" in adapted["data"]
        assert "pagination" in adapted["data"]
        assert len(adapted["data"]["tasks"]) == 2

        # 验证每个任务都被正确适配
        assert adapted["data"]["tasks"][0]["status"] == "pending"
        assert adapted["data"]["tasks"][0]["priority"] == "high"
        assert adapted["data"]["tasks"][1]["status"] == "in_progress"
        assert adapted["data"]["tasks"][1]["priority"] == "medium"

    def test_adapt_response_task_list_array_pagination(self):
        """测试任务数组被包装的分页信息"""
        response_data = {
            "code": 200,
            "data": [
                {"id": f"task_{i}", "status": "NOT_STARTED", "priority": "HIGH"}
                for i in range(5)
            ]
        }
        adapted = adapt_microservice_response_to_client(response_data)

        pagination = adapted["data"]["pagination"]
        assert pagination["current_page"] == 1
        assert pagination["page_size"] == 5
        assert pagination["total_count"] == 5
        assert pagination["total_pages"] == 1
        assert pagination["has_next"] is False
        assert pagination["has_prev"] is False

    # ===== 分页任务列表格式测试（关键!）=====

    def test_adapt_response_task_list_paginated(self):
        """测试分页任务列表格式: {"data": {"tasks": [...], "total": N}} - 本次bug的关键测试"""
        response_data = {
            "code": 200,
            "message": "success",
            "data": {
                "tasks": [
                    {"id": "task_1", "title": "Task 1", "status": "NOT_STARTED", "priority": "HIGH"},
                    {"id": "task_2", "title": "Task 2", "status": "IN_PROGRESS", "priority": "MEDIUM"},
                    {"id": "task_3", "title": "Task 3", "status": "COMPLETED", "priority": "LOW"}
                ],
                "total": 10,
                "limit": 3,
                "offset": 0
            }
        }
        adapted = adapt_microservice_response_to_client(response_data)

        # 验证tasks被正确适配
        assert "tasks" in adapted["data"]
        assert len(adapted["data"]["tasks"]) == 3

        # 验证每个任务的数据被正确转换
        assert adapted["data"]["tasks"][0]["status"] == "pending"  # NOT_STARTED → pending
        assert adapted["data"]["tasks"][0]["priority"] == "high"   # HIGH → high
        assert adapted["data"]["tasks"][1]["status"] == "in_progress"  # IN_PROGRESS → in_progress
        assert adapted["data"]["tasks"][1]["priority"] == "medium"     # MEDIUM → medium
        assert adapted["data"]["tasks"][2]["status"] == "completed"
        assert adapted["data"]["tasks"][2]["priority"] == "low"

        # 验证completion_percentage被添加
        for task in adapted["data"]["tasks"]:
            assert "completion_percentage" in task
            assert task["completion_percentage"] == 0.0

    def test_adapt_response_paginated_list_pagination_info(self):
        """测试分页任务列表的分页信息计算"""
        response_data = {
            "code": 200,
            "data": {
                "tasks": [
                    {"id": f"task_{i}", "status": "NOT_STARTED", "priority": "HIGH"}
                    for i in range(10)
                ],
                "total": 100,
                "limit": 10,
                "offset": 20  # 第3页
            }
        }
        adapted = adapt_microservice_response_to_client(response_data)

        pagination = adapted["data"]["pagination"]
        assert pagination["current_page"] == 3  # offset=20, limit=10 → page 3
        assert pagination["page_size"] == 10
        assert pagination["total_count"] == 100
        assert pagination["total_pages"] == 10  # 100/10 = 10页
        assert pagination["has_next"] is True   # 第3页，还有后续页
        assert pagination["has_prev"] is True   # 第3页，有前面的页

    def test_adapt_response_paginated_list_first_page(self):
        """测试分页列表的第一页"""
        response_data = {
            "code": 200,
            "data": {
                "tasks": [{"id": "task_1", "status": "NOT_STARTED", "priority": "HIGH"}],
                "total": 50,
                "limit": 10,
                "offset": 0  # 第1页
            }
        }
        adapted = adapt_microservice_response_to_client(response_data)

        pagination = adapted["data"]["pagination"]
        assert pagination["current_page"] == 1
        assert pagination["has_next"] is True   # 有下一页
        assert pagination["has_prev"] is False  # 没有上一页

    def test_adapt_response_paginated_list_last_page(self):
        """测试分页列表的最后一页"""
        response_data = {
            "code": 200,
            "data": {
                "tasks": [{"id": "task_1", "status": "NOT_STARTED", "priority": "HIGH"}],
                "total": 25,
                "limit": 10,
                "offset": 20  # 第3页（最后一页）
            }
        }
        adapted = adapt_microservice_response_to_client(response_data)

        pagination = adapted["data"]["pagination"]
        assert pagination["current_page"] == 3
        assert pagination["total_pages"] == 3
        assert pagination["has_next"] is False  # 没有下一页
        assert pagination["has_prev"] is True   # 有上一页

    # ===== 空列表测试 =====

    def test_adapt_response_empty_task_list_array(self):
        """测试空任务数组"""
        response_data = {
            "code": 200,
            "data": []
        }
        adapted = adapt_microservice_response_to_client(response_data)

        assert adapted["data"]["tasks"] == []
        assert adapted["data"]["pagination"]["total_count"] == 0

    def test_adapt_response_empty_task_list_paginated(self):
        """测试空分页任务列表"""
        response_data = {
            "code": 200,
            "data": {
                "tasks": [],
                "total": 0,
                "limit": 10,
                "offset": 0
            }
        }
        adapted = adapt_microservice_response_to_client(response_data)

        assert adapted["data"]["tasks"] == []
        assert adapted["data"]["pagination"]["total_count"] == 0
        assert adapted["data"]["pagination"]["current_page"] == 1

    # ===== 边界情况测试 =====

    def test_adapt_response_preserves_code_and_message(self):
        """测试保留code和message字段"""
        response_data = {
            "code": 201,
            "message": "created successfully",
            "data": {"id": "task_123", "status": "NOT_STARTED", "priority": "HIGH"}
        }
        adapted = adapt_microservice_response_to_client(response_data)

        assert adapted["code"] == 201
        assert adapted["message"] == "created successfully"

    def test_adapt_response_no_data_field(self):
        """测试没有data字段的响应"""
        response_data = {
            "code": 404,
            "message": "not found"
        }
        adapted = adapt_microservice_response_to_client(response_data)

        # 应该保持原样
        assert adapted == response_data

    def test_adapt_response_data_is_none(self):
        """测试data为None的响应"""
        response_data = {
            "code": 500,
            "message": "error",
            "data": None
        }
        adapted = adapt_microservice_response_to_client(response_data)

        # 应该保持原样
        assert adapted["data"] is None
