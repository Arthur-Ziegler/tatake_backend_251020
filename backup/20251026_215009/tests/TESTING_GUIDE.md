# TaKeKe Backend 单元测试规范

> **版本**: v1.0.0
> **更新日期**: 2025-10-26
> **适用范围**: `tests/units/` 单元测试

## 📋 测试原则

### KISS 原则
- 一个测试只验证一个行为
- 测试名称清晰描述验证内容
- Arrange-Act-Assert 结构清晰分离

### YAGNI 原则
- 不测试未实现功能
- 不过度参数化（仅必要场景）
- 避免测试工具类过度抽象

### SOLID 原则
- 单一职责：每个测试函数职责单一
- 开闭原则：使用 fixture 扩展而非修改
- 依赖倒置：Mock 接口而非实现

## 🎯 覆盖率目标

- **整体覆盖率**: ≥ 95%
- **关键业务逻辑**: 100% 分支覆盖
- **排除项**: `__init__.py`、`__repr__`、`Protocol`、抽象方法

## 📁 文件组织规范

### 路径映射规则
```
源文件: src/domains/auth/service.py
测试文件: tests/units/domains/auth/test_service.py

源文件: src/api/middleware/cors.py
测试文件: tests/units/api/middleware/test_cors.py
```

**规则**: 保持目录结构镜像，测试文件名加 `test_` 前缀

### 目录结构示例
```
tests/units/
├── api/
│   ├── middleware/
│   │   └── test_cors.py
│   └── test_main.py
├── domains/
│   ├── auth/
│   │   ├── conftest.py         # 领域专用 fixtures
│   │   ├── test_service.py
│   │   ├── test_repository.py
│   │   └── test_models.py
│   └── chat/
│       ├── tools/
│       │   └── test_calculator.py
│       └── test_service.py
└── core/
    └── test_validators.py
```

## ✍️ 测试编写规范

### 1. 测试函数命名

```python
# ✅ 好的命名
def test_init_guest_account_creates_valid_token():
    """初始化游客账号应生成有效令牌"""

def test_wechat_register_raises_error_on_duplicate_openid():
    """微信注册重复 openid 应抛出异常"""

# ❌ 差的命名
def test_auth():  # 不清晰
def test_case1():  # 无意义
def test_wechat_register_duplicate_openid_ValidationError():  # 过长
```

**命名模式**: `test_<方法名>_<场景>_<预期结果>`

### 2. 测试结构（AAA 模式）

```python
def test_create_task_with_valid_data():
    """创建任务应返回任务对象"""
    # Arrange - 准备测试数据
    task_data = {
        "title": "测试任务",
        "priority": "high"
    }
    service = TaskService()

    # Act - 执行被测操作
    result = service.create_task(task_data)

    # Assert - 验证结果
    assert result["title"] == "测试任务"
    assert result["priority"] == "high"
    assert "id" in result
```

### 3. Fixture 使用规范

```python
# conftest.py - 共享 fixtures
@pytest.fixture
def auth_db_session():
    """Auth 领域数据库会话"""
    # 创建表
    Auth.metadata.create_all(test_engine)
    session = TestingSessionLocal()
    yield session
    # 清理
    session.close()
    Auth.metadata.drop_all(test_engine)

# test_service.py - 使用 fixture
def test_create_user(auth_db_session):
    service = AuthService(session=auth_db_session)
    result = service.create_user(...)
    assert result is not None
```

**Fixture 作用域选择**:
- `function`: 每个测试独立（数据库会话）
- `class`: 同类测试共享
- `module`: 同文件测试共享
- `session`: 整个测试会话共享（慎用）

### 4. 参数化测试

```python
@pytest.mark.parametrize("priority,expected_score", [
    ("low", 1),
    ("medium", 3),
    ("high", 5),
    ("urgent", 10),
])
def test_calculate_priority_score(priority, expected_score):
    """测试优先级分数计算"""
    result = calculate_priority_score(priority)
    assert result == expected_score
```

**何时使用参数化**:
- 相同逻辑多个输入值
- 边界值测试（最小值、最大值、0、负数等）
- 等价类测试

### 5. 异常测试

```python
def test_login_with_invalid_credentials_raises_exception():
    """无效凭证登录应抛出认证异常"""
    service = AuthService()

    with pytest.raises(AuthenticationException, match="用户名或密码错误"):
        service.login("invalid_user", "wrong_password")
```

**必须测试的异常场景**:
- 参数验证失败
- 业务规则违反
- 资源不存在
- 权限不足

