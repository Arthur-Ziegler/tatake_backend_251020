# TaKeKe API 测试面板

基于 Streamlit 构建的 TaKeKe API 功能测试面板，提供友好的界面来测试和验证 API 功能。

## 🚀 快速开始

### 环境要求

- Python 3.11+
- uv 包管理器
- 运行中的 TaKeKe API 服务器（默认 http://localhost:8001）

### 启动步骤

1. **确保 API 服务器运行**
   ```bash
   # 在项目根目录启动 API 服务器
   uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
   ```

2. **启动 Streamlit 测试面板**
   ```bash
   # 在项目根目录运行
   uv run streamlit run streamlit_app/main.py
   ```

3. **访问测试面板**
   - 打开浏览器访问：http://localhost:8501
   - 左侧导航栏选择 "🏠 认证" 页面开始测试

## 📁 项目结构

```
streamlit_app/
├── main.py                 # 主入口文件
├── config.py               # 配置文件和全局 API 客户端
├── api_client.py           # HTTP 客户端封装
├── state_manager.py        # Session state 管理器
├── pages/                  # 页面文件
│   └── 1_🏠_认证.py        # 认证页面
├── components/             # 通用组件
│   ├── json_viewer.py      # JSON 查看器组件
│   └── error_handler.py    # 错误处理组件
└── README.md              # 本文档
```

## 🔧 核心功能

### 1. 认证管理
- **游客初始化**: 一键创建游客账号进行测试
- **Token 刷新**: 自动刷新过期的认证令牌
- **状态展示**: 实时显示当前认证状态

### 2. API 客户端
- **自动认证**: 自动从 session_state 注入 JWT Token
- **错误处理**: 统一的错误处理和用户友好提示
- **响应格式化**: 美观的 JSON 数据展示

### 3. 状态管理
- **Session 持久化**: 用户状态在会话期间保持
- **认证状态**: 统一的认证状态管理
- **配置管理**: 灵活的 API 端点配置

## 📖 使用指南

### 认证流程

1. **游客初始化**
   - 在左侧导航选择 "🏠 认证"
   - 点击 "🚀 游客初始化" 按钮
   - 系统会自动创建游客账号并获取 Token

2. **刷新 Token**
   - 认证成功后，如果 Token 过期
   - 点击 "🔄 刷新 Token" 按钮
   - 系统会获取新的认证令牌

3. **查看认证状态**
   - 页面顶部显示当前认证状态
   - 包含用户ID、用户类型和 Token 信息

### API 调用示例

```python
from streamlit_app.config import api_client

# GET 请求
response = api_client.get("/api/v1/tasks")

# POST 请求
response = api_client.post("/api/v1/tasks", json={
    "title": "测试任务",
    "description": "这是一个测试任务"
})

# PUT 请求
response = api_client.put("/api/v1/tasks/1", json={
    "title": "更新后的任务标题"
})
```

### 状态管理示例

```python
from streamlit_app.state_manager import (
    update_auth_state,
    is_authenticated,
    get_auth_headers
)

# 检查认证状态
if is_authenticated():
    st.success("已认证")

# 更新认证状态
update_auth_state(token, user_id, "guest")

# 获取认证头
headers = get_auth_headers()
```

## 🔍 错误处理

测试面板提供统一的错误处理机制：

- **400 请求参数错误**: 检查请求参数格式
- **401 认证失败**: 提示刷新 Token 或重新认证
- **403 权限不足**: 说明权限要求
- **404 资源不存在**: 检查请求路径
- **429 频率限制**: 提示降低请求频率
- **500 服务器错误**: 建议稍后重试

## 🛠️ 开发指南

### 添加新页面

1. 在 `pages/` 目录创建新的 Python 文件
2. 文件名格式：`{序号}_{图标}_{页面名称}.py`
3. 使用现有组件确保一致性

### 添加新组件

1. 在 `components/` 目录创建组件文件
2. 遵循现有的命名和结构规范
3. 提供完整的文档和错误处理

### API 客户端扩展

```python
# 在 api_client.py 中添加新方法
def custom_request(self, endpoint: str, **kwargs):
    return self.request("CUSTOM", endpoint, **kwargs)
```

## 🔧 配置选项

### 环境变量

- `API_BASE_URL`: API 服务器地址（默认: http://localhost:8001）

### 配置文件

在 `config.py` 中可以修改：
- API 端点地址
- 应用配置信息
- 全局客户端设置

## 🚨 注意事项

1. **安全性**: 测试面板仅用于开发测试，不要在生产环境使用
2. **数据隔离**: 游客数据可能被定期清理
3. **网络要求**: 需要能够访问 API 服务器
4. **浏览器兼容**: 建议使用现代浏览器（Chrome、Firefox、Safari）

## 🤝 贡献指南

1. 遵循现有的代码风格和结构
2. 添加适当的注释和文档
3. 确保错误处理的完整性
4. 测试所有新增功能

## 📞 支持

如果遇到问题：

1. 检查 API 服务器是否正常运行
2. 确认网络连接是否正常
3. 查看浏览器控制台错误信息
4. 联系开发团队获取帮助

---

**版本**: 1.0.0
**最后更新**: 2025-10-25
**维护者**: Claude Code Assistant