# TaKeKe API方案 v4 - 奖励系统重构版本

## 概述

本文档描述TaKeKe系统v4版本的API规范，重点实现了奖励系统的重构。v4版本基于v3规范，进一步简化和优化了奖励系统架构。

## v4核心变更

### 1. 奖励系统架构重构

**纯流水记录架构**
- 删除`rewards.stock_quantity`字段，采用100%流水记录
- 删除`rewards.cost_type`和`cost_value`字段，使用`points_value`作为统一兑换成本
- 所有奖品无限供应，通过`is_active`字段控制启用状态

**三条奖品获取路径**
1. **任务完成路径**：完成普通任务 → 2积分（确定性）
2. **Top3抽奖路径**：完成Top3任务 → 50%概率100积分 / 50%抽奖品（随机性）
3. **积分兑换路径**：使用积分兑换目标奖品（确定性，用户选择）

### 2. API响应格式标准化

**任务完成响应格式更新**
```json
{
  "code": 200,
  "data": {
    "task": {...},
    "reward_earned": {
      "type": "points|reward",
      "transaction_id": "uuid",
      "reward_id": "uuid|null",
      "amount": 10
    },
    "lottery_result": {...}, // 向后兼容保留
    "message": "任务完成成功"
  },
  "message": "success"
}
```

### 3. 番茄钟会话管理优化

**自动关闭机制**
- 用户创建新会话时，自动关闭未完成的旧会话
- 确保用户同时只有1个进行中会话

## 核心API规范

### 奖励系统API

#### 1. 获取奖品目录

**请求**
```
GET /rewards/catalog
```

**响应**
```json
{
  "code": 200,
  "data": {
    "rewards": [
      {
        "id": "reward-uuid",
        "name": "奖品名称",
        "icon": "图片URL",
        "description": "奖品描述",
        "is_exchangeable": true  // v4：所有奖品都无限供应
      }
    ],
    "total_count": 10
  }
}
```

#### 2. 兑换奖品

**请求**
```
POST /rewards/redeem
Content-Type: application/json

{
  "reward_id": "reward-uuid"
}
```

**响应**
```json
{
  "code": 200,
  "data": {
    "success": true,
    "reward": {
      "id": "reward-uuid",
      "name": "奖品名称",
      "points_value": 50
    },
    "transaction_group": "transaction-group-uuid",
    "points_deducted": 50,
    "message": "成功兑换奖品: 奖品名称"
  }
}
```

#### 3. Top3抽奖

**请求**
```
POST /top3/lottery
```

**响应**
```json
{
  "code": 200,
  "data": {
    "success": true,
    "type": "reward|points",
    "reward": {
      "id": "reward-uuid",
      "name": "奖品名称",
      "description": "奖品描述",
      "image_url": "图片URL"
    },
    "amount": 100,
    "message": "恭喜中奖！获得奖品" | "未中奖，获得100积分安慰奖"
  }
}
```

### 任务系统API

#### 1. 完成任务

**请求**
```
POST /tasks/{task_id}/complete
```

**响应（v4格式）**
```json
{
  "code": 200,
  "data": {
    "task": {
      "id": "task-uuid",
      "title": "任务标题",
      "status": "completed",
      // ... 其他任务字段
    },
    "reward_earned": {
      "type": "points|reward",
      "transaction_id": "transaction-uuid|null",
      "reward_id": "reward-uuid|null",
      "amount": 10
    },
    "lottery_result": {...}, // 仅Top3任务存在
    "message": "任务完成成功"
  }
}
```

### 专注力系统API

#### 1. 开始专注会话

**请求**
```
POST /focus/sessions
Content-Type: application/json

{
  "task_id": "task-uuid",
  "session_type": "focus|pause"
}
```

**响应**
```json
{
  "code": 200,
  "data": {
    "id": "session-uuid",
    "user_id": "user-uuid",
    "task_id": "task-uuid",
    "session_type": "focus",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": null
  }
}
```

**v4特性**：创建新会话时自动关闭用户的未完成旧会话

## 数据模型变更

### Reward模型 v4

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "points_value": "integer",  // v4：统一使用points_value作为兑换成本
  "image_url": "string",
  "category": "string",
  "is_active": "boolean",    // v4：控制奖品是否可用
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**删除字段**：
- `stock_quantity`：库存数量（改为无限供应）
- `cost_type`：成本类型（统一使用积分）
- `cost_value`：成本数值（整合到points_value）

