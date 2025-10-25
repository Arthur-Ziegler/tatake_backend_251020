"""
Streamlit 测试面板 - 积分系统页面

这个文件提供：
1. 积分余额显示（大号字体）
2. 积分流水记录（表格）
3. 积分历史查询功能

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_app.config import api_client
from streamlit_app.state_manager import (
    is_authenticated,
    show_auth_status
)
from streamlit_app.components.json_viewer import render_json
from streamlit_app.components.error_handler import show_error, handle_api_response

def main():
    """积分系统页面主函数"""
    # 页面配置
    st.set_page_config(
        page_title="积分系统 - TaKeKe API 测试面板",
        page_icon="💰",
        layout="wide"
    )

    st.title("💰 积分系统")
    st.markdown("---")

    # 检查认证状态
    if not is_authenticated():
        st.warning("⚠️ 请先进行认证才能查看积分信息")
        st.info("请在左侧导航栏选择 '🏠 认证' 页面进行登录")
        return

    # 显示认证状态
    show_auth_status()
    st.markdown("---")

    # 显示积分系统界面
    show_points_interface()

def show_points_interface():
    """显示积分系统主界面"""
    # 显示积分余额
    show_points_balance()

    st.markdown("---")

    # 显示积分流水
    show_points_transactions()

def show_points_balance():
    """显示积分余额"""
    st.subheader("💳 积分余额")

    # 刷新按钮
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 刷新余额", use_container_width=True):
            load_points_balance()

    with col2:
        if st.button("📊 查看统计", use_container_width=True):
            st.session_state.show_statistics = not st.session_state.get("show_statistics", False)

    # 加载并显示余额
    if "points_balance" not in st.session_state:
        load_points_balance()

    balance = st.session_state.points_balance

    if balance is not None:
        # 大号字体显示余额
        st.metric(
            label="当前积分",
            value=f"{balance:,}",
            delta=None
        )

        # 积分等级显示（如果有）
        if balance >= 10000:
            st.success("🏆 积分大师")
        elif balance >= 5000:
            st.success("⭐ 积分专家")
        elif balance >= 2000:
            st.success("🌟 积分达人")
        elif balance >= 1000:
            st.info("💫 积分新星")
        elif balance >= 500:
            st.info("🌱 积分学徒")
        else:
            st.warning("🌱 积分新手")

        # 统计信息
        if st.session_state.get("show_statistics", False):
            show_points_statistics()

    else:
        st.error("❌ 无法获取积分余额")

def show_points_statistics():
    """显示积分统计信息"""
    st.markdown("#### 📊 积分统计")

    # 加载今日获得积分
    with st.spinner("正在加载统计信息..."):
        today = datetime.now().strftime("%Y-%m-%d")

        # 这里可以添加更多统计查询
        # 例如：今日获得、今日消耗、本周变化等

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("今日获得", "+0", delta=None)

        with col2:
            st.metric("今日消耗", "-0", delta=None)

        with col3:
            st.metric("本周变化", "+0", delta=None)

def show_points_transactions():
    """显示积分流水记录"""
    st.subheader("📜 积分流水")

    # 查询选项
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        # 时间范围选择
        time_range = st.selectbox(
            "时间范围",
            options=["最近7天", "最近30天", "最近90天", "全部"],
            index=0,
            key="time_range"
        )

    with col2:
        # 交易类型筛选
        transaction_type = st.selectbox(
            "交易类型",
            options=["全部", "获得", "消耗"],
            index=0,
            key="transaction_type"
        )

    with col3:
        if st.button("🔍 查询", use_container_width=True):
            load_points_transactions(time_range, transaction_type)

    with col4:
        if st.button("📥 导出", use_container_width=True):
            export_transactions()

    # 加载并显示流水记录
    if "points_transactions" not in st.session_state:
        load_points_transactions(time_range, transaction_type)

    transactions = st.session_state.points_transactions

    if not transactions:
        st.info("📭 暂无积分流水记录")
        return

    st.success(f"📜 找到 {len(transactions)} 条流水记录")

    # 准备表格数据
    table_data = []
    for transaction in transactions:
        # 格式化交易金额
        amount = transaction.get("amount", 0)
        formatted_amount = f"+{amount:,}" if amount > 0 else f"{amount:,}"

        # 格式化时间
        created_at = transaction.get("created_at", "")
        if created_at:
            try:
                # 尝试解析时间格式
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = created_at
        else:
            formatted_time = "未知"

        table_data.append({
            "时间": formatted_time,
            "类型": transaction.get("type", "未知"),
            "描述": transaction.get("description", "无描述"),
            "积分变化": formatted_amount,
            "余额": f"{transaction.get('balance_after', 0):,}"
        })

    if table_data:
        df = pd.DataFrame(table_data)

        # 根据积分变化设置颜色
        def highlight_amount(row):
            if '+' in str(row['积分变化']):
                return ['background-color: #d4edda'] * len(row)
            elif '-' in str(row['积分变化']):
                return ['background-color: #f8d7da'] * len(row)
            return [''] * len(row)

        styled_df = df.style.apply(highlight_amount, axis=1)
        st.dataframe(styled_df, use_container_width=True)

        # 详细信息展开区域
        if st.checkbox("📋 显示详细信息"):
            for i, transaction in enumerate(transactions):
                with st.expander(f"📝 交易详情 - {table_data[i]['描述']}"):
                    render_json(transaction, "交易详细信息")

def load_points_balance():
    """加载积分余额"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("❌ 用户ID不存在")
        return

    with st.spinner("正在加载积分余额..."):
        response = api_client.get(f"/points/my-points?user_id={user_id}")

        if handle_api_response(response, "积分余额加载成功"):
            data = response.get("data", {})
            st.session_state.points_balance = data.get("current_balance", 0)
        else:
            st.session_state.points_balance = None

def load_points_transactions(time_range: str, transaction_type: str):
    """加载积分流水记录"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("❌ 用户ID不存在")
        return

    # 构建查询参数
    params = {"user_id": user_id}

    # 根据时间范围添加参数
    if time_range != "全部":
        days_map = {
            "最近7天": 7,
            "最近30天": 30,
            "最近90天": 90
        }
        days = days_map.get(time_range, 7)
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        params["start_date"] = start_date

    # 根据交易类型添加参数
    if transaction_type != "全部":
        params["type"] = transaction_type

    with st.spinner("正在加载积分流水..."):
        response = api_client.get("/points/transactions", params=params)

        if handle_api_response(response, "积分流水加载成功"):
            st.session_state.points_transactions = response.get("data", [])
        else:
            st.session_state.points_transactions = []

def export_transactions():
    """导出积分流水记录"""
    transactions = st.session_state.get("points_transactions", [])

    if not transactions:
        st.warning("⚠️ 没有可导出的数据")
        return

    # 准备导出数据
    export_data = []
    for transaction in transactions:
        export_data.append({
            "时间": transaction.get("created_at", ""),
            "类型": transaction.get("type", ""),
            "描述": transaction.get("description", ""),
            "积分变化": transaction.get("amount", 0),
            "余额后": transaction.get("balance_after", 0)
        })

    if export_data:
        df = pd.DataFrame(export_data)

        # 转换为 CSV 并提供下载
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 下载 CSV 文件",
            data=csv,
            file_name=f"points_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

if __name__ == "__main__":
    main()