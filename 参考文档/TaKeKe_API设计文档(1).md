# TaKeKe API 设计文档 - 最终实施版

> **文档版本**: v3.1
> **更新时间**: 2025-10-13 22:58 (北京时间)

---

## 📋 项目概述

### 项目定位
TaKeKe是一个AI驱动的智能任务管理小程序，采用游客模式+游戏化激励机制，帮助用户提升专注力和任务完成效率。

### 核心功能
1. **AI对话系统**: 纯对话功能，多媒体消息支持(待补充)
2. **任务树管理**: 无限层级任务结构，实时完成度计算
3. **番茄钟专注**: 25分钟专注 + 5分钟休息循环
4. **游戏化激励**: 任务完成即时抽奖 + 碎片收集 + 积分奖励
5. **游客模式**: 零门槛体验，无缝升级为正式账号

### 技术规范
- **协议**: RESTful API + OpenAPI 3.1.0
- **认证**: JWT Token + RefreshToken
- **数据格式**: JSON
- **编码**: UTF-8
- **响应格式**: 统一结构化响应

---

## 🎯 统一响应格式

所有API接口都使用统一的响应格式：

```typescript
interface ApiResponse<T> {
  code: number;           // 响应状态码 (200成功，其他为错误码)
  message: string;        // 响应消息 (成功或错误描述)
  data?: T;              // 响应数据 (成功时返回具体数据)
  timestamp: string;      // 响应时间戳 (ISO 8601格式)
  traceId: string;        // 追踪ID (用于问题定位)
}
```

### 错误响应示例
```json
{
  "code": 40001,
  "message": "用户名或密码错误",
  "timestamp": "2025-10-13T14:30:00Z",
  "traceId": "trace_abc123"
}
```

---

## 📋 API端口清单

> **重要说明**: 以下API清单为最终权威版本，所有开发实施均以此为准

### 1. 🔐 认证系统 (7个API)

| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 1 | POST | `/auth/guest/init` | 游客账号初始化 |
| 2 | POST | `/auth/guest/upgrade` | 游客账号升级 |
| 3 | POST | `/auth/sms/send` | 发送短信验证码 |
| 4 | POST | `/auth/login` | 用户登录 (支持多种方式) |
| 5 | POST | `/auth/refresh` | 刷新访问令牌 |
| 6 | POST | `/auth/logout` | 用户登出 |
| 7 | GET | `/auth/user-info` | 获取当前用户信息 |

### 2. 💬 AI对话系统 (4个API)

| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 1 | POST | `/chat/sessions` | 创建新对话会话 |
| 2 | POST | `/chat/sessions/{session_id}/send` | 发送消息给AI |
| 3 | GET | `/chat/sessions/{session_id}/history` | 获取特定会话历史 |
| 4 | GET | `/chat/sessions` | 获取用户所有会话列表 |

### 3. 🌳 任务树系统 (12个API)

#### 核心任务管理 (5个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 1 | POST | `/tasks` | 创建任务 |
| 2 | GET | `/tasks/tree/{task_id}` | 获取特定任务的子树（这个端点删除） |
| 3 | GET | `/tasks/{id}` | 获取特定任务详情 |
| 4 | PUT | `/tasks/{id}` | 更新任务信息 |
| 5 | DELETE | `/tasks/{id}` | 删除任务(软删除) |

#### 任务操作 (2个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 6 | POST | `/tasks/{id}/complete` | 标记任务完成(含心情反馈+抽奖) |
| 7 | POST | `/tasks/{id}/uncomplete` | 取消任务完成状态 |

#### 任务搜索与筛选 (2个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 8 | GET | `/tasks/search` | 全文搜索任务 |
| 9 | GET | `/tasks/filter` | 高级筛选任务 |

#### Top3管理 (3个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 10 | POST | `/tasks/top3` | 设定每日Top3任务 |
| 11 | PUT | `/tasks/top3/{date}` | 修改指定日期的Top3任务 |
| 12 | GET | `/tasks/top3/{date}` | 查看指定日期的Top3任务 |

### 4. 🎯 番茄钟系统 (8个API)

#### 专注会话管理 (5个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 1 | POST | `/focus/sessions` | 开始专注会话（必须绑定task_id） |
| 2 | GET | `/focus/sessions/{id}` | 获取会话详情 |
| 3 | PUT | `/focus/sessions/{id}/pause` | 暂停专注会话 |
| 4 | PUT | `/focus/sessions/{id}/resume` | 恢复专注会话 |
| 5 | POST | `/focus/sessions/{id}/complete` | 完成专注会话 |

#### 专注记录与统计 (3个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 6 | GET | `/focus/sessions` | 获取用户专注记录 |
| 7 | GET | `/focus/statistics` | 专注统计(趋势+分布+时长) |
| 8 | GET | `/focus/tasks/{taskId}/sessions` | 获取特定任务的专注记录 |

### 5. 🏆 奖励系统 (8个API)

#### 奖品管理 (3个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 1 | GET | `/rewards/catalog` | 获取可兑换奖品目录 |
| 2 | GET | `/rewards/collection` | 获取用户碎片收集状态 |
| 3 | POST | `/rewards/redeem` | 兑换(集齐碎片兑换实体奖品或单个碎片兑换积分) |

#### 积分系统 (5个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 4 | GET | `/points/balance` | 获取用户积分余额 |
| 5 | GET | `/points/transactions` | 获取积分变动记录 |
| 6 | GET | `/points/packages` | 获取积分套餐列表 |
| 7 | POST | `/points/purchase` | 购买积分(生成支付二维码) |
| 8 | GET | `/points/purchase/{id}` | 查询支付详情和结果 |

### 6. 📊 统计系统 (5个API)

#### 综合统计API (5个API)
| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 1 | GET | `/statistics/dashboard` | 综合仪表板数据(含任务+专注统计) |
| 2 | GET | `/statistics/tasks` | 任务完成统计(按时间分组) |
| 3 | GET | `/statistics/focus` | 专注统计(趋势+分布+时长) |

### 7. 👤 用户系统 (4个API)

