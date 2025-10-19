# 数据层架构规范

## ADDED Requirements

### Requirement: 基础 Repository 架构

数据层 **SHALL** 设计并实现基础的 Repository 抽象类，提供通用的 CRUD 操作，支持泛型类型安全，为具体模型 Repository 提供统一的基础接口和实现。

#### Scenario: 实现 BaseRepository 抽象类
```python
# 测试用例
def test_base_repository_create(session):
    """测试基础 Repository 创建功能"""
    repo = BaseRepository(session, User)
    user_data = {"nickname": "测试用户", "email": "test@example.com"}

    # 执行创建
    user = repo.create(user_data)

    # 验证结果
    assert user.id is not None
    assert user.nickname == "测试用户"
    assert user.email == "test@example.com"
    assert user.created_at is not None

def test_base_repository_get_by_id(session):
    """测试根据ID获取记录"""
    repo = BaseRepository(session, User)

    # 创建测试数据
    user = User(nickname="测试用户", email="test@example.com")
    session.add(user)
    session.commit()

    # 执行查询
    found_user = repo.get_by_id(user.id)

    # 验证结果
    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.nickname == "测试用户"

def test_base_repository_get_all_with_filters(session):
    """测试带过滤条件的列表查询"""
    repo = BaseRepository(session, User)

    # 创建测试数据
    user1 = User(nickname="用户1", email="user1@example.com")
    user2 = User(nickname="用户2", email="user2@example.com")
    user3 = User(nickname="用户3", email="user3@example.com", is_guest=True)

    session.add_all([user1, user2, user3])
    session.commit()

    # 执行过滤查询
    regular_users = repo.get_all(is_guest=False)
    guest_users = repo.get_all(is_guest=True)

    # 验证结果
    assert len(regular_users) == 2
    assert len(guest_users) == 1
    assert all(not user.is_guest for user in regular_users)
    assert all(user.is_guest for user in guest_users)
```

### Requirement: Repository 类型安全设计

Repository 层 **MUST** 确保完整的类型安全，利用 Python 泛型和 SQLModel 的类型注解，实现编译时类型检查和运行时类型验证，防止类型错误和提高代码可维护性。

#### Scenario: 泛型 Repository 类型检查
```python
# 测试用例
def test_repository_type_safety():
    """测试 Repository 类型安全"""
    session = Mock(spec=Session)

    # 创建针对不同模型的 Repository
    user_repo = BaseRepository(session, User)
    task_repo = BaseRepository(session, Task)

    # 验证类型信息
    assert user_repo.model == User
    assert task_repo.model == Task

    # 验证返回类型
    # mypy 应该能够推断出正确的返回类型
    user: User = user_repo.get_by_id("user_id")  # type: ignore
    task: Task = task_repo.get_by_id("task_id")  # type: ignore

def test_repository_method_return_types(session):
    """测试 Repository 方法返回类型"""
    repo = BaseRepository(session, User)

    # 测试各种返回类型
    user = repo.create({"nickname": "测试"})  # User
    assert isinstance(user, User)

    found_user = repo.get_by_id("id")  # Optional[User]
    assert found_user is None or isinstance(found_user, User)

    users = repo.get_all()  # List[User]
    assert isinstance(users, list)
    assert all(isinstance(u, User) for u in users)

    exists = repo.exists()  # bool
    assert isinstance(exists, bool)

    count = repo.count()  # int
    assert isinstance(count, int)
```

### Requirement: 错误处理机制

数据层 **SHALL** 建立完善的 Repository 层错误处理机制，包括数据库连接错误、验证错误、数据不存在错误等各种异常情况的处理，提供清晰的错误信息和一致的异常处理策略。

#### Scenario: Repository 异常处理
```python
# 测试用例
def test_repository_not_found_error(session):
    """测试记录不存在异常"""
    repo = BaseRepository(session, User)

    # 查询不存在的记录应该返回 None，而不是抛出异常
    user = repo.get_by_id("nonexistent_id")
    assert user is None

def test_repository_database_error_handling():
    """测试数据库错误处理"""
    # 模拟数据库连接错误
    broken_session = Mock()
    broken_session.add.side_effect = DatabaseError("连接失败")

    repo = BaseRepository(broken_session, User)

    # 应该抛出自定义异常
    with pytest.raises(RepositoryError):
        repo.create({"nickname": "测试"})

def test_repository_validation_error_handling(session):
    """测试数据验证错误处理"""
    repo = BaseRepository(session, User)

    # 提供无效数据
    invalid_data = {"nickname": "", "email": "invalid-email"}

    # 应该抛出验证异常
    with pytest.raises(ValidationError):
        repo.create(invalid_data)
```

### Requirement: 事务管理

Repository 层 **MUST** 实现事务管理功能，支持事务的提交、回滚和嵌套事务，确保数据操作的原子性和一致性，提供灵活的事务边界控制机制。

