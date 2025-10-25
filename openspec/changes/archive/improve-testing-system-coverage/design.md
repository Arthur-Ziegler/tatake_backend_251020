# 测试系统覆盖度改进设计文档

## 设计原则

### 1. 测试金字塔原则
- **单元测试**: 70% - 快速、独立的基础功能测试
- **集成测试**: 20% - 模块间交互测试
- **端到端测试**: 10% - 完整业务流程验证

### 2. 测试驱动开发(TDD)
- 先写测试，再实现功能
- 测试即文档，明确需求规范
- 持续重构，保持测试质量

### 3. 测试独立性原则
- 每个测试用例独立运行
- 无执行顺序依赖
- 数据隔离，避免相互影响

## 架构设计

### 测试层次架构

```
┌─────────────────────────────────────────┐
│              E2E Tests                  │
│  (完整业务流程验证, 用户视角测试)          │
├─────────────────────────────────────────┤
│           Integration Tests             │
│  (模块间交互测试, 数据库集成测试)          │
├─────────────────────────────────────────┤
│            Unit Tests                   │
│  (单一函数/方法测试, 快速反馈)            │
└─────────────────────────────────────────┘
```

### 测试组件设计

#### 1. 测试数据管理器
```python
class TestDataManager:
    """测试数据统一管理"""

    def __init__(self):
        self.factories = {}
        self.fixtures = {}
        self.cleanup_handlers = []

    def create_user(self, **kwargs):
        """创建测试用户"""
        pass

    def create_task(self, user_id, **kwargs):
        """创建测试任务"""
        pass

    def cleanup(self):
        """清理测试数据"""
        pass
```

#### 2. 测试API客户端
```python
class TestAPIClient:
    """专用测试API客户端"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None

    def authenticate(self, user_type="guest"):
        """认证测试用户"""
        pass

    def create_task(self, task_data):
        """创建任务API调用"""
        pass

    def complete_task(self, task_id):
        """完成任务API调用"""
        pass
```

#### 3. 业务流程测试器
```python
class BusinessFlowTester:
    """业务流程测试框架"""

    def __init__(self, api_client, data_manager):
        self.api_client = api_client
        self.data_manager = data_manager
        self.assertions = []

    def test_task_completion_flow(self):
        """测试任务完成流程"""
        # 1. 准备测试数据
        user = self.data_manager.create_user()
        task = self.data_manager.create_task(user.id)

        # 2. 执行业务操作
        response = self.api_client.complete_task(task.id)

        # 3. 验证结果
        self._assert_task_completed(task.id)
        self._assert_points_awarded(user.id, expected_points)
        self._assert_reward_record_created(user.id)

        return TestResult(success=True, assertions=self.assertions)
```

## 具体实现设计

### 1. 端到端业务流程测试

#### 任务完成→奖励发放流程测试

**测试设计**:
```python
class TestTaskRewardFlow:
    """任务奖励流程测试套件"""

    @pytest.fixture
    def setup_test_environment(self):
        """设置测试环境"""
        # 创建独立测试数据库
        # 初始化测试数据
        # 配置测试参数
        pass

    def test_simple_task_completion(self, setup_test_environment):
        """测试简单任务完成流程"""
        # Arrange: 准备测试数据
        user = TestDataFactory.create_user()
        task = TestDataFactory.create_task(user_id=user.id)

        # Act: 执行操作
        initial_points = UserService.get_points(user.id)
        response = TaskAPI.complete_task(task.id)
        final_points = UserService.get_points(user.id)

        # Assert: 验证结果
        assert response.status_code == 200
        assert final_points == initial_points + task.points_reward
        assert TaskService.get_task_status(task.id) == TaskStatus.COMPLETED

        # 验证积分流水记录
        transaction = PointsService.get_latest_transaction(user.id)
        assert transaction.type == TransactionType.TASK_COMPLETION
        assert transaction.amount == task.points_reward

    def test_top3_reward_trigger(self, setup_test_environment):
        """测试Top3奖励触发流程"""
        # 创建多个用户完成任务
        users = TestDataFactory.create_users(5)
        tasks = []

        for user in users:
            task = TestDataFactory.create_task(user_id=user.id)
            TaskAPI.complete_task(task.id)
            tasks.append(task)

        # 触发Top3奖励分配
        Top3Service.allocate_rewards()

        # 验证Top3奖励发放
        top3_users = Top3Service.get_top3_users()
        for user in top3_users:
            reward = RewardService.get_latest_reward(user.id)
            assert reward.type == RewardType.TOP3
            assert reward.points > 0
```

#### 奖励兑换→材料消耗流程测试