| 序号 | HTTP方法 | API路径 | 功能描述 |
|------|----------|---------|----------|
| 1 | GET | `/user/profile` | 获取用户基本信息(含设置) |
| 2 | PUT | `/user/profile` | 更新用户信息 |
| 3 | POST | `/user/avatar` | 上传用户头像 |
| 4 | POST | `/user/feedback` | 提交用户反馈 |

---

## 🎯 关键业务流程设计

### 1. 任务完成流程 (核心)
```
POST /tasks/{id}/complete
├── 请求参数:
│   ├── mood_feedback (心情反馈 - 强制)
│   └── completion_notes (完成备注 - 可选)
├── 响应数据:
│   ├── task (更新后的任务)
│   ├── lottery_result (抽奖结果 - 积分或碎片)
│   ├── completion_stats (完成统计)
│   └── points_earned (获得积分)
```

### 2. 奖品兑换流程 (精确碎片管理)
```
GET /rewards/collection (查看碎片收集)
├── 按奖品分类的碎片数量
├── 每个奖品的碎片收集进度
├── 可兑换状态判断
└── 积分余额信息

POST /rewards/redeem (兑换奖品)
├── 碎片兑换实物奖品(需要集齐数量)
├── 碎片兑换积分(按比例转换)
└── 积分直接兑换奖品
```

### 3. 积分购买流程
```
GET /points/packages (查询积分套餐)
├── 套餐列表和价格
├── 套餐详情和优惠信息
└── 用户选择套餐

POST /points/purchase (生成支付二维码)
├── 提交套餐ID
├── 生成支付二维码
├── 返回订单信息(含订单ID)
└── 订单状态为pending

GET /points/purchase/{id} (查询支付详情和结果)
├── 订单状态查询(pending/paid/failed/expired)
├── 支付成功时返回积分到账详情
├── 支付失败时返回失败原因
└── 订单完整信息(前端可据此显示不同状态)
```

### 4. 专注会话管理流程
```
POST /focus/sessions (开始专注会话)
├── 必须提供 task_id (强制关联)
├── 设定专注时长
└── 会话状态初始化

POST /focus/sessions/{id}/complete (完成专注会话)
├── 中断原因记录 (如果中断)
├── 心情反馈 (强制)
├── 实际专注时长
└── 获得专注积分奖励
```

### 5. AI对话session管理
```
POST /chat/sessions (创建会话)
├── 主题设置
├── session_id生成
└── 会话持久化

POST /chat/sessions/{session_id}/send (发送消息)
├── 消息历史关联
├── 上下文保持
└── AI回复
```

### 6. Top3任务设置流程
```
POST /tasks/top3 (设置Top3)
├── 积分余额检查 (必须>=300)
├── 消耗300积分
├── 每日只能设置一次
└── 返回设置结果

PUT /tasks/top3/{date} (修改Top3)
├── 调整当日重要任务
└── 保持积分消耗不变
```

---

## 🔐 认证系统 (7个API)

### 核心设计
- **游客模式**: 零门槛体验，支持数据无缝迁移
- **多途径认证**: 支持手机号、邮箱、微信登录
- **安全机制**: JWT Token + RefreshToken双重令牌
- **短信验证**: 支持手机号验证码登录和注册
- **完整登出**: 支持Token失效和清理

### API详情

#### 1. POST /auth/guest/init
**用途**: 游客账号初始化，创建临时访问权限
```typescript
// 请求
interface GuestInitRequest {
  device_id?: string;     // 设备ID(可选)
  platform?: string;      // 平台信息(可选)
}

// 响应
interface GuestInitResponse {
  user_id: string;        // 游客用户ID
  access_token: string;   // 访问令牌
  refresh_token: string;  // 刷新令牌
  expires_in: number;     // 令牌过期时间(秒)
  is_guest: boolean;      // 游客标识
}
```

#### 2. POST /auth/guest/upgrade
**用途**: 游客账号升级为正式账号
```typescript
// 请求
interface GuestUpgradeRequest {
  upgrade_type: "phone" | "email" | "wechat";

  // 手机号升级
  phone?: string;
  password?: string;
  sms_code?: string;

  // 邮箱升级
  email?: string;
  email_code?: string;

  // 微信升级
  wechat_openid?: string;
}

// 响应
interface GuestUpgradeResponse {
  user_id: string;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  is_guest: boolean;      // false
  user_info: {
    nickname: string;
    avatar?: string;
    phone?: string;
    email?: string;
    wechat_openid?: string;
  }
}
```

#### 3. POST /auth/login
**用途**: 用户登录
```typescript
// 请求
interface LoginRequest {
  login_type: "phone_password" | "phone_sms" | "email_password" | "email_code" | "wechat";

  // 手机号登录
  phone?: string;
  password?: string;
  sms_code?: string;

  // 邮箱登录
  email?: string;
  email_code?: string;

  // 微信登录
  wechat_openid?: string;
}

// 响应
interface LoginResponse {
  user_id: string;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  is_guest: boolean;      // false
  user_info: {
    nickname: string;
    avatar?: string;
    phone?: string;
    email?: string;
    wechat_openid?: string;
  }
}
```

#### 4. POST /auth/sms/send
**用途**: 发送短信验证码
```typescript
// 请求
interface SendSmsRequest {
  phone: string;                 // 手机号
  type: "login" | "register" | "reset_password"; // 短信类型
}

// 响应
interface SendSmsResponse {
  success: boolean;
  message: string;               // 发送结果消息
  cooldown_seconds?: number;     // 冷却时间(秒)
  next_send_time?: string;        // 下次可发送时间
}
```

#### 5. POST /auth/refresh
**用途**: 刷新访问令牌
```typescript
// 请求
interface RefreshRequest {
  refresh_token: string;
}

// 响应
interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}
```

#### 6. POST /auth/logout
**用途**: 用户登出
```typescript
// 请求
interface LogoutRequest {
  refresh_token?: string;       // 可选，用于失效refresh token
}

// 响应
interface LogoutResponse {
  success: boolean;
  message: string;
}
```

