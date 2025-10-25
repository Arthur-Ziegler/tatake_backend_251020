"""
Streamlit 测试面板 - 用户管理页面

这个文件提供：
1. 查看个人资料
2. 提交反馈表单
3. 用户设置管理

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from streamlit_app.config import api_client
from streamlit_app.state_manager import (
    is_authenticated,
    show_auth_status
)
from streamlit_app.components.json_viewer import render_json
from streamlit_app.components.error_handler import show_error, handle_api_response

def main():
    """用户管理页面主函数"""
    # 页面配置
    st.set_page_config(
        page_title="用户管理 - TaKeKe API 测试面板",
        page_icon="👤",
        layout="wide"
    )

    st.title("👤 用户管理")
    st.markdown("---")

    # 检查认证状态
    if not is_authenticated():
        st.warning("⚠️ 请先进行认证才能使用用户管理功能")
        st.info("请在左侧导航栏选择 '🏠 认证' 页面进行登录")
        return

    # 显示认证状态
    show_auth_status()
    st.markdown("---")

    # 显示用户管理界面
    show_user_management_interface()

def show_user_management_interface():
    """显示用户管理主界面"""
    # 创建标签页
    tab1, tab2, tab3 = st.tabs([
        "📋 个人资料",
        "💬 反馈建议",
        "⚙️ 账户设置"
    ])

    with tab1:
        show_personal_profile()

    with tab2:
        show_feedback_form()

    with tab3:
        show_account_settings()

def show_personal_profile():
    """显示个人资料"""
    st.subheader("📋 个人资料")

    # 刷新按钮
    if st.button("🔄 刷新资料", use_container_width=False):
        load_user_profile()

    # 加载并显示个人资料
    if "user_profile" not in st.session_state:
        load_user_profile()

    profile = st.session_state.user_profile

    if not profile:
        st.error("❌ 无法获取个人资料")
        return

    # 基本信息卡片
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 基本信息")
        user_id = profile.get("id", "未知")
        user_type = profile.get("user_type", "未知")
        created_at = profile.get("created_at", "未知")
        last_login = profile.get("last_login", "未知")

        st.info(f"**用户ID**: {user_id}")
        st.info(f"**用户类型**: {user_type}")
        st.info(f"**注册时间**: {created_at}")
        st.info(f"**最后登录**: {last_login}")

    with col2:
        st.markdown("### 📊 账户统计")
        # 这里可以显示一些统计数据
        # 例如：任务完成数、获得积分、使用天数等

        # 模拟统计数据（实际应该从API获取）
        st.metric("任务完成", "0")
        st.metric("获得积分", "0")
        st.metric("使用天数", "0")

    # 详细资料
    st.markdown("### 📝 详细资料")

    # 使用 JSON 展示完整资料
    if st.checkbox("🔍 查看完整资料数据"):
        render_json(profile, "用户完整资料")

    # 资料编辑区域（如果有API支持）
    if st.checkbox("✏️ 编辑资料"):
        show_profile_editor(profile)

def show_profile_editor(profile):
    """显示资料编辑器"""
    st.markdown("#### ✏️ 编辑个人资料")

    # 这里可以添加编辑表单
    # 例如：昵称、头像、个人简介等

    with st.form("profile_editor"):
        # 示例编辑字段
        nickname = st.text_input(
            "昵称",
            value=profile.get("nickname", ""),
            placeholder="输入您的昵称"
        )

        bio = st.text_area(
            "个人简介",
            value=profile.get("bio", ""),
            placeholder="介绍一下自己吧...",
            max_chars=200
        )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 保存修改", type="primary")
        with col2:
            cancelled = st.form_submit_button("❌ 取消")

        if submitted:
            # 这里应该调用更新资料的API
            st.success("✅ 资料更新成功（演示）")
            load_user_profile()  # 重新加载资料

        if cancelled:
            st.rerun()

def show_feedback_form():
    """显示反馈表单"""
    st.subheader("💬 反馈建议")

    st.markdown("""
    我们非常重视您的意见和建议！请通过下方表单向我们反馈，帮助我们改进产品和服务。
    """)

    # 反馈类型选择
    feedback_type = st.selectbox(
        "反馈类型",
        options=["功能建议", "问题反馈", "使用体验", "其他", "Bug报告"],
        index=0,
        help="请选择最符合您反馈内容的类型"
    )

    # 反馈内容
    feedback_content = st.text_area(
        "反馈内容",
        placeholder="请详细描述您的反馈内容...",
        height=150,
        max_chars=1000,
        help="请尽可能详细地描述，以便我们更好地理解和处理您的反馈"
    )

    # 联系方式（可选）
    contact_info = st.text_input(
        "联系方式（可选）",
        placeholder="邮箱或手机号，便于我们回复您",
        help="如果您希望我们回复，请留下联系方式"
    )

    # 严重程度（针对问题反馈）
    if feedback_type in ["问题反馈", "Bug报告"]:
        severity = st.selectbox(
            "严重程度",
            options=["轻微", "一般", "严重", "紧急"],
            index=1,
            help="请评估问题的严重程度"
        )
    else:
        severity = None

    # 提交按钮
    col1, col2 = st.columns([1, 1])
    with col1:
        submitted = st.button(
            "📤 提交反馈",
            type="primary",
            use_container_width=True,
            help="点击提交您的反馈"
        )
    with col2:
        if st.button(
            "🗑️ 清空表单",
            use_container_width=True,
            help="清空当前填写的内容"
        ):
            st.session_state.feedback_submitted = False
            st.rerun()

    # 提交反馈
    if submitted:
        if not feedback_content or not feedback_content.strip():
            st.error("❌ 请填写反馈内容")
            return

        submit_feedback(feedback_type, feedback_content.strip(), contact_info, severity)

    # 显示提交历史
    show_feedback_history()

def submit_feedback(feedback_type: str, content: str, contact_info: str, severity: str):
    """提交反馈"""
    if st.session_state.get("feedback_submitted", False):
        st.warning("⚠️ 您已经提交过反馈了，请勿重复提交")
        return

    with st.spinner("正在提交反馈..."):
        feedback_data = {
            "type": feedback_type,
            "content": content,
            "contact_info": contact_info
        }

        if severity:
            feedback_data["severity"] = severity

        response = api_client.post("/users/feedback", json=feedback_data)

        if handle_api_response(response, "🎉 反馈提交成功！", show_error_detail=False):
            st.session_state.feedback_submitted = True
            st.success("""
            ✅ **感谢您的反馈！**

            我们已经收到您的反馈，会尽快处理并回复。
            如果您留下了联系方式，我们会在1-3个工作日内与您联系。

            💡 **小贴士**: 您也可以通过以下方式联系我们：
            - 客服邮箱：support@takeke.com
            - 官方微信群：扫描二维码加入
            """)
        else:
            st.error("❌ 反馈提交失败，请稍后重试")

def show_feedback_history():
    """显示反馈历史"""
    st.markdown("---")
    st.markdown("#### 📜 反馈历史")

    # 这里应该调用API获取用户的反馈历史
    # 暂时显示模拟数据

    feedback_history = st.session_state.get("feedback_history", [])

    if not feedback_history:
        st.info("📭 暂无反馈历史")
        return

    for i, feedback in enumerate(feedback_history):
        with st.expander(f"📝 {feedback.get('type', '未知')} - {feedback.get('created_at', '未知时间')}"):
            st.markdown(f"**内容**: {feedback.get('content', '无内容')}")
            st.markdown(f"**状态**: {feedback.get('status', '未知')}")
            if feedback.get('reply'):
                st.markdown(f"**回复**: {feedback['reply']}")

def show_account_settings():
    """显示账户设置"""
    st.subheader("⚙️ 账户设置")

    st.markdown("""
    在这里您可以管理账户的各种设置选项。
    """)

    # 通知设置
    st.markdown("### 🔔 通知设置")

    email_notifications = st.checkbox(
        "邮件通知",
        value=True,
        help="通过邮件接收重要通知"
    )

    push_notifications = st.checkbox(
        "推送通知",
        value=True,
        help="通过应用推送接收通知"
    )

    marketing_notifications = st.checkbox(
        "营销通知",
        value=False,
        help="接收产品更新和优惠信息"
    )

    # 隐私设置
    st.markdown("### 🔒 隐私设置")

    profile_visibility = st.selectbox(
        "资料可见性",
        options=["公开", "仅好友", "私密"],
        index=1,
        help="控制其他用户是否可以看到您的资料"
    )

    activity_visibility = st.checkbox(
        "显示活动状态",
        value=True,
        help="允许其他用户看到您的在线状态"
    )

    # 账户安全
    st.markdown("### 🛡️ 账户安全")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔑 修改密码", use_container_width=True):
            st.info("密码修改功能暂未开放")

    with col2:
        if st.button("📱 绑定手机", use_container_width=True):
            st.info("手机绑定功能暂未开放")

    # 保存设置
    st.markdown("---")
    if st.button("💾 保存设置", type="primary", use_container_width=True):
        # 这里应该调用保存设置的API
        st.success("✅ 设置保存成功（演示）")

    # 危险区域
    st.markdown("---")
    st.markdown("### ⚠️ 危险操作")

    st.warning("""
    以下操作不可逆，请谨慎操作！
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚪 退出登录", use_container_width=True):
            st.info("退出登录功能暂未开放")

    with col2:
        if st.button("🗑️ 注销账户", use_container_width=True):
            st.error("注销账户功能暂未开放")

def load_user_profile():
    """加载用户资料"""
    with st.spinner("正在加载个人资料..."):
        response = api_client.get("/users/profile")

        if handle_api_response(response, "个人资料加载成功", show_error_detail=False):
            st.session_state.user_profile = response.get("data", {})
        else:
            st.session_state.user_profile = None

if __name__ == "__main__":
    main()