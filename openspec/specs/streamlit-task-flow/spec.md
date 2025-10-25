# streamlit-task-flow Specification

## Purpose
TBD - created by archiving change sub2.1-build-streamlit-testing-panel. Update Purpose after archive.
## Requirements
### Requirement: 任务管理页面（数据驱动）
页面 MUST 以树形结构展示任务列表，每行 MUST 提供操作按钮（完成/删除），并 MUST 支持创建任务和子任务。系统 SHALL 自动刷新任务列表，子任务 MUST 正确缩进显示。支持快速创建测试任务（预设模板）和完整表单创建（含高级选项）。

#### Scenario: 加载并显示任务树
```
GIVEN 用户打开任务管理页面
WHEN 页面加载完成
THEN 自动调用 GET /api/v1/tasks
AND 以树形结构渲染任务列表（子任务缩进显示）
AND 每行显示：缩进 + 任务标题 + 状态 + 操作按钮
```

#### Scenario: 快速创建测试任务
```
GIVEN 用户点击"快速创建测试任务"按钮
WHEN 系统使用预设模板：title="测试任务_{timestamp}", priority=1
THEN 调用 POST /api/v1/tasks 创建任务
AND 自动刷新任务列表
AND 新任务出现在列表顶部
```

#### Scenario: 创建任务（完整表单）
```
GIVEN 用户点击"创建任务"按钮
WHEN 出现表单，输入 title、description、priority
AND 可选展开"高级选项"，选择 parent_id（下拉列表显示现有任务）
AND 点击"提交"
THEN 调用 POST /api/v1/tasks
AND 自动刷新任务列表
```

#### Scenario: 在列表中完成任务
```
GIVEN 任务列表中显示一个待完成任务（ID=123）
WHEN 点击该任务行的"完成"按钮
THEN 调用 POST /api/v1/tasks/123/complete
AND 自动刷新任务列表
AND 任务状态更新为"已完成"
```

#### Scenario: 在列表中删除任务
```
GIVEN 任务列表中显示一个任务（ID=123）
WHEN 点击该任务行的"删除"按钮
THEN 调用 DELETE /api/v1/tasks/123
AND 自动刷新任务列表
AND 该任务从列表中移除
```

#### Scenario: 展开查看任务详细 JSON
```
GIVEN 任务列表已加载
WHEN 点击"展开查看完整 JSON"按钮
THEN 在表格下方显示完整的 API 响应 JSON
```

---

### Requirement: Top3 管理页面
页面 MUST 支持设置每日 Top3 任务，并 MUST 支持查看历史记录。系统 SHALL 通过多选框选择任务，并 MUST 在设置成功后显示消耗的积分。

#### Scenario: 设置 Top3 任务
```
GIVEN 用户已创建多个任务
WHEN 在 Top3 页面选择 3 个任务（使用多选框），点击"设置 Top3"
THEN 调用 POST /api/v1/tasks/top3，传入 task_ids=[123, 456, 789]
AND 显示成功提示 "Top3 设置成功，消耗 300 积分"
```

#### Scenario: 查看指定日期 Top3
```
GIVEN 用户想查看 2025-01-01 的 Top3
WHEN 输入日期"2025-01-01"，点击"查询"
THEN 调用 GET /api/v1/tasks/top3/2025-01-01
AND 显示该日期的 Top3 任务列表
```

---

### Requirement: 番茄钟系统页面（实时状态）
页面 MUST 实时显示当前活跃专注会话，并 MUST 提供开始/暂停/恢复/完成操作按钮。系统 SHALL 通过下拉列表选择任务，并 MUST 在会话状态变化时正确更新按钮状态。

#### Scenario: 开始专注会话
```
GIVEN 用户已创建任务（task_id=123）
WHEN 在番茄钟页面选择任务 123，点击"开始专注"
THEN 调用 POST /api/v1/focus/sessions，传入 task_id=123
AND 页面显示 "当前专注：任务 123 | 已用时：0 分钟"
AND 显示"暂停"和"完成"按钮
```

#### Scenario: 暂停专注会话
```
GIVEN 当前有活跃专注会话（session_id=abc）
WHEN 点击"暂停"按钮
THEN 调用 POST /api/v1/focus/sessions/abc/pause
AND 状态更新为 "已暂停"
AND 显示"恢复"按钮
```

#### Scenario: 恢复专注会话
```
GIVEN 当前专注会话已暂停
WHEN 点击"恢复"按钮
THEN 调用 POST /api/v1/focus/sessions/abc/resume
AND 状态更新为 "专注中"
AND 显示"暂停"和"完成"按钮
```

#### Scenario: 完成专注会话
```
GIVEN 当前有活跃专注会话（session_id=abc）
WHEN 点击"完成"按钮
THEN 调用 POST /api/v1/focus/sessions/abc/complete
AND 显示成功提示 "专注完成，已用时：25 分钟"
AND 当前会话状态清空
```

