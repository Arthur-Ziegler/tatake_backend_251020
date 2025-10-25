# 自动化测试验收规范

## 测试策略（I1方案）

### 1. Service层单元测试

**目标**：确保所有Service方法返回dict，绝不返回模型实例。

**测试文件**：`tests/unit/test_service_return_types.py`

**测试用例模板**：
```python
import pytest
from src.domains.task.service import TaskService

def test_task_service_get_task_returns_dict(db_session, sample_task):
    """验证TaskService.get_task()返回dict而非Task模型"""
    service = TaskService(db_session, points_service)

    # 执行
    result = service.get_task(sample_task.id, sample_task.user_id)

    # 断言：必须是dict类型
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    # 断言：包含所有必要字段
    assert "id" in result
    assert "title" in result
    assert "status" in result

    # 断言：字段类型正确
    assert isinstance(result["id"], str)
    assert isinstance(result["title"], str)
```

**覆盖范围**：
- Task Service: `get_task()`, `create_task()`, `update_task()` 等
- Chat Service: 所有返回业务数据的方法
- Focus Service: 所有返回业务数据的方法
- Reward Service: 所有返回业务数据的方法
- Top3 Service: 所有返回业务数据的方法
- User Service: 所有返回业务数据的方法

---

### 2. API端点集成测试

**目标**：验证每个端点正确使用泛型响应模型。

**测试文件**：`tests/integration/test_api_responses.py`

**测试用例模板**：
```python
import pytest
from fastapi.testclient import TestClient

def test_task_create_endpoint_response_format(client: TestClient, auth_token):
    """验证创建任务端点返回正确的响应格式"""
    # 准备
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {"title": "测试任务", "description": "测试描述"}

    # 执行
    response = client.post("/api/v1/tasks", json=data, headers=headers)

    # 断言：HTTP状态码
    assert response.status_code == 200

    # 断言：响应格式
    json_data = response.json()
    assert "code" in json_data
    assert "data" in json_data
    assert "message" in json_data

    # 断言：成功响应
    assert json_data["code"] == 201
    assert json_data["data"] is not None
    assert json_data["message"] == "任务创建成功"

    # 断言：data字段包含完整的TaskResponse结构
    task_data = json_data["data"]
    assert "id" in task_data
    assert "title" in task_data
    assert task_data["title"] == "测试任务"


def test_task_create_endpoint_error_response_format(client: TestClient, auth_token):
    """验证创建任务端点错误响应格式"""
    # 准备：无效数据（缺少必填字段）
    headers = {"Authorization": f"Bearer {auth_token}"}
    data = {}  # 缺少title

    # 执行
    response = client.post("/api/v1/tasks", json=data, headers=headers)

    # 断言：HTTP状态码
    assert response.status_code == 400

    # 断言：错误响应格式
    json_data = response.json()
    assert json_data["code"] == 400
    assert json_data["data"] is None
    assert "message" in json_data
```

**覆盖范围**：每个领域至少2个端点（1个成功+1个失败）

---

### 3. OpenAPI JSON自动化验证

**目标**：确保OpenAPI文档包含所有必要的schema定义。

**测试文件**：`tests/validation/test_openapi_schemas.py`

**测试脚本**：
```python
import pytest
import requests

def test_openapi_json_contains_all_schemas():
    """验证OpenAPI JSON包含所有必要的schema定义"""
    # 获取OpenAPI JSON
    response = requests.get("http://localhost:8000/openapi.json")
    assert response.status_code == 200

    openapi_spec = response.json()
    schemas = openapi_spec.get("components", {}).get("schemas", {})

    # 验证关键schema存在
    required_schemas = [
        "AuthTokenData",
        "TaskResponse",
        "ChatSessionResponse",
        "FocusSessionResponse",
        "RewardResponse",
        "Top3Response",
        "UserProfileResponse",
        "UnifiedResponse",
    ]

    for schema_name in required_schemas:
        assert schema_name in schemas, f"Missing schema: {schema_name}"

    # 验证泛型响应schema
    # 注意：FastAPI会为每个泛型实例生成单独的schema
    # 例如：UnifiedResponse[TaskResponse] 可能生成 "UnifiedResponse_TaskResponse_"

    print(f"✅ 验证通过：OpenAPI包含 {len(schemas)} 个schema定义")


def test_openapi_endpoints_have_response_models():
    """验证所有端点都有明确的response_model定义"""
    response = requests.get("http://localhost:8000/openapi.json")
    openapi_spec = response.json()

    paths = openapi_spec.get("paths", {})
    endpoints_without_schema = []

    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                responses = details.get("responses", {})
                success_response = responses.get("200", {})
                content = success_response.get("content", {})
                json_content = content.get("application/json", {})
                schema = json_content.get("schema", {})

                # 检查是否有schema引用
                if not schema.get("$ref") and not schema.get("allOf"):
                    endpoints_without_schema.append(f"{method.upper()} {path}")

    assert len(endpoints_without_schema) == 0, \
        f"以下端点缺少schema定义：{endpoints_without_schema}"

    print(f"✅ 验证通过：所有端点都有schema定义")
```