#### 7. GET /auth/user-info
**用途**: 获取当前用户信息
```typescript
// 响应
interface UserInfoResponse {
  user: {
    id: string;
    nickname: string;
    avatar?: string;
    phone?: string;
    email?: string;
    wechat_openid?: string;
    is_guest: boolean;
    created_at: string;
    last_login_at: string;
  };
}
```

---

## 💬 AI对话系统 (4个API)

### 核心设计
- **纯对话功能**: AI只负责对话，任务管理在后台通过工具进行
- **多媒体支持**: 支持文本、图片、语音、文件（其他模态待支持）
- **会话管理**: 支持多个主题会话
- **Session持久化**: 每个会话独立管理和持久化
- **历史记录**: 支持会话历史查询和会话列表

### API详情

#### 1. POST /chat/sessions
**用途**: 创建新对话会话

```typescript
// 请求
interface CreateChatSessionRequest {
  title?: string;                // 会话标题(可选，AI自动生成)
  initial_message?: string;      // 初始消息(可选)
}

// 响应
interface CreateChatSessionResponse {
  session_id: string;            // 会话ID
  title: string;                 // 会话标题
  created_at: string;            // 创建时间
}
```

#### 2. POST /chat/sessions/{session_id}/send
**用途**: 发送消息给AI
```typescript
// 请求
interface ChatSendRequest {
  message_type: "text" | "image" | "voice" | "file";
  content: string;               // 消息内容
  file_url?: string;             // 文件URL(非文本消息时)
}

// 响应
interface ChatSendResponse {
  message_id: string;            // 消息ID
  ai_response: {
    message_type: "text" | "image" | "voice" | "file";
    content: string;             // AI回复内容
    file_url?: string;           // AI回复文件URL
    metadata?: object;           // 回复元数据
  };
}
```

#### 3. GET /chat/sessions/{session_id}/history
**用途**: 获取特定会话历史
```typescript
// 请求参数
interface ChatHistoryQuery {
  page?: number;                 // 页码(默认1)
  page_size?: number;            // 每页数量(默认20)
}

// 响应
interface ChatHistoryResponse {
  session_id: string;
  messages: Array<{
    message_id: string;
    sender: "user" | "ai"| "tool";
    message_type: "text" | "image" | "voice" | "file";
    content: string;
    file_url?: string;
    timestamp: string;
  }>;
  pagination: {
    current_page: number;
    total_pages: number;
    total_count: number;
    page_size: number;
  };
}
```

#### 4. GET /chat/sessions
**用途**: 获取用户所有会话列表
```typescript
// 请求参数
interface ChatListQuery {
  page?: number;                 // 页码(默认1)
  page_size?: number;            // 每页数量(默认20)
}

// 响应
interface ChatListResponse {
  sessions: Array<{
    session_id: string;
    title: string;
    last_time: string;
    message_count: number;
  }>;
  pagination: {
    current_page: number;
    total_pages: number;
    total_count: number;
    page_size: number;
  };
}
```

---

## 🌳 任务树系统 (11个API)

### 核心设计
- **无限层级**: 支持任务树的无限层级结构
- **实时完成度**: 基于叶子节点实时计算完成度
- **灵活筛选**: 支持全文搜索和高级筛选（通过标签与时间）
- **Top3机制**: 每日重要任务管理，支持修改
- **任务完成**: 集成心情反馈和抽奖机制

### 数据模型
```typescript
interface Task {
  id: string;                     // 任务ID
  user_id: string;                // 用户ID
  parent_id?: string;             // 父任务ID
  predecessor_id?: string;        // 前驱任务ID
  title: string;                  // 任务标题
  description?: string;           // 任务详情
  status: "pending" | "in_progress" | "completed" | "cancelled"| "deleted";
  priority: "low" | "medium" | "high";
  due_date?: string;              // 截止日期
  planned_start_time?: string;    // 计划开始时间
  planned_end_time?: string;      // 计划结束时间
  estimated_pomodoros: number;    // 预计番茄数
  actual_pomodoros: number;       // 实际番茄数
  tags: string[];                 // 标签列表
  service_ids: string[];          // 关联服务ID列表
  completion_percentage: number;  // 完成百分比(自动计算)
  level: number;                  // 任务层级
  path: string;                   // 任务路径(如: "1/3/5")
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

interface TaskTop3 {
  id: string;
  user_id: string;
  date: string;                   // 日期(YYYY-MM-DD)
  task_id: string;                // 任务ID
  position: number;               // 位置(1/2/3)
  created_at: string;
}
```

### API详情

#### 核心任务管理 (5个API)

##### 1. POST /tasks
**用途**: 创建任务

```typescript
// 请求
interface CreateTaskRequest {
  title: string;                  // 任务标题
  description?: string;           // 任务详情
  priority?: "low" | "medium" | "high";
  due_date?: string;              // 截止日期
  planned_start_time?: string;    // 计划开始时间
  planned_end_time?: string;      // 计划结束时间
  estimated_pomodoros?: number;   // 预计番茄数
  tags?: string[];                // 标签列表
}

// 响应
interface CreateTaskResponse {
  task: Task;                     // 完整任务信息
}
```

##### 2. GET /tasks/tree/{task_id}
**用途**: 获取特定任务的子树
```typescript
// 请求参数
interface TaskTreeQuery {
  include_completed?: boolean;    // 是否包含已完成任务
  max_depth?: number;             // 最大深度(可选)
  filter_tags?: string[];         // 标签过滤(可选)
}

// 响应
interface TaskTreeResponse {
  tree: Task[];                   // 任务树结构(只包含 任务 id)
  total_count: number;            // 总任务数
  completed_count: number;        // 已完成任务数
}
```

##### 3. GET /tasks/{id}
**用途**: 获取特定任务详情

```typescript
// 响应
interface TaskDetailResponse {
  task: Task;                     // 任务详情
  children: Task[];               // 子任务列表
  parent?: Task;                  // 父任务信息
  path_tasks: Task[];             // 路径上的所有任务
}
```

