# UUID Architecture Batch 1 Design

## 架构决策
- **严格类型**: Service层仅接受UUID对象，拒绝字符串参数
- **Repository转换**: Repository层负责UUID↔String双向转换
- **错误处理**: API层返回422错误+详细UUID格式说明
- **Schema统一**: 所有自定义枚举类型支持Pydantic V2

## 技术要求
- 标准UUID格式验证（36字符带连字符）
- Swagger文档包含示例和错误说明
- 聊天系统修复字符串/数字比较逻辑
- 审计日志支持UUID类型绑定

## 风险控制
- 分批实施，优先修复运行时错误
- 每个修复包含对应测试用例
- 保持现有API契约不变