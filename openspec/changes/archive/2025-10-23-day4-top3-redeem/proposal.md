# Day3遗留+Day4完整实现：Top3+兑换系统

## Why
Day3任务完成API仅返回mock数据，奖品兑换API端点缺失，Top3 API未经测试验证。Day4需补全Day3遗留，实现完整的Top3设置、奖品兑换、配方查询功能闭环，并修复关键bug。

## What Changes

### Day3遗留任务补全
1. **修复任务完成API**：移除mock数据，真正调用TaskCompletionService，实现防刷（基于last_claimed_date）、抽奖、流水记录完整流程
2. **修复防刷逻辑bug**：检查`last_claimed_date is not None`即判定已领奖，与日期值无关
3. **新增奖品兑换API**：在reward/api.py中添加`POST /rewards/redeem`端点，实现材料验证和原子操作
4. **验证Top3 API**：测试300积分消耗、日期约束、每日限制、积分余额实时更新

### Day4新增功能
1. **新增配方查询API**：`GET /rewards/recipes`返回完整奖品信息，包含result_reward和required_rewards详情
2. **Top3积分余额集成**：Top3Service依赖注入PointsService，返回实时remaining_balance
3. **奖品/配方初始化**：从.env加载配置，字符串ID作为名称，自动生成UUID主键
4. **Repository修复**：修复get_all_rewards/recipes中的scalars()缺失问题
5. **异常扩展**：InsufficientRewardsException携带required_materials结构化数据

### 关键技术决策
- **字段名统一为materials**：数据库和Python模型都使用materials，不改为required_rewards（简化实现）
- **防刷逻辑简化**：只检查`last_claimed_date is not None`，不关心日期具体值
- **兑换逻辑整合**：RedemptionService集成到RewardService简化架构
- **Service依赖注入**：Top3Service注入PointsService获取实时余额
- **抽奖奖品池**：查询所有`is_active=True`的奖品，不限制特定池
- **错误码简化**：使用HTTP基础编码（400/404等），不新增自定义业务码
- **focus领域处理**：保留focus代码但Day4不涉及、不测试、不修改

## Impact
- **Affected APIs**:
  - 修改：`POST /tasks/{id}/complete`（移除mock，修复防刷逻辑）
  - 新增：`POST /rewards/redeem`（奖品兑换）
  - 新增：`GET /rewards/recipes`（配方查询，返回完整信息）
  - 修改：`POST /tasks/top3`（集成积分余额）
- **Affected Services**: TaskCompletionService、RewardService、Top3Service、RewardRepository、RecipeRepository
- **Affected Config**: .env奖品/配方初始化配置（字符串ID = 名称）
- **Database**: 新增reward/database.py初始化逻辑，无表结构变更
- **Not Affected**: focus领域完全不涉及

## Technical Details

### 防刷逻辑修复（关键bug修复）
```python
# src/domains/task/completion_service.py
def complete_task(task_id: UUID, user_id: UUID):
    task = self.task_repository.get_by_id(task_id, user_id)

    # 防刷检查：last_claimed_date不为空就不能再领奖（与日期值无关）
    if task.last_claimed_date is not None:
        return {
            "task": task,
            "reward_earned": {"type": "points", "amount": 0, "transaction_id": None}
        }

    # 正常奖励流程
    is_top3 = self._check_is_top3_task(task_id, user_id)
    reward = self._handle_reward(task_id, user_id, is_top3)

    # 更新last_claimed_date和status
    task.last_claimed_date = date.today()
    task.status = TaskStatusConst.COMPLETED
    self.task_repository.update(task_id, user_id, task)

    return {"task": task, "reward_earned": reward}
```

### 奖品/配方初始化逻辑
```python
# src/domains/reward/database.py (新文件)
def initialize_reward_database(session: Session):
    """
    从.env配置初始化奖品和配方数据

    策略：
    1. .env中字符串ID就是奖品名称（如"gold_coin" -> "小金币"）
    2. 自动生成UUID作为主键
    3. 按name检查是否已存在，不存在则创建
    """
    config = RewardConfig()

    # 初始化奖品
    for reward_data in config.get_default_rewards():
        existing = session.execute(
            select(Reward).where(Reward.name == reward_data["name"])
        ).scalar_one_or_none()

        if not existing:
            reward = Reward(
                id=uuid4(),  # 自动生成UUID
                name=reward_data["name"],
                description=reward_data["description"],
                points_value=reward_data["points_value"],
                category=reward_data["category"],
                is_active=reward_data["is_active"],
                cost_type="points",
                cost_value=reward_data["points_value"]
            )
            session.add(reward)
            logger.info(f"创建奖品: {reward.name} (UUID: {reward.id})")

    session.commit()

    # 初始化配方（字符串ID通过name查询转换为UUID）
    for recipe_data in config.get_default_recipes():
        # 查询result_reward的UUID
        result_reward = session.execute(
            select(Reward).where(Reward.name == recipe_data["result_reward_id"])
        ).scalar_one()

        # 转换materials中的字符串ID为UUID（保持字符串ID，运行时查询转换）
        recipe = RewardRecipe(
            id=uuid4(),
            name=recipe_data["name"],
            result_reward_id=result_reward.id,  # UUID
            materials=recipe_data["materials"],  # 保持字符串ID格式
            is_active=recipe_data["is_active"]
        )
        session.add(recipe)
        logger.info(f"创建配方: {recipe.name}")

    session.commit()
```

