# Task微服务迁移文档

## 概述

本文档记录了Task domain到微服务的完整迁移过程，将原本在本地的任务管理功能迁移到独立的Task微服务(localhost:20252)。

## 迁移范围

### 替换的功能（8个端点）
1. **任务CRUD（5个）**：
   - POST /tasks - 创建任务
   - GET /tasks/{task_id} - 获取任务详情
   - PUT /tasks/{task_id} - 更新任务
   - DELETE /tasks/{task_id} - 删除任务
   - GET /tasks - 获取任务列表

2. **Top3管理（2个）**：
   - POST /tasks/special/top3 - 设置Top3任务
   - GET /tasks/special/top3/{date} - 获取Top3任务

3. **任务统计（1个）**：
   - GET /tasks/statistics - 获取任务统计信息

### 保留的功能（2个端点）
- POST /tasks/{task_id}/complete（任务完成和奖励分发）
- POST /tasks/{task_id}/uncomplete（取消任务完成）

## 技术架构

### 代理模式
采用HTTP代理模式，保持API路径和响应格式完全不变：

```
客户端 → 主API → 微服务代理 → Task微服务
```

### 核心组件

#### 1. HTTP客户端 (`src/services/task_microservice_client.py`)
- 功能：封装与Task微服务的HTTP通信
- 特性：
  - 异步HTTP调用
  - 响应格式转换
  - 错误处理和重试机制
  - 超时配置（连接5秒，读取30秒）
  - 单例模式管理

#### 2. 响应格式转换
微服务格式 → 本地格式：
```json
// 微服务格式
{
  "success": true,
  "data": {...}
}

// 转换后格式
{
  "code": 200,
  "data": {...},
  "message": "success"
}
```

#### 3. 字段处理
微服务缺失字段返回null：
- `parent_id`: null
- `tags`: []
- `service_ids`: []
- `planned_start_time`: null
- `planned_end_time`: null
- `last_claimed_date`: null
- `completion_percentage`: 0.0
- `is_deleted`: false

## 配置更新

### 环境变量 (.env)
```env
# Task微服务配置
TASK_SERVICE_URL=http://127.0.0.1:20252/api/v1
TASK_SERVICE_TIMEOUT=30
```

### API配置 (`src/api/config.py`)
```python
# Task微服务配置
task_service_url: str = Field(
    default="http://127.0.0.1:20252/api/v1",
    description="Task微服务URL"
)
task_service_timeout: int = Field(
    default=30,
    description="Task微服务调用超时时间(秒)"
)
```

## 数据库变更

### 删除的表
- `tasks` 表
- `task_top3` 表

### 删除的文件
- `src/domains/task/models.py`
- `src/domains/task/repository.py`
- `src/domains/task/service.py`
- `src/domains/top3/models.py`
- `src/domains/top3/repository.py`
- `src/domains/top3/service.py`

### 保留的文件
- `src/domains/task/completion_service.py`（任务完成逻辑）
- `src/domains/task/router.py`（改为代理实现）
- `src/domains/top3/router.py`（改为代理实现）

## 业务逻辑处理

### Top3积分扣除流程
1. 验证用户积分余额 ≥ 300
2. 扣除300积分（调用PointsService）
3. 调用微服务设置Top3
4. 若微服务失败，回滚积分（事务处理）

### 错误处理机制
- 连接失败 → 503 Service Unavailable
- 超时 → 504 Gateway Timeout
- 微服务4xx/5xx → 透传错误码

## 测试覆盖

### 单元测试
- ✅ HTTP客户端功能测试 (17/17通过)
- ✅ 响应格式转换测试
- ✅ 错误处理测试
- ✅ 超时机制测试
- 📊 测试覆盖率：93%

### 测试文件
- `tests/unit/services/test_task_microservice_client.py`

## 部署注意事项

### 依赖关系
- Task微服务必须正常运行 (localhost:20252)
- Points服务必须可用（Top3扣费）
- 现有认证中间件保持不变

### 启动顺序
1. 启动Task微服务 (端口20252)
2. 启动主API服务
3. 验证微服务健康状态

### 监控要点
- 微服务连接状态
- API响应时间（增加50-100ms延迟）
- 错误率监控
- 积分扣费一致性

## 回滚方案

如果需要回滚到本地实现：

1. 恢复数据库表
   ```bash
   # 使用备份文件恢复
   cp tatake_backup_before_microservice_migration.db tatake.db
   ```

2. 恢复源代码文件
   ```bash
   # 恢复原始router文件
   cp src/domains/task/router_original.py src/domains/task/router.py
   cp src/domains/top3/router_original.py src/domains/top3/router.py
   ```

3. 恢复domain文件（从git或备份）

## 性能影响

### 延迟增加
- 额外HTTP调用：+50-100ms
- 网络序列化开销：+5-10ms

### 资源消耗
- 增加HTTP连接池
- 增加网络I/O
- 减少本地数据库负载

## 维护建议

### 定期检查
1. 微服务健康状态
2. 网络连接稳定性
3. 错误日志监控
4. 性能指标跟踪

### 优化方向
1. 考虑gRPC替代HTTP（减少延迟）
2. 实现连接池复用优化
3. 添加缓存机制
4. 实现熔断器模式

## 联系方式

如有问题或建议，请联系：
- 技术团队：TaKeKe团队
- 文档更新：2025-01-31

---

**注意**：本文档描述的是Task微服务迁移的第一阶段实现，后续可能会根据实际运行情况进行优化调整。