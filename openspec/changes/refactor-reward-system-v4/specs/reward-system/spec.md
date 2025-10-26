# 奖励系统规范变更

## REMOVED Requirements

### REQ-RWD-001: 奖品库存字段管理
**移除原因**：违反纯流水记录设计，数据冗余

#### Scenario: 删除库存字段
- **Given** 当前`rewards`表包含`stock_quantity`字段
- **When** 执行数据库迁移
- **Then** `stock_quantity`字段被删除
- **And** 所有奖品变为无限供应
- **And** 历史流水记录不受影响

### REQ-RWD-002: 奖品成本配置
**移除原因**：积分兑换改为直接查询奖品积分价值

#### Scenario: 删除成本字段
- **Given** `rewards`表包含`cost_type`和`cost_value`字段
- **When** 执行数据库迁移
- **Then** 这些字段被删除
- **And** 保留`points_value`字段用于兑换定价

## ADDED Requirements

### REQ-RWD-003: 积分兑换奖品
**新增原因**：补充v3未覆盖的功能

#### Scenario: 用户使用积分兑换奖品
- **Given** 用户积分余额为500
- **And** 奖品"钻石"的`points_value`为100
- **When** 用户请求兑换"钻石"
- **Then** 扣除100积分
- **And** 创建`reward_transaction`记录（quantity=1, source_type="redemption"）
- **And** 返回兑换成功信息

#### Scenario: 积分不足时兑换失败
- **Given** 用户积分余额为50
- **And** 奖品"钻石"的`points_value`为100
- **When** 用户请求兑换"钻石"
- **Then** 返回错误"积分不足"
- **And** 不创建任何流水记录

### REQ-RWD-004: 纯流水记录库存查询
**新增原因**：删除库存字段后需明确聚合查询逻辑

#### Scenario: 查询用户奖品余额
- **Given** 用户有以下流水记录：
  - 抽奖获得"小金币" +10
  - 合成消耗"小金币" -5
- **When** 查询用户"小金币"余额
- **Then** 通过`SUM(quantity)`聚合计算
- **And** 返回余额5

## MODIFIED Requirements

### REQ-RWD-005: Top3抽奖机制
**修改内容**：移除库存限制，动态从数据库获取奖品池

#### Scenario: 从所有激活奖品中抽奖
- **Given** 数据库中有3个`is_active=true`的奖品
- **When** 用户完成Top3任务触发抽奖
- **Then** 从这3个奖品中随机选择1个（50%概率中奖）
- **And** 不检查库存限制
- **And** 创建`reward_transaction`记录（source_type="lottery_reward"）

#### Scenario: 无激活奖品时抽奖
- **Given** 数据库中所有奖品`is_active=false`
- **When** 用户完成Top3任务触发抽奖
- **Then** 自动发放100积分（未中奖安慰奖）
- **And** 不发放奖品

### REQ-RWD-006: 任务完成奖励响应格式
**修改内容**：对齐v3文档定义

#### Scenario: 完成普通任务的响应格式
- **Given** 用户完成普通任务
- **When** API返回响应
- **Then** 响应格式为：
  ```json
  {
    "code": 200,
    "data": {
      "task": {...},
      "reward_earned": {
        "type": "points",
        "transaction_id": "uuid",
        "reward_id": null,
        "amount": 2
      }
    }
  }
  ```
- **And** 字段名为`reward_earned`（非`completion_result`）

#### Scenario: 完成Top3任务的响应格式
- **Given** 用户完成Top3任务并中奖
- **When** API返回响应
- **Then** 响应格式为：
  ```json
  {
    "code": 200,
    "data": {
      "task": {...},
      "reward_earned": {
        "type": "reward",
        "transaction_id": "uuid",
        "reward_id": "奖品ID",
        "amount": 1
      }
    }
  }
  ```
