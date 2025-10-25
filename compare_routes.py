#!/usr/bin/env python3
"""
对比工作路由和问题路由的差异
"""

import sys
sys.path.append('.')

def compare_working_vs_problematic():
    """对比工作和有问题的路由"""
    print("🔍 对比工作和有问题的路由...")

    from fastapi import FastAPI, Depends
    from pydantic import BaseModel, Field
    from typing import Optional, Annotated
    from uuid import UUID

    # 复制用户路由的导入和定义
    def get_current_user_id() -> UUID:
        return UUID('12345678-1234-5678-9abc-123456789abc')

    from sqlmodel import Session
    def get_db_session():
        class MockSession:
            pass
        yield MockSession()

    SessionDep = Annotated[Session, Depends(get_db_session)]

    class UnifiedResponse(BaseModel):
        code: int
        data: Optional[dict]
        message: str

    class UserProfileResponse(BaseModel):
        id: str
        nickname: str

    # 创建问题的路由 - 完全复制用户路由的逻辑
    problematic_app = FastAPI()

    @problematic_app.get("/profile", response_model=UnifiedResponse[UserProfileResponse])
    async def problematic_get_user_profile(
        user_id: UUID = Depends(get_current_user_id),
        session: Session = Depends(SessionDep)
    ) -> UnifiedResponse[UserProfileResponse]:
        return UnifiedResponse(
            code=200,
            data={"id": str(user_id), "nickname": "test"},
            message="success"
        )

    # 创建工作正常的路由 - 简化版本
    working_app = FastAPI()

    @working_app.get("/profile", response_model=dict)
    async def working_get_user_profile() -> dict:
        return {"id": "test", "nickname": "test"}

    # 检查问题路由
    print("🔍 问题路由分析:")
    problematic_schema = problematic_app.openapi()
    problematic_paths = problematic_schema.get("paths", {})

    for path, methods in problematic_paths.items():
        print(f"路径: {path}")
        for method, spec in methods.items():
            print(f"  方法: {method.upper()}")
            if "parameters" in spec:
                params = spec["parameters"]
                print(f"  参数数量: {len(params)}")
                for param in params:
                    param_name = param.get("name", "unknown")
                    print(f"    - {param_name}")
                    if param_name in ['args', 'kwargs']:
                        print(f"    ❌ 发现args/kwargs!")
            else:
                print("  参数: 无")

    # 检查工作路由
    print("\n✅ 工作路由分析:")
    working_schema = working_app.openapi()
    working_paths = working_schema.get("paths", {})

    for path, methods in working_paths.items():
        print(f"路径: {path}")
        for method, spec in methods.items():
            print(f"  方法: {method.upper()}")
            if "parameters" in spec:
                params = spec["parameters"]
                print(f"  参数: {[p.get('name') for p in params]}")
            else:
                print("  参数: 无")

def test_generic_response():
    """测试泛型响应是否导致问题"""
    print("\n🧪 测试泛型响应是否导致问题...")

    from fastapi import FastAPI
    from pydantic import BaseModel, Field
    from typing import Generic, TypeVar, Optional
    from uuid import UUID

    def get_current_user_id() -> UUID:
        return UUID('test-id')

    def get_db_session():
        class MockSession:
            pass
        yield MockSession()

    SessionDep = Annotated[MockSession, Depends(get_db_session)]

    T = TypeVar('T')

    class UnifiedResponse(BaseModel, Generic[T]):
        code: int
        data: Optional[T]
        message: str

    class TestResponse(BaseModel):
        test_field: str

    app = FastAPI()

    @app.get("/test-generic", response_model=UnifiedResponse[TestResponse])
    async def test_generic_endpoint(
        user_id: UUID = Depends(get_current_user_id),
        session: MockSession = Depends(get_db_session)
    ) -> UnifiedResponse[TestResponse]:
        return UnifiedResponse(
            code=200,
            data=TestResponse(test_field="test"),
            message="success"
        )

    try:
        schema = app.openapi()
        paths = schema.get("paths", {})

        for path, methods in paths.items():
            if "test-generic" in path:
                for method, spec in methods.items():
                    print(f"泛型响应路径: {path}")
                    if "parameters" in spec:
                        params = spec["parameters"]
                        print(f"参数: {[p.get('name') for p in params]}")
                        for param in params:
                            if param.get('name') in ['args', 'kwargs']:
                                print(f"❌ 泛型响应导致args/kwargs!")
    except Exception as e:
        print(f"泛型响应测试失败: {e}")

def test_direct_import():
    """测试直接导入是否导致问题"""
    print("\n🧪 测试直接导入是否导致问题...")

    try:
        from src.domains.user.router import router
        print("✅ 用户路由导入成功")

        # 尝试直接检查路由
        print(f"路由类型: {type(router)}")
        print(f"路由前缀: {router.prefix}")

        # 检查路由是否有问题
        from fastapi import FastAPI
        test_app = FastAPI()
        test_app.include_router(router, prefix="/test")

        schema = test_app.openapi()
        paths = schema.get("paths", {})
        print(f"测试应用路径数量: {len(paths)}")

        for path, methods in paths.items():
            if "/test" in path:
                for method, spec in methods.items():
                    if "parameters" in spec:
                        params = spec["parameters"]
                        args_kwargs = [p for p in params if p.get('name') in ['args', 'kwargs']]
                        if args_kwargs:
                            print(f"❌ 直接导入路由发现args/kwargs: {len(args_kwargs)}个")
                        else:
                            print(f"✅ 直接导入路由无args/kwargs问题")

    except Exception as e:
        print(f"❌ 直接导入测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 对比工作和有问题的路由")
    print("=" * 60)

    compare_working_vs_problematic()
    test_generic_response()
    test_direct_import()

    print("\n" + "=" * 60)
    print("🎯 对比结论:")
    print("1. 确定问题出现的具体条件")
    print("2. 找到问题的根本原因")
    print("3. 提供修复方案")
    print("=" * 60)