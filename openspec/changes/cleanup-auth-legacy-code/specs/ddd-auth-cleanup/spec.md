# ddd-auth-cleanup Specification

## Purpose
清理旧的认证系统实现，统一使用DDD领域驱动架构，确保系统中只有一个认证代码路径，提升代码可维护性和系统架构清晰度。

## ADDED Requirements

### Requirement: DDD Auth Domain Independence
系统 SHALL确保认证领域完全自包含，所有认证相关代码都在 `src/domains/auth/` 目录下。

#### Scenario: Auth Schema Self-Containment
- **GIVEN** 认证领域需要使用请求/响应Schema
- **WHEN** 实现认证API时
- **THEN** 系统 SHALL在 `src/domains/auth/schemas.py` 中定义所有认证Schema
- **AND** Schema SHALL只包含7个认证API所需的最小集合
- **AND** Schema SHALL不依赖 `src/api/schemas/` 中的任何定义

#### Scenario: No External Auth Dependencies
- **GIVEN** 认证领域的完整性要求
- **WHEN** 检查认证领域代码时
- **THEN** 系统 SHALL NOT在 `src/domains/auth/` 外部依赖任何认证相关代码
- **AND** 所有import SHALL限定在领域内部（如 `from .schemas import ...`）
- **AND** 认证领域 SHALL可以独立测试和部署

### Requirement: Legacy Code Removal
系统 SHALL完全删除旧的认证实现代码，防止代码冗余和维护混乱。

#### Scenario: Old Auth Router Removal
- **GIVEN** 存在旧的认证路由 `src/api/routers/auth.py`
- **WHEN** 执行清理任务时
- **THEN** 系统 SHALL删除 `src/api/routers/auth.py` 文件
- **AND** 系统 SHALL NOT在代码库中保留任何备份或注释掉的旧路由代码

#### Scenario: Old Auth Service Removal
- **GIVEN** 存在旧的认证服务文件
- **WHEN** 执行清理任务时
- **THEN** 系统 SHALL删除以下文件：
  - `src/services/async_auth_service.py`
  - `src/services/auth_service.py` (如果存在)
- **AND** 系统 SHALL确保没有其他代码引用这些服务

#### Scenario: Old Auth Repository Removal
- **GIVEN** 存在旧的认证仓库 `src/repositories/async_auth.py`
- **WHEN** 执行清理任务时
- **THEN** 系统 SHALL删除该文件
- **AND** 系统 SHALL更新所有依赖该仓库的代码

#### Scenario: Old Schema Files Removal
- **GIVEN** 存在包含认证Schema的旧文件
- **WHEN** 执行清理任务时
- **THEN** 系统 SHALL删除以下文件：
  - `src/api/schemas/auth.py`
  - `src/api/schemas.py` (如果主要用于认证)
- **AND** 系统 SHALL创建新的独立Schema文件在认证领域内

### Requirement: Dependency Injection Cleanup
系统 SHALL从全局依赖注入系统中移除所有旧认证相关的依赖。

#### Scenario: Remove Legacy Auth Service Dependencies
- **GIVEN** `src/api/dependencies.py` 包含旧认证服务的依赖
- **WHEN** 清理依赖注入系统时
- **THEN** 系统 SHALL删除以下导入：
  - `from src.services.async_auth_service import AsyncAuthService`
  - `from src.services import AuthService`
- **AND** 系统 SHALL删除以下依赖函数：
  - `get_async_auth_service()`
  - `get_auth_service()`

#### Scenario: Cleanup ServiceFactory Auth Methods
- **GIVEN** `ServiceFactory` 类包含旧认证服务的工厂方法
- **WHEN** 清理ServiceFactory时
- **THEN** 系统 SHALL删除以下方法：
  - `get_async_auth_repository()`
  - `get_async_auth_service()`
  - `get_auth_service()` (如果存在)
- **AND** 系统 SHALL保留其他服务的工厂方法

