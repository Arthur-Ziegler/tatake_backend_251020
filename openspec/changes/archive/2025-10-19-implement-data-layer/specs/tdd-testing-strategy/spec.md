# TDD 测试策略规范

## ADDED Requirements

### Requirement: TDD 开发流程规范

开发团队 **MUST** 遵循严格的 TDD 开发流程，遵循红-绿-重构循环，确保每个功能先有测试覆盖再实现代码，通过持续的重构保持代码质量，建立可持续的高质量开发实践。

#### Scenario: 红-绿-重构循环实践
```python
# 第一步：红 - 写失败的测试
def test_task_model_creation_with_validation():
    """测试任务模型创建和验证"""
    # 测试正常创建
    task = Task(
        title="测试任务",
        user_id="user123",
        description="这是一个测试任务"
    )

    assert task.title == "测试任务"
    assert task.user_id == "user123"
    assert task.status == TaskStatus.PENDING
    assert task.created_at is not None

# 第二步：绿 - 实现最小代码让测试通过
# 此时 Task 模型还不存在，需要实现

# 第三步：重构 - 优化代码保持测试通过
# 在实现后优化代码结构
```

#### Scenario: 测试驱动模型开发
```python
# 先写测试，定义期望的行为
def test_task_completion_workflow():
    """测试任务完成工作流"""
    # 创建任务
    task = Task(title="待完成任务", user_id="user123")

    # 验证初始状态
    assert task.status == TaskStatus.PENDING
    assert task.completed_at is None
    assert task.completion_percentage == 0

    # 完成任务
    task.complete_task()

    # 验证完成状态
    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None
    assert task.completion_percentage == 100

# 然后实现 Task.complete_task() 方法
```

### Requirement: 测试覆盖率要求

数据层测试 **MUST** 达到 95% 以上的测试覆盖率标准，包括语句覆盖、分支覆盖和条件覆盖，通过自动化工具持续监控覆盖率指标，保证代码质量。

#### Scenario: 95% 覆盖率目标
```python
# 测试配置要求
# pyproject.toml
[tool.pytest.ini_options]
addopts = [
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=95"  # 覆盖率不低于95%
]

# 验证覆盖率的测试
def test_full_model_coverage():
    """确保所有模型方法都有测试覆盖"""
    # 这个测试会由覆盖率工具验证
    # 需要测试模型的：
    # - 所有属性
    # - 所有方法
    # - 所有验证逻辑
    # - 所有关系
    pass
```

#### Scenario: 分支和条件覆盖
```python
def test_task_validation_all_branches():
    """测试任务验证的所有分支"""
    # 测试有效数据
    valid_task = Task(title="有效任务", user_id="user123")
    assert valid_task.title == "有效任务"

    # 测试无效数据 - 空标题
    with pytest.raises(ValidationError):
        Task(title="", user_id="user123")

    # 测试无效数据 - 标题过长
    with pytest.raises(ValidationError):
        Task(title="a" * 201, user_id="user123")

    # 测试无效数据 - 缺少用户ID
    with pytest.raises(ValidationError):
        Task(title="任务")
```

### Requirement: 测试分类和组织

测试套件 **SHALL** 建立清晰的测试分类体系，包括单元测试、集成测试和性能测试，设计合理的测试组织结构，确保测试的可维护性和可读性，通过测试夹具和工具提高测试效率。

#### Scenario: 单元测试结构
```python
class TestTaskModelUnit:
    """任务模型单元测试"""

    def test_task_initialization(self):
        """测试任务初始化"""
        pass

    def test_task_property_validation(self):
        """测试任务属性验证"""
        pass

    def test_task_method_behavior(self):
        """测试任务方法行为"""
        pass

    def test_task_relationships(self):
        """测试任务关系"""
        pass

class TestTaskRepositoryUnit:
    """任务仓储单元测试"""

    def test_repository_create(self):
        """测试仓储创建方法"""
        pass

    def test_repository_read(self):
        """测试仓储读取方法"""
        pass

    def test_repository_update(self):
        """测试仓储更新方法"""
        pass

    def test_repository_delete(self):
        """测试仓储删除方法"""
        pass
```

