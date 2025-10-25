#!/usr/bin/env python3
"""
实时调试Chat API错误，捕获完整的错误堆栈
"""

import logging
import traceback
import sys
from pathlib import Path

# 设置详细的日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chat_error_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 设置langgraph相关日志也为DEBUG
logging.getLogger('langgraph').setLevel(logging.DEBUG)
logging.getLogger('src.domains.chat').setLevel(logging.DEBUG)

def monkey_patch_chat_service():
    """给ChatService添加猴子补丁来捕获错误"""

    from src.domains.chat.service_separated import SeparatedChatService

    # 保存原始方法
    original_send_message = SeparatedChatService.send_message

    def debug_send_message(self, user_id: str, session_id: str, message: str):
        """带调试的send_message方法"""
        logger.info(f"🚀 开始发送消息: user_id={user_id}, session_id={session_id}, message='{message}'")

        try:
            result = original_send_message(self, user_id, session_id, message)
            logger.info(f"✅ 消息发送成功: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ 消息发送失败: {e}")
            logger.error(f"🔍 完整错误堆栈:\n{traceback.format_exc()}")

            # 检查是否是类型比较错误
            if "'>' not supported between instances of 'str' and 'int'" in str(e):
                logger.error("🚨 确认是类型比较错误！")

                # 尝试获取更多信息
                logger.error("🔧 检查checkpointer状态...")
                try:
                    if hasattr(self, 'db_manager'):
                        logger.info("✅ db_manager存在")
                    else:
                        logger.error("❌ db_manager不存在")

                except Exception as inner_e:
                    logger.error(f"❌ 检查db_manager时出错: {inner_e}")

            raise

    def debug_create_type_safe_checkpointer(self, base_checkpointer):
        """带调试的TypeSafeCheckpointer创建方法"""
        logger.debug(f"🔧 创建TypeSafeCheckpointer包装器")
        logger.debug(f"📋 Base checkpointer类型: {type(base_checkpointer)}")

        safe_checkpointer = original_create_type_safe_checkpointer(self, base_checkpointer)

        logger.debug(f"✅ TypeSafeCheckpointer创建成功: {type(safe_checkpointer)}")

        return safe_checkpointer

    # 应用猴子补丁
    SeparatedChatService.send_message = debug_send_message
    logger.info("🔧 SeparatedChatService猴子补丁已应用")

if __name__ == "__main__":
    print("🧪 实时调试Chat API错误")
    print("=" * 50)

    # 应用猴子补丁
    monkey_patch_chat_service()

    print("🔧 调试模式已启用")
    print("💡 现在可以测试Chat API，所有错误将被详细记录")
    print("📝 日志将保存到 chat_error_debug.log")
    print()
    print("🚀 启动测试服务器...")

    # 启动FastAPI服务器
    import uvicorn
    from src.api.main import app

    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="debug")