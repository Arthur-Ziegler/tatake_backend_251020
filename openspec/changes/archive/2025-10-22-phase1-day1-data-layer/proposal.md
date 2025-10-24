# Day1数据层搭建技术方案

## 变更概述
为TaKeKe后端项目实现第一阶段Day1的数据层搭建，建立完整的表结构、模型定义和初始化数据，为后续业务逻辑实现奠定基础。

## 技术决策

### 数据库选型
- **数据库**: SQLite（JSON兼容版本验证通过）
- **ORM框架**: SQLAlchemy自动建表功能
- **JSON支持**: 直接使用SQLAlchemy的`Column(JSON)`，无需序列化工具

### 模型重构策略
- **完全重写**: 基于v3方案重构所有模型，不保留旧字段
- **索引清理**: 删除所有自定义索引，仅保留主键
- **零数据迁移**: 不考虑旧数据兼容性，全新构建

## 实施计划

### Day1.1 数据模型层搭建 (0.5天)

**目标**: 完成所有数据模型的定义和表结构创建

**任务清单**:
- [ ] Task模型重构：删除番茄钟字段，增加last_claimed_date
- [ ] Reward模型重构：简化字段，移除不必要属性
- [ ] 新增RewardRecipe模型：支持JSON字段存储配方
- [ ] 新增RewardTransaction模型：实现奖励流水记录
- [ ] 新增PointsTransaction模型：实现积分流水记录
- [ ] 新增TaskTop3模型：支持JSON存储任务位置
- [ ] 数据库连接验证：确保JSON字段兼容性

### Day1.2 配置系统搭建 (0.3天)

**目标**: 建立完整的配置管理和初始化机制

**任务清单**:
- [ ] 创建game_config.py模块：集中管理所有游戏化参数
- [ ] 定义REWARD_CONFIG：奖励数值和概率配置
- [ ] 定义REWARD_RECIPES：兑换配方数据结构
- [ ] 定义REWARDS_VALUE_MAP：奖品价值映射
- [ ] 支持环境变量加载：优先.env，其次默认配置
- [ ] 数据初始化脚本：奖品和配方数据种子化

### Day1.3 表结构验证 (0.2天)

**目标**: 验证所有表结构正确创建和基本功能测试

**任务清单**:
- [ ] 数据库连接测试：验证SQLite连接和JSON支持
- [ ] 表创建测试：确保所有表正确建立
- [ ] 模型定义验证：测试字段类型和约束
- [ ] 索引验证：确认删除了所有自定义索引
- [ ] 数据初始化测试：验证配置数据正确加载

## 关键技术细节

### 模型设计规范

#### Task模型调整
```python
class Task(BaseModel, table=True):
    # 删除字段：estimated_pomodoros, actual_pomodoros, level, path
    # 新增字段：last_claimed_date
    last_claimed_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date(timezone=True)),
        description="最后领奖日期，UTC格式，用于防刷机制"
    )
```

#### Reward系统模型
```python
class Reward(BaseModel, table=True):
    # 简化字段：仅保留核心属性
    name: str
    description: Optional[str]
    points_value: int

class RewardRecipe(BaseModel, table=True):
    id: UUID
    result_reward_id: UUID
    required_rewards: List[Dict[str, Any]] = Field(
        sa_column=Column(JSON),
        description="所需材料列表，JSON格式存储"
    )
    name: Optional[str] = Field(
        default=None,
        description="配方名称，便于前端显示"
    )

class RewardTransaction(BaseModel, table=True):
    id: UUID
    user_id: UUID
    reward_id: UUID
    quantity: int
    source_type: str
    source_id: Optional[UUID]
    transaction_group: Optional[str] = Field(
        default=None,
        description="事务组ID，用于关联兑换操作的多个流水记录"
    )
```

#### Top3系统模型
```python
class TaskTop3(BaseModel, table=True):
    id: UUID
    user_id: UUID
    date: date
    task_ids: str = Field(
        sa_column=Column(JSON),
        description="Top3任务列表，JSON格式：[{\"task_id\":\"uuid\",\"position\":1}]"
    )
    # UNIQUE约束：UNIQUE(user_id, date)
```

### 配置系统架构

#### game_config.py设计
```python
from typing import Dict, Any, List
from enum import Enum

class TransactionSource(str, Enum):
    TASK_COMPLETE = "task_complete"
    TASK_COMPLETE_TOP3 = "task_complete_top3"
    TOP3_COST = "top3_cost"
    RECIPE_CONSUME = "recipe_consume"
    RECIPE_PRODUCE = "recipe_produce"

# 集中配置管理
REWARD_CONFIG: Dict[str, Any] = {
    "normal_task_points": 2,
    "top3_cost": 300,
    "top3_lottery": {
        "points_prob": 0.5,
        "points_amount": 100,
        "reward_prob": 0.5
    }
}

REWARD_RECIPES: List[Dict[str, Any]] = [
    {
        "id": "gold_to_diamond",
        "name": "金币兑换钻石",
        "result_reward_id": "diamond",
        "required_rewards": [
            {"reward_id": "gold_coin", "quantity": 10}
        ]
    }
]
```

### 环境配置支持

#### .env配置文件
```bash
# 数据库配置
DATABASE_URL=sqlite:///./tatake.db

# 游戏化配置
REWARD_NORMAL_TASK_POINTS=2
REWARD_TOP3_COST=300
REWARD_TOP3_POINTS_PROB=0.5
```

#### 动态加载机制
```python
import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """优先加载.env配置，覆盖默认值"""
    config = DEFAULT_CONFIG.copy()

    # 环境变量覆盖
    config["normal_task_points"] = int(
        os.getenv("REWARD_NORMAL_TASK_POINTS", config["normal_task_points"])
    )

    return config
```

## 风险控制

### 技术风险
- **SQLite版本兼容性**: 确保SQLite版本>=3.38.0支持JSON
- **JSON字段性能**: 监控JSON查询性能，必要时考虑优化
- **配置热更新**: 配置文件修改需要应用重启

### 质量保证
- **严格类型检查**: 使用Python类型注解，运行时验证
- **模型约束验证**: SQLModel字段约束确保数据完整性
- **单元测试覆盖**: 覆盖所有模型定义和配置加载逻辑

## 验收标准

### 功能验收
- [ ] 所有表能够正确创建，无SQL错误
- [ ] JSON字段能够正常读写，无数据丢失
- [ ] 配置能够正确加载，支持环境变量覆盖
- [ ] 模型字段类型正确，符合SQLModel规范

### 质量验收
- [ ] 代码符合项目规范，类型注解完整
- [ ] 所有模型定义与v3方案完全一致
- [ ] 配置模块结构清晰，易于维护
- [ ] 数据库连接稳定，支持多线程操作

### 交付物
- [ ] 重构后的所有模型文件
- [ ] 完整的配置管理模块
- [ ] 数据初始化脚本
- [ ] 验证测试用例
- [ ] 技术决策文档和风险控制清单

---

**预计工作量**: 1个工作日
**依赖关系**: 无（Day1第一个任务）
**风险等级**: 低（纯数据层工作，风险可控）