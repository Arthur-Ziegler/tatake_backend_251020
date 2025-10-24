# TaKeKe API 完整文档

## 概述

本文档描述了TaKeKe后端系统的完整API接口，包括任务管理、奖励系统、Top3系统、积分系统等核心功能。

### 基础信息
- **基础URL**: `http://localhost:8001`
- **API版本**: v1
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

### 统一响应格式

所有API都使用统一的响应格式：

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

### 状态码说明

| HTTP状态码 | 业务状态码 | 说明 |
|-----------|-----------|------|
| 200 | 200 | 操作成功 |
| 201 | 201 | 创建成功 |
| 400 | 4001 | 请求参数错误 |
| 401 | 4002 | 未授权 |
| 403 | 4003 | 禁止访问 |
| 404 | 4004 | 资源不存在 |
| 500 | 5001 | 服务器内部错误 |

## 一、认证系统

### 1.1 用户注册

**端点**: `POST /auth/register`

**请求体**:
```json
{
  "wechat_openid": "string"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "access_token": "jwt_token_string",
    "user_id": "uuid",
    "expires_in": 3600
  }
}
```

## 二、任务管理系统

### 2.1 创建任务

**端点**: `POST /tasks/`

**请求头**:
```
Authorization: Bearer {jwt_token}
```

**请求体**:
```json
{
  "title": "完成项目文档",
  "description": "编写项目的详细技术文档",
  "priority": "medium",
  "parent_id": "uuid",
  "tags": ["文档", "项目"],
  "due_date": "2025-12-31T23:59:59Z",
  "planned_start_time": "2025-12-20T09:00:00Z",
  "planned_end_time": "2025-12-30T18:00:00Z"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "任务创建成功",
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "title": "完成项目文档",
    "description": "编写项目的详细技术文档",
    "status": "pending",
    "priority": "medium",
    "parent_id": "uuid",
    "tags": ["文档", "项目"],
    "due_date": "2025-12-31T23:59:59Z",
    "planned_start_time": "2025-12-20T09:00:00Z",
    "planned_end_time": "2025-12-30T18:00:00Z",
    "is_deleted": false,
    "completion_percentage": 0.0,
    "last_claimed_date": null,
    "created_at": "2025-10-24T10:30:00Z",
    "updated_at": "2025-10-24T10:30:00Z"
  }
}
```

### 2.2 获取任务列表

**端点**: `GET /tasks/`

**查询参数**:
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）
- `include_deleted`: 是否包含已删除任务（默认false）

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "tasks": [
      {
        "id": "uuid",
        "title": "任务标题",
        "status": "pending",
        "priority": "medium",
        "completion_percentage": 0.0,
        "created_at": "2025-10-24T10:30:00Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "page_size": 20,
      "total_count": 100,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 2.3 获取单个任务

**端点**: `GET /tasks/{task_id}`

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "title": "任务标题",
    "description": "任务描述",
    "status": "pending",
    "priority": "medium",
    "parent_id": "uuid",
    "tags": ["标签"],
    "completion_percentage": 0.0,
    "last_claimed_date": null,
    "created_at": "2025-10-24T10:30:00Z",
    "updated_at": "2025-10-24T10:30:00Z"
  }
}
```

### 2.4 更新任务

**端点**: `PUT /tasks/{task_id}`

**请求体**:
```json
{
  "title": "更新后的标题",
  "description": "更新后的描述",
  "status": "in_progress",
  "priority": "high"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "id": "uuid",
    "title": "更新后的标题",
    "description": "更新后的描述",
    "status": "in_progress",
    "priority": "high",
    "updated_at": "2025-10-24T11:00:00Z"
  }
}
```

### 2.5 完成任务 ⭐

**端点**: `POST /tasks/{task_id}/complete`

**请求体**: 无（空对象）

**响应**:
```json
{
  "code": 200,
  "message": "任务完成成功",
  "data": {
    "task": {
      "id": "uuid",
      "title": "任务标题",
      "status": "completed",
      "completion_percentage": 100.0,
      "last_claimed_date": "2025-10-24T11:00:00Z"
    },
    "completion_result": {
      "success": true,
      "points_awarded": 2,
      "reward_type": "task_complete"
    },
    "lottery_result": null,
    "parent_update": {
      "success": true,
      "updated_tasks_count": 1,
      "updated_tasks": [
        {
          "task_id": "parent_uuid",
          "completion_percentage": 50.0
        }
      ]
    },
    "message": "任务完成成功，获得2积分"
  }
}
```

**业务规则**:
- 普通任务完成获得 **2积分**
- 如果是Top3任务，将触发抽奖机制
- **防刷机制**: 每个任务终身只能获得一次奖励
- 自动更新父任务的完成度

### 2.6 取消任务完成 ⭐

**端点**: `POST /tasks/{task_id}/uncomplete`

**请求体**: 无（空对象）

**响应**:
```json
{
  "code": 200,
  "message": "取消完成成功",
  "data": {
    "task": {
      "id": "uuid",
      "title": "任务标题",
      "status": "pending",
      "completion_percentage": 0.0,
      "last_claimed_date": "2025-10-24T11:00:00Z"
    },
    "parent_update": {
      "success": true,
      "updated_tasks_count": 1
    },
    "message": "取消完成成功（注意：已发放的积分和奖励不会回收）"
  }
}
```

**注意**: 取消完成不会回收已发放的积分和奖励，但会更新父任务完成度。

### 2.7 删除任务

**端点**: `DELETE /tasks/{task_id}`

**响应**:
```json
{
  "code": 200,
  "message": "删除成功",
  "data": {
    "deleted_task_id": "uuid",
    "deleted_count": 1,
    "cascade_deleted": false
  }
}
```

## 三、积分系统

### 3.1 获取积分余额

**端点**: `GET /points/my-points?user_id={user_id}`

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "current_balance": 1250,
    "total_earned": 2000,
    "total_spent": 750,
    "net_change_today": 50
  }
}
```

