# Day1数据层搭建设计文档

## 设计目标

为TaKeKe后端项目建立稳定、可扩展的数据层基础架构，支持SQLite JSON功能，确保与v3 API方案的完全对齐。

## 核心设计原则

### 简化优先
- **零数据迁移**: 不考虑与旧数据的兼容性，全新构建
- **最少索引**: 仅保留主键索引，简化维护
- **直接映射**: 表结构直接对应v3 API设计

### 技术选型
- **数据库**: SQLite 3.38+ (JSON兼容)
- **ORM**: SQLAlchemy 1.4+ (JSON字段支持)
- **配置管理**: Python原生+环境变量
- **测试**: pytest + 覆盖性检查

## 模型层设计

### Task模型重构
```python
# 核心变更：删除字段，简化结构
# 删除：estimated_pomodoros, actual_pomodoros, level, path
# 新增：last_claimed_date

# 数据类型优化：date字段使用DATE类型，业务层转换为时区
```

### Reward系统模型
```python
# 新增模型：RewardTransaction, PointsTransaction
# 删除模型：UserReward
# 字段设计：transaction_group支持兑换操作关联追踪
# JSON处理：直接使用SQLAlchemy JSON字段，无需序列化工具
```

### Top3系统模型
```python
# 新建模型：TaskTop3
# JSON存储：task_ids字段存储有序任务列表
# 约束：UNIQUE(user_id, date)确保唯一性
```

## 配置系统架构

### 分层配置
```python
# 1. 默认配置：game_config.py
# 2. 环境覆盖：.env文件优先级
# 3. 动态加载：支持运行时配置更新
```

### 枚举定义
```python
# TransactionSource枚举：确保类型安全和代码提示
# 严格类型：避免字符串硬编码错误
```

## 数据库架构

### 表关系图
```
tasks (1:N) reward_transactions
tasks (1:N) points_transactions
tasks (1:3) task_top3 (通过JSON)
rewards (1:N) reward_transactions
reward_recipes (1:N) reward_transactions
```

### 索引策略
```sql
-- 仅主键索引，性能问题后续解决
-- 无复合索引，简化维护
-- 无外键约束，减少复杂性
```

## JSON字段处理

### SQLite兼容性
```python
# 版本检查：确保SQLite >= 3.38.0
# JSON操作：使用原生json_extract, json_array等函数
# 聚合计算：SUM + json_array_length组合查询
```

### 配方存储
```json
{
  "required_rewards": [
    {"reward_id": "gold_coin", "quantity": 10}
  ]
}
```

## 风险控制

### 兼容性风险
- **SQLite版本**: 低于3.38.0时fallback到序列化方案
- **JSON查询**: 复杂查询的性能监控和优化准备

### 性能风险
- **全表扫描**: 接受初期性能损失，后续优化
- **JSON操作**: 监控大数据量下的JSON解析性能

## 扩展性设计

### 配置扩展
```python
# 支持热重载：watchdog监控配置文件变化
# A/B测试框架：用户分组配置支持
```

### 功能扩展
- **新字段添加**: 预留extension_fields JSON字段
- **新表创建**: 标准化表创建和初始化流程

## 质量保证

### 测试策略
- **单元测试**: 每个模型100%字段覆盖
- **集成测试**: JSON操作和SUM聚合准确性
- **兼容性测试**: 多SQLite版本环境测试

### 代码质量
- **类型注解**: 严格使用Python类型提示
- **文档字符串**: 完整的docstring和字段描述
- **代码风格**: 遵循项目统一的代码规范

---

**设计决策**: 极简架构，快速迭代，质量优先
**技术债务**: 明确记录性能和兼容性技术债务