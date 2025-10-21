# 任务清单: cleanup-auth-legacy-code

## 概述
本任务清单采用**测试驱动开发(TDD)**流程，每个阶段完成后必须运行测试并100%通过才能继续。

---

## 阶段1: 删除旧认证代码文件

### Task 1.1: 删除旧认证路由
**目标**: 删除 `src/api/routers/auth.py`

**步骤**:
```bash
rm src/api/routers/auth.py
```

**验证**:
- [x] 文件已删除 - 移动到backup目录
- [x] `git status` 显示文件已删除

---

### Task 1.2: 删除旧认证服务
**目标**: 删除 `src/services/async_auth_service.py` 和 `src/services/auth_service.py`

**步骤**:
```bash
rm -f src/services/async_auth_service.py
rm -f src/services/auth_service.py
```

**验证**:
- [ ] 文件已删除
- [ ] `git status` 显示文件已删除

---

### Task 1.3: 删除旧认证仓库
**目标**: 删除 `src/repositories/async_auth.py`

**步骤**:
```bash
rm -f src/repositories/async_auth.py
```

**验证**:
- [ ] 文件已删除
- [ ] `git status` 显示文件已删除

---

### Task 1.4: 删除旧Schema文件
**目标**: 删除 `src/api/schemas/auth.py` 和 `src/api/schemas.py`

**步骤**:
```bash
rm -f src/api/schemas/auth.py
rm -f src/api/schemas.py
```

**验证**:
- [ ] 文件已删除
- [ ] 检查 `src/api/schemas/__init__.py` 是否需要更新

---

### Task 1.5: 阶段性测试 - 预期失败
**目标**: 运行测试，预期会出现import错误

**步骤**:
```bash
uv run pytest src/domains/auth/tests/ -v
```

**预期结果**:
- ❌ 测试失败（import错误）
- 错误信息: `ModuleNotFoundError: No module named 'api.schemas.auth'`

**下一步**: 继续到阶段2修复import错误

---

## 阶段2: 创建认证领域Schema

### Task 2.1: 创建最小化Schema文件
**目标**: 创建 `src/domains/auth/schemas.py`，只包含7个API需要的Schema

**需要的Schema**:
```python
# 请求Schema
- GuestInitRequest
- GuestUpgradeRequest
- SMSCodeRequest
- LoginRequest
- TokenRefreshRequest
- LogoutRequest (可选)

# 响应Schema
- BaseResponse
- ErrorResponse
- AuthTokenResponse
- UserInfoResponse

# 辅助Schema
- DeviceInfo
- TokenInfo
- UserProfile
```

**步骤**:
1. 参考 `src/api/schemas/auth.py` 中的定义（不要复制粘贴）
2. 重新编写最小化的Schema
3. 确保所有字段都有验证和文档
4. 使用Pydantic v2语法

**文件位置**: `src/domains/auth/schemas.py`

**验证**:
- [ ] 文件已创建
- [ ] Schema定义完整
- [ ] 所有字段有类型注解
- [ ] 所有Schema有docstring

---

### Task 2.2: 更新service.py的import
**目标**: 修改 `src/domains/auth/service.py` 的Schema导入

**修改**:
```python
# 旧导入 (删除)
from api.schemas.auth import (
    GuestInitRequest, GuestUpgradeRequest, LoginRequest,
    SMSCodeRequest, TokenRefreshRequest, DeviceInfo
)

# 新导入 (添加)
from .schemas import (
    GuestInitRequest, GuestUpgradeRequest, LoginRequest,
    SMSCodeRequest, TokenRefreshRequest, DeviceInfo
)
```

**验证**:
- [ ] import语句已更新
- [ ] 没有语法错误

---

### Task 2.3: 更新router.py的import
**目标**: 修改 `src/domains/auth/router.py` 的Schema导入