**测试设计**:
```python
class TestRewardRedemptionFlow:
    """奖励兑换流程测试套件"""

    def test_simple_reward_redemption(self):
        """测试简单奖励兑换"""
        # 准备用户和积分
        user = TestDataFactory.create_user()
        UserService.add_points(user.id, 1000)

        # 准备奖励物品
        reward = TestDataFactory.create_reward(points_cost=500, stock=100)

        # 执行兑换
        initial_points = UserService.get_points(user.id)
        response = RewardAPI.redeem_reward(user.id, reward.id)

        # 验证结果
        assert response.status_code == 200
        final_points = UserService.get_points(user.id)
        assert final_points == initial_points - 500

        # 验证奖励获得
        user_reward = UserRewardService.get_user_reward(user.id, reward.id)
        assert user_reward is not None

    def test_recipe_composition_transaction(self):
        """测试配方组合事务一致性"""
        # 准备用户和材料
        user = TestDataFactory.create_user()
        materials = TestDataFactory.create_materials_for_user(user.id)

        # 准备配方
        recipe = TestDataFactory.create_recipe(
            required_materials=[
                {"material_id": materials[0].id, "quantity": 2},
                {"material_id": materials[1].id, "quantity": 1}
            ],
            result_item={"item_id": "sword", "quantity": 1}
        )

        # 记录初始状态
        initial_materials_state = UserMaterialService.get_user_materials(user.id)

        # 执行配方组合
        try:
            response = RecipeAPI.execute_recipe(user.id, recipe.id)

            # 验证事务成功
            assert response.status_code == 200

            # 验证材料消耗
            final_materials_state = UserMaterialService.get_user_materials(user.id)
            for required in recipe.required_materials:
                material = find_material(final_materials_state, required["material_id"])
                initial_qty = find_material(initial_materials_state, required["material_id"]).quantity
                assert material.quantity == initial_qty - required["quantity"]

            # 验证结果物品获得
            user_items = UserItemService.get_user_items(user.id)
            assert has_item(user_items, recipe.result_item["item_id"], recipe.result_item["quantity"])

        except Exception as e:
            # 验证事务回滚
            final_materials_state = UserMaterialService.get_user_materials(user.id)
            assert final_materials_state == initial_materials_state
            raise
```

### 2. Refresh Token机制测试设计

```python
class TestTokenRefreshFlow:
    """Token刷新流程测试套件"""

    def test_automatic_token_refresh(self):
        """测试自动Token刷新"""
        # 创建测试用户
        user = TestDataFactory.create_user()

        # 初始认证
        auth_response = AuthAPI.guest_init()
        initial_token = auth_response["access_token"]
        refresh_token = auth_response["refresh_token"]

        # 模拟Token过期
        TokenService.expire_token(initial_token)

        # 尝试使用过期Token
        api_client = TestAPIClient()
        api_client.set_token(initial_token)

        # 应该自动刷新Token
        response = api_client.get("/user/profile")

        # 验证Token已刷新
        assert response.status_code == 200
        new_token = api_client.get_current_token()
        assert new_token != initial_token
        assert TokenService.validate_token(new_token)

    def test_refresh_token_expired(self):
        """测试Refresh Token过期处理"""
        # 创建测试用户
        user = TestDataFactory.create_user()

        # 获取初始Token
        auth_response = AuthAPI.guest_init()
        refresh_token = auth_response["refresh_token"]

        # 使Refresh Token过期
        TokenService.expire_refresh_token(refresh_token)

        # 尝试刷新Token
        response = AuthAPI.refresh_token(refresh_token)

        # 应该返回认证错误
        assert response.status_code == 401
        assert response["error"] == "REFRESH_TOKEN_EXPIRED"

        # 需要重新认证
        new_auth_response = AuthAPI.guest_init()
        assert new_auth_response["access_token"] is not None

    def test_concurrent_token_refresh(self):
        """测试并发Token刷新"""
        # 创建测试用户
        user = TestDataFactory.create_user()

        # 获取初始Token
        auth_response = AuthAPI.guest_init()
        initial_token = auth_response["access_token"]
        refresh_token = auth_response["refresh_token"]

        # 模拟Token过期
        TokenService.expire_token(initial_token)

        # 并发执行多个请求
        import threading
        import concurrent.futures

        results = []

        def make_request():
            api_client = TestAPIClient()
            api_client.set_token(initial_token)
            response = api_client.get("/user/profile")
            results.append(response)

        # 启动多个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            concurrent.futures.wait(futures)

        # 验证所有请求都成功
        for result in results:
            assert result.status_code == 200

        # 验证Token只刷新了一次
        final_token = TokenService.get_current_user_token(user.id)
        token_refresh_count = TokenService.get_refresh_count(user.id)
        assert token_refresh_count == 1
```

### 3. 并发安全性测试设计

