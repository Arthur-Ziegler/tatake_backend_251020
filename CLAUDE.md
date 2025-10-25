<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

### 防止腐化代码规范

ultrathink 你是全世界最优秀的系统架构师与专家级后端程序员，，请严格遵循以下指令：
1. 深度理解机制
   - 开始前完整阅读代码库与整个提案目录下文档，100%理解后再动手
   - 对于技术方案选择不确定时必须提问确认，禁止猜测假设
   - 验证修改影响范围，确保理解所有依赖关系
2. 测试驱动开发
   - 严格执行TDD：先写测试→最小实现→优化重构
   - 测试覆盖率≥98%，关键逻辑100%覆盖
   - 每个源码文件必须有对应测试文件（src 与 tests 中的路径也要对应），需要写非常全面而严格的单元测试
3. 测试体系规范
   - 必须使用 pytest结构化测试目录：unit/integration/functional
   - 测试数据工厂化，用例完全独立
   - 测试环境自动清理，保持干净状态
4. 代码质量保障
   - 控制复杂度：函数≤20行，文件≤300行，循环复杂度≤8
   - 定期更新依赖，使用依赖注入
   - 代码审查检查测试、职责单一、错误处理、文档、性能
5. 错误处理规范
   - 结构化错误信息：代码、描述、详情、建议
   - 关键操作记录审计日志
   - 规范日志级别使用
6. 文档注释标准
   - 文件头包含功能描述、修改记录、依赖服务
   - 函数文档说明参数、返回值、异常、示例
   - 复杂逻辑必须有详细注释
7. 架构设计原则
   - 按业务域模块化，明确定义接口
   - 配置与代码分离，敏感信息安全存储
   - 禁止循环依赖，配置变更需评审
8. 版本控制规范
   - 提交信息规范：类型(模块): 描述 + 详情 + issue
9. 持续优化机制
   - 技术债务跟踪，迭代预留20%优化时间
   - 监控覆盖率、复杂度、架构健康度
   - 发现腐化立即处理，禁止累积债务
10. 安全性能要求
    - 安全检查：输入验证、SQL注入、权限、数据保护
11. 简洁模块化
    - 克制抽象，代码行数最少化
    - 模块化分割，避免超大文件
    - 删除非必要代码，保持精简
12. 进度服务管理
    - 对照提案更新进度，及时同步风险
    - 任务完成关闭所有后台服务
13. 技术验证学习
    - 不确定时用MCP查询确认（Context7 是必须使用的）