**修改**:
```python
# 旧导入 (删除)
from api.schemas.auth import (
    GuestInitRequest, GuestUpgradeRequest, LoginRequest,
    SMSCodeRequest, TokenRefreshRequest,
    AuthInitResponse, AuthUpgradeResponse, LoginResponse,
    TokenRefreshResponse, SMSCodeResponse, UserInfoResponse,
    BaseResponse, ErrorResponse
)

# 新导入 (添加)
from .schemas import (
    GuestInitRequest, GuestUpgradeRequest, LoginRequest,
    SMSCodeRequest, TokenRefreshRequest,
    AuthTokenResponse, UserInfoResponse,
    BaseResponse, ErrorResponse
)
```

**验证**:
- [ ] import语句已更新
- [ ] 响应模型可能需要调整（统一使用AuthTokenResponse）

---

### Task 2.4: 更新测试文件的import
**目标**: 修改 `src/domains/auth/tests/` 中所有测试文件的Schema导入

**文件列表**:
- `test_router.py`
- `test_service.py`
- `test_integration.py`
- `conftest.py`

**修改每个文件**:
```python
# 旧导入 (删除)
from api.schemas.auth import ...

# 新导入 (添加)
from src.domains.auth.schemas import ...
```

**验证**:
- [ ] 所有测试文件的import已更新
- [ ] 没有遗漏的文件

---

### Task 2.5: 阶段性测试 - Schema验证
**目标**: 运行测试，验证Schema定义正确

**步骤**:
```bash
# 运行所有认证测试
uv run pytest src/domains/auth/tests/ -v

# 如果有失败，单独运行Schema相关测试
uv run pytest src/domains/auth/tests/test_router.py::test_guest_init_request_validation -v
```

**预期结果**:
- ✅ 所有测试100%通过
- ✅ 没有import错误
- ✅ Schema验证正常工作

**如果失败**:
- 检查Schema定义是否完整
- 检查字段类型是否正确
- 检查验证器是否正确

---

## 阶段3: 清理依赖注入系统

### Task 3.1: 更新dependencies.py - 删除旧import
**目标**: 删除 `src/api/dependencies.py` 中旧认证服务的导入

**删除的导入**:
```python
from src.services.async_auth_service import AsyncAuthService
from src.services import AuthService  # 如果存在
```

**验证**:
- [ ] 旧import已删除
- [ ] 保留其他服务的import（UserService, TaskService等）

---

### Task 3.2: 更新dependencies.py - 删除工厂方法
**目标**: 删除 `get_async_auth_service` 和 `get_auth_service` 函数

**删除的函数** (约第195-251行):
```python
async def get_auth_service(...):
    ...

async def get_async_auth_service(...):
    ...
```

**验证**:
- [ ] 函数已删除
- [ ] 没有其他代码引用这些函数

---

### Task 3.3: 检查ServiceFactory类
**目标**: 检查并清理 `ServiceFactory` 类中的认证相关方法

**需要删除的方法**:
```python
class ServiceFactory:
    def get_async_auth_repository(...)  # 删除
    def get_async_auth_service(...)     # 删除
    def get_auth_service(...)           # 删除（如果存在）
```

**验证**:
- [ ] 旧方法已删除
- [ ] ServiceFactory类仍然正常工作

---

### Task 3.4: 阶段性测试 - 依赖注入验证
**目标**: 确保依赖注入系统清理后不影响认证功能

**步骤**:
```bash
# 运行认证路由测试（会测试依赖注入）
uv run pytest src/domains/auth/tests/test_router.py -v

# 运行集成测试
uv run pytest src/domains/auth/tests/test_integration.py -v
```

**预期结果**:
- ✅ 所有测试100%通过
- ✅ 认证领域独立运行，不依赖全局依赖注入

---

## 阶段4: 注释非认证路由

### Task 4.1: 注释main.py的路由导入
**目标**: 注释 `src/api/main.py` 中非认证路由的导入

