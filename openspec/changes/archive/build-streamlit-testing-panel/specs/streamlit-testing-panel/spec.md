# Spec: Streamlit API 测试面板

## 概述
构建基于 Streamlit 的数据驱动 API 测试面板，覆盖全部 38 个 API 端点，消除手动参数输入痛点，实现快速测试 API 数据关联性。

## ADDED Requirements

### Requirement: 基础架构和配置
应用 MUST 搭建 Streamlit 基础框架，提供 API 客户端封装和自动状态管理。系统 SHALL 自动注入 JWT Token 到所有需要认证的 API 请求，并 MUST 在 Token 失效时显示错误提示。

#### Scenario: 启动应用并连接 API 服务
```
GIVEN 后端 API 服务运行在 localhost:8001
WHEN 执行 `uv run streamlit run streamlit_app/main.py`
THEN 应用启动在 localhost:8501
AND 侧边栏显示 8 个业务页面导航
AND 状态栏显示 API 服务器地址（可配置）
```

#### Scenario: API 客户端自动注入 Token
```
GIVEN 用户已登录，Token 存储在 session_state
WHEN 调用任意需要认证的 API
THEN 自动在请求头添加 "Authorization: Bearer {token}"
AND 成功请求返回 200 响应
```

#### Scenario: Token 失效自动提示
```
GIVEN 用户 Token 已过期
WHEN 调用 API 返回 401 错误
THEN 显示红色错误提示 "Token 已失效，请重新登录"
AND 引导用户跳转到认证页面
```

---

### Requirement: 认证系统页面
页面 MUST 实现游客初始化、登录、刷新 Token 功能。系统 SHALL 将获取的 access_token 和 user_id 存储到 session_state，并 MUST 显示当前认证状态。

#### Scenario: 游客快速初始化
```
GIVEN 用户打开认证页面
WHEN 点击"游客初始化"按钮
THEN 调用 POST /api/v1/auth/guest/init
AND 将返回的 access_token 存入 session_state.token
AND 将返回的 user_id 存入 session_state.user_id
AND 显示成功提示 "游客初始化成功，User ID: {user_id}"
```

#### Scenario: 刷新 Token
```
GIVEN 用户已登录
WHEN 点击"刷新 Token"按钮
THEN 调用 POST /api/v1/auth/refresh，传入当前 refresh_token
AND 更新 session_state.token
AND 显示成功提示 "Token 刷新成功"
```

#### Scenario: 查看当前认证状态
```
GIVEN 用户已登录
WHEN 打开认证页面
THEN 显示当前 User ID、Token（前 20 字符）和过期时间
```

---

### Requirement: 任务管理页面（数据驱动）
页面 MUST 以树形结构展示任务列表，每行 MUST 提供操作按钮（完成/删除/编辑），并 MUST 支持创建任务和子任务。系统 SHALL 自动刷新任务列表，子任务 MUST 正确缩进显示。支持快速创建测试任务（预设模板）和完整表单创建（含高级选项）。

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

### Requirement: 智能聊天页面（类微信界面）
页面 MUST 提供类微信界面：左侧会话列表，右侧聊天记录+输入框，并 MUST 支持创建会话和发送消息。系统 SHALL 自动加载会话列表和聊天历史，用户消息和 AI 回复 MUST 区分显示。

#### Scenario: 创建聊天会话
```
GIVEN 用户打开聊天页面
WHEN 点击"创建会话"按钮，输入 title="测试会话"
THEN 调用 POST /api/v1/chat/sessions
AND 新会话出现在左侧会话列表
AND 自动选中新会话
```

#### Scenario: 发送消息并查看回复
```
GIVEN 用户已选中一个会话（session_id=abc）
WHEN 在输入框输入"你好"，点击"发送"
THEN 调用 POST /api/v1/chat/sessions/abc/send，传入 content="你好"
AND 聊天记录区域显示 "👤 你: 你好"
AND 等待 API 响应后显示 "🤖 AI: {AI 回复内容}"
```

