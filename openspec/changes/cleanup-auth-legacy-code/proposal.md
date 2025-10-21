# 提案: cleanup-auth-legacy-code

## 概述

清理旧的认证系统代码，统一使用DDD领域驱动架构的认证模块，确保系统中只有一个认证实现，并注释掉所有非认证模块的路由，使FastAPI应用只暴露7个认证API端点。

## 背景

当前项目中存在两套认证实现：

1. **旧实现（传统三层架构）**：
   - `src/api/routers/auth.py` - 旧认证路由
   - `src/services/async_auth_service.py` - 旧异步认证服务
   - `src/repositories/async_auth.py` - 旧认证仓库
   - `src/api/schemas/auth.py` - 混合了认证和其他模块的Schema

2. **新实现（DDD领域架构）**：
   - `src/domains/auth/` - 完整的认证领域模块
   - 独立的数据库 `tatake_auth.db`
   - 完整的测试套件
   - 7个认证API端点

当前 `src/api/main.py` 已经使用了新的DDD架构（`src/domains/auth/router.py`），但旧代码仍然存在于代码库中，造成混乱和潜在的维护问题。

## 目标

1. **彻底删除旧认证代码**：删除所有旧认证相关的文件和依赖
2. **认证Schema独立化**：创建 `src/domains/auth/schemas.py`，只包含7个认证API需要的最小Schema集合
3. **清理依赖注入系统**：从 `src/api/dependencies.py` 中移除所有旧认证相关的依赖
4. **注释非认证路由**：注释掉 `src/api/main.py` 中所有非认证模块的路由注册
5. **更新API信息端点**：修正 `/api/v1/info` 端点的统计数据，只显示7个认证端点
6. **重建数据库**：清空并重建 `tatake.db` 和 `tatake_auth.db`
7. **测试驱动验证**：每个阶段完成后运行测试，确保100%通过才继续

## 预期结果

清理完成后，系统应满足：

1. **唯一的认证实现**：只有 `src/domains/auth/` 存在认证代码
2. **最小化的FastAPI应用**：只暴露7个认证API + 3个系统端点
3. **干净的代码库**：无旧代码残留，无未使用的导入
4. **独立的认证领域**：Schema、Service、Repository都在 `src/domains/auth/` 内
5. **完整的测试覆盖**：所有测试通过，覆盖率>95%

## 暴露的API端点

### 认证端点 (7个)
- POST `/api/v1/auth/guest/init` - 游客账号初始化
- POST `/api/v1/auth/guest/upgrade` - 游客账号升级
- POST `/api/v1/auth/sms/send` - 发送短信验证码
- POST `/api/v1/auth/login` - 用户登录
- POST `/api/v1/auth/refresh` - 刷新访问令牌
- POST `/api/v1/auth/logout` - 用户登出
- GET `/api/v1/auth/user-info` - 获取用户信息

### 系统端点 (3个)
- GET `/` - 根路径
- GET `/health` - 健康检查
- GET `/api/v1/info` - API信息

### 文档端点 (3个)
- GET `/docs` - Swagger UI
- GET `/redoc` - ReDoc
- GET `/openapi.json` - OpenAPI规范

## 风险评估

1. **低风险**：删除旧代码不会影响现有功能（已使用新架构）
2. **中风险**：Schema迁移可能遗漏某些依赖（通过测试验证）
3. **可恢复**：所有更改都在git中，可随时回滚

## 时间估算

- 删除旧代码：30分钟
- Schema迁移：1小时
- 更新依赖和配置：30分钟
- 数据库重建：15分钟
- 测试验证：1小时
- **总计**: 约3小时

## 后续计划

清理完成后，可以按DDD架构逐步添加其他领域模块：
- User Domain (用户管理)
- Task Domain (任务管理)
- Focus Domain (专注系统)
- Chat Domain (AI对话)
- Reward Domain (奖励系统)
- Statistics Domain (统计分析)
