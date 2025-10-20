# 任务管理规格说明

## 概述

实现完整的任务管理系统，支持无限层级任务树、任务完成机制、Top3重点任务管理、搜索筛选等功能。集成奖励机制和游戏化元素。

## ADDED Requirements

### Requirement: 任务树结构管理
系统 SHALL支持无限层级的任务树结构，实现任务的层级关系管理。

#### Scenario: 任务创建和层级关联
- **GIVEN** 用户需要创建新任务
- **WHEN** 提供任务信息和父任务ID时
- **THEN** 系统 SHALL验证父任务存在性和权限
- **AND** 系统 SHALL创建任务并建立父子关系
- **AND** 系统 SHALL计算任务层级深度
- **AND** 系统 SHALL更新父任务的子任务统计
- **AND** 系统 SHALL验证任务层级不超过10层

#### Scenario: 任务树结构查询
- **GIVEN** 用户需要查看任务树结构
- **WHEN** 查询特定任务或整个任务树时
- **THEN** 系统 SHALL返回任务的完整层级结构
- **AND** 系统 SHALL包含每个任务的子任务列表
- **AND** 系统 SHALL计算任务的完成进度
- **AND** 系统 SHALL支持懒加载大型任务树
- **AND** 系统 SHALL优化查询性能避免递归过深

#### Scenario: 任务层级关系变更
- **GIVEN** 用户需要调整任务层级关系
- **WHEN** 移动任务到新的父任务下时
- **THEN** 系统 SHALL验证目标父任务的权限
- **AND** 系统 SHALL检测循环依赖问题
- **AND** 系统 SHALL更新任务的父子关系
- **AND** 系统 SHALL重新计算相关任务的统计信息
- **AND** 系统 SHALL记录任务移动历史

### Requirement: 任务完成机制
系统 SHALL实现任务完成机制，包括完成状态管理、心情反馈、奖励触发等。

#### Scenario: 任务完成流程
- **GIVEN** 用户完成一个任务
- **WHEN** 调用任务完成API时
- **THEN** 系统 SHALL验证任务状态和权限
- **AND** 系统 SHALL更新任务完成状态和时间
- **AND** 系统 SHALL触发心情反馈收集
- **AND** 系统 SHALL计算完成奖励（积分、碎片）
- **AND** 系统 SHALL更新用户等级和经验值
- **AND** 系统 SHALL触发抽奖机制（如果适用）

#### Scenario: 任务完成奖励计算
- **GIVEN** 任务完成需要计算奖励
- **WHEN** 计算奖励时
- **THEN** 系统 SHALL根据任务类型和难度计算基础积分
- **AND** 系统 SHALL考虑任务完成质量和及时性
- **AND** 系统 SHALL计算获得的碎片类型和数量
- **AND** 系统 SHALL检查连续完成任务获得额外奖励
- **AND** 系统 SHALL更新用户总积分和可用积分

#### Scenario: 任务取消完成
- **GIVEN** 用户需要取消任务完成状态
- **WHEN** 调用取消完成API时
- **THEN** 系统 SHALL验证任务当前状态
- **AND** 系统 SHALL检查取消完成的权限和时间限制
- **AND** 系统 SHALL回滚任务状态为未完成
- **AND** 系统 SHALL扣除相关奖励（积分、碎片）
- **AND** 系统 SHALL记录取消完成的原因
- **AND** 系统 SHALL更新相关统计信息

### Requirement: Top3重点任务管理
系统 SHALL实现Top3重点任务管理功能，帮助用户聚焦每日最重要的任务。

#### Scenario: Top3任务设置
- **GIVEN** 用户希望设置每日Top3任务
- **WHEN** 选择任务并设置为Top3时
- **THEN** 系统 SHALL验证用户权限和任务状态
- **AND** 系统 SHALL检查当日Top3数量限制
- **AND** 系统 SHALL消耗用户积分进行设置
- **AND** 系统 SHALL标记任务为Top3状态
- **AND** 系统 SHALL记录Top3设置时间和历史

#### Scenario: Top3任务修改和查询
- **GIVEN** 用户需要管理Top3任务
- **WHEN** 查询或修改Top3任务时
- **THEN** 系统 SHALL返回指定日期的Top3任务列表
- **AND** 系统 SHALL支持Top3任务的修改和替换
- **AND** 系统 SHALL计算Top3任务完成率
- **AND** 系统 SHALL提供Top3效果统计
- **AND** 系统 SHALL支持历史Top3查询

#### Scenario: Top3积分消耗机制
- **GIVEN** 用户设置Top3任务
- **WHEN** 计算积分消耗时
- **THEN** 系统 SHALL根据用户等级计算基础消耗
- **AND** 系统 SHALL考虑历史Top3设置频率
- **AND** 系统 SHALL检查用户可用积分余额
- **AND** 系统 SHALL提供积分不足的明确提示
- **AND** 系统 SHALL记录积分消耗明细

### Requirement: 任务搜索和筛选
系统 SHALL实现强大的任务搜索和筛选功能，支持多种查询条件。

#### Scenario: 全文搜索功能
- **GIVEN** 用户需要搜索任务
- **WHEN** 提供搜索关键词时
- **THEN** 系统 SHALL在任务标题和描述中搜索
- **AND** 系统 SHALL支持模糊匹配和高亮显示
- **AND** 系统 SHALL按相关性和时间排序结果
- **AND** 系统 SHALL支持搜索建议和历史记录
- **AND** 系统 SHALL优化搜索性能（索引、缓存）