##### 4. PUT /tasks/{id}
**用途**: 更新任务信息
```typescript
// 请求
interface UpdateTaskRequest {
  title?: string;
  description?: string;
  status: "pending" | "in_progress" | "completed" | "cancelled"| "deleted";
  priority?: "low" | "medium" | "high";
  due_date?: string;
  planned_start_time?: string;
  planned_end_time?: string;
  estimated_pomodoros?: number;
  tags?: string[];
}

// 响应
interface UpdateTaskResponse {
  task: Task;                     // 更新后的任务信息
}
```

##### 5. DELETE /tasks/{id}
**用途**: 删除任务(软删除)
```typescript
// 响应
interface DeleteTaskResponse {
  success: boolean;
  message: string;
}
```

#### 任务操作 (2个API)

##### 6. POST /tasks/{id}/complete
**用途**: 标记任务完成(自动计算完成度+触发抽奖)

```typescript
// 请求
interface CompleteTaskRequest {
  mood_feedback?: {               // 心情反馈(可选)
    mood: "happy" | "neutral" | "sad" | "anxious";
    comment?: string;
    difficulty: "easy" | "medium" | "hard";
  };
}

// 响应
interface CompleteTaskResponse {
  task: Task;                     // 更新后的任务信息
  lottery_result?: {              // 抽奖结果
    reward_type: "points" | "fragment";
    points_amount?: number;       // 获得积分数
    fragment?: {                  // 获得碎片
      id: string;
      name: string;
      icon: string;
      description: string;
    };
  };
  completion_stats: {             // 完成统计
    completed_subtasks: number;   // 完成的子任务数
    total_subtasks: number;       // 总子任务数
    new_completion_percentage: number;
  };
}
```

##### 7. POST /tasks/{id}/uncomplete
**用途**: 取消任务完成状态
```typescript
// 响应
interface UncompleteTaskResponse {
  task: Task;                     // 更新后的任务信息
  completion_stats: {
    completed_subtasks: number;
    total_subtasks: number;
    new_completion_percentage: number;
  };
}
```

#### 任务搜索与筛选 (2个API)

##### 8. GET /tasks/search
**用途**: 全文搜索任务
```typescript
// 请求参数
interface TaskSearchQuery {
  q: string;                      // 搜索关键词
  page?: number;                  // 页码
  page_size?: number;             // 每页数量
  include_completed?: boolean;    // 是否包含已完成
}

// 响应
interface TaskSearchResponse {
  tasks: Task[];
  pagination: {
    current_page: number;
    total_pages: number;
    total_count: number;
    page_size: number;
  };
  search_highlight: {             // 搜索高亮
    [task_id: string]: {
      title_highlight?: string;
      description_highlight?: string;
    };
  };
}
```

##### 9. GET /tasks/filter
**用途**: 高级筛选任务
```typescript
// 请求参数
interface TaskFilterQuery {
  status?: ("pending" | "in_progress" | "completed" | "cancelled")[];
  priority?: ("low" | "medium" | "high")[];
  tags?: string[];                // 标签列表
  tag_filter_mode?: "and" | "or" | "exclude"; // 标签筛选模式
  due_date_start?: string;        // 截止日期范围开始
  due_date_end?: string;          // 截止日期范围结束
  created_date_start?: string;    // 创建日期范围开始
  created_date_end?: string;      // 创建日期范围结束
  has_parent?: boolean;           // 是否有父任务
  has_children?: boolean;         // 是否有子任务
  completion_percentage_min?: number; // 完成度最小值
  completion_percentage_max?: number; // 完成度最大值
  page?: number;
  page_size?: number;
  sort_by?: "created_at" | "updated_at" | "due_date" | "priority" | "completion_percentage";
  sort_order?: "asc" | "desc";
}

// 响应
interface TaskFilterResponse {
  tasks: Task[];
  pagination: object;
  filter_summary: {
    applied_filters: object;
    total_filtered: number;
  };
}
```

#### Top3管理 (3个API)

##### 10. POST /tasks/top3
**用途**: 设定每日Top3任务
```typescript
// 请求
interface SetTop3Request {
  date: string;                   // 日期(YYYY-MM-DD)
  task_ids: string[];             // 任务ID列表(最多3个)
}

// 响应
interface SetTop3Response {
  date: string;
  top3_tasks: Array<{
    position: number;             // 位置(1/2/3)
    task: Task;
  }>;
  points_consumed: number;        // 消耗积分数(300)
}
```

##### 11. PUT /tasks/top3/{date}
**用途**: 修改指定日期的Top3任务

```typescript
// 请求
interface UpdateTop3Request {
  task_ids: string[];             // 任务ID列表(最多3个)
}

// 响应
interface UpdateTop3Response {
  date: string;
  top3_tasks: Array<{
    position: number;
    task: Task;
    completion_status: "completed" | "pending" | "overdue";
  }>;
  updated_at: string;
}
```



##### 12. GET /tasks/top3/{date}

**用途**: 查看指定日期的Top3任务

```typescript
// 响应
interface UpdateTop3Response {
  date: string;
  top3_tasks: Array<{
    position: number;
    task: Task;
    completion_status: "completed" | "pending" | "overdue";
  }>;
  updated_at: string;
}
```

---

## 🎯 番茄钟系统 (8个API)

### 核心设计
- **标准循环**: 25分钟专注 + 5分钟休息
- **强制任务关联**: 专注会话必须绑定具体任务
- **灵活管理**: 支持暂停、恢复、完成等操作
- **统计记录**: 记录专注数据和任务关联
- **心情反馈**: 专注完成后支持心情反馈

### 数据模型
```typescript
interface FocusSession {
  id: string;
  user_id: string;
  task_id?: string;               // 关联任务ID(可选)
  session_type: "focus" | "break" | "long_break";
  planned_duration: number;       // 计划时长(分钟)
  actual_duration: number;        // 实际时长(分钟)
  status: "pending" | "in_progress" | "completed" | "paused" | "abandoned";
  start_time: string;
  end_time?: string;
  pause_duration?: number;        // 暂停总时长(秒)
  interruptions_count: number;    // 干扰次数
  notes?: string;                 // 备注（完成时选填）
  satisfaction?: "very_satisfied" | "satisfied" | "neutral" | "dissatisfied" | "very_dissatisfied";              // 用户完成满意度（完成时选填）
  created_at: string;
}
```

### API详情

