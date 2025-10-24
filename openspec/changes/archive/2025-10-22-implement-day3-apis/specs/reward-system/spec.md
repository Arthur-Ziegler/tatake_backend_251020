## ADDED Requirements
### Requirement: Rewards Catalog with Environment Configuration
系统 SHALL 提供奖品目录查询功能，奖品数据从环境配置初始化。

#### Scenario: Get rewards catalog
- **WHEN** 用户调用GET /rewards/catalog
- **THEN** 系统返回所有可用奖品列表
- **AND** 包含奖品ID、名称、描述和积分价值
- **AND** 返回{code, message, data}统一格式

### Requirement: User Rewards Summary
系统 SHALL 提供用户奖品汇总查询功能，基于流水记录聚合计算。

#### Scenario: Get user rewards
- **WHEN** 用户调用GET /rewards/my-rewards
- **THEN** 系统返回用户拥有的奖品数量汇总
- **AND** 按奖品类型分组显示总数量
- **AND** 基于reward_transactions表SUM(quantity)聚合计算

### Requirement: Reward Recipe Management
系统 SHALL 支持奖品兑换配方管理，从环境配置加载。

#### Scenario: Initialize reward recipes
- **WHEN** 系统启动时
- **THEN** 从.env读取兑换配方配置
- **AND** 创建reward_recipes记录包含name和materials字段
- **AND** materials为JSON格式存储所需材料列表

## MODIFIED Requirements
### Requirement: Reward Transaction Model Alignment
RewardTransaction模型 SHALL 完全匹配v3文档的字段设计。

#### Scenario: Create reward transaction
- **WHEN** 记录奖励流水时
- **THEN** 使用source_type字段：task_complete_top3 | redemption | manual
- **AND** 记录source_id关联任务ID或配方ID
- **AND** 可选transaction_group关联同一兑换操作的多个记录

### Requirement: Reward Configuration Initialization
系统启动时 SHALL 从环境配置加载奖品池数据和配方。

#### Scenario: Initialize rewards from config
- **WHEN** 系统启动时
- **THEN** 从.env读取奖品配置并创建基础奖品记录
- **AND** 保留原有LLM配置，添加游戏化配置
- **AND** 创建抽奖奖品池配置