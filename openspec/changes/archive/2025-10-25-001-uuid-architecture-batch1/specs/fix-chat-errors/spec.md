# Fix Chat UUID Type Errors

## ADDED Requirements

### Requirement: Chat UUID Type Safety
聊天系统MUST接收UUID字符串参数时转换为UUID对象，MUST禁止字符串/数字比较操作。

#### Scenarios:
- **发送消息**: 当user_id为字符串格式时，转换为UUID对象再处理
- **消息查询**: 查询条件使用UUID对象而非字符串比较
- **会话管理**: session_id使用UUID类型，确保类型安全

## ADDED Requirements

### Requirement: Chat API UUID Validation
聊天API MUST验证UUID格式，MUST返回422错误和详细说明。

#### Scenarios:
- **POST /chat/sessions**: 验证user_id为36字符标准UUID格式
- **POST /chat/sessions/{session_id}/send**: 验证session_id格式
- **错误响应**: 返回422状态码 + "user_id必须是36字符UUID格式，如：550e8400-e29b-41d4-a716-446655440000"

### Requirement: Chat UUID Schema Documentation
Swagger文档 MUST包含UUID格式示例和错误说明。

#### Scenarios:
- **user_id参数**: 详细说明"36字符UUID格式，如：550e8400-e29b-41d4-a716-446655440000"
- **错误示例**: 提供422响应示例和格式说明
- **所有Chat API**: 涉及UUID的端点都要有完整文档