### 3.2 获取积分流水

**端点**: `GET /points/transactions?user_id={user_id}&page=1&page_size=20`

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "transactions": [
      {
        "id": "uuid",
        "user_id": "uuid",
        "amount": 2,
        "source_type": "task_complete",
        "source_id": "task_uuid",
        "created_at": "2025-10-24T11:00:00Z"
      },
      {
        "id": "uuid",
        "user_id": "uuid",
        "amount": 100,
        "source_type": "lottery_points",
        "source_id": "task_uuid",
        "created_at": "2025-10-24T10:30:00Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 3,
      "total_count": 45
    }
  }
}
```

**积分来源类型**:
- `task_complete`: 普通任务完成
- `lottery_points`: Top3抽奖获得积分
- `top3_cost`: 设置Top3消耗积分
- `recipe_consume`: 配方合成消耗
- `recipe_produce`: 配方合成产生

## 四、奖励系统

### 4.1 获取奖品目录

**端点**: `GET /rewards/catalog`

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "rewards": [
      {
        "id": "gold_coin",
        "name": "小金币",
        "description": "基础奖品，可通过完成任务获得",
        "points_value": 10,
        "category": "basic",
        "is_active": true,
        "image_url": "https://example.com/gold_coin.png"
      },
      {
        "id": "diamond",
        "name": "钻石",
        "description": "珍贵奖品，可通过小金币合成",
        "points_value": 100,
        "category": "premium",
        "is_active": true,
        "image_url": "https://example.com/diamond.png"
      }
    ],
    "total_count": 2
  }
}
```

### 4.2 获取我的奖品

**端点**: `GET /rewards/my-rewards?user_id={user_id}`

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "rewards": [
      {
        "reward_id": "gold_coin",
        "reward_name": "小金币",
        "quantity": 15,
        "category": "basic",
        "description": "基础奖品"
      },
      {
        "reward_id": "diamond",
        "reward_name": "钻石",
        "quantity": 2,
        "category": "premium",
        "description": "珍贵奖品"
      }
    ],
    "total_types": 2
  }
}
```

### 4.3 获取奖品配方

**端点**: `GET /rewards/recipes`

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "recipes": [
      {
        "id": "gold_to_diamond",
        "name": "小金币合成钻石",
        "description": "使用10个小金币合成1个钻石",
        "materials": [
          {
            "reward_id": "gold_coin",
            "reward_name": "小金币",
            "quantity": 10
          }
        ],
        "result_reward": {
          "reward_id": "diamond",
          "reward_name": "钻石",
          "quantity": 1
        },
        "is_active": true
      }
    ]
  }
}
```

### 4.4 合成奖品 ⭐

**端点**: `POST /rewards/recipes/{recipe_id}/redeem`

**请求体**: 无（空对象）

