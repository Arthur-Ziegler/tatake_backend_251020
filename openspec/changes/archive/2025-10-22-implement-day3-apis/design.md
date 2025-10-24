## Context
实现阶段1 Day3的完整基础API闭环，包含任务完成→奖励发放→基础查询→Top3管理的全部功能。基于现有DDD架构，严格按照v3文档设计，建立完整的游戏化任务管理系统。

## Goals / Non-Goals
- Goals: 完整的任务→奖励→查询→Top3流程，事务一致性，API响应统一
- Non-Goals: 心情反馈、过期时间、日期筛选、权重配置、并发优化

## Decisions
- API路径：去掉/api/v1/前缀，保持极简直接路径
- 配置管理：.env文件定义奖品池、配方、奖励参数，保留LLM配置
- 数据模型：RewardTransaction完全匹配v3文档字段
- 奖励机制：严格按v3文档（普通2分，Top3 50%抽奖100分）
- Top3判断：基于v3文档is_top3_task函数，查询当日Top3记录
- 事务一致性：数据库事务确保任务完成→奖励发放→完成度更新原子性
- 抽奖机制：简单随机选择，无权重配置

## Risks / Trade-offs
- 配置硬编码 → 简化部署，灵活性降低，但满足MVP需求
- 实时计算 → 数据一致性高，性能较低，但Day3不考虑性能优化
- 简化抽奖 → 开发快速，用户体验基础，但缺乏游戏深度
- 无并发处理 → 简化实现，但高并发场景有问题

## Technical Implementation Details

### 数据模型调整
```python
# RewardTransaction字段调整（匹配v3文档）
class RewardTransaction:
    user_id: str
    reward_id: str
    source_type: str  # "task_complete" | "task_complete_top3" | "redemption" | "expiration" | "manual"
    source_id: Optional[str]  # 关联的任务ID或配方ID
    quantity: int  # 正数获得，负数消耗
    transaction_group: Optional[str]  # 兑换操作的事务组ID
```

### 环境配置结构
```env
# === 保留LLM配置 ===
LLM_BASE_URL=...
OPENAI_API_KEY=...

# === 基础奖品配置 ===
REWARD_GOLD_COIN_ID="gold_coin"
REWARD_GOLD_COIN_NAME="小金币"
REWARD_GOLD_COIN_DESCRIPTION="基础奖品"
REWARD_GOLD_COIN_POINTS_VALUE=10

REWARD_DIAMOND_ID="diamond"
REWARD_DIAMOND_NAME="钻石"
REWARD_DIAMOND_DESCRIPTION="珍贵奖品"
REWARD_DIAMOND_POINTS_VALUE=100

# === 兑换配方配置 ===
RECIPE_GOLD_TO_DIAMOND_ID="gold_to_diamond"
RECIPE_GOLD_TO_DIAMOND_NAME="小金币合成钻石"
RECIPE_GOLD_TO_DIAMOND_MATERIALS='[{"reward_id": "gold_coin", "quantity": 10}]'
RECIPE_GOLD_TO_DIAMOND_RESULT="diamond"

# === 奖励系统配置 ===
NORMAL_TASK_POINTS=2
TOP3_COST_POINTS=300
TOP3_LOTTERY_POINTS_PROBABILITY=0.5
TOP3_LOTTERY_REWARD_PROBABILITY=0.5
TOP3_LOTTERY_POINTS_AMOUNT=100

# === 抽奖奖品池配置 ===
LOTTERY_REWARD_POOL='["gold_coin", "diamond"]'
```

### API响应格式标准
```python
def create_response(code: int, message: str, data: Any = None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data
    }
```

### Top3任务判断逻辑（支持position字段）
```python
def is_top3_task(user_id: str, task_id: str) -> bool:
    """基于v3文档的Top3判断逻辑，支持position字段"""
    today = date.today()
    top3 = get_top3_record(user_id, today)
    if not top3:
        return False

    # task_ids格式：[{'task_id': 'uuid', 'position': 1}, ...]
    task_ids = [item["task_id"] for item in top3.task_ids]
    return task_id in task_ids

def set_top3_with_positions(user_id: str, tasks_with_positions: List[Dict]) -> str:
    """设置Top3任务，包含位置信息"""
    # 验证position字段（1-3）
    # 按position排序存储
    # 返回事务ID
```

### 错误处理策略
```python
# 使用HTTP标准错误码，无统一异常处理中间件
HTTP_400_BAD_REQUEST = 400  # 请求参数错误
HTTP_401_UNAUTHORIZED = 401  # 未授权
HTTP_402_PAYMENT_REQUIRED = 402  # 积分不足
HTTP_403_FORBIDDEN = 403  # 禁止操作（重复设置Top3）
HTTP_404_NOT_FOUND = 404  # 资源不存在
HTTP_500_INTERNAL_SERVER_ERROR = 500  # 服务器内部错误
```

### 测试工程设计
```python
# test/目录结构
test/
├── data/           # 测试数据
│   ├── users.json  # 测试用户
│   ├── tasks.json  # 测试任务
│   └── rewards.json # 测试奖品
├── scripts/        # 测试脚本
│   ├── setup.py    # 环境设置
│   ├── cleanup.py  # 数据清理
│   └── run_tests.py # 运行测试
└── api/           # API测试
    ├── test_tasks.py
    ├── test_rewards.py
    └── test_top3.py
```

### 详细启动日志策略
```python
import logging

# 启动日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def initialize_system():
    logger.info("=== TaTakeKe Backend System Starting ===")

    # 1. 数据库初始化
    logger.info("Step 1: Initializing database...")
    # 详细的数据库初始化日志

    # 2. 配置加载
    logger.info("Step 2: Loading environment configuration...")
    # 详细的配置加载日志

    # 3. 奖品数据初始化
    logger.info("Step 3: Initializing reward data...")
    # 详细的奖品初始化日志

    # 4. 测试用户创建
    logger.info("Step 4: Creating test users...")
    # 详细的测试用户创建日志

    logger.info("=== System Initialization Complete ===")
```

### 事务一致性边界
```python
def complete_task_with_rewards(user_id, task_id):
    """任务完成→奖励发放→完成度更新的原子操作"""
    with db.transaction():
        # 1. 更新任务状态和领奖日期
        # 2. 发放奖励（积分或抽奖）
        # 3. 更新父任务完成度
        # 任一步失败，全部回滚
```

## Migration Plan
1. 扩展.env配置，保留原有LLM配置
2. 修改RewardTransaction模型字段和TaskTop3模型（支持position）
3. 创建统一响应格式工具函数
4. 重构任务完成API，集成Top3判断和奖励发放
5. 实现Top3相关API，包含积分消耗机制（无日期限制）
6. 实现奖品和积分查询API
7. 添加详细的启动日志记录和错误处理
8. 系统启动时从.env配置初始化基础数据并创建测试用户
9. 清理现有数据库，重新生成所有表结构
10. 创建test目录下的专门测试工程和测试数据

## Open Questions
- 无，所有技术细节已明确，可开始实施