# TaKeKe后端API方案 v3

## 一、数据库表结构设计

### 1.1 任务系统表
```sql
-- 任务主表
tasks(
  id, user_id, title, description, status, priority,
  parent_id, completion_percentage, tags, service_ids,
  due_date, planned_start_time, planned_end_time,
  is_deleted, last_claimed_date, created_at, updated_at
)
```

### 1.2 奖励系统表
```sql
-- 奖品基础信息表
rewards(id, name, description, points_value, created_at)

-- 奖品兑换配方表
reward_recipes(id, result_reward_id, required_rewards: JSON, created_at)
-- required_rewards: [{"reward_id": "uuid", "quantity": 10}]

-- 奖品流水表
reward_transactions(
  id, user_id, reward_id, quantity,
  source_type, source_id, transaction_group, created_at
)
-- source_type: lottery_reward | recipe_consume | recipe_produce
-- transaction_group: 兑换操作的多个记录关联ID

-- 积分流水表
points_transactions(id, user_id, amount, source_type, source_id, created_at)
-- source_type: task_complete | lottery_points | top3_cost | recharge
```

### 1.3 Top3系统表
```sql
-- 每日Top3记录表
task_top3(id, user_id, date, task_ids: JSON, created_at)
-- task_ids: [{"task_id": "uuid1", "position": 1}, {"task_id": "uuid2", "position": 2}]
-- 约束: UNIQUE(user_id, date)
```

### 1.4 番茄钟系统表
```sql
-- 专注会话记录表
focus_sessions(
  id, user_id, task_id, session_type,
  start_time, end_time,created_at
)
-- session_type: focus | break | long_break | pause
```

## 二、API设计规范

### 2.1 统一响应格式
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...}
}

// 错误响应
{
  "code": 4001,
  "message": "错误描述",
  "data": {}
}
```

### 2.2 任务管理API

#### 完成任务
```
POST /tasks/{id}/complete

Request:
{
  "mood_feedback": {
    "comment": "optional comment",
    "difficulty": "easy|medium|hard"
  }
}

Response:
{
  "code": 200,
  "message": "任务完成",
  "data": {
    "task": {...},
    "reward_earned": {
      "type": "points|reward",
      "transaction_id": "uuid",           // 对应的流水记录ID
      "reward_id": "uuid|null",           // 奖品ID（积分时为null）
      "amount": 10                       // 数量（积分数或奖品数）
    }
  }
}
```

#### 取消完成状态
```
POST /tasks/{id}/uncomplete

Response:
{
  "code": 200,
  "message": "已取消完成状态",
  "data": {
    "task": {...}
  }
}
```

### 2.3 奖励系统API

#### 奖品目录
```
GET /rewards/catalog

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "rewards": [
      {
        "id": "uuid",
        "name": "小金币",
        "description": "基础奖品",
        "points_value": 10
      }
    ]
  }
}
```

#### 我的奖品
```
GET /rewards/my-rewards

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "rewards": [
      {
        "reward_id": "uuid",
        "reward_name": "小金币",
        "quantity": 15                    // 聚合计算结果
      }
    ]
  }
}
```

#### 积分余额
```
GET /points/my-points

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "current_balance": 1200
  }
}
```

#### 积分流水
```
GET /points/transactions?page=1&page_size=20

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "transactions": [
      {
        "id": "uuid",
        "amount": 100,
        "source_type": "task_complete_top3",
        "source_id": "task_uuid",
        "created_at": "2025-10-22T10:30:00Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "total_count": 100
    }
  }
}
```


#### 奖品兑换
```
POST /rewards/redeem

Request:
{
  "recipe_id": "uuid"
}

Response:
{
  "code": 200,
  "message": "兑换成功",
  "data": {
    "transaction_group": "uuid",           // 本次兑换的事务组ID
    "consumed_materials": [
      {
        "reward_id": "gold_coin",
        "reward_name": "小金币",
        "quantity": -10
      }
    ],
    "produced_rewards": [
      {
        "reward_id": "diamond",
        "reward_name": "钻石",
        "quantity": 1
      }
    ]
  }
}
```

### 2.4 Top3系统API

#### 设置Top3
```
POST /tasks/top3

