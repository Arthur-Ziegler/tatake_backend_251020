# 设计文档

## 技术决策

### 决策1：统一使用泛型方案
**选择**：F1 - 全部使用`UnifiedResponse[T]`泛型
**原因**：
- ✅ Auth领域已验证成功
- ✅ 最大程度减少代码冗余
- ✅ 完全符合KISS原则
- ✅ 所有领域统一标准

**被拒绝方案**：F2 - 保留Wrapper类
**拒绝原因**：增加维护成本，违反DRY原则

### 决策2：删除所有Wrapper类
**删除清单**：
- Task: `TaskCreateResponse`, `TaskGetResponse`, `TaskUpdateResponse`, `TaskDeleteResponseWrapper`, `TaskListResponseWrapper`, `TaskCompleteResponseWrapper`, `TaskUncompleteResponseWrapper`
- Reward: `UserMaterialsResponseWrapper`, `AvailableRecipesResponseWrapper`, `RedeemRecipeResponseWrapper`

**保留清单**（业务数据模型）：
- Task: `TaskResponse`, `TaskListResponse`, `TaskDeleteResponse`, `CompleteTaskResponse`, `UncompleteTaskResponse`
- Chat: `ChatSessionResponse`, `MessageResponse`, `ChatHistoryResponse`, `SessionInfoResponse`, `SessionListResponse`
- Focus: `FocusSessionResponse`, `FocusSessionListResponse`, `FocusOperationResponse`
- Reward: `RewardResponse`, `RecipeMaterial`, `UserMaterial`, `AvailableRecipe`, `RedeemRecipeResponse`
- Top3: `Top3Response`, `GetTop3Response`
- User: `UserProfileResponse`, `FeedbackResponse`

### 决策3：分阶段并行执行
**原因**：
- ✅ 各领域完全独立，无依赖关系
- ✅ 并行执行可缩短总工期至1/3
- ✅ 单个领域失败不影响其他领域
- ✅ 便于Code Review和验证

**执行建议**：
1. 优先执行简单领域（Task、Focus）- 快速建立信心
2. 其次执行中等领域（Chat、User）- 积累经验
3. 最后执行复杂领域（Reward、Top3）- 应用最佳实践

### 决策4：Service层保持不变
**原因**：
- ✅ Service层继续返回dict/业务对象
- ✅ 路由层负责转换为Pydantic模型
- ✅ 符合单一职责原则
- ✅ 最小化改动范围

## 各领域技术细节

### Task领域
**挑战**：最多端点（7个），复杂响应结构
**解决方案**：
- 完成任务响应包含多个子结构（lottery_result、parent_update）
- 使用`Dict[str, Any]`保持灵活性
- 关键字段使用明确类型

**改造示例**：
```python
# 删除
class TaskCreateResponse(UnifiedResponse):
    data: TaskResponse

# 改为路由中使用
@router.post("/", response_model=UnifiedResponse[TaskResponse])
async def create_task(...) -> UnifiedResponse[TaskResponse]:
    ...
```

### Chat领域
**挑战**：部分端点使用`response_model=dict`
**解决方案**：
- 已有完整Schema定义（ChatSessionResponse等）
- 直接替换为`UnifiedResponse[ChatSessionResponse]`
- 删除所有`response_model=dict`

**特殊处理**：
- `/chat/health`端点返回`ChatHealthResponse`
- `/chat/sessions/{id}/messages`返回列表需包装为数据结构

### Focus领域
**挑战**：最简单，已有FocusOperationResponse
**解决方案**：
- 直接使用`UnifiedResponse[FocusSessionResponse]`
- FocusOperationResponse可能需要调整为数据模型

### Reward领域
**挑战**：已有部分Wrapper类使用
**解决方案**：
- 删除3个Wrapper类
- 保留业务数据模型
- 统一使用泛型方式

### Top3领域
**挑战**：当前使用`response_model=dict`
**解决方案**：
- 已有Top3Response和GetTop3Response
- 直接替换为泛型方式

### User领域
**挑战**：简单直接
**解决方案**：
- 4个端点统一处理
- UserProfileResponse已定义完整

## 风险与缓解

### 风险1：大规模改动导致回归问题
**缓解**：
- 分阶段执行，每个阶段独立验证
- 运行完整测试套件
- 保持Service层不变，降低影响面

### 风险2：复杂响应结构转换失败
**缓解**：
- 优先处理简单领域建立信心
- 对复杂结构使用`Dict[str, Any]`保持灵活性
- 详细测试每个端点的响应格式

### 风险3：并行开发导致冲突
**缓解**：
- 各领域文件完全独立
- 只有UnifiedResponse是共享资源（已在Auth中完成）
- 使用Git分支隔离各领域改动

### 风险4：测试覆盖不足
**缓解**：
- 阶段7专门用于验证
- Swagger UI手动检查
- OpenAPI JSON自动化验证

## 实施原则

1. **一致性优先**：所有领域使用相同模式
2. **最小改动**：只改路由层，不动Service
3. **保持兼容**：响应格式对前端完全透明
4. **充分测试**：每个阶段独立验证
5. **文档同步**：及时更新API文档

## 成功标准

### 功能标准
- [ ] 所有31个端点正常工作
- [ ] 响应格式保持`{code, data, message}`
- [ ] 前端调用无需任何改动

### 质量标准
- [ ] Swagger UI完整显示所有schema
- [ ] OpenAPI JSON包含所有数据模型
- [ ] 现有测试100%通过
- [ ] 代码审查无重大问题

### 性能标准
- [ ] 响应时间无明显增加（<5%）
- [ ] Pydantic验证开销可接受
- [ ] 无内存泄漏或性能回退
