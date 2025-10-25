"""
Streamlit 测试面板状态管理器

这个文件包含：
1. session_state 初始化函数
2. 状态管理工具函数
3. 认证状态管理

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
import os
from typing import Optional


def init_state():
    """
    初始化 streamlit session_state

    这个函数会在应用启动时设置所有必要的默认值
    """
    # 基础认证状态
    defaults = {
        "token": None,
        "refresh_token": None,
        "user_id": None,
        "api_base_url": os.getenv("API_BASE_URL", "http://localhost:8001"),
        "authenticated": False,
        "user_type": None,  # "guest" 或 "registered"
    }

    # 设置默认值
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def update_auth_state(token: str, user_id: str, user_type: str = "guest", refresh_token: str = None):
    """
    更新认证状态

    Args:
        token: JWT token
        user_id: 用户ID
        user_type: 用户类型 ("guest" 或 "registered")
        refresh_token: 刷新令牌
    """
    st.session_state.token = token
    st.session_state.refresh_token = refresh_token
    st.session_state.user_id = user_id
    st.session_state.user_type = user_type
    st.session_state.authenticated = True

def clear_auth_state():
    """清除认证状态"""
    st.session_state.token = None
    st.session_state.refresh_token = None
    st.session_state.user_id = None
    st.session_state.user_type = None
    st.session_state.authenticated = False

def is_authenticated() -> bool:
    """
    检查是否已认证

    Returns:
        是否已认证
    """
    return bool(st.session_state.get("token") and st.session_state.get("authenticated"))

def get_auth_headers() -> dict:
    """
    获取认证头

    Returns:
        包含认证头的字典
    """
    if is_authenticated():
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def show_auth_status():
    """显示当前认证状态的 UI 组件"""
    if is_authenticated():
        st.success("✅ 已认证")
        st.info(f"用户ID: {st.session_state.user_id}")
        st.info(f"用户类型: {st.session_state.user_type}")

        # 显示 token 的前20个字符
        token_preview = st.session_state.token[:20] + "..." if len(st.session_state.token) > 20 else st.session_state.token
        st.code(f"Token: {token_preview}")
    else:
        st.warning("❌ 未认证")
        st.info("请在认证页面进行登录或游客初始化")