### RewardTransaction模型（无变更）

```json
{
  "id": "string",
  "user_id": "string",
  "reward_id": "string",
  "source_type": "string",   // "task_complete_top3|redemption|lottery_reward"
  "source_id": "string",
  "quantity": "integer",     // 正数表示获得，负数表示消耗
  "transaction_group": "string",
  "created_at": "datetime"
}
```

## 业务逻辑规范

### 1. 奖品获取流程

**普通任务完成**
```
任务完成 → 获得2积分 → 记录points_transaction
```

**Top3任务完成**
```
任务完成 → 获得2积分 → 触发抽奖
                     ├─ 50%概率：随机选择活跃奖品（无库存限制）
                     └─ 50%概率：获得100积分安慰奖
```

**积分兑换**
```
选择奖品 → 检查积分余额 → 扣减积分 → 获得奖品 → 记录流水
```

### 2. 库存管理（v4变更）

**旧版本**：基于`stock_quantity`字段的库存管理
**v4版本**：无限供应，通过`reward_transactions`流水记录追踪

**查询用户奖品余额**
```sql
SELECT reward_id, SUM(quantity) as balance
FROM reward_transactions
WHERE user_id = ? AND quantity > 0
GROUP BY reward_id
```

### 3. 配置管理

**保留配置**
```python
{
  "normal_task_points": 2,           # 普通任务积分
  "top3_lottery_points_amount": 100,  # Top3安慰奖积分
  "top3_lottery_points_probability": 0.5,
  "top3_lottery_reward_probability": 0.5
}
```

**删除配置**
```python
# 以下配置改为数据库动态管理
{
  "lottery_reward_pool": [...],      # 从rewards表查询is_active=true
  "default_rewards": [...],          # 通过数据库管理奖品
  "default_recipes": [...]           # 通过数据库管理配方
}
```

## 测试覆盖

### v4测试重点

1. **数据库迁移测试**
   - 验证字段删除正确性
   - 验证数据完整性保持
   - 测试回滚功能

2. **业务逻辑测试**
   - 无限供应奖品验证
   - 纯流水记录计算
   - API响应格式验证

3. **集成测试**
   - 端到端奖品获取流程
   - 番茄钟会话管理
   - 并发场景处理

## 向后兼容性

### 保持兼容的部分

1. **基础API路径**不变
2. **核心业务逻辑**保持一致
3. **TransactionSource枚举**完整保留
4. **主要数据结构**向后兼容

### 破坏性变更

1. **任务完成响应格式**：`completion_result` → `reward_earned`
2. **奖励模型字段**：删除`stock_quantity`等字段
3. **配置管理**：部分配置项删除

## 部署指南

### 1. 数据库迁移

```bash
# 执行迁移脚本
uv run python src/domains/reward/migrations/refactor_reward_system_v4.py
```

### 2. 配置更新

确保环境变量配置正确：
- `DATABASE_URL`：数据库连接
- `NORMAL_TASK_POINTS`：普通任务积分（可选）
- `TOP3_LOTTERY_POINTS_AMOUNT`：安慰奖积分（可选）

### 3. 测试验证

```bash
# 运行v4专项测试
uv run python -m pytest tests/integration/test_refactor_reward_system_v4.py -v

# 运行迁移测试
uv run python -m pytest tests/integration/test_reward_system_v4_migration.py -v
```

## 验收标准

- [ ] 数据库无`stock_quantity`、`cost_type`、`cost_value`字段残留
- [ ] 任务完成API返回`reward_earned`字段（符合v3规范）
- [ ] 番茄钟新会话自动关闭旧会话
- [ ] 所有奖品无限供应，无库存限制
- [ ] v4文档完整覆盖3条奖品获取路径
- [ ] 所有单元测试通过（覆盖率≥98%）
- [ ] 所有集成测试通过
- [ ] API响应格式标准化完成

## 版本历史

- **v1.0**：基础API实现
- **v2.0**：UUID架构统一
- **v3.0**：奖励系统标准化
- **v4.0**：奖励系统重构（本文档）

---

**作者**：TaKeKe团队
**版本**：v4.0
**更新日期**：2025-01-26