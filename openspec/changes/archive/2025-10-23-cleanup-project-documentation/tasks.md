# 文档清理任务清单

- [x] **备份当前文档状态**（可选但推荐）
  - [x] 创建文档清单备份
  - [x] 确认重要文档已妥善保存

- [x] **删除过时的API方案文档**
  - [x] 删除 `./参考文档/TaKeKe_API方案_v1.md`
  - [x] 删除 `./参考文档/TaKeKe_API方案_v2.md`
  - [x] 删除 `./参考文档/old_TaKeKe_API设计文档(1).md`
  - [x] 删除 `./参考文档/old_TaKeKe_极简API实施方案.md`
  - [x] 删除 `./参考文档/old_最终API实施方案.md`
  - [x] 删除 `./参考文档/old_分阶段实施清单.md`

- [x] **删除临时测试报告和零食文件**
  - [x] 删除 `./TESTING_SUMMARY.md`
  - [x] 删除所有 `./focus_test_report_*.json` 文件
  - [x] 删除 `./test_focus_frontend_simulation.py`
  - [x] 删除 `./test_apis_comprehensive.py`
  - [x] 删除 `./test_api_simple.sh`
  - [x] 删除 `./test_all_apis.py`
  - [x] 删除 `./run_tests.py`
  - [x] 删除 `./init_test_data.py`
  - [x] 删除 `./test_sqlite_json_support.py`
  - [x] 删除 `./test_task_completion_service.py`
  - [x] 删除 `./test_reward_models.py`
  - [x] 删除 `./test_game_config.py`

- [x] **清理冗余的docs目录文档**
  - [x] 删除整个 `./docs/services/` 目录及其所有文件
  - [x] 删除 `./docs/test-quality-analysis.md`
  - [x] 删除 `./docs/数据层接口使用手册.md`，保留快速参考版本

- [x] **删除其他冗余文件**
  - [x] 删除 `./系统重构讨论文档.md`
  - [x] 删除其他临时或无用的markdown文件

- [x] **验证清理结果**
  - [x] 确认核心文档 `README.md`、`CLAUDE.md` 仍然存在
  - [x] 确认 `./参考文档/TaKeKe_API方案_v3.md` 仍然存在
  - [x] 确认所有 `./openspec/` 目录文件未被删除
  - [x] 确认项目可以正常启动（模块导入测试通过）
  - [x] 确认API功能完整

- [x] **更新项目文档**
  - [x] 更新 `README.md` 中的文档链接
  - [x] 更新项目结构说明

**注意事项：**
- 操作前请确认已备份重要信息
- 严格按照顺序执行，先验证再删除
- 如遇到不确定的文件，请先确认其用途