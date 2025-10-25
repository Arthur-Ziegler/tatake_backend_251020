"""
Streamlit 测试面板 - 认证页面

这个文件提供：
1. 游客初始化功能
2. Token 刷新功能
3. 认证状态展示

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from streamlit_app.config import api_client
from streamlit_app.state_manager import (
    update_auth_state,
    clear_auth_state,
    is_authenticated,
    show_auth_status
)
from streamlit_app.components.json_viewer import render_json
from streamlit_app.components.error_handler import show_error

def main():
    """认证页面主函数"""
    st.set_page_config(
        page_title="认证 - TaKeKe API 测试面板",
        page_icon="🏠",
        layout="wide"
    )

    st.title("🏠 认证管理")
    st.markdown("---")

    # 显示当前认证状态
    st.subheader("📊 当前认证状态")
    show_auth_status()
    st.markdown("---")

    # 认证操作区域
    if not is_authenticated():
        show_guest_init_section()
    else:
        show_authenticated_section()

def show_guest_init_section():
    """显示游客初始化区域"""
    st.subheader("🎭 游客初始化")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        游客账号可以让您体验基础功能，包括：
        - 创建和管理任务
        - 使用番茄钟功能
        - 查看奖励系统

        **注意**：游客数据可能会被清理，建议注册正式账号长期使用。
        """)

    with col2:
        if st.button("🚀 游客初始化", type="primary", use_container_width=True):
            init_guest_user()

def show_authenticated_section():
    """显示已认证用户的操作区域"""
    st.subheader("🔧 认证操作")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 刷新 Token", use_container_width=True):
            refresh_token()

    with col2:
        if st.button("🚪 退出登录", use_container_width=True):
            clear_auth_state()
            st.success("✅ 已退出登录")
            st.rerun()

def init_guest_user():
    """
    游客初始化
    调用 POST /api/v1/auth/guest/init
    """
    with st.spinner("正在初始化游客账号..."):
        response = api_client.post("/auth/guest/init")

        if response and response.get("code") == 200:
            data = response.get("data", {})
            token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            user_id = data.get("user_id")

            if token and user_id:
                # 更新认证状态
                update_auth_state(token, user_id, "guest", refresh_token)

                st.success("✅ 游客账号初始化成功！")
                st.info(f"用户ID: {user_id}")

                # 显示完整响应
                render_json(response, "📄 完整响应数据")

                # 重新运行页面以更新状态
                st.rerun()
            else:
                st.error("❌ 响应数据格式错误：缺少 token 或 user_id")
                render_json(response, "📄 错误响应")
        else:
            show_error(response)
            st.error("❌ 游客初始化失败")

def refresh_token():
    """
    刷新 Token
    调用 POST /api/v1/auth/refresh
    """
    if not is_authenticated():
        st.error("❌ 请先进行认证")
        return

    with st.spinner("正在刷新 Token..."):
        # 获取当前的refresh_token
        refresh_token = st.session_state.get("refresh_token")

        if not refresh_token:
            st.error("❌ 没有刷新令牌，请重新登录")
            return

        # 发送refresh_token
        refresh_data = {"refresh_token": refresh_token}
        response = api_client.post("/auth/refresh", json=refresh_data)

        if response and response.get("code") == 200:
            data = response.get("data", {})
            new_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")

            if new_token:
                # 更新 token 和 refresh_token
                st.session_state.token = new_token
                if new_refresh_token:
                    st.session_state.refresh_token = new_refresh_token

                st.success("✅ Token 刷新成功！")
                st.info(f"新Token: {new_token[:20]}...")

                # 显示完整响应
                render_json(response, "📄 完整响应数据")
            else:
                st.error("❌ 响应数据格式错误：缺少新 token")
                render_json(response, "📄 错误响应")
        else:
            show_error(response)
            st.error("❌ Token 刷新失败")

            # 如果是认证错误，清除认证状态
            if response and response.get("code") == 401:
                clear_auth_state()
                st.warning("⚠️ 由于 Token 失效，已自动退出登录")

if __name__ == "__main__":
    main()