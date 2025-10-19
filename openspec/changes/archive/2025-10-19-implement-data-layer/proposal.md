# TaKeKe 数据层实现提案

## 提案概述

**变更ID**: `implement-data-layer`
**项目**: TaKeKe API 后端
**阶段**: 第一阶段 - 数据层实现
**预计工期**: 2-3 周

### 目标

实现 TaKeKe API 后端的数据层，采用 SQLModel + SQLite + Repository 模式，建立坚实的数据库基础架构，为后续的服务层和 API 层提供支撑。

### 技术栈

- **Python 3.11+** + **uv** 环境管理
- **SQLModel** (基于 SQLAlchemy 的现代 ORM)
- **SQLite** (第一阶段数据库)
- **FastAPI** (为后续集成准备)
- **Pytest** + **pytest-asyncio** (TDD 测试框架)
- **测试覆盖率**: 目标 95%+

---

## 架构设计

### 三层架构预览

```
┌─────────────────┐
│   API 路由层     │ ← FastAPI 路由 (后续实现)
├─────────────────┤
│   业务服务层     │ ← 业务逻辑处理 (后续实现)
├─────────────────┤
│   数据访问层     │ ← Repository 模式 (本次实现)
├─────────────────┤
│   数据存储层     │ ← SQLModel + SQLite (本次实现)
└─────────────────┘
```

### 本次实现范围

**✅ 包含**:
- SQLModel 数据模型定义
- Repository 数据访问层
- SQLite 数据库配置
- 种子数据管理
- 完整的 TDD 测试套件
- 数据层设计文档

**❌ 不包含**:
- API 路由实现
- 业务服务层实现
- 数据库迁移脚本
- 生产环境部署配置

---

## 目录结构设计

```
tatake_backend/
├── src/
│   ├── models/                    # SQLModel 模型
│   │   ├── __init__.py           # 模型导出
│   │   ├── base.py               # 基础模型类
│   │   ├── user.py               # 用户相关模型
│   │   ├── task.py               # 任务相关模型
│   │   ├── focus.py              # 专注相关模型
│   │   ├── reward.py             # 奖励相关模型
│   │   └── chat.py               # 聊天相关模型
│   ├── repositories/             # Repository 数据访问层
│   │   ├── __init__.py           # Repository 导出
│   │   ├── base.py               # 基础 Repository 类
│   │   ├── user.py               # 用户 Repository
│   │   ├── task.py               # 任务 Repository
│   │   ├── focus.py              # 专注 Repository
│   │   ├── reward.py             # 奖励 Repository
│   │   └── chat.py               # 聊天 Repository
│   ├── database/                 # 数据库配置
│   │   ├── __init__.py           # 数据库模块导出
│   │   ├── connection.py         # 数据库连接配置
│   │   ├── session.py            # 会话管理
│   │   └── seeds.py              # 种子数据
│   └── core/                     # 核心工具
│       ├── __init__.py
│       ├── exceptions.py         # 自定义异常
│       └── utils.py              # 工具函数
├── tests/                        # TDD 测试目录
│   ├── __init__.py
│   ├── conftest.py               # pytest 配置
│   ├── models/                   # 模型测试
│   │   ├── test_user.py
│   │   ├── test_task.py
│   │   ├── test_focus.py
│   │   ├── test_reward.py
│   │   └── test_chat.py
│   ├── repositories/             # Repository 测试
│   │   ├── test_user_repository.py
│   │   ├── test_task_repository.py
│   │   ├── test_focus_repository.py
│   │   ├── test_reward_repository.py
│   │   └── test_chat_repository.py
│   └── database/                 # 数据库测试
│       ├── test_connection.py
│       └── test_seeds.py
├── docs/                         # 文档
│   ├── data-layer-design.md      # 数据层设计文档
│   ├── naming-conventions.md     # 命名规范文档
│   └── tdd-guidelines.md         # TDD 开发指南
├── pyproject.toml                # 项目配置和依赖
├── .gitignore
├── README.md
└── .env.example                  # 环境变量示例
```

