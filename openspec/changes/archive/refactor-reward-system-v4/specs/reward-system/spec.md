# reward-system Specification

## REMOVED Requirements

### Requirement: 奖品库存字段管理
删除`rewards`表的`stock_quantity`字段，违反v3纯流水记录设计，导致数据冗余。

#### Scenario: 删除库存字段并迁移数据
```
GIVEN 当前rewards表包含stock_quantity字段
WHEN 执行数据库迁移脚本
THEN stock_quantity字段被删除
AND 所有奖品变为无限供应
AND 历史reward_transactions流水记录不受影响
```

### Requirement: 奖品成本配置字段
删除`cost_type`和`cost_value`字段，积分兑换改为直接查询`points_value`。

#### Scenario: 删除成本字段
```
GIVEN rewards表包含cost_type和cost_value字段
WHEN 执行数据库迁移
THEN 这些字段被删除
AND 保留points_value字段用于兑换定价
```

## ADDED Requirements

### Requirement: 积分兑换奖品功能
用户 MUST 能够使用积分兑换奖品，系统 SHALL 扣除积分并创建流水记录。

#### Scenario: 用户使用积分兑换奖品
```
GIVEN 用户积分余额为500
AND 奖品"钻石"的points_value为100
WHEN 用户请求兑换"钻石"
THEN 扣除100积分
AND 创建reward_transaction记录（quantity=1, source_type="redemption"）
AND 返回兑换成功信息
```

#### Scenario: 积分不足时兑换失败
```
GIVEN 用户积分余额为50
AND 奖品"钻石"的points_value为100
WHEN 用户请求兑换"钻石"
THEN 返回错误"积分不足"
AND 不创建任何流水记录
```

### Requirement: 纯流水记录库存查询
系统 MUST 通过SUM聚合查询reward_transactions表计算用户奖品余额。

#### Scenario: 查询用户奖品余额
```
GIVEN 用户有以下流水记录：
  抽奖获得"小金币" +10
  合成消耗"小金币" -5
WHEN 查询用户"小金币"余额
THEN 通过SUM(quantity)聚合计算
AND 返回余额5
```

## MODIFIED Requirements

### Requirement: Top3抽奖机制
系统 SHALL 从所有is_active=true的奖品中随机抽奖，不检查库存限制。

#### Scenario: 从所有激活奖品中抽奖
```
GIVEN 数据库中有3个is_active=true的奖品
WHEN 用户完成Top3任务触发抽奖
THEN 从这3个奖品中随机选择1个（50%概率中奖）
AND 不检查库存限制
AND 创建reward_transaction记录（source_type="lottery_reward"）
```

#### Scenario: 无激活奖品时抽奖
```
GIVEN 数据库中所有奖品is_active=false
WHEN 用户完成Top3任务触发抽奖
THEN 自动发放100积分（未中奖安慰奖）
AND 不发放奖品
```

### Requirement: 任务完成奖励响应格式
API MUST 返回符合v3文档的`reward_earned`字段。

#### Scenario: 完成普通任务的响应格式
```
GIVEN 用户完成普通任务
WHEN API返回响应
THEN 响应格式为：
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
AND 字段名为reward_earned（非completion_result）
```

#### Scenario: 完成Top3任务的响应格式
```
GIVEN 用户完成Top3任务并中奖
WHEN API返回响应
THEN 响应格式为：
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