### Requirement: Non-Auth Router Isolation
系统 SHALL注释掉所有非认证模块的路由注册，确保FastAPI只暴露认证端点。

#### Scenario: Comment Out Non-Auth Router Imports
- **GIVEN** `src/api/main.py` 导入了多个路由模块
- **WHEN** 隔离认证路由时
- **THEN** 系统 SHALL注释掉以下导入：
  ```python
  # from src.api.routers import user, tasks, chat, focus, rewards_new, statistics_new
  ```
- **AND** 系统 SHALL保留认证路由导入：
  ```python
  from src.domains.auth.router import router as auth_router
  ```

#### Scenario: Comment Out Non-Auth Router Registrations
- **GIVEN** `src/api/main.py` 注册了多个路由
- **WHEN** 隔离认证路由时
- **THEN** 系统 SHALL只保留认证路由注册：
  ```python
  app.include_router(auth_router, prefix=config.api_prefix, tags=["认证系统"])
  ```
- **AND** 系统 SHALL注释掉所有其他路由注册
- **AND** 注释 SHALL包含说明信息："等待DDD架构实现"

### Requirement: API Info Endpoint Accuracy
系统 SHALL更新API信息端点，准确反映当前只有认证系统可用。

#### Scenario: Update Endpoint Statistics
- **GIVEN** `/api/v1/info` 端点显示所有模块的端点统计
- **WHEN** 更新API信息时
- **THEN** 系统 SHALL只显示认证系统的端点数量：
  ```json
  {
    "endpoints": {
      "认证系统": 7
    },
    "total_endpoints": 7
  }
  ```
- **AND** 系统 SHALL添加状态说明："认证领域已完成，其他领域开发中"

#### Scenario: Accurate Documentation Links
- **GIVEN** API信息端点需要提供文档链接
- **WHEN** 返回API信息时
- **THEN** 系统 SHALL包含完整的文档链接：
  - Swagger UI: `/docs`
  - ReDoc: `/redoc`
  - OpenAPI规范: `/openapi.json`

### Requirement: Database Rebuild
系统 SHALL重建数据库，清空所有旧数据，确保干净的开发环境。

#### Scenario: Backup Existing Databases
- **GIVEN** 存在 `tatake.db` 和 `tatake_auth.db` 数据库文件
- **WHEN** 重建数据库前
- **THEN** 系统 SHOULD提供备份选项
- **AND** 备份文件 SHALL使用时间戳命名：`*.db.backup.YYYYMMDD_HHMMSS`

#### Scenario: Delete Old Database Files
- **GIVEN** 需要清空所有数据
- **WHEN** 执行数据库重建时
- **THEN** 系统 SHALL删除以下文件：
  - `tatake.db`, `tatake.db-shm`, `tatake.db-wal`
  - `tatake_auth.db`, `tatake_auth.db-shm`, `tatake_auth.db-wal`

#### Scenario: Initialize Auth Database
- **GIVEN** 认证数据库已删除
- **WHEN** 应用启动时
- **THEN** 系统 SHALL自动创建 `tatake_auth.db`
- **AND** 系统 SHALL创建以下表结构：
  - `users` - 用户表
  - `sms_verifications` - 短信验证码表
  - `token_blacklist` - 令牌黑名单表
  - `user_sessions` - 用户会话表
  - `auth_logs` - 认证日志表
- **AND** 所有表 SHALL包含正确的索引和外键约束

### Requirement: Test-Driven Validation
系统 SHALL在每个清理阶段完成后运行测试，确保100%通过才继续下一阶段。

#### Scenario: Phase 1 - Delete Old Files Test
- **GIVEN** 旧认证文件已删除
- **WHEN** 运行测试时
- **THEN** 测试 SHALL失败并显示import错误
- **AND** 错误信息 SHALL明确指出缺少的模块

