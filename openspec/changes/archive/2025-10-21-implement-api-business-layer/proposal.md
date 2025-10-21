# implement-api-business-layer 变更提案

## Why

**业务需求驱动**：
TaKeKe应用已完成第一阶段的基础架构搭建，但缺乏核心业务功能的实现。用户无法使用任务管理、专注计时、奖励系统等核心功能，应用无法提供实际价值。必须实现完整的业务逻辑才能支撑用户日常使用。

**技术债务清理**：
当前Service层存在大量TODO项和占位符实现，Redis依赖增加部署复杂度，缺乏真实的JWT认证实现。需要重构架构以提高代码质量、可维护性和可扩展性。

**架构演进需要**：
随着业务复杂度增加，传统的单体架构已无法满足需求。需要引入领域驱动设计(DDD)思想，实现模块化架构，为后续功能扩展奠定基础。同时需要分离认证数据库和业务数据库，提高系统安全性和性能。

## What Changes

**核心变更**：
1. **实现46个API端点的完整业务逻辑** - 涵盖认证、任务、专注、奖励、AI对话、统计、用户管理7大模块
2. **重构认证架构为DDD模式** - 创建独立的认证领域模块，作为其他模块的模板
3. **数据库分离策略** - 将认证数据库与业务数据库分离，提高安全性和性能
4. **移除Redis依赖** - 用SQLite替代Redis存储，降低部署复杂度
5. **集成LangGraph AI对话系统** - 实现智能任务管理和长期记忆功能

**技术架构变更**：
- 创建`src/domains/auth/`独立领域模块
- 新增`tatake_auth.db`认证数据库
- 实现真实的JWT令牌管理和黑名单机制
- 补全Service层的所有业务逻辑实现
- 创建MockSMS服务用于测试和开发
- 优化数据库表结构支持新功能

**分批次实施**：
- 批次1：认证领域模块重构（已完成）
- 批次2：任务管理核心（20个API）
- 批次3：AI对话和增强功能（15个API）

## 概述

基于TaKeKe项目第一阶段的API层基础架构完成情况，第二阶段将完成剩下全部的API业务功能实现，包括46个API端点的完整业务逻辑、Service层补充实现、LangGraph AI对话集成以及数据库长期记忆系统。采用分批次实施策略，确保完全覆盖所有功能模块。

**重要架构调整**: 本阶段将引入**领域驱动设计(DDD)**思想，首先将认证相关代码重构为独立的领域模块(`src/domains/auth/`)，作为后续其他模块的模板。同时实施**数据库分离策略**，将认证数据库(`tatake_auth.db`)与业务数据库(`tatake.db`)分开管理。

## 背景

### 第一阶段完成情况

第一阶段已完成API层基础架构搭建，包括：

✅ **已完成的架构组件**：
- FastAPI应用基础结构（main.py, config.py）
- 统一响应格式和错误处理（responses.py）
- 完整的中间件系统（认证、日志、CORS、限流、安全）
- ServiceFactory依赖注入系统
- OpenAPI文档配置
- Pydantic数据模型基础框架
- **100%的测试覆盖**（33/33基础架构测试通过）

### Service层当前状态

根据详细分析，各Service模块的完成度：
- **AuthService**: 85%完成，主要缺JWT真实实现和Redis移除适配
- **TaskService**: 70%完成，缺任务完成逻辑和Top3管理
- **FocusService**: 65%完成，缺会话状态管理
- **RewardService**: 60%完成，缺核心兑换逻辑
- **StatisticsService**: 80%完成，基本可用
- **ChatService**: 40%完成，需要LangGraph重构和数据库记忆系统
- **UserService**: 55%完成，缺积分操作

## 变更范围

### 核心目标

完成所有46个API端点的业务实现，包括：

1. **认证系统**（7个API）- JWT真实实现 + 游客升级 + 短信验证
2. **任务管理**（12个API）- 完整CRUD + Top3管理 + 搜索筛选
3. **番茄钟系统**（8个API）- 会话管理 + 统计记录 + 奖励关联
4. **奖励系统**（8个API）- 碎片收集 + 积分管理 + 奖品兑换
5. **AI对话系统**（4个API）- LangGraph集成 + 任务工具 + 数据库记忆
6. **统计分析**（3个API）- 仪表板 + 趋势分析
7. **用户管理**（4个API）- 资料管理 + 头像上传 + 反馈系统

### 技术架构决策

