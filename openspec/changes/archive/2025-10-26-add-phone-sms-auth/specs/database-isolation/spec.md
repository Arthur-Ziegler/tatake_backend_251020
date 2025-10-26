# 认证数据库独立化规格

## MODIFIED Requirements

### Requirement: 数据库路径迁移至data目录
认证数据库 MUST 从 `tatake_auth.db` 迁移至 `data/auth.db`。

#### Scenario: 新环境初始化使用新路径
- **Given**: 全新环境，未创建数据库
- **When**: 调用 `create_tables()`
- **Then**:
  - 在 `data/auth.db` 创建数据库文件
  - 不在项目根目录创建 `tatake_auth.db`

#### Scenario: 环境变量配置新路径
- **Given**: `.env` 设置 `AUTH_DATABASE_URL=sqlite:///./data/auth.db`
- **When**: 启动应用
- **Then**:
  - `auth_engine` 连接到 `data/auth.db`
  - `get_database_info()` 返回正确路径

#### Scenario: data目录不存在时自动创建
- **Given**: 项目根目录下不存在 `data/` 目录
- **When**: 首次调用 `create_tables()`
- **Then**:
  - 自动创建 `data/` 目录
  - 在其中创建 `auth.db` 文件

#### Scenario: 数据库路径在健康检查中反映
- **Given**: 数据库连接正常
- **When**: 调用 `auth_db_manager.health_check()`
- **Then**: 返回 `{"connected": True, "path": "data/auth.db"}`

---

### Requirement: 数据库表结构独立性
Auth数据库 MUST 只包含auth和sms_verification表，SHALL NOT 依赖其他领域表。

#### Scenario: 创建Auth数据库表
- **Given**: 空数据库
- **When**: 调用 `create_tables()`
- **Then**:
  - 创建 `auth` 表（8个字段）
  - 创建 `auth_audit_logs` 表
  - 创建 `sms_verification` 表（10个字段）
  - 不创建其他领域表（task, chat等）

#### Scenario: 验证表结构独立性
- **Given**: Auth数据库已创建
- **When**: 调用 `auth_db_manager.verify_simplified_structure()`
- **Then**:
  - `auth_table_valid=True`（包含phone字段）
  - `auth_log_table_valid=True`
  - `sms_table_valid=True`
  - 不存在其他领域的外键关联

#### Scenario: 独立数据库连接管理
- **Given**: 应用同时使用 auth 和 task 数据库
- **When**:
  - `with get_auth_db() as auth_session`
  - `with get_task_db() as task_session`
- **Then**:
  - 两个session连接不同数据库文件
  - 事务相互独立

---

### Requirement: 数据库文件组织规范
所有领域数据库文件 SHALL 统一存放在data目录。

#### Scenario: data目录结构清晰
- **Given**: 项目完整运行
- **When**: 执行 `ls data/`
- **Then**: 显示
  ```
  data/
  ├── auth.db
  ├── chat.db
  ├── task.db (未来)
  ├── focus.db (未来)
  ```

#### Scenario: 数据库文件与领域对应
- **Given**: 查看 `data/` 目录
- **When**: 每个数据库文件名
- **Then**:
  - `auth.db` - 认证领域
  - `chat.db` - 对话领域
  - 文件名与领域目录 `src/domains/auth` 一致

---

## ADDED Requirements

### Requirement: SMSVerification表创建与索引
系统 MUST 新增短信验证码专用表，SHALL 创建索引以支持高效查询。

#### Scenario: SMSVerification表字段完整
- **Given**: 执行数据库迁移
- **When**: 检查表结构
- **Then**: 包含字段
  - `id` (主键)
  - `phone` (索引)
  - `code` (6位)
  - `scene` (register/login/bind)
  - `created_at`
  - `verified`
  - `verified_at`
  - `ip_address`
  - `error_count`
  - `locked_until`

#### Scenario: 复合索引支持高效查询
- **Given**: 表中有1000条验证码记录
- **When**: 查询 `SELECT * FROM sms_verification WHERE phone='13800138000' AND scene='login' AND verified=False ORDER BY created_at DESC LIMIT 1`
- **Then**:
  - 使用索引 `idx_sms_phone_scene`
  - 查询时间 < 5ms

#### Scenario: 锁定状态索引优化
- **Given**: 需要查询当前锁定的手机号
- **When**: 查询 `SELECT phone FROM sms_verification WHERE locked_until > NOW()`
- **Then**: 使用索引 `idx_sms_locked_until`

---

### Requirement: 数据库健康检查增强
健康检查 MUST 包含SMS表验证。

#### Scenario: 健康检查覆盖新表
- **Given**: Auth数据库完整初始化
- **When**: 调用 `auth_db_manager.health_check()`
- **Then**: 返回
  ```json
  {
    "status": "healthy",
    "tables": {
      "auth": true,
      "auth_audit_logs": true,
      "sms_verification": true
    }
  }
  ```

#### Scenario: SMS表缺失时健康检查失败
- **Given**: 数据库只创建了auth表，未创建sms_verification
- **When**: 调用 `health_check()`
- **Then**:
  - `status="unhealthy"`
  - `tables.sms_verification=false`
