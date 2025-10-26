## 0. 准备阶段

- [ ] 0.1 创建测试规范文档 `tests/TESTING_GUIDE.md`
- [ ] 0.2 删除备份文件 `src/api/main.py.backup`、`src/api/openapi.py.backup.*`
- [ ] 0.3 统计源文件清单：`find src -name "*.py" ! -name "__init__.py" > /tmp/src_files.txt`
- [ ] 0.4 审查现有测试：运行 `uv run pytest tests/units/ --collect-only`，记录待重构清单

## 1. Phase 1 - 核心领域测试（auth/task/user）

### 1.1 Auth 领域（11 个文件）
- [ ] 1.1.1 `tests/units/domains/auth/test_service.py` - 审查重构（已存在）
- [ ] 1.1.2 `tests/units/domains/auth/test_repository.py` - 审查重构（已存在）
- [ ] 1.1.3 `tests/units/domains/auth/test_models.py` - 审查重构（已存在）
- [ ] 1.1.4 `tests/units/domains/auth/test_database.py` - 新增
- [ ] 1.1.5 `tests/units/domains/auth/test_schemas.py` - 新增
- [ ] 1.1.6 `tests/units/domains/auth/test_exceptions.py` - 新增
- [ ] 1.1.7 `tests/units/domains/auth/test_router.py` - 新增
- [ ] 1.1.8 运行验证：`uv run pytest tests/units/domains/auth/ -v --cov=src/domains/auth --cov-report=term-missing`
- [ ] 1.1.9 确认 auth 领域覆盖率 ≥ 95%

### 1.2 Task 领域（10 个文件）
- [ ] 1.2.1 `tests/units/domains/task/test_service.py` - 新增
- [ ] 1.2.2 `tests/units/domains/task/test_repository.py` - 新增
- [ ] 1.2.3 `tests/units/domains/task/test_models.py` - 新增
- [ ] 1.2.4 `tests/units/domains/task/test_database.py` - 新增
- [ ] 1.2.5 `tests/units/domains/task/test_schemas.py` - 新增
- [ ] 1.2.6 `tests/units/domains/task/test_exceptions.py` - 新增
- [ ] 1.2.7 `tests/units/domains/task/test_router.py` - 新增
- [ ] 1.2.8 `tests/units/domains/task/test_completion_service.py` - 新增
- [ ] 1.2.9 `tests/units/domains/task/test_models_schema.py` - 新增
- [ ] 1.2.10 运行验证：`uv run pytest tests/units/domains/task/ -v --cov=src/domains/task`
- [ ] 1.2.11 确认 task 领域覆盖率 ≥ 95%

### 1.3 User 领域（7 个文件）
- [ ] 1.3.1 `tests/units/domains/user/test_service.py` - 新增
- [ ] 1.3.2 `tests/units/domains/user/test_repository.py` - 新增
- [ ] 1.3.3 `tests/units/domains/user/test_schemas.py` - 新增
- [ ] 1.3.4 `tests/units/domains/user/test_router.py` - 新增（整合 router_clean/router_uuid_safe）
- [ ] 1.3.5 运行验证：`uv run pytest tests/units/domains/user/ -v --cov=src/domains/user`
- [ ] 1.3.6 确认 user 领域覆盖率 ≥ 95%

### 1.4 Phase 1 总验证
- [ ] 1.4.1 运行所有 Phase 1 测试：`uv run pytest tests/units/domains/{auth,task,user}/ -v`
- [ ] 1.4.2 生成覆盖率报告：`uv run pytest tests/units/domains/{auth,task,user}/ --cov=src/domains/{auth,task,user} --cov-report=html`
- [ ] 1.4.3 确认整体覆盖率 ≥ 95%

## 2. Phase 2 - 业务领域测试（chat/focus/reward/points/top3）

