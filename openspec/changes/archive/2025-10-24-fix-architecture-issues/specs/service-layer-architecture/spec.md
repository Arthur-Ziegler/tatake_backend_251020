# Service Layer Architecture Specification

## MODIFIED Requirements

### Requirement: Service依赖注入一致性
所有Service类MUST显式声明构造函数依赖，遵循依赖注入原则。

**优先级**: P0
**变更原因**: 修复服务初始化失败问题

#### Scenario: TaskService初始化需要PointsService
```python
# Given: 创建TaskService实例
task_service = TaskService(session, points_service)

# When: 调用任务完成方法
result = task_service.complete_task(task_id, user_id)

# Then: 能够正确调用points_service发放积分
assert result["points_awarded"] > 0
```

#### Scenario: RewardService初始化需要PointsService
```python
# Given: 创建RewardService实例
reward_service = RewardService(session, points_service)

# When: 调用奖品兑换方法
result = reward_service.redeem_reward(user_id, reward_id)

# Then: 能够正确调用points_service扣除积分
assert reward_service.points_service is not None
```

### Requirement: UUID字段类型统一
所有模型的UUID字段MUST使用`str`类型，确保SQLite兼容性。

**优先级**: P0
**变更原因**: 修复SQLite UUID绑定错误

#### Scenario: 存储UUID为字符串
```python
# Given: 创建任务实例
task = Task(id=str(uuid4()), user_id=str(uuid4()), title="测试")

# When: 保存到数据库
session.add(task)
session.commit()

# Then: 能够成功存储和查询
retrieved = session.get(Task, task.id)
assert retrieved.id == task.id
assert isinstance(retrieved.id, str)
```

### Requirement: Repository API更新
所有Repository MUST使用`session.execute().scalars()`替代废弃的`session.exec()`。

**优先级**: P0
**变更原因**: 修复过时API导致的查询失败

#### Scenario: 查询单个实体
```python
# Given: 构建查询语句
statement = select(Task).where(Task.id == task_id)

# When: 执行查询
result = session.execute(statement).scalars().first()

# Then: 返回正确的实体对象
assert result is not None
assert result.id == task_id
```

#### Scenario: 查询实体列表
```python
# Given: 构建查询语句
statement = select(Task).where(Task.user_id == user_id)

# When: 执行查询
results = session.execute(statement).scalars().all()

# Then: 返回列表
assert isinstance(results, list)
```
