# Service Layer Core Logic Implementation

## ADDED Requirements

### 1. Points Transaction Service

**Requirement**: 实现基于points_transactions表的积分事务管理和余额计算服务

#### Scenario: 积分流水记录创建
- 当用户完成任务时，系统应该在points_transactions表中创建积分记录

#### Scenario: 实时积分余额计算
- 当查询用户积分余额时，系统应该使用纯SQL聚合查询：`SELECT COALESCE(SUM(amount), 0) FROM points_transactions WHERE user_id = :user_id`
- 不使用任何索引优化或缓存机制，保持简单实现
- 使用标准数据库事务确保操作原子性

### 2. Reward Transaction Service

**Requirement**: 实现基于reward_transactions表的奖励事务管理和库存计算服务

#### Scenario: 奖励发放记录
- 当用户获得奖励时，系统应该在reward_transactions表中创建奖励记录

#### Scenario: 实时奖励库存计算
- 当查询用户奖品库存时，系统应该使用纯SQL聚合查询：`SELECT SUM(CASE WHEN transaction_type = 'earned' THEN quantity WHEN transaction_type = 'consumed' THEN -quantity END) FROM reward_transactions WHERE user_id = :user_id AND reward_id = :reward_id`
- 不使用任何索引优化或缓存机制，保持简单实现
- 使用标准数据库事务确保操作原子性

### 3. Task Completion Service

**Requirement**: 实现任务完成和防刷机制

#### Scenario: 任务完成验证
- 当用户标记任务完成时，系统应该验证last_claimed_date防止重复领奖

#### Scenario: 任务状态更新
- 当任务完成并发放奖励后，系统应该更新任务状态和完成度
- 完成度计算采用递归算法，不限制递归深度，不考虑性能优化
- 递归更新所有父任务链，直到根任务为止

### 4. Top3 Service

**Requirement**: 实现每日重要任务设置和抽奖功能

#### Scenario: Top3任务设置
- 当用户设置Top3任务时，系统应该扣除300积分并记录任务

#### Scenario: Top3抽奖逻辑
- 当用户完成Top3任务时，系统应该执行50%概率抽奖
- 50%概率获得100积分，50%概率获得随机奖品
- 随机奖品选择：预设3个奖品，中奖后从中随机选择一个
- 所有抽奖结果使用UTC时间记录

### 5. Redemption Service

**Requirement**: 实现基于配方的奖励兑换系统

#### Scenario: 材料充足性验证
- 当用户发起兑换时，系统应该验证用户是否拥有足够的材料

#### Scenario: 原子兑换操作
- 当验证通过后，系统应该使用事务确保兑换操作的原子性

## MODIFIED Requirements

### 1. Remove Tomato Clock Functionality

**Requirement**: 彻底删除番茄钟功能

#### Scenario: 删除番茄钟字段
- 从Task模型和Schema中删除estimated_pomodoros和actual_pomodoros字段
- 清理文件列表：src/domains/task/schemas.py, src/domains/task/service.py, src/domains/task/tests/conftest.py, src/domains/task/tests/test_tree_structure.py
- 清理内容：删除所有estimated_pomodoros和actual_pomodoros字段引用和使用

### 2. Remove UserReward Code

**Requirement**: 彻底删除UserReward相关代码

#### Scenario: 删除UserReward引用
- 从所有服务层代码中删除UserReward导入和使用
- 清理文件列表：src/domains/reward/repository.py, src/domains/reward/schemas.py, src/domains/reward/service.py
- 清理内容：删除UserReward类导入、方法调用和Schema定义
- 不需要额外的Repository层隔离，直接在Service中处理数据库操作

### 3. Implement Simple Transaction Management

**Requirement**: 采用简单的事务管理确保操作原子性

#### Scenario: 基础事务管理
- 当执行需要原子性的操作时（如兑换、奖励发放），系统应该使用标准数据库事务
- 事务边界：操作成功则commit，失败则rollback
- 使用SQLAlchemy的session事务管理，不添加额外的锁机制
- 事务超时处理：使用数据库默认超时设置，超时直接失败
- 事务使用策略：仅在必要的Service方法中使用，不是每个方法都需要
- 所有时间字段使用UTC时区存储

## REMOVED Requirements

### 1. Legacy Tomato Clock APIs

**Requirement**: 移除番茄钟API接口

#### Scenario: 删除番茄钟路由
- 删除所有与番茄钟相关的API路由和处理器

### 2. UserReward Direct Operations

**Requirement**: 移除UserReward直接操作

#### Scenario: 删除UserReward CRUD
- 删除直接操作UserReward表的所有业务逻辑