"""
Streamlit 测试面板 - 番茄钟系统页面

这个文件提供：
1. 开始专注会话功能
2. 暂停/恢复/完成操作
3. 当前会话状态显示
4. 历史专注记录查看
5. 任务关联功能

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from streamlit_app.config import api_client
from streamlit_app.state_manager import is_authenticated, show_auth_status
from streamlit_app.components.json_viewer import render_json, render_api_response
from streamlit_app.components.error_handler import show_error, handle_api_response


def main():
    """番茄钟系统页面主函数"""
    st.set_page_config(
        page_title="番茄钟 - TaKeKe API 测试面板",
        page_icon="🍅",
        layout="wide"
    )

    st.title("🍅 番茄钟系统")
    st.markdown("---")

    # 检查认证状态
    if not is_authenticated():
        st.warning("⚠️ 请先进行认证")
        st.info("请使用左侧导航栏进入 '🏠 认证' 页面")
        return

    # 显示当前认证状态
    st.subheader("🔐 认证状态")
    show_auth_status()
    st.markdown("---")

    # 主要功能区域
    show_focus_management_interface()


def show_focus_management_interface():
    """显示番茄钟管理主界面"""
    # 创建两列布局
    col1, col2 = st.columns([2, 1])

    with col1:
        show_current_session_section()

    with col2:
        show_session_controls_section()

    st.markdown("---")

    # 历史记录区域
    show_session_history_section()

    st.markdown("---")

    # 使用说明
    show_focus_instructions()


def show_current_session_section():
    """显示当前会话区域"""
    st.subheader("🎯 当前专注会话")

    # 加载当前会话
    if "current_focus_session" not in st.session_state:
        load_current_focus_session()

    current_session = st.session_state.get("current_focus_session")

    if current_session:
        display_current_session(current_session)
    else:
        display_no_active_session()


def display_current_session(session: Dict[str, Any]):
    """显示当前活跃会话"""
    session_data = session.get("data", {})
    session_info = session_data.get("session", {})

    if not session_info:
        st.warning("⚠️ 会话数据格式异常")
        return

    # 会话基本信息
    task_id = session_info.get("task_id", "")
    session_type = session_info.get("session_type", "focus")
    status = session_info.get("status", "unknown")
    start_time = session_info.get("start_time", "")
    end_time = session_info.get("end_time", "")

    # 状态映射
    status_map = {
        "focus": "🍅 专注中",
        "pause": "⏸️ 暂停中",
        "completed": "✅ 已完成",
        "cancelled": "❌ 已取消"
    }

    # 显示会话信息
    st.info(f"**状态**: {status_map.get(status, status)}")
    st.info(f"**任务ID**: `{task_id[:12]}...`")

    # 获取任务详情
    task_detail = get_task_detail_by_id(task_id)
    if task_detail:
        task_title = task_detail.get("title", "未命名任务")
        task_desc = task_detail.get("description", "")
        st.info(f"**任务**: 📌 {task_title}")
        if task_desc:
            st.caption(f"📝 {task_desc[:100]}...")

    # 显示时间信息
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        local_start = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        st.info(f"**开始时间**: {local_start}")

        # 计算持续时间
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_dt = datetime.now()

        duration = end_dt - start_dt
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.info(f"**持续时间**: {int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒")

    # 显示完整会话数据
    with st.expander("📄 完整会话数据", expanded=False):
        st.json(session)


def display_no_active_session():
    """显示无活跃会话状态"""
    st.info("💡 当前没有活跃的专注会话")
    st.write("请选择一个任务开始专注")

    # 任务选择
    show_task_selection_for_focus()


def show_task_selection_for_focus():
    """显示为专注选择任务的界面"""
    # 加载任务列表
    if "tasks" not in st.session_state:
        load_tasks_for_focus()

    tasks = st.session_state.get("tasks", [])

    if not tasks:
        st.warning("⚠️ 暂无可用任务，请先创建任务")
        if st.button("📋 前往任务管理", use_container_width=True):
            st.switch_page("pages/2_📋_任务管理.py")
        return

    # 过滤待办任务
    pending_tasks = [task for task in tasks if task.get("status") == "pending"]

    if not pending_tasks:
        st.info("📭 暂无待办任务")
        return

    # 任务选择
    task_options = {}
    for task in pending_tasks:
        task_id = task.get("id", "")
        title = task.get("title", "未命名任务")
        priority = task.get("priority", "medium")
        description = task.get("description", "")

        priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(priority, "⚪")
        display_text = f"{priority_emoji} {title}"
        if description:
            display_text += f" ({description[:50]}...)"

        task_options[display_text] = task_id

    selected_task_display = st.selectbox(
        "选择要专注的任务",
        options=list(task_options.keys()),
        help="选择一个任务开始专注"
    )

    if selected_task_display:
        selected_task_id = task_options[selected_task_display]
        if st.button("🍅 开始专注", type="primary", use_container_width=True):
            start_focus_session(selected_task_id)


def show_session_controls_section():
    """显示会话控制区域"""
    st.subheader("🎮 会话控制")

    current_session = st.session_state.get("current_focus_session")
    if not current_session:
        st.info("💡 没有活跃会话需要控制")
        return

    session_data = current_session.get("data", {})
    session_info = session_data.get("session", {})
    session_id = session_info.get("id", "")
    status = session_info.get("status", "unknown")

    if not session_id:
        st.warning("⚠️ 会话ID获取失败")
        return

    st.write(f"**当前状态**: {status}")

    # 根据状态显示不同的控制按钮
    if status == "focus":
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("⏸️ 暂停专注", use_container_width=True):
                pause_focus_session(session_id)

        with col2:
            if st.button("✅ 完成专注", type="primary", use_container_width=True):
                complete_focus_session(session_id)

    elif status == "pause":
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("▶️ 恢复专注", type="primary", use_container_width=True):
                resume_focus_session(session_id)

        with col2:
            if st.button("✅ 完成专注", use_container_width=True):
                complete_focus_session(session_id)

    else:
        st.info(f"会话状态为 '{status}'，无需操作")

    # 刷新按钮
    st.markdown("---")
    if st.button("🔄 刷新会话状态", use_container_width=True):
        load_current_focus_session()


def show_session_history_section():
    """显示会话历史区域"""
    st.subheader("📚 专注历史")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.write("查看历史专注记录")

    with col2:
        if st.button("🔄 刷新历史", use_container_width=True):
            load_session_history()

    # 加载历史记录
    if "focus_history" not in st.session_state:
        load_session_history()

    history = st.session_state.get("focus_history", [])

    if not history:
        st.info("📭 暂无专注历史")
        return

    # 显示历史记录
    display_session_history(history)


def display_session_history(history: List[Dict[str, Any]]):
    """显示专注历史记录"""
    if not history:
        return

    st.write(f"**共 {len(history)} 条记录**")

    for i, session_record in enumerate(history[:10]):  # 只显示最近10条
        session_info = session_record.get("session", {})
        task_id = session_info.get("task_id", "")
        session_type = session_info.get("session_type", "focus")
        status = session_info.get("status", "unknown")
        start_time = session_info.get("start_time", "")
        end_time = session_info.get("end_time", "")

        # 状态映射
        status_map = {
            "focus": "🍅 专注",
            "pause": "⏸️ 暂停",
            "completed": "✅ 完成",
            "cancelled": "❌ 取消"
        }

        # 创建卡片布局
        with st.expander(f"{status_map.get(status, status)} - {start_time[:10]}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**任务ID**: `{task_id[:12]}...`")
                st.write(f"**状态**: {status_map.get(status, status)}")
                st.write(f"**类型**: {session_type}")

                # 获取任务详情
                task_detail = get_task_detail_by_id(task_id)
                if task_detail:
                    task_title = task_detail.get("title", "未命名任务")
                    st.write(f"**任务**: 📌 {task_title}")

            with col2:
                if start_time:
                    st.write(f"**开始**: {start_time[:19]}")
                if end_time:
                    st.write(f"**结束**: {end_time[:19]}")
                if start_time and end_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = end_dt - start_dt
                    minutes = int(duration.total_seconds() / 60)
                    st.write(f"**时长**: {minutes} 分钟")

    if len(history) > 10:
        st.info(f"💡 只显示最近10条记录，总共{len(history)}条")


def load_current_focus_session():
    """加载当前专注会话"""
    with st.spinner("正在加载当前会话..."):
        # 这里需要一个API来获取活跃会话，暂时使用会话列表API
        response = api_client.get("/focus/sessions?page=1&page_size=1")

        if response and response.get("code") == 200:
            data = response.get("data", {})
            items = data.get("items", [])

            # 查找活跃会话
            active_session = None
            for session in items:
                session_info = session.get("session", {})
                status = session_info.get("status", "")
                if status in ["focus", "pause"]:
                    active_session = session
                    break

            st.session_state.current_focus_session = active_session
        else:
            st.session_state.current_focus_session = None
            show_error(response, "❌ 加载会话失败")


def load_tasks_for_focus():
    """为专注功能加载任务列表"""
    with st.spinner("正在加载任务列表..."):
        response = api_client.get("/tasks/")

        if response and response.get("code") == 200:
            data = response.get("data", {})
            if isinstance(data, dict) and "items" in data:
                tasks = data["items"]
            elif isinstance(data, list):
                tasks = data
            else:
                tasks = []

            st.session_state.tasks = tasks
        else:
            st.session_state.tasks = []


def load_session_history():
    """加载专注历史记录"""
    with st.spinner("正在加载专注历史..."):
        response = api_client.get("/focus/sessions?page=1&page_size=50")

        if response and response.get("code") == 200:
            data = response.get("data", {})
            items = data.get("items", [])
            st.session_state.focus_history = items
            st.success(f"✅ 成功加载 {len(items)} 条历史记录")
        else:
            st.session_state.focus_history = []
            show_error(response, "❌ 加载历史记录失败")


def start_focus_session(task_id: str):
    """
    开始专注会话
    调用 POST /focus/sessions

    Args:
        task_id: 任务ID
    """
    request_data = {
        "task_id": task_id,
        "session_type": "focus"
    }

    with st.spinner("正在开始专注会话..."):
        response = api_client.post("/focus/sessions", json=request_data)

        if handle_api_response(response, "✅ 专注会话已开始"):
            # 重新加载当前会话
            load_current_focus_session()


def pause_focus_session(session_id: str):
    """
    暂停专注会话
    调用 POST /focus/sessions/{id}/pause

    Args:
        session_id: 会话ID
    """
    with st.spinner("正在暂停专注会话..."):
        response = api_client.post(f"/focus/sessions/{session_id}/pause")

        if handle_api_response(response, "✅ 专注会话已暂停"):
            # 重新加载当前会话
            load_current_focus_session()


def resume_focus_session(session_id: str):
    """
    恢复专注会话
    调用 POST /focus/sessions/{id}/resume

    Args:
        session_id: 会话ID
    """
    with st.spinner("正在恢复专注会话..."):
        response = api_client.post(f"/focus/sessions/{session_id}/resume")

        if handle_api_response(response, "✅ 专注会话已恢复"):
            # 重新加载当前会话
            load_current_focus_session()


def complete_focus_session(session_id: str):
    """
    完成专注会话
    调用 POST /focus/sessions/{id}/complete

    Args:
        session_id: 会话ID
    """
    with st.spinner("正在完成专注会话..."):
        response = api_client.post(f"/focus/sessions/{session_id}/complete")

        if handle_api_response(response, "✅ 专注会话已完成"):
            # 重新加载当前会话和历史记录
            load_current_focus_session()
            load_session_history()


def get_task_detail_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """
    根据任务ID获取任务详情

    Args:
        task_id: 任务ID

    Returns:
        任务详情数据，如果失败返回None
    """
    # 先从session_state中查找
    tasks = st.session_state.get("tasks", [])
    for task in tasks:
        if task.get("id") == task_id:
            return task

    # 如果没找到，调用API获取
    response = api_client.get(f"/tasks/{task_id}")
    if response and response.get("code") == 200:
        return response.get("data", {})

    return None


def show_focus_instructions():
    """显示使用说明"""
    st.subheader("📖 使用说明")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.write("**🍅 开始专注**")
        st.write("• 选择待办任务")
        st.write("• 点击开始专注")
        st.write("• 自动记录时间")

    with col2:
        st.write("**⏸️ 会话控制**")
        st.write("• 暂停当前专注")
        st.write("• 恢复专注会话")
        st.write("• 完成专注记录")

    with col3:
        st.write("**📚 历史记录**")
        st.write("• 查看专注历史")
        st.write("• 统计专注时长")
        st.write("• 关联任务信息")

    st.info("💡 **提示**: 专注会话与任务关联，完成专注后会自动更新任务状态！")


if __name__ == "__main__":
    main()