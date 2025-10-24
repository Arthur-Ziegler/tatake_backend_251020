# Tasks: Streamlit 测试面板任务流程实施

## 前置条件
- ✅ 提案 1（基础架构）必须已完成
- ✅ `api_client` 和 `state_manager` 已可用

## 阶段 1：任务管理页面（顺序执行）

### 1.1 创建页面和数据加载
- [ ] 创建 `pages/2_📋_任务管理.py`
- [ ] 实现 `load_tasks()` 函数：调用 `GET /api/v1/tasks`
- [ ] 页面加载时自动调用 `load_tasks()`
- [ ] 将任务列表存入 `session_state.tasks`

**验证**：打开页面，控制台输出任务列表

---

### 1.2 实现树形视图
- [ ] 创建 `components/task_tree.py`
- [ ] 实现 `render_task_tree(tasks)` 函数：筛选根任务
- [ ] 实现 `render_task_node(task, all_tasks, level)` 函数：
  - 计算缩进（全角空格 × level）
  - 使用 `st.columns([3, 1, 1, 1])` 布局
  - 显示任务标题、状态、操作按钮
  - 递归渲染子任务

**验证**：
1. 创建父任务和子任务（通过 SwaggerUI）
2. 打开页面，子任务正确缩进显示

---

### 1.3 实现行内操作按钮
- [ ] 添加"完成"按钮：
  - 调用 `POST /api/v1/tasks/{id}/complete`
  - 成功后调用 `load_tasks()` 刷新列表
- [ ] 添加"删除"按钮：
  - 调用 `DELETE /api/v1/tasks/{id}`
  - 成功后调用 `load_tasks()` 刷新列表

**验证**：
1. 点击"完成"按钮，任务状态更新
2. 点击"删除"按钮，任务从列表移除

---

### 1.4 实现快速创建测试任务
- [ ] 添加"快速创建测试任务"按钮
- [ ] 点击时调用 `POST /api/v1/tasks`，传入预设参数：
  - `title`: `f"测试任务_{datetime.now().strftime('%H%M%S')}"`
  - `priority`: 1
- [ ] 成功后调用 `load_tasks()` 刷新列表

**验证**：点击按钮，新任务出现在列表顶部

---

### 1.5 实现完整表单创建
- [ ] 使用 `st.expander` 创建折叠表单
- [ ] 添加表单字段：
  - `title`: `st.text_input`
  - `description`: `st.text_area`
  - `priority`: `st.number_input(1, 5, 1)`
- [ ] 添加"高级选项"折叠区域：
  - `parent_id`: `st.selectbox` 从现有任务选择
- [ ] 点击"提交"按钮，调用 `POST /api/v1/tasks`
- [ ] 成功后调用 `load_tasks()` 刷新列表

**验证**：
1. 填写表单，创建简单任务
2. 展开高级选项，选择父任务，创建子任务

---

### 1.6 添加 JSON 查看器
- [ ] 复用 `components/json_viewer.py`
- [ ] 在页面底部添加"展开查看完整 JSON"按钮
- [ ] 点击后显示完整的 API 响应 JSON

**验证**：点击按钮，显示任务列表 JSON

---

## 阶段 2：Top3 管理页面（顺序执行）

### 2.1 创建页面和设置 Top3
- [ ] 创建 `pages/7_⭐_Top3管理.py`
- [ ] 从 `session_state.tasks` 读取任务列表
- [ ] 使用 `st.multiselect` 创建任务多选框：
  - `options`: 任务 ID 列表
  - `format_func`: 显示任务标题
- [ ] 添加"设置 Top3"按钮：
  - 验证选择 1-3 个任务
  - 调用 `POST /api/v1/tasks/top3`
  - 显示成功提示 "Top3 设置成功，消耗 300 积分"

**验证**：
1. 选择 3 个任务，点击"设置 Top3"，成功提示
2. 选择 0 个或 4 个任务，显示错误提示

---

### 2.2 实现查询历史
- [ ] 添加日期选择器：`st.date_input("选择日期")`
- [ ] 添加"查询"按钮：
  - 调用 `GET /api/v1/tasks/top3/{date}`
  - 显示查询结果（使用 `st.json`）

**验证**：输入日期，查询历史 Top3

---

## 阶段 3：番茄钟系统页面（顺序执行）

### 3.1 创建页面和加载当前会话
- [ ] 创建 `pages/4_🍅_番茄钟.py`
- [ ] 实现 `load_current_session()` 函数：
  - 调用 `GET /api/v1/focus/sessions?status=active`
  - 存入 `session_state.current_focus`
- [ ] 页面加载时自动调用 `load_current_session()`

**验证**：如果有活跃会话，显示会话信息

---

### 3.2 显示当前会话状态
- [ ] 如果 `session_state.current_focus` 存在：
  - 使用 `st.info` 显示会话信息：
    - "当前专注：任务 {task_id} | 状态：{status}"
  - 根据状态显示对应按钮：
    - `status == 'focus'`: 显示"暂停"和"完成"按钮
    - `status == 'pause'`: 显示"恢复"和"完成"按钮

**验证**：手动创建专注会话（通过 SwaggerUI），打开页面显示正确状态

---

### 3.3 实现操作按钮
- [ ] 实现"暂停"按钮：
  - 调用 `POST /api/v1/focus/sessions/{id}/pause`
  - 成功后调用 `load_current_session()` 刷新状态
- [ ] 实现"恢复"按钮：
  - 调用 `POST /api/v1/focus/sessions/{id}/resume`
  - 成功后调用 `load_current_session()` 刷新状态
- [ ] 实现"完成"按钮：
  - 调用 `POST /api/v1/focus/sessions/{id}/complete`
  - 显示成功提示 "专注完成"
  - 成功后调用 `load_current_session()` 刷新状态

**验证**：测试完整流程：暂停→恢复→完成

---

### 3.4 实现开始专注
- [ ] 从 `session_state.tasks` 读取任务列表
- [ ] 使用 `st.selectbox` 创建任务选择器
- [ ] 添加"开始专注"按钮：
  - 调用 `POST /api/v1/focus/sessions`，传入 `task_id`
  - 成功后调用 `load_current_session()` 刷新状态

**验证**：选择任务，点击"开始专注"，页面显示新会话

---

## 阶段 4：完整验收测试（顺序执行）

### 4.1 完整业务流程测试
- [ ] 测试流程 1：创建任务→设置Top3
  - 快速创建 3 个测试任务
  - 设置为 Top3
  - 验证成功提示和积分消耗
- [ ] 测试流程 2：任务树形结构
  - 创建父任务
  - 创建 2 个子任务（指定 parent_id）
  - 验证子任务正确缩进显示
- [ ] 测试流程 3：番茄钟完整流程
  - 选择任务，开始专注
  - 暂停专注
  - 恢复专注
  - 完成专注
  - 验证状态流转正确

**验收标准**：
- ✅ 任务树形视图正确显示父子关系
- ✅ 行内操作按钮功能正常
- ✅ Top3 设置成功并显示积分消耗
- ✅ 番茄钟状态流转正确
- ✅ 完整流程测试通过

---

## 总计任务数：17 个
- 阶段 1：6 个任务（任务管理页面）
- 阶段 2：2 个任务（Top3 管理页面）
- 阶段 3：4 个任务（番茄钟系统页面）
- 阶段 4：1 个任务（验收测试，含 3 个子流程）
