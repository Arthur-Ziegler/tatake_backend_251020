## MODIFIED Requirements
### Requirement: Service Layer Organization
系统 SHALL使用统一的service层架构，避免重复服务实现。

#### Scenario: Service consolidation complete
- **WHEN** task和reward领域完成服务整合
- **THEN** 只保留service_v2版本作为主服务
- **AND** 所有API调用指向v2版本

## REMOVED Requirements
### Requirement: Legacy Service Support
**Reason**: 避免代码重复，简化维护
**Migration**: 使用service_v2版本替代