# Complete Task Microservice Migration - Design Document

## 架构决策

### 1. 代理模式增强

#### 当前问题分析
基于测试发现，现有的`TaskMicroserviceClient`存在以下设计问题：

1. **路径映射不完整**：只覆盖了部分API路径
2. **UUID格式处理缺失**：未验证微服务要求的UUID格式
3. **响应转换冗余**：微服务响应格式已符合标准，无需转换
4. **错误处理不完善**：缺少针对网络问题的优雅降级

#### 新的代理架构设计

```python
class EnhancedTaskMicroserviceClient:
    """增强版Task微服务客户端"""

    def __init__(self):
        self.base_url = "http://45.152.65.130:20253/api/v1"
        self.path_mappings = self._build_path_mappings()

    def _build_path_mappings(self) -> Dict[str, str]:
        """构建路径映射表"""
        return {
            # 查询任务：POST query → GET with user_id
            ("POST", "tasks/query"): ("GET", "tasks/{user_id}"),

            # 单个任务CRUD：需要user_id路径参数
            ("PUT", "tasks/{task_id}"): ("PUT", "tasks/{user_id}/{task_id}"),
            ("DELETE", "tasks/{task_id}"): ("DELETE", "tasks/{user_id}/{task_id}"),
            ("POST", "tasks/{task_id}/complete"): ("POST", "tasks/{user_id}/{task_id}/complete"),

            # Top3管理
            ("POST", "tasks/top3/query"): ("GET", "tasks/top3/{user_id}/{date}"),

            # 专注和番茄钟
            ("POST", "tasks/focus-status"): ("POST", "focus/sessions"),
            ("GET", "tasks/pomodoro-count"): ("GET", "pomodoros/count")
        }
```

### 2. 路径重写策略

#### 动态路径构建
```python
def rewrite_path(self, method: str, original_path: str, user_id: str, **kwargs) -> str:
    """根据映射规则重写API路径"""

    key = (method.upper(), original_path)

    if key not in self.path_mappings:
        return original_path  # 无需映射

    new_method, new_path_template = self.path_mappings[key]

    # 构建新路径
    if "{task_id}" in new_path_template:
        task_id = kwargs.get("task_id")
        if not task_id:
            raise ValueError("task_id is required for this operation")
        return new_path_template.format(user_id=user_id, task_id=task_id)

    elif "{date}" in new_path_template:
        date = kwargs.get("date")
        if not date:
            raise ValueError("date is required for this operation")
        return new_path_template.format(user_id=user_id, date=date)

    elif "{user_id}" in new_path_template:
        return new_path_template.format(user_id=user_id)

    else:
        return new_path_template
```

### 3. UUID验证机制

#### 严格的格式验证
```python
from uuid import UUID
import re

class UUIDValidator:
    """UUID格式验证器"""

    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """验证用户ID格式"""
        if not user_id:
            raise ValueError("user_id cannot be empty")

        try:
            UUID(user_id)
            return user_id
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {user_id}")

    @staticmethod
    def validate_task_id(task_id: str) -> str:
        """验证任务ID格式"""
        if not task_id:
            raise ValueError("task_id cannot be empty")

        try:
            UUID(task_id)
            return task_id
        except ValueError:
            raise ValueError(f"Invalid UUID format for task_id: {task_id}")
```

### 4. 响应处理优化

#### 直接透传策略
由于微服务响应格式已符合标准，采用直接透传：

```python
async def call_microservice(
    self,
    method: str,
    path: str,
    user_id: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """调用微服务API"""

    # 1. 验证UUID格式
    validated_user_id = UUIDValidator.validate_user_id(user_id)

    # 2. 重写路径
    new_path = self.rewrite_path(method, path, validated_user_id, **kwargs)
    full_url = f"{self.base_url}/{new_path.lstrip('/')}"

    # 3. 准备请求参数
    request_data = data.copy() if data else {}
    if method.upper() in ["POST", "PUT", "PATCH"]:
        request_data["user_id"] = validated_user_id

    # 4. 发送HTTP请求
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.request(
            method=method.upper(),
            url=full_url,
            json=request_data,
            params=params,
            headers=self._get_headers()
        )

    # 5. 直接返回微服务响应（无需格式转换）
    return response.json()
```