#### 专注会话管理 (5个API)

##### 1. POST /focus/sessions
**用途**: 开始专注会话
```typescript
// 请求
interface CreateFocusSessionRequest {
  task_id?: string;               // 关联任务ID(可选)
  session_type?: "focus" | "break" | "long_break"; // 会话类型
  planned_duration?: number;      // 计划时长(分钟，默认25/5/15)
}

// 响应
interface CreateFocusSessionResponse {
  session: FocusSession;
  current_time: string;           // 当前服务器时间
}
```

##### 2. GET /focus/sessions/{id}
**用途**: 获取会话详情
```typescript
// 响应
interface GetFocusSessionResponse {
  session: FocusSession;
  current_time: string;
  remaining_seconds?: number;     // 剩余秒数(进行中)
}
```

##### 3. PUT /focus/sessions/{id}/pause
**用途**: 暂停专注会话
```typescript
// 响应
interface PauseFocusSessionResponse {
  session: FocusSession;
  pause_time: string;
  remaining_seconds: number;
}
```

##### 4. PUT /focus/sessions/{id}/resume
**用途**: 恢复专注会话
```typescript
// 响应
interface ResumeFocusSessionResponse {
  session: FocusSession;
  resume_time: string;
  remaining_seconds: number;
}
```

##### 5. POST /focus/sessions/{id}/complete
**用途**: 完成专注会话
```typescript
// 请求
interface CompleteFocusSessionRequest {
  notes?: string;                 // 备注
  satisfaction?: "very_satisfied" | "satisfied" | "neutral" | "dissatisfied" | "very_dissatisfied";
}

// 响应
interface CompleteFocusSessionResponse {
  session: FocusSession;
  task_update?: {                 // 关联任务更新
    task_id: string;
    actual_pomodoros: number;     // 实际番茄数
    completion_percentage: number; // 完成百分比
  };
  rewards?: {                     // 完成奖励
    points_earned: number;        // 获得积分
    bonus_fragments?: Array<{     // 额外碎片奖励
      fragment_id: string;
      fragment_name: string;
    }>;
  };
  streak_info?: {                 // 连续专注信息
    current_streak: number;       // 当前连续天数
    best_streak: number;          // 最佳连续天数
  };
}
```

#### 专注记录与统计 (3个API)

##### 6. GET /focus/sessions
**用途**: 获取用户专注记录
```typescript
// 请求参数
interface FocusSessionsQuery {
  page?: number;
  page_size?: number;
  date_from?: string;             // 开始日期
  date_to?: string;               // 结束日期
  session_type?: "focus" | "break" | "long_break";
  status?: ("pending" | "in_progress" | "completed" | "paused" | "abandoned")[];
  task_id?: string;               // 关联任务ID
  sort_by?: "created_at" | "start_time" | "actual_duration";
  sort_order?: "asc" | "desc";
}

// 响应
interface FocusSessionsResponse {
  sessions: FocusSession[];
  pagination: object;
  statistics: {
    total_sessions: number;
    total_focus_time: number;     // 总专注时间(分钟)
    average_session_duration: number;
    completion_rate: number;
  };
}
```

##### 7. GET /focus/statistics
**用途**: 获取专注统计数据
```typescript
// 请求参数
interface FocusStatisticsQuery {
  period: "daily" | "weekly" | "monthly";
  date_from?: string;             // 开始日期
  date_to?: string;               // 结束日期
}

// 响应
interface FocusStatisticsResponse {
  period: string;
  data: Array<{
    date: string;                 // 日期
    total_sessions: number;       // 总会话数
    focus_sessions: number;       // 专注会话数
    total_focus_minutes: number;  // 总专注分钟数
    completion_rate: number;      // 完成率
    interruptions_count: number;  // 干扰次数
  }>;
  summary: {
    total_focus_hours: number;    // 总专注小时数
    daily_average: number;        // 日均专注时间
    best_day: {                   // 最佳表现日
      date: string;
      focus_minutes: number;
      sessions_count: number;
    };
  };
}
```

##### 8. GET /focus/tasks/{taskId}/sessions
**用途**: 获取特定任务的专注记录
```typescript
// 请求参数
interface TaskFocusSessionsQuery {
  page?: number;
  page_size?: number;
  session_type?: "focus" | "break" | "long_break";
}

// 响应
interface TaskFocusSessionsResponse {
  task_id: string;
  task_title: string;
  sessions: FocusSession[];
  pagination: object;
  task_statistics: {
    total_focus_sessions: number;
    total_focus_minutes: number;
    average_session_duration: number;
    estimated_vs_actual: {        // 预计vs实际
      estimated_pomodoros: number;
      actual_pomodoros: number;
    };
  };
}
```

---

## 🏆 奖励系统 (8个API)

### 核心设计
- **即时抽奖**: 任务完成立即触发抽奖，集成到任务完成API中
- **碎片收集**: 简化碎片管理，支持精确碎片收集状态查询
- **灵活兑换**: 支持碎片兑换奖品和积分直接兑换
- **积分系统**: 完整的积分管理和购买流程
- **支付优化**: 统一的支付流程和状态管理

### 数据模型
```typescript
interface Reward {
  id: string;
  name: string;                  // 奖励名称
  description: string;           // 奖励描述
  icon: string;                  // 图标URL
  points_value?: number;         // 积分价值
  amount_to_collect?: number;    // 所需碎片数
  is_redeemed: boolean;          // 是否兑换
}

interface UserFragment {
  id: string;
  user_id: string;
  reward_id: string;
  obtained_at: string;           // 获得时间
}

interface LotteryRecord {
  id: string;
  user_id: string;
  task_id: string;               // 关联任务ID
  reward_type: "points" | "fragment";
  points_amount?: number;        // 获得积分数
  fragment_id?: string;          // 获得碎片ID
  fragment_name?: string;        // 碎片名称
  mood_feedback?: {              // 心情反馈
    mood: string;
    comment?: string;
    difficulty: string;
  };
  created_at: string;
}

interface RedemptionRecord {
  id: string;
  user_id: string;
  type: "fragment_to_points" | "fragment_to_reward";
  fragment_id?: [string];          // 兑换的碎片ID列表（如果是碎片兑换奖品）
  reward_id?: string;            // 兑换的奖品ID
  points_gained?: number;        // 获得积分数
  created_at: string;
}

interface UserPoints {
  user_id: string;
  current_balance: number;       // 当前余额
  total_earned: number;          // 总获得
  total_spent: number;           // 总消费
  last_earned_at: string;        // 最后获得时间
  last_spent_at: string;         // 最后消费时间
}

interface PointsTransaction {
  id: string;
  user_id: string;
  type: "earn" | "spend";
  amount: number;
  source: string;                // 来源(task_complete / purchase / redemption)
  description: string;           // 描述
  created_at: string;
}
```

