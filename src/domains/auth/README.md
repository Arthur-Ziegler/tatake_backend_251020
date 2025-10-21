# 认证领域 (Auth Domain)

## 概述

认证领域是TaKeKe项目采用领域驱动设计(DDD)架构的第一个完整实现，负责处理用户身份认证、授权管理、游客账号升级等核心认证功能。该领域采用独立的数据库和完整的业务逻辑，为整个应用提供安全可靠的身份认证基础。

## 架构说明

### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (Router)                       │
│                 FastAPI路由定义 (7个端点)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Service Layer                                │
│              业务逻辑处理和规则验证                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Repository Layer                               │
│              数据访问抽象和数据库操作                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Database Layer                               │
│            认证专用数据库 (tatake_auth.db)                     │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 文件 | 功能描述 |
|------|------|----------|
| **Router** | `router.py` | FastAPI路由定义，包含7个认证API端点 |
| **Service** | `service.py` | 业务逻辑层，处理认证相关业务规则和流程 |
| **Repository** | `repository.py` | 数据访问层，封装数据库操作和查询逻辑 |
| **Models** | `models.py` | SQLModel数据模型定义，对应数据库表结构 |
| **Database** | `database.py` | 认证数据库连接管理和操作工具 |
| **Schemas** | `schemas.py` | Pydantic请求/响应模型定义 |
| **Exceptions** | `exceptions.py` | 认证领域专用异常类定义 |

## 数据库设计

### 认证数据库 (tatake_auth.db)

独立的SQLite数据库，专门存储认证相关数据，与业务数据库分离。

#### 数据表结构

| 表名 | 用途 | 主要字段 |
|------|------|----------|
| **users** | 用户基本信息 | username, email, phone, password_hash, is_guest, jwt_version |
| **user_settings** | 用户设置 | language, timezone, theme, notification_settings |
| **sms_verification** | 短信验证码 | phone, code, verification_type, expires_at, attempts |
| **token_blacklist** | JWT令牌黑名单 | token_id, user_id, token_type, expires_at |
| **user_sessions** | 用户会话管理 | session_id, device_info, ip_address, last_activity_at |
| **auth_logs** | 认证审计日志 | user_id, action, result, ip_address, timestamp |

#### 数据库分离优势

1. **安全性**: 认证数据独立存储，降低安全风险
2. **性能**: 认证查询独立，不影响业务查询性能
3. **扩展性**: 认证服务可独立部署和扩展
4. **维护性**: 认证逻辑独立，便于维护和升级

## API接口

### 认证系统API (7个端点)

| 端点 | 方法 | 功能 | 认证要求 |
|------|------|------|----------|
| `/auth/guest/init` | POST | 游客账号初始化 | ❌ |
| `/auth/guest/upgrade` | POST | 游客账号升级 | ✅ (游客令牌) |
| `/auth/sms/send` | POST | 发送短信验证码 | ✅ |
| `/auth/login` | POST | 用户登录 | ❌ |
| `/auth/refresh` | POST | 刷新访问令牌 | ❌ |
| `/auth/logout` | POST | 用户登出 | ✅ |
| `/auth/user-info` | GET | 获取用户信息 | ✅ |

### 请求/响应示例

#### 游客初始化
```bash
POST /api/v1/auth/guest/init
Content-Type: application/json

{
    "device_id": "device-12345",
    "device_type": "ios",
    "app_version": "1.0.0"
}
```

#### 响应
```json
{
    "success": true,
    "data": {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
        "is_guest": true
    }
}
```

## 使用指南

### 快速开始

1. **初始化数据库**
```python
from src.domains.auth.database import create_tables

await create_tables()  # 创建所有认证表
```

2. **注册认证路由**
```python
from src.domains.auth.router import router

app.include_router(router, prefix="/api/v1", tags=["认证系统"])
```

3. **使用认证服务**
```python
from src.domains.auth.service import AuthService
from src.domains.auth.database import get_auth_db

async with get_auth_db() as session:
    auth_service = AuthService(session)

    # 游客初始化
    result = await auth_service.init_guest_account(
        device_id="test-device",
        device_type="ios"
    )
```

### 认证中间件

使用JWT令牌进行身份验证：

```python
from src.api.middleware.auth import get_current_user

@router.get("/protected-endpoint")
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    return {"user_id": current_user.id}
```

### 错误处理

统一的错误处理格式：

```python
from src.domains.auth.exceptions import (
    AuthenticationException,
    TokenExpiredException,
    UserNotFoundException
)

try:
    # 认证操作
    pass
except TokenExpiredException as e:
    return {"error": e.message, "code": e.error_code}
```

## 核心功能详解

### 1. 游客账号系统

- **初始化**: 设备绑定创建临时游客账号
- **升级**: 通过手机号、邮箱或微信升级为正式用户
- **数据迁移**: 游客数据无缝迁移到正式账号

### 2. JWT令牌管理

- **双令牌机制**: Access Token (30分钟) + Refresh Token (7天)
- **令牌黑名单**: 数据库管理失效令牌
- **版本控制**: 强制令牌失效机制
- **自动刷新**: 令牌即将过期时自动刷新

### 3. 短信验证系统

- **Mock服务**: 控制台彩色输出验证码（测试友好）
- **频率限制**: 防止短信轰炸，1分钟1次限制
- **验证码管理**: 5分钟有效期，最多5次尝试
- **多种验证类型**: 登录、注册、重置密码

### 4. 安全机制

