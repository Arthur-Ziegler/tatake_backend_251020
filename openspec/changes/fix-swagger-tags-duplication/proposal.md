# 修复Swagger UI Tags重复与配置过载

## 概述
修复API文档tags重复显示和配置过度复杂导致的Swagger UI崩溃问题，恢复符合TaKeKe_API方案_v3.md的设计。

## Why
当前Swagger UI完全不可用：
- **Tags重复**：每个API端点tags显示两次（router定义 + main.py强制覆盖）
- **Description缺失**：main.py清空了API描述
- **配置过载**：openapi.py添加了违反架构的路由定义和复杂扩展
- **冗余代码**：28行重复的api_prefix判断

## What Changes
1. **删除tags重复** - main.py的include_router移除tags参数（7处）
2. **恢复description** - main.py:95恢复API描述（1处）
3. **清理openapi.py** - 删除路由定义、x-扩展、冗余示例（3处）
4. **简化判断** - 删除api_prefix的if/else（28行→7行）

## 解决方案

### 修改src/api/main.py
- 删除所有include_router的tags参数（让router自身定义生效）
- 恢复description为"TaKeKe API服务，提供认证和任务管理功能"
- 简化api_prefix判断为直接传值

### 修改src/api/openapi.py
- 删除setup_openapi()中的/api-info和/docs-health路由
- 删除x-tag-groups、x-changelog扩展
- examples只保留SuccessResponse和ErrorResponse
- schemas保留全部（StandardResponse、ErrorResponse、PaginatedResponse）
- description精简为1句话
- tags_metadata删除externalDocs

## 实施范围
- src/api/main.py:95,256-293 - Tags重复 + Description + 简化判断
- src/api/openapi.py:26-94,217-312,431-478,484-554 - 配置精简

## 成功标准
- Swagger UI显示8个分组，无重复
- 所有API端点正常访问
- 符合TaKeKe_API方案_v3.md设计
- 代码减少约100行
