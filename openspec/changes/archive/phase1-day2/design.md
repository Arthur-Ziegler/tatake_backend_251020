# Phase 1 Day 2 - Service Layer Core Logic Design

## Why

基于TaKeKe API方案v3的要求，需要在Day1数据层基础上实现完整的Service层核心业务逻辑。当前系统存在番茄钟功能分散和UserReward残留代码问题，需要进行彻底的架构清理和Service层实现。

## Technical Architecture Decisions

### 1. Service Layer Architecture

#### 依赖注入设计
- **PointsService**: 独立服务，负责积分流水管理
- **RewardService**: 依赖PointsService，负责奖励事务管理
- **TaskService**: 依赖PointsService和RewardService，负责任务完成和奖励发放
- **Top3Service**: 依赖PointsService，负责每日重要任务管理
- **RedemptionService**: 依赖RewardService和PointsService，负责奖励兑换

**设计原则**:
- Service之间允许依赖，但不能循环引用
- 不需要额外的Repository层隔离，直接在Service中处理SQL操作
- 事务仅在必要的操作中使用，不是每个方法都需要

### 2. 数据库设计

#### 流水记录架构
- **points_transactions**: 积分流水表，记录所有积分变动
- **reward_transactions**: 奖励流水表，记录所有奖励发放和消费
- **top3_tasks**: Top3任务设置表，记录每日重要任务

#### 时间处理策略
- 所有时间字段使用UTC时区存储
- 使用`datetime.utcnow()`获取当前时间
- 日期比较使用`date.today()`进行本地日期比较

### 3. 事务管理策略

#### 简化事务管理
```python
@contextmanager
def simple_transaction(session: Session):
    try:
        session.begin()
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
```

#### 使用场景
- **必须使用事务的操作**: 奖励兑换、任务完成奖励发放、Top3设置
- **不需要事务的操作**: 积分余额查询、奖励库存查询、统计查询

### 4. 纯SQL聚合查询

#### 积分余额计算
```sql
SELECT COALESCE(SUM(amount), 0)
FROM points_transactions
WHERE user_id = :user_id
```

#### 奖励库存计算
```sql
SELECT SUM(CASE
    WHEN transaction_type = 'earned' THEN quantity
    WHEN transaction_type = 'consumed' THEN -quantity
    ELSE 0
END)
FROM reward_transactions
WHERE user_id = :user_id AND reward_id = :reward_id
```

#### 积分统计查询
```sql
SELECT
    source_type,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
    SUM(amount) as net_change
FROM points_transactions
WHERE user_id = :user_id
AND DATE(created_at) BETWEEN :start_date AND :end_date
GROUP BY source_type
```

**性能策略**: 不考虑性能优化，不添加索引，不使用缓存

### 5. Top3抽奖算法

#### 抽奖逻辑
```python
def execute_lottery(self, user_id: UUID) -> LotteryResult:
    # 预设3个奖品
    PRESET_REWARDS = [
        {"id": "reward-001", "name": "咖啡券"},
        {"id": "reward-002", "name": "电影票"},
        {"id": "reward-003", "name": "游戏皮肤"}
    ]

    # 50%概率
    if random.random() < 0.5:
        # 获得积分
        return LotteryResult(type="points", value=100)
    else:
        # 获得随机奖品
        selected_reward = random.choice(PRESET_REWARDS)
        return LotteryResult(type="reward", reward=selected_reward)
```

## Service层实现细节

### 1. PointsService 实现

```python
class PointsService:
    def __init__(self, session: Session):
        self.session = session

    def calculate_balance(self, user_id: UUID) -> int:
        """计算积分余额"""
        result = self.session.execute(
            text("SELECT COALESCE(SUM(amount), 0) FROM points_transactions WHERE user_id = :user_id"),
            {"user_id": str(user_id)}
        ).scalar()
        return result or 0

    def add_points(self, user_id: UUID, amount: int, source_type: str, source_id: Optional[UUID] = None):
        """添加积分记录"""
        transaction = PointsTransaction(
            user_id=user_id,
            amount=amount,
            source_type=source_type,
            source_id=str(source_id) if source_id else None,
            created_at=datetime.utcnow()
        )
        self.session.add(transaction)

    def get_statistics(self, user_id: UUID, start_date: date, end_date: date):
        """获取积分统计"""
        result = self.session.execute(
            text("""
                SELECT source_type,
                       SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                       SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
                       SUM(amount) as net_change
                FROM points_transactions
                WHERE user_id = :user_id
                AND DATE(created_at) BETWEEN :start_date AND :end_date
                GROUP BY source_type
            """),
            {"user_id": str(user_id), "start_date": start_date, "end_date": end_date}
        ).fetchall()
        return result
```