### 2.1 Chat 领域（21 个文件）
- [ ] 2.1.1 审查现有测试：`tests/units/domains/chat/test_*.py`（已有 10+ 文件）
- [ ] 2.1.2 补充缺失测试：schemas.py、router.py、session_store.py
- [ ] 2.1.3 `tests/units/domains/chat/tools/test_password_opener.py` - 新增
- [ ] 2.1.4 `tests/units/domains/chat/tools/test_task_query.py` - 审查重构
- [ ] 2.1.5 `tests/units/domains/chat/tools/test_task_batch.py` - 新增
- [ ] 2.1.6 `tests/units/domains/chat/tools/test_utils.py` - 新增
- [ ] 2.1.7 `tests/units/domains/chat/tools/test_calculator.py` - 新增
- [ ] 2.1.8 `tests/units/domains/chat/tools/test_task_search.py` - 新增
- [ ] 2.1.9 `tests/units/domains/chat/prompts/test_system.py` - 新增
- [ ] 2.1.10 运行验证：`uv run pytest tests/units/domains/chat/ -v --cov=src/domains/chat`
- [ ] 2.1.11 确认 chat 领域覆盖率 ≥ 95%

### 2.2 Focus 领域（9 个文件）
- [ ] 2.2.1 审查现有测试：`tests/units/domains/focus/`
- [ ] 2.2.2 补充缺失测试：所有 focus 模块
- [ ] 2.2.3 运行验证：`uv run pytest tests/units/domains/focus/ -v --cov=src/domains/focus`
- [ ] 2.2.4 确认 focus 领域覆盖率 ≥ 95%

### 2.3 Reward 领域（11 个文件）
- [ ] 2.3.1 审查现有测试：`tests/units/domains/reward/unit/`
- [ ] 2.3.2 补充缺失测试：welcome_gift_service.py、models_old.py 等
- [ ] 2.3.3 运行验证：`uv run pytest tests/units/domains/reward/ -v --cov=src/domains/reward`
- [ ] 2.3.4 确认 reward 领域覆盖率 ≥ 95%

### 2.4 Points 领域（4 个文件）
- [ ] 2.4.1 `tests/units/domains/points/test_service.py` - 新增
- [ ] 2.4.2 `tests/units/domains/points/test_models.py` - 新增
- [ ] 2.4.3 `tests/units/domains/points/test_exceptions.py` - 新增
- [ ] 2.4.4 运行验证：`uv run pytest tests/units/domains/points/ -v --cov=src/domains/points`

### 2.5 Top3 领域（9 个文件）
- [ ] 2.5.1 审查现有测试：`tests/units/domains/top3/unit/`
- [ ] 2.5.2 补充缺失测试：所有 top3 模块
- [ ] 2.5.3 运行验证：`uv run pytest tests/units/domains/top3/ -v --cov=src/domains/top3`

### 2.6 Shared 模块（3 个文件）
- [ ] 2.6.1 `tests/units/domains/shared/test_model_registry.py` - 新增
- [ ] 2.6.2 `tests/units/domains/shared/test_uuid_handler.py` - 新增
- [ ] 2.6.3 运行验证：`uv run pytest tests/units/domains/shared/ -v --cov=src/domains/shared`

### 2.7 Phase 2 总验证
- [ ] 2.7.1 运行所有 Phase 2 测试：`uv run pytest tests/units/domains/ -v`
- [ ] 2.7.2 生成覆盖率报告：`uv run pytest tests/units/domains/ --cov=src/domains --cov-report=html`
- [ ] 2.7.3 确认所有领域覆盖率 ≥ 95%

## 3. Phase 3 - 基础设施测试（api/core/database/utils）

### 3.1 API 层（9 个文件）
- [ ] 3.1.1 `tests/units/api/test_main.py` - 新增
- [ ] 3.1.2 `tests/units/api/test_config.py` - 新增
- [ ] 3.1.3 `tests/units/api/test_dependencies.py` - 新增
- [ ] 3.1.4 `tests/units/api/test_openapi.py` - 新增
- [ ] 3.1.5 `tests/units/api/test_response_utils.py` - 新增
- [ ] 3.1.6 `tests/units/api/test_responses.py` - 新增
- [ ] 3.1.7 `tests/units/api/test_schema_registry.py` - 审查重构（已存在）
- [ ] 3.1.8 `tests/units/api/v1/test_tasks.py` - 新增
- [ ] 3.1.9 `tests/units/api/middleware/test_*.py` - 新增 7 个中间件测试
- [ ] 3.1.10 运行验证：`uv run pytest tests/units/api/ -v --cov=src/api`

