# 真实HTTP测试框架与P0 Bug修复 - 架构设计

## 设计目标

### 核心目标
1. **测试真实性**：测试环境100%还原生产环境HTTP请求处理流程
2. **快速失败**：P0 bug必须在<1分钟内被测试发现
3. **零假阳性**：消除ASGI Transport带来的测试通过但生产失败的问题
4. **渐进式重构**：为阶段2/3的全面重构铺平道路

### 非目标（留待后续阶段）
- ❌ 类型系统统一（阶段2）
- ❌ 100% API覆盖（阶段3）
- ❌ 性能测试框架（阶段3）

---

## 架构决策记录（ADR）

### ADR-001: 使用真实HTTP服务器而非ASGI Transport

**背景**：
当前测试使用`httpx.AsyncClient(transport=ASGITransport(app=app))`，这种方式虽然快速，但跳过了真实HTTP服务器的许多处理环节：
- 路由前缀处理
- 中间件执行
- CORS处理
- 请求头处理
- 实际网络传输

**决策**：使用`subprocess.Popen`启动真实uvicorn服务器

**理由**：
1. **完全一致性**：测试环境 = 生产环境
2. **真实性**：经过完整的HTTP协议栈
3. **可靠性**：消除环境差异导致的bug遗漏

**权衡**：
- ✅ 优点：100%真实，可靠性高
- ❌ 缺点：启动慢（~3秒），端口管理复杂
- **决定**：优先可靠性，接受启动开销

**替代方案**：
- 方案A：继续使用ASGITransport - ❌ 拒绝（无法发现生产bug）
- 方案B：使用TestClient - ❌ 拒绝（仍然不是真实HTTP）
- 方案C：Docker容器化测试 - ⏰ 延后（过于复杂，阶段3考虑）

---

### ADR-002: Session级别的服务器fixture

**背景**：
每个测试都启动/停止服务器会导致测试时间爆炸（每次3秒+）

**决策**：使用`scope="session"`的pytest fixture

```python
@pytest.fixture(scope="session")
def live_api_server():
    # 整个测试会话只启动一次服务器
    process = subprocess.Popen(...)
    yield "http://localhost:8099"
    process.terminate()
```

**理由**：
1. **性能**：从300秒（100个测试×3秒）降至3秒
2. **稳定性**：减少端口冲突风险
3. **简单性**：fixture管理更简单

**权衡**：
- ✅ 优点：测试速度快，资源占用少
- ❌ 缺点：测试间状态可能相互影响
- **缓解**：每个测试后清理数据（cleanup fixture）

---

### ADR-003: 数据清理策略 - 测试后清理

**背景**：
真实HTTP服务器使用真实数据库，需要管理测试数据隔离

**决策**：采用"测试后清理"策略

```python
@pytest.fixture(autouse=True)
def cleanup_test_data():
    yield  # 测试执行
    # 测试后清理创建的数据
    cleanup_tasks()
    cleanup_users()
    cleanup_points()
```

**理由**：
1. **真实性**：使用生产数据库，不需要专门测试数据库
2. **简单性**：无需维护两套数据库配置
3. **一致性**：测试环境更接近生产

**权衡**：
- ✅ 优点：配置简单，环境真实
- ❌ 缺点：清理不彻底会影响后续测试
- **缓解**：提供完整的清理工具函数

**替代方案**：
- 方案A：独立测试数据库 - ❌ 拒绝（配置复杂）
- 方案B：事务回滚 - ❌ 拒绝（影响真实场景测试）
- 方案C：Docker数据库 - ⏰ 延后（阶段3优化）

---

### ADR-004: 端口管理策略

**背景**：
固定端口8099可能被占用，导致测试失败

**决策**：
- **阶段1**：使用固定端口8099，测试前检查端口
- **阶段3**：升级为动态端口分配

```python
# 阶段1实现
PORT = 8099
if is_port_in_use(PORT):
    raise RuntimeError(f"Port {PORT} is already in use")
```

**理由**：
1. **简单性**：固定端口易于调试和理解
2. **快速交付**：避免过度设计
3. **可迭代**：阶段3再优化

**阶段3升级计划**：
```python
# 阶段3实现
def get_free_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]

PORT = get_free_port()
```

---

## P0 Bug修复设计

### Bug #1: 任务完成API请求体问题

#### 问题详述
```python
# 当前实现 - 错误
@router.post("/{task_id}/complete")
async def complete_task(
    task_id: UUID,
    request: CompleteTaskRequest = Body(...),  # ❌ 必传
)

# CompleteTaskRequest定义
class CompleteTaskRequest(BaseModel):
    mood_feedback: Optional[MoodFeedback] = None  # 可选字段
```

**根本问题**：
- `Body(...)`表示请求体必传
- 但CompleteTaskRequest所有字段都是可选的
- 导致客户端必须发送`{}`才能调用API

