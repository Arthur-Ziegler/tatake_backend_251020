"""
Streamlit 测试面板 - JSON 查看器组件

这个文件提供：
1. 可展开的 JSON 数据展示
2. 格式化的 JSON 渲染
3. 美观的数据展示界面

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
import json
from typing import Any, Dict, Optional


def render_json(data: Any, title: str = "响应详情", expanded: bool = False):
    """
    渲染可展开的 JSON 查看器

    Args:
        data: 要展示的数据（字典、列表或其他）
        title: 展开器的标题
        expanded: 是否默认展开
    """
    if data is None:
        st.warning("⚠️ 没有数据可显示")
        return

    try:
        # 使用 st.expander 创建可展开容器
        with st.expander(title, expanded=expanded):
            # 使用 st.json 格式化显示 JSON
            st.json(data)

            # 提供复制功能
            if st.button("📋 复制 JSON 数据", key=f"copy_{title}"):
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                st.code(json_str, language="json")
                st.success("✅ JSON 数据已显示，可以手动复制")

    except Exception as e:
        st.error(f"❌ 渲染 JSON 数据时出错: {str(e)}")
        # 如果 JSON 渲染失败，尝试以文本形式显示
        st.code(str(data))


def render_simple_dict(data: Dict[str, Any], title: str = "数据详情"):
    """
    渲染简单的键值对数据

    Args:
        data: 字典数据
        title: 标题
    """
    if not data:
        st.info("📭 暂无数据")
        return

    st.subheader(title)

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            # 复杂类型使用 JSON 展示
            with st.expander(f"📄 {key}"):
                st.json(value)
        else:
            # 简单类型直接显示
            st.write(f"**{key}**: `{value}`")


def render_api_response(response: Optional[Dict[str, Any]], show_success: bool = True):
    """
    渲染 API 响应数据

    Args:
        response: API 响应数据
        show_success: 是否显示成功消息
    """
    if not response:
        st.warning("⚠️ 没有响应数据")
        return

    # 显示响应状态
    code = response.get("code", 0)
    message = response.get("message", "")

    if show_success and code == 200:
        st.success("✅ 请求成功")

    if message:
        st.info(f"📝 消息: {message}")

    # 显示数据部分
    if "data" in response:
        render_json(response["data"], "📊 响应数据", expanded=True)

    # 显示完整响应
    render_json(response, "🔍 完整响应", expanded=False)


def render_table_from_dict(data: Dict[str, Any], title: str = "数据表格"):
    """
    将字典数据渲染为表格

    Args:
        data: 字典数据
        title: 表格标题
    """
    if not data:
        st.info("📭 暂无数据")
        return

    st.subheader(title)

    # 创建两列的表格数据
    table_data = []
    for key, value in data.items():
        # 格式化值
        if isinstance(value, (dict, list)):
            formatted_value = f"[{type(value).__name__}] {len(value)} 项"
        else:
            formatted_value = str(value)

        table_data.append([key, formatted_value])

    # 显示表格
    st.table(table_data)