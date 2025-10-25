# 任务清单

## 实施任务（顺序执行）

1. ✅ **修复main.py的tags重复**
   - ✅ 删除7个include_router的tags参数
   - ✅ 验证：检查代码不含tags=参数

2. ✅ **恢复main.py的description**
   - ✅ main.py:95恢复API描述
   - ✅ 验证：description不为空

3. ✅ **简化api_prefix判断逻辑**
   - ✅ 删除if/else，直接传prefix
   - ✅ 验证：代码从28行缩减到7行

4. ✅ **精简openapi.py配置**
   - ✅ 删除/api-info、/docs-health路由定义
   - ✅ 删除x-tag-groups、x-changelog
   - ✅ examples保留2个核心示例
   - ✅ 添加UnifiedResponse schema定义
   - ✅ tags_metadata删除externalDocs
   - ✅ 验证：openapi.py减少约80行

5. ✅ **测试API启动**
   - ✅ 访问/docs验证Swagger UI正常加载
   - ✅ 验证：UnifiedResponse schema可正确解析
   - ✅ 验证：API端点正常访问

6. **提交git**
   - git add .
   - git commit -m "fix: 修复Swagger UI tags重复和配置过载"
   - 验证：git status clean

## 并行任务
无（所有任务需顺序执行）

## 验证检查
- ✅ Swagger UI显示8个分组：系统、认证系统、任务管理、奖励系统、积分系统、Top3管理、智能聊天、番茄钟系统
- ✅ 每个分组只显示一次（移除重复tags参数）
- ✅ /docs正常访问，无schema解析错误
- ✅ /redoc正常访问
- ✅ 代码总行数减少约100行
- ✅ UnifiedResponse schema正确集成
- ✅ 配置简洁化，移除过度扩展
