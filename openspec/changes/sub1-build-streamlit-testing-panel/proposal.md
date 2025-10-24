# Proposal: Streamlit 测试面板基础架构

## 目的
构建 Streamlit 测试面板的基础架构，提供 API 客户端封装、状态管理和认证系统，为后续业务页面提供测试基础设施。

## Why
测试面板需要统一的基础设施来管理 API 调用、Token 认证和数据状态。通过先实现基础架构，可以：确保 API 客户端自动注入 JWT Token、统一管理 session_state 数据缓存、提供认证页面获取测试 Token。这样后续的任务流程和独立功能提案可以完全并行开发，无需重复实现基础代码。

## What Changes

### 包含功能
1. **Streamlit 项目结构**：创建 `streamlit_app/` 目录和基础文件
2. **API 客户端封装**：自动注入 Token 的 HTTP 客户端
3. **状态管理器**：session_state 初始化和数据管理
4. **认证系统页面**：游客初始化、登录、刷新 Token
5. **通用组件**：JSON 查看器、错误处理、刷新按钮

### 不包含
- 业务页面（任务、聊天、奖励等）
- 复杂的数据可视化

## 影响

### 受益方
- **提案 2.1 和 2.2**：复用基础架构，快速实现业务页面

### 技术影响
- 新增 Streamlit 依赖（`streamlit>=1.28.0`）
- 新增 `streamlit_app/` 目录和核心模块

## 依赖关系
- **被依赖**：提案 2.1 和 2.2 必须在本提案完成后才能开始

## 关联规格
- `streamlit-foundation`：基础架构核心规格

## 验收标准
1. ✅ 运行 `uv run streamlit run streamlit_app/main.py` 成功启动
2. ✅ 认证页面可以获取 Token 并存入 session_state
3. ✅ API 客户端自动注入 Token 到请求头
4. ✅ 通用组件（JSON 查看器、错误处理）可复用