## 🎭 Mock 策略

### Mock 使用原则
1. **优先真实依赖**: 能用真实对象尽量用（内存数据库、真实模型类）
2. **Mock 外部服务**: 第三方 API（LLM、微信 API）、文件系统、网络请求
3. **避免 Mock 内部**: 不 Mock 项目内部类/方法（暗示设计问题）

### 复杂 Mock 停止信号
**满足以下任一条件立即停止，讨论重构源码**:
- ❌ Mock 链超过 2 层 (`mock.method.return_value.another`)
- ❌ 单测试 Mock 超 4 个依赖
- ❌ Mock 设置代码超 15 行
- ❌ 需 Mock 私有方法

### Mock 示例

#### ✅ 好的 Mock（外部服务）
```python
def test_chat_service_with_mocked_llm(mocker):
    """测试聊天服务（Mock LLM）"""
    # Mock 外部 LLM API
    mock_response = {"content": "测试回复", "role": "assistant"}
    mocker.patch(
        "langchain_anthropic.ChatAnthropic.invoke",
        return_value=mock_response
    )

    service = ChatService()
    result = service.send_message("你好")

    assert result["content"] == "测试回复"
```

#### ✅ 好的 Mock（文件系统）
```python
def test_export_tasks_to_file(mocker):
    """测试导出任务到文件"""
    mock_file = mocker.mock_open()
    mocker.patch("builtins.open", mock_file)

    export_tasks(tasks=[...])

    mock_file.assert_called_once_with("tasks.json", "w")
```

#### ❌ 差的 Mock（过度 Mock）
```python
# 触发停止信号：Mock 链过长、Mock 数量过多
def test_complex_scenario(mocker):
    mock1 = mocker.Mock()
    mock2 = mocker.Mock()
    mock3 = mocker.Mock()
    mock4 = mocker.Mock()
    mock5 = mocker.Mock()

    mock1.method.return_value.another_method.return_value = "result"
    # ... 15+ 行 Mock 设置

    # 🚨 应停止并重构源码
```

### AI/LangChain 测试策略

**单元测试**: 全部 Mock
```python
@pytest.fixture
def mock_llm_chain(mocker):
    """Mock LangChain 调用"""
    return mocker.patch("langchain_core.runnables.Runnable.invoke")

def test_chat_tool_integration(mock_llm_chain):
    mock_llm_chain.return_value = {"output": "任务已创建"}
    # 测试业务逻辑
```

**集成测试**: 真实 API（保留在 `tests/integration/`）
```python
@pytest.mark.integration
@pytest.mark.slow
def test_real_llm_call():
    """真实 LLM 调用测试（需 API Key）"""
    # 使用真实 API
```

## 🗄️ 数据库测试规范

### 使用内存数据库
```python
# conftest.py 已配置
TEST_DATABASE_URL = "sqlite:///:memory:"
```

### 数据隔离
```python
@pytest.fixture(scope="function")
def test_db_session():
    """每个测试独立数据库会话"""
    SQLModel.metadata.create_all(test_engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    SQLModel.metadata.drop_all(test_engine)  # 清理
```

### 测试事务行为
```python
def test_task_creation_rollback_on_error(test_db_session):
    """任务创建失败应回滚"""
    service = TaskService(session=test_db_session)

    with pytest.raises(ValidationError):
        service.create_task(invalid_data)

    # 验证数据未写入
    tasks = test_db_session.query(Task).all()
    assert len(tasks) == 0
```

## 📊 测试标记（Markers）

```python
@pytest.mark.unit
def test_calculate_score():
    """单元测试标记"""

@pytest.mark.slow
def test_batch_import():
    """慢速测试标记（执行时间 > 1s）"""

@pytest.mark.database
def test_migration():
    """数据库测试标记"""
```

**运行特定标记**:
```bash
uv run pytest -m unit          # 只运行单元测试
uv run pytest -m "not slow"    # 跳过慢速测试
```

## 🔍 断言规范

### 使用明确断言
```python
# ✅ 好的断言
assert result["status"] == "completed"
assert len(tasks) == 5
assert "error" not in response

# ❌ 差的断言
assert result  # 不明确
assert True    # 无意义
```

### 断言消息
```python
# 复杂断言添加说明
assert calculated_score >= 0, f"分数不应为负: {calculated_score}"
assert user_id in active_users, f"用户 {user_id} 未在活跃列表中"
```