Request:
{
  "date": "2025-10-22",
  "tasks": [
    {"task_id": "uuid1", "position": 1},
    {"task_id": "uuid2", "position": 2}
  ]
}

Response:
{
  "code": 200,
  "message": "Top3设置成功",
  "data": {
    "date": "2025-10-22",
    "top3_tasks": [
      {
        "position": 1,
        "task": {...}
      }
    ],
    "points_consumed": 300,
    "remaining_balance": 900
  }
}
```

#### 查看Top3
```
GET /tasks/top3/{date}

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "date": "2025-10-22",
    "top3_tasks": [
      {
        "position": 1,
        "task": {...}
      }
    ]
  }
}
```

### 2.5 番茄钟系统API

#### 开始专注会话
```
POST /focus/sessions

// 备注：用户任一时刻只能有一个专注会话状态（如 focus、break、pause），每开始新会话会自动终止前一个未完成的 session 并将其状态关闭。
// 特别说明：若在专注（focus）时提交 pause，会自动终止当前专注 session，并创建一个新的 pause session。计算时，focus-pause-focus 可以累计计算专注总时长；但 break 与专注之间不会合并累计。
Request:
{
  "task_id": "uuid",
  "session_type": "focus|break|long_break|pause"
}

Response:
{
  "code": 200,
  "message": "操作成功", // 兼容专注会话、休息、暂停等各类开始
  "data": {
    "session": {
      // 会话详情：包含id、task_id、focus_id、session_type等字段
    },
    "current_time": "2025-10-22T10:30:00Z"
  }
}
```

## 三、核心业务设计

### 3.1 奖品获取机制（已实现永久防刷）
```python
def complete_task_reward(user_id, task_id):
    """
    任务完成奖励获取机制（v1.1 - 永久防刷版本）

    核心变更：从"同日限领"升级为"终身限领"
    - 使用last_claimed_date字段记录首次完成时间
    - 一旦领取过奖励，永久无法再次获得奖励
    """
    task = get_task(task_id)

    # ✅ 永久防刷检查：一旦领取过奖励，终身拒绝
    if task.last_claimed_date is not None:
        return {
            "type": "points",
            "transaction_id": None,
            "amount": 0,
            "reward_id": None,
            "message": "任务已完成奖励，无法重复获得"
        }

    if is_top3_task(user_id, task_id):
        # Top3：50%概率100积分，50%概率获得奖品
        # lottery_top3()从所有is_active=true的奖品中随机抽取
        lottery_result = lottery_top3()
        if lottery_result.type == "points":
            transaction_id = add_points_transaction(
                user_id, 100, "lottery_points", task_id
            )
            return {
                "type": "points",
                "transaction_id": transaction_id,
                "amount": 100,
                "reward_id": None
            }
        else:
            transaction_id = add_reward_transaction(
                user_id, lottery_result.reward_id, 1,
                "lottery_reward", task_id
            )
            return {
                "type": "reward",
                "transaction_id": transaction_id,
                "amount": 1,
                "reward_id": lottery_result.reward_id
            }
    else:
        # 普通任务：固定2积分（从30积分修正为2积分）
        transaction_id = add_points_transaction(
            user_id, 2, "task_complete", task_id
        )
        return {
            "type": "points",
            "transaction_id": transaction_id,
            "amount": 2,
            "reward_id": None
        }
```

### 3.2 奖品合成机制
```python
def compose_rewards(user_id, recipe_id):
    recipe = get_recipe(recipe_id)
    transaction_group = uuid4()

    # 检查材料（聚合计算）
    user_materials = get_user_materials(user_id)
    for required in recipe.required_rewards:
        if user_materials.get(required.reward_id, 0) < required.quantity:
            raise InsufficientRewards()

    # 扣除材料 + 添加结果（同一事务组）
    with db.transaction():
        consumed = []
        for required in recipe.required_rewards:
            transaction_id = add_reward_transaction(
                user_id, required.reward_id, -required.quantity,
                "recipe_consume", recipe_id, transaction_group
            )
            consumed.append({
                "reward_id": required.reward_id,
                "quantity": -required.quantity
            })

        produced = []
        transaction_id = add_reward_transaction(
            user_id, recipe.result_reward_id, 1,
            "recipe_produce", recipe_id, transaction_group
        )
        produced.append({
            "reward_id": recipe.result_reward_id,
            "quantity": 1
        })

    return {"transaction_group": transaction_group, "consumed": consumed, "produced": produced}
