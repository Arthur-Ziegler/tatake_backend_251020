# Design: Streamlit 测试面板任务流程

## 核心设计原则
1. **数据驱动 UI**：列表中每行自动关联 ID 操作按钮
2. **树形可视化**：子任务缩进显示，清晰展示父子关系
3. **实时状态更新**：操作后自动刷新列表

## 技术栈
- 复用提案 1 的基础架构（API 客户端、状态管理器）
- Streamlit 原生组件（无需额外依赖）

## 核心模块设计

### 1. 任务管理页面（pages/2_📋_任务管理.py）

#### 数据加载
```python
def load_tasks():
    response = api_client.get("/api/v1/tasks")
    if response and response.get("code") == 200:
        st.session_state.tasks = response["data"]["items"]
```

#### 树形视图渲染
```python
def render_task_tree(tasks: list):
    root_tasks = [t for t in tasks if not t.get("parent_id")]
    for task in root_tasks:
        render_task_node(task, tasks, level=0)

def render_task_node(task, all_tasks, level):
    indent = "　" * level  # 全角空格缩进
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

    with col1:
        st.write(f"{indent}📌 {task['title']}")
    with col2:
        st.write(task['status'])
    with col3:
        if st.button("完成", key=f"complete_{task['id']}"):
            api_client.post(f"/api/v1/tasks/{task['id']}/complete")
            load_tasks()  # 刷新列表
    with col4:
        if st.button("删除", key=f"delete_{task['id']}"):
            api_client.delete(f"/api/v1/tasks/{task['id']}")
            load_tasks()

    # 递归渲染子任务
    children = [t for t in all_tasks if t.get("parent_id") == task["id"]]
    for child in children:
        render_task_node(child, all_tasks, level + 1)
```

#### 创建任务
```python
# 快速创建
if st.button("快速创建测试任务"):
    api_client.post("/api/v1/tasks", json={
        "title": f"测试任务_{datetime.now().strftime('%H%M%S')}",
        "priority": 1
    })
    load_tasks()

# 完整表单
with st.expander("创建任务（完整表单）"):
    title = st.text_input("标题")
    description = st.text_area("描述")
    priority = st.number_input("优先级", 1, 5, 1)

    with st.expander("高级选项"):
        parent_id = st.selectbox("父任务", options=[None] + [t["id"] for t in tasks])

    if st.button("提交"):
        api_client.post("/api/v1/tasks", json={...})
        load_tasks()
```

### 2. Top3 管理页面（pages/7_⭐_Top3管理.py）

#### 设置 Top3
```python
tasks = st.session_state.get("tasks", [])
selected_tasks = st.multiselect(
    "选择 Top3 任务（1-3个）",
    options=[t["id"] for t in tasks],
    format_func=lambda id: next(t["title"] for t in tasks if t["id"] == id)
)

if st.button("设置 Top3"):
    if 1 <= len(selected_tasks) <= 3:
        api_client.post("/api/v1/tasks/top3", json={"task_ids": selected_tasks})
        st.success("Top3 设置成功，消耗 300 积分")
    else:
        st.error("请选择 1-3 个任务")
```

#### 查询历史
```python
date = st.date_input("选择日期")
if st.button("查询"):
    response = api_client.get(f"/api/v1/tasks/top3/{date}")
    st.json(response)
```

### 3. 番茄钟系统页面（pages/4_🍅_番茄钟.py）

#### 当前会话状态
```python
def load_current_session():
    response = api_client.get("/api/v1/focus/sessions?status=active")
    if response and response.get("data"):
        st.session_state.current_focus = response["data"][0]
    else:
        st.session_state.current_focus = None

# 显示当前会话
if st.session_state.get("current_focus"):
    session = st.session_state.current_focus
    st.info(f"当前专注：任务 {session['task_id']} | 状态：{session['status']}")

    if session['status'] == 'focus':
        if st.button("暂停"):
            api_client.post(f"/api/v1/focus/sessions/{session['id']}/pause")
            load_current_session()
    elif session['status'] == 'pause':
        if st.button("恢复"):
            api_client.post(f"/api/v1/focus/sessions/{session['id']}/resume")
            load_current_session()

    if st.button("完成"):
        api_client.post(f"/api/v1/focus/sessions/{session['id']}/complete")
        st.success("专注完成")
        load_current_session()
```

#### 开始专注
```python
tasks = st.session_state.get("tasks", [])
selected_task = st.selectbox("选择任务", options=[t["id"] for t in tasks])

if st.button("开始专注"):
    api_client.post("/api/v1/focus/sessions", json={"task_id": selected_task})
    load_current_session()
```

## 关键技术决策

### 决策 1：为什么使用递归渲染任务树？
**原因**：
- 支持无限层级嵌套
- 代码简洁，逻辑清晰
- 自动计算缩进层级

### 决策 2：为什么每个操作后都调用 load_tasks()？
**原因**：
- 确保 UI 显示最新数据
- 避免状态不一致
- 简化状态管理逻辑

### 决策 3：为什么 Top3 和番茄钟在同一提案？
**原因**：
- 两者都依赖任务管理
- 可以测试完整的任务生命周期
- 集中验证数据关联性

## 性能考虑
- **按需加载**：只在页面切换时加载数据
- **缓存列表**：任务列表存储在 session_state，避免重复请求
- **手动刷新**：提供刷新按钮，而非自动轮询

## 用户体验优化
- **快速创建**：一键生成测试任务，无需填写表单
- **智能下拉**：父任务选择、Top3 任务选择使用友好的下拉框
- **状态提示**：操作成功/失败立即显示提示
