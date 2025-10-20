#!/usr/bin/env python3
"""
API路由测试（简化版）

测试新的API路由是否正确注册，不需要认证。
"""

import asyncio
import sys
from fastapi.routing import APIRoute

sys.path.append('.')

from src.api.main import app


def test_api_routes():
    """测试API路由注册情况"""
    print("🚀 开始测试API路由注册情况")

    # 获取所有路由
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name,
                "tags": getattr(route, 'tags', [])
            })

    print(f"\n📋 总共发现 {len(routes)} 个API路由")

    # 按分组统计路由
    tag_groups = {}
    for route in routes:
        route_tags = route.get("tags", [])
        for tag in route_tags:
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(route)

    print("\n📊 按功能模块统计:")
    for tag, tag_routes in tag_groups.items():
        print(f"   {tag}: {len(tag_routes)} 个API")

    # 检查参考文档要求的API路径
    print("\n📌 检查参考文档要求的API路径:")

    # 奖励系统API
    rewards_apis = [
        "/api/v1/rewards/catalog",
        "/api/v1/rewards/collection",
        "/api/v1/rewards/redeem"
    ]

    # 积分系统API
    points_apis = [
        "/api/v1/points/balance",
        "/api/v1/points/transactions",
        "/api/v1/points/packages",
        "/api/v1/points/purchase",
        "/api/v1/points/purchase/{order_id}"
    ]

    # 统计系统API
    statistics_apis = [
        "/api/v1/statistics/dashboard",
        "/api/v1/statistics/tasks",
        "/api/v1/statistics/focus"
    ]

    all_required_apis = rewards_apis + points_apis + statistics_apis

    # 检查每个要求的API
    found_apis = []
    missing_apis = []

    for required_api in all_required_apis:
        found = False
        for route in routes:
            if route["path"].startswith(required_api.split("{")[0]):
                found_apis.append(required_api)
                found = True
                break
        if not found:
            missing_apis.append(required_api)

    print(f"\n✅ 找到的API ({len(found_apis)}):")
    for api in found_apis:
        print(f"   {api}")

    print(f"\n❌ 缺失的API ({len(missing_apis)}):")
    for api in missing_apis:
        print(f"   {api}")

    # 显示所有实际的API路径
    print(f"\n📋 所有实际的API路径:")
    for route in sorted(routes, key=lambda x: x["path"]):
        if "/api/v1" in route["path"]:
            methods_str = ", ".join(route["methods"])
            print(f"   {methods_str:8} {route['path']}")

    # 完成度统计
    completion_rate = len(found_apis) / len(all_required_apis) * 100
    print(f"\n📈 API完成度: {completion_rate:.1f}% ({len(found_apis)}/{len(all_required_apis)})")

    if completion_rate >= 90:
        print("🎉 API路由实现基本完成！")
    elif completion_rate >= 70:
        print("👍 API路由实现良好，还需要补充一些API")
    else:
        print("⚠️  API路由实现还需要继续完善")

    return len(missing_apis) == 0


def test_openapi_spec():
    """测试OpenAPI规范"""
    print("\n🔍 测试OpenAPI规范生成")

    try:
        openapi_schema = app.openapi()

        print(f"✅ OpenAPI规范生成成功")
        print(f"   标题: {openapi_schema.get('info', {}).get('title')}")
        print(f"   版本: {openapi_schema.get('info', {}).get('version')}")
        print(f"   路径数量: {len(openapi_schema.get('paths', {}))}")

        # 按路径前缀统计
        paths = openapi_schema.get('paths', {})
        prefixes = {}
        for path in paths:
            if '/api/v1' in path:
                prefix = path.split('/')[3]  # /api/v1/xxx
                prefixes[prefix] = prefixes.get(prefix, 0) + 1

        print(f"\n📊 API模块分布:")
        for prefix, count in sorted(prefixes.items()):
            print(f"   /api/v1/{prefix}: {count} 个端点")

        return True

    except Exception as e:
        print(f"❌ OpenAPI规范生成失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("API路由测试（简化版）")
    print("=" * 60)

    # 测试API路由
    routes_complete = test_api_routes()

    # 测试OpenAPI规范
    openapi_ok = test_openapi_spec()

    print("\n" + "=" * 60)
    if routes_complete and openapi_ok:
        print("🎉 所有测试通过！")
        print("✅ API路由已按照参考文档标准化")
        print("✅ 积分购买系统API路径已实现")
        print("✅ 统计系统API路径已实现")
        print("💡 接下来可以开始实现具体业务逻辑")
    else:
        print("⚠️  部分测试未通过，需要继续完善")

    print("=" * 60)


if __name__ == "__main__":
    main()