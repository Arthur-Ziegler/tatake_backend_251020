# TaKeKe项目测试指南

## 📋 目录

- [快速开始](#快速开始)
- [测试架构](#测试架构)
- [运行测试](#运行测试)
- [编写测试](#编写测试)
- [调试指南](#调试指南)
- [覆盖率报告](#覆盖率报告)
- [常见问题](#常见问题)

## 🚀 快速开始

### 环境准备

确保你的开发环境已经设置好：

```bash
# 安装依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或者
.venv\Scripts\activate     # Windows
```

### 运行所有测试

```bash
# 运行完整测试套件
uv run pytest

# 运行带覆盖率的测试
uv run pytest --cov=src --cov-report=html
```

## 🏗️ 测试架构

### 测试目录结构

```
tests/
├── conftest.py                 # 全局测试配置
├── pytest.ini                 # pytest配置文件
├── database/                   # 数据库测试
│   ├── test_connection.py     # 数据库连接测试
│   └── test_integration.py    # 数据库集成测试
├── domains/                    # 领域测试
│   ├── auth/                  # 认证领域测试
│   │   ├── test_auth_models.py
│   │   ├── test_auth_repository.py
│   │   └── test_auth_service.py
│   ├── task/                  # 任务领域测试
│   │   ├── test_task_models.py
│   │   ├── test_task_repository.py
│   │   └── test_task_service.py
│   ├── reward/                # 奖励领域测试
│   ├── focus/                 # 番茄钟领域测试
│   ├── chat/                  # 聊天领域测试
│   ├── points/                # 积分领域测试
│   └── top3/                  # Top3领域测试
├── e2e/                        # 端到端测试
├── integration/               # 集成测试
└── scenarios/                 # 场景测试
    ├── test_01_task_flow.py
    ├── test_02_top3_flow.py
    └── test_03_combined_flow.py
```

### 测试类型

#### 1. 单元测试 (`@pytest.mark.unit`)
测试单个函数或方法的功能
```python
@pytest.mark.unit
class TestTaskService:
    def test_create_task_success(self):
        # 测试任务创建成功场景
        pass
```

#### 2. 集成测试 (`@pytest.mark.integration`)
测试多个组件之间的协作
```python
@pytest.mark.integration
class TestTaskRewardIntegration:
    def test_task_completion_rewards(self):
        # 测试任务完成时的奖励发放
        pass
```

#### 3. 端到端测试 (`@pytest.mark.e2e`)
测试完整的用户流程
```python
@pytest.mark.e2e
class TestUserJourney:
    def test_complete_task_flow(self):
        # 测试从注册到任务完成的完整流程
        pass
```

## 🧪 运行测试

### 基本命令

```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/domains/auth/test_auth_service.py

# 运行特定测试类
uv run pytest tests/domains/auth/test_auth_service.py::TestAuthService

# 运行特定测试方法
uv run pytest tests/domains/auth/test_auth_service.py::TestAuthService::test_wechat_login_success
```

### 按标记运行

```bash
# 只运行单元测试
uv run pytest -m unit

# 只运行集成测试
uv run pytest -m integration

# 只运行端到端测试
uv run pytest -m e2e

# 运行多个标记
uv run pytest -m "unit or integration"
```

### 调试选项

```bash
# 显示详细输出
uv run pytest -v

# 显示print语句输出
uv run pytest -s

# 在第一个失败时停止
uv run pytest -x

# 只运行失败的测试
uv run pytest --lf

# 运行特定数量的失败测试
uv run pytest --maxfail=3
```

### 覆盖率报告

```bash
# 生成覆盖率报告
uv run pytest --cov=src --cov-report=term-missing

# 生成HTML覆盖率报告
uv run pytest --cov=src --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## ✏️ 编写测试

### 测试文件命名规范

- 测试文件应以`test_`开头
- 测试类应以`Test`开头
- 测试方法应以`test_`开头

### 基本测试结构

```python
import pytest
from src.domains.auth.service import AuthService
from src.domains.auth.models import Auth

@pytest.mark.unit
class TestAuthService:
    @pytest.fixture
    def auth_service(self, test_db_session):
        """创建AuthService实例的fixture"""
        return AuthService(test_db_session)

    @pytest.fixture
    def sample_user(self):
        """创建示例用户的fixture"""
        return Auth(
            wechat_openid="test_openid_123",
            is_guest=False
        )

    def test_create_user_success(self, auth_service, sample_user):
        """测试用户创建成功"""
        # Arrange - 准备测试数据
        # Act - 执行被测试的操作
        result = auth_service.create_user(sample_user)

        # Assert - 验证结果
        assert result is not None
        assert result.wechat_openid == sample_user.wechat_openid
```

### 使用Fixtures

```python
# 在conftest.py中定义全局fixtures
@pytest.fixture(scope="function")
def test_db_session():
    """创建测试数据库会话"""
    # 设置测试数据库
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()

# 在测试文件中使用fixtures
def test_with_database(self, test_db_session):
    # 使用test_db_session进行测试
    user = Auth(wechat_openid="test")
    test_db_session.add(user)
    test_db_session.commit()

    assert user.id is not None
```

### 模拟和打桩

```python
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestExternalAPI:
    def test_api_call_success(self):
        # 模拟外部API调用
        with patch('src.services.external_api.call') as mock_call:
            mock_call.return_value = {"status": "success"}

            result = external_service.make_api_call()

            assert result["status"] == "success"
            mock_call.assert_called_once()
```

### 参数化测试

```python
@pytest.mark.parametrize(
    "input_data,expected_result",
    [
        ("valid@email.com", True),
        ("invalid-email", False),
        ("", False),
        ("a@b.c", True),
    ]
)
def test_email_validation(self, input_data, expected_result):
    """测试邮箱验证"""
    result = validate_email(input_data)
    assert result == expected_result
```

### 异常测试

```python
def test_invalid_operation_raises_exception(self, service):
    """测试无效操作抛出异常"""
    with pytest.raises(ValueError, match="无效的操作"):
        service.invalid_operation()

def test_custom_exception(self, service):
    """测试自定义异常"""
    with pytest.raises(CustomException) as exc_info:
        service.operation_that_fails()

    assert exc_info.value.error_code == 1001
    assert "具体错误信息" in str(exc_info.value)
```

## 🐛 调试指南

### 1. 查看详细错误信息

```bash
# 显示完整的错误堆栈
uv run pytest --tb=long

# 显示更简洁的错误信息
uv run pytest --tb=short

# 不显示错误堆栈（只显示摘要）
uv run pytest --tb=no
```

### 2. 使用调试器

```python
def test_debug_example(self):
    import pdb; pdb.set_trace()  # 设置断点

    # 或者使用breakpoint() (Python 3.7+)
    # breakpoint()

    result = some_function()
    assert result == expected_value
```

### 3. 打印调试信息

```python
def test_with_debug_output(self, capsys):
    """捕获打印输出"""
    print("调试信息")

    captured = capsys.readouterr()
    assert "调试信息" in captured.out
```

### 4. 日志调试

```python
import logging

def test_with_logging(self, caplog):
    """捕获日志输出"""
    logger = logging.getLogger("src.domains.auth")

    logger.info("测试日志消息")

    assert "测试日志消息" in caplog.text
```

## 📊 覆盖率报告

### 查看覆盖率

```bash
# 终端输出覆盖率
uv run pytest --cov=src --cov-report=term-missing

# 生成HTML报告
uv run pytest --cov=src --cov-report=html

# 按模块查看覆盖率
uv run pytest --cov=src.domains.auth --cov-report=term-missing
```

### 覆盖率目标

- **单元测试**: 目标90%+覆盖率
- **集成测试**: 目标80%+覆盖率
- **整体项目**: 目标80%+覆盖率

### 忽略覆盖率的代码

```python
def complex_legacy_code():
    # pragma: no cover
    # 这段代码暂时不测试
    pass
```

## ❓ 常见问题

### Q: 测试数据库连接失败怎么办？

**A**: 检查以下几点：
1. 确保测试使用了内存数据库或独立的测试数据库
2. 检查数据库URL配置
3. 确保所有必要的表都已创建

```python
# 在conftest.py中确保数据库初始化
@pytest.fixture(scope="session")
def setup_test_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
```

### Q: UUID类型错误怎么解决？

**A**: 确保所有UUID字段都使用str类型：

```python
# 正确的UUID字段定义
id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
user_id: str = Field(..., index=True)

# 错误的UUID字段定义（会导致SQLite错误）
id: UUID = Field(default_factory=uuid4, primary_key=True)
```

### Q: 服务依赖注入问题怎么解决？

**A**: 在测试中正确初始化服务依赖：

```python
@pytest.fixture
def task_service(self, test_db_session):
    points_service = PointsService(test_db_session)
    return TaskService(test_db_session, points_service)
```

### Q: 如何处理异步代码测试？

**A**: 使用pytest-asyncio：

```python
import pytest

@pytest.mark.asyncio
async def test_async_function(self):
    result = await some_async_function()
    assert result is not None
```

### Q: 测试运行太慢怎么办？

**A**: 优化策略：
1. 使用内存数据库而不是文件数据库
2. 并行运行测试：`pytest -n auto`
3. 只运行相关的测试：`pytest -k "test_specific"`
4. 使用更快的断言方法

### Q: 如何测试私有方法？

**A**: 虽然不推荐，但必要时可以：

```python
def test_private_method(self):
    service = SomeService()
    # 使用名称访问私有方法
    result = service._private_method("arg")
    assert result == expected
```

更好的做法是测试公共接口，让私有方法通过公共接口间接测试。

## 🔧 高级技巧

### 1. 自定义标记

```python
# 在pytest.ini中定义标记
[tool:pytest]
markers =
    unit: 单元测试
    integration: 集成测试
    slow: 慢速测试
    database: 需要数据库的测试

# 在测试中使用
@pytest.mark.slow
@pytest.mark.database
def test_slow_database_operation(self):
    pass
```

### 2. 测试工厂模式

```python
@pytest.fixture
def user_factory():
    def create_user(**kwargs):
        defaults = {
            "wechat_openid": "test_openid",
            "is_guest": False
        }
        defaults.update(kwargs)
        return Auth(**defaults)

    return create_user

def test_with_factory(self, user_factory):
    user = user_factory(wechat_openid="custom_openid")
    assert user.wechat_openid == "custom_openid"
```

### 3. 测试容器

```python
class TestUserService:
    @pytest.fixture(autouse=True)
    def setup(self, test_db_session):
        """每个测试方法前都会执行的setup"""
        self.service = UserService(test_db_session)

    def test_create_user(self):
        user = self.service.create_user("test_openid")
        assert user is not None
```

## 📞 获取帮助

- **查看pytest文档**: `pytest --help`
- **查看可用fixtures**: `pytest --fixtures`
- **项目问题**: 在GitHub Issues中搜索或创建新issue
- **测试框架问题**: 查看pytest官方文档

---

**最后更新**: 2025-10-24
**维护者**: TaKeKe开发团队