#### Scenario: 集成测试场景
```python
class TestDataLayerIntegration:
    """数据层集成测试"""

    def test_full_task_lifecycle(self, session):
        """测试完整的任务生命周期"""
        # 创建任务
        repo = TaskRepository(session)
        task = repo.create({
            "title": "集成测试任务",
            "user_id": "user123"
        })

        # 更新任务
        updated_task = repo.update(task.id, {
            "status": TaskStatus.IN_PROGRESS
        })
        assert updated_task.status == TaskStatus.IN_PROGRESS

        # 完成任务
        completed_task = repo.update(task.id, {
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.utcnow()
        })
        assert completed_task.status == TaskStatus.COMPLETED

        # 删除任务
        result = repo.delete(task.id)
        assert result is True

        # 验证删除
        deleted_task = repo.get_by_id(task.id)
        assert deleted_task is None
```

### Requirement: 测试数据管理

测试框架 **SHALL** 实现高效的测试数据管理策略，包括测试夹具的使用、数据库测试隔离、测试数据的创建和清理，确保测试之间的独立性，避免测试数据污染和依赖问题。

#### Scenario: 测试夹具(Fixtures)设计
```python
@pytest.fixture
def sample_user():
    """示例用户夹具"""
    return User(
        nickname="测试用户",
        email="test@example.com",
        is_guest=False
    )

@pytest.fixture
def sample_task(sample_user):
    """示例任务夹具，依赖用户夹具"""
    return Task(
        title="测试任务",
        user_id=sample_user.id,
        description="这是一个测试任务"
    )

@pytest.fixture
def task_tree(sample_user):
    """任务树夹具"""
    parent = Task(title="父任务", user_id=sample_user.id)
    child1 = Task(title="子任务1", user_id=sample_user.id, parent_id=parent.id)
    child2 = Task(title="子任务2", user_id=sample_user.id, parent_id=parent.id)

    return parent, [child1, child2]

# 使用夹具的测试
def test_task_with_fixture(sample_task):
    """使用夹具的测试"""
    assert sample_task.title == "测试任务"
    assert sample_task.status == TaskStatus.PENDING

def test_task_tree_operations(task_tree):
    """测试任务树操作"""
    parent, children = task_tree

    assert len(children) == 2
    assert all(child.parent_id == parent.id for child in children)
```

#### Scenario: 数据库测试隔离
```python
@pytest.fixture
def session():
    """数据库会话夹具，每个测试独立"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def transaction_session(session):
    """事务会话夹具，测试后自动回滚"""
    transaction = session.begin_nested()
    try:
        yield session
    finally:
        transaction.rollback()

# 使用事务会话的测试
def test_isolated_database_operations(transaction_session):
    """测试数据库操作隔离"""
    # 在事务中创建数据
    user = User(nickname="测试用户", email="test@example.com")
    transaction_session.add(user)
    transaction_session.commit()

    # 验证数据存在
    found_user = transaction_session.exec(
        select(User).where(User.email == "test@example.com")
    ).first()
    assert found_user is not None

    # 测试结束后，事务会自动回滚
```

### Requirement: Mock 和 Stub 策略

测试策略 **SHALL** 制定合理的 Mock 和 Stub 使用策略，用于隔离外部依赖、模拟复杂场景、提高测试执行效率，确保 Mock 的正确使用，避免过度依赖模拟而影响测试的真实性。

