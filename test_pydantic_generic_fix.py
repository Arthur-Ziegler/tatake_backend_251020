#!/usr/bin/env python3
"""
测试Pydantic泛型修复
"""

import sys
sys.path.append('.')

def test_pydantic_v2_generic():
    """测试Pydantic v2泛型兼容性"""
    print("🧪 测试Pydantic v2泛型兼容性...")

    # 测试原始定义
    from typing import Generic, TypeVar
    from pydantic import BaseModel, Field

    T = TypeVar('T')

    class OriginalUnifiedResponse(BaseModel, Generic[T]):
        code: int
        data: Optional[T]
        message: str

    # 测试Pydantic v2方式
    from typing import Annotated

    class V2UnifiedResponse(BaseModel):
        code: int
        data: Optional[dict]
        message: str

    print("✅ 泛型模型创建成功")

    # 测试参数化
    try:
        # 原始方式
        original_response = OriginalUnifiedResponse[int](
            code=200,
            data=42,
            message="success"
        )
        print(f"✅ 原始泛型响应: {original_response}")

        # 使用类型注解方式
        annotated_response = V2UnifiedResponse(
            code=200,
            data={"value": 42},
            message="success"
        )
        print(f"✅ V2响应: {annotated_response}")

    except Exception as e:
        print(f"❌ 泛型测试失败: {e}")

def test_fastapi_with_pydantic_v2():
    """测试FastAPI与Pydantic v2泛型"""
    print("\n🧪 测试FastAPI与Pydantic v2泛型...")

    from fastapi import FastAPI
    from typing import Optional
    from pydantic import BaseModel, Field

    # 方案1: 使用Pydantic v2兼容的泛型
    from typing import Generic, TypeVar

    T = TypeVar('T')

    class CompatibleUnifiedResponse(BaseModel, Generic[T]):
        code: int
        data: Optional[T]
        message: str

    class TestResponse(BaseModel):
        value: int

    app = FastAPI()

    @app.get("/test-compatible")
    async def test_compatible() -> CompatibleUnifiedResponse[TestResponse]:
        return CompatibleUnifiedResponse(
            code=200,
            data=TestResponse(value=42),
            message="success"
        )

    # 方案2: 不使用泛型
    class SimpleResponse(BaseModel):
        code: int
        data: dict
        message: str

    @app.get("/test-simple")
    async def test_simple() -> SimpleResponse:
        return SimpleResponse(
            code=200,
            data={"value": 42},
            message="success"
        )

    try:
        # 检查OpenAPI schema
        schema = app.openapi()
        paths = schema.get("paths", {})

        print("OpenAPI路径分析:")
        for path, methods in paths.items():
            print(f"路径: {path}")
            for method, spec in methods.items():
                print(f"  方法: {method.upper()}")
                if "parameters" in spec:
                    params = spec["parameters"]
                    print(f"  参数: {[p.get('name') for p in params]}")
                    args_kwargs = [p for p in params if p.get('name') in ['args', 'kwargs']]
                    if args_kwargs:
                        print(f"  ❌ 发现args/kwargs: {len(args_kwargs)}个")
                        for param in args_kwargs:
                            print(f"    详情: {param}")
                else:
                    print(f"  参数: 无")

    except Exception as e:
        print(f"❌ FastAPI测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_direct_user_route_fix():
    """直接测试用户路由修复"""
    print("\n🧪 直接测试用户路由修复...")

    # 尝试创建修复版本的用户路由
    from fastapi import FastAPI, Depends
    from pydantic import BaseModel, Field
    from typing import Optional
    from uuid import UUID

    def get_current_user_id() -> UUID:
        return UUID('test-id')

    def get_db_session():
        class MockSession:
            pass
        yield MockSession()

    # 使用具体的响应模型而不是泛型
    class UserProfileResponse(BaseModel):
        id: str
        nickname: str

    class UpdateProfileRequest(BaseModel):
        nickname: Optional[str] = None

    class UpdateProfileResponse(BaseModel):
        id: str
        nickname: str
        updated_fields: list[str]

    class Result(BaseModel):
        code: int
        data: Optional[dict]
        message: str

    app = FastAPI()

    @app.get("/profile")
    async def get_user_profile(
        user_id: UUID = Depends(get_current_user_id),
        session: MockSession = Depends(get_db_session)
    ) -> Result:
        return Result(
            code=200,
            data={"id": str(user_id), "nickname": "test"},
            message="success"
        )

    @app.put("/profile")
    async def update_user_profile(
        request: UpdateProfileRequest,
        user_id: UUID = Depends(get_current_user_id),
        session: MockSession = Depends(get_db_session)
    ) -> Result:
        return Result(
            code=200,
            data={"id": str(user_id), "nickname": request.nickname},
            message="success"
        )

    try:
        schema = app.openapi()
        paths = schema.get("paths", {})

        print("修复版本路由分析:")
        for path, methods in paths.items():
            print(f"路径: {path}")
            for method, spec in methods.items():
                print(f"  方法: {method.upper()}")
                if "parameters" in spec:
                    params = spec["parameters"]
                    print(f"  参数: {[p.get('name') for p in params]}")
                    args_kwargs = [p for p in params if p.get('name') in ['args', 'kwargs']]
                    if args_kwargs:
                        print(f"  ❌ 仍有args/kwargs: {len(args_kwargs)}个")
                    else:
                        print(f"  ✅ 修复成功！无args/kwargs")
                else:
                    print(f"  ✅ 修复成功！无参数")

    except Exception as e:
        print(f"❌ 修复测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 测试Pydantic泛型修复")
    print("=" * 60)

    test_pydantic_v2_generic()
    test_fastapi_with_pydantic_v2()
    test_direct_user_route_fix()

    print("\n" + "=" * 60)
    print("🎯 测试结论:")
    print("1. 确定泛型是否是问题的根源")
    print("2. 提供可行的修复方案")
    print("3. 验证修复效果")
    print("=" * 60)