# Tasks: 1.4.3-api-coverage-quality-assurance

## 概述

本阶段实施**100% API端点覆盖率 + 全面质量保障体系**，包括端点覆盖、性能基准、并发测试、边界测试四个维度。

**前置依赖**：
- ✅ 阶段1 (1.4.1) 已完成：真实HTTP测试框架已就绪
- ✅ 阶段2 (1.4.2) 已完成：UUID类型系统已统一，P1 bug已修复

**预计工时**：约18-22小时（3-4个工作日）

## Phase 3.1: 测试工具库实现（4小时）

### Task 3.1.1: 实现端点发现工具 (1.5小时)

**文件**：`tests/tools/endpoint_discovery.py`

**实现内容**：
1. 创建 `EndpointDiscovery` 类
   - `get_all_endpoints()`: 扫描FastAPI路由，提取所有端点
   - `get_tested_endpoints()`: 解析测试代码，查找已测试端点
   - `generate_coverage_report()`: 生成覆盖率报告
   - `_calculate_domain_coverage()`: 按域统计覆盖率

2. 创建 `HTTPCallVisitor` AST访问者
   - 实现 `visit_Call()`: 识别 client.get/post/put/delete/patch 调用
   - 提取URL参数（字符串字面量和f-string）
   - 处理路径参数占位符

**验证步骤**：
```bash
# 创建测试工具目录
mkdir -p tests/tools

# 实现端点发现工具
# （编写代码）

# 测试端点发现功能
uv run python -c "
from src.api.main import app
from tests.tools.endpoint_discovery import EndpointDiscovery

discovery = EndpointDiscovery(app)
report = discovery.generate_coverage_report()
print(f'Total endpoints: {report[\"total\"]}')
print(f'Coverage: {report[\"coverage_rate\"]:.1%}')
"
```

**完成标准**：
- [x] `EndpointDiscovery` 类能正确扫描所有FastAPI路由
- [x] AST解析能识别测试代码中的HTTP调用
- [x] 覆盖率报告包含总数、已测试数、按域分组统计

---

### Task 3.1.2: 实现性能追踪器 (1小时)

**文件**：`tests/tools/performance_tracker.py`

**实现内容**：
1. 创建 `PerformanceStats` dataclass
   - 字段：p50, p95, p99, min, max, mean, count, timestamp

2. 创建 `PerformanceTracker` 类
   - `measure()`: 测量函数执行时间（使用 perf_counter）
   - `get_statistics()`: 计算统计数据（使用 statistics 库）
   - `compare_with_baseline()`: 与基准对比，检测回归
   - `load_baseline()` / `save_baseline()`: 基准数据持久化

3. 创建 `perf_tracker` pytest fixture

**验证步骤**：
```bash
# 实现性能追踪器
# （编写代码）

# 测试性能测量
uv run python -c "
import time
from tests.tools.performance_tracker import PerformanceTracker

tracker = PerformanceTracker()
for _ in range(10):
    tracker.measure(time.sleep, 0.01)

stats = tracker.get_statistics()
print(f'P50: {stats.p50:.2f}ms')
print(f'P95: {stats.p95:.2f}ms')
"
```

**完成标准**：
- [x] 性能测量精确（使用 perf_counter）
- [x] 统计计算正确（P50/P95/P99）
- [x] 基准对比功能正常（20%阈值）
- [x] 基准数据持久化到 `tests/reports/performance_baseline.json`

---

### Task 3.1.3: 实现并发测试工具 (1小时)

**文件**：`tests/tools/concurrent_tester.py`

**实现内容**：
1. 创建 `ConcurrentResult` dataclass
   - 字段：success_count, error_count, status_codes, errors, durations, latency统计

2. 创建 `ConcurrentTester` 类
   - `run_concurrent_requests()`: 执行并发请求（asyncio + httpx）
   - `_aggregate_results()`: 聚合并发结果
   - `run_concurrent_scenarios()`: 支持多场景并发

**验证步骤**：
```bash
# 实现并发测试工具
# （编写代码）

# 测试并发功能（需要先启动HTTP服务器）
uv run python -c "
import asyncio
from tests.tools.concurrent_tester import ConcurrentTester

async def test():
    tester = ConcurrentTester('http://localhost:8099')
    result = await tester.run_concurrent_requests(
        method='GET',
        path='/docs',
        repeat=10
    )
    print(f'Success: {result.success_count}')
    print(f'P95 latency: {result.p95_latency:.2f}ms')

asyncio.run(test())
"
```