### 浮点数比较
```python
import pytest

# 使用 pytest.approx
assert result == pytest.approx(3.14159, rel=1e-5)
```

## 🚀 测试执行

### 运行测试
```bash
# 运行所有单元测试
uv run pytest tests/units/ -v

# 运行特定领域
uv run pytest tests/units/domains/auth/ -v

# 运行单个文件
uv run pytest tests/units/domains/auth/test_service.py -v

# 运行单个测试
uv run pytest tests/units/domains/auth/test_service.py::test_login -v
```

### 覆盖率报告
```bash
# 生成 HTML 报告
uv run pytest tests/units/ --cov=src --cov-report=html

# 查看缺失行
uv run pytest tests/units/ --cov=src --cov-report=term-missing

# 特定模块覆盖率
uv run pytest tests/units/domains/auth/ --cov=src/domains/auth
```

### 性能分析
```bash
# 显示最慢的 10 个测试
uv run pytest tests/units/ --durations=10

# 详细输出
uv run pytest tests/units/ -vv

# 停止于首个失败
uv run pytest tests/units/ -x
```

## 📝 测试文档规范

### Docstring 要求
```python
def test_create_task_with_nested_subtasks():
    """
    测试创建带嵌套子任务的任务

    场景：
    1. 创建父任务
    2. 创建 2 个子任务
    3. 为子任务再创建子任务（3 层嵌套）

    验证：
    - 任务层级关系正确
    - 完成度计算正确
    - parent_id 外键约束生效
    """
```

### 注释规范
```python
def test_complex_calculation():
    # Arrange
    data = prepare_test_data()

    # Act
    result = complex_function(data)

    # Assert - 验证核心业务逻辑
    assert result["total"] == 100
    # Assert - 验证边界情况
    assert result["min"] >= 0
    assert result["max"] <= 100
```

## 🔧 常用测试工具

### pytest-mock
```python
def test_with_mock(mocker):
    spy = mocker.spy(SomeClass, "method")
    SomeClass().method()
    spy.assert_called_once()
```

### freezegun（时间控制）
```python
from freezegun import freeze_time

@freeze_time("2025-10-26 12:00:00")
def test_time_sensitive_feature():
    result = get_current_date()
    assert result == "2025-10-26"
```

### faker（测试数据生成）
```python
from faker import Faker
fake = Faker("zh_CN")

def test_with_random_data():
    username = fake.user_name()
    email = fake.email()
    # 测试逻辑
```

## ⚠️ 反模式（禁止）

### ❌ 测试依赖顺序
```python
# 测试间不应有依赖
class TestUserFlow:
    def test_01_create_user(self):
        self.user_id = create_user()  # ❌

    def test_02_update_user(self):
        update_user(self.user_id)  # ❌ 依赖 test_01
```

### ❌ 魔法数字
```python
def test_calculation():
    result = calculate(10, 20)
    assert result == 200  # ❌ 200 从何而来？

    # ✅ 应该
    BASE = 10
    MULTIPLIER = 20
    EXPECTED = BASE * MULTIPLIER
    result = calculate(BASE, MULTIPLIER)
    assert result == EXPECTED
```

### ❌ 过度 Setup
```python
@pytest.fixture
def complex_fixture():
    # ❌ 100+ 行准备代码
    # 暗示测试设计问题
```

### ❌ 测试实现细节
```python
def test_internal_cache():
    service = TaskService()
    service.process()
    # ❌ 测试内部缓存实现
    assert service._cache_size == 10

    # ✅ 应测试行为
    result = service.get_result()
    assert result is not None
```

## 📋 测试评审检查清单

**提交测试代码前检查**:
- [ ] 测试命名清晰（`test_<方法>_<场景>_<结果>`）
- [ ] AAA 结构清晰
- [ ] 覆盖正常路径 + 异常路径 + 边界值
- [ ] Mock 仅用于外部依赖
- [ ] 未触发"复杂 Mock 停止信号"
- [ ] 包含必要 docstring
- [ ] 测试独立（无顺序依赖）
- [ ] 断言明确具体
- [ ] 覆盖率满足要求（≥95%）
- [ ] 测试执行时间合理（单测试 < 1s）

## 🔗 参考资源

- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-mock 文档](https://pytest-mock.readthedocs.io/)
- [测试金字塔理论](https://martinfowler.com/articles/practical-test-pyramid.html)
- 项目配置：`pytest.ini`、`tests/conftest.py`

---

**维护者**: TaKeKe 团队
**更新**: 遇到新场景及时补充本文档
