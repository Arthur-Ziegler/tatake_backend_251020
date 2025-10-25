"""
Streamlit 测试面板 - 智能聊天页面

这个文件提供：
1. 类微信的聊天界面（左侧会话列表，右侧聊天记录）
2. 创建会话功能
3. 发送消息并查看 AI 回复
4. 会话切换功能

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from streamlit_app.config import api_client
from streamlit_app.state_manager import (
    is_authenticated,
    show_auth_status,
    init_state
)
from streamlit_app.components.json_viewer import render_json
from streamlit_app.components.error_handler import show_error, handle_api_response

def init_chat_state():
    """初始化聊天相关的 session_state"""
    defaults = {
        "current_session_id": None,
        "chat_sessions": [],
        "chat_messages": {},
        "new_session_title": ""
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def main():
    """智能聊天页面主函数"""
    # 页面配置
    st.set_page_config(
        page_title="智能聊天 - TaKeKe API 测试面板",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.title("💬 智能聊天")
    st.markdown("---")

    # 初始化聊天状态
    init_chat_state()

    # 检查认证状态
    if not is_authenticated():
        st.warning("⚠️ 请先进行认证才能使用聊天功能")
        st.info("请在左侧导航栏选择 '🏠 认证' 页面进行登录")
        return

    # 显示认证状态
    show_auth_status()
    st.markdown("---")

    # 显示聊天界面
    show_chat_interface()

def show_chat_interface():
    """显示聊天主界面"""
    # 创建两列布局：左侧会话列表（30%），右侧聊天记录（70%）
    col1, col2 = st.columns([3, 7])

    with col1:
        show_session_list()

    with col2:
        show_chat_area()

def show_session_list():
    """显示会话列表"""
    st.subheader("📝 会话列表")

    # 刷新会话列表按钮
    if st.button("🔄 刷新会话", use_container_width=True):
        load_sessions()

    # 创建新会话
    st.markdown("**创建新会话**")
    new_title = st.text_input(
        "会话标题",
        value=st.session_state.new_session_title,
        key="new_session_title_input",
        placeholder="输入会话标题..."
    )

    col_create, col_clear = st.columns([2, 1])
    with col_create:
        if st.button("➕ 创建会话", use_container_width=True):
            create_session(new_title)
    with col_clear:
        if st.button("🗑️ 清空", use_container_width=True):
            st.session_state.new_session_title = ""
            st.rerun()

    st.markdown("---")

    # 显示会话列表
    if st.session_state.chat_sessions:
        st.markdown("**已有会话**")
        for session in st.session_state.chat_sessions:
            session_id = session.get("id")
            session_title = session.get("title", f"会话 {session_id}")

            # 会话按钮
            button_type = "primary" if session_id == st.session_state.current_session_id else "secondary"

            if st.button(
                f"💭 {session_title}",
                key=f"session_{session_id}",
                use_container_width=True,
                type=button_type
            ):
                st.session_state.current_session_id = session_id
                load_session_messages(session_id)
                st.rerun()
    else:
        st.info("📭 暂无会话，请创建新会话开始聊天")

def show_chat_area():
    """显示聊天区域"""
    st.subheader("💬 聊天记录")

    if not st.session_state.current_session_id:
        st.info("👈 请在左侧选择或创建一个会话")
        return

    current_session_id = st.session_state.current_session_id

    # 显示当前会话信息
    current_session = next(
        (s for s in st.session_state.chat_sessions if s.get("id") == current_session_id),
        None
    )

    if current_session:
        st.info(f"当前会话: **{current_session.get('title', f'会话 {current_session_id}')}**")

    # 显示聊天记录
    show_messages()

    # 消息输入区域
    st.markdown("---")
    show_message_input()

def show_messages():
    """显示聊天消息记录"""
    current_session_id = st.session_state.current_session_id
    messages = st.session_state.chat_messages.get(current_session_id, [])

    if not messages:
        st.info("🗨️ 暂无消息，开始对话吧！")
        return

    # 使用滚动容器显示消息
    with st.container(height=400):
        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")

            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(content)
            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content)
            else:
                # 未知角色，简单显示
                st.markdown(f"**{role}**: {content}")

def show_message_input():
    """显示消息输入区域"""
    # 消息输入框
    user_input = st.chat_input(
        "输入消息...",
        key="chat_input",
        max_chars=1000
    )

    if user_input and user_input.strip():
        send_message(user_input.strip())

def load_sessions():
    """加载会话列表"""
    with st.spinner("正在加载会话列表..."):
        response = api_client.get("/chat/sessions")

        if handle_api_response(response, "会话列表加载成功"):
            st.session_state.chat_sessions = response.get("sessions", [])
            st.success(f"✅ 加载了 {len(st.session_state.chat_sessions)} 个会话")
        else:
            st.error("❌ 会话列表加载失败")

def create_session(title: str):
    """创建新会话"""
    if not title or not title.strip():
        st.error("❌ 请输入会话标题")
        return

    with st.spinner("正在创建会话..."):
        response = api_client.post(
            "/chat/sessions",
            json={"title": title.strip()}
        )

        if handle_api_response(response, "会话创建成功"):
            # 清空输入框
            st.session_state.new_session_title = ""

            # 重新加载会话列表
            load_sessions()

            # 自动切换到新创建的会话
            new_session = response.get("data", {})
            new_session_id = new_session.get("id")
            if new_session_id:
                st.session_state.current_session_id = new_session_id
                st.session_state.chat_messages[new_session_id] = []
                st.success(f"✅ 会话 '{title}' 创建成功，可以开始聊天了！")
        else:
            st.error("❌ 会话创建失败")

def load_session_messages(session_id: str):
    """加载指定会话的消息记录"""
    with st.spinner("正在加载聊天记录..."):
        response = api_client.get(f"/chat/sessions/{session_id}/messages")

        if handle_api_response(response, "聊天记录加载成功"):
            messages = response.get("data", [])
            st.session_state.chat_messages[session_id] = messages
        else:
            st.error("❌ 聊天记录加载失败")
            st.session_state.chat_messages[session_id] = []

def send_message(content: str):
    """发送消息"""
    current_session_id = st.session_state.current_session_id

    if not current_session_id:
        st.error("❌ 请先选择一个会话")
        return

    # 立即显示用户消息（乐观更新）
    if current_session_id not in st.session_state.chat_messages:
        st.session_state.chat_messages[current_session_id] = []

    st.session_state.chat_messages[current_session_id].append({
        "role": "user",
        "content": content
    })

    # 发送到 API
    with st.spinner("🤖 AI 正在思考..."):
        response = api_client.post(
            f"/chat/sessions/{current_session_id}/send",
            json={"content": content}
        )

        if handle_api_response(response, "消息发送成功"):
            # 重新加载消息记录以获取 AI 回复
            load_session_messages(current_session_id)
            st.rerun()
        else:
            # 如果发送失败，移除刚刚添加的用户消息
            st.session_state.chat_messages[current_session_id].pop()
            st.error("❌ 消息发送失败，请重试")

if __name__ == "__main__":
    main()