```

### 3.3 任务完成机制（已实现永久防刷 + 父任务自动更新）
```python
def complete_task_with_reward(user_id, task_id, mood_feedback):
    """
    任务完成机制（v1.1 - 完整实现版本）

    核心功能：
    1. ✅ 永久防刷：使用last_claimed_date实现终身限领
    2. ✅ 父任务自动更新：递归更新完成度
    3. ✅ 事务一致性：确保数据一致性
    """
    task = get_task(task_id)

    # ✅ 永久防刷检查：已领过奖则永久拒绝
    if task.last_claimed_date is not None:
        # 仍可更新任务状态，但不发放奖励
        task = update_task_status_only(task_id, "completed")
        # 递归更新父任务完成度（即使没有奖励也要更新）
        update_parent_completion_percentage(task_id)

        return {
            "task": task,
            "reward_earned": {
                "type": "points",
                "transaction_id": None,
                "amount": 0,
                "reward_id": None,
                "message": "任务已完成，但已领取过奖励"
            }
        }

    # 正常奖励流程（事务保证）
    with db.transaction():
        # 更新任务状态和首次领奖日期
        today = datetime.now(timezone.utc)
        task = update_task_and_claim_date(task_id, "completed", today)

        # 发放奖励（根据任务类型）
        reward = complete_task_reward(user_id, task_id)

        # ✅ 递归更新父任务完成度
        update_parent_completion_percentage(task_id)

    return {"task": task, "reward_earned": reward}

def update_parent_completion_percentage(task_id):
    """递归更新父任务完成度：基于叶子任务的完成情况"""
    task = get_task(task_id)
    while task.parent_id:
        parent = get_task(task.parent_id)
        leaf_tasks = get_leaf_tasks(parent.id)
        completed_count = sum(1 for leaf in leaf_tasks if leaf.status == "completed")
        completion_percentage = (completed_count / len(leaf_tasks)) * 100

        parent = update_task(parent.id, completion_percentage=completion_percentage)
        task = parent
```

### 3.4 Top3设置机制
```python
def set_top3(user_id, date, tasks_with_position):
    # 验证积分充足
    if get_points_balance(user_id) < 300:
        raise InsufficientPoints("积分不足300")

    # 检查当日是否已设置
    if get_top3(user_id, date):
        raise AlreadySetTop3("今日已设置Top3")

    # 验证任务所有权
    for task_info in tasks_with_position:
        task = get_task(task_info["task_id"])
        if task.user_id != user_id:
            raise UnauthorizedTask("任务不属于当前用户")

    # 设置Top3（JSON格式）
    with db.transaction():
        # 扣除积分
        add_points_transaction(user_id, -300, "top3_cost", None)

        # 记录Top3
        task_top3_data = [
            {"task_id": task_info["task_id"], "position": task_info["position"]}
            for task_info in tasks_with_position
        ]

        create_top3_record(user_id, date, json.dumps(task_top3_data))

    return {"points_consumed": 300, "remaining_balance": get_points_balance(user_id) - 300}

def is_top3_task(user_id, task_id):
    today = date.today()
    top3 = get_top3(user_id, today)
    if not top3:
        return False

    task_ids = [item["task_id"] for item in json.loads(top3.task_ids)]
    return task_id in task_ids
```

### 3.5 积分计算机制
```python
def get_points_balance(user_id):
    """获取用户当前积分余额"""
    result = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as balance "
        "FROM points_transactions WHERE user_id=?",
        (user_id,)
    ).fetchone()
    return result.balance

