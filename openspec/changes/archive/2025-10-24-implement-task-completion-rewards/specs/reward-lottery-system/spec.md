# Reward Lottery System Specification

## MODIFIED Requirements

### Requirement: Top3抽奖积分数量
Top3任务抽奖MUST在50%概率时发放100积分（不是50积分）。

**优先级**: P1
**变更原因**: 当前50积分，应为100积分（v3文档要求）

#### Scenario: 抽奖获得100积分
```python
# Given: 模拟抽奖结果为积分
random.seed(0)

# When: 调用Top3抽奖
result = reward_service.top3_lottery(user_id, task_id)

# Then: 获得100积分
assert result["type"] == "points"
assert result["amount"] == 100

# And: 创建积分流水，source_type为lottery_points
transaction = points_repo.get_latest(user_id)
assert transaction.amount == 100
assert transaction.source_type == "lottery_points"
```

### Requirement: Top3抽奖奖品池
奖品池MUST包含所有is_active=true的奖品，不限定category。

**优先级**: P1
**变更原因**: 当前从category='top3'筛选，应从所有is_active=true奖品中随机

#### Scenario: 从所有激活奖品抽取
```python
# Given: 数据库有3个激活奖品
rewards = [
    Reward(id="gold", name="金币", is_active=True, category="basic"),
    Reward(id="diamond", name="钻石", is_active=True, category="premium"),
    Reward(id="chest", name="宝箱", is_active=True, category="rare")
]

# When: 抽奖获得奖品
result = reward_service.top3_lottery(user_id, task_id)

# Then: 从所有激活奖品中随机选择
assert result["type"] == "reward"
assert result["reward_id"] in ["gold", "diamond", "chest"]
```

### Requirement: 抽奖source_type规范
抽奖积分MUST使用lottery_points，抽奖奖品MUST使用lottery_reward。

**优先级**: P1
**变更原因**: 新增lottery_reward枚举值，明确语义

#### Scenario: 抽奖积分source_type
```python
# Given: 抽奖获得积分
# When: 创建积分流水
points_service.add_points(user_id, 100, "lottery_points", task_id)

# Then: source_type正确
transaction = get_transaction(user_id)
assert transaction.source_type == "lottery_points"
```

#### Scenario: 抽奖奖品source_type
```python
# Given: 抽奖获得奖品
# When: 创建奖励流水
add_reward_transaction(user_id, reward_id, 1, "lottery_reward", task_id)

# Then: source_type正确
transaction = get_reward_transaction(user_id)
assert transaction.source_type == "lottery_reward"
```

## ADDED Requirements

### Requirement: lottery_reward枚举值
系统MUST在TransactionSource枚举中新增LOTTERY_REWARD值。

**优先级**: P1

#### Scenario: 枚举值可用
```python
# Given: 导入枚举
from src.config.game_config import TransactionSource

# When: 访问lottery_reward
source = TransactionSource.LOTTERY_REWARD

# Then: 值正确
assert source == "lottery_reward"
```
