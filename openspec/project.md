# TaKeKe Backend Project Context

## Purpose
TaKeKe Backend是一个基于DDD架构的现代化任务管理API系统，融合AI智能对话、番茄钟专注管理和积分奖励机制，为用户提供高效的任务管理和专注力提升解决方案。

## Tech Stack

### 核心框架
- **FastAPI 0.115+** - 现代高性能异步API框架，自动生成OpenAPI文档
- **SQLModel 0.0.27+** - 基于Pydantic的类型安全ORM，统一数据验证和序列化
- **SQLAlchemy 2.0+** - 异步数据库支持，支持复杂的查询和关系映射
- **aiosqlite** - 异步SQLite驱动，轻量级数据库解决方案

### AI/LangChain技术栈
- **LangGraph 1.0+** - 对话流程图管理，支持复杂的状态机逻辑
- **LangChain-Core** - LLM抽象层，支持多种AI模型提供商
- **LangChain-Anthropic/OpenAI** - Claude和GPT模型集成
- **LangGraph-Checkpoint-SQLite** - 对话状态持久化

### 安全认证
- **PyJWT 2.10+** - JWT令牌生成和验证
- **passlib + bcrypt** - 密码哈希和验证，BCrypt加密算法
- **python-jose** - JWT加密和解密支持

### 开发工具
- **pytest 8.4+** - 测试框架，支持异步测试
- **pytest-mock** - Mock对象和依赖注入测试
- **uvicorn** - ASGI服务器，支持热重载和性能监控
- **python-dotenv** - 环境变量管理

## Project Conventions

### Code Style
- **类型注解**：所有函数和方法使用完整的类型注解
- **文档字符串**：采用Google风格的docstring，包含参数、返回值和异常说明
- **命名规范**：
  - 类名：PascalCase（如 `FocusSession`）
  - 函数/变量：snake_case（如 `create_session`）
  - 常量：UPPER_SNAKE_CASE（如 `SessionTypeConst.FOCUS`）
- **导入顺序**：标准库 → 第三方库 → 本地模块，每组分隔空行

### Architecture Patterns
- **DDD六边形架构**：清晰的领域边界，每个领域独立包含models、repository、service、router
- **极简设计原则**：严格遵循KISS、YAGNI原则，避免过度设计
- **CQRS模式**：读写分离，Repository负责数据访问，Service负责业务逻辑
- **依赖注入**：通过FastAPI的dependency injection管理依赖关系
- **统一响应格式**：所有API返回 `{code, message, data}` 标准格式

### Testing Strategy
- **三层测试金字塔**：
  - 单元测试（70%）：Service和Repository层逻辑测试
  - 集成测试（20%）：API端点和数据库集成测试
  - 端到端测试（10%）：完整业务流程测试
- **测试覆盖率**：要求达到85%以上整体覆盖率
- **Mock策略**：外部依赖（如AI模型）使用Mock对象测试
- **测试数据管理**：使用pytest fixtures管理测试数据生命周期

### Git Workflow
- **分支策略**：
  - `main`：生产就绪代码
  - `develop`：开发集成分支
  - `feature/*`：功能开发分支
- **提交规范**：采用约定式提交格式（`feat:`, `fix:`, `docs:`, `test:`等）
- **代码审查**：所有功能分支必须经过代码审查才能合并
- **自动化测试**：CI/CD pipeline自动运行测试套件

## Domain Context

### 核心业务领域
1. **认证系统（Auth）**
   - 用户注册、登录、JWT令牌管理
   - 微信OpenID集成，支持第三方登录
   - 密码安全和会话管理

2. **任务管理（Task）**
   - 无限层级任务树结构，支持parent_id关系
   - 智能完成度计算（基于叶子节点统计）
   - 软删除机制和时间管理
   - 标签系统和优先级管理

3. **AI智能对话（Chat）**
   - 基于LangGraph的对话流程管理
   - 工具集成（计算器、密码生成器等）
   - 对话状态持久化和上下文管理
   - 支持多种AI模型（Claude、GPT等）

4. **番茄钟系统（Focus）**
   - 极简6字段设计，专注会话管理
   - 4种会话类型：focus/break/long_break/pause
   - 自动关闭机制和时段记录
   - 遵循Pomodoro Technique标准

5. **积分奖励系统（Points/Reward）**
   - 任务完成积分计算和事务管理
   - 奖励商品管理和兑换系统
   - 积分流水记录和余额统计
   - Top3任务特别奖励

6. **用户管理（User/Top3）**
   - 用户偏好设置和统计数据
   - Top3重要任务管理
   - 个人成就和进度跟踪

## Important Constraints

### 技术约束
- **数据库**：使用SQLite作为开发数据库，支持异步操作
- **API版本**：采用路径版本控制（`/api/v1/`）
- **响应格式**：严格遵循 `{code: int, message: str, data: dict}` 格式
- **错误处理**：统一的异常处理机制，详细的错误日志
- **性能要求**：API响应时间 < 200ms，支持并发访问

### 业务约束
- **时区处理**：所有时间字段使用UTC时区，前端负责时区转换
- **数据完整性**：严格的外键约束和级联删除策略
- **软删除**：重要数据采用软删除，保留数据完整性
- **幂等性**：所有API操作支持重复调用，数据状态一致

### 安全约束
- **认证**：所有业务API要求JWT令牌认证
- **授权**：基于用户ID的数据隔离，确保数据安全
- **数据验证**：使用Pydantic进行严格的输入验证
- **密码安全**：BCrypt哈希，最小密码强度要求

## External Dependencies

### AI服务依赖
- **Anthropic Claude API**：智能对话生成，支持上下文对话
- **OpenAI GPT API**：备选AI模型提供商，确保服务可用性
- **LangSmith**（可选）：对话质量监控和调试

### 系统依赖
- **Python 3.11+**：现代Python特性支持（async/await、类型注解等）
- **SQLite 3.x**：嵌入式数据库，无需额外配置
- **环境变量**：通过.env文件管理配置，支持多环境部署

### 运维依赖
- **Docker**：容器化部署，确保环境一致性
- **GitHub Actions**：CI/CD pipeline，自动化测试和部署
- **监控工具**：日志聚合和性能监控

---

**项目维护者**：TaKeKe团队
**最后更新**：2025年10月23日
**文档版本**：v1.0.0