# 实施任务清单

## 1. 数据库架构变更

### 1.1 创建数据迁移脚本
- [ ] 编写 Alembic 迁移脚本创建新的 `auth` 表
- [ ] 编写数据迁移脚本从 `auth_users` 表复制数据到 `auth` 表
- [ ] 编写脚本将用户资料数据（nickname, avatar, phone, email 等）导出到 CSV 文件（供 user 领域使用）
- [ ] 在迁移脚本中添加完整性检查，确保所有数据成功迁移

### 1.2 执行数据库迁移（测试环境）
- [ ] 在测试环境备份现有数据库
- [ ] 执行迁移脚本创建新表
- [ ] 执行数据迁移
- [ ] 验证数据完整性（行数、关键字段一致性）
- [ ] 测试新表的索引性能

### 1.3 清理旧表结构
- [ ] 标记旧表为 deprecated（添加注释）
- [ ] 在代码中移除对旧表的所有引用
- [ ] 准备旧表删除脚本（在生产环境运行 30 天后执行）

## 2. 数据模型层重构

### 2.1 更新 models.py
- [ ] 将 `User` 模型重命名为 `Auth` 模型
- [ ] 删除以下字段：`username`, `email`, `phone`, `password_hash`, `nickname`, `avatar`, `total_points`, `available_points`, `level`, `experience_points`, `device_id`, `device_type`, `wechat_unionid`
- [ ] 确保保留字段：`id`, `wechat_openid`, `is_guest`, `created_at`, `updated_at`, `last_login_at`, `jwt_version`
- [ ] 更新表名为 `auth`
- [ ] 更新索引定义：`idx_auth_wechat_openid`, `idx_auth_is_guest`, `idx_auth_created_at`
- [ ] 删除模型：`UserSettings`, `SMSVerification`, `TokenBlacklist`, `UserSession`
- [ ] 保留 `AuthLog` 模型（审计日志）

### 2.2 更新 database.py
- [ ] 更新数据库连接配置
- [ ] 删除已移除表的表定义
- [ ] 确保 `auth` 和 `auth_audit_logs` 表正确注册

## 3. Schema 层重构

### 3.1 更新请求 Schema
- [ ] 简化 `GuestInitRequest`：移除所有字段（或定义为空 schema）
- [ ] 创建 `WeChatRegisterRequest`：只包含 `wechat_openid` 字段
- [ ] 创建 `WeChatLoginRequest`：只包含 `wechat_openid` 字段
- [ ] 更新 `GuestUpgradeRequest`：只包含 `wechat_openid` 字段
- [ ] 保留 `TokenRefreshRequest`：只包含 `refresh_token` 字段
- [ ] 删除 `SMSCodeRequest`, `LoginRequest`（旧版）

### 3.2 更新响应 Schema
- [ ] 创建 `UnifiedResponse` 基础模型：`{ code: int, data: dict, message: str }`
- [ ] 更新 `AuthTokenResponse`：data 包含 `user_id`, `access_token`, `refresh_token`
- [ ] 删除 `UserInfoResponse`, `SMSCodeResponse`
- [ ] 删除 `BaseResponse`, `ErrorResponse`（使用新的 UnifiedResponse）

### 3.3 删除辅助 Schema
- [ ] 删除 `DeviceInfo` schema
- [ ] 删除 `UserProfile` schema
- [ ] 删除 `TokenInfo` schema
- [ ] 简化枚举：只保留 `UserTypeEnum`（guest/registered）

## 4. Repository 层重构

### 4.1 简化 AuthRepository
- [ ] 重命名方法：`get_user_by_*` → `get_by_wechat_openid`
- [ ] 删除方法：`get_user_by_phone`, `get_user_by_email`, `get_user_by_username`, `get_user_by_device`
- [ ] 简化 `create_user` 方法：只接受 `is_guest`, `wechat_openid` 参数
- [ ] 更新 `upgrade_guest_account` 方法：简化参数
- [ ] 删除 `update_user_last_login` 方法中对不存在字段的更新

### 4.2 删除不需要的 Repository
- [ ] 删除 `SMSRepository` 及其所有方法
- [ ] 删除 `TokenRepository` 及其所有方法
- [ ] 删除 `SessionRepository` 及其所有方法
- [ ] 保留 `AuditRepository`（审计日志）

## 5. Service 层重构

### 5.1 简化 AuthService
- [ ] 更新 `init_guest_account`：移除 device_info 参数，每次创建新游客
- [ ] 实现 `wechat_register`：创建游客 + 立即升级的组合逻辑
- [ ] 实现 `wechat_login`：验证 openid，返回 token
- [ ] 更新 `upgrade_guest_account`：简化为只需 user_id 和 wechat_openid
- [ ] 保留 `refresh_token`：无需修改
- [ ] 删除 `send_sms_code` 方法
- [ ] 删除 `logout` 方法
- [ ] 删除 `get_user_info` 方法

### 5.2 删除不需要的 Service
- [ ] 删除 `SMSService` 类
- [ ] 删除 `UserService` 类（用户管理移到 user 领域）
- [ ] 保留 `JWTService`：无需修改

### 5.3 添加代码注释说明
- [ ] 在 `wechat_register` 方法添加 docstring 说明其内部实现逻辑
- [ ] 在 router 的注册端点添加注释说明实现原理
- [ ] 在 design.md 中详细记录此设计决策

## 6. Router 层重构

