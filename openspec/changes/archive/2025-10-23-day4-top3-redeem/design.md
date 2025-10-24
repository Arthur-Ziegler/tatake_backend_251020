# 技术设计文档

## 核心技术决策汇总

### 决策1：字段名统一为materials
**最终决定**：保持数据库字段名和Python模型都为`materials`，不改为`required_rewards`

**理由**：
- 数据库表已创建，字段名为`materials`
- 避免数据库迁移和字段映射的复杂性
- 简化实现，减少项目复杂度
- API层可自行转换命名

### 决策2：防刷逻辑简化
**实现**：只检查`last_claimed_date is not None`，不关心日期具体值

**理由**：
- 简化防刷逻辑，避免时区问题
- 一次领奖后永久不能重复领（除非手动重置）
- 允许任务重复完成（status可改回pending），但不能重复领奖

**代码**：
```python
if task.last_claimed_date is not None:
    return {"reward_earned": {"amount": 0}}  # 已领过奖，返回0

# 首次领奖
task.last_claimed_date = date.today()
```

### 决策3：奖品/配方初始化策略
**策略**：.env中字符串ID就是奖品名称，初始化时自动生成UUID

**实现流程**：
1. 应用启动时调用`initialize_reward_database()`
2. 从game_config读取default_rewards和default_recipes
3. 按name查询是否存在，不存在则创建
4. 配方的result_reward_id通过name查询转换为UUID
5. 配方的materials保持字符串ID格式，运行时查询转换

**优点**：
- 无需手动管理UUID
- .env配置简单直观
- 支持重复初始化（幂等性）

### 决策4：抽奖奖品池策略
**策略**：查询所有`is_active=True`的奖品，不限制特定池

**理由**：
- 简化配置，无需维护奖品池列表
- 灵活性高，通过is_active控制奖品可用性
- 奖品池为空时保底给100积分

**代码**：
```python
statement = select(Reward).where(Reward.is_active == True)
rewards = self.session.execute(statement).scalars().all()
reward = random.choice(rewards) if rewards else None
```

### 决策5：错误码简化
**决定**：使用HTTP基础编码（400/404等），不新增自定义业务码

**理由**：
- 减少项目复杂度
- HTTP状态码已足够表达语义
- 错误message和data提供详细信息

**映射**：
- 400：参数错误、材料不足、业务规则违反
- 404：资源不存在
- 500：服务器内部错误

## 架构决策

### RedemptionService集成到RewardService
**理由**：
- 兑换逻辑与奖励系统紧密耦合
- 避免过度拆分Service层
- RewardService已包含reward_repo和recipe_repo

### Top3Service依赖注入PointsService
**依赖图**：
```
TaskCompletionService
    ├─→ TaskService
    ├─→ Top3Service
    │       └─→ PointsService (依赖注入)
    ├─→ PointsService
    └─→ RewardService
```

**实现**：
```python
class Top3Service:
    def __init__(self, session: Session):
        self.session = session
        self.points_service = PointsService(session)  # 共享session

    def set_top3(self, user_id, request):
        balance = self.points_service.get_balance(user_id)
        if balance < 300:
            raise InsufficientPointsException(300, balance)

        # 扣除积分
        self.points_service.add_transaction(user_id, -300, "top3_cost")
        remaining = balance - 300
        return {..., "remaining_balance": remaining}
```

## 数据流设计

### 任务完成流程（含防刷修复）
```
POST /tasks/{id}/complete
    ↓
TaskCompletionService.complete_task
    ↓
1. 获取任务
2. **防刷检查**：if task.last_claimed_date is not None → 返回amount=0
3. 检测是否Top3任务
4. 抽奖逻辑：
   ├─→ 非Top3：+2积分
   └─→ Top3：50% +100积分 | 50% 随机奖品（从is_active=True中选）
5. 更新task.last_claimed_date = date.today()
6. 更新task.status = COMPLETED
7. 返回结果
```

### 奖品兑换流程（含结构化错误）
```
POST /rewards/redeem {recipe_id}
    ↓
RewardService.redeem_reward
    ↓
1. 查询配方
2. 聚合查询用户材料（通过name查询UUID）
3. 验证材料充足：
   - 不足→抛出InsufficientRewardsException(required_materials=[...])
4. 开启事务：
   ├─→ 扣除材料：add_reward_transaction(quantity=-N)
   └─→ 添加结果：add_reward_transaction(quantity=+1)
5. 返回transaction_group

API层捕获异常：
catch InsufficientRewardsException as e:
    return JSONResponse({
        "code": 400,
        "message": e.detail,
        "data": {"required": e.required_materials}
    })
```

### 配方查询流程（含完整信息）
```
GET /rewards/recipes
    ↓
RewardService.get_all_recipes_enriched
    ↓
1. 查询所有配方（修复scalars()后）
2. 对每个配方：
   a. 查询result_reward详情（通过UUID）
   b. 遍历materials：
      - 通过字符串ID（name）查询Reward
      - 填充reward_name、reward_id（UUID）
3. 返回enriched配方列表：
   {
     "id": "uuid",
     "name": "配方名",
     "result_reward": {id, name, description, points_value},
     "materials": [{reward_id, reward_name, quantity}]
   }
```