**响应**:
```json
{
  "code": 200,
  "message": "合成成功",
  "data": {
    "transaction_group": "uuid",
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
    ],
    "message": "成功合成1个钻石"
  }
}
```

**业务规则**:
- 检查用户是否有足够的材料
- 使用事务确保原子性操作
- 所有操作使用同一个`transaction_group`关联

## 五、Top3系统

### 5.1 设置Top3

**端点**: `POST /tasks/top3`

**请求体**:
```json
{
  "date": "2025-10-24",
  "task_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**响应**:
```json
{
  "code": 200,
  "message": "Top3设置成功",
  "data": {
    "date": "2025-10-24",
    "top3_tasks": [
      {
        "position": 1,
        "task_id": "uuid1"
      },
      {
        "position": 2,
        "task_id": "uuid2"
      },
      {
        "position": 3,
        "task_id": "uuid3"
      }
    ],
    "points_consumed": 300,
    "remaining_balance": 700
  }
}
```

**业务规则**:
- 消耗 **300积分**
- 每天只能设置一次Top3
- 最多设置3个任务
- 任务必须属于当前用户

### 5.2 获取Top3

**端点**: `GET /tasks/top3/{date}`

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "date": "2025-10-24",
    "top3_tasks": [
      {
        "position": 1,
        "task_id": "uuid1"
      },
      {
        "position": 2,
        "task_id": "uuid2"
      }
    ]
  }
}
```

## 六、Top3抽奖机制详解 ⭐

### 6.1 抽奖触发条件

当任务满足以下条件时触发抽奖：
1. 任务状态为已完成
2. 任务在当天的Top3列表中
3. 任务未领取过奖励（`last_claimed_date`为空）

### 6.2 抽奖规则

```python
# 抽奖概率配置
LOTTERY_CONFIG = {
    "points_probability": 0.5,      # 50%概率获得积分
    "points_amount": 100,           # 积分数量
    "reward_probability": 0.5       # 50%概率获得奖品
}
```

### 6.3 抽奖结果

**获得积分**:
```json
{
  "lottery_result": {
    "reward_type": "points",
    "points": 100,
    "message": "恭喜获得100积分！",
    "transaction_id": "uuid"
  }
}
```

**获得奖品**:
```json
{
  "lottery_result": {
    "reward_type": "reward",
    "reward_id": "diamond",
    "reward_name": "钻石",
    "quantity": 1,
    "message": "恭喜获得钻石！",
    "transaction_id": "uuid"
  }
}
```

### 6.4 奖品池

所有`is_active=true`的奖品都有机会被抽中，包括：
- 小金币
- 钻石
- 其他激活的奖品

## 七、防刷机制详解 ⭐

### 7.1 任务完成防刷

**机制**: 使用`last_claimed_date`字段记录任务首次完成时间
- `last_claimed_date = null`: 未领取过奖励，可以获得奖励
- `last_claimed_date ≠ null`: 已领取过奖励，永久无法再次获得奖励

### 7.2 Top3设置防刷

**机制**: 数据库唯一约束`UNIQUE(user_id, date)`
- 每个用户每天只能设置一次Top3
- 重复设置会抛出`Top3AlreadyExistsException`

### 7.3 防刷验证示例

```python
# 第一次完成任务 - 可以获得奖励
task = get_task(task_id)  # last_claimed_date = null
reward = complete_task(user_id, task_id)  # 获得2积分，last_claimed_date = now

# 第二次完成同一任务 - 无法获得奖励
task = get_task(task_id)  # last_claimed_date = now
reward = complete_task(user_id, task_id)  # 获得0积分，已防刷
```

## 八、父任务完成度自动更新 ⭐

### 8.1 更新机制

当子任务完成或取消完成时，系统会自动递归更新所有父任务的完成度：

```python
def update_parent_completion_percentage(task_id):
    """递归更新父任务完成度"""
    task = get_task(task_id)

    # 计算当前任务的直接子任务完成度
    children = get_direct_children(task.id)
    if children:
        completed_count = sum(1 for child in children if child.status == "completed")
        completion_percentage = (completed_count / len(children)) * 100

        # 更新当前任务（如果是父任务）
        update_task(task.id, completion_percentage=completion_percentage)

    # 递归更新父任务
    if task.parent_id:
        update_parent_completion_percentage(task.parent_id)
```

### 8.2 完成度计算规则