### 2. RewardService 实现

```python
class RewardService:
    def __init__(self, session: Session, points_service: PointsService):
        self.session = session
        self.points_service = points_service

    def calculate_inventory(self, user_id: UUID, reward_id: UUID) -> int:
        """计算奖励库存"""
        result = self.session.execute(
            text("""
                SELECT SUM(CASE
                    WHEN transaction_type = 'earned' THEN quantity
                    WHEN transaction_type = 'consumed' THEN -quantity
                    ELSE 0
                END)
                FROM reward_transactions
                WHERE user_id = :user_id AND reward_id = :reward_id
            """),
            {"user_id": str(user_id), "reward_id": str(reward_id)}
        ).scalar()
        return result or 0

    def add_reward(self, user_id: UUID, reward_id: UUID, quantity: int,
                  transaction_type: str, source_type: str, source_id: Optional[UUID] = None,
                  transaction_group_id: Optional[UUID] = None):
        """添加奖励记录"""
        transaction = RewardTransaction(
            user_id=user_id,
            reward_id=reward_id,
            quantity=quantity,
            transaction_type=transaction_type,
            source_type=source_type,
            source_id=str(source_id) if source_id else None,
            transaction_group_id=str(transaction_group_id) if transaction_group_id else None,
            created_at=datetime.utcnow()
        )
        self.session.add(transaction)

    def consume_reward(self, user_id: UUID, reward_id: UUID, quantity: int,
                      transaction_type: str, transaction_group_id: Optional[UUID] = None):
        """消耗奖励"""
        self.add_reward(
            user_id=user_id,
            reward_id=reward_id,
            quantity=-quantity,
            transaction_type=transaction_type,
            source_type="consumption",
            transaction_group_id=transaction_group_id
        )
```

### 3. TaskService 实现

```python
class TaskService:
    def __init__(self, session: Session, points_service: PointsService, reward_service: RewardService):
        self.session = session
        self.points_service = points_service
        self.reward_service = reward_service

    def complete_task_with_reward(self, user_id: UUID, task_id: UUID) -> Task:
        """完成任务并发放奖励"""
        with simple_transaction(self.session):
            # 验证任务
            task = self.session.query(Task).filter_by(id=task_id).first()
            if not task:
                raise TaskNotFoundError(f"Task {task_id} not found")

            # 防刷检查
            today = date.today()
            if task.last_claimed_date == today:
                raise AlreadyClaimedError(f"Task already claimed today")

            # 判断是否为Top3任务并发放奖励
            is_top3 = self._is_top3_task(task_id)
            if is_top3:
                lottery_result = self._execute_top3_lottery(user_id)
            else:
                # 普通任务固定2积分
                self.points_service.add_points(
                    user_id=user_id,
                    amount=2,
                    source_type="task_complete",
                    source_id=task_id
                )
                lottery_result = {"type": "points", "value": 2}

            # 更新任务状态
            task.status = "completed"
            task.last_claimed_date = today
            task.completed_at = datetime.utcnow()

            # 递归更新完成度
            self._update_completion_percentage(task_id)

            return task, lottery_result

    def _is_top3_task(self, task_id: UUID) -> bool:
        """检查是否为Top3任务"""
        result = self.session.execute(
            text("SELECT 1 FROM top3_tasks WHERE task_id = :task_id AND DATE(created_at) = DATE('now')"),
            {"task_id": str(task_id)}
        ).scalar()
        return result is not None

    def _execute_top3_lottery(self, user_id: UUID):
        """执行Top3抽奖"""
        # 预设3个奖品
        preset_rewards = [
            {"id": "reward-coffee", "name": "咖啡券"},
            {"id": "reward-movie", "name": "电影票"},
            {"id": "reward-game", "name": "游戏皮肤"}
        ]

        if random.random() < 0.5:
            # 50%概率获得100积分
            self.points_service.add_points(
                user_id=user_id,
                amount=100,
                source_type="task_complete_top3"
            )
            return {"type": "points", "value": 100}
        else:
            # 50%概率获得随机奖品
            selected_reward = random.choice(preset_rewards)
            self.reward_service.add_reward(
                user_id=user_id,
                reward_id=selected_reward["id"],
                quantity=1,
                transaction_type="earned",
                source_type="task_complete_top3"
            )
            return {"type": "reward", "reward": selected_reward}

    def _update_completion_percentage(self, task_id: UUID):
        """递归更新任务完成度"""
        task = self.session.query(Task).filter_by(id=task_id).first()
        if not task or not task.parent_id:
            return

        self._recursive_update_completion(task.parent_id)

    def _recursive_update_completion(self, parent_id: UUID):
        """递归计算完成度"""
        children = self.session.query(Task).filter_by(parent_id=parent_id).all()
        total_leaf = 0
        completed_leaf = 0

        for child in children:
            child_count = self.session.query(Task).filter_by(parent_id=child.id).count()
            if child_count == 0:  # 叶子任务
                total_leaf += 1
                if child.status == "completed":
                    completed_leaf += 1

        completion_percentage = (completed_leaf / total_leaf * 100) if total_leaf > 0 else 0

        self.session.query(Task).filter_by(id=parent_id).update({
            "completion_percentage": completion_percentage
        })

        # 继续向上递归
        parent = self.session.query(Task).filter_by(id=parent_id).first()
        if parent and parent.parent_id:
            self._recursive_update_completion(parent.parent_id)
```

