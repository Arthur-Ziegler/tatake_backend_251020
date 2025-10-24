# Design: Streamlit 测试面板基础架构

## 核心设计原则
1. **极简基础**：只实现必需的基础设施，不做过度设计
2. **可复用性**：API 客户端和状态管理器可被后续提案直接使用
3. **统一标准**：提供一致的错误处理和响应格式

## 技术栈
- **Streamlit 1.28+**：Web 应用框架
- **Requests**：HTTP 客户端
- **Python 3.11+**：与项目主体一致

## 目录结构
```
streamlit_app/
├── main.py                 # 主入口（显示认证页面）
├── config.py               # 配置（API_BASE_URL="http://localhost:8001"）
├── api_client.py           # HTTP 客户端封装
├── state_manager.py        # session_state 管理器
├── pages/                  # 业务页面（提案 2.1 和 2.2 实现）
│   └── 1_🏠_认证.py
└── components/             # 通用组件
    ├── json_viewer.py      # JSON 可展开查看
    └── error_handler.py    # 错误提示组件
```

## 核心模块设计

### 1. API 客户端（api_client.py）
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

        # 自动处理 401
        if response.status_code == 401:
            st.error("Token 已失效，请重新登录")
            return None

        return response.json()

    def get(self, endpoint, **kwargs):
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        return self.request("POST", endpoint, **kwargs)
```

### 2. 状态管理器（state_manager.py）
```python
def init_state():
    """初始化 session_state"""
    defaults = {
        "token": None,
        "user_id": None,
        "api_base_url": "http://localhost:8001"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
```

### 3. 认证页面（pages/1_🏠_认证.py）
提供三个功能：
- 游客初始化（调用 `/api/v1/auth/guest/init`）
- 刷新 Token（调用 `/api/v1/auth/refresh`）
- 显示当前认证状态（User ID、Token 前缀）

### 4. 通用组件

#### JSON 查看器（components/json_viewer.py）
```python
def render_json(data: dict, title: str = "响应详情"):
    with st.expander(title):
        st.json(data)
```

#### 错误处理（components/error_handler.py）
```python
def show_error(response: dict):
    if response and response.get("code") != 200:
        st.error(f"错误：{response.get('message')}")
        with st.expander("查看完整响应"):
            st.json(response)
```

## 关键技术决策

### 决策 1：为什么不实现业务页面？
**原因**：
- 基础架构和业务逻辑解耦，便于并行开发
- 减少提案 1 的工作量，加快交付速度
- 提案 2.1 和 2.2 可以专注业务逻辑

### 决策 2：认证页面为什么放在提案 1？
**原因**：
- 认证是所有业务页面的前置依赖
- Token 管理是基础设施的一部分
- 避免提案 2.1 和 2.2 重复实现认证逻辑

### 决策 3：API 客户端的设计
**选择单例模式**：
```python
# config.py
api_client = APIClient(base_url="http://localhost:8001")
```
**原因**：
- 全局共享一个客户端实例
- 后续提案直接 `from streamlit_app.config import api_client` 使用
- 简化使用方式

## 性能考虑
- **最小化依赖**：只安装 Streamlit 和 Requests
- **延迟加载**：业务页面在提案 2 中实现，不影响基础架构启动速度

## 安全考虑
- **仅本地测试**：不暴露到公网
- **Token 内存存储**：关闭浏览器即清空
