#!/usr/bin/env python3
"""
最小复现args/kwargs问题
"""

import sys
sys.path.append('.')

def minimal_reproduction():
    """最小复现问题"""
    print("🔍 最小复现args/kwargs问题...")

    from fastapi import FastAPI
    from pydantic import BaseModel, Field
    from typing import Optional

    # 创建最基本的模型
    class TestRequest(BaseModel):
        name: Optional[str] = Field(None, description="名称")

    class TestResponse(BaseModel):
        message: str
        name: Optional[str] = None

    app = FastAPI()

    @app.post("/test", response_model=TestResponse)
    async def test_endpoint(
        request: TestRequest
    ) -> TestResponse:
        return TestResponse(
            message="success",
            name=request.name
        )

    # 检查OpenAPI schema
    try:
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        for path, methods in paths.items():
            if "test" in path:
                for method, spec in methods.items():
                    print(f"路径: {path}")
                    print(f"方法: {method.upper()}")
                    if "parameters" in spec:
                        params = spec["parameters"]
                        print(f"参数: {[p.get('name') for p in params]}")
                        for param in params:
                            if param.get('name') in ['args', 'kwargs']:
                                print(f"❌ 发现args/kwargs: {param}")
                    else:
                        print("参数: 无")
                    break
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_with_dependencies():
    """测试带依赖的版本"""
    print("\n🧪 测试带依赖的版本...")

    from fastapi import FastAPI, Depends
    from pydantic import BaseModel, Field
    from typing import Optional, Annotated

    class TestRequest(BaseModel):
        name: Optional[str] = Field(None, description="名称")

    class TestResponse(BaseModel):
        message: str
        name: Optional[str] = None

    # 模拟依赖
    def get_current_user():
        return "test-user"

    def get_session():
        return "mock-session"

    # 模拟SessionDep
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from sqlmodel import Session
    else:
        Session = object

    SessionDep = Annotated[Session, Depends(get_session)]

    app = FastAPI()

    @app.post("/test-with-deps", response_model=TestResponse)
    async def test_with_deps(
        request: TestRequest,
        user_id: str = Depends(get_current_user),
        session: Session = Depends(get_session)
    ) -> TestResponse:
        return TestResponse(
            message="success",
            name=request.name
        )

    # 检查OpenAPI schema
    try:
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        for path, methods in paths.items():
            if "test-with-deps" in path:
                for method, spec in methods.items():
                    print(f"路径: {path}")
                    print(f"方法: {method.upper()}")
                    if "parameters" in spec:
                        params = spec["parameters"]
                        print(f"参数: {[p.get('name') for p in params]}")
                        for param in params:
                            if param.get('name') in ['args', 'kwargs']:
                                print(f"❌ 发现args/kwargs: {param}")
                    else:
                        print("参数: 无")
                    break
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_actual_user_router():
    """测试实际的用户路由"""
    print("\n🧪 测试实际的用户路由...")

    from src.domains.user.router import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    try:
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        user_paths = {k: v for k, v in paths.items() if "/user" in k}

        print(f"用户路径数量: {len(user_paths)}")

        for path, methods in user_paths.items():
            print(f"\n路径: {path}")
            for method, spec in methods.items():
                print(f"  方法: {method.upper()}")
                if "parameters" in spec:
                    params = spec["parameters"]
                    print(f"  参数数量: {len(params)}")
                    for param in params:
                        param_name = param.get("name", "unknown")
                        param_required = param.get("required", False)
                        print(f"    - {param_name} (required={param_required})")

                        if param_name in ['args', 'kwargs']:
                            print(f"    ❌ 发现args/kwargs参数!")
                            print(f"       详情: {param}")

    except Exception as e:
        print(f"❌ 用户路由测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 最小复现args/kwargs问题")
    print("=" * 60)

    minimal_reproduction()
    test_with_dependencies()
    test_actual_user_router()

    print("\n" + "=" * 60)
    print("🎯 复现结论:")
    print("1. 确定args/kwargs是否在所有情况下出现")
    print("2. 找到问题的确切触发条件")
    print("3. 为修复提供指导")
    print("=" * 60)