#### Scenario: Repository 事务边界
```python
# 测试用例
def test_repository_transaction_rollback(session):
    """测试事务回滚"""
    repo = BaseRepository(session, User)

    # 开始事务
    transaction = session.begin_nested()

    try:
        # 创建用户
        user = repo.create({"nickname": "测试用户"})
        user_id = user.id

        # 验证用户已创建
        assert repo.get_by_id(user_id) is not None

        # 模拟错误
        raise ValueError("模拟错误")

    except ValueError:
        # 回滚事务
        transaction.rollback()

    # 验证用户已被回滚
    assert repo.get_by_id(user_id) is None

def test_repository_multiple_operations(session):
    """测试多个操作在同一事务中"""
    user_repo = BaseRepository(session, User)
    task_repo = BaseRepository(session, Task)

    # 在同一事务中创建多个记录
    with session.begin():
        user = user_repo.create({"nickname": "测试用户"})
        task1 = task_repo.create({
            "title": "任务1",
            "user_id": user.id
        })
        task2 = task_repo.create({
            "title": "任务2",
            "user_id": user.id
        })

    # 验证所有记录都已创建
    assert user_repo.get_by_id(user.id) is not None
    assert task_repo.get_by_id(task1.id) is not None
    assert task_repo.get_by_id(task2.id) is not None
```

## MODIFIED Requirements

### Requirement: 具体模型 Repository 实现

数据层 **SHALL** 基于基础 Repository 抽象类，实现针对具体业务模型的 Repository 类，包括 UserRepository、TaskRepository、FocusSessionRepository 等，提供模型特定的查询方法和业务逻辑封装。

#### Scenario: UserRepository 特定功能
```python
# 测试用例
def test_user_repository_find_by_email(session):
    """测试根据邮箱查找用户"""
    repo = UserRepository(session)

    # 创建测试用户
    user = User(nickname="测试用户", email="test@example.com")
    session.add(user)
    session.commit()

    # 执行查询
    found_user = repo.find_by_email("test@example.com")

    # 验证结果
    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email == "test@example.com"

def test_user_repository_find_by_phone(session):
    """测试根据手机号查找用户"""
    repo = UserRepository(session)

    # 创建测试用户
    user = User(nickname="测试用户", phone="13800138000")
    session.add(user)
    session.commit()

    # 执行查询
    found_user = repo.find_by_phone("13800138000")

    # 验证结果
    assert found_user is not None
    assert found_user.phone == "13800138000"

def test_user_repository_update_last_login(session):
    """测试更新最后登录时间"""
    repo = UserRepository(session)

    # 创建测试用户
    user = User(nickname="测试用户")
    session.add(user)
    session.commit()

    # 记录原始登录时间
    original_login_time = user.last_login_at

    # 更新登录时间
    repo.update_last_login(user.id)

    # 验证更新
    updated_user = repo.get_by_id(user.id)
    assert updated_user.last_login_at > original_login_time
```

#### Scenario: TaskRepository 树形结构查询
```python
# 测试用例
def test_task_repository_find_root_tasks(session):
    """测试查找根任务（无父任务的任务）"""
    repo = TaskRepository(session)
    user_id = "user123"

    # 创建任务树结构
    root_task = Task(title="根任务", user_id=user_id)
    child_task1 = Task(title="子任务1", user_id=user_id, parent_id=root_task.id)
    child_task2 = Task(title="子任务2", user_id=user_id, parent_id=root_task.id)
    grandchild_task = Task(title="孙任务", user_id=user_id, parent_id=child_task1.id)

    session.add_all([root_task, child_task1, child_task2, grandchild_task])
    session.commit()

    # 查找根任务
    root_tasks = repo.find_root_tasks(user_id)

    # 验证结果
    assert len(root_tasks) == 1
    assert root_tasks[0].id == root_task.id
    assert root_tasks[0].title == "根任务"

def test_task_repository_find_subtasks(session):
    """测试查找子任务"""
    repo = TaskRepository(session)
    user_id = "user123"

    # 创建任务树结构
    parent_task = Task(title="父任务", user_id=user_id)
    child_task1 = Task(title="子任务1", user_id=user_id, parent_id=parent_task.id)
    child_task2 = Task(title="子任务2", user_id=user_id, parent_id=parent_task.id)

    session.add_all([parent_task, child_task1, child_task2])
    session.commit()

    # 查找子任务
    subtasks = repo.find_subtasks(parent_task.id)

    # 验证结果
    assert len(subtasks) == 2
    subtask_titles = [task.title for task in subtasks]
    assert "子任务1" in subtask_titles
    assert "子任务2" in subtask_titles

def test_task_repository_calculate_completion_percentage(session):
    """测试计算任务完成百分比"""
    repo = TaskRepository(session)
    user_id = "user123"

    # 创建任务树结构
    parent_task = Task(title="父任务", user_id=user_id)
    child_task1 = Task(title="子任务1", user_id=user_id, parent_id=parent_task.id, status=TaskStatus.COMPLETED)
    child_task2 = Task(title="子任务2", user_id=user_id, parent_id=parent_task.id, status=TaskStatus.PENDING)
    child_task3 = Task(title="子任务3", user_id=user_id, parent_id=parent_task.id, status=TaskStatus.COMPLETED)

    session.add_all([parent_task, child_task1, child_task2, child_task3])
    session.commit()

    # 计算完成百分比
    percentage = repo.calculate_completion_percentage(parent_task.id)

    # 验证结果：3个子任务中2个完成，应该是 66%
    assert percentage == 66
```

