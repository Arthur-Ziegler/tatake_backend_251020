# Task Completion API Specification

## ADDED Requirements

### Requirement: 任务完成API
系统MUST实现POST /tasks/{id}/complete和POST /tasks/{id}/uncomplete端点。

**优先级**: P1

#### Scenario: 普通任务首次完成获得2积分
```python
# Given: 用户有一个未完成的普通任务
task = Task(id=task_id, user_id=user_id, status="pending", last_claimed_date=None)

# When: 调用完成任务API
response = client.post(f"/tasks/{task_id}/complete", headers=auth_headers)

# Then: 返回成功，奖励2积分
assert response.json()["code"] == 200
assert response.json()["data"]["reward_earned"]["amount"] == 2
assert response.json()["data"]["reward_earned"]["type"] == "points"
```

#### Scenario: 任务已领奖永久拒绝
```python
# Given: 任务last_claimed_date不为空
task = Task(id=task_id, last_claimed_date=datetime(2025, 10, 20))

# When: 再次完成任务
response = client.post(f"/tasks/{task_id}/complete", headers=auth_headers)

# Then: 拒绝发放奖励
assert response.json()["data"]["reward_earned"]["amount"] == 0
assert response.json()["data"]["message"] == "任务已领过奖励"
```

#### Scenario: Top3任务完成触发抽奖
```python
# Given: 任务在今日Top3中
top3_service.set_top3(user_id, date.today(), [task_id])

# When: 完成Top3任务
response = client.post(f"/tasks/{task_id}/complete", headers=auth_headers)

# Then: 触发抽奖（50%概率100积分或奖品）
reward = response.json()["data"]["reward_earned"]
assert reward["type"] in ["points", "reward"]
if reward["type"] == "points":
    assert reward["amount"] == 100
else:
    assert reward["reward_id"] is not None
```

#### Scenario: 取消完成不回收奖励
```python
# Given: 已完成的任务
task = Task(id=task_id, status="completed", last_claimed_date=datetime.now())

# When: 取消完成
response = client.post(f"/tasks/{task_id}/uncomplete", headers=auth_headers)

# Then: 状态改为pending，last_claimed_date不清除
assert response.json()["data"]["task"]["status"] == "pending"
assert response.json()["data"]["task"]["last_claimed_date"] is not None
```

### Requirement: 父任务完成度自动更新
系统MUST在子任务完成时递归更新所有父任务的completion_percentage。

**优先级**: P1

#### Scenario: 叶子任务完成更新父任务
```python
# Given: 任务树 parent -> [child1, child2]
parent = Task(id=parent_id, completion_percentage=0)
child1 = Task(id=child1_id, parent_id=parent_id, status="pending")
child2 = Task(id=child2_id, parent_id=parent_id, status="pending")

# When: 完成child1
complete_task(child1_id, user_id)

# Then: parent完成度更新为50%
parent_updated = get_task(parent_id)
assert parent_updated.completion_percentage == 50.0
```

#### Scenario: 深层任务递归更新
```python
# Given: 三层任务树 root -> parent -> child
root = Task(id=root_id, completion_percentage=0)
parent = Task(id=parent_id, parent_id=root_id, completion_percentage=0)
child = Task(id=child_id, parent_id=parent_id, status="pending")

# When: 完成child
complete_task(child_id, user_id)

# Then: parent和root都更新为100%
assert get_task(parent_id).completion_percentage == 100.0
assert get_task(root_id).completion_percentage == 100.0
```

### Requirement: Top3任务检测方法
Top3Service MUST提供方法判断任务是否在当日Top3中。

**优先级**: P1

#### Scenario: 检测任务在Top3中
```python
# Given: 任务在今日Top3列表
top3 = TaskTop3(user_id=user_id, top_date=date.today(), task_ids=[task_id])

# When: 检测任务
result = top3_service.is_task_in_today_top3(user_id, task_id)

# Then: 返回True
assert result is True
```

#### Scenario: 检测任务不在Top3中
```python
# Given: 今日无Top3设置
# When: 检测任务
result = top3_service.is_task_in_today_top3(user_id, task_id)

# Then: 返回False
assert result is False
```
