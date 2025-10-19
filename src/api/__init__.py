"""
TaKeKe API Layer
================

TaKeKe项目的API层实现，基于FastAPI框架提供完整的RESTful API服务。

模块结构:
- main.py: FastAPI主应用
- config.py: 应用配置
- dependencies.py: 依赖注入
- middleware/: 中间件模块
- responses.py: 统一响应格式

支持的API模块:
- 认证系统 (7个API)
- AI对话系统 (4个API)
- 任务管理 (12个API)
- 番茄钟系统 (8个API)
- 奖励系统 (8个API)
- 统计系统 (3个API)
- 用户管理 (4个API)
"""

__version__ = "1.0.0"
__author__ = "TaKeKe Team"