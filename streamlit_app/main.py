"""
Streamlit 测试面板主入口文件

这个文件是 Streamlit 测试面板的主入口，提供：
1. 初始化 session_state
2. 显示基本的认证状态信息
3. 提供导航到其他页面的功能

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from streamlit_app.state_manager import init_state
from streamlit_app.config import api_client

# 初始化 session_state
init_state()

def main():
    """主函数，设置页面布局和内容"""
    st.set_page_config(
        page_title="TaKeKe API 测试面板",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🧪 TaKeKe API 测试面板")
    st.markdown("---")

    # 显示认证状态
    show_auth_status()

    # 显示导航信息
    show_navigation()

def show_auth_status():
    """显示当前认证状态"""
    st.subheader("🔐 认证状态")

    if st.session_state.get("token"):
        st.success("✅ 已认证")
        st.info(f"用户ID: {st.session_state.get('user_id', 'N/A')}")
        st.code(f"Token: {st.session_state.token[:20]}...")
    else:
        st.warning("❌ 未认证")
        st.info("请在左侧导航栏选择 '🏠 认证' 页面进行认证")

def show_navigation():
    """显示导航信息"""
    st.subheader("📍 页面导航")
    st.markdown("""
    请使用左侧导航栏访问不同功能页面：

    - **🏠 认证**: 游客初始化、登录、刷新Token
    - 其他页面将在后续提案中实现

    ---

    **面板状态**: 🚧 基础架构建设中...
    """)

if __name__ == "__main__":
    main()