### 配方查询API（返回完整奖品信息）
```python
# src/domains/reward/service.py
def get_all_recipes_enriched(self):
    """查询所有配方并填充完整奖品信息"""
    recipes = self.recipe_repo.get_all_recipes()  # 已修复scalars()
    enriched = []

    for recipe in recipes:
        # 查询result_reward详情
        result_reward = self.reward_repo.get_reward_by_id(recipe.result_reward_id)

        # 填充materials的奖品名称（通过name查询UUID）
        enriched_materials = []
        for material in recipe.materials:
            # 字符串ID是名称，查询奖品详情
            reward = session.execute(
                select(Reward).where(Reward.name == material["reward_id"])
            ).scalar_one_or_none()

            enriched_materials.append({
                "reward_id": str(reward.id) if reward else material["reward_id"],
                "reward_name": reward.name if reward else material["reward_id"],
                "quantity": material["quantity"]
            })

        enriched.append({
            "id": str(recipe.id),
            "name": recipe.name,
            "result_reward": {
                "id": str(result_reward.id),
                "name": result_reward.name,
                "description": result_reward.description,
                "points_value": result_reward.points_value
            },
            "materials": enriched_materials
        })

    return enriched
```

### Repository修复（scalars()缺失）
```python
# src/domains/reward/repository.py
class RewardRepository:
    def get_all_rewards(self) -> List[Reward]:
        statement = select(Reward)
        # 修复：添加scalars()
        return list(self.session.execute(statement).scalars().all())

class RecipeRepository:
    def get_all_recipes(self) -> List[RewardRecipe]:
        statement = select(Reward Recipe)
        # 修复：添加scalars()
        return list(self.session.execute(statement).scalars().all())
```

### 异常扩展（结构化错误）
```python
# src/domains/reward/exceptions.py
class InsufficientRewardsException(RewardException):
    def __init__(self, message: str, required_materials: List[Dict] = None):
        self.required_materials = required_materials or []
        super().__init__(
            detail=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )

# src/domains/reward/api.py
@router.post("/redeem")
async def redeem_reward(request: RedeemRequest, session: SessionDep):
    try:
        result = service.redeem_reward(user_id, request.recipe_id)
        return StandardResponse.success(data=result.model_dump())
    except InsufficientRewardsException as e:
        # 返回结构化错误
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": e.detail,
                "data": {"required": e.required_materials}
            }
        )
```

### 抽奖逻辑（查询所有可用奖品）
```python
# src/domains/reward/service.py
def lottery(self, user_id: UUID, task_id: UUID, is_top3: bool):
    if not is_top3:
        # 普通任务：固定2积分
        self.points_repo.add_transaction(user_id, 2, "task_complete", task_id)
        return LotteryResult(type="points", amount=2)

    # Top3任务：抽奖
    if random.random() < 0.5:
        # 50%概率：100积分
        self.points_repo.add_transaction(user_id, 100, "task_complete_top3", task_id)
        return LotteryResult(type="points", amount=100)
    else:
        # 50%概率：随机奖品（查询所有is_active=True的奖品）
        statement = select(Reward).where(Reward.is_active == True)
        rewards = self.session.execute(statement).scalars().all()

        if not rewards:
            # 保底：给100积分
            self.points_repo.add_transaction(user_id, 100, "task_complete_top3", task_id)
            logger.warning("奖品池为空，给予保底积分")
            return LotteryResult(type="points", amount=100)

        # 随机选一个奖品
        reward = random.choice(rewards)
        self.reward_repo.add_user_reward(user_id, reward.id, quantity=1)
        return LotteryResult(type="reward", reward=self._to_reward_response(reward))
```

## Validation Plan

### 功能验证
- [ ] 任务完成API返回真实数据（无mock）
- [ ] 防刷机制：last_claimed_date不为None时返回amount=0
- [ ] Top3任务完成：50%概率100积分，50%概率随机奖品
- [ ] 积分余额计算正确（SUM聚合）
- [ ] 配方查询返回完整奖品信息（名称、描述等）
- [ ] 兑换材料验证：不足时返回结构化错误（required列表）
- [ ] 兑换原子操作：失败时全部回滚
- [ ] Top3设置消耗300积分且返回实时余额
- [ ] Top3日期约束：仅能设置当天或次日
- [ ] Repository.scalars()修复后查询正常

### 集成测试场景
1. **完整游戏化流程**：创建任务→设置Top3→完成任务→抽奖→兑换奖品
2. **防刷场景**：任务完成后再次完成，验证amount=0
3. **积分不足场景**：积分<300时设置Top3失败
4. **材料不足场景**：奖品数量不足时兑换返回详细错误
5. **事务一致性**：兑换失败时无任何流水记录
6. **奖品初始化**：应用启动自动创建奖品和配方

## Deliverables
- [ ] 修复后的completion_service.py（防刷逻辑）
- [ ] 新建的reward/database.py（初始化逻辑）
- [ ] 修复后的reward/repository.py（scalars()）
- [ ] 扩展的reward/api.py（redeem+recipes端点）
- [ ] 扩展的reward/exceptions.py（结构化错误）
- [ ] 更新的top3/service.py（PointsService依赖注入）
- [ ] 完整的端到端测试用例
- [ ] 数据一致性验证脚本

## Risks & Mitigations
- **风险1**：字符串ID与UUID映射失败→初始化时严格验证name存在性
- **风险2**：Service循环依赖→严格控制依赖方向（Top3→Points单向）
- **风险3**：事务并发冲突→使用数据库默认隔离级别，MVP阶段可接受
- **风险4**：Repository scalars()修复遗漏→全项目搜索类似问题

## Out of Scope
- focus领域的任何修改、测试、验证（保留代码但完全不涉及）
- 性能优化和缓存机制
- 高并发场景处理
- 取消完成状态API（POST /tasks/{id}/uncomplete）
- 自定义业务错误码（使用HTTP基础编码）