**完成标准**：
- [x] asyncio + httpx 实现真实并发（非线程池）
- [x] 结果聚合包含成功率、状态码分布、延迟统计
- [x] 支持混合场景的并发测试

---

### Task 3.1.4: 实现边界用例生成器 (0.5小时)

**文件**：`tests/tools/edge_case_generator.py`

**实现内容**：
创建 `EdgeCaseGenerator` 类，包含静态方法：
- `invalid_uuids()`: 无效UUID列表（SQL注入、XSS、格式错误等）
- `boundary_integers()`: 边界整数（0, 负数, INT_MAX, 溢出值）
- `boundary_strings()`: 边界字符串（空、超长、Unicode、特殊字符、攻击向量）
- `boundary_dates()`: 边界日期（过去、未来、无效日期）
- `attack_vectors()`: 常见攻击向量分类

**验证步骤**：
```bash
# 实现边界用例生成器
# （编写代码）

# 测试用例生成
uv run python -c "
from tests.tools.edge_case_generator import EdgeCaseGenerator

print('Invalid UUIDs:', len(EdgeCaseGenerator.invalid_uuids()))
print('Boundary strings:', len(EdgeCaseGenerator.boundary_strings()))
print('Attack vectors:', len(EdgeCaseGenerator.attack_vectors()))
"
```

**完成标准**：
- [x] 每个类别至少包含8-10个测试用例
- [x] 用例包含描述字段（desc）便于测试输出
- [x] 覆盖常见的安全攻击向量（SQL注入、XSS、路径遍历）

---

## Phase 3.2: 100%端点覆盖测试（8小时）

### Task 3.2.1: Task域完整端点测试 (2小时)

**文件**：`tests/e2e/test_task_endpoints.py`

**实现内容**：
测试所有Task域端点（约15个端点）：
1. `GET /tasks` - 列出所有任务（过滤已删除）
2. `POST /tasks/create` - 创建任务
3. `PATCH /tasks/{task_id}/complete` - 完成任务（验证Bug #1修复：请求体可选）
4. `PATCH /tasks/{task_id}/uncomplete` - 取消完成
5. `PUT /tasks/{task_id}` - 更新任务内容
6. `DELETE /tasks/{task_id}` - 软删除任务
7. 权限控制测试：跨用户访问拒绝

**验证步骤**：
```bash
# 实现测试
# （编写代码）

# 运行Task域测试
uv run pytest tests/e2e/test_task_endpoints.py -v

# 验证覆盖
uv run python -c "
from src.api.main import app
from tests.tools.endpoint_discovery import EndpointDiscovery

discovery = EndpointDiscovery(app)
report = discovery.generate_coverage_report()
task_coverage = report['by_domain'].get('tasks', {})
print(f'Task domain coverage: {task_coverage.get(\"coverage_rate\", 0):.1%}')
"
```

**完成标准**：
- [x] Task域所有端点都有对应测试
- [x] 每个端点至少测试3种场景：正常、权限、数据验证
- [x] Bug #1修复验证通过（请求体可选）
- [x] 所有测试使用真实HTTP服务器（real_api_client）

---

### Task 3.2.2: Points域完整端点测试 (1小时)

**文件**：`tests/e2e/test_points_endpoints.py`

**实现内容**：
测试所有Points域端点（3个端点）：
1. `GET /points/my-points` - 获取积分余额（验证Bug #3修复：正确路径 + UUID处理）
2. `GET /points/transactions` - 获取交易历史（分页测试）
3. 验证 `/points/balance` 端点不存在（错误路径已删除）

**验证步骤**：
```bash
# 运行Points域测试
uv run pytest tests/e2e/test_points_endpoints.py -v

# 验证正确路径
uv run python -c "
from src.api.main import app
endpoints = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/points/my-points' in endpoints
assert '/points/balance' not in endpoints
print('✅ Points API paths are correct')
"
```

**完成标准**：
- [x] Bug #3-4修复验证通过（正确路径 + UUID处理）
- [x] 积分余额计算准确
- [x] 交易历史分页功能正常
- [x] 错误路径已确认删除

---

### Task 3.2.3: Reward域完整端点测试 (1小时)

**文件**：`tests/e2e/test_reward_endpoints.py`

