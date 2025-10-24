# documentation-cleanup Specification

## Purpose
清理项目中的冗余和过时文档，提高项目结构清晰度和维护效率。

## Why
当前项目存在大量冗余文档，包括过时的API方案文档（v1、v2版本）、临时测试报告、重复的docs目录文档等。这些文档不仅增加了维护负担，还会让新开发者感到困惑。通过系统性清理这些冗余文档，可以提高项目结构的清晰度，降低维护成本，同时保留所有重要的核心文档。

## REMOVED Requirements

### Requirement: 删除过时的API方案文档
项目SHALL删除所有过时的API方案文档，仅保留最新的v3版本。

#### Scenario: 删除v1和v2版本文档
**Given** 项目存在多个版本的API方案文档
**When** 执行文档清理
**Then** 删除v1和v2版本的API方案文档，保留v3版本

#### Scenario: 删除带old前缀的过时文档
**Given** 参考文档目录存在带old前缀的文件
**When** 执行文档清理
**Then** 删除所有old_前缀的文档文件

---

### Requirement: 删除临时测试报告和零食文件
项目SHALL删除所有临时生成的测试报告和无用文件。

#### Scenario: 删除测试总结报告
**Given** 项目根目录存在TESTING_SUMMARY.md
**When** 执行文档清理
**Then** 删除TESTING_SUMMARY.md文件

#### Scenario: 删除临时测试JSON报告
**Given** 项目中存在focus_test_report_*.json等临时报告文件
**When** 执行文档清理
**Then** 删除所有临时测试报告JSON文件

#### Scenario: 删除测试脚本文件
**Given** 项目中存在test_*.py测试脚本
**When** 执行文档清理
**Then** 删除临时测试脚本文件

---

### Requirement: 清理冗余的docs目录文档
项目SHALL清理docs目录中的冗余文档，保留核心架构文档。

#### Scenario: 删除services目录下的冗余文档
**Given** docs/services目录包含7个详细文档
**When** 执行文档清理
**Then** 删除docs/services目录下的所有冗余文档

#### Scenario: 删除测试质量分析文档
**Given** 存在test-quality-analysis.md文档
**When** 执行文档清理
**Then** 删除docs/test-quality-analysis.md文件

#### Scenario: 删除重复的数据层文档
**Given** 存在数据层接口使用手册和快速参考两个文档
**When** 执行文档清理
**Then** 删除冗余的数据层文档，保留一个核心版本

## ADDED Requirements

### Requirement: 保持OpenSpec文档完整性
项目SHALL保持所有OpenSpec相关文档的完整性，不进行删除。

#### Scenario: 保护OpenSpec目录
**Given** openspec目录包含所有规格说明和变更记录
**When** 执行文档清理
**Then** 不删除任何openspec目录下的文件

#### Scenario: 保护归档提案
**Given** openspec/changes/archive目录包含已归档的提案
**When** 执行文档清理
**Then** 不删除任何已归档的提案文件

---

### Requirement: 验证清理结果
项目SHALL验证文档清理后的结果，确保重要文档未被误删。

#### Scenario: 验证核心文档保留
**When** 文档清理完成
**Then** 确认README.md、CLAUDE.md、v3 API文档等核心文件仍然存在

#### Scenario: 验证项目功能完整性
**When** 文档清理完成
**Then** 确认项目可以正常启动和运行