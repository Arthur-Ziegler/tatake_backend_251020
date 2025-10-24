# Top3管理API规范

## MODIFIED Requirements

### Top3积分余额集成

**Requirement**: POST /tasks/top3响应必须包含实时remaining_balance，通过Top3Service依赖注入PointsService获取。

#### Scenario: 设置Top3返回实时余额
- Given 用户当前积分余额为500
- When 用户调用POST /tasks/top3设置Top3任务
- Then 系统扣除300积分
- And 查询PointsService获取最新余额
- And 返回remaining_balance=200

#### Scenario: 积分不足时设置失败
- Given 用户当前积分余额为200
- When 用户调用POST /tasks/top3
- Then 返回{code: 400, message: "积分不足"}
- And remaining_balance字段不返回（因操作失败）

### Top3验证规则

**Requirement**: 设置Top3必须验证日期约束、积分充足、每日限制、任务所有权。

#### Scenario: 日期仅能为当天或次日
- Given 当前日期为2025-10-23
- When 用户尝试设置日期为2025-10-25的Top3
- Then 返回{code: 400, message: "Top3只能设置为当天或次日"}

#### Scenario: 每日仅能设置一次
- Given 用户已设置2025-10-23的Top3
- When 用户再次尝试设置2025-10-23的Top3
- Then 返回{code: 400, message: "今日已设置Top3"}

#### Scenario: 任务必须属于当前用户
- Given 用户A尝试将用户B的任务设为Top3
- When 调用POST /tasks/top3
- Then 返回{code: 404, message: "任务不属于当前用户"}

### 抽奖奖品池动态查询

**Requirement**: Top3任务完成抽奖必须查询所有is_active=True的奖品，随机选择一个。

#### Scenario: 从所有可用奖品中抽取
- Given 数据库中存在多个is_active=True的奖品
- And 用户完成Top3任务且抽奖结果为奖品（50%概率）
- When 执行抽奖逻辑
- Then 系统执行select(Reward).where(Reward.is_active == True)
- And 添加scalars()调用获取对象列表
- And 从查询结果中random.choice随机选择一个奖品
- And 创建奖品流水记录，quantity=+1，source=top3_lottery

#### Scenario: 奖品池为空时保底给积分
- Given 数据库中不存在is_active=True的奖品
- And 用户完成Top3任务且抽奖结果为奖品
- When 执行抽奖逻辑
- Then 系统查询奖品池为空
- And 保底给予100积分
- And 创建积分流水记录，amount=+100，source=task_complete_top3
- And 记录warning日志："奖品池为空，给予保底积分"

#### Scenario: is_active=False的奖品不进入奖品池
- Given 数据库中存在5个奖品，其中3个is_active=True，2个is_active=False
- When 执行抽奖查询
- Then 查询结果仅包含3个is_active=True的奖品
- And 2个is_active=False的奖品被过滤