#### Scenario: Phase 2 - Schema Migration Test
- **GIVEN** 新的Schema文件已创建并更新import
- **WHEN** 运行认证测试时
- **THEN** 所有Schema相关测试 SHALL 100%通过
- **AND** Schema验证器 SHALL正常工作
- **AND** Request/Response模型 SHALL正确序列化

#### Scenario: Phase 3 - Dependency Injection Test
- **GIVEN** 依赖注入系统已清理
- **WHEN** 运行路由和集成测试时
- **THEN** 认证API SHALL正常工作
- **AND** 测试 SHALL NOT依赖全局依赖注入系统

#### Scenario: Phase 4 - Router Isolation Test
- **GIVEN** 非认证路由已注释
- **WHEN** 启动FastAPI服务时
- **THEN** Swagger UI SHALL只显示7个认证端点
- **AND** 访问注释掉的路由 SHALL返回404错误

#### Scenario: Phase 5 - Database Rebuild Test
- **GIVEN** 数据库已重建
- **WHEN** 运行数据库测试时
- **THEN** Repository层测试 SHALL 100%通过
- **AND** 数据库表结构 SHALL正确
- **AND** CRUD操作 SHALL正常工作

#### Scenario: Phase 6 - Final Integration Test
- **GIVEN** 所有清理任务已完成
- **WHEN** 运行完整测试套件时
- **THEN** 所有测试 SHALL 100%通过
- **AND** 测试覆盖率 SHALL > 95%
- **AND** 无任何警告或错误

### Requirement: Minimal Schema Design
系统 SHALL创建最小化的Schema集合，只包含7个认证API真正需要的定义。

#### Scenario: Request Schema Completeness
- **GIVEN** 7个认证API端点
- **WHEN** 设计Schema时
- **THEN** 系统 SHALL提供以下请求Schema：
  - `GuestInitRequest` - 游客初始化请求
  - `GuestUpgradeRequest` - 游客升级请求
  - `SMSCodeRequest` - 短信验证码请求
  - `LoginRequest` - 登录请求
  - `TokenRefreshRequest` - 令牌刷新请求
  - `LogoutRequest` - 登出请求（可选）
- **AND** 每个Schema SHALL包含完整的字段验证
- **AND** 每个Schema SHALL包含详细的docstring

#### Scenario: Response Schema Uniformity
- **GIVEN** 需要统一的响应格式
- **WHEN** 设计响应Schema时
- **THEN** 系统 SHALL提供以下响应Schema：
  - `BaseResponse` - 基础响应（success, message, data, timestamp）
  - `ErrorResponse` - 错误响应
  - `AuthTokenResponse` - 认证令牌响应（用于init/upgrade/login/refresh）
  - `UserInfoResponse` - 用户信息响应
- **AND** 所有响应 SHALL继承或使用统一的基础结构

#### Scenario: Helper Schema Minimalism
- **GIVEN** 需要辅助数据结构
- **WHEN** 设计辅助Schema时
- **THEN** 系统 SHALL只包含必需的辅助Schema：
  - `DeviceInfo` - 设备信息
  - `TokenInfo` - 令牌信息
  - `UserProfile` - 用户资料
- **AND** 系统 SHALL NOT包含其他模块的兼容性Schema

### Requirement: FastAPI Application Minimalism
系统 SHALL确保FastAPI应用只暴露认证端点和系统端点。

#### Scenario: Exposed Endpoints Count
- **GIVEN** FastAPI应用启动后
- **WHEN** 查看API端点列表时
- **THEN** 系统 SHALL暴露以下端点：
  - 认证端点: 7个
  - 系统端点: 3个 (/, /health, /api/v1/info)
  - 文档端点: 3个 (/docs, /redoc, /openapi.json)
- **AND** 总端点数 SHALL为13个

#### Scenario: Swagger UI Verification
- **GIVEN** Swagger UI可访问
- **WHEN** 用户访问 `/docs` 时
- **THEN** Swagger UI SHALL只显示以下API分组：
  - "系统" - 包含根路径、健康检查、API信息
  - "认证系统" - 包含7个认证端点
