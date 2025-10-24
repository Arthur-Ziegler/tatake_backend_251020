# Design: Streamlit API 测试面板架构

## 核心设计原则
1. **数据驱动 UI**：避免手动参数输入，通过列表+按钮直接操作
2. **自动状态管理**：session_state 维护所有 API 响应数据
3. **极简实现**：遵循 KISS 原则，功能优先，不做美化

## 技术栈
- **Streamlit 1.28+**：快速构建交互式 Web 应用
- **Requests**：HTTP 客户端
- **Python 3.11+**：与项目主体保持一致

## 架构设计

### 目录结构
```
streamlit_app/
├── main.py                 # 主入口（页面路由）
├── config.py               # 配置（API_BASE_URL="http://localhost:8001"）
├── api_client.py           # HTTP 客户端封装（自动注入 Token）
├── state_manager.py        # session_state 管理器
├── pages/
│   ├── 1_🏠_认证.py
│   ├── 2_📋_任务管理.py
│   ├── 3_💬_智能聊天.py
│   ├── 4_🍅_番茄钟.py
│   ├── 5_🎁_奖励系统.py
│   ├── 6_💰_积分系统.py
│   ├── 7_⭐_Top3管理.py
│   └── 8_👤_用户管理.py
└── components/
    ├── task_tree.py        # 任务树形视图组件
    ├── chat_interface.py   # 聊天界面组件
    ├── focus_status.py     # 番茄钟状态组件
    └── json_viewer.py      # JSON 可展开查看组件
```

### 核心模块设计

#### 1. API 客户端（api_client.py）
```python
class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def request(self, method, endpoint, **kwargs):
        # 自动从 session_state 注入 Token
        if "token" in st.session_state:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            kwargs.setdefault("headers", {}).update(headers)

        response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)

        # 自动处理 401 Token 失效
        if response.status_code == 401:
            st.error("Token 已失效，请重新登录")
            return None

        return response.json()
```

#### 2. 状态管理器（state_manager.py）
```python
def init_state():
    """初始化 session_state"""
    defaults = {
        "token": None,
        "user_id": None,
        "tasks": [],
        "chat_sessions": [],
        "focus_session": None,
        "points_balance": 0,
        "my_rewards": [],
        "top3_records": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def refresh_tasks():
    """刷新任务列表"""
    response = api_client.get("/api/v1/tasks")
    if response and response.get("code") == 200:
        st.session_state.tasks = response["data"]["items"]
```

#### 3. 任务树形视图（components/task_tree.py）
```python
def render_task_tree(tasks: list):
    """渲染任务树（递归缩进）"""
    root_tasks = [t for t in tasks if not t.get("parent_id")]

    for task in root_tasks:
        render_task_node(task, tasks, level=0)

def render_task_node(task, all_tasks, level):
    """渲染单个任务节点"""
    indent = "　" * level  # 全角空格缩进
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

    with col1:
        st.write(f"{indent}📌 {task['title']}")
    with col2:
        st.write(task['status'])
    with col3:
        if st.button("完成", key=f"complete_{task['id']}"):
            api_client.post(f"/api/v1/tasks/{task['id']}/complete")
            refresh_tasks()
    with col4:
        if st.button("删除", key=f"delete_{task['id']}"):
            api_client.delete(f"/api/v1/tasks/{task['id']}")
            refresh_tasks()

    # 递归渲染子任务
    children = [t for t in all_tasks if t.get("parent_id") == task["id"]]
    for child in children:
        render_task_node(child, all_tasks, level + 1)
```

#### 4. 聊天界面（components/chat_interface.py）
```python
def render_chat_interface(session_id: str):
    """类微信聊天界面"""
    # 加载聊天历史
    messages = api_client.get(f"/api/v1/chat/sessions/{session_id}/messages")

    # 消息列表容器（固定高度，可滚动）
    with st.container(height=400):
        for msg in messages.get("data", []):
            if msg["role"] == "user":
                st.markdown(f"**👤 你**: {msg['content']}")
            else:
                st.markdown(f"**🤖 AI**: {msg['content']}")

    # 输入框 + 发送按钮
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input("输入消息", key=f"chat_input_{session_id}")
    with col2:
        if st.button("发送", key=f"send_{session_id}"):
            api_client.post(
                f"/api/v1/chat/sessions/{session_id}/send",
                json={"content": user_input}
            )
            st.rerun()  # 刷新界面显示新消息
```

## 关键技术决策

### 决策 1：为什么选择 Streamlit？
**备选方案**：
- HTML + Vanilla JS：更流畅，但开发成本高
- Gradio：功能类似，但定制能力弱
- Postman Collection：专业但不直观

**选择 Streamlit 原因**：
- 快速开发（纯 Python，无需前端知识）
- 自动状态管理（`session_state` 机制）
- 符合项目 `uv` 依赖管理

### 决策 2：数据驱动 vs 表单驱动
**选择数据驱动**：
- 表单驱动：每次调用 API 都要填参数（SwaggerUI 的痛点）
- 数据驱动：先加载数据列表，再通过按钮操作（核心需求）

**实现方式**：
1. 页面加载时自动调用列表 API（如 `GET /tasks`）
2. 渲染数据表格/树形视图
3. 每行数据提供操作按钮（完成/删除/编辑）
4. 按钮点击后自动使用该行数据的 ID 调用 API

### 决策 3：Token 管理策略
**方案**：
1. 登录/初始化后将 Token 存入 `session_state.token`
2. `api_client.request()` 自动注入 `Authorization` 头
3. 检测到 401 错误时显示提示，引导用户重新登录
4. 提供"刷新 Token"按钮（调用 `/auth/refresh`）

### 决策 4：错误处理
**原则**：
- 显示完整错误响应（JSON）
- 红色提示框（`st.error()`）
- 不做复杂的错误恢复（保持简单）

## 性能考虑
- **按需加载**：只在切换页面时调用对应的列表 API
- **缓存响应**：通过 `session_state` 避免重复请求
- **手动刷新**：提供"刷新"按钮，而非自动轮询

## 安全考虑
- **仅用于本地测试**：不暴露到公网
- **Token 存储在 session_state**：关闭浏览器即清空
- **不存储敏感数据**：仅展示 API 响应，不持久化
