# 设计文档：Task微服务迁移

## 架构设计

### 整体架构
```
客户端
  ↓
主API (FastAPI)
  ↓ JWT验证
task/router.py (代理层)
  ↓ HTTP调用
Task微服务 (localhost:20252)
  ↓
微服务数据库 (PostgreSQL/SQLite)
```

## 关键设计决策

### 1. 代理模式 vs 直接路由
**选择**：代理模式
**理由**：
- API路径完全不变，前端无感知
- 可在代理层处理格式转换、积分扣除
- 灵活性高，便于后续优化

### 2. 响应格式转换
**微服务格式**：
```json
{
  "success": true,
  "data": {...}
}
```

**转换后格式**：
```json
{
  "code": 200,
  "data": {...},
  "message": "success"
}
```

**映射规则**：
- `success: true` → `code: 200`, `message: "success"`
- `success: false` → `code: 400/404/500`（根据错误类型）
- 错误时提取`message`字段

### 3. Top3积分扣除
**实现位置**：代理层（调用微服务前）
**流程**：
1. 验证用户积分余额 ≥ 300
2. 扣除300积分（调用PointsService）
3. 调用微服务设置Top3
4. 若微服务失败，回滚积分（事务处理）

### 4. 字段缺失处理
**策略**：返回null，前端容错
**影响**：
- 任务树结构功能暂时不可用（无parent_id）
- 完成度计算依赖本地逻辑（保留complete端点）

### 5. 认证流程
**不变**：继续使用现有JWT中间件
**user_id传递**：作为query parameter传给微服务

## 数据库迁移

### 删除表
- `tasks`表 → 删除
- `top3_tasks`表 → 删除

### 删除文件
- `src/domains/task/models.py` → 删除Task模型
- `src/domains/task/repository.py` → 删除
- `src/domains/task/service.py` → 删除（保留completion_service.py）
- `src/domains/top3/models.py` → 删除
- `src/domains/top3/repository.py` → 删除
- `src/domains/top3/service.py` → 删除

### 保留文件
- `src/domains/task/completion_service.py` → 保留（任务完成逻辑）
- `src/domains/task/router.py` → 改为代理实现
- `src/domains/top3/router.py` → 改为代理实现

## HTTP客户端设计

### 使用httpx
```python
import httpx

TASK_SERVICE_URL = "http://127.0.0.1:20252/api/v1"

async def call_task_service(method: str, path: str, **kwargs):
    async with httpx.AsyncClient() as client:
        response = await client.request(method, f"{TASK_SERVICE_URL}{path}", **kwargs)
        return transform_response(response)
```

### 超时配置
- 连接超时：5秒
- 读取超时：30秒

### 错误处理
- 连接失败 → 503 Service Unavailable
- 超时 → 504 Gateway Timeout
- 微服务4xx/5xx → 透传错误码

## 测试策略

### 单元测试
- Mock微服务HTTP调用
- 验证响应格式转换
- 验证Top3积分扣除逻辑

### 集成测试
- 启动真实微服务
- 验证完整调用链路
- 验证错误处理

### 回归测试
- 运行现有task相关测试
- 确保API行为完全一致

## 回滚计划
1. 恢复task/top3表结构（保留迁移文件）
2. 恢复原router.py实现
3. 恢复models/repository/service文件
4. 重新运行迁移脚本

## 性能考虑
- 增加HTTP调用延迟：预计50-100ms
- 微服务连接池复用（httpx.AsyncClient）
- 后续可考虑gRPC优化