### API详情

#### 奖品管理 (3个API)

##### 1. GET /rewards/catalog
**用途**: 获取可兑换奖品目录

```typescript
// 响应
interface RewardsCatalogResponse {
  categories: Array<{
    category_name: string;
    rewards: Reward[];
  }>;
}
```

##### 2. GET /rewards/collection
**用途**: 获取用户碎片收集状态
```typescript
// 响应
interface RewardsCollectionResponse {
  fragments: Reward[]
  collection_summary: {
    total_fragment_types: number; // 总碎片种类数
    completed_collections: number;// 已完成的收集
    in_progress_collections: number; // 进行中的收集
    completion_rate: number;      // 完成率
    total_points_value: number;   // 碎片总积分价值
  };
}
```

##### 3. POST /rewards/redeem
**用途**: 兑换奖品
```typescript
// 请求
interface RedeemRewardRequest {
  reward_id: string[];              // 奖品ID列表
  redemption_type: "fragment_to_reward" | "fragment_to_points";
}

// 响应
interface RedeemRewardResponse {
  redemption: RedemptionRecord;
  messages: string[];              // 兑换结果提示信息
}
```

#### 积分系统 (5个API)

##### 4. GET /points/balance
**用途**: 获取用户积分余额
```typescript
// 响应
interface PointsBalanceResponse {
  current_balance: number;
  points_info: {
    total_earned: number;
    total_spent: number;
    net_change_today: number;     // 今日净变化
    net_change_week: number;      // 本周净变化
    net_change_month: number;     // 本月净变化
  };
}
```

##### 5. GET /points/transactions
**用途**: 获取积分变动记录
```typescript
// 请求参数
interface PointsTransactionsQuery {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  type?: "earn" | "spend";
  source?: string;
}

// 响应
interface PointsTransactionsResponse {
  transactions: PointsTransaction[];
  pagination: object;
  summary: {
    total_earned: number;
    total_spent: number;
    net_change: number;
    transaction_count: number;
  };
}
```

##### 6. GET /points/packages
**用途**: 获取积分套餐列表
```typescript
// 响应
interface PointsPackagesResponse {
  packages: Array<{
    id: string;
    name: string;                 // 套餐名称
    description: string;
    points_amount: number;        // 积分数量
    price: number;                // 价格
    currency: string;             // 计价货币
    bonus_points?: number;        // 赠送积分
    discount_percentage?: number; // 折扣百分比
    valid_until?: string;         // 有效期至
  }>;
}
```

##### 7. POST /points/purchase
**用途**: 购买积分(生成支付二维码)
```typescript
// 请求
interface PurchasePointsRequest {
  package_id: string;            // 套餐ID
}

// 响应
interface PurchasePointsResponse {
  order_info: {
    order_id: string;
    package_name: string;
    points_amount: number;
    price: number;                // 价格(元)
    currency: string;
  };
  payment_info: {
    qrcode_url: string;           // 支付二维码URL
    qrcode_base64?: string;       // 二维码Base64(可选)
    expires_at: string;           // 二维码过期时间
    payment_methods: string[];    // 支持的支付方式
  };
  order_status: "pending" | "paid" | "expired";
}
```

##### 8. GET /points/purchase/{id}
**用途**: 查询支付详情和结果
```typescript
// 响应
interface PurchaseDetailsResponse {
  order_info: {
    order_id: string;
    package_name: string;
    points_amount: number;
    price: number;
    currency: string;
    created_at: string;
    paid_at?: string;
    expires_at: string;
  };
  order_status: "pending" | "paid" | "failed" | "expired";
  payment_details?: {             // 支付成功时返回
    payment_method: string;
    paid_amount: number;
    transaction_id: string;
    paid_at: string;
  };
}
```

---

## 📊 统计系统 (5个API)

### 核心设计
- **多维度统计**: 任务、专注多维度分析
- **趋势分析**: 日/周/月趋势对比
- **综合仪表板**: 提供一站式数据概览
- **性能优化**: 合并相关统计查询，提升性能
- **可视化支持**: 为图表提供完整数据结构

### API详情

#### 任务统计 (1个API)

##### 1. GET /statistics/tasks
**用途**: 任务完成统计(按时间分组)
```typescript
// 请求参数
interface TaskStatisticsQuery {
  period: "daily" | "weekly" | "monthly";
  date_from?: string;
  date_to?: string;
  group_by?: "status" | "priority" | "tags";
}

// 响应
interface TaskStatisticsResponse {
  period: string;
  data: Array<{
    date: string;
    total_tasks: number;
    completed_tasks: number;
    pending_tasks: number;
    cancelled_tasks: number;
    completion_rate: number;
    average_completion_time: number; // 平均完成时间(小时)
  }>;
  summary: {
    total_tasks: number;
    completion_rate: number;
    most_productive_day: string;
    productivity_trend: "improving" | "stable" | "declining";
  };
}
```

#### 专注统计 (1个API)

##### 2. GET /statistics/focus
**用途**: 专注统计(趋势+分布+时长)
```typescript
// 请求参数
interface FocusStatisticsQuery {
  period: "daily" | "weekly" | "monthly";
  date_from?: string;
  date_to?: string;
}

// 响应
interface FocusStatisticsResponse {
  trends: Array<{
    date: string;
    total_minutes: number;
    session_count: number;
    average_quality: number;
    completion_rate: number;
    interruptions_count: number;
  }>;
  distribution: {
    hourly_distribution: Array<{
      hour: number;                 // 小时(0-23)
      focus_minutes: number;
      session_count: number;
      efficiency_score: number;
    }>;
    daily_distribution: Array<{
      day_of_week: string;          // 星期几
      total_minutes: number;
      average_quality: number;
      peak_hours: number[];
    }>;
    quality_distribution: {
      "excellent": number;
      "good": number;
      "average": number;
      "poor": number;
    };
  };
  summary: {
    total_focus_hours: number;    // 总专注小时数
    daily_average: number;        // 日均专注时间
    best_day: {                   // 最佳表现日
      date: string;
      focus_minutes: number;
      sessions_count: number;
    };
    trend: "improving" | "stable" | "declining"; // 趋势
    best_focus_time: string;      // 最佳专注时间段
    average_session_length: number;
    focus_efficiency: number;
    interruption_frequency: number;
  };
}
```

#### 综合统计 (1个API)

##### 3. GET /statistics/dashboard
**用途**: 综合仪表板数据
```typescript
// 响应
interface DashboardResponse {
  overview: {
    productivity_score: number;
    tasks_completed_today: number;
    focus_time_today: number;
    current_streak: number;
    points_earned_today: number;
  };
  quick_stats: {
    weekly_completion_rate: number;
    average_focus_quality: number;
    total_active_tasks: number;
    upcoming_deadlines: number;
  };
  recent_activities: Array<{
    type: "task_completed" | "focus_session" | "reward_earned";
    description: string;
    timestamp: string;
    points?: number;
  }>;
  goals_progress: Array<{
    goal_type: string;
    target: number;
    current: number;
    unit: string;
    deadline: string;
  }>;
  insights: Array<{
    title: string;
    content: string;
    type: "achievement" | "suggestion" | "warning";
    priority: "high" | "medium" | "low";
  }>;
}
```

---

## 👤 用户系统 (4个API)

### 核心设计
- **简洁用户信息**: 基本用户信息管理
- **头像管理**: 支持头像上传和更新
- **反馈机制**: 收集用户反馈和建议
- **设置集成**: 用户设置集成到基本信息API中
- **精简API**: 合并相关功能，减少API数量

### 数据模型
```typescript
interface User {
  id: string;
  nickname: string;               // 昵称
  avatar?: string;                // 头像URL
  phone?: string;                 // 手机号
  email?: string;                 // 邮箱
  wechat_openid?: string;         // 微信OpenID
  is_guest: boolean;              // 游客标识
  created_at: string;
  last_login_at: string;
  settings: UserSettings;
}

interface UserSettings {
  focus_duration: number;         // 专注时长(分钟)
  break_duration: number;         // 休息时长(分钟)
  long_break_duration: number;    // 长休息时长(分钟)
  auto_start_breaks: boolean;     // 自动开始休息
  auto_start_focus: boolean;      // 自动开始专注
  notification_enabled: boolean;  // 通知开关
  sound_enabled: boolean;         // 声音开关
  theme: "light" | "dark" | "auto";
  language: string;
  timezone: string;
}

interface UserFeedback {
  id: string;
  user_id: string;
  type: "bug_report" | "feature_request" | "general_feedback" | "complaint";
  title: string;
  content: string;
  contact_info?: string;          // 联系方式
  attachments?: string[];         // 附件URLs
  status: "pending" | "processing" | "resolved" | "closed";
  created_at: string;
  updated_at: string;
}
```

### API详情

##### 1. GET /user/profile
**用途**: 获取用户基本信息
```typescript
// 响应
interface UserProfileResponse {
  user: User;
}
```

##### 2. PUT /user/profile
**用途**: 更新用户信息
```typescript
// 请求
interface UpdateProfileRequest {
  nickname?: string;
  phone?: string;
  email?: string;
  settings?: Partial<UserSettings>;
}

// 响应
interface UpdateProfileResponse {
  user: User;
  updated_fields: string[];
}
```

##### 3. POST /user/avatar
**用途**: 上传用户头像
```typescript
// 请求 (multipart/form-data)
interface UploadAvatarRequest {
  avatar: File;                   // 图片文件
}

// 响应
interface UploadAvatarResponse {
  avatar_url: string;
  thumbnail_url?: string;
  file_info: {
    size: number;
    format: string;
    dimensions?: { width: number; height: number };
  };
}
```

##### 4. POST /user/feedback
**用途**: 提交用户反馈
```typescript
// 请求
interface FeedbackRequest {
  type: "bug_report" | "feature_request" | "general_feedback" | "complaint";
  title: string;
  content: string;
  contact_info?: string;          // 联系方式
  attachments?: string[];         // 附件URLs
  device_info?: {                 // 设备信息
    platform: string;
    version: string;
    model?: string;
  };
}

// 响应
interface FeedbackResponse {
  feedback_id: string;
  status: "pending";
  estimated_response_time: string; // 预计回复时间
  auto_reply?: string;            // 自动回复
}
```


---

## 🎯 API架构总览

### 关键设计特点

#### 1. 游客模式支持
- `POST /auth/guest/init` - 零门槛体验
- `POST /auth/guest/upgrade` - 无缝数据迁移
- 支持手机、邮箱、微信三种升级方式
- `POST /auth/sms/send` - 短信验证码支持
- `POST /auth/logout` - 完整登出流程

#### 2. Session管理系统
- `POST /chat/sessions` - 创建独立会话
- `POST /chat/sessions/{session_id}/send` - 会话消息管理
- `GET /chat/sessions/{session_id}/history` - 会话历史查询
- `GET /chat/sessions` - 会话列表管理

#### 3. 任务树结构
- 无限层级，支持复杂任务分解
- 实时完成度计算(基于叶子节点)
- 集成任务完成奖励机制
- Top3任务管理，支持修改操作

#### 4. 强制任务关联
- 专注会话必须绑定具体任务
- 任务完成集成心情反馈和抽奖
- 专注统计与任务关联分析

#### 5. 优化奖励机制
- 任务完成立即触发抽奖(集成到API中)
- 简化碎片管理，精确状态查询
- 统一支付流程，优化用户体验
- 积分系统完整，支持购买和消费记录

