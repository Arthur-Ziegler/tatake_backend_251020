# API场景测试套件

## 概述

这是TaKeKe后端API的场景测试套件，用于验证系统的端到端业务流程。测试覆盖了32个API端点，通过模拟真实用户操作来确保跨模块业务逻辑的正确性。

## 测试架构

### 目录结构
```
tests/scenarios/
├── conftest.py              # 共享fixtures和测试配置
├── utils.py                 # 测试工具函数
├── test_01_task_flow.py     # 任务完整流程测试
├── test_02_top3_flow.py     # Top3特殊奖励流程测试
├── test_03_combined_flow.py # 跨模块组合流程测试
├── test_04_focus_flow.py    # Focus番茄钟流程测试
└── README.md                # 本文档
```

### 测试设计原则

1. **隔离性**: 每个测试文件使用独立的测试用户，确保测试之间不相互影响
2. **真实性**: 使用真实HTTP调用到运行在8001端口的后端服务
3. **自动化**: 测试数据自动创建和清理
4. **可读性**: 详细的测试步骤和结果输出

## 测试场景

### 1. 任务完整流程测试 (`test_01_task_flow.py`)

**优先级**: A（最高）

**测试内容**:
- ✅ 创建任务
- ✅ 查看任务详情
- ✅ 更新任务信息
- ✅ 完成任务获得积分
- ✅ 积分变化验证
- ✅ 奖励获取验证
- ✅ 子任务层次结构
- ✅ 批量操作
- ✅ 错误处理

**业务流程**: 创建 → 更新 → 完成 → 获得积分 → 查看奖励

### 2. Top3特殊奖励流程测试 (`test_02_top3_flow.py`)

**优先级**: B（高）

**测试内容**:
- ✅ 积分积累（完成任务）
- ✅ Top3设置（消耗300积分）
- ✅ Top3任务完成
- ✅ 特殊奖励验证
- ✅ 高价值奖品兑换
- ✅ 重复设置防护
- ✅ 错误处理

**业务流程**: 充值积分 → 设置Top3 → 完成Top3任务 → 验证高价值奖励

### 3. Focus番茄钟流程测试 (`test_04_focus_flow.py`)

**优先级**: C（中）

**测试内容**:
- ✅ 开始Focus会话
- ✅ 暂停/恢复会话
- ✅ 完成会话获得积分
- ✅ 多会话管理
- ✅ 历史记录查询
- ✅ 错误处理
- ✅ 任务集成

**业务流程**: 开始 → 暂停 → 恢复 → 完成 → 查询历史

### 4. 跨模块组合流程测试 (`test_03_combined_flow.py`)

**优先级**: D（低但重要）

**测试内容**:
- ✅ 任务+Focus组合
- ✅ Top3+Focus+任务树
- ✅ 跨模块错误处理
- ✅ 综合业务场景
- ✅ 数据一致性验证

**业务流程**: 复杂的多模块协作场景

## 运行指南

### 环境要求

1. **后端服务**: 确保后端服务运行在 `http://localhost:8001`
2. **Python环境**: 使用uv管理依赖
3. **测试数据库**: 配置独立的测试数据库

### 安装依赖

```bash
# 安装测试依赖
uv add --dev pytest httpx
```

### 运行测试

#### 运行所有场景测试
```bash
# 在项目根目录运行
uv run pytest tests/scenarios/ -v
```

#### 运行特定场景测试
```bash
# 只运行任务流程测试
uv run pytest tests/scenarios/test_01_task_flow.py -v

# 只运行Top3流程测试
uv run pytest tests/scenarios/test_02_top3_flow.py -v

# 只运行Focus流程测试
uv run pytest tests/scenarios/test_04_focus_flow.py -v

# 只运行跨模块组合测试
uv run pytest tests/scenarios/test_03_combined_flow.py -v
```

#### 按优先级运行
```bash
# 运行高优先级测试（A+B）
uv run pytest tests/scenarios/ -m "task_flow or top3_flow" -v

# 运行所有标记为场景的测试
uv run pytest tests/scenarios/ -m scenario -v
```

#### 并行运行（提高速度）
```bash
# 使用4个进程并行运行
uv run pytest tests/scenarios/ -n 4 -v
```

#### 生成详细报告
```bash
# 生成HTML报告
uv run pytest tests/scenarios/ --html=scenario_test_report.html --self-contained-html

# 只显示失败测试的详细信息
uv run pytest tests/scenarios/ -v --tb=short
```

