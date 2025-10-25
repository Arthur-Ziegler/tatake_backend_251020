# Fix Auth Audit UUID Type Errors

## ADDED Requirements

### Requirement: AuthAuditLog UUID Handling
AuthAuditLog的user_id字段 MUST支持UUID对象转换，MUST解决"Expected UUID object, got str"错误。

#### Scenarios:
- **创建日志**: Repository层接收UUID对象，转换为字符串存储
- **查询日志**: user_id查询支持UUID参数输入
- **批量操作**: 支持UUID列表的批量日志操作

## ADDED Requirements

### Requirement: Auth Repository UUID Conversion
AuthRepository MUST实现完整的UUID↔String转换机制。

#### Scenarios:
- **create_audit_log**: 接收UUID对象，内部转换为字符串
- **get_user_audit_logs**: 支持UUID参数查询
- **批量查询**: UUID列表转换为字符串列表处理

### Requirement: Auth Audit Error Handling
审计日志创建失败时 MUST提供详细错误信息和UUID格式说明。

#### Scenarios:
- **UUID验证**: 验证user_id格式，无效时返回422错误
- **错误消息**: "user_id必须是36字符UUID格式，如：550e8400-e29b-41d4-a716-446655440000"
- **Swagger文档**: 审计相关API包含UUID格式说明