**修改** (约第167行):
```python
# 旧代码
from src.api.routers import user, tasks, chat, focus, rewards_new, statistics_new
from src.domains.auth.router import router as auth_router

# 新代码
# from src.api.routers import user, tasks, chat, focus, rewards_new, statistics_new
from src.domains.auth.router import router as auth_router
```

**验证**:
- [ ] import已注释
- [ ] 认证路由import保留

---

### Task 4.2: 注释main.py的路由注册
**目标**: 注释所有非认证路由的 `include_router`

**修改** (约第168-178行):
```python
# 只保留认证路由
app.include_router(auth_router, prefix=config.api_prefix, tags=["认证系统"])

# 注释其他路由
# app.include_router(user.router, prefix=config.api_prefix, tags=["用户管理"])
# app.include_router(tasks.router, prefix=config.api_prefix, tags=["任务管理"])
# app.include_router(chat.router, prefix=config.api_prefix, tags=["AI对话"])
# app.include_router(focus.router, prefix=f"{config.api_prefix}/focus", tags=["专注系统"])
# app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/rewards", tags=["奖励系统"])
# app.include_router(rewards_new.router, prefix=f"{config.api_prefix}/points", tags=["积分系统"])
# app.include_router(statistics_new.router, prefix=f"{config.api_prefix}/statistics", tags=["统计分析"])
```

**验证**:
- [ ] 只有认证路由被注册
- [ ] 注释格式正确

---

### Task 4.3: 更新API信息端点
**目标**: 修改 `/api/v1/info` 端点，只显示认证系统的7个端点

**修改** `src/api/main.py` (约第138-163行):
```python
@app.get(f"{config.api_prefix}/info", tags=["系统"])
async def api_info():
    """API信息端点"""
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

**验证**:
- [ ] 端点统计已更新
- [ ] 返回数据准确

---

### Task 4.4: 阶段性测试 - FastAPI启动验证
**目标**: 启动FastAPI服务，验证只有认证端点可用

**步骤**:
```bash
# 启动服务
uv run uvicorn src.api.main:app --reload --port 8000

# 在另一个终端测试
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/info
```

**预期结果**:
- ✅ 服务正常启动
- ✅ `/api/v1/info` 显示只有7个认证端点
- ✅ 访问 http://localhost:8000/docs 只看到认证相关API

**验证API列表**:
```
系统端点 (3个):
- GET  /
- GET  /health
- GET  /api/v1/info

认证端点 (7个):
- POST /api/v1/auth/guest/init
- POST /api/v1/auth/guest/upgrade
- POST /api/v1/auth/sms/send
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET  /api/v1/auth/user-info

文档端点 (3个):
- GET  /docs
- GET  /redoc
- GET  /openapi.json
```

---

## 阶段5: 重建数据库

### Task 5.1: 备份现有数据库
**目标**: 备份 `tatake.db` 和 `tatake_auth.db`（可选）

**步骤**:
```bash
# 如果需要保留数据，先备份
cp tatake.db tatake.db.backup.$(date +%Y%m%d_%H%M%S)
cp tatake_auth.db tatake_auth.db.backup.$(date +%Y%m%d_%H%M%S)
```

**验证**:
- [ ] 备份文件已创建（如果需要）

---

### Task 5.2: 删除现有数据库
**目标**: 删除 `tatake.db` 和 `tatake_auth.db`

**步骤**:
```bash
rm -f tatake.db tatake.db-shm tatake.db-wal
rm -f tatake_auth.db tatake_auth.db-shm tatake_auth.db-wal
```

**验证**:
- [ ] 数据库文件已删除
- [ ] WAL和SHM文件也已删除

---

### Task 5.3: 初始化认证数据库
**目标**: 通过启动应用自动创建认证数据库表结构

**步骤**:
```bash
# 方式1: 启动应用（会自动创建表）
uv run uvicorn src.api.main:app --reload

