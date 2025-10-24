# Phase 1 Day 2 - Service Layer Core Logic Implementation

## Why
基于TaKeKe API方案v3要求，需要在Day1数据层基础上实现完整的Service层核心业务逻辑。当前系统存在番茄钟功能分散和UserReward残留代码问题，需要进行彻底的架构清理和Service层实现，建立任务完成→奖励发放→积分计算的完整闭环。

## What Changes

### 核心变更概述

**Service层架构重构**：
- 实现5个核心Service类：PointsService、RewardService、TaskService、Top3Service、RedemptionService
- 建立清晰的依赖注入关系，避免循环引用
- 使用简化的事务管理策略，确保关键操作的原子性

**数据模型彻底清理**：
- 完全删除番茄钟相关字段和功能（estimated_pomodoros、actual_pomodoros）
- 彻底清理UserReward残留代码，完全基于流水记录架构
- 统一使用UTC时区处理所有时间字段

**业务逻辑实现**：
- 纯SQL聚合查询计算积分余额和奖励库存，不考虑性能优化
- 实现50%概率的Top3抽奖算法（预设3个奖品）
- 建立基于事务组ID的奖励兑换原子操作机制
- 实现递归的任务完成度计算和防刷机制

### 技术决策

#### 1. Service层架构设计
**选择：依赖注入 + 直接数据访问**
- Service类之间允许依赖关系（PointsService → RewardService → TaskService）
- 不需要额外的Repository层，直接在Service中处理SQL操作
- 使用标准SQLAlchemy session管理数据库连接

#### 2. 事务管理策略
**选择：简化事务管理**
- 使用简单的事务上下文管理器，不实现悲观锁
- 仅在关键操作（兑换、奖励发放）中使用事务
- 事务超时使用数据库默认设置，失败直接回滚

#### 3. 数据计算方式
**选择：纯SQL聚合查询**
- 积分余额：`SELECT COALESCE(SUM(amount), 0) FROM points_transactions WHERE user_id = :user_id`
- 奖励库存：使用CASE语句聚合earned/consumed交易
- 不使用索引优化或缓存，保持简单实现

#### 4. 时间处理策略
**选择：统一UTC时区**
- 所有时间字段使用`datetime.utcnow()`存储
- 日期比较使用`date.today()`进行本地日期比较
- 防刷机制基于日期字段的比较

#### 5. 代码清理范围
**选择：彻底清理遗留代码**
- 番茄钟：删除所有estimated_pomodoros和actual_pomodoros相关代码
- UserReward：删除所有UserReward类导入、方法和Schema定义
- 测试代码：同步清理测试用例中的相关引用

## 实施计划

### Day2.1 数据模型清理 (1天)
**目标**：彻底删除番茄钟和UserReward遗留代码

**关键任务**:
- 清理Task Schema中的番茄钟字段
- 清理Task Service中的番茄钟逻辑
- 删除Reward相关代码中的UserReward引用
- 验证清理完整性

### Day2.2 核心Service实现 (3天)
**目标**：实现5个核心Service类的基础功能

**关键任务**:
- PointsService：积分流水管理和余额计算
- RewardService：奖励事务管理和库存计算
- TaskService：任务完成和奖励发放机制
- Top3Service：每日重要任务管理和抽奖
- RedemptionService：基于配方的奖励兑换系统

### Day2.3 依赖注入和事务管理 (1天)
**目标**：建立Service间依赖关系和事务边界

**关键任务**:
- Service类依赖注入配置
- 简化事务管理器实现
- 关键操作的事务边界设置

### Day2.4 集成测试和验证 (1天)
**目标**：验证完整业务流程和数据一致性

**关键任务**:
- 端到端业务流程测试
- 数据计算准确性验证
- 防刷机制有效性测试

## 验收标准

### 功能验收
- [ ] 所有Service层方法正确实现
- [ ] 积分余额计算准确性100%
- [ ] 奖励库存计算准确性100%
- [ ] 任务完成奖励机制正常工作
- [ ] Top3抽奖逻辑概率正确
- [ ] 防刷机制有效防止重复领奖
- [ ] 奖励兑换原子操作确保数据一致性

### 质量验收
- [ ] 番茄钟功能完全删除
- [ ] UserReward相关代码完全清理
- [ ] 代码符合项目规范，类型注解完整
- [ ] 所有Service方法有完整文档字符串
- [ ] 单元测试覆盖率>95%
- [ ] 集成测试覆盖完整业务流程

## 交付物

- [ ] 完整的Service层实现（5个核心Service类）
- [ ] 彻底清理的数据模型（无番茄钟和UserReward残留）
- [ ] 简化的事务管理系统
- [ ] 完整的单元测试套件
- [ ] 端到端集成测试用例
- [ ] 详细的技术文档和实现说明

## 风险控制

### 技术风险
- **事务并发**: 使用简化事务管理，依赖数据库默认隔离级别
- **聚合查询性能**: 按要求不考虑性能优化，后续版本可改进
- **递归计算复杂性**: 详细测试各种任务树结构边界情况

### 缓解措施
- **代码清理**: 使用grep全局搜索确保清理彻底性
- **依赖管理**: 详细设计依赖关系图，避免循环引用
- **测试覆盖**: 高覆盖率测试确保实现正确性

---

**工作量评估**: 6个工作日
**技术债务清理**: 番茄钟和UserReward彻底删除
**风险等级**: 中等（Service层重构和事务管理）