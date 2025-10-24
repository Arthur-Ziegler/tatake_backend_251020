# Recipe Synthesis Specification

## ADDED Requirements

### Requirement: 奖品配方合成
系统MUST支持多个奖品合成另一个奖品，基于reward_recipes表配置。

**优先级**: P1

#### Scenario: 10金币合成1钻石
```python
# Given: 用户有10个金币
add_reward_transaction(user_id, "gold_coin", 10, "lottery_reward", task_id)

# And: 配方配置为10金币→1钻石
recipe = RewardRecipe(
    id="gold_to_diamond",
    result_reward_id="diamond",
    required_rewards=[{"reward_id": "gold_coin", "quantity": 10}]
)

# When: 执行合成
result = reward_service.compose_rewards(user_id, "gold_to_diamond")

# Then: 扣除10金币，获得1钻石
assert result["consumed_materials"][0]["quantity"] == -10
assert result["produced_rewards"][0]["quantity"] == 1
assert result["transaction_group"] is not None
```

#### Scenario: 材料不足合成失败
```python
# Given: 用户只有5个金币（需要10个）
add_reward_transaction(user_id, "gold_coin", 5, "lottery_reward", task_id)

# When: 尝试合成
# Then: 抛出InsufficientRewardsException
with pytest.raises(InsufficientRewardsException) as exc:
    reward_service.compose_rewards(user_id, "gold_to_diamond")

assert "材料不足" in str(exc.value)
```

### Requirement: 合成事务一致性
材料扣除和结果发放MUST在同一事务中执行，使用transaction_group关联。

**优先级**: P1

#### Scenario: 合成操作原子性
```python
# Given: 用户有10金币
# When: 合成过程中数据库错误
with pytest.raises(SQLAlchemyError):
    with mock.patch('session.commit', side_effect=SQLAlchemyError):
        reward_service.compose_rewards(user_id, "gold_to_diamond")

# Then: 事务回滚，金币数量不变
balance = get_user_materials(user_id)
assert balance["gold_coin"] == 10
```

#### Scenario: transaction_group关联流水
```python
# Given: 执行合成
result = reward_service.compose_rewards(user_id, "gold_to_diamond")
group_id = result["transaction_group"]

# When: 查询流水记录
transactions = get_transactions_by_group(group_id)

# Then: 包含扣除和发放两条记录
assert len(transactions) == 2
assert transactions[0].source_type == "recipe_consume"
assert transactions[0].quantity == -10
assert transactions[1].source_type == "recipe_produce"
assert transactions[1].quantity == 1
```

### Requirement: 用户材料聚合查询
系统MUST通过聚合reward_transactions表实时计算用户奖品库存。

**优先级**: P1

#### Scenario: 聚合计算奖品数量
```python
# Given: 用户有多条奖励流水
add_reward_transaction(user_id, "gold_coin", 5, "lottery_reward")
add_reward_transaction(user_id, "gold_coin", 5, "lottery_reward")
add_reward_transaction(user_id, "gold_coin", -3, "recipe_consume")

# When: 查询用户材料
materials = reward_service.get_user_materials(user_id)

# Then: 正确聚合（5+5-3=7）
assert materials["gold_coin"] == 7
```

## REMOVED Requirements

### Requirement: 积分兑换奖品功能
**变更原因**: 与奖品配方合成功能冲突，需重构或删除
**迁移策略**: 如果现有RewardService.redeem_reward是积分换奖品，需改造为配方合成或删除
