# UUID Architecture Batch 2: Core Domain Unification

## Why
当前Task和User领域存在UUID类型不一致问题，导致以下风险：
1. Service层混合使用str和UUID参数，类型安全性不足
2. Repository层UUID转换逻辑分散，维护成本高
3. API文档缺少UUID格式说明，开发者体验差
4. 错误处理不统一，调试困难

需要统一核心业务域的UUID架构，确保类型安全和开发效率。

## What Changes
1. **Task领域重构**: 统一TaskService方法签名为UUID参数，实现TaskRepository UUID转换
2. **User领域实现**: 创建UserRepository和UUID转换逻辑，修改UserService为UUID类型安全
3. **类型验证增强**: 移除Union[str, UUID]参数，实现严格UUID类型
4. **API文档完善**: 更新Swagger包含详细UUID示例和错误说明
5. **测试覆盖**: 创建全面的UUID类型安全测试用例

## 概述
统一Task和User领域的UUID架构，实现核心业务功能的类型安全。

## 关键内容
- **Task领域**: 统一Service层UUID参数，Repository层转换逻辑
- **User领域**: 实现UUID类型安全的用户管理功能
- **API文档**: 完善Swagger UUID格式说明和错误示例
- **类型验证**: 422错误响应和严格UUID格式验证

## 备注
核心业务域的UUID统一，为后续扩展域奠定基础。包含完整的测试覆盖。