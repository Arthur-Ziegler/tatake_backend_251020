# 设计文档：奖励系统重构v4

## 核心设计决策

### 1. 纯流水记录架构
**决策**：删除`stock_quantity`，采用100%流水记录

**理由**：
- 单一数据源，消除冗余
- 完整的审计追踪
- 灵活的库存策略（通过流水记录调整）

**实现**：
```sql
-- 查询用户奖品余额
SELECT reward_id, SUM(quantity) as balance
FROM reward_transactions
WHERE user_id = ?
GROUP BY reward_id
HAVING balance > 0;

-- Top3抽奖无需库存检查
SELECT id FROM rewards WHERE is_active = true;
```

### 2. 积分兑换vs抽奖
**路径设计**：
1. 任务完成 → 2积分（确定性）
2. Top3抽奖 → 100积分或奖品（随机性）
3. 积分兑换 → 奖品（确定性，用户选择）

**平衡机制**：
- 抽奖：低成本（完成任务），高不确定性
- 兑换：高成本（消耗积分），确定获得目标奖品

### 3. 番茄钟会话管理
**并发控制**：用户同时只能有1个进行中会话

**实现策略**：
```python
def create_session(user_id, task_id, session_type):
    # 1. 关闭旧会话
    db.execute("""
        UPDATE focus_sessions
        SET end_time = NOW()
        WHERE user_id = ? AND end_time IS NULL
    """, user_id)

    # 2. 创建新会话
    new_session = FocusSession(
        user_id=user_id,
        task_id=task_id,
        session_type=session_type,
        start_time=NOW(),
        end_time=None
    )
    db.add(new_session)
```

## 数据库迁移策略

### 迁移脚本伪代码
```sql
-- Step 1: 备份数据
CREATE TABLE rewards_backup AS SELECT * FROM rewards;

-- Step 2: 删除字段
ALTER TABLE rewards DROP COLUMN stock_quantity;
ALTER TABLE rewards DROP COLUMN cost_type;
ALTER TABLE rewards DROP COLUMN cost_value;

-- Step 3: 验证数据完整性
SELECT COUNT(*) FROM reward_transactions; -- 确保流水记录完整

-- Step 4: 清理索引
DROP INDEX IF EXISTS idx_reward_stock;
```

## API变更影响分析

### 影响范围
| API端点 | 变更类型 | 影响 |
|---------|----------|------|
| `POST /tasks/{id}/complete` | 响应格式修改 | 前端需调整字段名 |
| `POST /focus/sessions` | 行为增强 | 无破坏性变更 |
| `GET /rewards/catalog` | 无变更 | 无影响 |
| `POST /rewards/redeem` | 逻辑简化 | 后端优化，前端无感知 |

### 前端适配要点
```typescript
// 修改前
interface CompleteTaskResponse {
  completion_result: {...}
  lottery_result?: {...}
}

// 修改后（符合v3）
interface CompleteTaskResponse {
  task: Task
  reward_earned: {
    type: 'points' | 'reward'
    transaction_id: string
    reward_id: string | null
    amount: number
  }
}
```

## 配置管理优化

### 保留配置
```python
# game_config.py
class TransactionSource(str, Enum):
    TASK_COMPLETE = "task_complete"
    LOTTERY_POINTS = "lottery_points"
    LOTTERY_REWARD = "lottery_reward"
    REDEMPTION = "redemption"

# Top3抽奖安慰奖积分
TOP3_LOTTERY_CONSOLATION_POINTS = 100
```

### 删除配置
```python
# ❌ 删除（改为数据库动态查询）
lottery_reward_pool = ["gold_coin", "diamond"]
default_rewards = [...]
default_recipes = [...]
```

## 测试策略

### 关键测试场景
1. **纯流水记录验证**
   - 创建多个奖品流水
   - 验证SUM聚合正确性
   - 验证负数流水（合成消耗）

2. **无限供应验证**
   - 连续抽奖100次
   - 验证不报库存不足错误
   - 验证流水记录完整

3. **番茄钟并发控制**
   - 快速连续创建会话
   - 验证只有1个进行中会话
   - 验证旧会话自动关闭

## 回滚计划
如遇严重问题，可通过以下步骤回滚：
1. 恢复`stock_quantity`字段（从备份表）
2. 恢复旧API响应格式（兼容层）
3. 回滚数据库迁移脚本