---

## 核心模型设计

### 模型映射关系

基于 API 文档，设计以下核心模型：

1. **用户系统模型** (4个)
   - `User` - 用户基本信息
   - `UserSettings` - 用户设置
   - `UserFeedback` - 用户反馈
   - `SmsCode` - 短信验证码

2. **任务系统模型** (3个)
   - `Task` - 任务信息(支持树结构)
   - `TaskTop3` - 每日Top3任务
   - `TaskTag` - 任务标签

3. **专注系统模型** (2个)
   - `FocusSession` - 专注会话
   - `FocusStatistics` - 专注统计

4. **奖励系统模型** (5个)
   - `Reward` - 奖励配置
   - `UserFragment` - 用户碎片收集
   - `LotteryRecord` - 抽奖记录
   - `PointsTransaction` - 积分流水
   - `PointsPackage` - 积分套餐

5. **聊天系统模型** (2个)
   - `ChatSession` - 聊天会话
   - `ChatMessage` - 聊天消息

### 命名规范

**表名**: `snake_case` 复数形式
**模型类名**: `PascalCase` 单数形式
**字段名**: `snake_case`
**外键**: `{related_table}_id`
**时间字段**: `*_at` (created_at, updated_at)

---

## Repository 设计

### 基础 Repository 架构

```python
# 基础 Repository 类
class BaseRepository[T]:
    def __init__(self, session: Session, model: Type[T])
    def create(self, obj_data: dict) -> T
    def get_by_id(self, obj_id: str) -> Optional[T]
    def get_all(self, **filters) -> List[T]
    def update(self, obj_id: str, update_data: dict) -> Optional[T]
    def delete(self, obj_id: str) -> bool
    def exists(self, **filters) -> bool
    def count(self, **filters) -> int

# 具体 Repository 示例
class TaskRepository(BaseRepository[Task]):
    def find_by_user(self, user_id: str) -> List[Task]
    def find_pending_tasks(self, user_id: str) -> List[Task]
    def find_subtasks(self, parent_id: str) -> List[Task]
    def calculate_completion_percentage(self, task_id: str) -> int
```

### Repository 原则

1. **单一责任**: 每个 Repository 负责一个模型的 CRUD 操作
2. **查询封装**: 复杂查询封装在 Repository 方法中
3. **事务管理**: Repository 不处理事务，由上层服务处理
4. **异常处理**: 统一的异常处理机制
5. **类型安全**: 使用泛型确保类型安全

---

## TDD 测试策略

### 测试金字塔

```
        /\
       /  \  <- 集成测试 (15%)
      /____\
     /      \ <- Repository 测试 (25%)
    /________\
   /          \ <- 单元测试 (60%)
  /____________\
```

### 测试分类

1. **单元测试** (60%)
   - 模型字段验证测试
   - 模型关系测试
   - 工具函数测试
   - 覆盖率目标: 98%+

2. **Repository 测试** (25%)
   - CRUD 操作测试
   - 查询方法测试
   - 异常情况测试
   - 覆盖率目标: 95%+

3. **集成测试** (15%)
   - 模型关系测试
   - 数据库约束测试
   - 种子数据测试
   - 覆盖率目标: 90%+

### TDD 开发流程

1. **红阶段**: 写失败的测试
2. **绿阶段**: 写最少的代码让测试通过
3. **重构阶段**: 重构代码保持测试通过