**实现内容**：
测试所有Reward域端点（2个端点）：
1. `POST /user/welcome-gift/claim` - 领取欢迎礼包（验证Bug #5修复：数据持久化）
2. `GET /rewards/my-rewards` - 获取我的奖励（验证数据返回）

**测试场景**：
- 欢迎礼包首次领取成功
- 欢迎礼包重复领取失败
- 验证数据库确实写入（flush + count验证）
- 空奖励情况处理（返回空字典非null）

**验证步骤**：
```bash
# 运行Reward域测试
uv run pytest tests/e2e/test_reward_endpoints.py -v
```

**完成标准**：
- [x] Bug #5修复验证通过（数据持久化 + UUID处理）
- [x] 欢迎礼包领取逻辑正确（1000积分 + 3奖励）
- [x] 数据写入验证机制生效
- [x] 空奖励场景处理正确

---

### Task 3.2.4: Top3域完整端点测试 (1小时)

**文件**：`tests/e2e/test_top3_endpoints.py`

**实现内容**：
测试所有Top3域端点（2个端点）：
1. `POST /top3/set` - 设置Top3（验证Bug #6修复：UUID转换）
2. `GET /top3` - 获取Top3

**测试场景**：
- 设置Top3成功（扣除300积分）
- 积分不足拒绝
- 重复日期拒绝
- 任务不属于用户拒绝
- 获取已设置的Top3
- 获取未设置的Top3（返回空列表）

**验证步骤**：
```bash
# 运行Top3域测试
uv run pytest tests/e2e/test_top3_endpoints.py -v
```

**完成标准**：
- [x] Bug #6修复验证通过（UUID转换正确）
- [x] Top3设置逻辑完整（积分扣除、任务验证）
- [x] 唯一性约束生效（重复日期拒绝）
- [x] 空Top3场景处理正确

---

### Task 3.2.5: User域完整端点测试 (2小时)

**文件**：`tests/e2e/test_user_endpoints.py`

**实现内容**：
测试所有User域端点（5个端点）：
1. `POST /user/register` - 注册
2. `POST /user/login` - 登录
3. `GET /user/profile` - 获取个人信息（验证Bug #7修复：SessionDep统一）
4. `PUT /user/profile` - 更新个人信息
5. 验证删除的端点：`POST /user/avatar`, `POST /user/feedback`（Bug #8）

**测试场景**：
- 注册新用户成功
- 重复手机号注册失败
- 登录获取token
- 获取个人信息（使用SessionDep）
- 更新昵称、头像URL
- 删除的端点返回404

**验证步骤**：
```bash
# 运行User域测试
uv run pytest tests/e2e/test_user_endpoints.py -v

# 验证SessionDep统一
grep -r "get_user_session" src/domains/user/ && echo "❌ 仍在使用get_user_session" || echo "✅ 已统一使用SessionDep"

# 验证删除的端点
uv run python -c "
from src.api.main import app
endpoints = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/user/avatar' not in endpoints
assert '/user/feedback' not in endpoints
print('✅ Avatar and Feedback endpoints removed')
"
```

**完成标准**：
- [x] Bug #7修复验证通过（SessionDep统一）
- [x] Bug #8修复验证通过（avatar/feedback删除）
- [x] 用户注册登录流程完整
- [x] 个人信息CRUD功能正常

---

### Task 3.2.6: Chat域完整端点测试 (1小时)

**文件**：`tests/e2e/test_chat_endpoints.py`

**实现内容**：
测试所有Chat域端点（3个端点）：
1. `POST /chat/session/start` - 开始对话
2. `POST /chat/message` - 发送消息
3. `GET /chat/history` - 获取历史记录

**测试场景**：
- 创建对话会话
- 发送消息并获取AI回复
- 获取完整历史记录
- 消息排序正确（时间顺序）

**验证步骤**：
```bash
# 运行Chat域测试
uv run pytest tests/e2e/test_chat_endpoints.py -v
```

**完成标准**：
- [x] Chat域所有端点都有测试
- [x] 对话流程完整（创建会话 -> 发送消息 -> 查看历史）
- [x] AI回复生成正常（可使用mock）

---

### Task 3.2.7: 覆盖率验证元测试 (1小时)

**文件**：`tests/e2e/test_api_coverage.py`

**实现内容**：
创建元测试验证100%覆盖率：
1. `test_100_percent_endpoint_coverage()`: 验证覆盖率 = 100%
2. `test_all_domains_covered()`: 验证每个域的覆盖率
3. 生成详细覆盖率报告到 `tests/reports/coverage_report.json`
4. 如果有未测试端点，失败并列出详细清单

