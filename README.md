# TaKeKe Backend

基于 DDD 架构的现代化 API 后端服务，集成 AI 聊天功能。

## 📁 项目结构

```
src/
├── api/           # API层 - FastAPI Web框架
├── domains/       # 领域层 - 业务逻辑核心
├── database/      # 数据库层 - 多数据库架构
├── config/        # 配置层 - 环境和应用配置

docs/              # 项目文档
openspec/          # OpenSpec 规格管理
tests/             # API测试和集成测试
```

## 🛠️ 技术栈

- **FastAPI** - 高性能异步API框架
- **SQLModel** - 结合 Pydantic 的 ORM
- **SQLite** - 轻量级数据库
- **Pydantic** - 数据验证和序列化
- **Python 3.11+** - 现代 Python 版本

## 🚀 快速开始

### 环境要求
- Python 3.11+
- uv 包管理器

### 安装依赖
```bash
uv sync
```

### 启动服务

1. **启动 API 服务器**
   ```bash
   uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
   ```

### 运行测试
```bash
uv run pytest
```

## 🎯 核心功能

- **用户认证** - JWT令牌认证系统
- **任务管理** - CRUD操作和状态管理
- **番茄时钟** - 专注时间管理
- **积分系统** - 游戏化激励机制
- **排行榜** - Top3竞争系统
- **AI聊天** - LangGraph智能对话

## 📚 文档

- API规格文档：`openspec/specs/`
- 变更提案：`openspec/changes/`
- 完整API文档：`docs/TaKeKe_API方案_v3.md`

## 🔧 开发指南

### 项目架构
- 采用 Domain-Driven Design (DDD) 架构
- 多数据库设计（认证、任务、聊天分离）
- 异步编程提升性能
- 完整的测试覆盖（95%+）

### 代码规范
- 使用 Black 进行代码格式化
- 使用 MyPy 进行类型检查
- 遵循 PEP 8 编码规范
- 完整的文档字符串

---

**版本**: v3.0.0
**最后更新**: 2025-10-25
**维护团队**: TaKeKe 开发团队