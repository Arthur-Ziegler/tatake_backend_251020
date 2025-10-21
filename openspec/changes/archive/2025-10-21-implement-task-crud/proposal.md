# 实现任务管理核心功能（Task CRUD）

## Why

TaKeKe 项目需要任务管理功能来支持用户创建、查看、修改和删除任务。这是整个应用的核心功能之一，也是后续番茄钟、统计分析等功能的基础。

当前系统只有认证领域（auth），缺少任务管理能力，无法满足产品需求。需要实现：
1. 基础的任务 CRUD（创建、读取、更新、删除）操作
2. 支持父子任务关系的任务树结构
3. 任务状态管理和标签分类
4. 任务列表查询和基础筛选功能

本次变更聚焦于第一阶段核心功能实现，遵循 KISS 和 YAGNI 原则，为后续扩展（如任务完成抽奖、Top3管理、高级筛选等）打下基础。

## What Changes

### 核心变更

1. **新增 Task 领域（DDD架构）**
   - 创建 `src/domains/task/` 目录，包含完整的领域模型
   - 遵循现有的 DDD 分层架构（models, schemas, repository, service, router）
   - 与 auth 领域保持一致的代码风格和目录结构

2. **数据库设计**
   - 创建 `tasks` 表，包含 15 个字段
   - 核心字段：id, user_id, title, description, status, priority, parent_id, tags
   - 时间字段：due_date, planned_start_time, planned_end_time, created_at, updated_at
   - 软删除字段：is_deleted
   - 建立 4 个单列索引：user_id, status, is_deleted, parent_id
   - 所有时间字段使用 UTC 时区

3. **5 个核心 API 端点**
   - `POST /tasks` - 创建任务（只需 title 必填）
   - `GET /tasks/{id}` - 获取任务详情（包含 is_deleted 字段）
   - `PUT /tasks/{id}` - 更新任务（支持部分更新）
   - `DELETE /tasks/{id}` - 软删除任务（级联删除子任务）
   - `GET /tasks` - 获取任务列表（支持分页、状态筛选）

4. **业务逻辑**
   - 创建任务时验证 parent_id 存在性
   - 更新任务时支持修改 parent_id，需防止循环引用
   - 删除任务时级联软删除所有子任务
   - tags 字段使用 JSON 存储，更新时完全替换
   - 时间字段验证：planned_end_time 必须晚于 planned_start_time

5. **响应格式统一**
   - 复用 auth 领域的统一响应格式：`{ "code": 200, "data": {...}, "message": "success" }`
   - 列表 API 的分页信息放在 data 内部
   - 已删除任务查询时返回 404

### 不在本次变更范围内（留待后续实现）

- 任务完成功能（POST /tasks/{id}/complete）及抽奖机制
- Top3 任务管理
- 高级筛选功能（GET /tasks/filter）
- 全文搜索功能（GET /tasks/search）
- 任务树查询（GET /tasks/tree/{task_id}）
- 番茄钟相关字段（estimated_pomodoros, actual_pomodoros）
- 任务完成时间（completed_at）

## Impact

### 受影响的规范
- **新增** `task-crud` - 任务 CRUD 操作规范

### 受影响的代码
- **新增** `src/domains/task/` - 完整的 task 领域实现
  - `models.py` - Task 数据模型
  - `schemas.py` - 请求/响应 Schema
  - `repository.py` - 数据访问层
  - `service.py` - 业务逻辑层
  - `router.py` - API 路由层
  - `database.py` - 数据库配置
  - `tests/` - 单元测试和集成测试

- **修改** `src/api/main.py` - 注册 task router

### 数据库迁移
- 创建 Alembic 迁移脚本，新增 `tasks` 表
- 新表结构不影响现有 auth 表

### 外部依赖
- 无新增外部依赖
- 使用现有技术栈：SQLModel, FastAPI, PostgreSQL

### 风险
- **中等风险**：循环引用检测逻辑需要仔细测试
- **低风险**：级联软删除逻辑需要确保不会误删数据

### 缓解措施
- 编写完整的单元测试和集成测试（覆盖率 > 95%）
- 级联删除前先验证子任务列表
- 提供详细的 API 文档和示例
