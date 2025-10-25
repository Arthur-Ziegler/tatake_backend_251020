# 实施任务清单

## 阶段0：Service层标准化（关键前置）
- [ ] 0.1 检查Task Service所有方法返回类型
- [ ] 0.2 改造`TaskService.get_task()`返回dict而非Task模型
- [ ] 0.3 检查其他领域Service，确保都返回dict
- [ ] 0.4 编写Service层单元测试验证返回类型

## 阶段1：Task领域迁移（7端点）
- [ ] 1.1 删除Task schemas.py中的7个Wrapper类
- [ ] 1.2 迁移`POST /tasks`（创建任务）
- [ ] 1.3 迁移`GET /tasks/{id}`（获取任务）
- [ ] 1.4 迁移`PUT /tasks/{id}`（更新任务）
- [ ] 1.5 迁移`DELETE /tasks/{id}`（删除任务）
- [ ] 1.6 迁移`GET /tasks`（任务列表）
- [ ] 1.7 迁移`POST /tasks/{id}/complete`（完成任务）
- [ ] 1.8 迁移`POST /tasks/{id}/uncomplete`（取消完成）

## 阶段2：Focus领域迁移（5端点）
- [ ] 2.1 迁移`POST /focus/sessions`（开始会话）
- [ ] 2.2 迁移`POST /focus/sessions/{id}/pause`（暂停）
- [ ] 2.3 迁移`POST /focus/sessions/{id}/resume`（恢复）
- [ ] 2.4 迁移`POST /focus/sessions/{id}/complete`（完成）
- [ ] 2.5 迁移`GET /focus/sessions`（会话列表）

## 阶段3：Chat领域迁移（7端点）
- [ ] 3.1 迁移`POST /chat/sessions`（创建会话）
- [ ] 3.2 迁移`POST /chat/sessions/{id}/send`（发送消息）
- [ ] 3.3 迁移`GET /chat/sessions/{id}/messages`（消息历史）
- [ ] 3.4 迁移`GET /chat/sessions/{id}`（会话信息）
- [ ] 3.5 迁移`GET /chat/sessions`（会话列表）
- [ ] 3.6 迁移`DELETE /chat/sessions/{id}`（删除会话）
- [ ] 3.7 迁移`GET /chat/health`（健康检查）

## 阶段4：User领域迁移（4端点）
- [ ] 4.1 迁移`GET /user/profile`（获取用户信息）
- [ ] 4.2 迁移`PUT /user/profile`（更新用户信息）
- [ ] 4.3 迁移`POST /user/avatar`（上传头像）
- [ ] 4.4 迁移`POST /user/feedback`（提交反馈）

## 阶段5：Reward领域迁移（6端点）
- [ ] 5.1 删除Reward schemas.py中的2个Wrapper类
- [ ] 5.2 迁移`GET /rewards/catalog`（奖品目录）
- [ ] 5.3 迁移`GET /rewards/my-rewards`（我的奖品）
- [ ] 5.4 迁移`POST /rewards/exchange/{id}`（积分兑换）
- [ ] 5.5 迁移`GET /rewards/materials`（我的材料）
- [ ] 5.6 迁移`GET /rewards/recipes`（可用配方）
- [ ] 5.7 迁移`POST /rewards/recipes/{id}/redeem`（配方合成）

## 阶段6：Top3领域迁移（2端点）
- [ ] 6.1 迁移`POST /top3`（设置Top3）
- [ ] 6.2 迁移`GET /top3/{date}`（获取Top3）

## 阶段7：自动化验证与清理（I1方案）
- [ ] 7.1 编写pytest测试用例（每个端点至少2个用例）
- [ ] 7.2 编写OpenAPI JSON自动化验证脚本
- [ ] 7.3 使用mypy检查类型一致性
- [ ] 7.4 运行完整测试套件（pytest + 集成测试）
- [ ] 7.5 手动验证Swagger UI显示所有schema
- [ ] 7.6 验证Service层零模型实例返回（代码审查）
- [ ] 7.7 清理未使用的辅助函数和Wrapper类
- [ ] 7.8 更新API文档和架构规范

## 并行化建议
- **并行组A**：阶段1（Task）+ 阶段2（Focus）- 简单领域
- **并行组B**：阶段3（Chat）+ 阶段4（User）- 中等复杂度
- **并行组C**：阶段5（Reward）+ 阶段6（Top3）- 复杂领域

## 依赖关系
- 各阶段内部任务必须顺序执行
- 不同阶段之间无依赖，可并行执行
- 阶段7必须在所有前置阶段完成后执行

## 预估工时
- 阶段0：Service层标准化 - 1小时（关键前置）
- 阶段1：Task领域 - 2.5小时（含Service改造）
- 阶段2：Focus领域 - 1.5小时
- 阶段3：Chat领域 - 2小时
- 阶段4：User领域 - 1小时
- 阶段5：Reward领域 - 2小时
- 阶段6：Top3领域 - 0.5小时
- 阶段7：自动化验证清理 - 2小时（含测试编写）
- **总计**：约12.5小时（串行）/ 约5小时（并行）
