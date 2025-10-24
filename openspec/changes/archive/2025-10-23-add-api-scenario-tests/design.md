# 技术设计

## Context
项目已实现32个API（认证5+任务7+奖励4+积分2+Top3 2+Focus5+Chat7），需要场景测试验证业务逻辑。

## Goals / Non-Goals
**Goals:**
- 覆盖4类核心业务场景（任务流程、Top3、组合场景、Focus）
- 每个场景独立可运行，失败不影响其他场景
- 测试数据自动创建清理，每文件共享用户

**Non-Goals:**
- 不做性能测试
- 不做前端交互测试
- 不做并发压力测试

## Decisions

### 1. 目录结构
```
tests/scenarios/
├── conftest.py              # 共享fixtures
├── utils.py                 # 辅助工具
├── test_01_task_flow.py     # 任务完整流程
├── test_02_top3_flow.py     # Top3特殊奖励
├── test_03_combined_flow.py # 跨模块组合
├── test_04_focus_flow.py    # Focus番茄钟
└── README.md                # 使用文档
```

### 2. 测试数据隔离策略
- **Fixture scope**: `module`级别（每文件共享用户）
- **创建时机**: `@pytest.fixture(scope="module")`在文件开始创建测试用户
- **清理时机**: fixture的yield后自动清理该文件创建的所有资源
- **数据库事务**: 不使用事务回滚，使用API删除确保测试真实性

### 3. API客户端封装
```python
class APIClient:
    def __init__(self, base_url, token):
        self.client = httpx.Client(base_url=base_url)
        self.token = token

    def request(self, method, path, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"}
        return self.client.request(method, path, headers=headers, **kwargs)
```

### 4. 断言策略
- 响应码断言：`assert response.status_code == 200`
- 响应格式断言：`assert response.json()["code"] == 200`
- 业务逻辑断言：验证积分计算、奖励发放、完成度更新
- 使用自定义`assert_xxx`函数提高可读性

## Risks / Trade-offs
- **Risk**: 测试数据未清理导致污染
  - **Mitigation**: 每个fixture显式清理，提供独立清理脚本
- **Risk**: 外部依赖（AI服务）导致测试不稳定
  - **Mitigation**: Chat场景独立，其他场景不依赖AI
- **Risk**: 测试时间过长
  - **Mitigation**: 场景优先级排序，支持按marker运行

## Migration Plan
1. 创建新目录`tests/scenarios/`
2. 实现基础设施（conftest, utils）
3. 按优先级实现场景测试（A→B→D→C）
4. 编写文档和运行指南
5. 集成到CI/CD（可选）

无需迁移现有测试，场景测试作为补充存在。

## Open Questions
- 是否需要集成到CI/CD自动运行？（暂定：否，手动运行即可）
- 是否需要生成HTML报告？（暂定：否，pytest默认输出即可）