#### 1. **领域驱动设计(DDD)引入** 🆕
- **建立独立认证领域** (`src/domains/auth/`)
  - 包含完整的router、service、repository、models、database
  - 自包含的README文档说明架构和使用方法
  - 作为其他领域模块的标准模板
- **领域边界清晰**
  - 认证领域：用户身份、JWT、短信验证
  - 未来任务领域：任务管理、专注会话
  - 未来奖励领域：积分、碎片、兑换
- **渐进式迁移策略**
  - 当前仅重构认证模块到领域层
  - 其他模块保持现状(src/api/routers/*)
  - 后续逐步迁移其他模块

#### 2. **数据库分离策略** 🆕
- **认证数据库** (`tatake_auth.db`)
  - users表(用户基本信息)
  - user_settings表(用户设置)
  - sms_verification表(短信验证码)
  - token_blacklist表(JWT黑名单)
  - user_sessions表(用户会话)
  - auth_logs表(认证审计日志)
- **业务数据库** (`tatake.db`)
  - tasks表及相关任务数据
  - focus_sessions表
  - chat_sessions表
  - rewards表及相关奖励数据
- **跨库关联策略**
  - 使用`user_id`字符串关联(不用外键)
  - 避免跨库事务复杂性
  - Service层保证数据一致性
- **⚠️ 潜在风险与缓解**
  - 风险：数据不一致性(应用层维护关联)
  - 缓解：软删除策略 + 定期一致性检查脚本

#### 3. **Redis移除策略**
- **删除Redis依赖**，改用SQLite存储
- 短信验证码用数据库存储 + 冷却时间逻辑
- JWT黑名单用数据库维护（token_blacklist表）
- 用户会话用JWT本身管理

#### 4. **LangGraph集成方案**
- **使用真实LLM服务**：通过环境变量配置BaseURL和API Key
- **数据库长期记忆**：替换Redis，使用SQLite存储对话历史
- **Supervisor-Agent模式**：主supervisor节点路由到专门agent
- **工具调用集成**：AI通过工具调用操作任务管理功能

#### 5. **分批次实施策略** (已调整)
- **批次1**：认证领域模块重构 + Schema层补全（11个API）- 3周
  - 创建`src/domains/auth/`完整目录结构
  - 补全`src/api/schemas/auth.py`
  - 实施数据库分离
  - 完善测试套件(覆盖率>90%)
- **批次2**：任务管理核心（20个API）- 3-4周
- **批次3**：AI对话和增强功能（15个API）- 4-5周

#### 6. **Mock服务策略** (已优化)
为外部服务创建完全功能的Mock服务：
- `src/services/external/mock_sms_service.py` - 短信服务模拟
  - **控制台彩色输出**验证码(方便测试)
  - 随机生成6位数字验证码
  - 5分钟有效期
  - 频率限制和冷却时间
- `src/services/external/mock_wechat_service.py` - 微信登录模拟
- 完全模拟真实响应，包含详细的替换注释

#### 7. **Pydantic Schema设计**
独立的schema目录结构：
```
src/api/schemas/
├── __init__.py
└── auth.py        # 🆕 认证相关Schema(7个请求+7个响应)
                   # GuestInitRequest/Response
                   # GuestUpgradeRequest/Response
                   # SMSCodeRequest/Response
                   # LoginRequest/Response
                   # TokenRefreshRequest/Response
                   # LogoutRequest/Response
                   # UserInfoResponse
├── tasks/         # 【未来】任务相关模型
├── focus/         # 【未来】专注相关模型
├── rewards/       # 【未来】奖励相关模型
├── chat/          # 【未来】对话相关模型
├── statistics/    # 【未来】统计相关模型
└── user/          # 【未来】用户相关模型
```

#### 8. **模块注册策略** 🆕
- **当前阶段**：仅注册认证API到FastAPI app
  ```python
  # main.py
  app.include_router(auth.router, prefix="/api/v1", tags=["认证系统"])
  # 其他router暂时注释
  # app.include_router(user.router, ...)
  # app.include_router(tasks.router, ...)
  ```
- **后续阶段**：逐步启用其他模块

## 详细实施计划

### 批次1：认证核心模块（3周，11个API）

#### 目标
建立完整的用户认证体系，为所有其他功能提供身份验证基础。

#### 包含功能
**认证系统API（7个）**：
- `POST /auth/guest/init` - 游客账号初始化
- `POST /auth/guest/upgrade` - 游客账号升级
- `POST /auth/sms/send` - 短信验证码发送
- `POST /auth/login` - 用户登录
- `POST /auth/refresh` - 令牌刷新
- `POST /auth/logout` - 用户登出
- `GET /auth/user-info` - 用户信息获取

**用户管理API（4个）**：
- `GET /user/profile` - 获取用户信息
- `PUT /user/profile` - 更新用户信息
- `POST /user/avatar` - 头像上传
- `POST /user/feedback` - 用户反馈

#### Service层补充
- **AuthService补充**：JWT真实实现、数据库验证码存储、令牌黑名单
- **UserService补充**：积分操作逻辑、用户设置管理

#### 技术重点
- JWT + PyJWT集成
- 数据库验证码存储和冷却逻辑
- Mock短信服务集成
- 令牌黑名单数据库管理

### 批次2：任务管理核心（3-4周，20个API）

#### 目标
实现核心的任务管理和专注功能，这是应用的主要价值所在。

#### 包含功能
**任务管理API（12个）**：
- `POST /tasks` - 创建任务
- `GET /tasks/{id}` - 任务详情
- `PUT /tasks/{id}` - 更新任务
- `DELETE /tasks/{id}` - 删除任务
- `POST /tasks/{id}/complete` - 完成任务
- `POST /tasks/{id}/uncomplete` - 取消完成
- `GET /tasks/search` - 任务搜索
- `GET /tasks/filter` - 任务筛选
- `POST /tasks/top3` - 设置Top3任务
- `PUT /tasks/top3/{date}` - 修改Top3任务
- `GET /tasks/top3/{date}` - 查看Top3任务
- `GET /tasks/tree` - 任务树结构

**番茄钟系统API（8个）**：
- `POST /focus/sessions` - 开始专注会话
- `GET /focus/sessions/{id}` - 会话详情
- `PUT /focus/sessions/{id}/pause` - 暂停会话
- `PUT /focus/sessions/{id}/resume` - 恢复会话
- `POST /focus/sessions/{id}/complete` - 完成会话
- `GET /focus/sessions` - 专注记录
- `GET /focus/statistics` - 专注统计
- `GET /focus/tasks/{id}/sessions` - 任务专注记录

#### Service层补充
- **TaskService补充**：任务完成逻辑、抽奖机制、Top3管理、搜索筛选
- **FocusService补充**：会话状态管理、完成机制、统计记录

#### 技术重点
- 任务树结构的无限层级处理
- 任务完成与奖励系统的集成
- 专注会话的状态机管理
- 任务搜索和筛选的性能优化

### 批次3：AI对话和增强功能（4-5周，15个API）

#### 目标
实现AI对话功能和奖励系统，提供智能化的任务管理和完整的激励机制。

#### 包含功能
**AI对话系统API（4个）**：
- `POST /chat/sessions` - 创建会话
- `POST /chat/sessions/{id}/send` - 发送消息
- `GET /chat/sessions/{id}/history` - 会话历史
- `GET /chat/sessions` - 会话列表

**奖励系统API（8个）**：
- `GET /rewards/catalog` - 奖品目录
- `GET /rewards/collection` - 碎片收集状态
- `POST /rewards/redeem` - 奖品兑换
- `GET /rewards/lottery/chance` - 抽奖机会查询
- `POST /rewards/lottery/draw` - 执行抽奖
- `GET /rewards/history` - 兑换历史
- `GET /rewards/fragments` - 碎片详情
- `POST /rewards/claim` - 领取奖励

**统计分析API（3个）**：
- `GET /statistics/dashboard` - 综合仪表板
- `GET /statistics/tasks` - 任务统计
- `GET /statistics/focus` - 专注统计

#### Service层补充
- **ChatService重构**：LangGraph集成、真实LLM调用、数据库记忆系统
- **RewardService补充**：核心兑换逻辑、抽奖机制、碎片收集
- **StatisticsService优化**：性能优化、数据导出

#### 技术重点
- LangGraph状态机重构
- 真实LLM API集成
- 数据库长期记忆系统
- 任务管理工具集成
- 抽奖算法实现
- 统计数据缓存优化

## 技术要求

### 核心技术栈
- **Web框架**: FastAPI + Uvicorn
- **数据库**: SQLite + SQLAlchemy异步ORM
- **AI框架**: LangGraph + LangChain
- **认证**: PyJWT + 数据库黑名单
- **测试**: Pytest + TDD流程
- **依赖管理**: uv
- **代码质量**: 类型注解 + 统一错误处理

### 外部服务集成
- **LLM服务**: 通过环境变量配置的真实API
- **短信服务**: Mock SMS服务（完全模拟）
- **微信登录**: Mock WeChat服务（完全模拟）
- **文件存储**: 本地文件系统

### 数据库设计
- **移除Redis依赖**
- 新增`token_blacklist`表用于JWT黑名单
- 新增`sms_verification`表用于验证码存储
- 新增`chat_memory`表用于长期对话记忆
- 优化现有表结构以支持新功能

### 性能要求
- **API响应时间**: < 100ms (95%请求)
- **并发支持**: 1000+用户
- **数据库优化**: 索引优化 + 查询优化
- **缓存策略**: SQLite内存缓存 + 应用层缓存

## 验收标准

### 功能验收
- ✅ 所有46个API端点实现完成并测试通过
- ✅ LangGraph AI对话功能正常工作
- ✅ 认证授权系统（JWT + 数据库黑名单）正常工作
- ✅ 任务管理和专注系统功能完整
- ✅ 奖励系统和抽奖机制正常运行
- ✅ 统计分析功能准确有效

### 质量验收
- ✅ API测试覆盖率 > 95%（单元测试、集成测试）
- ✅ Service层业务逻辑测试完整
- ✅ LangGraph对话流程测试通过
- ✅ 性能测试通过（响应时间 < 100ms）
- ✅ 安全测试通过（认证、授权、输入验证）

### 架构验收
- ✅ 代码结构清晰合理，模块化设计
- ✅ ServiceFactory依赖注入正确实现
- ✅ 数据库Schema设计合理
- ✅ LangGraph集成架构清晰
- ✅ Mock服务易于替换为真实服务

### 开发流程验收
- ✅ 每个功能模块遵循TDD流程
- ✅ 每批次完全测试通过后再进行下一批次
- ✅ 代码注释完整，包含文件头和函数文档
- ✅ Git提交规范，开发进度清晰
- ✅ Mock服务替换文档清晰

## 风险评估

### 技术风险
- **中等风险**: LangGraph集成复杂度
  - 缓解策略：分阶段实现，先基础对话后工具集成
- **低风险**: Service层业务逻辑补充
  - 缓解策略：基于现有架构逐步完善
- **低风险**: 数据库Schema变更
  - 缓解策略：使用Alembic进行数据库迁移

### 进度风险
- **中等风险**: 批次3工作量较大（AI对话 + 奖励系统）
  - 缓解策略：并行开发，提前准备Mock服务
- **低风险**: 外部服务集成
  - 缓解策略：使用完全功能的Mock服务占位

### 质量风险
- **低风险**: LangGraph测试覆盖
  - 缓解策略：详细的单元测试和集成测试
- **低风险**: 性能优化
  - 缓解策略：分批次性能测试和优化

## 关键技术决策总结

1. **分批次实施**: 3个批次，循序渐进确保质量
2. **Redis移除**: 全面改用SQLite存储，降低部署复杂度
3. **LangGraph集成**: 真实LLM + 数据库长期记忆
4. **Mock服务策略**: 完全功能模拟，便于后续替换
5. **Service层同步**: API实现与Service业务逻辑同步完善
6. **TDD流程**: 严格的测试驱动开发，确保代码质量

## 后续计划

### 完成后可以继续：
- 前端集成开发（React/Vue小程序）
- 性能监控和优化（APM集成）
- 真实外部服务集成（SMS、微信、支付）
- 高级AI功能（多模态、个性化推荐）
- 生产环境部署和运维

### 当前状态
- ✅ 基础架构已完成（FastAPI、中间件、数据模型）
- ✅ Service层架构清晰，需要业务逻辑补充
- ✅ 分批次实施计划已制定
- ✅ **批次1已完成**：认证核心模块完整实现（DDD架构、数据库分离、完整测试套件）
- 🔄 准备开始批次2：任务管理核心实现

---

**更新日期**: 2025-10-21
**创建人**: AI Assistant
**预计完成时间**: 10-12周
**当前阶段**: 批次2 - 任务管理核心实现准备
**优先级**: 高
**开发方式**: 分批次实施 + TDD + Git版本管理 + 严格质量标准
**批次1状态**: ✅ 已完成（认证领域模块重构、7个阶段全部完成）