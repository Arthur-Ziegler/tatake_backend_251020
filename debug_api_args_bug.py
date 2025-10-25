#!/usr/bin/env python3
"""
调试用户管理API的args/kwargs参数问题

根据用户提供的截图，所有用户管理API都被错误地要求传递args和kwargs参数，
这应该是FastAPI参数解析的严重BUG。
"""

import sys
import os
sys.path.append('.')

def analyze_fastapi_parameter_parsing():
    """分析FastAPI参数解析问题"""
    print("🔍 分析FastAPI参数解析问题...")

    from fastapi import FastAPI
    from fastapi.routing import APIRoute
    from pydantic import BaseModel, Field
    from typing import Optional, List

    # 检查原始用户路由的问题
    print("\n1️⃣ 检查用户路由的参数解析:")
    try:
        from src.domains.user.router import router

        for route in router.routes:
            if hasattr(route, 'endpoint'):
                print(f"路径: {route.path}")
                print(f"方法: {route.methods}")
                print(f"函数: {route.endpoint.__name__}")

                # 检查函数签名
                import inspect
                sig = inspect.signature(route.endpoint)
                print(f"参数签名: {sig}")

                # 检查路由定义
                if hasattr(route, 'dependant'):
                    try:
                        # 尝试不同的属性名
                        if hasattr(route.dependant, 'params'):
                            print(f"解析的参数: {[p.name for p in route.dependant.params]}")
                        elif hasattr(route.dependant, 'path_params'):
                            print(f"路径参数: {[p.name for p in route.dependant.path_params]}")
                        elif hasattr(route.dependant, 'query_params'):
                            print(f"查询参数: {[p.name for p in route.dependant.query_params]}")
                        else:
                            print(f"依赖属性: {dir(route.dependant)}")
                    except Exception as e:
                        print(f"依赖检查失败: {e}")

                print("---")

    except Exception as e:
        print(f"❌ 检查用户路由失败: {e}")
        import traceback
        traceback.print_exc()

def test_pydantic_field_examples():
    """测试Pydantic Field示例是否导致问题"""
    print("\n2️⃣ 测试Pydantic Field示例的影响:")

    from pydantic import BaseModel, Field
    from typing import Optional, List

    # 创建包含example字段的模型
    class TestModel(BaseModel):
        nickname: Optional[str] = Field(None, example="新昵称", description="用户昵称")
        updated_fields: List[str] = Field(..., example=["nickname"], description="已更新的字段列表")

    # 创建不包含example字段的模型
    class CleanModel(BaseModel):
        nickname: Optional[str] = Field(None, description="用户昵称")
        updated_fields: List[str] = Field(..., description="已更新的字段列表")

    print("包含example的模型:")
    print(f"  模型字段: {TestModel.model_fields}")
    print(f"  JSON Schema: {TestModel.model_json_schema()}")

    print("\n不包含example的模型:")
    print(f"  模型字段: {CleanModel.model_fields}")
    print(f"  JSON Schema: {CleanModel.model_json_schema()}")

def test_fastapi_route_creation():
    """测试FastAPI路由创建"""
    print("\n3️⃣ 测试FastAPI路由创建:")

    from fastapi import FastAPI
    from pydantic import BaseModel, Field
    from typing import Optional, List

    app = FastAPI()

    # 测试原始定义
    class UpdateProfileRequest(BaseModel):
        nickname: Optional[str] = Field(None, example="新昵称", description="用户昵称")

    class UpdateProfileResponse(BaseModel):
        updated_fields: List[str] = Field(..., example=["nickname"], description="已更新的字段列表")

    @app.put("/test-original")
    async def test_original(
        request: UpdateProfileRequest,
        user_id: str = "test-user"
    ):
        return {"status": "ok"}

    # 测试清理后的定义
    class CleanUpdateProfileRequest(BaseModel):
        nickname: Optional[str] = Field(None, description="用户昵称")

    class CleanUpdateProfileResponse(BaseModel):
        updated_fields: List[str] = Field(..., description="已更新的字段列表")

    @app.put("/test-clean")
    async def test_clean(
        request: CleanUpdateProfileRequest,
        user_id: str = "test-user"
    ):
        return {"status": "ok"}

    print("原始路由:")
    for route in app.routes:
        if hasattr(route, 'path') and 'test-original' in route.path:
            print(f"  路径: {route.path}")
            if hasattr(route, 'dependant') and hasattr(route.dependant, 'params'):
            print(f"  参数: {[p.name for p in route.dependant.params]}")
        else:
            print(f"  参数: 无法获取依赖参数信息")

    print("\n清理后路由:")
    for route in app.routes:
        if hasattr(route, 'path') and 'test-clean' in route.path:
            print(f"  路径: {route.path}")
            if hasattr(route, 'dependant') and hasattr(route.dependant, 'params'):
            print(f"  参数: {[p.name for p in route.dependant.params]}")
        else:
            print(f"  参数: 无法获取依赖参数信息")

def check_schema_validation():
    """检查Schema验证问题"""
    print("\n4️⃣ 检查Schema验证:")

    from src.domains.user.schemas import UpdateProfileRequest, UpdateProfileResponse

    try:
        print("UpdateProfileRequest schema:")
        schema = UpdateProfileRequest.model_json_schema()
        print(f"  属性: {list(schema.get('properties', {}).keys())}")
        print(f"  完整schema: {schema}")

        print("\nUpdateProfileResponse schema:")
        response_schema = UpdateProfileResponse.model_json_schema()
        print(f"  属性: {list(response_schema.get('properties', {}).keys())}")
        print(f"  完整schema: {response_schema}")

    except Exception as e:
        print(f"❌ Schema验证失败: {e}")
        import traceback
        traceback.print_exc()

def test_type_annotation_issues():
    """测试类型注解问题"""
    print("\n5️⃣ 测试类型注解问题:")

    from typing import List
    from pydantic import BaseModel, Field

    print("测试不同的类型注解:")

    # 可能有问题的类型注解
    class ProblematicTypeModel(BaseModel):
        list_field: list[str] = Field(..., example=["nickname"])
        optional_field: Optional[str] = Field(None, example="test")

    # 修复后的类型注解
    from typing import Optional as Opt
    from typing import List as Lst

    class FixedTypeModel(BaseModel):
        list_field: Lst[str] = Field(..., description="字段列表")
        optional_field: Opt[str] = Field(None, description="可选字段")

    print("可能有问题:")
    try:
        schema1 = ProblematicTypeModel.model_json_schema()
        print(f"  Schema生成成功: {len(schema1.get('properties', {}))} 个属性")
    except Exception as e:
        print(f"  ❌ Schema生成失败: {e}")

    print("修复后:")
    try:
        schema2 = FixedTypeModel.model_json_schema()
        print(f"  Schema生成成功: {len(schema2.get('properties', {}))} 个属性")
    except Exception as e:
        print(f"  ❌ Schema生成失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 调试用户管理API的args/kwargs参数问题")
    print("=" * 60)

    analyze_fastapi_parameter_parsing()
    test_pydantic_field_examples()
    test_fastapi_route_creation()
    check_schema_validation()
    test_type_annotation_issues()

    print("\n" + "=" * 60)
    print("🎯 调试结论:")
    print("1. 确定参数解析错误的根本原因")
    print("2. 找到导致args/kwargs参数的具体问题")
    print("3. 提供修复方案")
    print("=" * 60)