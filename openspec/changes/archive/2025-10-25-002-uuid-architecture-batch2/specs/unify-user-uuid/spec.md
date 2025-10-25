# Unify User Domain UUID Architecture

## MODIFIED Requirements

### Requirement: User Service UUID Implementation
UserService MUST实现UUID类型安全，移除字符串类型依赖。

#### Scenarios:
- **get_user_profile**: user_id参数使用UUID类型
- **update_user_profile**: user_id参数使用UUID类型
- **claim_welcome_gift**: user_id参数使用UUID类型
- **所有方法**: 移除字符串类型兼容性

### Requirement: User Router UUID Validation
User Router MUST实现UUID格式验证和422错误响应。

#### Scenarios:
- **JWT解析**: 从token提取的user_id转换为UUID对象
- **参数验证**: 验证UUID格式，无效返回422错误
- **错误消息**: "user_id必须是36字符UUID格式，如：550e8400-e29b-41d4-a716-446655440000"

## ADDED Requirements

### Requirement: User Repository Pattern
User领域MUST实现Repository模式，支持UUID转换。

#### Scenarios:
- **UserRepository**: 创建用户Repository类
- **UUID转换**: Repository层处理UUID↔String转换
- **查询方法**: 支持UUID参数的用户查询操作

### Requirement: User API UUID Documentation
User相关API的Swagger文档MUST包含UUID格式说明。

#### Scenarios:
- **GET /user/profile**: UUID格式参数文档
- **PUT /user/profile**: 请求体验证和错误示例
- **欢迎礼包API**: UUID格式验证和错误响应
- **所有User API**: 完整的UUID文档覆盖

### Requirement: User UUID Integration Tests
User领域MUST有完整的UUID集成测试。

#### Scenarios:
- **JWT到UUID转换**: 验证token解析的UUID转换
- **跨领域调用**: User到Task领域的UUID传递
- **错误处理**: 无效UUID格式的错误响应测试