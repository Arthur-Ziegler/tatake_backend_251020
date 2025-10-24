"""
Streamlit 测试面板配置文件

这个文件包含：
1. API 基础配置
2. 全局 API 客户端实例
3. 其他配置常量

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import os
from streamlit_app.api_client import APIClient

# API 基础配置
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8001"
)

# 创建全局 API 客户端实例
api_client = APIClient(base_url=API_BASE_URL)

# 应用配置
APP_CONFIG = {
    "title": "TaKeKe API 测试面板",
    "description": "用于测试 TaKeKe API 功能的 Streamlit 应用",
    "version": "1.0.0"
}