#!/usr/bin/env python3
"""
简单测试脚本，用于调试短信验证API的问题
"""

import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_simple():
    """简单测试"""
    try:
        from src.services.external.mock_sms_service import MockSMSService
        from src.services.auth_service import AuthService
        from src.api.dependencies import initialize_dependencies, cleanup_dependencies

        # 初始化依赖
        await initialize_dependencies()

        try:
            # 测试MockSMSService
            print("测试MockSMSService...")
            mock_service = MockSMSService()
            result = mock_service.send_verification_code(
                phone="13812345678",
                verification_type="login"
            )
            print(f"MockSMSService结果: {result}")

            # 测试AuthService
            print("\n测试AuthService...")
            # 这里需要数据库session，我们暂时跳过

        finally:
            await cleanup_dependencies()

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple())