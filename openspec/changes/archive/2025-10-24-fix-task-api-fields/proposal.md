# 修复任务API字段映射与核心逻辑缺陷

## 问题背景

在测试任务相关API时，发现7个核心问题导致API返回数据不完整、部分API报500错误：

### 🔴 严重问题（导致500错误）
1. **缺失Service方法**：router调用了不存在的`update_task_with_tree_structure`和`delete_task`方法
2. **SQL查询字段缺失**：get_tasks方法只查询了7个字段，遗漏了tags、service_ids、priority等8个关键字段
3. **任务完成逻辑错误**：service.py中通过任务标题判断Top3（错误），应使用top3_service
4. **uncomplete_task类型错误**：对Dict对象调用model_dump()方法

### 🟡 数据设计问题
5. **level和path字段混乱**：数据库表中不存在，但Schema要求返回，代码中硬编码假数据
6. **计算字段冗余**：is_overdue和duration_minutes应由前端计算
7. **user_id暴露**：安全考虑不应返回
8. **service_ids缺失**：模型中有但Schema中未定义
9. **last_claimed_date未设置**：任务完成时未更新此字段，导致防刷机制失效

## 解决方案

### 设计原则
1. **KISS原则**：删除level/path复杂树结构字段，简化为parent_id关系
2. **前后端职责分离**：计算字段由前端负责
3. **安全优先**：不返回敏感的user_id字段
4. **数据完整性**：确保所有模型字段正确映射到API响应

### 提案分解策略

本提案分为**5个可并行的子任务**和**1个依赖任务**：

#### 阶段1：独立清理任务（可100%并行执行）⚡

- **1.1** - 删除level和path字段
- **1.2** - 删除is_overdue和duration_minutes字段
- **1.3** - 修复TaskResponse Schema（删除user_id，添加service_ids）
- **1.4** - 修复SQL查询字段映射
- **1.5** - 实现缺失的Service方法

#### 阶段2：依赖任务（需等待1.4完成）🔗

- **2** - 修复任务完成逻辑（依赖1.4的SQL修复）

### 实施计划

**并行度**：5个任务可同时开工，大幅缩短交付时间

**风险控制**：
- 每个子任务都有独立的测试验证
- 阶段1完成后统一回归测试
- 阶段2依赖明确，避免冲突

## 技术影响分析

### 影响范围
- ✅ 所有任务相关API端点
- ✅ TaskResponse Schema定义
- ✅ Task模型和Repository层
- ✅ 任务完成奖励逻辑

### 破坏性变更
- ⚠️ API响应中删除：`user_id`, `is_overdue`, `duration_minutes`, `level`, `path`
- ⚠️ API响应中添加：`service_ids`（当前返回空数组`[]`）
- ✅ 前端需要自行计算is_overdue和duration_minutes

### 兼容性保证
- 统一响应格式保持不变：`{code, message, data}`
- 所有必需字段正确返回
- 现有测试用例需要更新

## 验收标准

### 功能验收
- [ ] 任务创建API返回完整字段（tags, service_ids, due_date等）
- [ ] 任务列表API返回完整字段
- [ ] 任务详情API返回完整字段
- [ ] 任务更新API正常工作（200响应）
- [ ] 任务删除API正常工作（200响应）
- [ ] 任务完成API设置last_claimed_date
- [ ] 任务取消完成API正常工作（200响应）

### 数据验收
- [ ] 响应中不包含：user_id, is_overdue, duration_minutes, level, path
- [ ] 响应中包含：service_ids（空数组）
- [ ] tags字段正确序列化JSON数据
- [ ] 所有时间字段正确返回

### 测试验收
- [ ] 所有单元测试通过
- [ ] 所有API scenario测试通过
- [ ] 端到端测试覆盖完整流程

## 后续工作

1. 前端适配新的响应格式
2. 更新API文档和示例
3. 监控生产环境API错误率

---

**提案人**：Claude Code
**创建日期**：2025-10-24
**预估工时**：8小时（并行执行可缩短至3小时）
**优先级**：🔴 P0（阻塞线上功能）
