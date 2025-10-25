#!/usr/bin/env python3
"""
独立调试User端点问题
"""

import sys
import os

# 设置最小路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_user_router_isolated():
    """独立测试User路由"""
    print("🔍 创建完全独立的User路由测试...")

    # 创建最小的User路由副本
    from fastapi import APIRouter, Depends
    from uuid import UUID
    from typing import Dict, Any

    # 模拟依赖
    def get_current_user_id() -> UUID:
        return UUID('12345678-1234-5678-9abc-123456789abc')

    def get_db_session():
        class MockSession:
            pass
        return MockSession()

    # 创建全新的路由
    test_router = APIRouter(prefix="/user", tags=["用户测试"])

    @test_router.get("/profile", summary="获取用户信息（测试版）")
    async def test_get_user_profile(
        user_id: UUID = Depends(get_current_user_id),
        session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """测试版本 - 不使用任何泛型"""
        return {
            "code": 200,
            "data": {"id": str(user_id), "nickname": "测试用户"},
            "message": "success"
        }

    @test_router.post("/welcome-gift/claim", summary="领取欢迎礼包（测试版）")
    async def test_claim_welcome_gift(
        user_id: UUID = Depends(get_current_user_id),
        session = Depends(get_db_session)
    ) -> Dict[str, Any]:
        """测试版本 - 不使用任何泛型"""
        return {
            "code": 200,
            "data": {"points_granted": 1000},
            "message": "success"
        }

    # 测试路由
    from fastapi import FastAPI
    test_app = FastAPI()
    test_app.include_router(test_router, prefix="/api/v1")

    # 生成OpenAPI
    try:
        openapi_schema = test_app.openapi()
        paths = openapi_schema.get("paths", {})

        print("📊 测试路由OpenAPI检查:")
        all_clean = True

        for path, methods in paths.items():
            if "/user/" in path:
                for method, spec in methods.items():
                    if method.lower() in ['get', 'post', 'put', 'delete']:
                        parameters = spec.get("parameters", [])
                        args_kwargs = [p for p in parameters if p.get("name") in ["args", "kwargs"]]

                        if args_kwargs:
                            print(f"  ❌ {method.upper()} {path}: {[p.get('name') for p in args_kwargs]}")
                            all_clean = False
                        else:
                            print(f"  ✅ {method.upper()} {path}: 无问题参数")

        if all_clean:
            print("\n🎉 独立测试通过! 问题不在FastAPI本身")
        else:
            print("\n❌ 独立测试也失败! FastAPI本身有问题")

        return all_clean

    except Exception as e:
        print(f"❌ 独立测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_original_user_router():
    """测试原始User路由"""
    print("\n🔍 测试原始User路由...")

    try:
        # 强制清除所有模块缓存
        modules_to_clear = [k for k in list(sys.modules.keys()) if 'tatake' in k or 'src' in k]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        # 重新导入
        from fastapi import FastAPI
        from src.domains.user.router import router

        # 创建测试应用
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1")

        # 检查导入的类
        from src.domains.user.schemas import UnifiedResponse as UserUnifiedResponse
        print(f"📋 User UnifiedResponse类型: {UserUnifiedResponse}")
        print(f"   是否为Generic: {hasattr(UserUnifiedResponse, '__parameters__')}")

        # 生成OpenAPI
        openapi_schema = test_app.openapi()
        paths = openapi_schema.get("paths", {})

        print("📊 原始路由OpenAPI检查:")
        problem_count = 0

        for path, methods in paths.items():
            if "/user/" in path:
                for method, spec in methods.items():
                    if method.lower() in ['get', 'post', 'put', 'delete']:
                        parameters = spec.get("parameters", [])
                        args_kwargs = [p for p in parameters if p.get("name") in ["args", "kwargs"]]

                        if args_kwargs:
                            print(f"  ❌ {method.upper()} {path}: {[p.get('name') for p in args_kwargs]}")
                            problem_count += 1
                        else:
                            print(f"  ✅ {method.upper()} {path}: 无问题参数")

        if problem_count == 0:
            print("\n🎉 原始路由也通过了!")
        else:
            print(f"\n❌ 原始路由有 {problem_count} 个问题")

        return problem_count == 0

    except Exception as e:
        print(f"❌ 原始路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 User端点独立调试")
    print("=" * 60)

    # 先测试独立路由
    independent_ok = test_user_router_isolated()

    # 再测试原始路由
    original_ok = test_original_user_router()

    print("\n" + "=" * 60)
    print("📋 调试结论:")
    print(f"  独立测试: {'✅ 通过' if independent_ok else '❌ 失败'}")
    print(f"  原始测试: {'✅ 通过' if original_ok else '❌ 失败'}")

    if independent_ok and not original_ok:
        print("  结论: User路由代码中仍有问题")
    elif not independent_ok and not original_ok:
        print("  结论: FastAPI或环境有根本问题")
    elif independent_ok and original_ok:
        print("  结论: 问题已解决!")
    print("=" * 60)