# 方式2: 运行认证领域的数据库初始化
uv run python -c "
from src.domains.auth.database import init_auth_database
import asyncio
asyncio.run(init_auth_database())
"
```

**验证**:
- [ ] `tatake_auth.db` 已创建
- [ ] 表结构正确（users, sms_verifications, token_blacklist等）

---

### Task 5.4: 验证数据库结构
**目标**: 检查数据库表结构是否正确

**步骤**:
```bash
# 检查认证数据库
sqlite3 tatake_auth.db ".schema"
```

**预期表结构**:
```sql
CREATE TABLE users (...);
CREATE TABLE sms_verifications (...);
CREATE TABLE token_blacklist (...);
CREATE TABLE user_sessions (...);
CREATE TABLE auth_logs (...);
```

**验证**:
- [ ] 所有表已创建
- [ ] 索引已创建
- [ ] 外键约束正确

---

### Task 5.5: 阶段性测试 - 数据库测试
**目标**: 运行数据库相关测试

**步骤**:
```bash
# 运行Repository测试
uv run pytest src/domains/auth/tests/test_repository.py -v

# 运行集成测试
uv run pytest src/domains/auth/tests/test_integration.py -v
```

**预期结果**:
- ✅ 所有数据库测试100%通过
- ✅ CRUD操作正常
- ✅ 事务处理正确

---

## 阶段6: 最终验证与测试

### Task 6.1: 运行完整测试套件
**目标**: 运行所有认证领域测试，确保100%通过

**步骤**:
```bash
# 运行所有测试
uv run pytest src/domains/auth/tests/ -v

# 生成覆盖率报告
uv run pytest src/domains/auth/tests/ --cov=src/domains/auth --cov-report=html --cov-report=term
```

**预期结果**:
- ✅ 所有测试100%通过
- ✅ 测试覆盖率 > 95%
- ✅ 无警告或错误

**覆盖率要求**:
- Repository层: 100%
- Service层: >95%
- Router层: >95%
- 整体: >95%

---

### Task 6.2: 手工测试认证流程
**目标**: 手工测试完整的认证流程

**测试流程**:
```bash
# 1. 游客账号初始化
curl -X POST http://localhost:8000/api/v1/auth/guest/init \
  -H "Content-Type: application/json" \
  -d '{}'

# 2. 发送短信验证码
curl -X POST http://localhost:8000/api/v1/auth/sms/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000", "verification_type": "register"}'

# 3. 游客账号升级
curl -X POST http://localhost:8000/api/v1/auth/guest/upgrade \
  -H "Authorization: Bearer <guest_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "upgrade_method": "sms_code",
    "phone": "13800138000",
    "sms_code": "123456"
  }'

# 4. 用户登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login_method": "sms_code",
    "phone": "13800138000",
    "sms_code": "123456"
  }'

# 5. 获取用户信息
curl -X GET http://localhost:8000/api/v1/auth/user-info \
  -H "Authorization: Bearer <access_token>"

# 6. 刷新令牌
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# 7. 用户登出
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

**验证**:
- [ ] 游客初始化成功
- [ ] 短信验证码发送成功（控制台有彩色输出）
- [ ] 游客升级成功
- [ ] 用户登录成功
- [ ] 获取用户信息成功
- [ ] 令牌刷新成功
- [ ] 用户登出成功

---

### Task 6.3: 验证API文档
**目标**: 检查Swagger UI文档是否正确

**步骤**:
1. 访问 http://localhost:8000/docs
2. 检查只显示认证相关API
3. 测试每个API的"Try it out"功能

**验证**:
- [ ] Swagger UI正常显示
- [ ] 只有认证端点（7个）
- [ ] 所有端点都有完整的描述
- [ ] Request/Response Schema正确
- [ ] "Try it out"功能正常

---

### Task 6.4: 代码质量检查
**目标**: 运行代码质量工具

**步骤**:
```bash
# Ruff检查（如果安装）
uv run ruff check src/domains/auth/

# 类型检查（如果安装mypy）
uv run mypy src/domains/auth/
```

**验证**:
- [ ] 无代码风格问题
- [ ] 无类型错误
- [ ] 无未使用的import

