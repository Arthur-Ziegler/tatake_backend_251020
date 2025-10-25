"""
聊天工具模块

包含LangGraph可用的工具集合，如计算器、任务查询、任务CRUD、任务搜索、批量操作等。

工具分类：
1. 基础工具：计算器、芝麻开门
2. 任务查询：query_tasks、get_task_detail
3. 任务CRUD：create_task、update_task、delete_task
4. 任务搜索：search_tasks
5. 批量操作：batch_create_subtasks

总共8个工具，支持完整的任务管理功能。
"""

from .calculator import calculator
from .password_opener import sesame_opener
from .task_query import query_tasks, get_task_detail, AVAILABLE_TOOLS
from .task_crud import create_task, update_task, delete_task, AVAILABLE_TOOLS as CRUD_AVAILABLE_TOOLS
from .task_search import search_tasks, AVAILABLE_TOOLS as SEARCH_AVAILABLE_TOOLS
from .task_batch import batch_create_subtasks, get_batch_tools_info

__all__ = [
    # 基础工具
    "calculator",
    "sesame_opener",

    # 任务查询工具
    "query_tasks",
    "get_task_detail",
    "AVAILABLE_TOOLS",

    # 任务CRUD工具
    "create_task",
    "update_task",
    "delete_task",
    "CRUD_AVAILABLE_TOOLS",

    # 任务搜索工具
    "search_tasks",
    "SEARCH_AVAILABLE_TOOLS",

    # 批量操作工具
    "batch_create_subtasks",
    "get_batch_tools_info"
]