- **密码安全**: bcrypt哈希算法
- **输入验证**: Pydantic严格验证
- **SQL注入防护**: SQLAlchemy ORM保护
- **审计日志**: 完整的认证操作记录

## 测试说明

### 测试结构

```
tests/
├── test_router.py      # API路由层测试
├── test_service.py     # 业务逻辑层测试
├── test_repository.py  # 数据访问层测试
├── test_models.py      # 数据模型测试
├── test_integration.py # 集成测试
├── test_edge_cases.py  # 边界条件测试
└── conftest.py        # pytest配置
```

### 运行测试

```bash
# 运行所有认证测试
pytest src/domains/auth/tests/ -v

# 生成覆盖率报告
pytest src/domains/auth/tests/ --cov=src/domains/auth --cov-report=html

# 运行特定测试
pytest src/domains/auth/tests/test_service.py::test_guest_init -v

# 并行运行测试
pytest src/domains/auth/tests/ -n 4
```

### 测试覆盖目标

- **单元测试覆盖率**: > 95%
- **集成测试覆盖**: > 90%
- **边界条件测试**: 100%覆盖
- **安全测试**: SQL注入、XSS、令牌安全

### 测试用例类型

1. **正常流程测试**: 验证基本功能正常工作
2. **边界条件测试**: 验证临界值处理
3. **异常情况测试**: 验证错误处理
4. **并发测试**: 验证多用户场景
5. **安全测试**: 验证安全机制
6. **性能测试**: 验证响应时间

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `AUTH_DATABASE_URL` | `sqlite+aiosqlite:///./tatake_auth.db` | 认证数据库连接URL |
| `AUTH_ECHO_SQL` | `false` | 是否输出SQL语句（调试用） |
| `JWT_SECRET_KEY` | - | JWT签名密钥（必须设置） |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | 访问令牌过期时间（分钟） |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新令牌过期时间（天） |
| `SMS_CODE_EXPIRE_MINUTES` | `5` | 短信验证码过期时间（分钟） |
| `SMS_RATE_LIMIT_SECONDS` | `60` | 短信发送间隔限制（秒） |

### 配置示例

```bash
# .env 文件
AUTH_DATABASE_URL="sqlite+aiosqlite:///./tatake_auth.db"
AUTH_ECHO_SQL="false"
JWT_SECRET_KEY="your-super-secret-jwt-key-here"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
SMS_CODE_EXPIRE_MINUTES=5
SMS_RATE_LIMIT_SECONDS=60
```

## 部署指南

### 生产环境部署

1. **数据库初始化**
```bash
# 确保认证数据库存在
python -c "
import asyncio
from src.domains.auth.database import create_tables
asyncio.run(create_tables())
"
```

2. **环境配置**
```bash
# 设置生产环境变量
export JWT_SECRET_KEY="your-production-jwt-secret"
export AUTH_DATABASE_URL="sqlite+aiosqlite:///./data/tatake_auth.db"
```

3. **权限设置**
```bash
# 确保数据库文件权限正确
chmod 600 tatake_auth.db
chown www-data:www-data tatake_auth.db
```

### 数据备份

```python
from src.domains.auth.database import auth_db_manager

# 备份数据库
await auth_db_manager.backup_database("backup/auth_backup_$(date +%Y%m%d).db")

# 恢复数据库
await auth_db_manager.restore_database("backup/auth_backup_20231021.db")
```

### 健康检查

```python
from src.domains.auth.database import auth_db_manager

# 检查数据库健康状态
health = await auth_db_manager.health_check()
print(f"数据库状态: {health['status']}")
```

## 监控和日志

### 关键指标

- **认证成功率**: 成功认证数 / 总认证请求数
- **令牌刷新频率**: 刷新请求数 / 访问令牌发放数
- **短信验证成功率**: 验证成功数 / 短信发送数
- **游客升级率**: 成功升级数 / 游客账号数

### 日志记录

认证操作自动记录到 `auth_logs` 表：

```sql
-- 查看认证统计
SELECT
    action,
    result,
    COUNT(*) as count,
    created_at::date as date
FROM auth_logs
GROUP BY action, result, created_at::date
ORDER BY date DESC;
```

## 常见问题

### Q: 如何更换JWT密钥？

A: 更新 `JWT_SECRET_KEY` 环境变量，所有现有令牌将立即失效。

### Q: 如何处理数据库迁移？

A: 使用提供的迁移脚本，确保数据一致性：

```bash
python scripts/migrate_auth_data.py --from-old --to-new
```

### Q: 如何启用真实短信服务？

A: 替换 `MockSMSService` 为真实的短信服务实现：

```python
# 替换 MockSMSService 为真实服务
from src.services.external.aliyun_sms_service import AliyunSMSService
```

### Q: 如何优化数据库性能？

A: 定期清理过期数据和重建索引：

```python
from src.domains.auth.database import auth_db_manager

# 清理过期验证码
await auth_db_manager.cleanup_expired_sms_codes()

# 清理过期令牌
await auth_db_manager.cleanup_expired_tokens()
```

## 更新日志

### v1.0.0 (2025-10-21)

- ✅ 实现完整的认证领域架构
- ✅ 创建独立的认证数据库
- ✅ 实现7个核心认证API
- ✅ 集成JWT令牌管理系统
- ✅ 实现Mock短信服务
- ✅ 添加完整的测试套件
- ✅ 编写详细的文档说明

---

**维护者**: AI Assistant
**最后更新**: 2025-10-21
**版本**: 1.0.0
**状态**: 生产就绪 ✅