```python
class TestConcurrencySafety:
    """并发安全性测试套件"""

    def test_concurrent_task_completion(self):
        """测试并发任务完成"""
        # 创建测试用户和任务
        user = TestDataFactory.create_user()
        task = TestDataFactory.create_task(
            user_id=user.id,
            points_reward=100,
            anti_spam_window=300  # 5分钟防垃圾窗口
        )

        # 并发执行多次任务完成
        import threading
        import time

        results = []

        def complete_task():
            response = TaskAPI.complete_task(task.id)
            results.append(response)

        # 启动多个并发请求
        threads = []
        for i in range(5):
            thread = threading.Thread(target=complete_task)
            threads.append(thread)

        # 同时启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证只有一次成功
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count == 1

        # 验证积分只增加一次
        final_points = UserService.get_points(user.id)
        assert final_points == 100

        # 验证其他请求被反垃圾机制阻止
        anti_spam_count = sum(1 for r in results if r.status_code == 429)
        assert anti_spam_count == 4

    def test_concurrent_reward_redemption(self):
        """测试并发奖励兑换"""
        # 创建测试用户和奖励
        users = TestDataFactory.create_users(10)
        reward = TestDataFactory.create_reward(
            points_cost=100,
            stock=5  # 只有5个库存
        )

        # 给所有用户足够积分
        for user in users:
            UserService.add_points(user.id, 1000)

        # 并发执行奖励兑换
        import concurrent.futures

        results = []

        def redeem_reward(user):
            response = RewardAPI.redeem_reward(user.id, reward.id)
            return {"user_id": user.id, "response": response}

        # 启动并发兑换
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(redeem_reward, user) for user in users]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 验证只有5个用户成功兑换
        success_results = [r for r in results if r["response"].status_code == 200]
        assert len(success_results) == 5

        # 验证库存正确扣减
        final_stock = RewardService.get_stock(reward.id)
        assert final_stock == 0

        # 验证失败用户的积分未扣除
        failure_results = [r for r in results if r["response"].status_code != 200]
        for result in failure_results:
            user_id = result["user_id"]
            final_points = UserService.get_points(user_id)
            assert final_points == 1000  # 积分未扣除
```

## 测试执行框架

### 测试运行器设计

```python
class ComprehensiveTestRunner:
    """综合测试运行器"""

    def __init__(self):
        self.test_suites = [
            UnitTestSuite(),
            IntegrationTestSuite(),
            E2ETestSuite(),
            ConcurrencyTestSuite()
        ]

    def run_all_tests(self):
        """运行所有测试"""
        results = {}

        for suite in self.test_suites:
            suite_result = suite.run()
            results[suite.name] = suite_result

        return TestReport(results)

    def run_coverage_analysis(self):
        """运行覆盖率分析"""
        coverage_data = CoverageAnalyzer.analyze()
        return CoverageReport(coverage_data)
```

### 测试报告设计

```python
class TestReport:
    """测试报告生成器"""

    def generate_html_report(self, results):
        """生成HTML测试报告"""
        pass

    def generate_coverage_report(self, coverage_data):
        """生成覆盖率报告"""
        pass

    def generate_trend_report(self, historical_data):
        """生成趋势分析报告"""
        pass
```

## 配置管理

### 测试环境配置

```yaml
# test_config.yml
test_environments:
  unit:
    database: "sqlite:///:memory:"
    redis: "redis://localhost:6379/1"
    api_base_url: "http://localhost:8000"

  integration:
    database: "postgresql://test_user:test_pass@localhost:5432/test_db"
    redis: "redis://localhost:6379/2"
    api_base_url: "http://localhost:8000"

  e2e:
    database: "postgresql://test_user:test_pass@localhost:5432/e2e_test_db"
    redis: "redis://localhost:6379/3"
    api_base_url: "http://localhost:8000"

test_data:
  default_users: 10
  tasks_per_user: 5
  rewards_catalog_size: 20

performance_thresholds:
  api_response_time: 2.0  # seconds
  test_execution_time: 300  # seconds
  memory_usage_limit: 512  # MB
```

## 部署和维护

### CI/CD集成

```yaml
# .github/workflows/test.yml
name: Comprehensive Test Suite

on: [push, pull_request]

jobs:
  unit_tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Unit Tests
        run: |
          uv run pytest tests/unit/ -v --cov=src --cov-report=xml

  integration_tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test_password
    steps:
      - uses: actions/checkout@v2
      - name: Run Integration Tests
        run: |
          uv run pytest tests/integration/ -v

  e2e_tests:
    runs-on: ubuntu-latest
    needs: [unit_tests, integration_tests]
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E Tests
        run: |
          uv run pytest tests/e2e/ -v
```

这个设计文档为测试系统改进提供了完整的技术架构和实现指导，确保测试覆盖度改进项目的成功实施。