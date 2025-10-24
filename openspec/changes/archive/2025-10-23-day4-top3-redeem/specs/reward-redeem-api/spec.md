# 奖品兑换API规范

## ADDED Requirements

### 兑换端点实现

**Requirement**: 新增POST /rewards/redeem端点，实现基于配方的奖品兑换功能，支持材料验证和原子操作。

#### Scenario: 材料充足时成功兑换
- Given 用户拥有10个小金币奖品
- And 存在配方：10个小金币→1个钻石
- When 用户调用POST /rewards/redeem {recipe_id: "gold_to_diamond"}
- Then 系统验证材料充足
- And 在同一事务中执行：
  - 创建奖品流水记录，quantity=-10，source=recipe_consume
  - 创建奖品流水记录，quantity=+1，source=recipe_produce
- And 两条记录使用相同的transaction_group关联
- And 返回{code: 200, data: {transaction_group, consumed_materials, produced_rewards}}

#### Scenario: 材料不足时兑换失败并返回结构化错误
- Given 用户仅拥有5个小金币奖品
- And 存在配方：10个小金币→1个钻石
- When 用户调用POST /rewards/redeem {recipe_id: "gold_to_diamond"}
- Then 系统抛出InsufficientRewardsException异常
- And 异常携带required_materials结构化数据
- And 返回{code: 400, message: "材料不足", data: {required: [{reward_id: "uuid", reward_name: "小金币", required: 10, owned: 5}]}}
- And 不创建任何流水记录

#### Scenario: 配方不存在时兑换失败
- Given 用户提供不存在的recipe_id
- When 用户调用POST /rewards/redeem {recipe_id: "invalid_recipe"}
- Then 返回{code: 404, message: "配方不存在"}

### 事务一致性保证

**Requirement**: 兑换操作必须确保原子性，失败时所有流水记录回滚。

#### Scenario: 兑换过程中断时全部回滚
- Given 用户拥有充足材料
- When 执行兑换操作
- And 扣除材料成功但添加结果失败
- Then 所有流水记录回滚
- And 用户材料库存不变
- And 返回错误响应
