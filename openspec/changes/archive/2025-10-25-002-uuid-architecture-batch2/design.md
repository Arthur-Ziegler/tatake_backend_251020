# UUID Architecture Batch 2 Design

## 架构决策
- **统一接口**: TaskService和UserService仅接受UUID参数
- **Repository转换**: 实现TaskRepository和UserRepository的UUID转换
- **类型安全**: 移除所有Union[str, UUID]参数，严格UUID类型
- **文档完善**: Swagger包含详细UUID示例和错误说明

## 技术要求
- Service层方法签名统一为UUID参数
- 移除现有的ensure_str_uuid等临时转换函数
- Repository层实现标准UUID转换模式
- API层422错误响应和详细说明

## 风险控制
- 保持现有API契约，只修改内部实现
- 分步骤重构，每步包含测试验证
- 向后兼容UUID字符串格式输入