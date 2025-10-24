## Why

当前Task模型缺少树结构支持，无法实现API设计文档要求的"无限层级任务结构"功能。现有模型只有基础的parent_id关系，缺少任务层级深度、路径管理和完成度计算能力，这阻塞了任务树系统的核心功能实现。

## What Changes

- **增强Task数据模型**：添加level、path、completion_percentage、estimated_pomodoros、actual_pomodoros字段
- **实现树结构计算逻辑**：包括自动计算任务层级深度和路径
- **实现完成度计算算法**：基于叶子节点数量递归计算任务完成百分比
- **更新数据库架构**：重建Task表结构，添加必要的索引支持
- **增强TaskService功能**：支持树结构相关的业务逻辑

## Impact

- **Affected specs**: `specs/task-crud/spec.md` - 需要修改现有CRUD功能以支持树结构
- **Affected code**:
  - `src/domains/task/models.py` - 数据模型扩展
  - `src/domains/task/service.py` - 业务逻辑增强
  - `src/domains/task/repository.py` - 数据访问层增强
  - `src/domains/task/database.py` - 数据库结构调整
  - `tests/domains/task/` - 测试用例扩展

**Dependencies**: 无外部依赖，使用现有技术栈（SQLModel、SQLAlchemy）