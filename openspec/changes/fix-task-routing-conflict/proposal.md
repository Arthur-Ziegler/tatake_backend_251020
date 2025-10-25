# 修复任务路由冲突

## Why
`/tasks/top3` 与 `/tasks/{task_id}` 路由冲突导致422错误，需要重新设计Top3 API路径。

## 核心问题
任务API路由冲突：FastAPI将"top3"当作task_id参数，尝试解析为UUID失败。

## 解决方案
将Top3 API路径调整为 `/tasks/special/top3` 避免冲突。

## 预期效果
Top3任务API正常工作，消除路由解析错误。