# 认证领域简化设计文档

## Context

当前认证系统支持多种登录方式和功能，包括：
- 4种登录方式：手机号+验证码、密码、微信、Apple ID
- 游客系统：基于设备信息识别
- 用户信息管理：昵称、头像、积分、等级
- 6个数据库表：users, sms_verification, token_blacklist, user_sessions, user_settings, audit_logs

这些功能导致系统复杂度高、职责不清、维护成本大。需要简化为单一职责的纯认证领域。

### 约束条件
- Token 机制保持不变（JWT with access_token + refresh_token）
- 审计日志功能保留

### 利益相关者
- 

## Goals / Non-Goals

### Goals
1. **简化认证流程**：统一为微信 OpenID 单一登录方式
2. **明确领域边界**：auth 领域只负责身份认证，不管理用户资料
3. **标准化响应格式**：所有端点统一响应结构
4. **减少数据库复杂度**：从 6 张表减少到 2 张表（auth + audit_logs）
5. **提升代码可维护性**：移除冗余代码和不必要的依赖

### Non-Goals
1. ❌ 实现微信 API 对接（假设客户端已获取 openid）
2. ❌ 实现用户资料管理（应在独立的 user 领域实现）
3. ❌ 实现游客清理机制（留待后续实现）
4. ❌ 提供微信 code 换 openid 的服务端接口

## Decisions

### 决策 1: 游客身份生成策略

**决定**：每次游客初始化都创建全新的随机身份，不依赖任何客户端信息

**理由**：
- 设备信息不可靠，容易伪造和碰撞
- 简化服务端逻辑，无需查重和去重
- 客户端负责管理本地游客身份（通过保存 user_id 和 token）

**替代方案**：
- ❌ 基于 IP + User-Agent 生成游客：不可靠，用户切换网络会创建新账号
- ❌ 要求客户端传递设备 UUID：增加客户端负担，且无法防止伪造

**权衡**：
- ✅ 优点：简单、安全、无状态
- ⚠️ 缺点：用户卸载应用后丢失游客身份（可接受，游客数据本就是临时的）

### 决策 2: 微信注册的内部实现

**决定**：微信注册 = 创建游客 + 立即升级

**理由**：
- 复用游客升级逻辑，避免代码重复
- 保持数据一致性（所有用户都有 created_at 和 last_login_at）
- 简化事务管理

**实现细节**：
```python
async def wechat_register(wechat_openid: str):
    # 1. 检查 openid 是否已存在
    if await auth_repo.get_by_wechat_openid(wechat_openid):
        raise ConflictError("用户已注册")

    # 2. 创建游客账号
    guest = await create_guest()

    # 3. 立即升级为正式用户
    user = await upgrade_guest(guest.id, wechat_openid)

    return user
```

**在代码和文档中的说明**：
- 在 `router.py` 的 `/auth/register` 端点注释中明确说明
- 在 `service.py` 的 `wechat_register` 方法 docstring 中注明实现原理
- 在 API 文档中说明此设计决策

### 决策 3: 统一响应格式

**决定**：所有端点使用 `{ "code": int, "data": dict, "message": str }` 格式

**理由**：
- 与前端约定的标准格式一致
- `code` 使用 HTTP 状态码，减少学习成本
- `message` 提供人类可读的错误描述

**示例**：
```json
// 成功响应
{
  "code": 200,
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc..."
  },
  "message": "success"
}

// 错误响应
{
  "code": 404,
  "data": null,
  "message": "用户不存在"
}
```

**实现方式**：
- 创建 `UnifiedResponse` Pydantic 模型
- 在所有 router 函数中手动构造响应（不使用全局中间件，保持显式）

### 决策 4: 数据库表结构

**决定**：重命名 `auth_users` 为 `auth`，只保留 7 个核心字段

**字段说明**：
| 字段 | 类型 | 说明 | 索引 |
|------|------|------|------|
| `id` | UUID | 主键 | PRIMARY KEY |
| `wechat_openid` | String(100) | 微信 OpenID，游客为 null | UNIQUE, INDEX |
| `is_guest` | Boolean | 是否为游客 | INDEX |
| `created_at` | DateTime(TZ) | 创建时间 | INDEX |
| `updated_at` | DateTime(TZ) | 更新时间 | - |
| `last_login_at` | DateTime(TZ) | 最后登录时间 | - |
| `jwt_version` | Integer | JWT 版本号 | - |

