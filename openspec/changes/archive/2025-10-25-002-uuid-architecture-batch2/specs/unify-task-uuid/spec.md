# Unify Task Domain UUID Architecture

## MODIFIED Requirements

### Requirement: Task Service UUID Parameters
TaskService所有方法MUST使用UUID参数，移除Union类型支持。

#### Scenarios:
- **get_task**: user_id参数从Union[str, UUID]改为UUID
- **create_task**: user_id参数严格使用UUID类型
- **update_task**: user_id参数严格使用UUID类型
- **delete_task**: user_id参数严格使用UUID类型

### Requirement: Task Repository UUID Conversion
TaskRepository MUST实现标准UUID转换，移除ensure_str_uuid函数。

#### Scenarios:
- **查询方法**: 内部将UUID转换为字符串进行数据库操作
- **权限验证**: user_id比较使用UUID对象
- **批量操作**: UUID列表转换为字符串列表处理

## ADDED Requirements

### Requirement: Task API UUID Documentation
Task相关API的Swagger文档MUST包含UUID格式说明和错误示例。

#### Scenarios:
- **POST /tasks**: user_id参数文档"36字符UUID格式，如：550e8400-e29b-41d4-a716-446655440000"
- **PUT /tasks/{id}**: user_id参数和错误响应示例
- **GET /tasks**: 查询参数UUID格式验证
- **错误响应**: 422状态码和UUID格式说明

### Requirement: Task UUID Type Safety Tests
Task领域MUST有完整的UUID类型安全测试覆盖。

#### Scenarios:
- **Service层测试**: 验证UUID参数类型检查
- **Repository测试**: 验证UUID转换正确性
- **API测试**: 验证422错误响应格式
- **集成测试**: 跨领域UUID传递测试