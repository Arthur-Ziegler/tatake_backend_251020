# 迁移所有剩余领域到FastAPI原生响应模型

## 目标
将Task、Chat、Focus、Reward、Top3、User共6个领域的31个API端点从JSONResponse/dict迁移到FastAPI原生Pydantic泛型响应模型，并统一Service层返回格式。

## 动机
Auth领域迁移已验证成功，泛型`UnifiedResponse[T]`方案完美解决Swagger UI显示问题。现需将成功经验推广到所有剩余领域，实现项目级架构统一。

**关键问题**：当前各领域Service层返回值类型不一致（部分返回dict，部分返回模型实例），违反架构一致性原则。

## 方案
**F1泛型统一方案 + G1 Service层标准化 + H2异常处理 + I1自动化验证**：
1. 所有领域使用`UnifiedResponse[T]`泛型模型
2. **强制要求**：所有Service方法统一返回dict，绝不返回Pydantic/SQLModel实例
3. 路由层直接返回错误UnifiedResponse（与Auth一致）
4. 自动化pytest测试验证

### 覆盖领域
1. **Task领域** - 7个端点 - TaskResponse/TaskListResponse/TaskDeleteResponse
2. **Chat领域** - 7个端点 - ChatSessionResponse/MessageResponse/ChatHistoryResponse
3. **Focus领域** - 5个端点 - FocusSessionResponse/FocusSessionListResponse
4. **Reward领域** - 6个端点 - RewardResponse/RecipeResponse/MaterialsResponse
5. **Top3领域** - 2个端点 - Top3Response
6. **User领域** - 4个端点 - UserProfileResponse

## 核心改动

### 1. Service层强制标准化（新增，关键！）
**强制要求**：所有Service方法统一返回`Dict[str, Any]`，绝不返回模型实例。

**改造范围**：
- **Task Service**: `get_task()` 从返回`Task`改为返回`dict`
- **其他Service**: 检查并统一所有返回值为dict

**改造模式**：
```python
# ❌ 错误：返回模型实例
def get_task(self, task_id: UUID, user_id: UUID) -> Task:
    return self.repository.get(task_id)

# ✅ 正确：返回dict
def get_task(self, task_id: UUID, user_id: UUID) -> Dict[str, Any]:
    task = self.repository.get(task_id)
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        ...  # 完整字段映射
    }
```

### 2. Schema层统一
- **改造UnifiedResponse为泛型**（在Auth中已完成）
- **删除所有Wrapper类**：TaskCreateResponse、ChatSessionResponseWrapper等
- **保留业务数据模型**：TaskResponse、ChatSessionResponse等

### 3. 路由层标准化
**统一模式（与Auth完全一致）**：
```python
@router.post("/endpoint", response_model=UnifiedResponse[DataModel])
async def endpoint(...) -> UnifiedResponse[DataModel]:
    try:
        result = service.method(...)  # 必须返回dict
        return UnifiedResponse(
            code=200,
            data=DataModel(**result),  # dict转Pydantic
            message="success"
        )
    except SomeException as e:
        return UnifiedResponse(  # 直接返回错误响应
            code=400,
            data=None,
            message=str(e)
        )
```

### 4. 异常处理统一（H2方案）
**不使用HTTPException**，路由层直接返回错误UnifiedResponse，与Auth领域保持一致。

## 技术细节

### Task领域改造
- **删除**：TaskCreateResponse、TaskGetResponse、TaskUpdateResponse等7个Wrapper类
- **保留**：TaskResponse、TaskListResponse、TaskDeleteResponse（业务数据模型）
- **迁移**：7个端点（create/get/update/delete/list/complete/uncomplete）

### Chat领域改造
- **删除**：所有`response_model=dict`声明
- **保留**：ChatSessionResponse、MessageResponse、ChatHistoryResponse等
- **迁移**：7个端点（create/send/history/info/list/delete/health）

### Focus领域改造
- **保留**：FocusSessionResponse、FocusSessionListResponse
- **迁移**：5个端点（start/pause/resume/complete/list）

### Reward领域改造
- **删除**：UserMaterialsResponseWrapper、AvailableRecipesResponseWrapper
- **保留**：RewardResponse、RecipeMaterial、UserMaterial等
- **迁移**：6个端点（catalog/my-rewards/exchange/materials/recipes/redeem）

### Top3领域改造
- **保留**：Top3Response、GetTop3Response
- **迁移**：2个端点（set/get）

### User领域改造
- **保留**：UserProfileResponse、FeedbackResponse
- **迁移**：4个端点（profile/update/avatar/feedback）

## 影响范围
- **Schema文件**：6个领域的schemas.py - 删除Wrapper类，保留数据模型
- **路由文件**：6个领域的router.py/api.py - 改造31个端点
- **Service层**：无需改动
- **前端接口**：响应格式完全不变

## 验证标准

### 自动化测试验证（I1方案）
- [ ] **pytest单元测试**：每个端点至少1个成功+1个失败用例
- [ ] **Service层测试**：验证所有方法返回dict而非模型实例
- [ ] **OpenAPI JSON验证**：自动化脚本检查schema完整性
- [ ] **类型检查**：mypy验证返回类型一致性

### 功能验证
- [ ] Swagger UI正确显示所有31个端点的响应schema
- [ ] 所有端点的响应示例完整显示（包含data字段内容）
- [ ] 现有集成测试全部通过
- [ ] 前端调用无需改动

### 架构一致性验证
- [ ] **零容忍**：检查代码中不存在Service返回模型实例的情况
- [ ] 所有端点异常处理使用统一模式（返回UnifiedResponse）
- [ ] 删除所有Wrapper类，代码中无残留

## 分阶段执行
按领域并行执行，互不依赖：
- **阶段1**：Task + Focus（12个端点，相对简单）
- **阶段2**：Chat + User（11个端点，中等复杂度）
- **阶段3**：Reward + Top3（8个端点，复杂但端点少）

## 后续工作
- 清理`src/api/responses.py`中未使用的辅助函数
- 更新API文档和使用示例
- 性能基准测试对比
