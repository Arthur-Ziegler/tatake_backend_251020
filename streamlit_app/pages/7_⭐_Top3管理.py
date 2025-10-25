"""
Streamlit 测试面板 - Top3管理页面

这个文件提供：
1. 设置每日Top3重要任务功能
2. 查询指定日期Top3任务功能
3. 显示积分消耗和状态信息
4. 任务选择和确认界面

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from streamlit_app.config import api_client
from streamlit_app.state_manager import is_authenticated, show_auth_status
from streamlit_app.components.json_viewer import render_json, render_api_response
from streamlit_app.components.error_handler import show_error, handle_api_response


def main():
    """Top3管理页面主函数"""
    st.set_page_config(
        page_title="Top3管理 - TaKeKe API 测试面板",
        page_icon="⭐",
        layout="wide"
    )

    st.title("⭐ Top3 管理")
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
    show_top3_management_interface()


def show_top3_management_interface():
    """显示Top3管理主界面"""
    # 创建两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        show_set_top3_section()

    with col2:
        show_query_top3_section()

    st.markdown("---")

    # 显示操作说明
    show_instructions()


def show_set_top3_section():
    """显示设置Top3区域"""
    st.subheader("🎯 设置今日Top3")

    # 加载任务列表
    if "tasks" not in st.session_state:
        load_tasks_for_top3()

    tasks = st.session_state.get("tasks", [])

    if not tasks:
        st.warning("⚠️ 暂无可用任务，请先创建任务")
        if st.button("📋 前往任务管理", use_container_width=True):
            st.switch_page("pages/2_📋_任务管理.py")
        return

    # 任务选择
    st.write("**选择Top3任务（1-3个）**")

    # 创建任务选项
    task_options = {}
    for task in tasks:
        task_id = task.get("id", "")
        title = task.get("title", "未命名任务")
        status = task.get("status", "unknown")
        priority = task.get("priority", "medium")

        # 只显示待办任务
        if status == "pending":
            status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(status, "❓")
            priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(priority, "⚪")
            display_text = f"{status_emoji} {priority_emoji} {title} ({task_id[:8]}...)"
            task_options[display_text] = task_id

    if not task_options:
        st.info("📭 暂无待办任务")
        return

    # 多选框
    selected_tasks = st.multiselect(
        "选择任务",
        options=list(task_options.keys()),
        help="选择1-3个最重要的任务作为今日Top3"
    )

    # 验证选择
    if len(selected_tasks) > 3:
        st.error("❌ 最多只能选择3个任务")
        return

    if len(selected_tasks) == 0:
        st.info("💡 请选择1-3个任务设置Top3")
        return

    # 显示选中的任务
    st.write("**已选择的任务：**")
    for i, task_display in enumerate(selected_tasks, 1):
        task_id = task_options[task_display]
        st.write(f"{i}. {task_display}")

    # 设置按钮
    st.write("---")

    # 确认设置
    if st.session_state.get("confirm_top3", False):
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("✅ 确认设置Top3", type="primary", use_container_width=True):
                set_top3_tasks([task_options[task] for task in selected_tasks])

        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.confirm_top3 = False
                st.rerun()
    else:
        if st.button("🎯 设置Top3任务", type="primary", use_container_width=True):
            st.session_state.confirm_top3 = True
            st.rerun()


def show_query_top3_section():
    """显示查询Top3区域"""
    st.subheader("🔍 查询Top3历史")

    # 日期选择
    today = date.today()
    default_date = today.strftime("%Y-%m-%d")

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_date = st.date_input(
            "选择查询日期",
            value=today,
            max_value=today + timedelta(days=1),
            help="查询指定日期的Top3任务设置"
        )

    with col2:
        if st.button("🔍 查询", use_container_width=True):
            query_top3_by_date(selected_date.strftime("%Y-%m-%d"))

    # 显示查询结果
    if st.session_state.get("top3_result"):
        show_top3_result(st.session_state.top3_result)


def show_top3_result(result: Dict[str, Any]):
    """显示Top3查询结果"""
    if not result:
        return

    data = result.get("data", {})
    top3_tasks = data.get("top3_tasks", [])
    query_date = data.get("date", "未知日期")

    st.write(f"**{query_date} 的Top3任务：**")

    if not top3_tasks:
        st.info("📭 该日期未设置Top3任务")
        return

    # 显示Top3任务列表
    for i, task_info in enumerate(top3_tasks, 1):
        task_id = task_info.get("task_id", "")
        position = task_info.get("position", i)

        st.write(f"**{position}.** 任务ID: `{task_id}`")

        # 尝试获取任务详情
        task_detail = get_task_detail_by_id(task_id)
        if task_detail:
            title = task_detail.get("title", "未命名任务")
            description = task_detail.get("description", "")
            status = task_detail.get("status", "unknown")
            priority = task_detail.get("priority", "medium")

            status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "cancelled": "❌"}.get(status, "❓")
            priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(priority, "⚪")

            st.write(f"   {status_emoji} {priority_emoji} **{title}**")
            if description:
                st.write(f"   📝 {description[:100]}...")
        else:
            st.write(f"   📝 任务详情获取失败")

        st.write("")

    # 显示积分消耗信息
    if "points_consumed" in data:
        points_consumed = data["points_consumed"]
        remaining_balance = data.get("remaining_balance", 0)

        st.info(f"💰 **积分消耗**: {points_consumed} 积分")
        st.info(f"💳 **剩余余额**: {remaining_balance} 积分")

    # 显示完整响应
    with st.expander("📄 完整响应数据", expanded=False):
        st.json(result)


def load_tasks_for_top3():
    """为Top3设置加载任务列表"""
    with st.spinner("正在加载任务列表..."):
        response = api_client.get("/tasks/")

        if response and response.get("code") == 200:
            # 从响应中提取任务列表
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
            show_error(response, "❌ 加载任务列表失败")


def set_top3_tasks(task_ids: List[str]):
    """
    设置Top3任务
    调用 POST /tasks/special/top3

    Args:
        task_ids: 任务ID列表
    """
    # 构建请求数据
    top3_data = []
    for i, task_id in enumerate(task_ids, 1):
        top3_data.append({
            "task_id": task_id,
            "position": i
        })

    request_data = {
        "task_ids": top3_data
    }

    with st.spinner("正在设置Top3任务..."):
        response = api_client.post("/tasks/special/top3", json=request_data)

        if handle_api_response(response, "✅ Top3设置成功，消耗300积分"):
            # 清理确认状态
            st.session_state.confirm_top3 = False
            # 清理之前的查询结果
            if "top3_result" in st.session_state:
                del st.session_state.top3_result
            # 重新加载任务列表
            load_tasks_for_top3()


def query_top3_by_date(target_date: str):
    """
    查询指定日期的Top3任务
    调用 GET /tasks/special/top3/{date}

    Args:
        target_date: 目标日期，格式YYYY-MM-DD
    """
    with st.spinner(f"正在查询 {target_date} 的Top3任务..."):
        response = api_client.get(f"/tasks/special/top3/{target_date}")

        if response and response.get("code") == 200:
            st.session_state.top3_result = response
            st.success(f"✅ 成功获取 {target_date} 的Top3任务")
        else:
            st.session_state.top3_result = None
            show_error(response, f"❌ 查询 {target_date} 的Top3任务失败")


def get_task_detail_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """
    根据任务ID获取任务详情
    调用 GET /tasks/{task_id}

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


def show_instructions():
    """显示操作说明"""
    st.subheader("📖 使用说明")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("**🎯 设置Top3**")
        st.write("• 每天只能设置一次Top3")
        st.write("• 需要消耗300积分")
        st.write("• 最多选择3个任务")
        st.write("• 支持设置优先级位置")

    with col2:
        st.write("**🔍 查询功能**")
        st.write("• 查询任意日期的Top3")
        st.write("• 显示任务详细信息")
        st.write("• 显示积分消耗记录")
        st.write("• 支持历史数据追溯")

    st.info("💡 **提示**: Top3任务是每日最重要的3个任务，建议优先完成这些任务以获得更多奖励！")


if __name__ == "__main__":
    main()