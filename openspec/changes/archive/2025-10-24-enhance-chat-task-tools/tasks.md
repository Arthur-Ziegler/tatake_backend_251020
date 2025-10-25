# 实施任务清单

## Phase 1: 工具基础设施

### 1.1 创建工具辅助模块
- [ ] 创建 `src/domains/chat/tools/utils.py`
- [ ] 实现 `get_task_service_context()` - Session管理上下文管理器
  - 使用 `get_engine()` 获取数据库引擎
  - 创建Session并注入TaskService和PointsService
  - 实现异常处理和Session清理
- [ ] 实现 `safe_uuid_convert()` - UUID安全转换
  - 处理None值
  - 捕获ValueError并返回友好错误
- [ ] 实现 `parse_datetime()` - ISO日期解析
  - 支持Z时区标记
  - 支持标准ISO格式
  - 提供详细错误信息
- [ ] 实现 `_success_response()` 和 `_error_response()` - 统一JSON响应格式

**验证**：
```bash
uv run python -c "from src.domains.chat.tools.utils import *; print('✓ Utils module OK')"
```

---

## Phase 2: 任务管理工具实现（可并行）

### 2.1 实现 create_task 工具
- [ ] 定义工具签名（支持全字段）
  - title, description, parent_id, priority, tags
  - due_date, planned_start_time, planned_end_time (ISO字符串)
  - state (InjectedState自动注入)
- [ ] 实现参数验证和转换
  - UUID转换（user_id, parent_id）
  - datetime解析（3个时间字段）
  - 捕获并返回友好错误
- [ ] 调用TaskService.create_task()
- [ ] 返回标准JSON格式

**验证**：工具单元测试通过

---

### 2.2 实现 update_task 工具
- [ ] 定义工具签名
  - task_id (必填), title, description, status, priority
  - tags, due_date (ISO字符串)
- [ ] UUID转换和权限验证
- [ ] 构造UpdateTaskRequest对象
- [ ] 调用TaskService.update_task_with_tree_structure()
- [ ] 返回更新后的任务信息

**验证**：单元测试覆盖成功和权限失败场景

---

### 2.3 实现 delete_task 工具
- [ ] 定义工具签名（task_id, state）
- [ ] UUID转换和权限验证
- [ ] 调用TaskService.delete_task()
- [ ] 返回删除确认信息

**验证**：测试软删除和权限验证

---

### 2.4 实现 query_tasks 工具
- [ ] 定义工具签名
  - status, parent_id, limit, offset, state
- [ ] UUID转换（parent_id如果提供）
- [ ] 构造TaskListQuery对象
- [ ] 调用TaskService.list_tasks()
- [ ] 返回任务列表和分页信息

**验证**：测试不同过滤条件的查询

---

### 2.5 实现 get_task_detail 工具
- [ ] 定义工具签名（task_id, state）
- [ ] UUID转换和权限验证
- [ ] 调用TaskService.get_task()
- [ ] 返回完整任务信息（含子任务）

**验证**：测试详情获取和权限验证

---

### 2.6 实现 search_tasks 工具（方案D）
- [ ] 定义工具签名（query, limit, state）
- [ ] 调用TaskService.list_tasks()获取所有任务（最多limit个）
- [ ] 简化任务信息（id, title, status, priority, 时间字段）
- [ ] 返回任务列表供LLM分析
- [ ] 附加提示信息

**验证**：
- 测试返回字段正确性
- 测试token消耗（100任务约8000 tokens）

---

### 2.7 实现 batch_create_subtasks 工具
- [ ] 定义工具签名（parent_id, subtasks列表, state）
- [ ] UUID转换（parent_id, user_id）
- [ ] 预验证父任务存在且有权限
- [ ] 循环创建子任务
  - 构造CreateTaskRequest（title, description, parent_id）
  - 调用TaskService.create_task()
  - 收集成功和失败结果
- [ ] 返回部分成功结果
  - {"success": bool, "created": [...], "failed": [...]}

**验证**：
- 测试全部成功场景
- 测试部分失败场景（第3个失败）
- 测试父任务不存在场景

---

## Phase 3: LangGraph集成

