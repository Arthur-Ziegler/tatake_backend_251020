# 设计文档: cleanup-auth-legacy-code

## 架构决策

### 1. DDD领域驱动设计架构

**决策**: 采用DDD领域驱动设计，每个业务领域独立封装

**理由**:
- ✅ **高内聚低耦合**: 每个领域自包含，减少跨模块依赖
- ✅ **独立演进**: 认证领域可以独立升级、测试、部署
- ✅ **清晰边界**: 领域边界明确，职责分离
- ✅ **可扩展性**: 便于后续添加其他领域模块
- ✅ **团队协作**: 不同团队可独立开发不同领域

**领域结构**:
```
src/domains/auth/
├── __init__.py          # 领域公共接口
├── router.py            # FastAPI路由（API层）
├── service.py           # 业务逻辑层
├── repository.py        # 数据访问层
├── models.py            # 数据模型（SQLModel）
├── schemas.py           # 请求/响应Schema（NEW）
├── database.py          # 数据库连接管理
├── exceptions.py        # 领域异常
├── README.md            # 领域文档
└── tests/               # 测试套件
    ├── conftest.py
    ├── test_repository.py
    ├── test_service.py
    ├── test_router.py
    ├── test_security.py
    └── test_integration.py
```

### 2. Schema独立化设计

**决策**: 在认证领域内创建最小化的Schema集合

**原Schema问题**:
- `src/api/schemas/auth.py` 有1177行代码
- 包含97个类定义
- 混合了认证Schema和其他模块的兼容性Schema
- 违反了DDD的领域自包含原则

**新Schema设计**:
```python
# src/domains/auth/schemas.py

# ===== 请求Schema (7个API × 1个请求 = 7个) =====
- GuestInitRequest          # POST /auth/guest/init
- GuestUpgradeRequest       # POST /auth/guest/upgrade
- SMSCodeRequest            # POST /auth/sms/send
- LoginRequest              # POST /auth/login
- TokenRefreshRequest       # POST /auth/refresh
- LogoutRequest             # POST /auth/logout (可选，可用BaseRequest)
# GET /auth/user-info 无请求体

# ===== 响应Schema (统一格式) =====
- BaseResponse              # 基础响应
- ErrorResponse             # 错误响应
- AuthTokenResponse         # 令牌响应（用于init/upgrade/login/refresh）
- UserInfoResponse          # 用户信息响应

# ===== 辅助Schema =====
- DeviceInfo                # 设备信息
- TokenInfo                 # 令牌信息
- UserProfile               # 用户资料
```

**设计原则**:
- ✅ **最小化**: 只包含7个API真正需要的Schema
- ✅ **无冗余**: 不包含其他模块的兼容性代码
- ✅ **自文档化**: 每个Schema都有完整的docstring和字段说明
- ✅ **类型安全**: 使用Pydantic完整验证
- ✅ **可测试**: Schema定义清晰，易于单元测试

### 3. 依赖清理策略

**要删除的依赖** (`src/api/dependencies.py`):
```python
# 删除导入
from src.services.async_auth_service import AsyncAuthService

# 删除工厂方法
async def get_async_auth_service(...)  # 第236-251行
async def get_auth_service(...)        # 第195-216行（如果存在）
```

**保留的依赖**:
```python
# 保留其他服务的依赖（虽然暂时不用）
from src.services import (
    UserService,
    TaskService,
    FocusService,
    RewardService,
    StatisticsService,
    ChatService
)
```

### 4. 数据库架构

**决策**: 使用双数据库架构

**数据库分离**:
```
tatake_auth.db          # 认证领域专用数据库
├── users               # 用户表
├── sms_verifications   # 短信验证码表
├── token_blacklist     # 令牌黑名单表
├── user_sessions       # 用户会话表
└── auth_logs           # 认证日志表

tatake.db               # 业务数据库（未来使用）
├── tasks               # 任务表
├── focus_sessions      # 专注会话表
├── rewards             # 奖励表
├── chat_sessions       # 对话会话表
└── ...
```

**优势**:
- ✅ **领域隔离**: 认证数据独立，不会被业务逻辑污染
- ✅ **安全性**: 敏感认证数据与业务数据分离
- ✅ **性能**: 认证数据库可以独立优化
- ✅ **可扩展**: 未来可以迁移到独立的认证服务

**重建策略**:
```bash
# 1. 备份现有数据库（如果需要）
cp tatake.db tatake.db.backup
cp tatake_auth.db tatake_auth.db.backup

# 2. 删除现有数据库
rm tatake.db tatake_auth.db

# 3. 通过应用启动自动重建
# src/domains/auth/database.py 中的 create_tables() 会自动创建表结构
```

### 5. 测试驱动开发流程

**决策**: 每个阶段完成后必须运行测试，100%通过才继续