**实际用例**：
```bash
# ❌ 当前：必须传请求体
curl -X POST /tasks/{id}/complete -d '{}'

# ✅ 期望：可以不传请求体
curl -X POST /tasks/{id}/complete
```

#### 修复方案

**方案A：请求体改为可选**（推荐）
```python
@router.post("/{task_id}/complete")
async def complete_task(
    task_id: UUID,
    request: Optional[CompleteTaskRequest] = Body(None),  # ✅ 可选
    session: SessionDep,
    user_id: UUID = Depends(get_current_user_id)
):
    # 处理None情况
    mood_feedback = request.mood_feedback if request else None
```

**优点**：
- ✅ 符合REST API最佳实践
- ✅ 向后兼容（仍然可以传mood_feedback）
- ✅ 简单直接

**方案B：使用默认值**
```python
request: CompleteTaskRequest = Body(default=CompleteTaskRequest())
```

**缺点**：
- ❌ 语义不清晰
- ❌ 仍然需要传`{}`

**决定**：采用方案A

#### 测试验证

```python
async def test_complete_task_without_body(real_api_client, test_task):
    """测试不传请求体完成任务"""
    response = await real_api_client.post(
        f"/tasks/{test_task.id}/complete",
        headers={"Authorization": f"Bearer {token}"}
        # 注意：无json参数
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["task"]["status"] == "completed"

async def test_complete_task_with_mood_feedback(real_api_client, test_task):
    """测试带mood_feedback完成任务"""
    response = await real_api_client.post(
        f"/tasks/{test_task.id}/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mood_feedback": {
                "comment": "很好完成了",
                "difficulty": "easy"
            }
        }
    )
    assert response.status_code == 200
```

---

### Bug #6: Top3 UUID错误

#### 问题详述

**错误信息**：
```
'UUID' object has no attribute 'replace'
```

**调用栈**：
```python
# src/domains/top3/service.py:48
current_balance = self.points_service.get_balance(user_id)
                                                    ↓ UUID对象
# src/domains/points/service.py:71
{"user_id": str(user_id)}
              ↓ str(UUID对象)
# 某处代码尝试调用
user_id.replace(...)  # ❌ UUID对象没有replace方法
```

**根本原因**：
1. Top3 Service接收UUID对象
2. PointsService期望str或UUID（内部会转换）
3. 但在某些代码路径，UUID对象被直接使用

#### 修复方案

**临时修复（阶段1）**：显式转换
```python
# src/domains/top3/service.py:48
# 修改前
current_balance = self.points_service.get_balance(user_id)

# 修改后
current_balance = self.points_service.get_balance(str(user_id))
```

**根本修复（阶段2）**：类型系统统一
- 见阶段2提案`1.4.2-uuid-type-safety-p1-fixes`

#### 需要修改的位置

搜索所有调用`points_service.get_balance`的地方：
```bash
rg "points_service\.get_balance\(" src/
```

修改清单：
1. `src/domains/top3/service.py:48` - set_top3方法
2. `src/domains/top3/service.py:72` - get_balance调用

#### 测试验证

```python
async def test_set_top3_success(real_api_client, test_tasks):
    """测试设置Top3成功"""
    response = await real_api_client.post(
        "/tasks/special/top3",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "date": "2025-10-26",
            "task_ids": [str(task1.id), str(task2.id), str(task3.id)]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["points_consumed"] == 300
    # 验证不会报UUID错误
```

---

## 代码删除策略

### 需要删除的文件/代码

#### 完全删除的测试文件
这些文件使用ASGITransport，需要完全重写：
```
tests/e2e/test_api_coverage.py          - 使用ASGITransport
tests/e2e/test_system_comprehensive.py  - 使用ASGITransport
tests/performance/test_concurrent_load.py - 使用ASGITransport
tests/domains/reward/test_welcome_gift.py - 使用ASGITransport
```

#### 需要修改的conftest文件
```python
# tests/conftest.py - 删除旧的test_client fixture
@pytest.fixture
async def test_client():  # ❌ 删除
    async with AsyncClient(transport=ASGITransport(app=app)) as client:
        yield client
```

#### 保留但标记废弃
某些测试可能在阶段2/3重写，暂时保留：
```python
# tests/integration/test_api_responses.py
# TODO: 在阶段3重写为真实HTTP测试
```

---

## 测试数据清理设计

### 清理范围
每个测试后需要清理的数据：
1. 测试用户（test_开头的用户）
2. 测试任务（测试期间创建的）
3. 测试积分流水
4. 测试奖励记录
5. 测试Top3记录

### 清理实现

