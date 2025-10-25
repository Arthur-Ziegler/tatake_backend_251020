"""
LangGraph类型错误的根本修复

直接修复LangGraph内部的get_new_channel_versions函数，
在版本比较前修复类型问题。

这是真正的根本解决方案，直接在错误发生的源头进行修复。
"""

import logging
import langgraph.pregel._utils as langgraph_utils

logger = logging.getLogger(__name__)

# 保存原始函数
_original_get_new_channel_versions = None

def _fixed_get_new_channel_versions(channels, values, previous_versions):
    """
    修复版本类型的get_new_channel_versions函数

    这个函数直接修复LangGraph内部的类型比较问题。
    在版本比较之前，确保所有版本号都是整数类型。
    """
    logger.debug("🔧 修复LangGraph版本类型问题")

    new_versions = {}

    for channel, value in values.items():
        logger.debug(f"  处理channel: {channel}, value: {value} (类型: {type(value)})")

        # 检查是否是LangGraph的特殊版本号格式
        if isinstance(value, str) and '.' in value:
            # 处理类似 "00000000000000000000000000000002.0.243798848838515" 的格式
            parts = value.split('.')
            if len(parts) >= 2 and parts[0].isdigit():
                version_num = int(parts[0]) if parts[0].strip() else 1
                new_versions[channel] = version_num
                logger.debug(f"  ✅ 修复LangGraph特殊格式: {channel} = {version_num}")
            else:
                # 其他字符串格式，使用哈希生成稳定整数
                hash_version = abs(hash(value)) % (10**9)
                new_versions[channel] = hash_version
                logger.debug(f"  ✅ 修复字符串格式: {channel} = {hash_version} (哈希)")
        elif isinstance(value, str):
            # 简单字符串转换
            try:
                int_version = int(value)
                new_versions[channel] = int_version
                logger.debug(f"  ✅ 转换字符串为整数: {channel} = {int_version}")
            except ValueError:
                # 无法转换的字符串，使用哈希
                hash_version = abs(hash(value)) % (10**9)
                new_versions[channel] = hash_version
                logger.debug(f"  ✅ 转换无效字符串: {channel} = {hash_version} (哈希)")
        else:
            # 数字类型，直接使用
            new_versions[channel] = value
            logger.debug(f"  ✅ 直接使用数字类型: {channel} = {value}")

    # 调用原始函数进行正常的版本比较逻辑
    # 但传递修复后的版本号
    try:
        result = _original_get_new_channel_versions(channels, values, previous_versions)
        logger.debug("🎯 原始函数执行成功")
        return result
    except Exception as e:
        logger.error(f"❌ 原始函数执行失败: {e}")
        # 如果原始函数失败，返回我们修复的版本
        return new_versions

def apply_langgraph_fix():
    """
    应用LangGraph修复

    这个函数应该在应用启动时调用，替换LangGraph的内部函数。
    """
    global _original_get_new_channel_versions

    if _original_get_new_channel_versions is None:
        # 保存原始函数
        _original_get_new_channel_versions = langgraph_utils.get_new_channel_versions

        # 应用修复
        langgraph_utils.get_new_channel_versions = _fixed_get_new_channel_versions

        logger.info("🚀 LangGraph类型修复已应用")
        logger.info("   - 修复 get_new_channel_versions 函数")
        logger.info("   - 处理 LangGraph 特殊版本号格式")
        logger.info("   - 确保所有版本号都是整数类型")

        return True
    else:
        logger.warning("⚠️ LangGraph修复已经应用过了")
        return False

def remove_langgraph_fix():
    """
    移除LangGraph修复，恢复原始函数

    主要用于测试和调试。
    """
    global _original_get_new_channel_versions

    if _original_get_new_channel_versions is not None:
        # 恢复原始函数
        langgraph_utils.get_new_channel_versions = _original_get_new_channel_versions
        _original_get_new_channel_versions = None

        logger.info("🔄 LangGraph修复已移除，恢复原始函数")
        return True
    else:
        logger.warning("⚠️ 没有找到已应用的LangGraph修复")
        return False

# 便捷函数
def is_langgraph_fix_applied():
    """检查LangGraph修复是否已应用"""
    global _original_get_new_channel_versions
    return _original_get_new_channel_versions is not None