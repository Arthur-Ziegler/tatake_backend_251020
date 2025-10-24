# 任务完成API规范

## MODIFIED Requirements

### 任务完成端点实现

**Requirement**: POST /tasks/{id}/complete必须调用真实Service，移除mock数据，实现完整的任务完成→奖励发放→流水记录流程。

#### Scenario: 普通任务完成获得2积分
- Given 用户拥有一个状态为pending的普通任务
- And 该任务不在当日Top3列表中
- When 用户调用POST /tasks/{task_id}/complete
- Then 系统更新任务状态为completed
- And 创建积分流水记录，amount=+2，source=task_complete
- And 返回reward_earned包含type=points, amount=2

#### Scenario: Top3任务完成抽奖获得100积分
- Given 用户拥有一个状态为pending的任务
- And 该任务在当日Top3列表中
- And 抽奖结果为积分（50%概率）
- When 用户调用POST /tasks/{task_id}/complete
- Then 系统更新任务状态为completed
- And 创建积分流水记录，amount=+100，source=task_complete_top3
- And 返回reward_earned包含type=points, amount=100

#### Scenario: Top3任务完成抽奖获得随机奖品
- Given 用户拥有一个状态为pending的任务
- And 该任务在当日Top3列表中
- And 抽奖结果为奖品（50%概率）
- When 用户调用POST /tasks/{task_id}/complete
- Then 系统更新任务状态为completed
- And 查询所有is_active=True的奖品，随机选择一个
- And 若奖品池为空，保底给100积分
- And 创建奖品流水记录，quantity=+1，source=top3_lottery
- And 返回reward_earned包含type=reward, reward_id, amount=1
- And 设置任务的last_claimed_date为当天日期

#### Scenario: 防刷检查基于last_claimed_date非空（核心修复）
- Given 用户拥有一个任务
- And 该任务的last_claimed_date字段不为None（无论日期值）
- When 用户调用POST /tasks/{task_id}/complete
- Then 返回reward_earned.amount=0
- And 不创建任何积分或奖品流水记录
- And task.status可以更新但不影响防刷判断
- And 响应说明"已领取过奖励"

#### Scenario: 首次完成任务设置last_claimed_date
- Given 用户拥有一个状态为pending的任务
- And 该任务的last_claimed_date为None
- When 用户调用POST /tasks/{task_id}/complete并成功领取奖励
- Then 系统设置task.last_claimed_date = date.today()
- And 更新task.status = COMPLETED
- And 创建相应的积分或奖品流水记录
- And 该任务后续无法再次领取奖励（即使状态改回pending）

### 响应格式规范

**Requirement**: 任务完成API响应必须符合v3文档定义的统一格式。

#### Scenario: 成功响应包含完整信息
- Given 任务完成成功
- When 返回响应
- Then 响应格式为{code: 200, message: "任务完成", data: {...}}
- And data包含task字段（任务完整信息）
- And data包含reward_earned字段（type, transaction_id, amount, reward_id）
