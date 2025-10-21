"""
TaKeKe聊天领域

基于LangGraph的AI对话系统，提供智能聊天功能。
包括会话管理、消息处理、工具集成等核心功能。
"""

from .database import create_tables, check_connection
from .service import ChatService

__all__ = [
    "create_tables",
    "check_connection",
    "ChatService"
]