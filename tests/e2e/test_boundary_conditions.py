"""
边界条件和错误场景测试

测试系统在各种边界条件和异常情况下的行为。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4
import time


@pytest.mark.integration
@pytest.mark.boundary
class TestInputBoundaryConditions:
    """输入边界条件测试类"""

    @pytest.mark.parametrize(
        "title,description,should_succeed",
        [
            ("A", "最短标题", True),
            ("A" * 200, "最大长度标题测试", True),
            ("", "空标题", False),
            ("A" * 201, "超长标题测试", False),
        ],
        ids=["min_title", "max_title", "empty_title", "too_long_title"]
    )
    def test_task_title_boundary(self, test_db_session, title, description, should_succeed):
        """测试任务标题长度边界"""
        from src.domains.task.service import TaskService
        from src.domains.task.schemas import TaskCreate

        task_service = TaskService(test_db_session)
        user_id = str(uuid4())

        task_data = TaskCreate(
            title=title,
            description=description,
            priority="medium",
            tags=[]
        )

        if should_succeed:
            task = task_service.create_task(user_id, task_data)
            assert task is not None
            assert task.title == title
        else:
            with pytest.raises((ValueError, Exception)):
                task_service.create_task(user_id, task_data)

    @pytest.mark.parametrize(
        "points_amount",
        [1, 10000, 0, -1, 999999],
        ids=["min_positive", "max_positive", "zero", "negative", "extreme"]
    )
    def test_points_transaction_boundary(self, test_db_session, points_amount):
        """测试积分交易边界条件"""
        from src.domains.points.service import PointsService

        points_service = PointsService(test_db_session)
        user_id = str(uuid4())

        if points_amount > 0:
            result = points_service.add_points(user_id, points_amount, "test")
            assert result is not None
            final_balance = points_service.get_balance(user_id)
            assert final_balance == points_amount
        elif points_amount == 0:
            result = points_service.add_points(user_id, points_amount, "test")
            assert result is not None
            final_balance = points_service.get_balance(user_id)
            assert final_balance == 0
        else:
            # 负积分应该被允许（扣除积分）
            points_service.add_points(user_id, 1000, "initial")
            result = points_service.add_points(user_id, points_amount, "test")
            final_balance = points_service.get_balance(user_id)
            assert final_balance == 1000 + points_amount


@pytest.mark.integration
@pytest.mark.boundary
class TestResourceBoundaryConditions:
    """资源边界条件测试类"""

    def test_memory_usage_boundary(self, test_db_session):
        """测试内存使用边界条件"""
        from src.domains.task.service import TaskService
        from src.domains.task.schemas import TaskCreate

        task_service = TaskService(test_db_session)
        user_id = str(uuid4())

        # 创建大量任务测试内存边界
        task_count = 50
        tasks = []

        for i in range(task_count):
            task_data = TaskCreate(
                title=f"内存测试任务{i+1}",
                description=f"内存测试任务描述{i+1}",
                priority="medium",
                tags=[f"tag{i}", f"memory_test", f"batch{i//10}"]
            )
            task = task_service.create_task(user_id, task_data)
            tasks.append(task)

        # 验证所有任务都成功创建
        assert len(tasks) == task_count

        # 验证可以查询任务列表
        task_list = task_service.get_user_tasks(user_id, limit=50)
        assert len(task_list) <= 50
        assert all(task.user_id == user_id for task in task_list)

    def test_concurrent_operation_boundary(self, test_db_session):
        """测试并发操作边界条件"""
        import threading
        from src.domains.points.service import PointsService
        from src.domains.task.service import TaskService

        points_service = PointsService(test_db_session)
        task_service = TaskService(test_db_session)
        user_id = str(uuid4())

        # 给用户初始积分
        points_service.add_points(user_id, 1000, "initial")

        results = []
        errors = []

        def worker_task(worker_id):
            """工作线程任务"""
            try:
                from src.domains.task.schemas import TaskCreate
                task_data = TaskCreate(
                    title=f"并发任务-{worker_id}",
                    description=f"并发测试任务-{worker_id}",
                    priority="medium"
                )
                task = task_service.create_task(user_id, task_data)

                # 扣除积分
                points_service.add_points(user_id, -10, f"concurrent_test_{worker_id}")

                results.append((worker_id, task.id, "success"))
            except Exception as e:
                errors.append((worker_id, str(e)))

        # 创建多个并发线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_task, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=5)

        # 验证结果
        assert len(results) + len(errors) == 10
        assert len(results) >= 8

        # 验证最终积分余额
        final_balance = points_service.get_balance(user_id)
        assert final_balance >= 0


@pytest.mark.integration
@pytest.mark.boundary
class TestErrorRecoveryBoundary:
    """错误恢复边界测试类"""

    @pytest.mark.parametrize(
        "error_scenario,recovery_strategy",
        [
            ("insufficient_points", "add_points"),
            ("task_not_found", "create_new"),
            ("top3_exists", "update_existing"),
        ],
        ids=["points_recovery", "task_recovery", "top3_recovery"]
    )
    def test_error_recovery_scenarios(self, test_db_session, error_scenario, recovery_strategy):
        """测试各种错误恢复场景"""
        from src.domains.points.service import PointsService
        from src.domains.task.service import TaskService
        from src.domains.top3.service import Top3Service
        from src.domains.task.schemas import TaskCreate
        from src.domains.top3.schemas import SetTop3Request

        points_service = PointsService(test_db_session)
        task_service = TaskService(test_db_session)
        top3_service = Top3Service(test_db_session)
        user_id = str(uuid4())

        # 根据不同场景设置初始条件
        if error_scenario == "insufficient_points":
            pass
        elif error_scenario == "task_not_found":
            fake_task_id = str(uuid4())
        elif error_scenario == "top3_exists":
            points_service.add_points(user_id, 1000, "initial")
            task_data = TaskCreate(title="已有任务", description="测试", priority="medium")
            task = task_service.create_task(user_id, task_data)
            request = SetTop3Request(date=date.today().isoformat(), task_ids=[str(task.id)])
            top3_service.set_top3(user_id, request)

        # 执行可能失败的操作
        try:
            if error_scenario == "insufficient_points":
                task_data = TaskCreate(title="积分测试", description="测试", priority="medium")
                task = task_service.create_task(user_id, task_data)
                request = SetTop3Request(date=date.today().isoformat(), task_ids=[str(task.id)])
                top3_service.set_top3(user_id, request)

            elif error_scenario == "task_not_found":
                task_service.get_task_by_id(user_id, fake_task_id)

            elif error_scenario == "top3_exists":
                task_data = TaskCreate(title="重复任务", description="测试", priority="medium")
                task = task_service.create_task(user_id, task_data)
                request = SetTop3Request(date=date.today().isoformat(), task_ids=[str(task.id)])
                top3_service.set_top3(user_id, request)

            # 如果没有异常，说明测试需要调整
            pytest.fail(f"错误场景 {error_scenario} 没有按预期失败")

        except Exception as e:
            if error_scenario == "insufficient_points" and recovery_strategy == "add_points":
                # 恢复策略：添加积分
                points_service.add_points(user_id, 500, "recovery")
                # 重试操作
                task_data = TaskCreate(title="恢复任务", description="恢复测试", priority="medium")
                task = task_service.create_task(user_id, task_data)
                request = SetTop3Request(date=date.today().isoformat(), task_ids=[str(task.id)])
                result = top3_service.set_top3(user_id, request)
                assert result is not None

            # 验证系统状态仍然合理
            current_balance = points_service.get_balance(user_id)
            assert current_balance >= 0


@pytest.mark.integration
@pytest.mark.boundary
class TestExtremeConditions:
    """极端条件测试类"""

    def test_high_volume_operations(self, test_db_session):
        """测试高容量操作"""
        from src.domains.task.service import TaskService
        from src.domains.points.service import PointsService
        from src.domains.task.schemas import TaskCreate

        task_service = TaskService(test_db_session)
        points_service = PointsService(test_db_session)
        user_id = str(uuid4())

        # 给用户大量积分
        points_service.add_points(user_id, 5000, "bulk_test")

        # 批量创建任务
        batch_size = 25
        created_tasks = []

        start_time = time.time()

        for batch_start in range(0, 100, batch_size):
            batch_tasks = []
            for i in range(batch_size):
                task_data = TaskCreate(
                    title=f"高容量测试任务{batch_start + i + 1}",
                    description=f"批量测试任务{batch_start + i + 1}",
                    priority="medium"
                )
                try:
                    task = task_service.create_task(user_id, task_data)
                    batch_tasks.append(task)
                except Exception as e:
                    print(f"批量创建失败: {e}")

            created_tasks.extend(batch_tasks)

            # 每50个任务后检查性能
            if batch_start % 50 == 0:
                elapsed = time.time() - start_time
                print(f"已创建 {len(created_tasks)} 个任务，耗时 {elapsed:.2f}s")

                if elapsed > 10:
                    pytest.fail(f"高容量操作性能不佳：{len(created_tasks)}个任务耗时{elapsed:.2f}s")

        end_time = time.time()
        total_time = end_time - start_time

        # 验证结果
        assert len(created_tasks) >= 75
        assert total_time < 20
        print(f"高容量测试完成：{len(created_tasks)}个任务，总耗时{total_time:.2f}s")

        # 验证查询性能
        query_start = time.time()
        user_tasks = task_service.get_user_tasks(user_id, limit=100)
        query_time = time.time() - query_start

        assert query_time < 5
        assert len(user_tasks) <= 100

    def test_extreme_data_sizes(self, test_db_session):
        """测试极端数据大小"""
        from src.domains.task.service import TaskService
        from src.domains.task.schemas import TaskCreate

        task_service = TaskService(test_db_session)
        user_id = str(uuid4())

        # 测试极端大小的数据
        extreme_cases = [
            ("超长标题", "A" * 199, "正常描述"),
            ("超长描述", "正常标题", "B" * 800),
        ]

        for case_name, title, description in extreme_cases:
            try:
                task_data = TaskCreate(
                    title=title,
                    description=description,
                    priority="medium",
                    tags=[]
                )

                task = task_service.create_task(user_id, task_data)
                assert task is not None
                assert len(task.title) <= 200
                print(f"极端数据测试 {case_name}: 成功")

            except Exception as e:
                print(f"极端数据测试 {case_name}: 被拒绝 - {e}")
                assert "长度" in str(e) or "大小" in str(e)

    def test_concurrent_boundary_pressure(self, test_db_session):
        """测试并发边界压力"""
        import threading
        import time

        from src.domains.task.service import TaskService
        from src.domains.points.service import PointsService
        from src.domains.task.schemas import TaskCreate

        task_service = TaskService(test_db_session)
        points_service = PointsService(test_db_session)

        # 创建多个用户进行并发测试
        user_count = 3
        operations_per_user = 10
        users = [str(uuid4()) for _ in range(user_count)]

        # 给每个用户积分
        for user_id in users:
            points_service.add_points(user_id, 500, "concurrent_test")

        results = []
        errors = []

        def user_worker(user_id, worker_id):
            """用户工作线程"""
            try:
                for i in range(operations_per_user):
                    task_data = TaskCreate(
                        title=f"并发测试-用户{worker_id}-任务{i+1}",
                        description=f"并发测试任务描述",
                        priority="medium"
                    )

                    # 创建任务
                    task = task_service.create_task(user_id, task_data)

                    # 扣除少量积分
                    points_service.add_points(user_id, -5, f"concurrent_{worker_id}_{i}")

                    results.append((user_id, worker_id, i, "success"))

                    # 添加小的随机延迟
                    time.sleep(0.001)

            except Exception as e:
                errors.append((user_id, worker_id, str(e)))

        # 启动所有工作线程
        start_time = time.time()
        threads = []

        for i, user_id in enumerate(users):
            thread = threading.Thread(target=user_worker, args=(user_id, i))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=10)

        end_time = time.time()
        total_time = end_time - start_time

        # 收集和分析结果
        success_count = len(results)
        total_operations = user_count * operations_per_user
        success_rate = success_count / total_operations if total_operations > 0 else 0

        # 验证并发测试结果
        assert success_rate >= 0.8
        assert total_time < 20
        assert len(errors) < total_operations * 0.2

        print(f"并发压力测试完成：{success_count}/{total_operations} 成功 ({success_rate:.1%})，耗时 {total_time:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])