## Code Cleanup Strategy

### 1. 番茄钟功能清理

**需要清理的文件**:
- `src/domains/task/schemas.py` - 删除estimated_pomodoros和actual_pomodoros字段
- `src/domains/task/service.py` - 删除番茄钟相关业务逻辑
- `src/domains/task/tests/conftest.py` - 删除测试数据中的番茄钟字段
- `src/domains/task/tests/test_tree_structure.py` - 删除番茄钟相关测试用例

**清理策略**:
- 删除所有字段定义和引用
- 删除相关的业务逻辑
- 更新测试用例，移除番茄钟断言

### 2. UserReward代码清理

**需要清理的文件**:
- `src/domains/reward/repository.py` - 删除UserReward导入和方法
- `src/domains/reward/schemas.py` - 删除UserRewardResponse定义
- `src/domains/reward/service.py` - 删除UserReward相关业务逻辑

**清理策略**:
- 删除UserReward类导入
- 删除get_user_rewards和get_user_reward方法
- 删除UserRewardResponse Schema
- 移除所有UserReward相关的业务调用

## Testing Strategy

### 1. 单元测试范围

**Service层测试**:
- PointsService的积分计算和统计功能
- RewardService的库存计算和事务记录功能
- TaskService的任务完成和奖励发放功能
- Top3Service的设置和抽奖功能
- RedemptionService的兑换原子操作功能

**数据模型测试**:
- 验证番茄钟字段已完全删除
- 验证UserReward相关代码已清理
- 验证事务表结构正确性

### 2. 集成测试范围

**业务流程测试**:
- 完整的任务完成→奖励发放→积分计算流程
- Top3任务设置→完成→抽奖→奖励发放流程
- 奖励兑换的完整原子操作流程
- 积分和奖励的准确计算和统计

**防刷机制测试**:
- 验证同一天重复完成任务不会重复获得奖励
- 验证Top3任务每日只能设置一次
- 验证防刷时间戳的正确更新

## Risk Mitigation

### 1. 技术风险

**事务风险**:
- 简化事务管理可能在并发情况下出现数据不一致
- 缓解措施：使用数据库默认事务隔离级别

**性能风险**:
- 纯SQL聚合查询在大数据量下可能性能较差
- 缓解措施：后续版本可考虑添加索引优化

### 2. 业务风险

**抽奖公平性**:
- 随机数生成需要确保足够的随机性
- 缓解措施：使用Python标准库的random模块

**数据一致性**:
- 递归完成度计算可能在复杂任务树下出错
- 缓解措施：增加边界检查和错误处理

## Deployment Considerations

### 1. 数据库迁移

**表结构变更**:
- 确保points_transactions和reward_transactions表结构正确
- 验证索引约束符合业务需求
- 备份现有数据以防回滚需要

### 2. 代码部署

**向后兼容性**:
- API接口保持兼容，仅修改内部实现
- 删除的字段确保不影响现有功能
- 新增的Service功能逐步启用

**监控指标**:
- 积分和奖励计算的准确性
- 事务执行的成功率和失败率
- 关键业务操作的响应时间