### 奖品/配方初始化流程
```
应用启动（src/api/main.py - lifespan）
    ↓
initialize_reward_database(session)
    ↓
1. 加载game_config.get_default_rewards()
2. 对每个reward_data：
   - 查询name是否存在
   - 不存在→创建Reward(id=uuid4(), name=data["name"], ...)
3. 加载game_config.get_default_recipes()
4. 对每个recipe_data：
   - 通过name查询result_reward → 获取UUID
   - 创建RewardRecipe(result_reward_id=UUID, materials=data["materials"])
   - materials保持字符串ID格式
5. 提交事务
```

## 关键bug修复

### Bug1：防刷逻辑缺失
**问题**：只检查status，未检查last_claimed_date
**修复**：
```python
# 修复前
if task.status == TaskStatusConst.COMPLETED:
    return {"already_completed": True}

# 修复后
if task.last_claimed_date is not None:
    return {"reward_earned": {"amount": 0}}
```

### Bug2：Repository.scalars()缺失
**问题**：`execute().all()`返回元组，不是对象
**修复**：
```python
# 修复前
return list(self.session.execute(statement).all())  # 返回[(Reward,), ...]

# 修复后
return list(self.session.execute(statement).scalars().all())  # 返回[Reward, ...]
```

**全项目搜索**：
```bash
grep -r "execute(statement).all()" src/domains/
# 修复所有Repository中的类似问题
```

### Bug3：InsufficientRewardsException无结构化数据
**修复**：
```python
# 修复前
raise InsufficientRewardsException(f"需要{qty}个，当前{owned}个")

# 修复后
raise InsufficientRewardsException(
    message="材料不足",
    required_materials=[
        {"reward_id": "xxx", "required": 10, "owned": 5}
    ]
)
```

## 事务管理策略

### 关键操作事务边界
1. **任务完成**：task更新 + last_claimed_date设置 + 奖励发放（原子操作）
2. **奖品兑换**：材料扣除 + 结果添加（同一transaction_group）
3. **Top3设置**：积分扣除 + Top3记录创建（原子操作）

### 事务实现
```python
try:
    # 业务逻辑
    session.commit()
except Exception as e:
    session.rollback()
    raise
```

## 错误处理设计

### 异常类扩展
```python
class InsufficientRewardsException(RewardException):
    def __init__(self, message: str, required_materials: List[Dict] = None):
        self.required_materials = required_materials or []
        super().__init__(detail=message, status_code=400)
```

### API层异常处理
```python
@router.post("/redeem")
async def redeem_reward(...):
    try:
        result = service.redeem_reward(...)
        return StandardResponse.success(data=result)
    except RecipeNotFoundException as e:
        return JSONResponse(status_code=404, content={"code": 404, "message": e.detail, "data": {}})
    except InsufficientRewardsException as e:
        return JSONResponse(status_code=400, content={"code": 400, "message": e.detail, "data": {"required": e.required_materials}})
    except Exception as e:
        return JSONResponse(status_code=500, content={"code": 500, "message": "服务器内部错误", "data": {}})
```

## 性能考虑

### MVP阶段策略（保持不变）
- 不考虑缓存
- 不考虑索引优化
- 不考虑并发锁
- 聚合查询使用SQL SUM函数

### 已知限制（新增）
1. 配方查询时需要多次数据库查询（N+1问题）
2. 字符串ID到UUID映射频繁查询name字段
3. Repository scalars()修复可能遗漏其他文件

### 未来优化方向（新增）
1. 启动时构建name→UUID映射表（内存缓存）
2. 配方查询使用JOIN减少查询次数
3. 全项目扫描并修复所有Repository查询问题

## 测试策略

### 单元测试覆盖（新增）
- initialize_reward_database()：验证幂等性
- TaskCompletionService.complete_task()：防刷逻辑
- RewardService.get_all_recipes_enriched()：完整信息填充
- Repository.scalars()：查询结果类型验证

### 集成测试场景（新增）
- 应用启动自动初始化奖品和配方
- 任务完成后再次完成返回amount=0
- 配方查询返回完整奖品信息

## 配置清单

### .env配置（无需新增TOP3_REWARD_POOL）
```bash
# 奖品配置（字符串ID = 名称）
REWARD_GOLD_COIN_NAME="小金币"
REWARD_GOLD_COIN_DESCRIPTION="基础奖品"
REWARD_GOLD_COIN_POINTS_VALUE=10

REWARD_DIAMOND_NAME="钻石"
REWARD_DIAMOND_DESCRIPTION="珍贵奖品"
REWARD_DIAMOND_POINTS_VALUE=100

# 配方配置（使用奖品名称）
RECIPE_GOLD_TO_DIAMOND_NAME="小金币合成钻石"
RECIPE_GOLD_TO_DIAMOND_MATERIALS='[{"reward_id": "小金币", "quantity": 10}]'
RECIPE_GOLD_TO_DIAMOND_RESULT="钻石"

# 奖励参数
NORMAL_TASK_POINTS=2
TOP3_COST_POINTS=300
TOP3_LOTTERY_POINTS_AMOUNT=100
```

## 兼容性说明

### focus领域处理（保持不变）
- 策略：保留代码但完全不涉及
- 原因：focus功能按v3方案属于Day5范畴
- 操作：Day4不修改、不测试、不验证focus相关代码

### 向后兼容（新增）
- 所有新增API不影响现有功能
- 数据库无表结构变更，仅添加流水记录
- 现有API响应格式保持不变
- 字段名保持materials，无需迁移