#### Scenario: 切换会话
```
GIVEN 左侧会话列表有多个会话
WHEN 点击另一个会话
THEN 右侧聊天记录区域切换到该会话的历史消息
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

#### Scenario: 完成专注会话
```
GIVEN 当前有活跃专注会话（session_id=abc）
WHEN 点击"完成"按钮
THEN 调用 POST /api/v1/focus/sessions/abc/complete
AND 显示成功提示 "专注完成，已用时：25 分钟"
AND 当前会话状态清空
```

---

### Requirement: 奖励系统页面
页面 MUST 显示奖品目录、我的材料、可用配方，并 MUST 支持一键兑换操作。系统 SHALL 以表格形式展示奖品和材料，兑换成功后 MUST 自动刷新相关列表。

#### Scenario: 查看奖品目录
```
GIVEN 用户打开奖励系统页面
WHEN 页面加载
THEN 调用 GET /api/v1/rewards/catalog
AND 以表格形式显示：奖品名称 | 所需积分 | 兑换按钮
```

#### Scenario: 积分兑换奖品
```
GIVEN 用户积分余额为 500
AND 奖品目录中有一个奖品（reward_id=abc，所需积分 300）
WHEN 点击该奖品的"兑换"按钮
THEN 调用 POST /api/v1/rewards/exchange/abc
AND 显示成功提示 "兑换成功，剩余积分：200"
AND 自动刷新"我的奖品"列表
```

#### Scenario: 查看我的材料
```
GIVEN 用户完成任务后获得材料
WHEN 切换到"我的材料"标签
THEN 调用 GET /api/v1/rewards/materials
AND 显示材料列表：材料名称 | 数量
```

#### Scenario: 使用配方兑换奖品
```
GIVEN 用户拥有材料（木材 x3, 石头 x2）
AND 存在配方（recipe_id=abc，需要木材 x2, 石头 x1）
WHEN 点击"使用配方兑换"按钮
THEN 调用 POST /api/v1/rewards/recipes/abc/redeem
AND 显示成功提示 "兑换成功，获得奖品：宝箱"
AND 自动刷新材料列表和奖品列表
```

---

### Requirement: 积分系统页面
页面 MUST 显示积分余额和完整流水记录。系统 SHALL 以大号字体突出显示积分余额，流水记录 MUST 包含时间、类型、变化、余额字段。

#### Scenario: 查看积分余额
```
GIVEN 用户打开积分系统页面
WHEN 页面加载
THEN 调用 GET /api/v1/points/my-points?user_id={user_id}
AND 大号字体显示积分余额：💰 当前积分：500
```

#### Scenario: 查看积分流水
```
GIVEN 用户有多笔积分记录
WHEN 点击"查看流水"按钮
THEN 调用 GET /api/v1/points/transactions?user_id={user_id}
AND 以表格显示：时间 | 类型 | 变化 | 余额
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

### Requirement: 用户管理页面
页面 MUST 支持查看和编辑个人资料。系统 SHALL 显示用户名、邮箱、注册时间，并 MUST 提供反馈提交表单。

#### Scenario: 查看个人资料
```
GIVEN 用户已登录
WHEN 打开用户管理页面
THEN 调用 GET /api/v1/users/profile
AND 显示：用户名、邮箱、注册时间
```

#### Scenario: 提交反馈
```
GIVEN 用户打开用户管理页面
WHEN 输入反馈内容"功能很好用"，点击"提交反馈"
THEN 调用 POST /api/v1/users/feedback
AND 显示成功提示 "反馈提交成功"
```

---

### Requirement: 通用功能
应用 MUST 提供统一的错误处理、JSON 查看器和数据刷新功能。系统 SHALL 在 API 错误时显示完整 JSON 响应，所有页面 MUST 提供手动刷新按钮。

#### Scenario: 错误响应完整显示
```
GIVEN API 返回错误响应（如 404 任务不存在）
WHEN 调用失败
THEN 显示红色错误提示框
AND 展示完整错误 JSON：{"code": 404, "message": "任务不存在"}
```

#### Scenario: 手动刷新数据
```
GIVEN 用户在任务管理页面
WHEN 点击页面右上角的"刷新"按钮
THEN 重新调用 GET /api/v1/tasks
AND 更新任务列表
```

## 测试验收
1. **覆盖率**：所有 38 个 API 端点均可通过 UI 调用
2. **数据驱动**：任务、聊天、奖励页面均无需手动输入 ID
3. **状态管理**：Token 自动注入，数据自动缓存
4. **交互体验**：任务树形视图正确缩进，聊天界面流畅