**索引设计**：
- `idx_auth_wechat_openid` ON (`wechat_openid`) - 登录查询
- `idx_auth_is_guest` ON (`is_guest`) - 游客统计
- `idx_auth_created_at` ON (`created_at`) - 按创建时间查询

**删除的表**：
- `auth_sms_verification` - 不再需要短信验证
- `auth_token_blacklist` - 不再支持登出功能
- `auth_user_sessions` - 不再维护会话状态
- `auth_user_settings` - 用户设置移至 user 领域

**保留的表**：
- `auth_audit_logs` - 审计日志继续保留

### 决策 5: 移除登出功能

**决定**：不再提供用户登出端点，不维护 token 黑名单

**理由**：
- Token 本身有过期时间（30分钟），风险可控
- 移除黑名单表简化数据库维护
- 客户端可通过删除本地 token 实现登出效果
- 如用户认为 token 泄露，可通过修改密码（未来功能）使所有 token 失效

**安全考虑**：
- JWT 包含 `jwt_version` 字段
- 升级账号时 `jwt_version += 1`，旧 token 自动失效
- 未来如需强制登出，可手动增加用户的 `jwt_version`

### 决策 6: 游客升级流程

**决定**：升级时需要提供游客的 access_token 和微信 openid

**流程**：
```
1. 客户端在 Header 中携带游客的 access_token
2. 服务端从 token 中解析出 user_id
3. 验证该用户必须是游客（is_guest=true）
4. 验证 wechat_openid 未被其他用户使用
5. 更新用户：is_guest=false, wechat_openid=提供的值, jwt_version+=1
6. 返回新的 token
```

**安全保障**：
- 必须验证当前 token 的有效性
- 必须验证 token 中的 user_id 对应的用户是游客
- 必须验证 openid 的唯一性

## API 端点设计

### 1. POST /api/v1/auth/guest/init - 游客初始化

**请求**：
```json
// 无请求体
{}
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "user_id": "uuid",
    "access_token": "jwt_token",
    "refresh_token": "jwt_token"
  },
  "message": "success"
}
```

### 2. POST /api/v1/auth/register - 微信注册

**请求**：
```json
{
  "wechat_openid": "oA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5"
}
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "user_id": "uuid",
    "access_token": "jwt_token",
    "refresh_token": "jwt_token"
  },
  "message": "success"
}
```

**错误响应**（409 - 用户已存在）：
```json
{
  "code": 409,
  "data": null,
  "message": "该微信账号已注册"
}
```

### 3. POST /api/v1/auth/login - 微信登录

**请求**：
```json
{
  "wechat_openid": "oA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5"
}
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "user_id": "uuid",
    "access_token": "jwt_token",
    "refresh_token": "jwt_token"
  },
  "message": "success"
}
```

**错误响应**（404 - 用户不存在）：
```json
{
  "code": 404,
  "data": null,
  "message": "用户不存在，请先注册"
}
```

### 4. POST /api/v1/auth/guest/upgrade - 游客升级

**请求头**：
```
Authorization: Bearer <guest_access_token>
```

**请求体**：
```json
{
  "wechat_openid": "oA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5"
}
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "user_id": "uuid",
    "access_token": "jwt_token",
    "refresh_token": "jwt_token"
  },
  "message": "success"
}
```

**错误响应**：
- 401 - token 无效或已过期
- 403 - 当前用户不是游客
- 409 - 该微信账号已被其他用户使用

### 5. POST /api/v1/auth/refresh - 刷新 Token

**请求**：
```json
{
  "refresh_token": "jwt_refresh_token"
}
```

**响应**（200）：
```json
{
  "code": 200,
  "data": {
    "user_id": "uuid",
    "access_token": "jwt_token",
    "refresh_token": "jwt_token"
  },
  "message": "success"
}
```

**错误响应**（401）：
```json
{
  "code": 401,
  "data": null,
  "message": "refresh_token 无效或已过期"
}
```

## Risks / Trade-offs

### 风险 1: 数据迁移失败

