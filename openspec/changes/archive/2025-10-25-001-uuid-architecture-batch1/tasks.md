# Batch 1 Tasks: Emergency UUID Fixes

## 核心任务 (15个)

### 1. Schema兼容性修复 (优先级: 紧急)
- [x] 修复TaskStatus的Pydantic V2 core_schema方法 (使用Literal类型)
- [x] 修复TaskPriority的Pydantic V2 core_schema方法 (使用Literal类型)
- [x] 修复SessionType的Pydantic V2 core_schema方法 (src/domains/focus/models.py:59-68)
- [x] 验证Schema Registry注册成功 (src/api/schema_registry.py已导入)
- [x] 测试OpenAPI文档生成正常

### 2. Chat领域UUID修复 (优先级: 紧急)
- [x] 定位并修复聊天系统的字符串/数字比较错误 (src/domains/chat/service.py:修复UUID版本比较)
- [x] 实现Chat API的UUID格式验证 (src/domains/chat/tools/utils.py:safe_uuid_convert)
- [x] 添加Chat API的Swagger UUID文档 (已集成到schema_registry.py)
- [x] 创建Chat UUID类型安全测试 (tests/domains/chat/test_chat_type_safety.py)

### 3. Auth审计日志修复 (优先级: 高)
- [x] 修复AuthAuditLog的UUID类型绑定错误 (src/domains/auth/repository.py:UUIDConverter)
- [x] 完善AuthRepository的UUID转换逻辑 (src/domains/auth/repository.py:全面实现UUID转换)
- [x] 添加Auth审计UUID验证测试 (tests/domains/auth/test_auth_uuid_fixes.py)

### 4. 集成测试和验证 (优先级: 高)
- [x] 创建跨领域UUID集成测试 (tests/integration/test_uuid_architecture_integration.py)
- [x] 验证API错误响应格式正确 (tests/validation/test_api_parameters.py)
- [x] 确认Swagger文档完整性和准确性 (src/utils/api_validators.py)

## 依赖关系
- Schema修复 → Chat/Auth修复 (依赖)
- 单元测试 → 集成测试 (顺序)
- 代码修复 → 文档更新 (同步)

## 验收标准
- [x] 所有Pydantic V2 Schema注册成功 (TaskStatus/TaskPriority使用Literal，SessionType实现core_schema)
- [x] Chat系统无运行时错误 (UUID版本比较错误已修复)
- [x] Auth审计日志正常工作 (UUIDConverter实现类型转换)
- [x] API返回422错误而非500 (api_validators.py实现错误格式验证)
- [x] Swagger文档包含UUID示例和说明 (schema_registry.py完整导入)