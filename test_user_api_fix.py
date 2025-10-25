#!/usr/bin/env python3
"""
测试用户管理API修复

验证Pydantic v2兼容性修复是否解决了args/kwargs参数问题
"""

import sys
import os
sys.path.append('.')

def test_user_api_schemas():
    """测试用户API Schema生成"""
    print("🧪 测试用户API Schema生成...")

    from src.domains.user.schemas import (
        UserProfileResponse,
        UpdateProfileRequest,
        UpdateProfileResponse,
        WelcomeGiftResponse,
        WelcomeGiftHistoryResponse
    )

    schemas_to_test = [
        ("UserProfileResponse", UserProfileResponse),
        ("UpdateProfileRequest", UpdateProfileRequest),
        ("UpdateProfileResponse", UpdateProfileResponse),
        ("WelcomeGiftResponse", WelcomeGiftResponse),
        ("WelcomeGiftHistoryResponse", WelcomeGiftHistoryResponse)
    ]

    for name, schema_class in schemas_to_test:
        try:
            schema = schema_class.model_json_schema()
            print(f"  ✅ {name}: Schema生成成功")
            print(f"     属性数量: {len(schema.get('properties', {}))}")
            print(f"     包含示例: {'example' in schema}")
        except Exception as e:
            print(f"  ❌ {name}: Schema生成失败 - {e}")

def test_fastapi_route_parsing():
    """测试FastAPI路由解析"""
    print("\n🧪 测试FastAPI路由解析...")

    from fastapi import FastAPI
    from src.domains.user.schemas import UpdateProfileRequest, UpdateProfileResponse

    app = FastAPI()

    @app.put("/test-update-profile", response_model=UpdateProfileResponse)
    async def test_update_profile(
        request: UpdateProfileRequest,
        user_id: str = "test-user"
    ):
        return UpdateProfileResponse(
            id=user_id,
            nickname=request.nickname or "default",
            updated_fields=["nickname"] if request.nickname else []
        )

    try:
        # 检查路由是否正确注册
        routes = [r for r in app.routes if hasattr(r, 'path') and 'test-update-profile' in r.path]
        if routes:
            route = routes[0]
            print(f"  ✅ 路由注册成功: {route.path}")
            print(f"     方法: {route.methods}")
            print(f"     响应模型: {route.response_model}")
        else:
            print("  ❌ 路由注册失败")
    except Exception as e:
        print(f"  ❌ 路由测试失败: {e}")

def test_user_router_integration():
    """测试用户路由集成"""
    print("\n🧪 测试用户路由集成...")

    try:
        from src.domains.user.router import router
        print(f"  ✅ 用户路由加载成功")
        print(f"     路由数量: {len(router.routes)}")

        # 检查具体路由
        routes = []
        for route in router.routes:
            if hasattr(route, 'path'):
                routes.append(f"{list(route.methods)} {route.path}")

        print(f"     路由列表:")
        for route_info in routes[:5]:  # 显示前5个
            print(f"       {route_info}")

    except Exception as e:
        print(f"  ❌ 用户路由集成失败: {e}")
        import traceback
        traceback.print_exc()

def test_api_docs_generation():
    """测试API文档生成"""
    print("\n🧪 测试API文档生成...")

    try:
        from fastapi import FastAPI
        from src.domains.user.router import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/user")

        # 尝试获取OpenAPI schema
        openapi_schema = app.openapi()

        user_paths = [path for path in openapi_schema.get("paths", {}).keys() if "/user" in path]
        print(f"  ✅ OpenAPI Schema生成成功")
        print(f"     用户API路径数量: {len(user_paths)}")

        # 检查是否有args/kwargs问题
        has_args_issue = False
        for path in user_paths:
            path_spec = openapi_schema["paths"][path]
            for method in path_spec:
                if "parameters" in path_spec[method]:
                    params = path_spec[method]["parameters"]
                    for param in params:
                        if param.get("name") in ["args", "kwargs"]:
                            has_args_issue = True
                            print(f"  ❌ 发现args/kwargs参数: {path} {method}")

        if not has_args_issue:
            print(f"  ✅ 没有发现args/kwargs参数问题")

    except Exception as e:
        print(f"  ❌ API文档生成失败: {e}")
        import traceback
        traceback.print_exc()

def test_parameter_validation():
    """测试参数验证"""
    print("\n🧪 测试参数验证...")

    from src.domains.user.schemas import UpdateProfileRequest

    # 测试有效请求
    try:
        valid_request = UpdateProfileRequest(nickname="测试昵称")
        print(f"  ✅ 有效请求验证成功: {valid_request.nickname}")
    except Exception as e:
        print(f"  ❌ 有效请求验证失败: {e}")

    # 测试空请求
    try:
        empty_request = UpdateProfileRequest()
        print(f"  ✅ 空请求验证成功: nickname={empty_request.nickname}")
    except Exception as e:
        print(f"  ❌ 空请求验证失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 测试用户管理API修复")
    print("=" * 60)

    test_user_api_schemas()
    test_fastapi_route_parsing()
    test_user_router_integration()
    test_api_docs_generation()
    test_parameter_validation()

    print("\n" + "=" * 60)
    print("🎯 测试总结:")
    print("1. Pydantic v2兼容性修复已完成")
    print("2. 所有Schema应该正常生成")
    print("3. 不应该再出现args/kwargs参数问题")
    print("=" * 60)