```python
# tests/utils/cleanup.py
async def cleanup_test_data(client: httpx.AsyncClient, user_ids: List[str]):
    """清理测试数据"""

    for user_id in user_ids:
        # 1. 删除用户所有任务
        await client.delete(f"/tasks/all?user_id={user_id}")

        # 2. 清理积分流水（保留余额为0）
        # 注：这里不真正删除，而是通过添加负数积分归零
        balance = await get_balance(client, user_id)
        if balance != 0:
            await client.post(f"/points/adjust", json={
                "user_id": user_id,
                "amount": -balance,
                "source_type": "test_cleanup"
            })

        # 3. 清理奖励记录
        await client.delete(f"/rewards/all?user_id={user_id}")

        # 4. 清理Top3记录
        await client.delete(f"/tasks/special/top3/all?user_id={user_id}")

@pytest.fixture(autouse=True)
async def auto_cleanup(real_api_client):
    """自动清理fixture"""
    created_users = []

    # 提供注册用户的帮助函数
    async def register_test_user():
        response = await real_api_client.post("/auth/guest-init")
        user_data = response.json()["data"]
        created_users.append(user_data["user_id"])
        return user_data

    # 将帮助函数注入到请求上下文
    real_api_client.register_test_user = register_test_user

    yield

    # 测试后清理
    if created_users:
        await cleanup_test_data(real_api_client, created_users)
```

### 清理验证

```python
async def test_cleanup_works(real_api_client):
    """验证清理机制工作正常"""
    # 创建测试数据
    user = await real_api_client.register_test_user()
    task = await create_test_task(real_api_client, user["user_id"])

    # 验证数据存在
    assert task is not None

    # Fixture会自动清理
    # 在下一个测试中验证数据已清理
```

---

## 实施顺序

### 第1步：基础设施（最关键）
1. 创建`tests/conftest_real_http.py`
2. 实现`live_api_server` fixture
3. 实现`real_api_client` fixture
4. 测试服务器能正常启动/停止

**验收**：
```bash
uv run pytest tests/conftest_real_http.py -v
# 应该看到服务器启动、测试执行、服务器关闭
```

### 第2步：Bug修复
1. 修复任务完成API（router.py）
2. 修复Top3 UUID问题（service.py）
3. 编写单元测试验证修复

**验收**：
```bash
uv run pytest tests/domains/task/test_complete_api.py -v
uv run pytest tests/domains/top3/test_set_top3.py -v
```

### 第3步：P0功能验证测试
1. 创建`tests/e2e/test_critical_apis.py`
2. 测试任务完成（空body + 带body）
3. 测试Top3设置
4. 确保使用真实HTTP

**验收**：
```bash
uv run pytest tests/e2e/test_critical_apis.py -v
# 所有测试通过，无UUID错误
```

### 第4步：删除旧代码
1. 删除ASGITransport相关测试
2. 删除旧的conftest.py中的test_client
3. 更新导入语句

**验收**：
```bash
rg "ASGITransport" tests/
# 应该返回0结果
```

### 第5步：文档更新
1. 更新`tests/README.md`
2. 更新`docs/testing-system-design.md`
3. 添加变更日志

---

## 性能考虑

### 服务器启动优化
```python
# 使用--reload=false加速启动
process = subprocess.Popen([
    "uv", "run", "uvicorn", "src.api.main:app",
    "--host", "0.0.0.0",
    "--port", "8099",
    "--reload", "false",  # 禁用热重载
    "--log-level", "error"  # 减少日志输出
])
```

### 预期性能
- 服务器启动：3秒
- 单个测试：50-200ms
- 阶段1总测试时间：<1分钟（~10个测试）

---

## 向阶段2/3的过渡

### 阶段1为阶段2铺路
- ✅ 真实HTTP测试基础已建立
- ✅ 测试清理机制已完善
- ✅ P0 bug已修复，系统可用
- → 阶段2可以专注于类型系统重构

### 阶段1为阶段3铺路
- ✅ 测试框架已经成熟
- ✅ 性能基准已建立
- → 阶段3可以快速扩展测试覆盖

---

## 风险缓解措施

### 端口冲突风险
**缓解**：
```python
def wait_for_server(url: str, timeout: int = 10):
    """等待服务器就绪"""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"{url}/health")
            return True
        except:
            time.sleep(0.5)
    return False
```

### 服务器启动失败风险
**缓解**：
```python
if not wait_for_server(server_url):
    process.terminate()
    raise RuntimeError("API server failed to start")
```

### 测试数据污染风险
**缓解**：
- 使用test_前缀标记测试数据
- 完善cleanup逻辑
- 阶段3引入数据库隔离

---

## 总结

### 关键设计原则
1. **真实性优先**：牺牲速度换取可靠性
2. **渐进式重构**：阶段1只做必要的，为阶段2/3铺路
3. **质量门槛**：P0 bug必须在阶段1修复

### 成功指标
- ✅ 真实HTTP测试可以运行
- ✅ P0 bug已修复
- ✅ 所有旧测试代码已删除
- ✅ 测试执行时间<1分钟
- ✅ 无回归问题

### 下一步
见阶段2提案：`1.4.2-uuid-type-safety-p1-fixes`