### 3.1 更新工具注册
- [ ] 修改 `src/domains/chat/graph.py`
- [ ] 导入所有新工具
  ```python
  from .tools.task_tools import (
      create_task, update_task, delete_task,
      query_tasks, get_task_detail,
      search_tasks, batch_create_subtasks
  )
  ```
- [ ] 更新ToolNode注册
  ```python
  tool_node = ToolNode([
      sesame_opener,  # 保留现有工具
      create_task, update_task, delete_task,
      query_tasks, get_task_detail,
      search_tasks, batch_create_subtasks
  ])
  ```
- [ ] 更新模型工具绑定
  ```python
  model = model.bind_tools([所有8个工具])
  ```

**验证**：
```bash
uv run python -c "from src.domains.chat.graph import create_chat_graph; print('✓ Graph compilation OK')"
```

---

### 3.2 验证State传递机制
- [ ] 确认ChatState.user_id字段存在
- [ ] 测试InjectedState在工具中正确注入
- [ ] 验证user_id从API→Service→Graph→工具的完整链路
- [ ] 添加日志记录user_id传递（debug模式）

**验证**：启动服务，发送测试消息，检查日志

---

## Phase 4: 测试

### 4.1 工具单元测试（可并行）
- [ ] 创建 `tests/domains/chat/test_task_tools_unit.py`
- [ ] Mock `get_task_service_context()`
- [ ] Mock `InjectedState`（提供fake user_id）
- [ ] 测试每个工具的成功场景
  - create_task：验证参数传递和返回格式
  - update_task：验证字段更新逻辑
  - delete_task：验证软删除调用
  - query_tasks：验证过滤参数传递
  - get_task_detail：验证详情获取
  - search_tasks：验证简化字段逻辑
  - batch_create_subtasks：验证批量逻辑
- [ ] 测试错误处理场景
  - UUID格式错误
  - datetime解析错误
  - TaskService异常（任务不存在、权限不足）
- [ ] 测试返回JSON格式正确性

**验证**：`uv run pytest tests/domains/chat/test_task_tools_unit.py -v`
**目标覆盖率**：> 90%

---

### 4.2 工具集成测试
- [ ] 创建 `tests/domains/chat/test_task_tools_integration.py`
- [ ] 使用真实数据库（测试fixture）
- [ ] 测试完整调用链
  - 工具 → TaskService → TaskRepository → 数据库
- [ ] 测试多用户隔离
  - UserA创建任务
  - UserB尝试访问/修改UserA的任务（应失败）
- [ ] 测试任务树创建
  - 创建父任务
  - 创建子任务（parent_id指向父任务）
  - 验证关系正确
- [ ] 测试批量创建部分成功
  - 构造部分非法的subtasks
  - 验证成功和失败列表正确

**验证**：`uv run pytest tests/domains/chat/test_task_tools_integration.py -v`

---

### 4.3 对话场景测试（E2E）
- [ ] 创建 `tests/e2e/test_chat_task_management.py`
- [ ] 场景1：创建任务对话
  ```
  用户："帮我创建一个任务：完成项目方案"
  AI：[调用create_task] → "已创建任务《完成项目方案》，ID: xxx"
  ```
- [ ] 场景2：更新任务对话
  ```
  用户："把任务xxx的优先级改为高"
  AI：[调用update_task] → "已将任务《完成项目方案》优先级改为高"
  ```
- [ ] 场景3：任务拆分对话（多轮）
  ```
  用户："把任务xxx拆分成几个子任务"
  AI："建议拆分为：1.需求调研 2.方案设计 3.文档撰写，确认吗？"
  用户："好的"
  AI：[调用batch_create_subtasks] → "已创建3个子任务"
  ```
- [ ] 场景4：任务搜索对话
  ```
  用户："我有哪些关于项目的任务？"
  AI：[调用search_tasks] → 分析并返回相关任务列表
  ```
- [ ] 场景5：批量创建部分失败
  ```
  用户："创建5个子任务：【包含非法数据】"
  AI：[调用batch_create_subtasks] → "成功创建3个，2个失败：【错误详情】"
  ```

**验证**：`uv run pytest tests/e2e/test_chat_task_management.py -v`

---

### 4.4 工具辅助函数测试
- [ ] 创建 `tests/domains/chat/test_task_tools_utils.py`
- [ ] 测试 `safe_uuid_convert()`
  - 有效UUID字符串
  - None值
  - 无效格式（应抛ValueError）
