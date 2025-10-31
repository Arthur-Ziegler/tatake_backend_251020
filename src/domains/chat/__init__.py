"""
TaKeKe聊天领域

简化版聊天系统，提供4个核心接口：
1. 查询所有会话列表
2. 查询聊天记录
3. 删除会话
4. 聊天接口（流式）
"""

# 简化版本，只需要导出router
from .router import router

__all__ = [
    "router"
]