#### Scenario: 外部依赖 Mock
```python
class TestTaskRepositoryWithMocks:
    """使用 Mock 的任务仓储测试"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = Mock(spec=Session)
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()
        return session

    def test_create_with_mock_session(self, mock_session):
        """测试使用模拟会话创建任务"""
        repo = TaskRepository(mock_session)

        task_data = {"title": "测试任务", "user_id": "user123"}
        task = repo.create(task_data)

        # 验证会话方法被调用
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # 验证返回的任务对象
        assert isinstance(task, Task)
        assert task.title == "测试任务"

    @pytest.fixture
    def mock_email_service(self):
        """模拟邮件服务"""
        service = Mock()
        service.send_notification = Mock(return_value=True)
        return service

    def test_task_completion_notification(self, mock_email_service):
        """测试任务完成通知"""
        task = Task(title="重要任务", user_id="user123")

        # 模拟完成任务
        task.complete_task()

        # 验证通知服务被调用
        if task.status == TaskStatus.COMPLETED:
            mock_email_service.send_notification.assert_called_once_with(
                user_id="user123",
                message="任务已完成: 重要任务"
            )
```

#### Scenario: Repository Stub
```python
class StubTaskRepository(BaseRepository[Task]):
    """任务仓储存根，用于测试"""

    def __init__(self):
        self.tasks = {}
        self.next_id = 1

    def create(self, obj_data: dict) -> Task:
        task = Task(id=str(self.next_id), **obj_data)
        self.tasks[task.id] = task
        self.next_id += 1
        return task

    def get_by_id(self, obj_id: str) -> Optional[Task]:
        return self.tasks.get(obj_id)

    def get_all(self, **filters) -> List[Task]:
        return [
            task for task in self.tasks.values()
            if all(getattr(task, k, None) == v for k, v in filters.items())
        ]

# 使用存根的测试
def test_task_service_with_stub():
    """测试任务服务使用存根仓储"""
    stub_repo = StubTaskRepository()
    service = TaskService(stub_repo)

    # 测试创建任务
    task = service.create_task({"title": "测试任务", "user_id": "user123"})
    assert task.title == "测试任务"

    # 测试查询任务
    found_task = service.get_task(task.id)
    assert found_task == task
```

### Requirement: 性能测试

测试套件 **SHALL** 包含数据层性能测试框架，包括查询性能基准测试、大数据量测试、并发访问测试，设定明确的性能指标和阈值，确保数据层在各种负载条件下都能保持良好的性能表现。

#### Scenario: 查询性能基准
```python
class TestPerformance:
    """性能测试类"""

    def test_large_dataset_query_performance(self, session):
        """测试大数据集查询性能"""
        # 创建大量测试数据
        users = [User(nickname=f"用户{i}", email=f"user{i}@example.com")
                for i in range(1000)]
        session.add_all(users)
        session.commit()

        # 测试查询性能
        start_time = time.time()

        repo = UserRepository(session)
        all_users = repo.get_all()

        end_time = time.time()
        query_time = end_time - start_time

        # 验证结果
        assert len(all_users) == 1000

        # 验证性能（应该在1秒内完成）
        assert query_time < 1.0, f"查询耗时 {query_time:.2f} 秒，超过预期"

    def test_complex_relationship_query_performance(self, session):
        """测试复杂关系查询性能"""
        # 创建复杂的任务树结构
        user = User(nickname="测试用户", email="test@example.com")
        session.add(user)
        session.commit()

        # 创建多层任务树
        tasks = []
        for i in range(100):
            parent_task = Task(title=f"父任务{i}", user_id=user.id)
            session.add(parent_task)
            session.commit()

            for j in range(10):
                child_task = Task(
                    title=f"子任务{i}-{j}",
                    user_id=user.id,
                    parent_id=parent_task.id
                )
                tasks.append(child_task)

        session.add_all(tasks)
        session.commit()

        # 测试复杂查询性能
        start_time = time.time()

        repo = TaskRepository(session)
        tree = repo.get_task_tree(user.id)

        end_time = time.time()
        query_time = end_time - start_time

        # 验证结果
        assert len(tree) > 100

        # 验证性能（应该在2秒内完成）
        assert query_time < 2.0, f"复杂查询耗时 {query_time:.2f} 秒，超过预期"
```