#### Scenario: 高级筛选功能
- **GIVEN** 用户需要筛选任务
- **WHEN** 设置多个筛选条件时
- **THEN** 系统 SHALL支持状态筛选（完成/未完成/进行中）
- **AND** 系统 SHALL支持优先级筛选（高/中/低）
- **AND** 系统 SHALL支持时间范围筛选（创建时间/完成时间）
- **AND** 系统 SHALL支持标签和分类筛选
- **AND** 系统 SHALL支持多条件组合筛选

#### Scenario: 搜索结果优化
- **GIVEN** 用户获取搜索或筛选结果
- **WHEN** 返回结果时
- **THEN** 系统 SHALL支持分页加载
- **AND** 系统 SHALL提供结果统计信息
- **AND** 系统 SHALL支持结果排序（时间/优先级/进度）
- **AND** 系统 SHALL缓存常用查询结果
- **AND** 系统 SHALL记录搜索日志用于优化

### Requirement: 任务统计和分析
系统 SHALL提供任务相关的统计功能，帮助用户了解任务完成情况。

#### Scenario: 个人任务统计
- **GIVEN** 用户需要查看任务统计
- **WHEN** 查询个人统计时
- **THEN** 系统 SHALL计算任务完成率
- **AND** 系统 SHALL统计不同类型任务的完成情况
- **AND** 系统 SHALL分析任务完成的时间分布
- **AND** 系统 SHALL提供任务效率分析
- **AND** 系统 SHALL生成改进建议

#### Scenario: 任务趋势分析
- **GIVEN** 用户需要了解任务完成趋势
- **WHEN** 查询趋势数据时
- **THEN** 系统 SHALL提供日/周/月维度的完成趋势
- **AND** 系统 SHALL分析任务完成的高峰时段
- **AND** 系统 SHALL预测未来任务完成情况
- **AND** 系统 SHALL识别任务完成模式
- **AND** 系统 SHALL提供可视化数据支持

## MODIFIED Requirements

### Requirement: TaskService业务逻辑增强
原有的TaskService SHALL增强以支持完整的任务管理功能。

#### Scenario: 任务状态转换管理
- **GIVEN** 任务状态需要变更
- **WHEN** 执行状态转换时
- **THEN** TaskService SHALL验证状态转换的合法性
- **AND** TaskService SHALL触发相关的业务逻辑
- **AND** TaskService SHALL更新统计数据
- **AND** TaskService SHALL记录状态变更历史

## 技术实现细节

### 数据库Schema变更

```sql
-- 任务表优化
ALTER TABLE tasks ADD COLUMN is_top3 BOOLEAN DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN top3_date DATE;
ALTER TABLE tasks ADD COLUMN completion_points INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN completion_fragments JSONB;
ALTER TABLE tasks ADD COLUMN satisfaction_score INTEGER;
ALTER TABLE tasks ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE;

-- Top3记录表
CREATE TABLE top3_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id UUID NOT NULL,
    task_id UUID NOT NULL,
    top3_date DATE NOT NULL,
    points_consumed INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_date (user_id, top3_date),
    INDEX idx_task_id (task_id)
);

-- 任务完成记录表
CREATE TABLE task_completion_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id UUID NOT NULL,
    task_id UUID NOT NULL,
    completion_points INTEGER NOT NULL,
    fragments_earned JSONB,
    satisfaction_score INTEGER,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_task (user_id, task_id),
    INDEX idx_completion_date (completed_at)
);
```

### 业务逻辑算法

#### 任务完成积分计算算法
```python
def calculate_completion_points(task, user, completion_quality):
    """
    计算任务完成积分

    Args:
        task: 任务对象
        user: 用户对象
        completion_quality: 完成质量评分 (1-5)

    Returns:
        积分数量
    """
    # 基础积分（根据任务类型和难度）
    base_points = {
        'simple': 10,
        'medium': 20,
        'complex': 50
    }.get(task.difficulty, 10)

    # 质量加成（1.0 - 2.0倍）
    quality_multiplier = 1.0 + (completion_quality - 3) * 0.25

    # 及时性加成（提前完成额外20%）
    timeliness_bonus = 1.2 if task.completed_before_deadline else 1.0

    # 连续完成加成
    streak_bonus = 1.0 + min(user.current_streak * 0.1, 1.0)

    total_points = int(
        base_points * quality_multiplier * timeliness_bonus * streak_bonus
    )

    return total_points
```

#### 抽奖机制算法
```python
def calculate_lottery_chance(user, task_completion):
    """
    计算抽奖机会

    Returns:
        抽奖次数
    """
    # 基础抽奖次数（完成任务获得1次）
    base_chances = 1

    # 高质量完成额外机会
    if task_completion.satisfaction_score >= 4:
        base_chances += 1

    # 连续完成奖励
    if user.current_streak >= 7:
        base_chances += 1

    # Top3任务完成额外机会
    if task_completion.task.is_top3:
        base_chances += 1

    return min(base_chances, 5)  # 最多5次机会
```

---

**规格版本**: 1.0.0
**创建日期**: 2025-10-20
**适用模块**: 任务管理API + TaskService
**依赖模块**: SQLite数据库, RewardService, StatisticsService