#### Scenario: FocusSessionRepository 时间范围查询
```python
# 测试用例
def test_focus_session_repository_find_by_date_range(session):
    """测试根据日期范围查找专注会话"""
    repo = FocusSessionRepository(session)
    user_id = "user123"

    # 创建不同时间的专注会话
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    session1 = FocusSession(
        user_id=user_id,
        start_time=datetime.combine(yesterday, time(10, 0)),
        actual_duration=25
    )
    session2 = FocusSession(
        user_id=user_id,
        start_time=datetime.combine(today, time(14, 0)),
        actual_duration=30
    )
    session3 = FocusSession(
        user_id=user_id,
        start_time=datetime.combine(tomorrow, time(9, 0)),
        actual_duration=20
    )

    session.add_all([session1, session2, session3])
    session.commit()

    # 查询今天到明天的会话
    sessions = repo.find_by_date_range(
        user_id=user_id,
        start_date=datetime.combine(today, time(0, 0)),
        end_date=datetime.combine(tomorrow, time(23, 59, 59))
    )

    # 验证结果
    assert len(sessions) == 2
    session_ids = [s.id for s in sessions]
    assert session2.id in session_ids
    assert session3.id in session_ids
    assert session1.id not in session_ids

def test_focus_session_repository_get_statistics(session):
    """测试获取专注统计信息"""
    repo = FocusSessionRepository(session)
    user_id = "user123"

    # 创建多个专注会话
    sessions = [
        FocusSession(user_id=user_id, actual_duration=25, status=SessionStatus.COMPLETED),
        FocusSession(user_id=user_id, actual_duration=30, status=SessionStatus.COMPLETED),
        FocusSession(user_id=user_id, actual_duration=20, status=SessionStatus.ABANDONED),
        FocusSession(user_id=user_id, actual_duration=45, status=SessionStatus.COMPLETED),
    ]

    session.add_all(sessions)
    session.commit()

    # 获取统计信息
    stats = repo.get_statistics(user_id)

    # 验证结果
    assert stats.total_sessions == 4
    assert stats.completed_sessions == 3
    assert stats.total_focus_minutes == 100  # 25+30+45
    assert stats.completion_rate == 75  # 3/4 * 100
    assert stats.average_session_duration == 33  # 100/3
```

#### Scenario: RewardRepository 抽奖逻辑
```python
# 测试用例
def test_reward_repository_get_available_rewards(session):
    """测试获取可用奖励"""
    repo = RewardRepository(session)

    # 创建不同状态的奖励
    active_reward = Reward(name="活跃奖励", category=RewardCategory.PHYSICAL, is_active=True)
    inactive_reward = Reward(name="非活跃奖励", category=RewardCategory.DIGITAL, is_active=False)
    limited_reward = Reward(name="限量奖励", category=RewardCategory.VOUCHER, is_active=True, is_limited=True, total_quantity=10)

    session.add_all([active_reward, inactive_reward, limited_reward])
    session.commit()

    # 获取可用奖励
    available_rewards = repo.get_available_rewards()

    # 验证结果
    assert len(available_rewards) == 2  # 活跃奖励和限量奖励
    reward_names = [r.name for r in available_rewards]
    assert "活跃奖励" in reward_names
    assert "限量奖励" in reward_names
    assert "非活跃奖励" not in reward_names

def test_reward_repository_draw_lottery(session):
    """测试抽奖逻辑"""
    repo = RewardRepository(session)
    user_id = "user123"
    task_id = "task456"

    # 创建奖励配置
    points_reward = Reward(
        name="积分奖励",
        category=RewardCategory.POINTS,
        points_value=50,
        lottery_probability=0.7  # 70% 概率
    )
    fragment_reward = Reward(
        name="碎片奖励",
        category=RewardCategory.FRAGMENT,
        lottery_probability=0.3  # 30% 概率
    )

    session.add_all([points_reward, fragment_reward])
    session.commit()

    # 执行抽奖
    result = repo.draw_lottery(user_id, task_id, mood=MoodLevel.HAPPY)

    # 验证结果
    assert result is not None
    assert result.user_id == user_id
    assert result.task_id == task_id
    assert result.reward_type in [LotteryRewardType.POINTS, LotteryRewardType.FRAGMENT]

    if result.reward_type == LotteryRewardType.POINTS:
        assert result.points_amount is not None
        assert result.points_amount > 0
    elif result.reward_type == LotteryRewardType.FRAGMENT:
        assert result.fragment_id is not None
```

## REMOVED Requirements

*No removed requirements in this specification.*