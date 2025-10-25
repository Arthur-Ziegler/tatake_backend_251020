#!/usr/bin/env python3
"""
简单调试用户管理API问题
"""

import sys
sys.path.append('.')

def main():
    print("🔍 调试用户管理API问题...")

    # 检查Pydantic模型
    from src.domains.user.schemas import UpdateProfileRequest, UpdateProfileResponse

    print("1. 检查Pydantic模型:")
    try:
        request_schema = UpdateProfileRequest.model_json_schema()
        print(f"  Request Schema: {request_schema}")

        response_schema = UpdateProfileResponse.model_json_schema()
        print(f"  Response Schema: {response_schema}")
    except Exception as e:
        print(f"  ❌ Schema检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()