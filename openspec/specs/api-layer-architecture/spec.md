# api-layer-architecture Specification

## Purpose
基于TaKeKe API设计文档，实现完整的RESTful API层，作为服务层和前端之间的接口层，提供43个API端点，涵盖认证、AI对话、任务管理、番茄钟、奖励系统、统计分析和用户管理等7个核心模块。
## Requirements
### Requirement: API Layer Foundation
系统 SHALL实现完整的API层基础架构，作为服务层和前端之间的桥梁。

#### Scenario: FastAPI Application Structure
- **GIVEN** 需要创建FastAPI应用基础结构
- **WHEN** 设置API层时
- **THEN** 系统 SHALL提供以下文件结构：
  ```
  src/api/
  ├── __init__.py
  ├── main.py                  # FastAPI主应用文件
  ├── config.py                # 应用配置
  ├── dependencies.py          # 依赖注入
  ├── middleware/              # 中间件目录
  │   ├── __init__.py
  │   ├── auth.py             # 认证中间件
  │   ├── logging.py          # 日志中间件
  │   ├── cors.py             # CORS中间件
  │   ├── rate_limit.py       # 限流中间件
  │   └── exception_handler.py # 异常处理中间件
  └── responses.py             # 统一响应格式
  ```

#### Scenario: API Versioning
- **GIVEN** 需要支持API版本管理
- **WHEN** 设计API路由时
- **THEN** 系统 SHALL使用 `/api/v1` 作为版本前缀
- **AND** 系统 SHALL支持向后兼容的版本升级

### Requirement: Unified Response Format
系统 SHALL实现统一的API响应格式，确保前端一致性。

#### Scenario: Standard Response Structure
- **GIVEN** 需要统一的响应格式
- **WHEN** 设计API响应时
- **THEN** 系统 SHALL使用以下格式：
  ```json
  {
    "code": 200,
    "message": "操作成功",
    "data": {...},
    "timestamp": "2025-10-20T10:00:00Z",
    "traceId": "trace_123456"
  }
  ```

#### Scenario: Error Response Format
- **GIVEN** 需要统一的错误响应格式
- **WHEN** 处理API错误时
- **THEN** 错误响应 SHALL包含：
  - 错误代码和消息
  - 详细的错误上下文
  - 用户友好的错误描述
  - 调试信息和TraceID

### Requirement: Authentication Module
系统 SHALL实现完整的认证系统API，支持多种认证方式。

#### Scenario: Guest User System
- **GIVEN** 需要降低用户使用门槛
- **WHEN** 实现认证系统时
- **THEN** 系统 SHALL支持游客模式：
  - `POST /auth/guest/init` - 游客账号初始化
  - `POST /auth/guest/upgrade` - 游客账号升级
- **AND** 游客账号 SHALL支持无缝升级到正式账号

#### Scenario: Multi-Method Authentication
- **GIVEN** 需要支持多种认证方式
- **WHEN** 实现登录功能时
- **THEN** 系统 SHALL支持：
  - 手机号 + 短信验证码登录
  - 邮箱 + 验证码登录
  - 微信登录
  - JWT + RefreshToken令牌机制

#### Scenario: SMS Verification
- **GIVEN** 需要短信验证功能
- **WHEN** 实现短信验证时
- **THEN** 系统 SHALL提供：
  - `POST /auth/sms/send` - 发送验证码
  - 验证码生成和验证逻辑
  - 发送频率限制
  - 验证码有效期管理

### Requirement: Task Management API
系统 SHALL实现完整的任务树管理API，支持无限层级任务结构。

#### Scenario: Task CRUD Operations
- **GIVEN** 需要完整的任务管理功能
- **WHEN** 实现任务API时
- **THEN** 系统 SHALL提供：
  - `POST /tasks` - 创建任务
  - `GET /tasks/{id}` - 获取任务详情
  - `PUT /tasks/{id}` - 更新任务
  - `DELETE /tasks/{id}` - 删除任务
- **AND** 任务 SHALL支持无限层级树结构

#### Scenario: Task Completion and Lottery
- **GIVEN** 需要激励用户完成任务
- **WHEN** 实现任务完成时
- **THEN** 系统 SHALL集成：
  - 心情反馈收集
  - 抽奖机制触发
  - 积分奖励发放
  - 完成记录统计

#### Scenario: Task Search and Filter
- **GIVEN** 需要灵活的任务查询功能
- **WHEN** 实现任务搜索时
- **THEN** 系统 SHALL支持：
  - 全文搜索功能
  - 多条件筛选
  - 搜索结果高亮
  - 智能排序

#### Scenario: Top3 Task Management
- **GIVEN** 需要每日重点任务管理
- **WHEN** 实现Top3功能时
- **THEN** 系统 SHALL提供：
  - `POST /tasks/top3` - 设置Top3任务
  - `PUT /tasks/top3/{date}` - 修改Top3任务
  - `GET /tasks/top3/{date}` - 查看Top3任务
- **AND** Top3设置 SHALL消耗积分

### Requirement: AI Chat System API
系统 SHALL实现AI对话系统API，专注于纯对话功能，基于LangGraph框架进行状态管理和持久化。

#### Scenario: Chat Session Management
- **GIVEN** 需要管理对话会话
- **WHEN** 实现聊天API时
- **THEN** 系统 SHALL提供：
  - `POST /chat/sessions` - 创建会话
  - `GET /chat/sessions` - 获取会话列表
  - 会话持久化和历史管理
  - 基于LangGraph SQLiteMemory的会话状态管理
  - UUID4会话ID生成策略

#### Scenario: Message Processing
- **GIVEN** 需要处理消息发送和接收
- **WHEN** 实现消息API时
- **THEN** 系统 SHALL支持：
  - `POST /chat/sessions/{id}/send` - 发送消息
  - `GET /chat/sessions/{id}/history` - 获取历史消息
  - LangGraph对话引擎集成
  - 基于JWT认证的用户隔离
  - 工具调用支持（计算器等）

#### Scenario: Chat API File Structure
- **GIVEN** 需要实现聊天API
- **WHEN** 组织API文件时
- **THEN** 系统 SHALL创建：
  - `src/api/chat.py` - 聊天API路由文件
  - 集成到FastAPI主应用的聊天路由
  - 认证中间件集成
  - 统一响应格式应用

#### Scenario: LangGraph Integration
- **GIVEN** 需要集成LangGraph到API层
- **WHEN** 处理聊天请求时
- **THEN** 系统 SHALL：
  - 从JWT token解析user_id
  - 构建LangGraph配置参数
  - 调用聊天服务层处理请求
  - 返回标准化的API响应

#### Scenario: Chat Response Format
- **GIVEN** 需要统一的聊天响应格式
- **WHEN** 设计API响应时
- **THEN** 系统 SHALL使用：
  ```json
  {
    "code": 200,
    "message": "操作成功",
    "data": {
      "session_id": "uuid-123",
      "message_id": "uuid-456",
      "ai_response": {
        "content": "AI回复内容",
        "role": "assistant",
        "tool_calls": []
      }
    },
    "timestamp": "2025-10-21T10:00:00Z"
  }
  ```

#### Scenario: Session History Format
- **GIVEN** 需要标准化的历史记录格式
- **WHEN** 查询会话历史时
- **THEN** 系统 SHALL返回：
  ```json
  {
    "code": 200,
    "message": "查询成功",
    "data": {
      "session_id": "uuid-123",
      "messages": [
        {
          "message_id": "uuid-456",
          "role": "user|assistant|tool",
          "content": "消息内容",
          "timestamp": "2025-10-21T10:00:00Z"
        }
      ],
      "pagination": {
        "current_page": 1,
        "total_pages": 1,
        "total_count": 10
      }
    }
  }
  ```

#### Scenario: Simple Session Listing
- **GIVEN** 需要获取用户会话列表
- **WHEN** 查询会话时
- **THEN** 系统 SHALL通过LangGraph checkpointer遍历
- **AND** 基于user_id过滤用户相关会话
- **AND** 返回基础会话信息（无性能优化要求）

### Requirement: Focus Session API
系统 SHALL实现番茄钟专注会话API，支持完整的专注流程管理。

#### Scenario: Focus Session Lifecycle
- **GIVEN** 需要管理专注会话
- **WHEN** 实现专注API时
- **THEN** 系统 SHALL提供完整的会话生命周期：
  - `POST /focus/sessions` - 开始专注会话
  - `GET /focus/sessions/{id}` - 获取会话详情
  - `PUT /focus/sessions/{id}/pause` - 暂停会话
  - `PUT /focus/sessions/{id}/resume` - 恢复会话
  - `POST /focus/sessions/{id}/complete` - 完成会话

#### Scenario: Task Association Requirement
- **GIVEN** 需要强制关联任务
- **WHEN** 开始专注会话时
- **THEN** 系统 SHALL要求用户选择关联任务
- **AND** 系统 SHALL验证任务的有效性

#### Scenario: Focus Statistics
- **GIVEN** 需要统计专注数据
- **WHEN** 实现统计功能时
- **THEN** 系统 SHALL提供：
  - `GET /focus/statistics` - 专注统计数据
  - `GET /focus/tasks/{id}/sessions` - 任务专注记录
  - 多维度统计分析
  - 趋势分析支持

### Requirement: Reward System API
系统 SHALL实现完整的奖励系统API，包括碎片收集和奖品兑换。

#### Scenario: Fragment Collection
- **GIVEN** 需要管理碎片收集
- **WHEN** 实现奖励API时
- **THEN** 系统 SHALL提供：
  - `GET /rewards/collection` - 碎片收集状态
  - 碎片状态查询
  - 收集进度计算
  - 兑换状态判断

#### Scenario: Prize Redemption
- **GIVEN** 需要支持奖品兑换
- **WHEN** 实现兑换功能时
- **THEN** 系统 SHALL提供：
  - `GET /rewards/catalog` - 奖品目录
  - `POST /rewards/redeem` - 兑换奖品
  - 碎片兑换逻辑
  - 兑换记录管理

#### Scenario: Points System
- **GIVEN** 需要完整的积分系统
- **WHEN** 实现积分API时
- **THEN** 系统 SHALL支持：
  - `GET /points/balance` - 积分余额
  - `GET /points/transactions` - 积分记录
  - `POST /points/purchase` - 购买积分
  - 积分套餐管理

### Requirement: Statistics API
系统 SHALL实现统计分析API，提供多维度的数据分析功能。

#### Scenario: Comprehensive Dashboard
- **GIVEN** 需要综合仪表板
- **WHEN** 实现统计API时
- **THEN** 系统 SHALL提供：
  - `GET /statistics/dashboard` - 综合仪表板
  - 多维度数据聚合
  - 实时数据刷新
  - 智能分析功能

#### Scenario: Task Statistics
- **GIVEN** 需要任务统计分析
- **WHEN** 实现任务统计时
- **THEN** 系统 SHALL支持：
  - `GET /statistics/tasks` - 任务统计
  - 任务完成率分析
  - 时间维度分析
  - 趋势预测

### Requirement: User Management API
系统 SHALL实现用户管理API，支持用户信息和设置管理。

#### Scenario: User Profile Management
- **GIVEN** 需要管理用户信息
- **WHEN** 实现用户API时
- **THEN** 系统 SHALL提供：
  - `GET /user/profile` - 获取用户信息
  - `PUT /user/profile` - 更新用户信息
  - 用户设置管理
  - 隐私数据处理

#### Scenario: Avatar Upload
- **GIVEN** 需要支持头像上传
- **WHEN** 实现文件上传时
- **THEN** 系统 SHALL支持：
  - `POST /user/avatar` - 上传头像
  - 文件格式验证
  - 图片处理和缩略图生成
  - 存储管理

#### Scenario: User Feedback
- **GIVEN** 需要收集用户反馈
- **WHEN** 实现反馈功能时
- **THEN** 系统 SHALL提供：
  - `POST /user/feedback` - 提交反馈
  - 反馈分类处理
  - 附件上传支持
  - 反馈状态跟踪

### Requirement: API Security
系统 SHALL实现完整的API安全机制，保护系统安全。

#### Scenario: JWT Authentication
- **GIVEN** 需要JWT令牌认证
- **WHEN** 实现认证中间件时
- **THEN** 系统 SHALL提供：
  - JWT令牌验证
  - RefreshToken机制
  - 令牌自动刷新
  - 令牌失效处理

#### Scenario: Rate Limiting
- **GIVEN** 需要防止API滥用
- **WHEN** 实现限流中间件时
- **THEN** 系统 SHALL支持：
  - 基于用户的限流
  - 基于IP的限流
  - 分级限流策略
  - 限流状态响应

#### Scenario: Input Validation
- **GIVEN** 需要防止恶意输入
- **WHEN** 实现API验证时
- **THEN** 系统 SHALL提供：
  - Pydantic模型验证
  - SQL注入防护
  - XSS防护
  - CSRF防护

### Requirement: API Documentation
系统 SHALL生成完整的API文档，支持开发者使用。

#### Scenario: OpenAPI Documentation
- **GIVEN** 需要API文档
- **WHEN** 生成文档时
- **THEN** 系统 SHALL提供：
  - OpenAPI 3.1.0规范文档
  - 交互式文档界面
  - API使用示例
  - 文档认证配置

#### Scenario: API Examples
- **GIVEN** 需要帮助开发者理解API
- **WHEN** 编写文档时
- **THEN** 系统 SHALL提供：
  - 详细的请求示例
  - 响应格式示例
  - 错误处理示例
  - 认证示例

### Requirement: Performance Optimization
系统 SHALL优化API性能，确保良好的用户体验。

#### Scenario: Response Time Optimization
- **GIVEN** 需要快速API响应
- **WHEN** 优化API时
- **THEN** 系统 SHALL确保：
  - 95%请求响应时间 < 100ms
  - 异步处理支持
  - 数据库查询优化
  - 缓存策略实现

#### Scenario: Caching Strategy
- **GIVEN** 需要提升API性能
- **WHEN** 实现缓存时
- **THEN** 系统 SHALL支持：
  - Redis缓存热点数据
  - 查询结果缓存
  - 用户会话缓存
  - 统计数据缓存

### Requirement: Testing Coverage
系统 SHALL实现全面的API测试覆盖，确保代码质量。

#### Scenario: Unit Testing
- **GIVEN** 需要API单元测试
- **WHEN** 编写测试时
- **THEN** 系统 SHALL确保：
  - 每个API端点都有测试
  - 测试覆盖率 > 95%
  - Mock依赖隔离
  - 边界条件测试

#### Scenario: Integration Testing
- **GIVEN** 需要API集成测试
- **WHEN** 测试API协作时
- **THEN** 系统 SHALL验证：
  - API与Service层集成
  - 认证流程完整性
  - 错误处理一致性
  - 数据流正确性

## ADDED Requirements

### Requirement: User Route Registration
系统必须正确注册用户系统路由到主应用。

#### Scenario: User Profile Access
- **GIVEN** 用户需要访问个人信息
- **WHEN** 发送GET请求到 `/user/profile`
- **THEN** 系统 SHALL返回用户基本信息而不是404错误
- **Implementation**: 在main.py中导入并注册user路由器

### Requirement: Unified JWT Authentication
系统必须统一所有API的JWT认证机制，从token获取user_id。

#### Scenario: Points API Authentication
- **GIVEN** 用户查询积分余额
- **WHEN** 发送带JWT token的GET请求到 `/points/my-points`
- **THEN** 系统 SHALL从token自动解析user_id，不需要查询参数
- **Implementation**: 统一所有API使用FastAPI依赖注入获取user_id

### Requirement: Focus Single Session Management
系统必须维护单一活跃Focus会话，新会话创建时自动关闭旧会话。

#### Scenario: Focus Session Auto-Close
- **GIVEN** 用户存在未完成的专注会话
- **WHEN** 创建新的专注会话时
- **THEN** 系统 SHALL自动关闭旧会话并创建新会话
- **Implementation**: 修改会话创建逻辑，添加会话状态转换验证

## Notes
该API层设计基于现有的Service Layer架构，通过FastAPI框架实现完整的RESTful API功能。系统采用分层架构，确保API层、Service层和Repository层之间的清晰分离，同时保持高性能和良好的可维护性。