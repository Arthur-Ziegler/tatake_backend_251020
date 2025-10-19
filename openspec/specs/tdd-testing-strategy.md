# TDD测试策略规范

## 概述

本文档定义了 TaKeKe 项目的测试驱动开发（TDD）策略、测试标准和最佳实践。

## TDD方法论

### 三步循环
1. **红阶段**: 编写失败的测试用例
2. **绿阶段**: 编写最小可行代码使测试通过
3. **重构阶段**: 优化代码结构，保持测试通过

### 核心原则
- **测试先行**: 先写测试，后写实现
- **小步快跑**: 每次只实现一个功能点
- **持续重构**: 不断改进代码质量
- **高覆盖率**: 确保测试覆盖所有关键路径

## 测试架构

### 测试分层
```
端到端测试 (E2E Tests)
    ↓
集成测试 (Integration Tests)
    ↓
单元测试 (Unit Tests)
```

### 测试类型
- **单元测试**: 测试单个函数或方法
- **集成测试**: 测试模块间交互
- **端到端测试**: 测试完整业务流程

## 测试框架

### 核心工具
- **pytest**: 测试框架和断言库
- **pytest-cov**: 代码覆盖率工具
- **pytest-mock**: Mock和Patch工具
- **factory_boy**: 测试数据工厂

### 配置文件
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=95"
]
```

## 单元测试标准

### 测试结构
```python
class TestClassName:
    def setup_method(self):
        """每个测试方法前执行"""
        self.test_data = create_test_data()

    def teardown_method(self):
        """每个测试方法后执行"""
        cleanup_test_data()

    def test_method_success_case(self):
        """测试成功场景"""
        # Arrange
        # Act
        # Assert
        pass

    def test_method_failure_case(self):
        """测试失败场景"""
        # Arrange
        # Act
        # Assert
        pass
```

### 命名规范
- **测试类**: `Test` + 被测类名
- **测试方法**: `test_` + 方法名 + `_` + 场景描述
- **测试文件**: `test_` + 模块名 + `.py`

### 断言标准
- 使用具体的断言方法
- 提供清晰的错误信息
- 验证所有重要的输出
- 测试边界条件

## 集成测试标准

### 数据库测试
```python
@pytest.fixture
def test_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    BaseSQLModel.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
```

### Repository测试
```python
class TestUserRepository:
    def test_create_user_success(self, test_session):
        """测试用户创建成功"""
        # Arrange
        user_repo = UserRepository(test_session)
        user_data = {...}

        # Act
        user = user_repo.create(user_data)

        # Assert
        assert user.id is not None
        assert user.email == user_data["email"]
```

## 测试数据管理

### 测试数据工厂
```python
class UserFactory:
    @staticmethod
    def create_user(**overrides):
        default_data = {
            "email": "test@example.com",
            "nickname": "测试用户",
            "user_type": "registered"
        }
        default_data.update(overrides)
        return default_data
```

### 测试数据清理
- 使用独立的测试数据库
- 每个测试使用独立的会话
- 自动清理测试数据
- 避免测试间数据污染

## Mock和Patch策略

### Mock使用原则
- 只Mock外部依赖
- 优先使用真实对象
- 验证Mock的调用次数和参数
- 避免过度Mock

### Patch使用示例
```python
def test_external_api_call(self):
    """测试外部API调用"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "success"}

        result = external_service.get_data()

        assert result["status"] == "success"
        mock_get.assert_called_once_with("https://api.example.com")
```

## 覆盖率要求

### 覆盖率标准
- **模型层**: 95%+ 代码覆盖率
- **Repository层**: 90%+ 代码覆盖率
- **服务层**: 95%+ 代码覆盖率
- **总体覆盖率**: 90%+ 代码覆盖率

### 覆盖率报告
- 生成HTML覆盖率报告
- 识别未覆盖的代码路径
- 定期检查覆盖率趋势

## 性能测试

### 测试指标
- **响应时间**: 关键接口响应时间
- **吞吐量**: 并发请求处理能力
- **内存使用**: 内存占用和泄漏
- **数据库查询**: 查询执行时间

### 性能测试工具
- **pytest-benchmark**: 性能基准测试
- **locust**: 负载测试
- **memory_profiler**: 内存分析

## 持续集成

### CI/CD流程
- 自动运行所有测试
- 检查代码覆盖率
- 生成测试报告
- 阻止低质量代码合并

### 测试环境
- 开发环境: 快速反馈
- 测试环境: 完整验证
- 预生产环境: 最终验证

## 测试最佳实践

### 测试设计
- **独立性**: 测试间不相互依赖
- **可重复性**: 测试结果可重现
- **快速执行**: 单个测试快速完成
- **清晰意图**: 测试目的明确

### 错误处理测试
```python
def test_invalid_parameter_raises_error(self):
    """测试无效参数抛出错误"""
    with pytest.raises(RepositoryValidationError):
        user_repo.create({"email": "", "nickname": ""})
```

### 边界条件测试
```python
def test_edge_cases(self):
    """测试边界条件"""
    # 测试空值
    # 测试最大值
    # 测试最小值
    # 测试特殊字符
    pass
```

## 测试维护

### 测试重构
- 随代码重构更新测试
- 消除重复的测试代码
- 提高测试可读性
- 优化测试执行速度

### 测试文档
- 为复杂测试添加注释
- 记录测试场景和预期行为
- 维护测试数据文档

## 常见问题和解决方案

### 测试环境问题
- **数据库连接**: 使用内存数据库
- **时间依赖**: Mock时间相关函数
- **网络请求**: Mock外部API
- **文件操作**: 使用临时文件

### 测试性能问题
- **测试数据过多**: 使用数据工厂
- **数据库操作慢**: 使用事务回滚
- **测试执行慢**: 并行执行测试

## 测试工具和插件

### 推荐插件
- **pytest-xdist**: 并行测试执行
- **pytest-mock**: Mock支持
- **pytest-cov**: 覆盖率统计
- **pytest-html**: HTML测试报告

### IDE集成
- **VS Code**: Python插件支持
- **PyCharm**: 内置pytest支持
- **调试支持**: 断点调试测试

## 总结

TDD是确保代码质量的关键实践，通过严格的测试流程和覆盖率要求，我们可以构建高质量、可维护的代码库。

### 核心价值
- **代码质量**: 高覆盖率的测试保证代码质量
- **重构信心**: 测试保护下的安全重构
- **文档作用**: 测试作为可执行的文档
- **回归防护**: 防止功能退化

### 持续改进
- 定期审查测试质量
- 优化测试执行效率
- 更新测试工具和流程
- 团队培训和知识分享