### 5. 错误处理与降级

#### 分层错误处理
```python
class TaskMicroserviceError(Exception):
    """微服务调用异常"""
    def __init__(self, message: str, status_code: int = 500, is_recoverable: bool = False):
        self.message = message
        self.status_code = status_code
        self.is_recoverable = is_recoverable
        super().__init__(self.message)

class ErrorHandlingStrategy:
    """错误处理策略"""

    @staticmethod
    def handle_network_error(error: Exception) -> TaskMicroserviceError:
        """处理网络错误"""
        if isinstance(error, httpx.ConnectError):
            return TaskMicroserviceError(
                "Task微服务连接失败，请稍后重试",
                status_code=503,
                is_recoverable=True
            )
        elif isinstance(error, httpx.TimeoutException):
            return TaskMicroserviceError(
                "Task微服务响应超时，请稍后重试",
                status_code=504,
                is_recoverable=True
            )
        else:
            return TaskMicroserviceError(
                f"网络异常: {str(error)}",
                status_code=500,
                is_recoverable=True
            )
```

## 数据流设计

### 1. 请求处理流程
```
客户端请求 → JWT验证 → 路由匹配 → UUID验证 → 路径重写 → 微服务调用 → 响应返回
```

### 2. 具体API流程示例

#### 查询任务列表
```
POST /tasks/query
    ↓
提取user_id (UUID验证)
    ↓
重写为: GET /api/v1/tasks/{user_id}
    ↓
调用微服务: GET http://45.152.65.130:20253/api/v1/tasks/{user_id}
    ↓
直接返回微服务响应
```

#### 更新任务
```
PUT /tasks/{task_id}
    ↓
提取user_id + task_id (双UUID验证)
    ↓
重写为: PUT /api/v1/tasks/{user_id}/{task_id}
    ↓
调用微服务: PUT http://45.152.65.130:20253/api/v1/tasks/{user_id}/{task_id}
    ↓
直接返回微服务响应
```

## 性能优化策略

### 1. 连接池管理
```python
class ConnectionPoolManager:
    """连接池管理器"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

    async def close(self):
        """关闭连接池"""
        await self.client.aclose()
```

### 2. 缓存策略
```python
class TaskCacheManager:
    """任务缓存管理器"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存

    async def get_cached_tasks(self, user_id: str) -> Optional[List[Dict]]:
        """获取缓存的任务列表"""
        cache_key = f"tasks:{user_id}"
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return data
        return None
```

## 兼容性保证

### 1. API接口兼容
- 保持所有现有API路径不变
- 保持请求/响应格式不变
- 保持错误码和错误信息格式不变

### 2. 功能兼容
- 确保所有现有功能正常工作
- 保持业务逻辑一致性
- 维护数据完整性

### 3. 性能兼容
- 确保响应时间在可接受范围内
- 保持并发处理能力
- 维护系统稳定性

## 测试策略

### 1. 单元测试
- UUID验证逻辑测试
- 路径重写逻辑测试
- 错误处理逻辑测试
- 响应格式测试

### 2. 集成测试
- 完整API调用链测试
- 微服务连接测试
- 错误场景测试
- 性能基准测试

### 3. 回归测试
- 现有功能测试用例
- 前端兼容性测试
- 数据一致性测试

## 监控与维护

### 1. 关键指标监控
- API响应时间
- 微服务调用成功率
- 错误率统计
- 并发处理能力

### 2. 日志管理
- 结构化日志记录
- 错误日志追踪
- 性能日志分析
- 审计日志管理

### 3. 健康检查
- 微服务连接状态检查
- API可用性检查
- 性能指标检查
- 自动故障恢复