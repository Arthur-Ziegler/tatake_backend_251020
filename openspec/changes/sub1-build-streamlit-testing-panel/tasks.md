# Tasks: Streamlit 测试面板基础架构实施

## 阶段 1：项目搭建（顺序执行）

### 1.1 创建项目结构
- [ ] 创建 `streamlit_app/` 目录
- [ ] 创建 `main.py`（主入口）
- [ ] 创建 `config.py`（配置文件）
- [ ] 创建 `pages/` 和 `components/` 子目录
- [ ] 添加 Streamlit 依赖：`uv add streamlit>=1.28.0 requests`

**验证**：运行 `uv run streamlit run streamlit_app/main.py`，显示空白页面

---

### 1.2 实现 API 客户端
- [ ] 编写 `api_client.py`：
  - `APIClient` 类定义
  - `request()` 方法：自动注入 Token
  - `get()`, `post()`, `put()`, `delete()` 快捷方法
  - 401 错误处理
- [ ] 在 `config.py` 中创建全局 `api_client` 实例

**验证**：手动调用 `api_client.get("/health")`，返回 API 响应

---

### 1.3 实现状态管理器
- [ ] 编写 `state_manager.py`：
  - `init_state()` 函数
  - 初始化 `token`, `user_id`, `api_base_url` 默认值
- [ ] 在 `main.py` 中调用 `init_state()`

**验证**：打印 `st.session_state`，确认默认值已设置

---

## 阶段 2：认证系统页面（顺序执行）

### 2.1 创建认证页面
- [ ] 创建 `pages/1_🏠_认证.py`
- [ ] 实现游客初始化功能：
  - "游客初始化"按钮
  - 调用 `POST /api/v1/auth/guest/init`
  - 存储 Token 和 User ID 到 session_state
  - 显示成功提示
- [ ] 实现刷新 Token 功能：
  - "刷新 Token"按钮
  - 调用 `POST /api/v1/auth/refresh`
  - 更新 session_state.token
- [ ] 实现认证状态展示：
  - 显示当前 User ID
  - 显示 Token 前 20 字符

**验证**：
1. 点击"游客初始化"，成功获取 Token
2. 刷新页面，Token 丢失（符合预期）
3. 点击"刷新 Token"，Token 更新

---

## 阶段 3：通用组件（可并行）

### 3.1 JSON 查看器组件
- [ ] 创建 `components/json_viewer.py`
- [ ] 实现 `render_json(data, title)` 函数：
  - 使用 `st.expander` 可展开容器
  - 使用 `st.json()` 显示格式化 JSON

**验证**：在认证页面调用 `render_json()`，显示 API 响应

---

### 3.2 错误处理组件
- [ ] 创建 `components/error_handler.py`
- [ ] 实现 `show_error(response)` 函数：
  - 检测 `code != 200`
  - 显示红色错误提示框（`st.error()`）
  - 提供"查看完整响应"按钮

**验证**：模拟 404 错误，显示错误提示

---

## 阶段 4：文档和验收（顺序执行）

### 4.1 编写文档
- [ ] 创建 `streamlit_app/README.md`：
  - 启动指南
  - 目录结构说明
  - API 客户端使用示例
  - 状态管理器使用说明
- [ ] 在根目录 `README.md` 添加测试面板启动说明

**验证**：按照文档指南，新用户可成功启动应用

---

### 4.2 完整验收测试
- [ ] 测试完整认证流程：
  - 游客初始化
  - 刷新 Token
  - 查看认证状态
- [ ] 验证 API 客户端自动注入 Token
- [ ] 验证通用组件可复用

**验收标准**：
- ✅ 运行 `uv run streamlit run streamlit_app/main.py` 成功启动
- ✅ 认证页面可获取 Token 并存入 session_state
- ✅ API 客户端自动注入 Token
- ✅ JSON 查看器和错误处理组件可正常使用

---

## 总计任务数：15 个
- 阶段 1：3 个任务
- 阶段 2：1 个任务（含 3 个子功能）
- 阶段 3：2 个任务（可并行）
- 阶段 4：2 个任务