- **叶子任务**: 完成时100%，未完成时0%
- **父任务**: 基于直接子任务的完成百分比计算
- **根任务**: 递归计算所有子任务的完成情况

### 8.3 更新示例

```
任务树结构:
根任务 (0%)
├── 子任务1 (0%) ← 完成 → (100%)
├── 子任务2 (0%) ← 完成 → (100%)
└── 子任务3 (0%)

更新过程:
1. 子任务1完成 → 根任务完成度 = 1/3 * 100% = 33.3%
2. 子任务2完成 → 根任务完成度 = 2/3 * 100% = 66.7%
3. 子任务3完成 → 根任务完成度 = 3/3 * 100% = 100%
```

## 九、错误处理

### 9.1 常见错误码

| 错误码 | 错误信息 | 说明 |
|--------|----------|------|
| 4001 | 请求参数错误 | 请求体格式或字段验证失败 |
| 4003 | 权限不足 | 任务不属于当前用户 |
| 4004 | 资源不存在 | 任务或奖品不存在 |
| 4101 | 积分不足 | 设置Top3时积分不足300 |
| 4102 | Top3已存在 | 当天已设置过Top3 |
| 4103 | 任务已完成奖励 | 任务已领取过奖励，无法重复领取 |
| 4104 | 材料不足 | 合成奖品时材料不足 |
| 5001 | 服务器内部错误 | 数据库操作失败等 |

### 9.2 错误响应示例

```json
{
  "code": 4101,
  "message": "积分不足，需要300积分，当前余额只有250积分",
  "data": {
    "required_points": 300,
    "current_balance": 250,
    "shortage": 50
  }
}
```

## 十、使用示例

### 10.1 完整的任务完成流程

```bash
# 1. 注册用户
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"wechat_openid": "test_openid_12345"}'

# 2. 创建任务
curl -X POST http://localhost:8001/tasks/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "学习Python编程",
    "description": "完成Python基础教程",
    "priority": "medium"
  }'

# 3. 完成任务
curl -X POST http://localhost:8001/tasks/{task_id}/complete \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{}'

# 4. 查看积分余额
curl -X GET "http://localhost:8001/points/my-points?user_id={user_id}" \
  -H "Authorization: Bearer {jwt_token}"
```

### 10.2 Top3设置和抽奖流程

```bash
# 1. 设置Top3（消耗300积分）
curl -X POST http://localhost:8001/tasks/top3 \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-10-24",
    "task_ids": ["task_uuid_1", "task_uuid_2"]
  }'

# 2. 完成Top3任务（触发抽奖）
curl -X POST http://localhost:8001/tasks/{top3_task_id}/complete \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{}'

# 3. 查看抽奖结果（50%概率100积分，50%概率获得奖品）
# 结果在响应的lottery_result字段中
```

### 10.3 奖品合成流程

```bash
# 1. 查看可用的配方
curl -X GET http://localhost:8001/rewards/recipes \
  -H "Authorization: Bearer {jwt_token}"

# 2. 合成奖品
curl -X POST http://localhost:8001/rewards/recipes/{recipe_id}/redeem \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{}'

# 3. 查看合成后的奖品
curl -X GET "http://localhost:8001/rewards/my-rewards?user_id={user_id}" \
  -H "Authorization: Bearer {jwt_token}"
```

## 十一、版本更新说明

### v1.0 → v1.1 主要变更

1. **任务完成奖励系统**:
   - 新增任务完成API（POST /tasks/{id}/complete）
   - 新增取消完成API（POST /tasks/{id}/uncomplete）
   - 实现积分奖励机制（普通任务2积分）
   - 实现Top3抽奖机制（50%概率100积分或奖品）

2. **防刷机制升级**:
   - 从"同日限领"升级为"终身限领"
   - 使用`last_claimed_date`字段记录首次完成时间

3. **父任务完成度自动更新**:
   - 子任务完成时自动递归更新父任务完成度
   - 基于叶子任务完成状态计算完成百分比

4. **奖励系统完善**:
   - 新增奖品合成功能
   - 事务组关联机制
   - 聚合查询优化

5. **数据格式兼容性**:
   - 支持新旧Top3数据格式
   - JSON格式修复和验证

---

**文档版本**: v1.1
**更新时间**: 2025-10-24
**维护团队**: TaKeKe开发团队
**联系方式**: 如有疑问请联系开发团队