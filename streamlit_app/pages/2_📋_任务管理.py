"""
Streamlit 测试面板 - 任务管理页面

这个文件提供：
1. 任务列表展示（树形结构）
2. 任务创建功能（快速创建和完整表单）
3. 任务操作功能（完成/删除）
4. JSON 数据查看器

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from datetime import datetime
from typing import List, Optional, Dict, Any

from streamlit_app.config import api_client
from streamlit_app.state_manager import is_authenticated, show_auth_status
from streamlit_app.components.json_viewer import render_json, render_api_response
from streamlit_app.components.error_handler import show_error, handle_api_response


def main():
    """任务管理页面主函数"""
    st.set_page_config(
        page_title="任务管理 - TaKeKe API 测试面板",
        page_icon="📋",
        layout="wide"
    )

    st.title("📋 任务管理")
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
    show_task_management_interface()


def show_task_management_interface():
    """显示任务管理主界面"""
    # 数据加载区域
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("📊 任务列表")

    with col2:
        if st.button("🔄 刷新任务列表", use_container_width=True):
            load_tasks()

    # 加载并显示任务
    if "tasks" not in st.session_state:
        load_tasks()

    # 显示任务树形视图
    tasks = st.session_state.get("tasks", [])
    if tasks:
        render_task_tree(tasks)
    else:
        st.info("📭 暂无任务，请创建任务")

    st.markdown("---")

    # 任务创建区域
    show_task_creation_section()

    st.markdown("---")

    # JSON 查看器
    if tasks:
        render_json(tasks, "📄 任务列表完整数据", expanded=False)


def load_tasks():
    """
    加载任务列表
    调用 GET /tasks/
    """
    with st.spinner("正在加载任务列表..."):
        response = api_client.get("/tasks/")

        if response and response.get("code") == 200:
            # 从响应中提取任务列表
            data = response.get("data", {})
            if isinstance(data, dict) and "tasks" in data:
                tasks = data["tasks"]
            elif isinstance(data, dict) and "items" in data:
                tasks = data["items"]
            elif isinstance(data, list):
                tasks = data
            else:
                tasks = []

            st.session_state.tasks = tasks
            st.success(f"✅ 成功加载 {len(tasks)} 个任务")
        else:
            st.session_state.tasks = []
            show_error(response, "❌ 加载任务列表失败")
            st.error("请检查网络连接或稍后重试")


def render_task_tree(tasks: List[Dict[str, Any]]):
    """
    渲染任务树形视图

    Args:
        tasks: 任务列表
    """
    if not tasks:
        st.info("📭 暂无任务")
        return

    st.subheader("🌳 任务树形视图")

    # 获取根任务（没有父任务的任务）
    root_tasks = [task for task in tasks if not task.get("parent_id")]

    if not root_tasks:
        st.info("📭 暂无根任务")
        return

    # 渲染每个根任务及其子任务
    for i, task in enumerate(root_tasks):
        render_task_node(task, tasks, level=0, key_prefix=f"root_{i}")


def render_task_node(task: Dict[str, Any], all_tasks: List[Dict[str, Any]], level: int, key_prefix: str = ""):
    """
    渲染单个任务节点

    Args:
        task: 当前任务数据
        all_tasks: 所有任务列表（用于查找子任务）
        level: 当前层级（用于缩进）
        key_prefix: 键前缀（确保唯一性）
    """
    # 计算缩进
    indent = "　" * level  # 使用全角空格进行缩进

    # 获取任务信息
    task_id = task.get("id", "")
    title = task.get("title", "未命名任务")
    status = task.get("status", "unknown")
    priority = task.get("priority", "medium")

    # 状态映射
    status_map = {
        "pending": "⏳ 待办",
        "completed": "✅ 已完成",
        "cancelled": "❌ 已取消",
        "in_progress": "🔄 进行中"
    }

    # 优先级映射
    priority_map = {
        "low": "🟢 低",
        "medium": "🟡 中",
        "high": "🔴 高"
    }

    # 创建列布局
    col1, col2, col3, col4, col5 = st.columns([4, 2, 1, 1, 1])

    with col1:
        st.write(f"{indent}📌 {title}")
        if task.get("description"):
            st.caption(f"{indent}   {task['description'][:100]}...")

    with col2:
        st.write(status_map.get(status, status))
        st.write(priority_map.get(priority, priority))

    with col3:
        if st.button("✅ 完成", key=f"complete_{key_prefix}_{task_id}", use_container_width=True):
            complete_task(task_id)

    with col4:
        if st.button("🗑️ 删除", key=f"delete_{key_prefix}_{task_id}", use_container_width=True):
            delete_task(task_id)

    with col5:
        if st.button("👁️ 详情", key=f"detail_{key_prefix}_{task_id}", use_container_width=True):
            show_task_detail(task)

    # 递归渲染子任务
    children = [t for t in all_tasks if t.get("parent_id") == task_id]
    for i, child in enumerate(children):
        render_task_node(child, all_tasks, level + 1, key_prefix=f"{key_prefix}_{i}")


def show_task_creation_section():
    """显示任务创建区域"""
    st.subheader("➕ 创建任务")

    # 创建两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("**快速创建测试任务**")
        if st.button("🚀 快速创建测试任务", type="primary", use_container_width=True):
            create_quick_test_task()

    with col2:
        st.write("**完整表单创建**")
        if st.button("📝 打开完整表单", use_container_width=True):
            st.session_state.show_full_form = not st.session_state.get("show_full_form", False)

    # 显示完整表单（如果展开）
    if st.session_state.get("show_full_form", False):
        show_full_task_form()


def create_quick_test_task():
    """
    快速创建测试任务
    调用 POST /tasks/
    """
    current_time = datetime.now().strftime('%H%M%S')
    task_data = {
        "title": f"测试任务_{current_time}",
        "description": f"这是一个在 {current_time} 创建的测试任务",
        "priority": "medium"
    }

    with st.spinner("正在创建测试任务..."):
        response = api_client.post("/tasks/", json=task_data)

        if handle_api_response(response, "✅ 测试任务创建成功"):
            # 重新加载任务列表
            load_tasks()


def show_full_task_form():
    """显示完整任务创建表单"""
    st.write("---")
    st.write("**📝 完整任务创建表单**")

    with st.form("create_task_form"):
        # 基础字段
        title = st.text_input("任务标题 *", placeholder="请输入任务标题")
        description = st.text_area("任务描述", placeholder="请输入任务描述（可选）")
        priority = st.selectbox("优先级", options=["low", "medium", "high"], format_func=lambda x: {"low": "低", "medium": "中", "high": "高"}[x])

        # 高级选项
        with st.expander("🔧 高级选项"):
            # 获取现有任务列表作为父任务选项
            tasks = st.session_state.get("tasks", [])
            parent_options = {"无": None}
            for task in tasks:
                task_title = task.get("title", "未命名任务")
                task_id = task.get("id", "")
                parent_options[f"{task_title} ({task_id[:8]}...)"] = task_id

            selected_parent = st.selectbox("父任务", options=list(parent_options.keys()))
            parent_id = parent_options[selected_parent]

        # 表单按钮
        col1, col2 = st.columns([1, 1])
        with col1:
            submitted = st.form_submit_button("✅ 创建任务", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)

        if cancelled:
            st.session_state.show_full_form = False
            st.rerun()

        if submitted:
            if not title:
                st.error("❌ 请输入任务标题")
                return

            create_task_with_full_form(title, description, priority, parent_id)


def create_task_with_full_form(title: str, description: str, priority: str, parent_id: Optional[str]):
    """
    使用完整表单创建任务

    Args:
        title: 任务标题
        description: 任务描述
        priority: 优先级
        parent_id: 父任务ID
    """
    task_data = {
        "title": title,
        "description": description if description else None,
        "priority": priority
    }

    if parent_id:
        task_data["parent_id"] = parent_id

    with st.spinner("正在创建任务..."):
        response = api_client.post("/tasks/", json=task_data)

        if handle_api_response(response, "✅ 任务创建成功", show_error_detail=False):
            # 清理表单状态
            st.session_state.show_full_form = False
            # 重新加载任务列表
            load_tasks()


def complete_task(task_id: str):
    """
    完成任务
    调用 POST /tasks/{task_id}/complete

    Args:
        task_id: 任务ID
    """
    completion_data = {}  # 完成任务的请求体可能为空

    with st.spinner(f"正在完成任务 {task_id[:8]}..."):
        response = api_client.post(f"/tasks/{task_id}/complete", json=completion_data)

        if handle_api_response(response, "✅ 任务完成成功"):
            # 重新加载任务列表
            load_tasks()


def delete_task(task_id: str):
    """
    删除任务
    调用 DELETE /tasks/{task_id}

    Args:
        task_id: 任务ID
    """
    # 确认删除
    if st.session_state.get(f"confirm_delete_{task_id}", False):
        with st.spinner(f"正在删除任务 {task_id[:8]}..."):
            response = api_client.delete(f"/tasks/{task_id}")

            if handle_api_response(response, "✅ 任务删除成功"):
                # 清理确认状态
                if f"confirm_delete_{task_id}" in st.session_state:
                    del st.session_state[f"confirm_delete_{task_id}"]
                # 重新加载任务列表
                load_tasks()
    else:
        st.session_state[f"confirm_delete_{task_id}"] = True
        st.warning(f"⚠️ 确认要删除任务 {task_id[:8]}... 吗？请再次点击删除按钮确认。")
        st.rerun()


def show_task_detail(task: Dict[str, Any]):
    """显示任务详情"""
    task_id = task.get("id", "")
    st.write(f"**任务详情:** {task_id[:12]}...")
    render_json(task, f"📋 任务: {task.get('title', '未命名')}", expanded=True)


if __name__ == "__main__":
    main()