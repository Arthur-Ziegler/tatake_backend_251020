# streamlit-foundation Specification

## Purpose
TBD - created by archiving change sub1-build-streamlit-testing-panel. Update Purpose after archive.
## Requirements
### Requirement: 项目结构和配置
系统 MUST 创建完整的 Streamlit 项目结构，包含主入口、配置文件和核心模块。应用 SHALL 通过 `uv run streamlit run` 命令启动，并 MUST 在 localhost:8501 提供服务。

#### Scenario: 启动应用
```
GIVEN 后端 API 服务运行在 localhost:8001
WHEN 执行 `uv run streamlit run streamlit_app/main.py`
THEN 应用启动在 localhost:8501
AND 显示认证页面
```

---

### Requirement: API 客户端封装
系统 MUST 提供 API 客户端类，封装 HTTP 请求逻辑。客户端 SHALL 自动从 session_state 读取 Token 并注入到请求头，并 MUST 在 401 错误时显示提示。

#### Scenario: 自动注入 Token
```
GIVEN 用户已登录，Token 存储在 session_state.token
WHEN 调用 api_client.get("/api/v1/tasks")
THEN 请求头自动包含 "Authorization: Bearer {token}"
AND 成功返回 200 响应
```

#### Scenario: Token 失效处理
```
GIVEN 用户 Token 已过期
WHEN 调用 API 返回 401 错误
THEN 显示红色错误提示 "Token 已失效，请重新登录"
```

---

### Requirement: 状态管理器
系统 MUST 提供状态管理器，初始化 session_state 默认值。状态管理器 SHALL 维护 token、user_id、api_base_url 等核心状态。

#### Scenario: 初始化状态
```
GIVEN 用户首次打开应用
WHEN 调用 init_state()
THEN session_state.token 初始化为 None
AND session_state.user_id 初始化为 None
AND session_state.api_base_url 初始化为 "http://localhost:8001"
```

---

### Requirement: 认证系统页面
页面 MUST 实现游客初始化、刷新 Token 和认证状态展示功能。系统 SHALL 将获取的 access_token 和 user_id 存储到 session_state。

#### Scenario: 游客初始化
```
GIVEN 用户打开认证页面
WHEN 点击"游客初始化"按钮
THEN 调用 POST /api/v1/auth/guest/init
AND 将 access_token 存入 session_state.token
AND 将 user_id 存入 session_state.user_id
AND 显示成功提示 "游客初始化成功，User ID: {user_id}"
```

#### Scenario: 刷新 Token
```
GIVEN 用户已登录
WHEN 点击"刷新 Token"按钮
THEN 调用 POST /api/v1/auth/refresh
AND 更新 session_state.token
AND 显示成功提示 "Token 刷新成功"
```

#### Scenario: 查看认证状态
```
GIVEN 用户已登录
WHEN 打开认证页面
THEN 显示当前 User ID
AND 显示 Token 前 20 字符
```

---

### Requirement: 通用组件
系统 MUST 提供 JSON 查看器和错误处理组件，供后续业务页面复用。组件 SHALL 以可展开方式显示完整 JSON，错误处理 MUST 显示红色提示框。

#### Scenario: JSON 查看器
```
GIVEN API 返回 JSON 响应
WHEN 调用 render_json(data)
THEN 显示可展开的 JSON 查看器
AND 点击后显示格式化的 JSON 内容
```

#### Scenario: 错误处理
```
GIVEN API 返回错误响应 {"code": 404, "message": "任务不存在"}
WHEN 调用 show_error(response)
THEN 显示红色错误提示框 "错误：任务不存在"
AND 提供"查看完整响应"按钮
```

