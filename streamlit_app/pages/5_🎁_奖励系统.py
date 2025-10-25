"""
Streamlit 测试面板 - 奖励系统页面

这个文件提供：
1. 奖品目录查看和兑换
2. 我的奖品列表
3. 我的材料列表
4. 可用配方和兑换功能

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from streamlit_app.config import api_client
from streamlit_app.state_manager import (
    is_authenticated,
    show_auth_status
)
from streamlit_app.components.json_viewer import render_json, render_api_response
from streamlit_app.components.error_handler import show_error, handle_api_response

def main():
    """奖励系统页面主函数"""
    # 页面配置
    st.set_page_config(
        page_title="奖励系统 - TaKeKe API 测试面板",
        page_icon="🎁",
        layout="wide"
    )

    st.title("🎁 奖励系统")
    st.markdown("---")

    # 检查认证状态
    if not is_authenticated():
        st.warning("⚠️ 请先进行认证才能使用奖励系统")
        st.info("请在左侧导航栏选择 '🏠 认证' 页面进行登录")
        return

    # 显示认证状态
    show_auth_status()
    st.markdown("---")

    # 显示奖励系统标签页
    show_reward_tabs()

def show_reward_tabs():
    """显示奖励系统的标签页"""
    # 创建四个标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 奖品目录",
        "🎯 我的奖品",
        "📦 我的材料",
        "⚗️ 可用配方"
    ])

    with tab1:
        show_reward_catalog()

    with tab2:
        show_my_rewards()

    with tab3:
        show_my_materials()

    with tab4:
        show_available_recipes()

def show_reward_catalog():
    """显示奖品目录"""
    st.subheader("🏆 奖品目录")

    # 刷新按钮
    if st.button("🔄 刷新奖品目录", use_container_width=False):
        load_reward_catalog()

    # 加载并显示奖品目录
    if "reward_catalog" not in st.session_state:
        load_reward_catalog()

    catalog = st.session_state.reward_catalog

    if not catalog:
        st.info("📭 暂无奖品可用")
        return

    st.success(f"🎁 当前共有 {len(catalog)} 个奖品可兑换")

    # 显示奖品列表
    for i, reward in enumerate(catalog):
        reward_id = reward.get("id")
        name = reward.get("name", f"奖品 {reward_id}")
        description = reward.get("description", "暂无描述")
        points_cost = reward.get("points_cost", 0)
        stock = reward.get("stock", 0)

        # 奖品卡片
        with st.container():
            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])

            with col1:
                st.markdown(f"### 🎁 {name}")
                if description:
                    st.caption(description)

            with col2:
                st.metric("所需积分", points_cost)

            with col3:
                st.metric("库存", stock)

            with col4:
                if stock > 0:
                    if st.button(
                        "🛒 兑换",
                        key=f"redeem_{reward_id}",
                        use_container_width=True,
                        type="primary"
                    ):
                        redeem_reward(reward_id, name)
                else:
                    st.button(
                        "😔 缺货",
                        key=f"out_of_stock_{reward_id}",
                        use_container_width=True,
                        disabled=True
                    )

            st.markdown("---")

def show_my_rewards():
    """显示我的奖品"""
    st.subheader("🎯 我的奖品")

    # 刷新按钮
    if st.button("🔄 刷新我的奖品", use_container_width=False):
        load_my_rewards()

    # 加载并显示我的奖品
    if "my_rewards" not in st.session_state:
        load_my_rewards()

    my_rewards = st.session_state.my_rewards

    if not my_rewards:
        st.info("📭 暂无奖品，快去兑换吧！")
        return

    st.success(f"🎯 您拥有 {len(my_rewards)} 个奖品")

    # 使用表格显示奖品
    import pandas as pd

    # 准备表格数据
    table_data = []
    for reward in my_rewards:
        table_data.append({
            "奖品名称": reward.get("name", "未知"),
            "获得时间": reward.get("acquired_at", "未知"),
            "状态": reward.get("status", "未知"),
            "描述": reward.get("description", "暂无描述")[:50] + "..." if len(reward.get("description", "")) > 50 else reward.get("description", "暂无描述")
        })

    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

    # 详细信息展开区域
    if st.checkbox("📋 显示详细信息"):
        for reward in my_rewards:
            with st.expander(f"🎁 {reward.get('name', '未知奖品')}"):
                render_json(reward, "奖品详细信息")

def show_my_materials():
    """显示我的材料"""
    st.subheader("📦 我的材料")

    # 刷新按钮
    if st.button("🔄 刷新我的材料", use_container_width=False):
        load_my_materials()

    # 加载并显示我的材料
    if "my_materials" not in st.session_state:
        load_my_materials()

    materials = st.session_state.my_materials

    if not materials:
        st.info("📭 暂无材料")
        return

    st.success(f"📦 您拥有 {len(materials)} 种材料")

    # 使用表格显示材料
    import pandas as pd

    # 准备表格数据
    table_data = []
    for material in materials:
        table_data.append({
            "材料名称": material.get("name", "未知"),
            "数量": material.get("quantity", 0),
            "类型": material.get("type", "未知"),
            "描述": material.get("description", "暂无描述")[:50] + "..." if len(material.get("description", "")) > 50 else material.get("description", "暂无描述")
        })

    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

    # 详细信息展开区域
    if st.checkbox("📋 显示详细信息"):
        for material in materials:
            with st.expander(f"📦 {material.get('name', '未知材料')}"):
                render_json(material, "材料详细信息")

def show_available_recipes():
    """显示可用配方"""
    st.subheader("⚗️ 可用配方")

    # 刷新按钮
    if st.button("🔄 刷新可用配方", use_container_width=False):
        load_available_recipes()

    # 加载并显示可用配方
    if "available_recipes" not in st.session_state:
        load_available_recipes()

    recipes = st.session_state.available_recipes

    if not recipes:
        st.info("📭 暂无可用配方")
        return

    st.success(f"⚗️ 当前共有 {len(recipes)} 个配方可用")

    # 显示配方列表
    for i, recipe in enumerate(recipes):
        recipe_id = recipe.get("id")
        name = recipe.get("name", f"配方 {recipe_id}")
        description = recipe.get("description", "暂无描述")
        result_item = recipe.get("result_item", {})
        required_materials = recipe.get("required_materials", [])

        # 配方卡片
        with st.container():
            st.markdown(f"### ⚗️ {name}")

            if description:
                st.caption(description)

            # 显示所需材料
            if required_materials:
                st.markdown("**所需材料:**")
                material_cols = st.columns(len(required_materials))
                for j, material in enumerate(required_materials):
                    with material_cols[j]:
                        material_name = material.get("name", "未知")
                        material_quantity = material.get("quantity", 0)
                        st.metric(material_name, material_quantity)

            # 显示合成结果
            if result_item:
                result_name = result_item.get("name", "未知")
                result_quantity = result_item.get("quantity", 0)
                st.markdown(f"**合成结果:** {result_name} x{result_quantity}")

            # 合成按钮
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(
                    "🔨 合成",
                    key=f"craft_{recipe_id}",
                    use_container_width=True,
                    type="primary"
                ):
                    craft_recipe(recipe_id, name)
            with col2:
                if st.button(
                    "📋 详情",
                    key=f"recipe_detail_{recipe_id}",
                    use_container_width=True
                ):
                    with st.expander(f"配方详情: {name}", expanded=True):
                        render_json(recipe, "完整配方信息")

            st.markdown("---")

def load_reward_catalog():
    """加载奖品目录"""
    with st.spinner("正在加载奖品目录..."):
        response = api_client.get("/rewards/catalog")

        if handle_api_response(response, "奖品目录加载成功"):
            st.session_state.reward_catalog = response.get("rewards", [])
        else:
            st.session_state.reward_catalog = []

def load_my_rewards():
    """加载我的奖品"""
    with st.spinner("正在加载我的奖品..."):
        response = api_client.get("/rewards/my-rewards")

        if handle_api_response(response, "我的奖品加载成功"):
            st.session_state.my_rewards = response.get("data", [])
        else:
            st.session_state.my_rewards = []

def load_my_materials():
    """加载我的材料"""
    with st.spinner("正在加载我的材料..."):
        response = api_client.get("/rewards/materials")

        if handle_api_response(response, "我的材料加载成功"):
            st.session_state.my_materials = response.get("data", [])
        else:
            st.session_state.my_materials = []

def load_available_recipes():
    """加载可用配方"""
    with st.spinner("正在加载可用配方..."):
        response = api_client.get("/rewards/recipes")

        if handle_api_response(response, "可用配方加载成功"):
            st.session_state.available_recipes = response.get("data", [])
        else:
            st.session_state.available_recipes = []

def redeem_reward(reward_id: str, reward_name: str):
    """兑换奖品"""
    with st.spinner(f"正在兑换 {reward_name}..."):
        response = api_client.post(f"/rewards/exchange/{reward_id}")

        if handle_api_response(response, f"🎉 成功兑换 {reward_name}！"):
            # 重新加载相关数据
            load_my_rewards()
            load_reward_catalog()
            st.success("🎉 兑换成功！请在 '我的奖品' 标签页中查看。")
        else:
            st.error("❌ 兑换失败，请检查积分余额或库存")

def craft_recipe(recipe_id: str, recipe_name: str):
    """使用配方合成物品"""
    with st.spinner(f"正在使用配方 {recipe_name} 合成..."):
        response = api_client.post(f"/rewards/recipes/{recipe_id}/redeem")

        if handle_api_response(response, f"🔨 成功使用 {recipe_name} 合成！"):
            # 重新加载相关数据
            load_my_materials()
            load_my_rewards()
            st.success("🔨 合成成功！请在 '我的奖品' 或 '我的材料' 标签页中查看。")
        else:
            st.error("❌ 合成失败，请检查材料是否充足")

if __name__ == "__main__":
    main()