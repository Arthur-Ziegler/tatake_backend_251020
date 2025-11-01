# Complete Task Microservice Migration

## 概述
基于对Task微服务(45.152.65.130:20253)的完整测试验证，将所有9个核心Task API完全迁移至微服务实现，解决现有混合架构中的路径不匹配和功能缺失问题，实现统一高效的微服务架构。

## 背景
经过详细测试发现，Task微服务已经完全可用且功能强大：
- ✅ 9个核心API全部正常工作
- ✅ 100%测试覆盖率(129个测试通过)
- ✅ 包含完整的奖励系统集成
- ✅ 标准RESTful设计和统一响应格式

但是当前客户端实现存在以下问题：
- ❌ API路径不匹配：客户端期望`/tasks/{task_id}`，微服务提供`/tasks/{user_id}/{task_id}`
- ❌ UUID格式要求：微服务严格要求UUID格式，客户端可能传递字符串
- ❌ 混合架构：部分功能本地实现，部分微服务代理，架构不一致

## 目标
1. **完全迁移至微服务**：移除所有本地Task实现，统一使用微服务
2. **解决路径不匹配**：适配微服务的RESTful路径结构
3. **修复UUID格式问题**：确保所有ID传递符合UUID标准
4. **统一响应处理**：移除不必要的格式转换，直接使用微服务响应
5. **增强功能体验**：利用微服务的奖励系统等高级功能

## 范围

### 迁移的API (9个全部)
| 序号 | 功能 | 当前路径 | 微服务路径 | 迁移策略 |
|------|------|----------|------------|----------|
| 1 | 查询任务 | `POST /tasks/query` | `GET /api/v1/tasks/{user_id}` | 路径重写 |
| 2 | 创建任务 | `POST /tasks` | `POST /api/v1/tasks` | 路径适配 |
| 3 | 更新任务 | `PUT /tasks/{task_id}` | `PUT /api/v1/tasks/{user_id}/{task_id}` | 路径重写 |
| 4 | 删除任务 | `DELETE /tasks/{task_id}` | `DELETE /api/v1/tasks/{user_id}/{task_id}` | 路径重写 |
| 5 | 设置Top3 | `POST /tasks/top3` | `POST /api/v1/tasks/top3` | 路径适配 |
| 6 | 查询Top3 | `POST /tasks/top3/query` | `GET /api/v1/tasks/top3/{user_id}/{date}` | 路径重写 |
| 7 | 完成任务 | `POST /tasks/{task_id}/complete` | `POST /api/v1/tasks/{user_id}/{task_id}/complete` | 路径重写 |
| 8 | 专注状态 | `POST /tasks/focus-status` | `POST /api/v1/focus/sessions` | 路径重写 |
| 9 | 番茄计数 | `GET /tasks/pomodoro-count` | `GET /api/v1/pomodoros/count` | 路径重写 |

### 移除的本地实现
- `src/domains/task/database_local*.py` - 本地数据库操作
- `src/domains/task/service_local.py` - 本地业务逻辑
- `src/domains/task/models_local.py` - 本地数据模型
- `src/domains/task/completion_service.py` - 本地完成逻辑（已被微服务替代）
- 专注状态和番茄钟本地实现

### 保留的文件
- `src/domains/task/router.py` - 改造为纯代理
- `src/services/task_microservice_client.py` - 增强功能
- 相关测试文件 - 更新为微服务测试

## 技术方案

### 1. 路径映射策略
```python
# 新的路径映射逻辑
path_mappings = {
    # 查询任务
    "POST /tasks/query": "GET /api/v1/tasks/{user_id}",

    # 单个任务操作 (需要user_id参数)
    "PUT /tasks/{task_id}": "PUT /api/v1/tasks/{user_id}/{task_id}",
    "DELETE /tasks/{task_id}": "DELETE /api/v1/tasks/{user_id}/{task_id}",
    "POST /tasks/{task_id}/complete": "POST /api/v1/tasks/{user_id}/{task_id}/complete",

    # Top3操作
    "POST /tasks/top3/query": "GET /api/v1/tasks/top3/{user_id}/{date}",

    # 专注和番茄钟
    "POST /tasks/focus-status": "POST /api/v1/focus/sessions",
    "GET /tasks/pomodoro-count": "GET /api/v1/pomodoros/count"
}
```

### 2. UUID验证增强
```python
from uuid import UUID

def validate_and_convert_uuid(user_id: str) -> str:
    """验证并转换UUID格式"""
    try:
        UUID(user_id)  # 验证格式
        return user_id
    except ValueError:
        raise ValueError(f"Invalid UUID format: {user_id}")
```

### 3. 响应格式统一
微服务响应格式已符合标准，无需转换：
```json
{
  "code": 200,
  "success": true,
  "message": "操作成功",
  "data": {...}
}
```

### 4. 错误处理优化
- 网络超时：返回504状态码
- 连接失败：返回503状态码
- 微服务4xx/5xx：直接透传
- UUID格式错误：返回400状态码

## 架构优势
1. **统一性**：所有Task功能通过微服务提供，架构一致
2. **性能**：利用微服务的优化和缓存机制
3. **功能**：获得完整的奖励系统集成
4. **维护**：单一数据源，避免数据不一致
5. **扩展**：微服务的独立扩展和部署能力

## 风险与缓解

### 网络依赖风险
- **风险**：微服务不可用时所有Task功能失效
- **缓解**：实现连接池、重试机制和降级策略

### 延迟增加
- **风险**：增加网络调用延迟
- **缓解**：异步调用、连接复用和性能监控

### 数据迁移
- **风险**：现有本地数据可能丢失
- **缓解**：备份现有数据，提供数据迁移工具

## 依赖
- Task微服务稳定运行(45.152.65.130:20253)
- 认证微服务提供用户身份验证
- 网络连接稳定

## 验收标准
1. 所有9个API完全通过微服务实现
2. 现有功能测试100%通过
3. 性能指标：API响应时间 < 300ms
4. 错误处理：网络异常时正确降级
5. 数据一致性：用户数据无丢失

## 成功指标
- 微服务调用成功率 > 99%
- API响应时间 < 300ms
- 测试覆盖率 > 95%
- 用户功能完整可用
- 系统稳定性提升