---

## 🔧 技术实施指南

### 开发环境要求
- **Python**: 3.11+
- **框架**: FastAPI
- **数据库**: PostgreSQL + Redis
- **文档**: OpenAPI 3.1.0 + Redoc
- **测试**: pytest + coverage

### 项目结构建议
```
tatake_backend/
├── src/
│   ├── api/                     # API路由
│   │   ├── auth.py             # 认证相关
│   │   ├── chat.py             # AI对话
│   │   ├── tasks.py            # 任务管理
│   │   ├── focus.py            # 番茄钟
│   │   ├── rewards.py          # 奖励系统
│   │   ├── statistics.py       # 统计分析
│   │   └── user.py             # 用户管理
│   ├── core/                   # 核心功能
│   │   ├── auth.py             # 认证逻辑
│   │   ├── database.py         # 数据库配置
│   │   ├── security.py         # 安全相关
│   │   └── utils.py            # 工具函数
│   ├── models/                 # 数据模型
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── focus.py
│   │   └── reward.py
│   ├── schemas/                # Pydantic模式
│   ├── services/               # 业务逻辑
│   └── tests/                  # 测试代码
```

### 开发优先级

#### 第一阶段：核心业务闭环 (14个API)
**目标**: 实现完整的任务管理→专注→完成→奖励循环

1. **认证核心** (5个API)
   - POST /auth/guest/init (游客初始化)
   - POST /auth/guest/upgrade (游客升级)
   - POST /auth/login (用户登录)
   - POST /auth/refresh (刷新令牌)
   - POST /auth/logout (用户登出)

2. **任务核心闭环** (5个API)
   - POST /tasks/{id}/complete (任务完成+心情反馈+抽奖)
   - POST /tasks/{id}/uncomplete (取消完成)
   - POST /tasks/top3 (设置Top3+积分检查)
   - PUT /tasks/top3/{date} (修改Top3)
   - GET /tasks/{id} (任务详情)

3. **奖励核心功能** (4个API)
   - GET /rewards/catalog (奖品目录)
   - GET /rewards/collection (碎片收集状态)
   - POST /rewards/redeem (兑换奖品)
   - GET /points/balance (积分余额)

#### 第二阶段：功能增强 (15个API)
**目标**: 完善搜索筛选、专注管理和会话管理

1. **AI对话系统** (4个API)
   - POST /chat/sessions (创建会话)
   - POST /chat/sessions/{session_id}/send (发送消息)
   - GET /chat/sessions/{session_id}/history (会话历史)
   - GET /chat/sessions (会话列表)

2. **任务基础管理** (4个API)
   - POST /tasks (创建任务)
   - PUT /tasks/{id} (更新任务)
   - DELETE /tasks/{id} (删除任务)
   - GET /tasks/tree/{task_id} (获取任务子树)

3. **番茄钟完整管理** (4个API)
   - GET /focus/sessions/{id} (会话详情)
   - PUT /focus/sessions/{id}/pause (暂停)
   - PUT /focus/sessions/{id}/resume (恢复)
   - GET /focus/tasks/{taskId}/sessions (任务专注记录)

4. **任务搜索筛选** (2个API)
   - GET /tasks/search (搜索)
   - GET /tasks/filter (筛选)

5. **用户功能** (1个API)
   - POST /user/avatar (上传头像)

#### 第三阶段：完整体验 (17个API)
**目标**: 提供完整的统计、支付和高级功能

1. **统计系统** (5个API)
   - GET /statistics/dashboard (综合仪表板)
   - GET /statistics/tasks (任务统计)
   - GET /statistics/completion-rate (完成率)
   - GET /statistics/productivity (生产力)
   - GET /statistics/focus (专注统计)

2. **积分系统完善** (3个API)
   - GET /points/transactions (积分记录)
   - POST /points/purchase (购买积分)
   - POST /auth/sms/send (短信验证码)

3. **用户体验完善** (3个API)
   - GET /focus/sessions (专注记录)
   - GET /user/profile (用户信息)
   - POST /user/feedback (用户反馈)

4. **其他功能** (3个API)
   - GET /auth/user-info (获取当前用户信息)
   - PUT /user/profile (更新用户信息)
   - POST /user/avatar (上传头像)

### 数据库设计要点

#### 核心表结构
1. **users** - 用户基本信息
2. **tasks** - 任务信息(支持树结构)
3. **focus_sessions** - 专注会话记录
4. **rewards** - 奖励配置
5. **user_fragments** - 用户碎片收集
6. **lottery_records** - 抽奖记录
7. **points_transactions** - 积分流水
8. **user_settings** - 用户设置

#### 索引策略
- `tasks(user_id, parent_id)` - 任务树查询优化
- `focus_sessions(user_id, start_time)` - 专注记录查询
- `lottery_records(user_id, created_at)` - 抽奖历史查询
- `user_fragments(user_id, reward_id)` - 碎片收集查询

### 安全考虑

#### 认证安全
- JWT Token有效时间：15分钟
- RefreshToken有效时间：7天
- 密码加密：bcrypt
- API限流：基于用户和IP

#### 数据安全
- 敏感信息加密存储
- SQL注入防护
- XSS防护
- CSRF防护

### 性能优化

#### 数据库优化
- 读写分离
- 连接池管理
- 查询优化
- 索引优化

#### 缓存策略
- Redis缓存用户会话
- 任务树结构缓存
- 统计数据缓存
- 奖励配置缓存

### 监控和日志

#### 日志记录
- 结构化日志格式
- 请求/响应日志
- 错误日志详情
- 性能监控日志

#### 监控指标
- API响应时间
- 数据库查询性能
- 用户活跃度
- 系统资源使用

---

## 🔄 版本管理

### API版本控制
- URL路径版本：`/api/v1/`
- 向后兼容性保证
- 废弃API通知机制

### 数据库版本管理
- Alembic数据库迁移
- 版本号与代码同步
- 回滚策略

---

**文档版本**: v3.1
**更新日期**: 2025-10-13 22:58 (北京时间)
**设计理念**: 精简而不简单，专注核心价值
**适用场景**: 技术实施指南，API开发参考