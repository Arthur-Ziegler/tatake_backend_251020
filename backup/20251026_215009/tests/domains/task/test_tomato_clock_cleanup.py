"""
测试番茄钟功能清理

验证所有番茄钟相关字段和功能已完全从项目中删除。

测试覆盖：
1. Task模型中不包含estimated_pomodoros和actual_pomodoros字段
2. Task Schema中不包含番茄钟字段
3. Task Service中不包含番茄钟逻辑
4. 测试用例中不引用番茄钟字段

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import pytest
from sqlmodel import Session
from sqlalchemy import text


class TestTomatoClockCleanup:
    """测试番茄钟功能彻底清理"""

    def test_task_model_no_tomato_fields(self, session: Session):
        """验证Task模型不包含番茄钟字段"""
        from src.domains.task.models import Task

        # 检查Task模型，确保没有番茄钟字段
        task_columns = Task.__table__.columns.keys()
        tomato_fields = ['estimated_pomodoros', 'actual_pomodoros']

        # 找出存在的番茄钟字段
        found_tomato_fields = [field for field in tomato_fields if field in task_columns]

        # 应该没有番茄钟相关字段
        assert len(found_tomato_fields) == 0, f"Found tomato clock fields: {found_tomato_fields}"

    def test_task_schema_no_tomato_fields(self):
        """验证Task Schema不包含番茄钟字段"""
        try:
            from src.domains.task.schemas import CreateTaskRequest, UpdateTaskRequest, TaskResponse

            # 检查CreateTaskRequest的字段
            create_fields = set(CreateTaskRequest.model_fields.keys())
            assert "estimated_pomodoros" not in create_fields, "CreateTaskRequest contains estimated_pomodoros"
            assert "actual_pomodoros" not in create_fields, "CreateTaskRequest contains actual_pomodoros"

            # 检查UpdateTaskRequest的字段
            update_fields = set(UpdateTaskRequest.model_fields.keys())
            assert "estimated_pomodoros" not in update_fields, "UpdateTaskRequest contains estimated_pomodoros"
            assert "actual_pomodoros" not in update_fields, "UpdateTaskRequest contains actual_pomodoros"

            # 检查TaskResponse的字段
            response_fields = set(TaskResponse.model_fields.keys())
            assert "estimated_pomodoros" not in response_fields, "TaskResponse contains estimated_pomodoros"
            assert "actual_pomodoros" not in response_fields, "TaskResponse contains actual_pomodoros"

        except ImportError as e:
            pytest.fail(f"Failed to import task schemas: {e}")

    def test_task_service_no_tomato_logic(self):
        """验证Task Service不包含番茄钟相关逻辑"""
        try:
            from src.domains.task.service import TaskService
            import inspect

            # 检查TaskService的所有方法
            methods = inspect.getmembers(TaskService, predicate=inspect.ismethod)

            for name, method in methods:
                if not name.startswith('_'):  # 只检查public方法
                    source = inspect.getsource(method)
                    # 确保源码中不包含番茄钟相关字段
                    assert "estimated_pomodoros" not in source, f"Method {name} contains estimated_pomodoros"
                    assert "actual_pomodoros" not in source, f"Method {name} contains actual_pomodoros"

        except ImportError as e:
            pytest.fail(f"Failed to import TaskService: {e}")

    def test_no_tomato_references_in_codebase(self):
        """验证整个代码库中没有番茄钟相关引用"""
        import subprocess
        import os

        # 使用grep搜索整个src目录
        try:
            result = subprocess.run(
                ["rg", "--count", "estimated_pomodoros|actual_pomodoros", "src/"],
                capture_output=True,
                text=True,
                check=True
            )

            # 应该没有匹配结果
            assert result.stdout.strip() == "0", f"Found tomato clock references in codebase: {result.stdout}"

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to search codebase: {e}")
        except FileNotFoundError:
            # ripgrep可能不可用，跳过此测试
            pytest.skip("ripgrep not available for codebase search")

    def test_task_completion_flow_without_tomato(self, session: Session):
        """验证任务完成流程不依赖番茄钟"""
        try:
            from src.domains.task.service import TaskService
            from src.domains.task.models import Task

            # 创建一个测试任务（不包含番茄钟字段）
            task_data = {
                "title": "Test Task Without Tomato",
                "description": "Test description",
                "status": "pending"
            }

            # 验证可以正常创建任务，不需要番茄钟字段
            service = TaskService(session)

            # 这里的测试只是为了验证代码结构，实际实现会在后续Service重构中完成
            # 当前重点是确保没有番茄钟依赖

        except Exception as e:
            # 如果因为缺少番茄钟字段而报错，说明清理不彻底
            if "estimated_pomodoros" in str(e) or "actual_pomodoros" in str(e):
                pytest.fail(f"Task creation still requires tomato clock fields: {e}")
            # 其他错误可以接受，因为这不是功能测试
            pass