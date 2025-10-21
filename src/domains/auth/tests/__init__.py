"""
认证领域测试模块

该模块包含认证领域的所有单元测试和集成测试。

测试分类:
- test_router.py: API路由层测试
- test_service.py: 业务逻辑层测试
- test_repository.py: 数据访问层测试
- test_models.py: 数据模型测试
- test_integration.py: 集成测试
- conftest.py: pytest配置和fixtures

测试覆盖率目标: > 95%
测试策略:
1. 单元测试: 测试各层独立功能
2. 集成测试: 测试层间交互
3. 边界测试: 测试异常情况和边界条件
4. 安全测试: 测试认证安全和权限控制
5. 性能测试: 测试API响应时间

运行测试:
```bash
# 运行所有认证测试
pytest src/domains/auth/tests/ -v

# 运行测试并生成覆盖率报告
pytest src/domains/auth/tests/ --cov=src/domains/auth --cov-report=html

# 运行特定测试
pytest src/domains/auth/tests/test_service.py::test_guest_init -v
```
"""