**验证步骤**：
```bash
# 运行所有E2E测试
uv run pytest tests/e2e/ -v

# 运行覆盖率验证
uv run pytest tests/e2e/test_api_coverage.py -v

# 查看覆盖率报告
cat tests/reports/coverage_report.json | python -m json.tool
```

**完成标准**：
- [x] `test_100_percent_endpoint_coverage()` 通过
- [x] 覆盖率报告包含详细统计（总数、已测试、按域分组）
- [x] 如果有遗漏，清晰列出未测试端点

---

## Phase 3.3: 性能基准测试（3小时）

### Task 3.3.1: 主要端点性能测试 (2小时)

**文件**：`tests/performance/test_api_response_time.py`

**实现内容**：
为所有主要端点建立性能基准（每个端点执行20次）：
1. **Task域**：`GET /tasks`, `POST /tasks/create`, `PATCH /tasks/{id}/complete`
2. **Points域**：`GET /points/my-points`, `GET /points/transactions`
3. **Reward域**：`GET /rewards/my-rewards`
4. **Top3域**：`POST /top3/set`
5. **User域**：`GET /user/profile`

**性能SLA**：
- P95 < 200ms
- P99 < 500ms

**验证步骤**：
```bash
# 准备测试数据（100个任务、200个交易等）
uv run python tests/tools/prepare_perf_data.py

# 运行性能测试
uv run pytest tests/performance/test_api_response_time.py -v

# 查看性能基准
cat tests/reports/performance_baseline.json | python -m json.tool
```

**完成标准**：
- [x] 所有主要端点的P95 < 200ms
- [x] 所有主要端点的P99 < 500ms
- [x] 性能基准数据保存到文件
- [x] 测试输出包含详细统计（P50/P95/P99）

---

### Task 3.3.2: 性能回归检测测试 (1小时)

**文件**：`tests/performance/test_performance_regression.py`

**实现内容**：
1. 对比当前性能与历史基准
2. 检测P95回归（超过20%阈值）
3. 生成性能对比报告
4. 如果回归，测试失败并输出详细diff

**验证步骤**：
```bash
# 首次运行：建立基准
uv run pytest tests/performance/test_performance_regression.py -v

# 模拟性能退化（修改代码引入慢查询）
# ...

# 再次运行：检测回归
uv run pytest tests/performance/test_performance_regression.py -v
# 预期：测试失败，提示性能回归

# 恢复代码
# ...

# 再次运行：应该通过
uv run pytest tests/performance/test_performance_regression.py -v
```

**完成标准**：
- [x] 回归检测机制正常（20%阈值）
- [x] 首次运行创建基准，后续运行对比基准
- [x] 回归时提供详细diff（当前vs基准）
- [x] 可选 `--update-baseline` 标志更新基准

---

## Phase 3.4: 并发负载测试（3小时）

### Task 3.4.1: Points系统并发一致性测试 (1小时)

**文件**：`tests/concurrent/test_points_concurrency.py`

**实现内容**：
测试积分系统的并发数据一致性：
1. `test_concurrent_points_deduction_consistency()`: 10个并发扣减，验证最终余额正确
2. `test_concurrent_points_addition_consistency()`: 10个并发充值，验证最终余额正确
3. `test_mixed_concurrent_points_operations()`: 混合充值扣减，验证最终一致
4. `test_points_balance_query_during_updates()`: 查询期间更新，验证读已提交

**验证步骤**：
```bash
# 运行Points并发测试
uv run pytest tests/concurrent/test_points_concurrency.py -v
```

**完成标准**：
- [x] 所有并发测试通过（无数据不一致）
- [x] 并发扣减不会导致负余额
- [x] 事务隔离正确（读已提交）
- [x] 并发性能可接受（P95 < 500ms）

---

### Task 3.4.2: Top3系统并发唯一性测试 (1小时)

**文件**：`tests/concurrent/test_top3_concurrency.py`

**实现内容**：
测试Top3系统的并发唯一性约束：
1. `test_concurrent_top3_set_same_date()`: 3个并发请求同一日期，只有1个成功
2. `test_concurrent_top3_set_different_dates()`: 3个并发请求不同日期，都成功
3. `test_concurrent_top3_query_during_creation()`: 创建期间查询，不见部分数据

