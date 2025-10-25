"""
Streamlit 测试面板包初始化文件

这个文件让 streamlit_app 成为一个合法的 Python 包，
解决了模块导入问题。

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

# 设置包的版本信息
__version__ = "1.0.0"
__author__ = "Claude Code Assistant"
__description__ = "TaKeKe API 测试面板"

# 导入主要组件，方便外部使用
from .config import api_client
from .state_manager import init_state, is_authenticated

__all__ = [
    "api_client",
    "init_state",
    "is_authenticated",
    "__version__",
    "__author__",
    "__description__"
]