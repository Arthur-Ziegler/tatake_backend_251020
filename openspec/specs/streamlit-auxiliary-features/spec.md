# streamlit-auxiliary-features Specification

## Purpose
TBD - created by archiving change sub2.2-build-streamlit-testing-panel. Update Purpose after archive.
## Requirements
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