---

### Task 6.5: 清理.gitignore
**目标**: 确保数据库文件不被提交

**检查** `.gitignore`:
```
*.db
*.db-shm
*.db-wal
*.backup
```

**验证**:
- [ ] 数据库文件在.gitignore中
- [ ] 备份文件在.gitignore中

---

### Task 6.6: Git提交
**目标**: 提交所有更改

**步骤**:
```bash
# 查看更改
git status

# 添加文件
git add .

# 提交
git commit -m "cleanup: 删除旧认证代码，统一使用DDD领域架构

- 删除旧认证路由、服务、仓库和Schema
- 创建认证领域专用Schema (src/domains/auth/schemas.py)
- 清理依赖注入系统中的旧认证依赖
- 注释非认证路由，只保留7个认证API
- 更新API信息端点统计数据
- 重建数据库，清空所有数据
- 所有测试100%通过，覆盖率>95%
"
```

**验证**:
- [ ] 所有文件已添加
- [ ] 提交信息清晰
- [ ] 提交成功

---

## 完成标准

清理任务完成后，系统应满足：

### 功能标准
- ✅ 只有 `src/domains/auth/` 包含认证代码
- ✅ FastAPI只暴露7个认证API + 3个系统端点
- ✅ 所有旧认证代码已删除
- ✅ 认证Schema独立在领域内

### 测试标准
- ✅ 所有测试100%通过
- ✅ 测试覆盖率>95%
- ✅ 无测试警告或错误

### 代码质量标准
- ✅ 无未使用的import
- ✅ 无代码风格问题
- ✅ 无类型错误

### 运行标准
- ✅ FastAPI服务正常启动
- ✅ Swagger UI显示正确
- ✅ 7个认证API全部可用
- ✅ 数据库结构正确

### 文档标准
- ✅ API文档完整
- ✅ 代码注释清晰
- ✅ README更新（如果需要）

---

## 时间估算

| 阶段 | 预计时间 | 说明 |
|------|---------|------|
| 阶段1: 删除旧代码 | 15分钟 | 删除文件较简单 |
| 阶段2: 创建Schema | 60分钟 | 需要仔细编写Schema |
| 阶段3: 清理依赖 | 20分钟 | 删除依赖注入代码 |
| 阶段4: 注释路由 | 15分钟 | 注释main.py代码 |
| 阶段5: 重建数据库 | 10分钟 | 删除和重建数据库 |
| 阶段6: 最终验证 | 60分钟 | 完整测试和验证 |
| **总计** | **约3小时** | 包含所有测试时间 |

---

## 故障排除

### 问题1: Schema导入错误
**症状**: `ModuleNotFoundError: No module named 'src.domains.auth.schemas'`

**解决**:
1. 确认 `src/domains/auth/schemas.py` 已创建
2. 检查import路径是否正确
3. 重启Python解释器或IDE

### 问题2: 测试失败
**症状**: 部分测试用例失败

**解决**:
1. 查看错误消息定位问题
2. 检查Schema定义是否与测试匹配
3. 确认数据库连接正常

### 问题3: FastAPI启动失败
**症状**: 服务无法启动，报import错误

**解决**:
1. 检查main.py中的所有import
2. 确认注释的代码格式正确
3. 查看错误堆栈定位具体问题

### 问题4: 数据库表未创建
**症状**: `tatake_auth.db` 为空或缺少表

**解决**:
1. 手动运行数据库初始化脚本
2. 检查 `src/domains/auth/database.py` 中的 `create_tables()` 函数
3. 查看日志确认是否有错误

---

## 回滚计划

如果需要回滚：

```bash
# 1. 使用git恢复
git reset --hard HEAD~1

# 2. 或者从备份恢复数据库
cp tatake.db.backup tatake.db
cp tatake_auth.db.backup tatake_auth.db

# 3. 重启服务
uv run uvicorn src.api.main:app --reload
```