**验证步骤**：
```bash
# 运行Top3并发测试
uv run pytest tests/concurrent/test_top3_concurrency.py -v
```

**完成标准**：
- [x] 唯一性约束生效（同一日期只能设置一次）
- [x] 积分扣除正确（只扣除成功请求的300积分）
- [x] 查询不见脏数据（读已提交）

---

### Task 3.4.3: Reward系统并发幂等性测试 (1小时)

**文件**：`tests/concurrent/test_reward_concurrency.py`

**实现内容**：
测试奖励系统的并发幂等性：
1. `test_concurrent_welcome_gift_claim_idempotency()`: 5个并发领取，只有1个成功
2. `test_concurrent_reward_redemption()`: 并发使用奖励，不会超支
3. `test_concurrent_reward_grant_and_query()`: 发放期间查询，数据一致

**验证步骤**：
```bash
# 运行Reward并发测试
uv run pytest tests/concurrent/test_reward_concurrency.py -v
```

**完成标准**：
- [x] 欢迎礼包幂等性正确（只能领取一次）
- [x] 奖励使用不会超支（数量不为负）
- [x] 并发发放和查询无数据不一致

---

## Phase 3.5: 边界异常测试（3小时）

### Task 3.5.1: 无效输入处理测试 (1小时)

**文件**：`tests/edge_cases/test_invalid_inputs.py`

**实现内容**：
使用参数化测试验证无效输入处理：
1. `test_invalid_uuid_handling()`: 无效UUID在各个端点的处理（422而非500）
2. `test_sql_injection_prevention()`: SQL注入尝试被阻止
3. `test_xss_prevention()`: XSS脚本被转义
4. `test_path_traversal_prevention()`: 路径遍历被阻止

**验证步骤**：
```bash
# 运行无效输入测试
uv run pytest tests/edge_cases/test_invalid_inputs.py -v

# 应该看到多个参数化测试用例
```

**完成标准**：
- [x] 所有无效UUID测试通过（返回422而非500）
- [x] SQL注入测试通过（参数化查询安全）
- [x] XSS测试通过（内容转义）
- [x] 路径遍历测试通过（输入验证）

---

### Task 3.5.2: 边界值测试 (1小时)

**文件**：`tests/edge_cases/test_boundary_values.py`

**实现内容**：
测试各种边界值：
1. `test_empty_string_handling()`: 空字符串、纯空格的处理
2. `test_extremely_long_string_handling()`: 超长字符串（1000/10000字符）
3. `test_integer_boundary_values()`: 0、负数、INT_MAX、溢出值
4. `test_invalid_date_formats()`: 无效日期、不存在的日期

**验证步骤**：
```bash
# 运行边界值测试
uv run pytest tests/edge_cases/test_boundary_values.py -v
```

**完成标准**：
- [x] 空字符串正确拒绝（422）
- [x] 超长字符串正确处理（拒绝或截断）
- [x] 整数边界值正确处理（无溢出）
- [x] 无效日期正确拒绝

---

### Task 3.5.3: 权限边界测试 (1小时)

**文件**：`tests/edge_cases/test_security_vectors.py`

**实现内容**：
测试授权和权限边界：
1. `test_missing_token_handling()`: 无token访问受保护端点
2. `test_invalid_token_handling()`: 无效/过期token
3. `test_cross_user_access_prevention()`: 跨用户资源访问
4. `test_mass_assignment_prevention()`: 批量赋值漏洞检查

**验证步骤**：
```bash
# 运行安全向量测试
uv run pytest tests/edge_cases/test_security_vectors.py -v
```

**完成标准**：
- [x] 无token返回401
- [x] 无效token返回401
- [x] 跨用户访问返回403/404
- [x] 批量赋值被阻止（Pydantic严格模式）

---

## Phase 3.6: 文档与集成（2小时）

### Task 3.6.1: 更新测试文档 (1小时)

**文件**：
- `tests/README.md` - 测试套件使用指南
- `docs/testing-strategy.md` - 测试策略文档
- `docs/performance-sla.md` - 性能SLA文档

**实现内容**：
1. **tests/README.md**：
   - 测试套件结构说明
   - 运行各类测试的命令
   - 测试工具库使用说明
   - 覆盖率报告查看方法

2. **docs/testing-strategy.md**：
   - 四维度测试架构说明
   - 端点覆盖策略
   - 性能测试策略
   - 并发测试策略
   - 边界测试策略