---

### 4. 类型检查（mypy）

**目标**：确保类型注解正确且一致。

**配置文件**：`pyproject.toml`
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = "src.domains.*.service"
check_untyped_defs = true
```

**验证命令**：
```bash
uv run mypy src/domains/task/service.py
uv run mypy src/domains/chat/service.py
uv run mypy src/domains/focus/service.py
uv run mypy src/domains/reward/service.py
uv run mypy src/domains/top3/service.py
uv run mypy src/domains/user/service.py
```

**期望结果**：零类型错误

---

## 验收检查清单

### 自动化验证
- [ ] `pytest tests/unit/test_service_return_types.py` - 全部通过
- [ ] `pytest tests/integration/test_api_responses.py` - 全部通过
- [ ] `pytest tests/validation/test_openapi_schemas.py` - 全部通过
- [ ] `mypy src/domains/*/service.py` - 零错误

### 手动验证
- [ ] 启动服务器：`uv run uvicorn src.api.main:app --reload`
- [ ] 访问Swagger UI：http://localhost:8000/docs
- [ ] 检查每个端点的Schemas部分是否显示完整
- [ ] 检查Example Value是否包含data字段内容

### 代码审查
- [ ] 搜索代码中是否有`-> Task`、`-> FocusSession`等模型返回类型
- [ ] 确认所有Service方法签名为`-> Dict[str, Any]`
- [ ] 确认所有路由函数签名为`-> UnifiedResponse[DataModel]`
- [ ] 确认已删除所有Wrapper类

### 性能基准
- [ ] 响应时间无明显增加（<5%）
- [ ] 内存占用正常
- [ ] 无内存泄漏

---

## 测试数据准备

**Fixtures文件**：`tests/conftest.py`

```python
import pytest
from src.domains.task.models import Task
from src.domains.auth.service import AuthService

@pytest.fixture
def sample_task(db_session, test_user):
    """创建示例任务"""
    task = Task(
        id=uuid4(),
        user_id=test_user.id,
        title="测试任务",
        description="测试描述",
        status="pending",
        priority="medium",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(task)
    db_session.commit()
    return task

@pytest.fixture
def auth_token(client, test_user):
    """获取认证token"""
    response = client.post("/api/v1/auth/login", json={
        "wechat_openid": test_user.wechat_openid
    })
    return response.json()["data"]["access_token"]
```

---

## CI/CD集成

**GitHub Actions配置**：`.github/workflows/test.yml`

```yaml
name: API Response Model Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install uv
      run: pip install uv

    - name: Install dependencies
      run: uv sync

    - name: Run Service layer tests
      run: uv run pytest tests/unit/test_service_return_types.py -v

    - name: Run API integration tests
      run: uv run pytest tests/integration/test_api_responses.py -v

    - name: Run OpenAPI validation
      run: |
        uv run uvicorn src.api.main:app &
        sleep 5
        uv run pytest tests/validation/test_openapi_schemas.py -v

    - name: Type checking
      run: uv run mypy src/domains/*/service.py
```

---

## 失败处理流程

### 如果Service层测试失败
1. 检查Service方法签名是否为`-> Dict[str, Any]`
2. 检查方法内部是否正确转换模型为dict
3. 运行单个测试：`pytest tests/unit/test_service_return_types.py::test_task_service_get_task_returns_dict -v`

### 如果API端点测试失败
1. 检查路由函数的`response_model`是否为`UnifiedResponse[DataModel]`
2. 检查返回语句是否构造了正确的UnifiedResponse
3. 检查异常处理是否返回UnifiedResponse

### 如果OpenAPI验证失败
1. 检查是否所有端点都设置了`response_model`
2. 检查schema是否在`components/schemas`中注册
3. 手动访问`/openapi.json`查看实际内容

### 如果mypy类型检查失败
1. 添加缺失的类型注解
2. 修正错误的返回类型声明
3. 运行`mypy --show-error-codes`查看详细错误
