"""
任务域UUID统一化测试

测试任务域中UUID类型的统一使用，确保：
1. 模型层统一使用UUID对象
2. 服务层内部使用UUID对象
3. API边界层正确转换UUID对象与字符串
4. 数据库层正确处理UUID存储

测试策略：
- TDD：先写测试，再实现
- 边界覆盖：覆盖所有UUID转换边界
- 类型安全：确保运行时类型正确性
- 集成测试：验证跨层UUID处理
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Dict, Any
from sqlalchemy import inspect

from sqlmodel import create_engine, Session
from sqlalchemy.pool import StaticPool

from src.domains.task.models import Task
from src.core.uuid_converter import UUIDConverter


class TestUUIDUnification:
    """UUID统一化测试套件"""

    @pytest.fixture
    def in_memory_db(self):
        """内存数据库fixture"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        return engine

    @pytest.fixture
    def db_session(self, in_memory_db):
        """数据库会话fixture"""
        Task.metadata.create_all(in_memory_db)
        with Session(in_memory_db) as session:
            yield session

    @pytest.fixture
    def sample_user_id(self):
        """示例用户ID fixture"""
        return uuid4()

    def test_task_model_uuid_fields(self, sample_user_id):
        """测试Task模型使用UUID类型字段"""
        # Act: 创建Task对象
        task = Task(
            user_id=sample_user_id,
            title="测试任务",
            description="测试描述",
            status="pending",
            priority="medium"
        )

        # Assert: 验证字段类型
        assert isinstance(task.id, UUID)
        assert isinstance(task.user_id, UUID)
        assert task.user_id == sample_user_id
        # ID应该自动生成，不等于sample_user_id
        assert task.id != sample_user_id

    def test_task_factory_uuid_creation(self, sample_user_id):
        """测试Task工厂方法UUID创建"""
        # Act: 使用工厂方法创建
        task = Task.create_example(sample_user_id)

        # Assert: 验证UUID类型
        assert isinstance(task.id, UUID)
        assert isinstance(task.user_id, UUID)
        assert task.title == "示例任务"
        assert task.status == "pending"

    def test_task_string_uuid_conversion_at_boundary(self, sample_user_id):
        """测试在边界层进行UUID字符串转换"""
        # Arrange: 创建UUID对象
        uuid_obj = sample_user_id
        uuid_str = str(uuid_obj)

        # Act & Assert: 测试转换器
        converted_uuid = UUIDConverter.ensure_uuid(uuid_str)
        assert isinstance(converted_uuid, UUID)
        assert converted_uuid == uuid_obj

        # Act & Assert: 测试反转换
        converted_str = UUIDConverter.ensure_string(uuid_obj)
        assert isinstance(converted_str, str)
        assert converted_str == uuid_str

    def test_task_model_persistence_with_uuid(self, db_session, sample_user_id):
        """测试Task模型UUID持久化"""
        # Arrange: 创建Task对象
        task = Task(
            id=sample_user_id,
            user_id=sample_user_id,
            title="持久化测试任务",
            description="测试数据库持久化",
            status="pending",
            priority="high"
        )

        # Act: 保存到数据库
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert: 验证UUID类型保持
        assert isinstance(task.id, UUID)
        assert isinstance(task.user_id, UUID)
        assert task.id == sample_user_id
        assert task.user_id == sample_user_id

    def test_task_query_by_uuid(self, db_session, sample_user_id):
        """测试使用UUID查询任务"""
        # Arrange: 创建并保存任务
        task = Task.create_example(sample_user_id)
        db_session.add(task)
        db_session.commit()

        # Act: 使用任务的实际ID查询
        from sqlmodel import select
        statement = select(Task).where(Task.id == task.id)
        queried_task = db_session.exec(statement).first()

        # Assert: 验证查询结果
        assert queried_task is not None
        assert isinstance(queried_task.id, UUID)
        assert isinstance(queried_task.user_id, UUID)
        assert queried_task.id == task.id
        assert queried_task.user_id == sample_user_id

    def test_uuid_conversion_safety(self):
        """测试UUID转换的安全性"""
        # Arrange: 测试各种输入
        valid_uuid = uuid4()
        valid_uuid_str = str(valid_uuid)
        invalid_uuid_str = "invalid-uuid"
        none_value = None
        number_value = 123

        # Act & Assert: 有效UUID转换
        assert UUIDConverter.ensure_uuid(valid_uuid) == valid_uuid
        assert UUIDConverter.ensure_uuid(valid_uuid_str) == valid_uuid

        # Act & Assert: 有效字符串转换
        assert UUIDConverter.ensure_string(valid_uuid) == valid_uuid_str
        assert UUIDConverter.ensure_string(valid_uuid_str) == valid_uuid_str

        # Act & Assert: 无效输入处理
        with pytest.raises((TypeError, ValueError)):
            UUIDConverter.ensure_uuid(invalid_uuid_str)

        with pytest.raises((TypeError, ValueError)):
            UUIDConverter.ensure_uuid(none_value)

        with pytest.raises((TypeError, ValueError)):
            UUIDConverter.ensure_uuid(number_value)

    def test_task_relationship_uuid_compatibility(self, db_session, sample_user_id):
        """测试任务关系中UUID的兼容性"""
        # Arrange: 创建父任务和子任务
        parent_task = Task.create_example(
            sample_user_id,
            title="父任务",
            description="这是一个父任务"
        )
        child_task = Task.create_example(
            sample_user_id,
            title="子任务",
            description="这是一个子任务",
            parent_id=parent_task.id
        )

        # Act: 保存任务
        db_session.add(parent_task)
        db_session.add(child_task)
        db_session.commit()

        # Assert: 验证关系的UUID兼容性
        assert isinstance(parent_task.id, UUID)
        assert isinstance(child_task.parent_id, UUID)
        assert child_task.parent_id == parent_task.id

        # Act: 通过父任务ID查询子任务
        from sqlmodel import select
        statement = select(Task).where(Task.parent_id == parent_task.id)
        children = db_session.exec(statement).all()

        # Assert: 验证查询结果
        assert len(children) == 1
        assert children[0].id == child_task.id
        assert isinstance(children[0].parent_id, UUID)

    def test_batch_uuid_operations(self, sample_user_id):
        """测试批量UUID操作"""
        # Arrange: 准备UUID列表
        uuids = [uuid4(), uuid4(), uuid4()]
        uuid_strs = [str(uuid) for uuid in uuids]

        # Act: 批量转换
        converted_uuids = UUIDConverter.batch_to_uuid(uuid_strs)
        converted_strs = UUIDConverter.batch_to_string(uuids)

        # Assert: 验证批量转换结果
        assert len(converted_uuids) == 3
        assert len(converted_strs) == 3
        assert all(isinstance(uuid, UUID) for uuid in converted_uuids)
        assert all(isinstance(s, str) for s in converted_strs)
        assert converted_uuids == uuids
        assert converted_strs == [str(uuid) for uuid in uuids]

    def test_uuid_consistency_across_operations(self, db_session, sample_user_id):
        """测试跨操作UUID一致性"""
        # Arrange: 创建初始任务
        original_task = Task.create_example(
            sample_user_id,
            title="一致性测试任务"
        )
        db_session.add(original_task)
        db_session.commit()

        # Act: 查询并更新任务
        from sqlmodel import select
        statement = select(Task).where(Task.id == original_task.id)
        task = db_session.exec(statement).first()
        task.title = "更新后的任务"
        task.status = "in_progress"
        db_session.commit()

        # Act: 再次查询验证
        updated_task = db_session.exec(statement).first()

        # Assert: 验证UUID在所有操作中保持一致
        assert updated_task is not None
        assert isinstance(updated_task.id, UUID)
        assert isinstance(updated_task.user_id, UUID)
        assert updated_task.id == original_task.id
        assert updated_task.user_id == original_task.user_id
        assert updated_task.title == "更新后的任务"
        assert updated_task.status == "in_progress"

    def test_uuid_boundary_layer_compatibility(self):
        """测试UUID在API边界层的兼容性"""
        # Arrange: 准备API层常见的UUID处理场景
        service_uuid = uuid4()
        api_string = str(service_uuid)

        # Act: 模拟API层转换
        # 1. 接收字符串，转换为UUID对象
        service_uuid_received = UUIDConverter.ensure_uuid(api_string)

        # 2. 业务逻辑处理（使用UUID对象）
        assert isinstance(service_uuid_received, UUID)

        # 3. 返回响应，转换为字符串
        response_string = UUIDConverter.ensure_string(service_uuid_received)

        # Assert: 验证边界层转换正确性
        assert isinstance(response_string, str)
        assert response_string == api_string
        assert service_uuid_received == service_uuid

    def test_database_uuid_field_types(self, in_memory_db):
        """测试数据库中UUID字段的类型定义"""
        # Arrange: 创建表结构
        Task.metadata.create_all(in_memory_db)

        # 检查表结构
        inspector = inspect(in_memory_db)
        columns = inspector.get_columns("tasks")

        # Assert: 验证UUID相关字段类型
        id_column = next(col for col in columns if col["name"] == "id")
        user_id_column = next(col for col in columns if col["name"] == "user_id")

        # 确保字段类型支持UUID存储（SQLite中通常是CHAR/VARCHAR/TEXT）
        id_type_str = str(id_column["type"]).upper()
        user_id_type_str = str(user_id_column["type"]).upper()

        assert any(t in id_type_str for t in ["VARCHAR", "CHAR", "TEXT", "STRING"])
        assert any(t in user_id_type_str for t in ["VARCHAR", "CHAR", "TEXT", "STRING"])

        # 验证字段长度足够存储UUID（36字符）
        if "length" in id_column:
            assert id_column["length"] >= 36
        if "length" in user_id_column:
            assert user_id_column["length"] >= 36

    def test_uuid_performance_considerations(self):
        """测试UUID操作的性能考虑"""
        # Arrange: 大量UUID操作测试
        large_uuid_list = [uuid4() for _ in range(1000)]

        # Act: 批量转换操作
        import time

        start_time = time.time()
        converted_to_str = UUIDConverter.batch_to_string(large_uuid_list)
        str_conversion_time = time.time() - start_time

        start_time = time.time()
        converted_to_uuid = UUIDConverter.batch_to_uuid(converted_to_str)
        uuid_conversion_time = time.time() - start_time

        # Assert: 验证性能在可接受范围内
        assert str_conversion_time < 0.1  # 100ms内完成1000个转换
        assert uuid_conversion_time < 0.1  # 100ms内完成1000个转换
        assert len(converted_to_str) == 1000
        assert len(converted_to_uuid) == 1000

    def test_uuid_edge_cases(self):
        """测试UUID边界情况处理"""
        # Test case 1: 空字符串
        with pytest.raises((TypeError, ValueError)):
            UUIDConverter.ensure_uuid("")

        # Test case 2: 格式不正确的UUID字符串
        invalid_formats = [
            "short",
            "too-long-uuid-string-that-exceeds-standard-length",
            "not-a-uuid-at-all",
            "12345678-1234-1234-1234-123456789abcd",  # 真正无效：最后一部分13个字符
        ]

        for invalid_uuid in invalid_formats:
            with pytest.raises((TypeError, ValueError)):
                UUIDConverter.ensure_uuid(invalid_uuid)

        # Test case 3: 大小写混合
        mixed_case_uuid = "550E8400-E29B-41D4-A716-446655440000"
        converted = UUIDConverter.ensure_uuid(mixed_case_uuid)
        assert isinstance(converted, UUID)
        assert str(converted).lower() == mixed_case_uuid.lower()

    def test_uuid_memory_efficiency(self):
        """测试UUID对象的内存效率"""
        # Arrange: 创建大量UUID对象
        uuids = [uuid4() for _ in range(100)]

        # Act & Assert: 验证UUID对象可以被正确垃圾回收
        import sys
        import gc

        # 记录初始内存使用
        initial_objects = len(gc.get_objects())

        # 删除UUID引用
        del uuids

        # 强制垃圾回收
        gc.collect()

        # 验证对象被清理
        final_objects = len(gc.get_objects())

        # 允许一定的对象创建开销，但不应该有大量未释放的UUID对象
        assert (final_objects - initial_objects) < 1000  # 合理的内存增长


if __name__ == "__main__":
    pytest.main([__file__])