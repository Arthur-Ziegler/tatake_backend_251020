"""
聊天工具函数

提供session_id生成等工具功能。

设计原则：
1. 简单可靠：生成确定格式的session_id
2. 高性能：避免复杂的随机数生成
3. 时间有序：session_id按时间排序
4. 冲突避免：通过随机数避免重复

作者：TaKeKe团队
版本：1.0.0
"""

import random
from datetime import datetime, timezone


def generate_session_id() -> str:
    """
    生成会话ID

    格式：YYYYMMDDHHMMSS_XXXX
    - 前缀：当前时间戳（精确到秒）
    - 后缀：4位随机十六进制数

    Returns:
        str: 会话ID，例如：20251101051704_4a42
    """
    # 获取当前UTC时间
    now = datetime.now(timezone.utc)

    # 格式化时间戳：YYYYMMDDHHMMSS
    timestamp = now.strftime("%Y%m%d%H%M%S")

    # 生成4位随机十六进制数
    random_suffix = f"{random.randint(0, 0xFFFF):04x}"

    # 组合成session_id
    session_id = f"{timestamp}_{random_suffix}"

    return session_id


def generate_default_title() -> str:
    """
    生成默认会话标题

    格式：会话YYYYMMDDHHMMSS

    Returns:
        str: 默认标题，例如：会话20251101051704
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M%S")
    return f"会话{timestamp}"