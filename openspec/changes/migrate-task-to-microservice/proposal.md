# Migrate Task Domain to Microservice

## 概述
将task domain的基础CRUD和Top3功能迁移至task微服务(localhost:20252)，采用代理模式保持API完全兼容，删除本地task/top3数据表。

## 目标
- 替换任务CRUD、Top3设置/查询为微服务代理
- 保留任务完成/取消完成逻辑（依赖奖励系统）
- 删除task、top3数据表及相关模型
- API路径、响应格式、认证方式完全不变

## 范围

### 替换功能（8个端点）
1. **任务CRUD（5个）**：POST/GET/PUT/DELETE /tasks, GET /tasks
2. **Top3管理（2个）**：POST/GET /tasks/special/top3
3. **任务统计（1个）**：新增GET /tasks/statistics

### 保留功能（2个端点）
- POST /tasks/{task_id}/complete（含积分/抽奖）
- POST /tasks/{task_id}/uncomplete

### 数据库清理
- 删除`tasks`表
- 删除`top3_tasks`表
- 删除相关模型：`Task`, `Top3Task`

## 技术方案

### 代理模式
在`task/router.py`和`top3/router.py`中实现HTTP代理：
1. 保持现有路由路径
2. 解析JWT获取user_id
3. 调用微服务API（http://127.0.0.1:20252/api/v1）
4. 转换响应格式：`{success, data}` → `{code, data, message}`
5. Top3设置前扣除300积分

### 字段处理
微服务缺失字段返回null：
- `parent_id`, `tags`, `service_ids`, `planned_start_time`, `planned_end_time`
- `last_claimed_date`, `completion_percentage`, `is_deleted`

### 状态枚举
采用微服务枚举：
- `todo`, `inprogress`, `completed`（不做映射转换）

## 依赖
- 微服务正常运行（localhost:20252）
- Points服务可用（Top3扣费）
- 现有认证中间件不变

## 风险
- 微服务字段缺失可能影响前端显示
- 网络延迟增加（多一层HTTP调用）
- 微服务宕机影响全部任务功能

## 验收标准
1. 所有替换端点功能与原API完全一致
2. 现有测试用例100%通过
3. Top3设置正确扣除300积分
4. task/top3表已删除，应用正常运行