def get_points_statistics(user_id):
    """获取积分统计信息"""
    result = db.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as total_earned,
            COALESCE(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) as total_spent,
            COALESCE(SUM(CASE WHEN DATE(created_at) = DATE('now') THEN amount ELSE 0 END), 0) as net_change_today
        FROM points_transactions
        WHERE user_id=?
    """, (user_id,)).fetchone()

    return {
        "current_balance": get_points_balance(user_id),
        "total_earned": result.total_earned,
        "total_spent": abs(result.total_spent),
        "net_change_today": result.net_change_today
    }

def get_user_materials(user_id):
    """获取用户当前拥有的所有奖品（聚合计算）"""
    results = db.execute(
        "SELECT reward_id, SUM(quantity) as total "
        "FROM reward_transactions WHERE user_id=? GROUP BY reward_id",
        (user_id,)
    ).fetchall()
    return {r.reward_id: r.total for r in results if r.total > 0}
```

## 四、关键配置参数

### 4.1 奖励配置
```python
# game_config.py
REWARD_CONFIG = {
    # 基础奖励
    "normal_task_points": 2,              # 普通任务积分
    "top3_cost": 300,                    # Top3设置成本

    # Top3抽奖配置
    "top3_lottery": {
        "points_prob": 0.5,              # 抽积分概率
        "points_amount": 100,             # 抽积分数量
        "reward_prob": 0.5                # 抽奖品概率
    },

    # 奖品价值配置（示例）
    "rewards_value": {
        "gold_coin": 10,                 # 小金币价值
        "diamond": 100,                  # 钻石价值
        "chest": 500                     # 宝箱价值
    }
}

# 兑换配方配置
REWARD_RECIPES = [
    {
        "id": "gold_to_diamond",
        "result_reward_id": "diamond",
        "required_rewards": [
            {"reward_id": "gold_coin", "quantity": 10}
        ]
    },
    {
        "id": "diamond_to_chest",
        "result_reward_id": "chest",
        "required_rewards": [
            {"reward_id": "diamond", "quantity": 5}
        ]
    }
]
```

### 4.2 业务规则（v1.1 - 已实现的防刷机制）
```python
# ✅ 防刷机制（已完全实现）
# - 任务终身限领1次：通过last_claimed_date字段判断，不为None则永久拒绝
# - Top3每日限设1次：通过UNIQUE(user_id, date)约束保证
# - 无领奖冷却时间：简化设计，依赖终身限领机制
# - 防刷验证示例：
#   第一次完成任务 → 获得2积分，last_claimed_date = now
#   第二次完成任务 → 获得0积分，已防刷，last_claimed_date保持不变

# 系统约束
SYSTEM_CONSTRAINTS = {
    "top3_max_tasks": 3,                # Top3最多3个任务
    "task_title_max_length": 100,        # 任务标题最大长度
    "reward_name_max_length": 50,        # 奖品名称最大长度
    "max_task_depth": 10                 # 任务树最大深度
}
```

## 五、MVP实施计划

### 5.1 阶段划分

#### 阶段1：基础闭环（3天）
**目标**：实现任务完成→奖励发放→基础查询的完整闭环

**Day 1：数据层搭建**
- [ ] Task模型字段调整：删除番茄钟字段，增加last_claimed_date
- [ ] 建表：rewards, reward_recipes, reward_transactions, points_transactions, task_top3
- [ ] 初始化奖品和配方数据
- [ ] 验证表结构

**Day 2：核心逻辑实现**
- [ ] 积分系统：points_transactions表CRUD操作
- [ ] 奖品系统：reward_transactions表CRUD + 聚合计算逻辑
- [ ] 任务完成：防刷检查 + 奖励发放 + 完成度更新
- [ ] Top3判断和抽奖逻辑

**Day 3：基础API实现**
- [ ] POST /tasks/{id}/complete（完成+奖励）
- [ ] GET /rewards/catalog（奖品目录）
- [ ] GET /rewards/my-rewards（我的奖品）
- [ ] GET /points/balance（积分余额）
- [ ] GET /points/transactions（积分流水）

#### 阶段2：增强功能（2天）
**目标**：实现Top3设置、奖品兑换、番茄钟基础功能

**Day 4：Top3+兑换系统**
- [ ] POST /tasks/top3（设置Top3）
- [ ] GET /tasks/top3/{date}（查看Top3）
- [ ] POST /rewards/redeem（奖品兑换）
- [ ] 兑换配方验证和原子操作逻辑

**Day 5：番茄钟+集成测试**
- [ ] POST /focus/sessions（开始专注）
- [ ] POST /focus/sessions/{id}/complete（完成专注）
- [ ] 端到端集成测试：创建任务→完成→兑换奖品
- [ ] 数据一致性验证

### 5.2 具体任务清单

#### 开发任务
- [ ] 数据库模型定义和迁移脚本
- [ ] Repository层：所有表的基础CRUD操作
- [ ] Service层：核心业务逻辑实现
- [ ] API层：所有接口的请求响应处理
- [ ] 单元测试：核心业务逻辑测试用例
- [ ] 集成测试：端到端功能测试

#### 测试检查清单
- [ ] 普通任务完成获得2积分
- [ ] Top3任务完成50%概率100积分，50%概率获得奖品
- [ ] 同一任务重复完成永久获得0积分（防刷验证）
- [ ] 积分余额计算正确（SUM聚合）
- [ ] 奖品数量聚合计算正确
- [ ] 兑换配方材料验证正确
- [ ] Top3设置消耗300积分验证
- [ ] 任务完成度递归更新正确
- [ ] 长事务失败时全部回滚

## 六、重要备注

### 6.1 数据一致性（v1.1 - 已完全实现）
- **长事务保证**：任务完成→奖励发放→完成度更新，任一步失败全部回滚 ✅
- **防重复机制**：last_claimed_date字段同任务终身只能领一次奖，有效防止刷奖 ✅
- **事务组关联**：奖品兑换的多个操作用transaction_group关联，便于追踪 ✅
- **软删除兼容**：任务删除不影响Top3记录和专注会话历史 ✅
- **递归更新一致性**：父任务完成度更新也包含在事务中，保证数据一致性 ✅

### 6.2 计算逻辑
- **完成度计算**：基于叶子任务的完成状态，递归更新父任务完成百分比
- **奖品余额**：通过SUM聚合reward_transactions实时计算，无库存表
- **积分余额**：通过SUM聚合points_transactions实时计算
- **Top3判断**：通过JSON解析task_ids字段判断任务是否在当日Top3中

### 6.3 性能考虑
- **按需加载**：任务树按需查询，不预加载全部子任务
- **实时计算**：所有数据实时计算，不使用缓存
- **无优化设计**：不考虑高并发和大数据量场景，专注功能完整性
- **聚合查询优化**：用户余额查询使用数据库SUM函数，避免内存计算

### 6.4 扩展预留
- **参数化配置**：所有奖励数值和业务规则通过配置文件管理，支持A/B测试
- **LangGraph集成**：预留AI工具调用接口，支持异步任务处理
- **JSON灵活存储**：Top3的JSON格式支持后续功能扩展，如优先级、标签等
- **事务组机制**：为后续的复杂业务操作预留关联追踪能力

---

**版本**: v3.1（防刷机制升级 + 完整功能实现）
**更新时间**: 2025-10-24
**核心理念**: 流水记录，聚合计算，简单可靠，条理清晰
**主要变更**:
- ✅ 防刷机制从"同日限领"升级为"终身限领"
- ✅ 任务完成奖励系统完整实现（POST /tasks/{id}/complete）
- ✅ 普通任务积分从30修正为2积分
- ✅ Top3抽奖机制：50%概率100积分，50%概率获得奖品
- ✅ 父任务完成度自动递归更新
- ✅ 奖品配方合成系统完整实现
- ✅ source_type枚举优化：lottery_reward替代top3_lottery
- ✅ 取消任务完成功能（POST /tasks/{id}/uncomplete）
- ✅ 数据库JSON格式兼容性修复
- ✅ 完整的端到端测试验证