3. **docs/performance-sla.md**：
   - 性能SLA定义（P95 < 200ms, P99 < 500ms）
   - 性能基准数据
   - 性能回归检测机制
   - 性能优化建议

**验证步骤**：
```bash
# 验证文档可读性
cat tests/README.md
cat docs/testing-strategy.md
cat docs/performance-sla.md
```

**完成标准**：
- [x] tests/README.md 包含完整使用说明
- [x] 测试策略文档解释四维度架构
- [x] 性能SLA文档定义明确

---

### Task 3.6.2: CI/CD流程集成 (1小时)

**文件**：`.github/workflows/test.yml` (如果使用GitHub Actions)

**实现内容**：
更新CI/CD流程，分阶段运行测试：
1. **Stage 1**: 快速反馈测试（critical tests，<2分钟）
2. **Stage 2**: E2E端点覆盖测试（<5分钟）
3. **Stage 3**: 性能测试（<3分钟）
4. **Stage 4**: 并发测试（<2分钟）
5. **Stage 5**: 边界测试（<2分钟）
6. **生成报告**: 覆盖率报告、性能报告

**验证步骤**：
```bash
# 本地模拟CI流程
uv run pytest -m "critical and not slow"
uv run pytest tests/e2e/
uv run pytest tests/performance/
uv run pytest tests/concurrent/
uv run pytest tests/edge_cases/

# 查看总执行时间（应该 < 15分钟）
```

**完成标准**：
- [x] CI流程分阶段运行，快速反馈
- [x] 所有阶段通过才能合并代码
- [x] 生成覆盖率报告和性能报告
- [x] 总执行时间 < 15分钟

---

## Phase 3.7: 验证与清理（1小时）

### Task 3.7.1: 完整测试套件运行验证 (0.5小时)

**验证步骤**：
```bash
# 运行完整测试套件
uv run pytest tests/ -v --tb=short

# 验证覆盖率
uv run pytest tests/e2e/test_api_coverage.py -v

# 验证性能基准
cat tests/reports/performance_baseline.json | python -m json.tool

# 统计测试数量
uv run pytest tests/ --collect-only | grep "test session starts"
```

**完成标准**：
- [x] 所有测试通过（success rate = 100%）
- [x] 端点覆盖率 = 100%
- [x] 性能测试覆盖主要端点（>80%）
- [x] 并发测试无数据不一致
- [x] 边界测试覆盖常见异常情况

---

### Task 3.7.2: 验证提案并标记为已应用 (0.5小时)

**验证步骤**：
```bash
# 验证OpenSpec提案
uv run openspec validate 1.4.3-api-coverage-quality-assurance --strict

# 应用提案（归档到archive）
uv run openspec apply 1.4.3-api-coverage-quality-assurance
```

**完成标准**：
- [x] OpenSpec验证通过
- [x] 提案成功应用并归档
- [x] 所有spec要求已实现

---

## 总结清单

### 必须满足（Must Have）
- [ ] 端点覆盖率 = 100%（所有路由都有测试）
- [ ] 性能测试覆盖率 > 80%（主要端点有性能基准）
- [ ] 所有并发测试通过（无数据一致性错误）
- [ ] 测试套件成功率 = 100%（所有测试稳定通过）

### 期望满足（Should Have）
- [ ] 边界测试覆盖率 > 80%
- [ ] P95响应时间 < 200ms
- [ ] 测试执行时间 < 15分钟

### 可选满足（Could Have）
- [ ] 代码覆盖率 > 70%
- [ ] 测试质量评分 > 85分
- [ ] 自动化测试报告生成

---

**预计总工时**：约18-22小时
**关键里程碑**：
- Day 1-2: 测试工具库 + 端点覆盖（Phase 3.1 + 3.2）
- Day 3: 性能测试 + 并发测试（Phase 3.3 + 3.4）
- Day 4: 边界测试 + 文档集成（Phase 3.5 + 3.6 + 3.7）

**风险点**：
1. 性能测试可能因环境波动不稳定 → 使用中位数和宽松阈值（20%）
2. 并发测试可能偶尔失败 → 添加重试机制和足够的超时时间
3. 测试执行时间可能超出预期 → 使用pytest-xdist并行执行

**成功标准**：
✅ 100%端点覆盖率
✅ 所有性能SLA达标
✅ 所有并发测试通过
✅ 边界测试覆盖主要异常场景
✅ CI/CD集成完成