### 6.1 更新认证端点
- [ ] 简化 `POST /api/v1/auth/guest/init`：无需请求体
- [ ] 创建 `POST /api/v1/auth/register`：接受 wechat_openid
- [ ] 创建 `POST /api/v1/auth/login`：接受 wechat_openid
- [ ] 更新 `POST /api/v1/auth/guest/upgrade`：简化请求体，只接受 wechat_openid
- [ ] 保留 `POST /api/v1/auth/refresh`：无需修改

### 6.2 删除端点
- [ ] 删除 `POST /api/v1/auth/sms/send`
- [ ] 删除 `POST /api/v1/auth/logout`
- [ ] 删除 `GET /api/v1/auth/user-info`

### 6.3 统一响应格式
- [ ] 更新所有端点使用 `UnifiedResponse` 格式
- [ ] 确保成功响应：`{ "code": 200, "data": {...}, "message": "success" }`
- [ ] 确保错误响应：`{ "code": 4xx/5xx, "data": null, "message": "错误描述" }`
- [ ] 移除 `create_error_response` 函数，直接返回统一格式

### 6.4 更新依赖注入
- [ ] 更新 `get_current_user_id` 依赖函数
- [ ] 移除 `get_client_info` 函数（不再需要设备信息）
- [ ] 简化错误处理逻辑

## 7. 响应格式中间件

### 7.1 更新 responses.py
- [ ] 创建 `unified_response()` 辅助函数
- [ ] 创建 `error_response()` 辅助函数
- [ ] 移除 timestamp 和 traceId 相关代码

### 7.2 更新 exception_handler.py
- [ ] 更新全局异常处理器使用新的响应格式
- [ ] 确保所有异常都返回统一格式

## 8. 异常处理更新

### 8.1 更新自定义异常
- [ ] 保留 `AuthenticationException`
- [ ] 保留 `UserNotFoundException`
- [ ] 保留 `TokenException`
- [ ] 保留 `ValidationError`
- [ ] 删除 `SMSException`

### 8.2 更新异常消息
- [ ] 统一错误消息为中文
- [ ] 确保错误消息清晰、用户友好

## 9. 测试重构

### 9.1 单元测试
- [ ] 重写 `test_service.py`：覆盖新的 AuthService 方法
- [ ] 重写 `test_repository.py`：覆盖简化后的 Repository
- [ ] 删除 `test_sms_service.py`
- [ ] 更新 `test_security.py`：JWT 测试
- [ ] 确保测试覆盖率 > 95%

### 9.2 集成测试
- [ ] 重写 `test_integration.py`：覆盖完整的认证流程
- [ ] 测试游客初始化 → 登录 → 升级流程
- [ ] 测试微信注册 → 登录流程
- [ ] 测试 token 刷新流程
- [ ] 测试各种错误场景

### 9.3 Router 测试
- [ ] 重写 `test_router.py`：覆盖所有 API 端点
- [ ] 测试响应格式统一性
- [ ] 测试错误响应格式
- [ ] 测试认证中间件

### 9.4 数据迁移测试
- [ ] 编写数据迁移测试脚本
- [ ] 验证迁移前后数据一致性
- [ ] 测试边界情况（空值、特殊字符等）

## 10. 文档更新

### 10.1 API 文档
- [ ] 更新 OpenAPI schema 定义
- [ ] 更新 FastAPI 自动生成的文档
- [ ] 为每个端点添加详细的请求/响应示例
- [ ] 添加错误码说明

### 10.2 代码注释
- [ ] 为所有公共方法添加 docstring
- [ ] 在关键设计决策处添加注释
- [ ] 在 `wechat_register` 方法注释中说明内部实现

### 10.3 迁移指南
- [ ] 编写客户端迁移指南（API 变更说明）
- [ ] 编写数据迁移操作手册
- [ ] 编写回滚操作手册

## 11. 部署准备

### 11.1 环境变量配置
- [ ] 确认 JWT_SECRET_KEY 配置
- [ ] 确认数据库连接字符串
- [ ] 移除 SMS 相关配置

### 11.2 数据库备份
- [ ] 在生产环境执行迁移前进行完整备份
- [ ] 验证备份可恢复性
- [ ] 准备快速回滚方案

### 11.3 监控和日志
- [ ] 配置新端点的监控指标
- [ ] 更新日志收集配置
- [ ] 设置错误告警阈值

## 12. 部署和验证

### 12.1 测试环境部署
- [ ] 部署到测试环境
- [ ] 执行数据库迁移
- [ ] 运行完整的测试套件
- [ ] 进行手动验证测试

### 12.2 生产环境部署
- [ ] 在维护窗口执行数据迁移
- [ ] 部署新版本后端
- [ ] 监控错误率和响应时间
- [ ] 验证关键功能正常

### 12.3 回滚准备
- [ ] 准备数据库回滚脚本
- [ ] 准备代码回滚方案
- [ ] 确认回滚触发条件

## 13. 后续清理

### 13.1 旧代码清理（30天后）
- [ ] 删除旧数据库表：`auth_users`, `auth_sms_verification`, `auth_token_blacklist`, `auth_user_sessions`, `auth_user_settings`
- [ ] 删除备份文件和迁移脚本
- [ ] 清理未使用的依赖

### 13.2 性能优化
- [ ] 分析新架构的性能瓶颈
- [ ] 优化数据库查询
- [ ] 调整缓存策略（如有需要）

## 验收标准

- ✅ 所有单元测试通过，覆盖率 > 95%
- ✅ 所有集成测试通过
- ✅ API 文档完整且准确
- ✅ 数据迁移成功，无数据丢失
- ✅ 所有端点响应格式统一
- ✅ 旧端点已删除，新端点正常工作
- ✅ 游客初始化、注册、登录、升级、刷新流程完整可用
- ✅ 生产环境部署成功，无重大错误
