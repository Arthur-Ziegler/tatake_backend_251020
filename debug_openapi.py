#!/usr/bin/env python3
"""
调试OpenAPI生成问题
"""

import sys
import os
sys.path.append('.')

import json

def debug_openapi_generation():
    """调试OpenAPI生成过程"""
    print("🔍 调试OpenAPI生成过程...")

    from fastapi import FastAPI
    from src.domains.user.router import router

    # 创建独立的app
    app = FastAPI(title="Debug App")

    # 手动添加用户路由
    app.include_router(router, prefix="/api/v1")

    # 生成OpenAPI schema
    try:
        openapi_schema = app.openapi()

        print("📋 OpenAPI Schema结构:")
        print(f"  版本: {openapi_schema.get('openapi')}")
        print(f"  信息: {openapi_schema.get('info', {}).get('title')}")

        # 检查路径
        paths = openapi_schema.get("paths", {})
        print(f"\n🛣️ API路径数量: {len(paths)}")

        for path, methods in paths.items():
            print(f"\n路径: {path}")
            for method, spec in methods.items():
                print(f"  方法: {method.upper()}")

                # 检查参数
                if "parameters" in spec:
                    params = spec["parameters"]
                    print(f"  参数数量: {len(params)}")
                    for param in params:
                        param_name = param.get("name", "unknown")
                        param_in = param.get("in", "unknown")
                        param_required = param.get("required", False)
                        print(f"    - {param_name} ({param_in}, required={param_required})")

                        # 检查是否是args/kwargs
                        if param_name in ["args", "kwargs"]:
                            print(f"    ❌ 发现args/kwargs参数!")
                            print(f"       详情: {json.dumps(param, indent=6, ensure_ascii=False)}")

                # 检查请求体
                if "requestBody" in spec:
                    content = spec["requestBody"].get("content", {})
                    print(f"  请求体内容类型: {list(content.keys())}")

                    for content_type, content_spec in content.items():
                        schema_ref = content_spec.get("schema", {}).get("$ref", "")
                        if schema_ref:
                            print(f"    {content_type}: {schema_ref}")

    except Exception as e:
        print(f"❌ OpenAPI生成失败: {e}")
        import traceback
        traceback.print_exc()

def test_individual_route():
    """测试单个路由"""
    print("\n🧪 测试单个路由...")

    from fastapi import FastAPI
    from src.domains.user.schemas import UpdateProfileRequest, UpdateProfileResponse
    from pydantic import BaseModel

    app = FastAPI()

    @app.put("/simple-profile")
    async def simple_update_profile(
        request: UpdateProfileRequest
    ) -> UpdateProfileResponse:
        return UpdateProfileResponse(
            id="test-id",
            nickname=request.nickname or "default",
            updated_fields=["nickname"]
        )

    try:
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        for path, methods in paths.items():
            if "simple-profile" in path:
                print(f"✅ 简单路由: {path}")
                for method, spec in methods.items():
                    print(f"  方法: {method}")
                    if "parameters" in spec:
                        print(f"  参数: {[p.get('name') for p in spec['parameters']]}")
                    else:
                        print(f"  参数: 无")

    except Exception as e:
        print(f"❌ 单个路由测试失败: {e}")

def test_dependency_injection():
    """测试依赖注入问题"""
    print("\n🧪 测试依赖注入...")

    from fastapi import FastAPI, Depends
    from sqlmodel import Session
    from typing import Annotated

    # 模拟依赖
    def get_current_user():
        return "test-user"

    def get_db_session():
        return Session()

    # 测试类型注解
    SessionDep = Annotated[Session, Depends(get_db_session)]

    app = FastAPI()

    @app.get("/test-deps")
    async def test_deps(
        user_id: str = Depends(get_current_user),
        session: Session = Depends(get_db_session)
    ):
        return {"user_id": user_id}

    try:
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        for path, methods in paths.items():
            if "test-deps" in path:
                for method, spec in methods.items():
                    if "parameters" in spec:
                        params = spec["parameters"]
                        print(f"依赖注入参数: {[p.get('name') for p in params]}")
                        for param in params:
                            if param.get('name') in ['args', 'kwargs']:
                                print(f"❌ 发现args/kwargs: {param}")

    except Exception as e:
        print(f"❌ 依赖注入测试失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 调试OpenAPI生成问题")
    print("=" * 60)

    debug_openapi_generation()
    test_individual_route()
    test_dependency_injection()

    print("\n" + "=" * 60)
    print("🎯 调试结论:")
    print("1. 确定args/kwargs参数的来源")
    print("2. 检查是否是依赖注入问题")
    print("3. 验证修复效果")
    print("=" * 60)