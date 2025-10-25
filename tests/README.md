# API测试使用指南

## 快速开始

### 1. 基础功能测试（30秒快速验证）
```bash
uv run python test_simple_coverage.py
```

### 2. 真实API环境测试
先启动服务器：
```bash
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8001
```

然后运行测试：
```bash
uv run python test_live_api.py
```

### 3. 完整测试套件（推荐）
```bash
uv run python run_api_tests.py
# 或者使用pytest
uv run pytest tests/ -m "api_coverage" --tb=short
```

### 4. 性能和并发测试
```bash
uv run pytest tests/performance/ -m "performance" --tb=short
```

## 测试覆盖范围

- ✅ **API端点全覆盖**：认证、任务、奖励、用户管理
- ✅ **欢迎礼包功能**：领取、历史、重复领取测试
- ✅ **错误场景**：401、404、500等全面覆盖
- ✅ **性能测试**：P95<200ms，并发10用户
- ✅ **数据持久化**：不隔离、不清理的端到端测试

## 预期结果

所有测试应该100%通过，确保零风险部署。如遇失败，检查：
1. API服务器是否正常运行
2. 数据库连接是否正常
3. 依赖包是否正确安装

---

**作者**：TaKeKe团队
**版本**：1.3.0
**最后更新**：2025年10月25日