- **AND** Swagger UI SHALL NOT显示其他业务模块的端点

### Requirement: Code Quality Standards
系统 SHALL确保清理后的代码符合高质量标准。

#### Scenario: No Unused Imports
- **GIVEN** 代码清理完成
- **WHEN** 运行代码质量检查时
- **THEN** 系统 SHALL NOT包含未使用的import
- **AND** 所有import SHALL是必需的

#### Scenario: No Commented Code Clutter
- **GIVEN** 清理完成后
- **WHEN** 检查代码库时
- **THEN** 系统 SHALL NOT包含大段注释掉的旧代码
- **AND** 注释 SHALL只用于说明和文档目的

#### Scenario: Test Coverage Requirement
- **GIVEN** 认证领域的测试套件
- **WHEN** 运行覆盖率检查时
- **THEN** 总体覆盖率 SHALL > 95%
- **AND** Repository层覆盖率 SHALL = 100%
- **AND** Service层覆盖率 SHALL > 95%
- **AND** Router层覆盖率 SHALL > 95%

## MODIFIED Requirements

### Requirement: API Layer Foundation (from api-layer-architecture)
系统 SHALL更新API层基础架构，移除对旧认证模块的引用。

#### Scenario: Dependencies Module Update
- **GIVEN** `src/api/dependencies.py` 包含所有服务的依赖注入
- **WHEN** 清理认证依赖时
- **THEN** 系统 SHALL保留其他服务的依赖（UserService, TaskService等）
- **AND** 系统 SHALL删除旧认证服务的依赖
- **BUT** 系统 SHALL保持依赖注入系统的整体结构不变

#### Scenario: Main Application Router Registration
- **GIVEN** `src/api/main.py` 注册多个路由模块
- **WHEN** 更新路由注册时
- **THEN** 系统 SHALL注释非认证路由但保持代码可读性
- **AND** 系统 SHALL添加清晰的注释说明为何注释
- **AND** 系统 SHALL保持main.py的整体结构不变

## REMOVED Requirements

### Requirement: Legacy Auth Service Layer
系统 SHALL移除旧的认证服务层实现。

#### Scenario: AsyncAuthService Removal
- **GIVEN** 存在 `AsyncAuthService` 类
- **WHEN** 删除旧代码时
- **THEN** 系统 SHALL完全删除该类及其所有方法
- **AND** 系统 SHALL删除该服务的所有测试文件（如果独立存在）

#### Scenario: Legacy Auth Repository Removal
- **GIVEN** 存在旧的认证Repository实现
- **WHEN** 删除旧代码时
- **THEN** 系统 SHALL删除 `AsyncAuthRepository` 及其相关代码
- **AND** 系统 SHALL确保没有破坏其他Repository的功能

### Requirement: Shared Schema Layer
系统 SHALL移除共享的Schema层（`src/api/schemas/`），改用领域内Schema。

#### Scenario: Centralized Auth Schema Removal
- **GIVEN** 存在 `src/api/schemas/auth.py` (1177行)
- **WHEN** 采用DDD架构时
- **THEN** 系统 SHALL删除该文件
- **AND** 系统 SHALL创建领域专属的最小Schema替代
- **AND** 新Schema SHALL不超过500行（仅包含必需定义）

## Notes
本规范定义了从传统三层架构迁移到DDD领域驱动架构的清理过程。核心原则是：
1. **彻底性**: 完全删除旧代码，不留残留
2. **独立性**: 认证领域完全自包含
3. **可测试性**: 每个阶段都有测试验证
4. **最小化**: 只保留必需的代码和功能
5. **可回滚性**: 所有操作都可通过git回滚

清理后，系统将只有一个认证实现路径，为后续其他领域的DDD架构迁移奠定基础。
