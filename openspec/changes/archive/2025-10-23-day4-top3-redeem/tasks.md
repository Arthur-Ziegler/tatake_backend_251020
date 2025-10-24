# 任务清单

## 阶段1：Day3遗留补全（0.5天）

### 1.1 修复任务完成API防刷逻辑
- [ ] 修改completion_service.py，添加防刷检查逻辑
- [ ] 在complete_task开头检查：if task.last_claimed_date is not None
- [ ] 已领过奖时返回reward_earned.amount=0
- [ ] 首次领奖时设置task.last_claimed_date = date.today()
- [ ] 测试防刷场景：任务完成后再次完成返回0积分
- **验证**：curl测试同任务重复完成获0积分（无论日期）

### 1.2 修复任务完成API真实调用
- [ ] 修改completion_router.py，移除mock数据
- [ ] 真实调用TaskCompletionService.complete_task
- [ ] 测试Top3任务抽奖（50%积分/50%奖品）
- [ ] 测试普通任务固定2积分
- [ ] 验证响应格式符合v3文档
- **验证**：curl测试返回真实流水记录ID

### 1.3 新增奖品兑换API端点
- [ ] 在reward/api.py添加`POST /rewards/redeem`路由
- [ ] 定义RedeemRequest schema（recipe_id字段）
- [ ] 调用RewardService.redeem_reward方法
- [ ] 实现事务组ID返回逻辑
- [ ] 实现InsufficientRewardsException结构化错误捕获
- [ ] 测试材料不足场景（返回required_materials详细列表）
- [ ] 测试兑换成功场景（消耗+产出流水）
- **验证**：使用不存在的recipe_id调用返回404

### 1.4 验证Top3 API完整性
- [ ] 测试设置Top3（300积分消耗）
- [ ] 验证日期约束（仅当天或次日）
- [ ] 验证每日限制（重复设置失败）
- [ ] 测试积分不足场景（<300失败）
- [ ] 测试任务所有权验证（他人任务失败）
- **验证**：积分<300时调用set_top3返回错误

## 阶段2：Day4新增功能（1.5天）

### 2.1 修复Repository查询bug
- [ ] 全项目搜索execute(statement).all()模式
- [ ] 修复reward/repository.py中get_all_rewards添加scalars()
- [ ] 修复reward/repository.py中get_all_recipes添加scalars()
- [ ] 验证返回对象类型（非元组）
- [ ] 测试查询返回正确的对象列表
- **验证**：print(type(rewards[0]))输出Reward而非tuple

### 2.2 扩展InsufficientRewardsException
- [ ] 修改reward/exceptions.py添加required_materials参数
- [ ] 更新__init__方法接收List[Dict]类型
- [ ] 保存required_materials到实例属性
- [ ] 测试异常创建包含材料列表
- **验证**：raise异常后能访问e.required_materials属性

### 2.3 实现奖品/配方初始化逻辑
- [ ] 新建reward/database.py文件
- [ ] 实现initialize_reward_database(session)函数
- [ ] 从game_config.get_default_rewards()读取配置
- [ ] 按name查询奖品是否存在，不存在则创建（自动生成UUID）
- [ ] 从game_config.get_default_recipes()读取配方
- [ ] 配方的result_reward_id通过name查询转换为UUID
- [ ] materials保持字符串ID格式（name）
- [ ] 在src/api/main.py的lifespan中调用初始化
- [ ] 测试幂等性（重复初始化不报错）
- **验证**：应用启动后数据库存在默认奖品和配方

### 2.4 新增配方查询API（含完整信息填充）
- [ ] 在reward/api.py添加`GET /rewards/recipes`路由
- [ ] 在RewardService添加get_all_recipes_enriched方法
- [ ] 从RecipeRepository查询所有配方（已修复scalars）
- [ ] 对每个配方查询result_reward完整信息（id, name, description, points_value）
- [ ] 遍历materials，通过name查询Reward获取UUID和名称
- [ ] 填充enriched_materials：[{reward_id(UUID), reward_name, quantity}]
- [ ] 返回enriched配方列表
- [ ] 测试空配方场景
- [ ] 测试多配方返回包含完整奖品信息
- **验证**：curl /rewards/recipes返回材料包含reward_name字段