### 测试配置

#### pytest标记
- `@pytest.mark.scenario`: 标记场景测试
- `@pytest.mark.task_flow`: 任务流程测试
- `@pytest.mark.top3_flow`: Top3流程测试
- `@pytest.mark.focus_flow`: Focus流程测试
- `@pytest.mark.combined_flow`: 跨模块组合测试

#### 环境变量
```bash
# 设置测试环境
export TESTING=true
export API_BASE_URL=http://localhost:8001
export TEST_TIMEOUT=30
```

## 测试数据管理

### 用户隔离
- 每个测试文件创建独立的测试用户
- 用户命名规则: `场景测试用户_YYYYMMDD_HHMMSS_XXX`
- 测试结束后自动清理用户数据

### 数据清理策略
1. **任务清理**: 测试结束后删除所有创建的任务
2. **积分记录**: 保留积分流水记录用于审计
3. **会话清理**: 清理所有Focus会话和Top3记录
4. **失败处理**: 即使测试失败也会尝试清理数据

### 积分管理
- 初始用户积分: 0
- 任务完成奖励: 10积分
- Focus会话奖励: 15积分（25分钟）
- Top3额外奖励: 50积分
- Top3设置消耗: 300积分

## 故障排除

### 常见问题

#### 1. 后端服务连接失败
```
错误: ConnectionRefusedError: [Errno 61] Connection refused
解决: 确保后端服务运行在 localhost:8001
```

#### 2. 认证失败
```
错误: 401 Unauthorized
解决: 检查JWT_SECRET_KEY配置是否正确
```

#### 3. 数据库连接问题
```
错误: 数据库连接超时
解决: 检查数据库服务是否正常运行
```

#### 4. 测试数据污染
```
问题: 测试之间相互影响
解决: 检查数据清理逻辑，确保使用独立用户
```

### 调试技巧

#### 1. 详细日志输出
```bash
# 显示详细日志
uv run pytest tests/scenarios/ -v -s --tb=long
```

#### 2. 单独运行问题测试
```bash
# 只运行一个测试函数
uv run pytest tests/scenarios/test_01_task_flow.py::test_complete_task_flow -v -s
```

#### 3. 检查API响应
```python
# 在测试中添加调试输出
print(f"API响应: {response.json()}")
```

#### 4. 数据库状态检查
```python
# 在测试中检查数据库状态
response = client.get("/tasks/")
print(f"当前任务: {response.json()}")
```

## 扩展指南

### 添加新场景测试

1. **创建测试文件**:
   ```python
   # test_05_new_flow.py
   import pytest
   from utils import *

   @pytest.mark.scenario
   def test_new_scenario(authenticated_client):
       # 实现新场景测试
       pass
   ```

2. **使用工具函数**:
   ```python
   # 创建测试数据
   task = create_task_with_validation(client, task_data)

   # 验证API响应
   assert_api_success(response)

   # 验证积分变化
   assert_points_change(before, after, expected)
   ```

3. **清理测试数据**:
   ```python
   try:
       # 测试逻辑
       pass
   finally:
       # 清理数据
       client.delete(f"/tasks/{task_id}")
   ```

### 添加新的断言函数

在 `utils.py` 中添加新的断言函数：

```python
def assert_new_condition(actual, expected, message="条件不满足"):
    """自定义断言函数"""
    assert actual == expected, f"{message}: 期望 {expected}, 实际 {actual}"
```

### 配置CI/CD

在GitHub Actions中添加场景测试：

```yaml
- name: Run Scenario Tests
  run: |
    # 启动后端服务
    uv run python src/main.py &
    sleep 10

    # 运行场景测试
    uv run pytest tests/scenarios/ -v --html=report.html
```

## 贡献指南

1. **遵循测试命名规范**: `test_XX_descriptive_name.py`
2. **使用描述性函数名**: `test_specific_business_flow`
3. **添加详细注释**: 说明测试的业务目的
4. **确保数据清理**: 防止测试间污染
5. **更新文档**: 添加新测试的说明

## 版本历史

- **v1.0.0**: 初始版本，包含4个核心场景测试
  - 任务完整流程测试
  - Top3特殊奖励流程测试
  - Focus番茄钟流程测试
  - 跨模块组合流程测试

## 联系方式

如有问题或建议，请联系TaKeKe开发团队。