- [ ] 测试 `parse_datetime()`
  - 标准ISO格式
  - Z时区格式
  - 带时区偏移格式
  - 无效格式（应抛ValueError）
  - None值
- [ ] 测试 `get_task_service_context()`
  - Session正确创建和关闭
  - 异常时Session回滚

**验证**：`uv run pytest tests/domains/chat/test_task_tools_utils.py -v`

---

## Phase 5: 文档和部署

### 5.1 更新文档
- [ ] 更新 `src/domains/chat/tools/task_tools.py` 文档字符串
  - 每个工具详细说明
  - 参数说明和格式要求
  - 返回格式说明
  - 使用示例
- [ ] 编写 `docs/chat-task-tools-guide.md`（如需要）
  - 工具使用指南
  - 任务拆分最佳实践
  - 常见问题解答

**验证**：文档清晰完整，包含示例

---

### 5.2 性能和安全审查
- [ ] Token成本评估
  - 统计单次工具调用的token消耗
  - 评估搜索工具在不同任务数量下的成本
  - 文档化成本数据
- [ ] 安全审查
  - 确认所有工具都验证user_id
  - 确认UUID转换正确处理异常
  - 确认无SQL注入风险（使用ORM）
  - 确认敏感信息不泄露
- [ ] 性能测试
  - 测试批量创建100个子任务的耗时
  - 测试搜索100个任务的耗时
  - 确保响应时间 < 2秒

**验证**：无安全漏洞，性能满足MVP要求

---

### 5.3 部署准备
- [ ] 运行完整测试套件
  ```bash
  uv run pytest tests/ -v --cov=src/domains/chat/tools
  ```
- [ ] 验证测试覆盖率 > 85%
- [ ] 检查所有工具在实际对话中可用
- [ ] 准备监控指标
  - 工具调用频率（按工具统计）
  - 工具调用成功率
  - 批量创建成功/失败比例
  - 平均响应时间
- [ ] 编写回滚方案
  - 如果工具有严重问题，如何快速禁用
  - 数据库迁移回滚（如果需要）

**验证**：所有测试通过，准备好生产部署

---

## 依赖关系图

```
Phase 1 (必须先完成)
   ↓
Phase 2 (7个工具可并行开发)
   ├── 2.1 create_task
   ├── 2.2 update_task
   ├── 2.3 delete_task
   ├── 2.4 query_tasks
   ├── 2.5 get_task_detail
   ├── 2.6 search_tasks
   └── 2.7 batch_create_subtasks
   ↓
Phase 3 (集成)
   ↓
Phase 4 (测试可部分并行)
   ├── 4.1 单元测试 (并行)
   ├── 4.2 集成测试 (并行)
   ├── 4.3 E2E测试 (依赖4.1和4.2)
   └── 4.4 辅助函数测试 (并行)
   ↓
Phase 5 (文档和部署)
```

---

## 预估工作量

| Phase | 任务数 | 预估时间 | 可并行？ |
|-------|--------|---------|---------|
| Phase 1 | 5个任务 | 1.5小时 | 否 |
| Phase 2 | 7个工具 | 3-4小时 | 是（7个并行） |
| Phase 3 | 2个任务 | 1小时 | 否 |
| Phase 4 | 4组测试 | 4-5小时 | 部分并行 |
| Phase 5 | 3个任务 | 1-2小时 | 否 |

**总计**：10-13小时（1-2个工作日）

---

## 里程碑

- ✅ **Milestone 1**：工具基础设施完成（Phase 1）
- ✅ **Milestone 2**：所有7个工具实现完成（Phase 2）
- ✅ **Milestone 3**：LangGraph集成完成，工具可调用（Phase 3）
- ✅ **Milestone 4**：测试覆盖率 > 85%（Phase 4）
- ✅ **Milestone 5**：生产就绪，可部署（Phase 5）

---

## 验证检查清单

部署前必须完成：

- [ ] 所有单元测试通过（> 90%覆盖率）
- [ ] 所有集成测试通过
- [ ] 所有E2E场景测试通过
- [ ] 工具在真实对话中可用
- [ ] 性能满足要求（响应时间 < 2s）
- [ ] 无安全漏洞
- [ ] 文档完整
- [ ] 回滚方案准备就绪