### 2.5 Top3积分余额集成
- [ ] 在Top3Service.__init__中注入PointsService（共享session）
- [ ] 修改set_top3方法，调用points_service.get_balance获取当前余额
- [ ] 计算remaining_balance = 当前余额 - 300
- [ ] 更新响应格式包含remaining_balance字段
- [ ] 测试余额计算准确性
- **验证**：设置Top3后返回的remaining_balance与实际余额一致

### 2.6 实现抽奖奖品池逻辑（查询所有可用奖品）
- [ ] 修改RewardService.lottery方法的Top3分支
- [ ] 50%概率时查询所有is_active=True的奖品
- [ ] 使用select(Reward).where(Reward.is_active == True)
- [ ] 添加scalars()调用获取对象列表
- [ ] 奖品池为空时保底给100积分（记录warning日志）
- [ ] 奖品池不为空时random.choice随机选择
- [ ] 调用add_user_reward添加奖品流水
- [ ] 测试is_active=True/False过滤正确性
- [ ] 测试奖品池为空保底逻辑
- **验证**：抽奖返回的奖品都是is_active=True的

## 阶段3：集成测试与数据验证（0.5天）

### 3.1 端到端游戏化流程测试
- [ ] 场景1：创建任务→设置Top3→完成任务→抽奖积分
- [ ] 场景2：创建任务→设置Top3→完成任务→抽奖奖品
- [ ] 场景3：完成任务获奖品→兑换成高级奖品
- [ ] 场景4：积分充足→设置Top3→完成多个任务→查看流水
- [ ] 验证每步操作的流水记录正确
- **验证**：完整流程无报错，所有流水记录一致

### 3.2 防刷与边界测试
- [ ] 同任务同日多次完成（仅第一次获奖）
- [ ] 积分不足设置Top3（<300失败）
- [ ] 材料不足兑换（详细错误信息）
- [ ] Top3日期非法（非当天/次日失败）
- [ ] 重复设置Top3（每日限1次）
- **验证**：所有边界场景返回正确错误码和message

### 3.3 数据一致性验证
- [ ] 积分余额 = SUM(points_transactions.amount)
- [ ] 奖品库存 = SUM(reward_transactions.quantity)
- [ ] 兑换失败时无任何流水记录
- [ ] 任务完成失败时积分未增加
- [ ] transaction_group正确关联兑换操作
- **验证**：手动查询数据库验证聚合计算正确性

## 阶段4：代码清理与文档（0.2天）

### 4.1 代码清理
- [ ] 删除completion_router.py中的注释mock代码
- [ ] 统一错误处理格式
- [ ] 补充关键方法的docstring
- [ ] 清理未使用的import

### 4.2 文档更新
- [ ] 更新API文档（新增2个端点）
- [ ] 补充.env配置说明
- [ ] 记录已知限制和未来优化点

## 依赖关系
- 任务1.1必须最先执行（防刷逻辑是核心修复）
- 任务1.2依赖1.1完成（防刷逻辑修复后才能测试真实调用）
- 任务1.3、1.4可并行执行
- 任务2.1、2.2可独立并行执行（Repository修复和异常扩展）
- 任务2.3依赖2.1完成（需要Repository修复后才能测试初始化）
- 任务2.4依赖2.1、2.2、2.3完成（需要正确查询、扩展异常、已初始化数据）
- 任务2.5依赖1.4完成（Top3 API验证通过后才能集成积分余额）
- 任务2.6依赖1.1、2.1、2.3完成（需要防刷修复、Repository修复、数据初始化）
- 阶段3依赖阶段1、2全部完成
- 阶段4最后执行

## 验收标准
- [ ] 所有API无mock数据，调用真实Service
- [ ] 防刷逻辑基于last_claimed_date非空检查（无日期比较）
- [ ] Repository.scalars()修复后查询返回对象而非元组
- [ ] InsufficientRewardsException携带required_materials结构化数据
- [ ] 应用启动自动初始化奖品和配方（幂等性）
- [ ] 配方查询API返回完整奖品信息（名称、描述等）
- [ ] Top3设置返回实时remaining_balance
- [ ] 抽奖逻辑查询所有is_active=True奖品（无固定池）
- [ ] 端到端测试通过率100%
- [ ] 防刷和边界测试全部通过
- [ ] 数据库一致性验证无误差
- [ ] openspec validate --strict通过
- [ ] focus领域代码未被修改
