# Day1数据层搭建任务清单

## 任务概述
完成TaKeKe后端项目第一阶段的数据层搭建，建立完整的表结构、模型定义和初始化数据，为后续业务逻辑实现奠定基础。

## 具体任务

### Day1.1 数据模型层搭建 (0.5天)

**任务1.1: Task模型重构**
- [x] 修改 `src/domains/task/models.py`
- [x] 删除字段: `estimated_pomodoros`, `actual_pomodoros`, `level`, `path`
- [x] 新增字段: `last_claimed_date: Optional[date]`
- [x] 删除所有自定义索引定义
- [x] 更新模型注释和字段描述

**任务1.2: Reward系统模型重构**
- [x] 重写 `src/domains/reward/models.py`
- [x] 保留模型: `Reward` (简化字段)
- [x] 重构模型: `RewardRecipe` (添加name字段)
- [x] 新增模型: `RewardTransaction`
- [x] 新增模型: `PointsTransaction`
- [x] 删除模型: `UserReward`

**任务1.3: Top3系统模型创建**
- [x] 创建 `src/domains/top3/models.py`
- [x] 定义模型: `TaskTop3`
- [x] 设置JSON字段和UNIQUE约束

**任务1.4: 验证SQLite JSON兼容性**
- [ ] 检查当前SQLite版本支持JSON1扩展
- [ ] 创建测试文件验证JSON操作
- [ ] 更新数据库连接配置

### Day1.2 配置系统搭建 (0.3天)

**任务2.1: 创建配置模块**
- [ ] 创建 `src/config/game_config.py`
- [ ] 定义枚举类型: `TransactionSource`
- [ ] 集中管理奖励配置参数
- [ ] 支持环境变量加载

**任务2.2: 初始化数据脚本**
- [ ] 创建 `src/config/initial_data.py`
- [ ] 定义奖励种子数据: 3个基础奖品
- [ ] 定义兑换配方: 2个基础配方
- [ ] 创建数据初始化函数

**任务2.3: 数据库连接增强**
- [ ] 增强 `src/database/connection.py`
- [ ] 添加JSON字段验证函数
- [ ] 支持配置热加载机制
- [ ] 优化错误处理

### Day1.3 表结构创建与验证 (0.7天)

**任务3.1: 表创建脚本**
- [ ] 创建 `scripts/create_tables.py`
- [ ] 使用SQLAlchemy的`create_all()`
- [ ] 验证所有表结构正确创建
- [ ] 检查约束和索引

**任务3.2: 数据库验证脚本**
- [ ] 创建 `scripts/validate_db.py`
- [ ] 验证JSON字段读写功能
- [ ] 测试SUM聚合查询正确性
- [ ] 验证表关联完整性

**任务3.3: 数据初始化执行**
- [ ] 创建 `scripts/init_data.py`
- [ ] 执行奖励和配方数据初始化
- [ ] 验证数据正确加载
- [ ] 生成初始化日志

### Day1.4 测试用例编写 (0.5天)

**任务4.1: 模型测试**
- [x] 创建 `tests/domains/task/test_models.py`
- [x] 测试Task模型字段变化
- [x] 测试last_claimed_date字段
- [x] 验证JSON字段类型

**任务4.2: 配置测试**
- [x] 创建 `tests/config/test_game_config.py`
- [x] 测试配置加载和覆盖
- [x] 测试枚举类型定义
- [x] 验证初始化数据

**任务4.3: 数据库集成测试**
- [x] 创建 `tests/database/test_integration.py`
- [x] 测试表创建和初始化
- [x] 测试JSON字段操作
- [x] 验证约束和索引
- [x] 测试事务回滚

## 验收标准

### 功能验收
- [x] 所有模型字段类型与v3方案完全一致
- [x] 数据库表正确创建，支持JSON操作
- [x] 配置系统能正确加载和覆盖
- [x] 初始化数据正确写入数据库

### 质量验收
- [ ] 代码通过pylint检查，符合项目规范
- [ ] 类型注解完整，文档字符串规范
- [ ] 测试用例覆盖主要功能和边界情况
- [x] 无SQLAlchemy警告和数据库连接问题

### 交付物
- [ ] 重构后的所有模型文件
- [x] 完整的配置管理模块
- [x] 数据库创建和初始化脚本
- [x] 全面的测试用例
- [x] 技术决策文档和风险清单

## 风险控制

### 技术风险
- **SQLite版本**: JSON支持检查失败时降级方案
- **模型重构**: 确保不影响现有功能模块
- **性能影响**: 全表扫描性能影响监控

### 缓解措施
- **版本兼容性**: 提供SQLite版本检查和降级方案
- **渐进重构**: 分步骤重构，每步验证功能
- **测试覆盖**: 全面的单元和集成测试

## 依赖关系

### 前置条件
- SQLite 3.38.0+ (JSON支持)
- SQLAlchemy 1.4+ (JSON字段支持)
- Python 3.11+ (项目基础要求)

### 后续影响
- 为Day2业务逻辑实现提供数据基础
- 支持后续API接口的数据查询需求
- 确保配置系统支持热更新需求

---

**预计总工作量**: 1个工作日
**当前状态**: 准备开始实施