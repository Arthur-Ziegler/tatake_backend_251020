"""
Streamlit 测试面板 - 错误处理组件

这个文件提供：
1. 统一的错误显示界面
2. API 响应错误分析
3. 用户友好的错误提示

作者: Claude Code Assistant
创建时间: 2025-10-25
"""

import streamlit as st
from typing import Optional, Dict, Any


def show_error(response: Optional[Dict[str, Any]], title: str = "❌ 请求失败", show_button: bool = True):
    """
    显示 API 错误响应

    Args:
        response: API 响应数据
        title: 错误标题
        show_button: 是否显示查看详情按钮（在表单内设为False避免冲突）
    """
    if not response:
        st.error("❌ 请求失败：没有响应数据")
        return

    code = response.get("code", 0)
    message = response.get("message", "未知错误")

    # 主要错误提示
    st.error(f"{title} (错误码: {code})")
    st.warning(f"📝 错误信息: {message}")

    # 根据错误码提供更具体的提示
    show_error_suggestion(code)

    # 显示完整响应 - 只有允许显示按钮时才显示
    if show_button:
        if st.button("🔍 查看完整响应", key=f"show_error_detail_{code}"):
            with st.expander("📄 完整错误响应", expanded=True):
                st.json(response)
    else:
        # 在表单内，直接显示响应内容，不使用按钮
        with st.expander("📄 完整错误响应", expanded=False):
            st.json(response)


def show_error_suggestion(code: int):
    """
    根据错误码提供解决建议

    Args:
        code: HTTP 状态码或业务错误码
    """
    suggestions = {
        400: {
            "title": "🔧 请求参数错误",
            "tips": [
                "检查请求参数是否正确",
                "确认必填字段都已提供",
                "验证数据格式是否符合要求"
            ]
        },
        401: {
            "title": "🔐 认证失败",
            "tips": [
                "Token 可能已过期，请刷新 Token",
                "如果未登录，请先进行游客初始化",
                "检查 Token 格式是否正确"
            ]
        },
        403: {
            "title": "🚫 权限不足",
            "tips": [
                "当前用户可能没有执行此操作的权限",
                "某些功能需要注册用户才能使用",
                "联系管理员获取相应权限"
            ]
        },
        404: {
            "title": "🔍 资源不存在",
            "tips": [
                "请求的资源可能已被删除",
                "检查 URL 路径是否正确",
                "确认资源 ID 是否有效"
            ]
        },
        429: {
            "title": "⏰ 请求频率限制",
            "tips": [
                "请求过于频繁，请稍后重试",
                "避免短时间内重复操作",
                "等待一段时间后再试"
            ]
        },
        500: {
            "title": "💥 服务器内部错误",
            "tips": [
                "服务器出现异常，请稍后重试",
                "如果问题持续存在，请联系技术支持",
                "可以尝试刷新页面重新操作"
            ]
        }
    }

    if code in suggestions:
        suggestion = suggestions[code]
        st.info(f"**{suggestion['title']}**")
        for tip in suggestion['tips']:
            st.write(f"• {tip}")
    else:
        st.info("💡 **建议**: 请检查网络连接或稍后重试")


def show_success(message: str = "✅ 操作成功"):
    """
    显示成功消息

    Args:
        message: 成功消息
    """
    st.success(message)


def show_warning(message: str):
    """
    显示警告消息

    Args:
        message: 警告消息
    """
    st.warning(f"⚠️ {message}")


def show_info(message: str):
    """
    显示信息消息

    Args:
        message: 信息消息
    """
    st.info(f"ℹ️ {message}")


def handle_api_response(response: Optional[Dict[str, Any]], success_message: str = "操作成功", show_error_detail: bool = False):
    """
    统一处理 API 响应

    Args:
        response: API 响应数据
        success_message: 成功时的消息
        show_error_detail: 是否显示错误详情按钮

    Returns:
        bool: 操作是否成功
    """
    if not response:
        show_error(None, show_button=show_error_detail)
        return False

    code = response.get("code", 0)

    if code in [200, 201]:  # 接受200和201状态码
        show_success(success_message)
        return True
    else:
        show_error(response, show_button=show_error_detail)
        return False


def create_error_alert(error_type: str, message: str, details: Optional[str] = None):
    """
    创建自定义错误警告

    Args:
        error_type: 错误类型
        message: 错误消息
        details: 错误详情
    """
    st.error(f"🚨 {error_type}: {message}")

    if details:
        with st.expander("📋 查看详细信息"):
            st.code(details)


def validate_response_data(response: Optional[Dict[str, Any]], required_fields: list) -> bool:
    """
    验证响应数据是否包含必需字段

    Args:
        response: API 响应数据
        required_fields: 必需字段列表

    Returns:
        bool: 验证是否通过
    """
    if not response:
        show_error(None, "响应数据为空")
        return False

    data = response.get("data", {})
    missing_fields = []

    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)

    if missing_fields:
        st.error(f"❌ 响应数据缺少必需字段: {', '.join(missing_fields)}")
        return False

    return True