#!/usr/bin/env python3
"""
直接测试用户API当前状态的脚本

这个脚本直接调用User路由函数，检查参数解析问题是否仍然存在。
"""

import os
import sys
import logging
import inspect
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_user_route_signatures():
    """分析User路由的函数签名"""
    try:
        print("🔍 分析User路由函数签名...")

        from src.domains.user.router import router
        from fastapi.routing import APIRoute

        for route in router.routes:
            if isinstance(route, APIRoute):
                print(f"\n📋 路由: {list(route.methods)} {route.path}")
                print(f"   函数: {route.endpoint.__name__}")

                # 分析函数签名
                sig = inspect.signature(route.endpoint)
                print(f"   参数:")
                for param_name, param in sig.parameters.items():
                    print(f"     {param_name}: {param.annotation} = {param.default}")

                # 分析依赖
                if hasattr(route, 'dependant') and route.dependant:
                    print(f"   依赖参数:")
                    for dep_param in route.dependant.call_params:
                        print(f"     {dep_param.name}: {dep_param.type_}")

        print("\n" + "="*60)

    except Exception as e:
        print(f"❌ 路由签名分析失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

def test_dependency_injection():
    """测试依赖注入的实际工作情况"""
    try:
        print("🔍 测试依赖注入...")

        from src.domains.user.router import get_user_profile
        from src.database import get_db_session
        from src.api.dependencies import get_current_user_id
        from fastapi import Depends
        from uuid import uuid4
        from typing import Annotated

        print("✅ 成功导入路由函数和依赖")

        # 检查函数签名
        sig = inspect.signature(get_user_profile)
        print(f"get_user_profile 签名: {sig}")

        # 尝试模拟依赖注入
        print("\n📋 模拟依赖注入调用...")

        # 创建模拟的session
        session = None  # 这里应该创建真实的session，但为了测试先跳过
        user_id = uuid4()

        # 尝试直接调用（这应该会失败，但可以看到错误信息）
        try:
            # 如果函数使用正确的Annotated语法，这应该可以工作
            result = get_user_profile(session, user_id)
            print("✅ 直接调用成功")
        except Exception as e:
            print(f"❌ 直接调用失败: {type(e).__name__}: {e}")
            print("这可能说明依赖注入有问题")

    except Exception as e:
        print(f"❌ 依赖注入测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

def check_import_versions():
    """检查导入的版本和类型"""
    try:
        print("🔍 检查Python和包版本...")

        import fastapi
        import pydantic
        import sqlmodel
        import typing

        print(f"FastAPI版本: {fastapi.__version__}")
        print(f"Pydantic版本: {pydantic.__version__}")
        print(f"SQLModel版本: {sqlmodel.__version__}")
        print(f"Python版本: {sys.version}")

        # 检查Annotated是否可用
        try:
            from typing import Annotated
            print("✅ typing.Annotated 可用")
        except ImportError:
            print("❌ typing.Annotated 不可用")
            try:
                from typing_extensions import Annotated
                print("✅ typing_extensions.Annotated 可用")
            except ImportError:
                print("❌ Annotated 完全不可用 - 这可能是问题所在!")

    except Exception as e:
        print(f"❌ 版本检查失败: {type(e).__name__}: {e}")

def test_openapi_generation():
    """测试OpenAPI文档生成"""
    try:
        print("🔍 测试OpenAPI文档生成...")

        from src.domains.user.router import router
        from fastapi import FastAPI

        # 创建临时FastAPI应用
        app = FastAPI()
        app.include_router(router)

        # 生成OpenAPI schema
        openapi_schema = app.openapi()

        print("✅ OpenAPI schema 生成成功")

        # 检查用户相关的路径
        user_paths = {k: v for k, v in openapi_schema["paths"].items() if "user" in k}

        print(f"\n📋 发现 {len(user_paths)} 个用户相关路径:")
        for path, path_item in user_paths.items():
            for method, operation in path_item.items():
                if method.upper() != "PARAMETERS":
                    print(f"  {method.upper()} {path}")

                    # 检查参数
                    if "parameters" in operation:
                        print(f"    参数: {len(operation['parameters'])} 个")
                        for param in operation["parameters"]:
                            param_name = param.get("name", "unknown")
                            param_in = param.get("in", "unknown")
                            required = param.get("required", False)
                            print(f"      - {param_name} (in: {param_in}, required: {required})")
                    else:
                        print("    参数: 无")

                    # 检查是否有args/kwargs问题
                    if "requestBody" in operation:
                        content = operation["requestBody"].get("content", {})
                        for content_type, content_info in content.items():
                            schema = content_info.get("schema", {})
                            if "properties" in schema:
                                for prop_name, prop_info in schema["properties"].items():
                                    if prop_name in ["args", "kwargs"]:
                                        print(f"    🚨 发现问题参数: {prop_name}")

        return openapi_schema

    except Exception as e:
        print(f"❌ OpenAPI生成测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 开始用户API当前状态分析...")
    print("=" * 60)

    # 测试1: 检查版本
    print("\n📋 测试1: 检查Python和包版本")
    check_import_versions()

    print("\n" + "-" * 40)

    # 测试2: 分析路由签名
    print("\n📋 测试2: 分析路由函数签名")
    analyze_user_route_signatures()

    print("\n" + "-" * 40)

    # 测试3: 测试依赖注入
    print("\n📋 测试3: 测试依赖注入")
    test_dependency_injection()

    print("\n" + "-" * 40)

    # 测试4: 测试OpenAPI生成
    print("\n📋 测试4: 测试OpenAPI文档生成")
    test_openapi_generation()

    print("\n" + "=" * 60)
    print("🏁 分析完成")