### 测试工具配置

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=95"
]
```

---

## 开发计划

### 第一周：基础架构

**Day 1-2: 项目初始化**
- [ ] 配置 uv 环境和依赖
- [ ] 设置项目目录结构
- [ ] 配置 pytest 和测试环境
- [ ] 编写基础配置文件

**Day 3-4: 基础模型**
- [ ] 实现 BaseSQLModel
- [ ] 实现 User 模型
- [ ] 编写 User 模型 TDD 测试
- [ ] 测试覆盖率达到 95%+

**Day 5-7: 核心模型**
- [ ] 实现 Task 模型 (支持树结构)
- [ ] 实现 FocusSession 模型
- [ ] 完整的 TDD 测试套件
- [ ] 模型关系验证测试

### 第二周：Repository 层

**Day 8-9: 基础 Repository**
- [ ] 实现 BaseRepository
- [ ] 实现 UserRepository
- [ ] Repository TDD 测试
- [ ] 异常处理测试

**Day 10-11: 核心 Repository**
- [ ] 实现 TaskRepository
- [ ] 实现 FocusSessionRepository
- [ ] 复杂查询方法测试
- [ ] 性能测试

**Day 12-14: 奖励系统**
- [ ] 实现奖励相关模型
- [ ] 实现 RewardRepository
- [ ] 种子数据系统
- [ ] 集成测试

### 第三周：完善和文档

**Day 15-17: 聊天和反馈系统**
- [ ] 实现聊天相关模型
- [ ] 实现反馈系统模型
- [ ] Repository 层完善
- [ ] 全面测试

**Day 18-19: 文档和优化**
- [ ] 编写数据层设计文档
- [ ] 编写命名规范文档
- [ ] 编写 TDD 开发指南
- [ ] 代码重构和优化

**Day 20-21: 验证和交付**
- [ ] 完整测试套件运行
- [ ] 测试覆盖率验证 (95%+)
- [ ] 性能基准测试
- [ ] 交付验收

---

## 质量保证

### 代码质量标准

1. **测试覆盖率**: 最低 95%，目标 98%
2. **类型注解**: 100% 类型注解覆盖
3. **文档字符串**: 所有公共 API 有文档
4. **代码风格**: 使用 black + isort + mypy
5. **性能测试**: 关键查询性能基准

### CI/CD 检查

```yaml
# .github/workflows/test.yml
name: Data Layer Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest --cov=src --cov-fail-under=95
      - name: Type checking
        run: uv run mypy src
      - name: Code formatting
        run: uv run black --check src tests
```

---

## 风险评估

### 技术风险

1. **SQLModel 成熟度**: 相比 SQLAlchemy 生态较新
   - 缓解: 选择稳定版本，充分测试
2. **SQLite 性能**: 大量数据时性能限制
   - 缓解: 第一阶段验证，后续可平滑迁移到 PostgreSQL
3. **复杂查询**: 树形结构查询复杂度
   - 缓解: 优化查询设计，充分测试

### 项目风险

1. **TDD 学习成本**: 团队 TDD 经验不足
   - 缓解: 提供 TDD 培训和指南
2. **测试时间**: TDD 开发时间较长
   - 缓解: 长期收益，减少后期 bug 修复成本

---

## 成功标准

### 功能标准

- [ ] 所有核心模型实现完成
- [ ] Repository 层功能完整
- [ ] 种子数据系统正常工作
- [ ] 与 API 文档完全匹配

### 质量标准

- [ ] 测试覆盖率达到 95%+
- [ ] 所有类型检查通过
- [ ] 性能基准达标
- [ ] 文档完整准确

### 可维护性标准

- [ ] 代码结构清晰
- [ ] 命名规范一致
- [ ] 文档详实
- [ ] 易于扩展

---

## 下一步计划

数据层完成后，将为第二阶段（服务层）奠定坚实基础：

1. **服务层开发**: 基于 Repository 实现业务逻辑
2. **API 层开发**: 基于 FastAPI 实现 RESTful API
3. **测试扩展**: 增加集成测试和端到端测试
4. **性能优化**: 基于实际使用情况优化查询
5. **部署准备**: 容器化和生产环境配置

---

## 总结

本提案专注于建立一个高质量、可测试、可维护的数据层基础架构。通过严格的 TDD 方法论，确保代码质量和长期可维护性，为 TaKeKe 项目的成功奠定坚实基础。

**核心理念**: 代码质量是项目成功的基础，TDD 是保证质量的最佳实践。