**测试阶段**:
```
阶段1: 删除旧文件
  → 运行测试 → 预期：import错误
  → 修复import → 运行测试 → 预期：100%通过

阶段2: 创建schemas.py
  → 运行测试 → 预期：Schema相关测试通过
  → 验证API → 运行测试 → 预期：100%通过

阶段3: 更新依赖注入
  → 运行测试 → 预期：依赖注入测试通过
  → 验证路由 → 运行测试 → 预期：100%通过

阶段4: 注释非认证路由
  → 运行测试 → 预期：只有认证测试运行
  → 启动服务 → 手工验证 → 预期：只有认证端点

阶段5: 重建数据库
  → 运行测试 → 预期：数据库测试通过
  → 集成测试 → 预期：100%通过

阶段6: 最终验证
  → 完整测试套件 → 预期：所有测试100%通过
  → 代码覆盖率 → 预期：>95%
  → API手工测试 → 预期：7个端点正常工作
```

**测试命令**:
```bash
# 运行认证领域测试
uv run pytest src/domains/auth/tests/ -v

# 运行测试并生成覆盖率报告
uv run pytest src/domains/auth/tests/ --cov=src/domains/auth --cov-report=html

# 运行特定测试文件
uv run pytest src/domains/auth/tests/test_router.py -v
```

### 6. 路由注释策略

**当前路由注册** (`src/api/main.py:167-178`):
```python
from src.api.routers import user, tasks, chat, focus, rewards_new, statistics_new
from src.domains.auth.router import router as auth_router

app.include_router(auth_router, prefix=config.api_prefix, tags=["认证系统"])
app.include_router(user.router, prefix=config.api_prefix, tags=["用户管理"])
app.include_router(tasks.router, prefix=config.api_prefix, tags=["任务管理"])
app.include_router(chat.router, prefix=config.api_prefix, tags=["AI对话"])
app.include_router(focus.router, prefix=f"{config.api_prefix}/focus", tags=["专注系统"])
app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/rewards", tags=["奖励系统"])
app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/points", tags=["积分系统"])
app.include_router(statistics_new.router, prefix=f"{config.api_prefix}/statistics", tags=["统计分析"])
```

**修改后**:
```python
# from src.api.routers import user, tasks, chat, focus, rewards_new, statistics_new
from src.domains.auth.router import router as auth_router

# 只注册认证路由
app.include_router(auth_router, prefix=config.api_prefix, tags=["认证系统"])

# 其他路由暂时注释掉，等待DDD架构实现
# app.include_router(user.router, prefix=config.api_prefix, tags=["用户管理"])
# app.include_router(tasks.router, prefix=config.api_prefix, tags=["任务管理"])
# app.include_router(chat.router, prefix=config.api_prefix, tags=["AI对话"])
# app.include_router(focus.router, prefix=f"{config.api_prefix}/focus", tags=["专注系统"])
# app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/rewards", tags=["奖励系统"])
# app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/points", tags=["积分系统"])
# app.include_router(statistics_new.router, prefix=f"{config.api_prefix}/statistics", tags=["统计分析"])
```

### 7. API信息端点更新

**当前实现** (`src/api/main.py:138-163`):
```python
@app.get(f"{config.api_prefix}/info", tags=["系统"])
async def api_info():
    return create_success_response(
        data={
            "endpoints": {
                "认证系统": 7,
                "AI对话系统": 10,    # ❌ 应该删除
                "任务管理": 12,       # ❌ 应该删除
                "专注系统": 15,       # ❌ 应该删除
                "奖励系统": 12,       # ❌ 应该删除
                "统计分析": 10,       # ❌ 应该删除
                "用户管理": 6         # ❌ 应该删除
            },
            "total_endpoints": 72,    # ❌ 应该改为7
            ...
        }
    )
```

**更新后**:
```python
@app.get(f"{config.api_prefix}/info", tags=["系统"])
async def api_info():
    return create_success_response(
        data={
            "api_name": config.app_name,
            "api_version": config.app_version,
            "api_prefix": config.api_prefix,
            "endpoints": {
                "认证系统": 7
            },
            "total_endpoints": 7,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            },
            "status": "认证领域已完成，其他领域开发中"
        },
        message="API信息 - 当前仅包含认证系统"
    )
```

## 技术栈

- **Web框架**: FastAPI 0.104+
- **数据库**: SQLite + SQLModel
- **认证**: JWT + bcrypt
- **测试**: pytest + pytest-asyncio
- **代码质量**: ruff + mypy
- **文档**: OpenAPI 3.1.0

## 安全考虑

1. **密码安全**: 使用bcrypt加密，salt轮数12
2. **JWT安全**: 使用HS256算法，密钥长度≥32字节
3. **令牌黑名单**: 登出后令牌立即失效
4. **验证码安全**: 6位数字，5分钟有效期，3次重试限制
5. **会话管理**: 独立的会话表，支持设备绑定

## 性能优化

1. **数据库索引**: 在user_id, phone, token_jti等字段上建立索引
2. **异步IO**: 全异步数据库操作
3. **连接池**: SQLAlchemy连接池管理
4. **缓存策略**: 暂不实现（未来可用Redis）

## 可维护性

1. **代码结构**: 清晰的DDD分层
2. **文档完整**: 每个函数都有docstring
3. **测试覆盖**: >95%覆盖率
4. **错误处理**: 统一的异常体系
5. **日志记录**: 结构化日志（Console输出）
