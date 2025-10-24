## REMOVED Requirements
### Requirement: API Unit Tests
**Reason**: API测试应聚焦于端到端场景，而非单元测试
**Migration**: 使用tests/scenarios/下的场景测试替代

### Requirement: Integration Tests
**Reason**: 避免测试重复，scenarios测试更符合业务需求
**Migration**: 保留tests/scenarios/，删除tests/integration/

## MODIFIED Requirements
### Requirement: Scenario-Based Testing
系统 SHALL使用基于业务场景的测试方法。

#### Scenario: Complete test coverage
- **WHEN** 场景测试运行完成
- **THEN** 覆盖主要业务流程
- **AND** 确保API端到端功能正常