**风险**：现有用户数据（昵称、头像、积分）迁移到其他领域时可能出错

**缓解措施**：
- 迁移前完整备份数据库
- 编写可重复执行的幂等迁移脚本
- 在测试环境充分验证
- 保留旧表一段时间作为备份

### 风险 2: 游客账号滥用

**风险**：无限制的游客创建可能导致数据库膨胀或恶意刷量

**缓解措施**：
- 后续可添加 IP 级别的频率限制（当前版本不实现）
- 后续可实现游客账号定期清理机制（创建时间超过 N 天且未升级）

### 风险 3: 客户端适配成本

**风险**：所有客户端需要同步更新以适配新的 API

**缓解措施**：
- 提供详细的 API 迁移文档
- 考虑短期内同时支持新旧两套 API（通过 `/v1` 和 `/v2` 区分）

### 风险 4: 无法强制用户登出

**风险**：移除登出功能后，丢失的设备或泄露的 token 在过期前仍可使用

**权衡**：
- Token 过期时间较短（30分钟），风险可控
- 用户可通过升级账号使旧 token 失效（jwt_version 机制）
- 如确需强制登出，可手动增加数据库中的 jwt_version

## Migration Plan

### 阶段 1: 准备阶段（开发环境）

1. **创建新表结构**
   - 创建 `auth` 表
   - 保留 `auth_audit_logs` 表
   - 标记其他表为待删除

2. **数据迁移脚本**
   ```python
   # 迁移用户基础认证信息
   INSERT INTO auth (id, wechat_openid, is_guest, created_at, updated_at, last_login_at, jwt_version)
   SELECT id, wechat_openid, is_guest, created_at, updated_at, last_login_at, jwt_version
   FROM auth_users;

   # 迁移用户资料到 user 领域（假设存在）
   INSERT INTO user_profiles (user_id, nickname, avatar, phone, email, ...)
   SELECT id, nickname, avatar, phone, email, ...
   FROM auth_users;
   ```

3. **代码重构**
   - 更新所有 models, schemas, routers, services
   - 移除 SMS 相关代码
   - 统一响应格式

4. **测试覆盖**
   - 单元测试覆盖所有新端点
   - 集成测试验证完整流程
   - 负载测试验证性能

### 阶段 2: 部署阶段（生产环境）

1. **执行数据迁移**
   - 在维护窗口执行迁移脚本
   - 验证数据完整性
   - 保留旧表作为备份（30天后删除）

2. **部署新版本后端**
   - 使用蓝绿部署或滚动更新
   - 监控错误率和响应时间
   - 准备快速回滚方案

3. **客户端更新**
   - 发布新版本客户端
   - 强制旧版本升级（如有必要）
   - 监控客户端错误上报

### 阶段 3: 清理阶段

1. **删除旧表**（30天后）
   ```sql
   DROP TABLE auth_users;
   DROP TABLE auth_sms_verification;
   DROP TABLE auth_token_blacklist;
   DROP TABLE auth_user_sessions;
   DROP TABLE auth_user_settings;
   ```

2. **移除兼容代码**
   - 删除旧的 Schema 定义
   - 删除迁移脚本

### Rollback Plan

如果部署后出现严重问题：

1. **数据库回滚**：
   - 还原数据库备份
   - 重新部署旧版本代码

2. **代码回滚**：
   - Git revert 到上一个稳定版本
   - 重新部署

3. **客户端回滚**：
   - 移除强制更新限制
   - 允许旧版本继续使用

## Open Questions

1. ❓ **是否需要实现 wechat_openid 的格式验证？**
   - 回答：不验证（已确认）

2. ❓ **是否需要服务端调用微信 API 验证 openid 的真实性？**
   - 回答：不需要，假设客户端传递的 openid 是可信的（已确认）

3. ❓ **用户资料（昵称、头像、积分）迁移到哪个领域？**
   - 待确认：需要与团队讨论是否已存在 user 领域，当前不需要考虑

4. ❓ **是否需要保留审计日志？**
   - 回答：保留 `auth_audit_logs` 表（已确认）

5. ❓ **游客账号的清理策略是什么？**
   - 回答：当前版本不实现清理功能（已确认）