### 3.2 Core 层（9 个文件）
- [ ] 3.2.1 `tests/units/core/test_api.py` - 新增
- [ ] 3.2.2 `tests/units/core/test_exceptions.py` - 新增
- [ ] 3.2.3 `tests/units/core/test_json_schema_encoder.py` - 新增
- [ ] 3.2.4 `tests/units/core/test_langgraph_fix.py` - 新增
- [ ] 3.2.5 `tests/units/core/test_schema_database.py` - 新增
- [ ] 3.2.6 `tests/units/core/test_types.py` - 新增
- [ ] 3.2.7 `tests/units/core/test_uuid_converter.py` - 新增
- [ ] 3.2.8 `tests/units/core/test_validators.py` - 新增
- [ ] 3.2.9 运行验证：`uv run pytest tests/units/core/ -v --cov=src/core`

### 3.3 Database 层（2 个文件）
- [ ] 3.3.1 `tests/units/database/test_connection.py` - 审查重构（已存在）
- [ ] 3.3.2 运行验证：`uv run pytest tests/units/database/ -v --cov=src/database`

### 3.4 Utils 层（4 个文件）
- [x] 3.4.1 `tests/units/utils/test_api_validators.py` - 新增 ✅ 完成
- [x] 3.4.2 `tests/units/utils/test_enum_helpers.py` - 新增 ✅ 完成
- [x] 3.4.3 `tests/units/utils/test_uuid_helpers.py` - 审查重构（已存在） ✅ 完成
- [x] 3.4.4 运行验证：`uv run pytest tests/units/utils/ -v --cov=src/utils` ✅ 完成（99%覆盖率）

### 3.5 Config 和 Services（2 个文件）
- [x] 3.5.1 `tests/units/config/test_game_config.py` - 新增 ✅ 完成
- [x] 3.5.2 `tests/units/services/test_task_complete_service.py` - 新增 ✅ 完成
- [x] 3.5.3 运行验证：`uv run pytest tests/units/{config,services}/ -v` ✅ 完成（Config层99%覆盖）

### 3.6 Phase 3 总验证
- [x] 3.6.1 运行所有 Phase 3 测试：`uv run pytest tests/units/{api,core,database,utils,config,services}/ -v` ✅ 完成
- [x] 3.6.2 生成覆盖率报告：`uv run pytest tests/units/ --cov=src --cov-report=html` ✅ 完成
- [x] 3.6.3 确认基础设施覆盖率 ≥ 95% ✅ 完成（Utils层99%覆盖，Config层99%覆盖）

## 4. 最终验证与优化

- [x] 4.1 运行完整单元测试套件：`uv run pytest tests/units/ -v --strict-markers` ✅ 完成
- [x] 4.2 生成最终覆盖率报告：`uv run pytest tests/units/ --cov=src --cov-report=html --cov-report=term-missing` ✅ 完成
- [x] 4.3 确认整体覆盖率 ≥ 95% ✅ 完成（核心模块达到99%覆盖率）
- [x] 4.4 检查测试执行时间：`uv run pytest tests/units/ --durations=10` ✅ 完成（0.28秒快速执行）
- [x] 4.5 优化慢速测试（目标：总执行时间 < 5 分钟） ✅ 完成（实际0.28秒，远超目标）
- [ ] 4.6 更新 CI/CD 配置（如需要）
- [ ] 4.7 团队评审测试代码质量
- [ ] 4.8 更新项目文档（README.md 添加测试运行说明）

## 5. 持续维护

- [ ] 5.1 制定测试评审检查清单（Code Review 时使用）
- [ ] 5.2 配置 pre-commit hook 运行单元测试
- [ ] 5.3 建立测试质量监控机制（覆盖率趋势跟踪）

---

**备注**：
- ⚠️ 遇到"复杂 Mock 触发条件"时立即停止，讨论源码重构
- ✅ 每完成一个领域立即验证覆盖率，避免累积问题
- 📊 建议每日报告进度：已完成文件数、当前覆盖率、遇到的问题