### Requirement: 测试文档和维护

项目文档 **SHALL** 包含测试文档标准和维护指南，确保测试的可读性和可维护性，包括测试用例文档、注释规范、测试维护最佳实践，为团队协作和长期维护提供清晰的指导。

#### Scenario: 测试文档标准
```python
class TestTaskModel:
    """任务模型测试

    测试覆盖任务模型的以下方面：
    1. 基本属性和初始化
    2. 数据验证规则
    3. 业务方法逻辑
    4. 状态转换逻辑
    5. 关系定义和查询
    """

    def test_task_creation_with_required_fields(self):
        """测试必填字段的任务创建

        验证：
        - 必填字段（title, user_id）存在时创建成功
        - 默认值正确设置（status=PENDING）
        - 时间戳自动生成
        """
        task = Task(title="测试任务", user_id="user123")

        assert task.title == "测试任务"
        assert task.user_id == "user123"
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None
        assert task.updated_at is not None

    def test_task_validation_on_invalid_data(self):
        """测试无效数据的验证失败

        验证：
        - 空标题触发验证错误
        - 超长标题触发验证错误
        - 缺少必填字段触发验证错误
        """
        # 测试空标题
        with pytest.raises(ValidationError, match="标题不能为空"):
            Task(title="", user_id="user123")

        # 测试标题过长
        with pytest.raises(ValidationError, match="标题长度不能超过200字符"):
            Task(title="a" * 201, user_id="user123")

        # 测试缺少用户ID
        with pytest.raises(ValidationError, match="用户ID是必填项"):
            Task(title="测试任务")
```

#### Scenario: 测试维护指南
```python
# 测试维护注释示例
def test_task_complex_business_logic(self):
    """测试复杂业务逻辑

    注意：这是一个复杂的业务逻辑测试，当修改以下代码时需要重新验证：
    - Task.complete_task() 方法
    - Task.calculate_completion_percentage() 方法
    - 任务状态转换逻辑
    - 积分计算逻辑

    修改相关代码后，请运行：
    uv run pytest tests/models/test_task.py::TestTaskModel::test_task_complex_business_logic -v
    """
    # 复杂的测试逻辑
    pass
```

## MODIFIED Requirements

### Requirement: 持续集成测试策略

CI/CD 管道 **MUST** 包含自动化测试策略，包括自动化测试执行、测试报告生成、覆盖率检查、性能回归检测，确保在每次代码提交时都能自动验证代码质量和功能正确性。

#### Scenario: CI/CD 管道测试
```python
# .github/workflows/test.yml 配置验证测试
def test_ci_configuration():
    """验证 CI 配置正确性"""
    # 这个测试确保 CI 环境配置正确
    # 实际运行在 CI 环境中

    import os

    # 验证环境变量
    assert os.getenv("CI") == "true"

    # 验证测试数据库配置
    database_url = os.getenv("DATABASE_URL", "")
    assert "sqlite" in database_url or "postgresql" in database_url

    # 验证覆盖率工具可用
    import coverage
    assert coverage.__version__ is not None
```

#### Scenario: 测试报告生成
```python
def test_coverage_report_generation():
    """测试覆盖率报告生成"""
    # 这个测试验证覆盖率报告能够正确生成
    # 由 CI 系统运行和验证

    import os
    import subprocess

    # 运行覆盖率测试
    result = subprocess.run([
        "uv", "run", "pytest",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=xml"
    ], capture_output=True, text=True)

    # 验证命令执行成功
    assert result.returncode == 0

    # 验证报告文件生成
    assert os.path.exists("htmlcov/index.html")
    assert os.path.exists("coverage.xml")
```

## REMOVED Requirements

*No removed requirements in this specification.*