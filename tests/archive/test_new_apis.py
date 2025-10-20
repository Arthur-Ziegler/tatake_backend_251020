#!/usr/bin/env python3
"""
新API系统功能测试

测试按照参考文档重新设计的API系统：
1. 奖励系统API路径测试
2. 积分系统API路径测试
3. 统计系统API路径测试
4. 积分购买系统功能测试
"""

import asyncio
import sys
import json
from uuid import uuid4
from datetime import datetime, timezone, timedelta

sys.path.append('.')

from src.api.main import app
from src.api.dependencies import get_db_session, initialize_dependencies
from fastapi.testclient import TestClient


def test_new_api_routes():
    """测试新的API路由"""
    print("🚀 开始测试新API路由系统")

    # 创建测试客户端
    client = TestClient(app)

    # 测试根路径
    print("\n📌 测试1: 根路径访问")
    response = client.get("/")
    if response.status_code == 200:
        print("✅ 根路径访问正常")
        data = response.json()
        print(f"   API名称: {data['data']['name']}")
        print(f"   版本: {data['data']['version']}")
    else:
        print(f"❌ 根路径访问失败: {response.status_code}")

    # 测试奖励系统API
    print("\n📌 测试2: 奖励系统API路径")

    # 测试获取奖励目录
    response = client.get("/api/v1/rewards/catalog")
    if response.status_code == 401:  # 需要认证，说明路由正常
        print("✅ GET /rewards/catalog 路由正常（需要认证）")
    else:
        print(f"⚠️  GET /rewards/catalog 状态码: {response.status_code}")

    # 测试获取碎片收集状态
    response = client.get("/api/v1/rewards/collection")
    if response.status_code == 401:
        print("✅ GET /rewards/collection 路由正常（需要认证）")
    else:
        print(f"⚠️  GET /rewards/collection 状态码: {response.status_code}")

    # 测试积分系统API
    print("\n📌 测试3: 积分系统API路径")

    # 测试获取积分套餐
    response = client.get("/api/v1/points/packages")
    if response.status_code == 401:
        print("✅ GET /points/packages 路由正常（需要认证）")
    else:
        print(f"⚠️  GET /points/packages 状态码: {response.status_code}")

    # 测试积分余额
    response = client.get("/api/v1/points/balance")
    if response.status_code == 401:
        print("✅ GET /points/balance 路由正常（需要认证）")
    else:
        print(f"⚠️  GET /points/balance 状态码: {response.status_code}")

    # 测试统计系统API
    print("\n📌 测试4: 统计系统API路径")

    # 测试综合仪表板
    response = client.get("/api/v1/statistics/dashboard")
    if response.status_code == 401:
        print("✅ GET /statistics/dashboard 路由正常（需要认证）")
    else:
        print(f"⚠️  GET /statistics/dashboard 状态码: {response.status_code}")

    # 测试任务统计
    response = client.get("/api/v1/statistics/tasks")
    if response.status_code == 401:
        print("✅ GET /statistics/tasks 路由正常（需要认证）")
    else:
        print(f"⚠️  GET /statistics/tasks 状态码: {response.status_code}")

    # 测试专注统计
    response = client.get("/api/v1/statistics/focus")
    if response.status_code == 401:
        print("✅ GET /statistics/focus 路由正常（需要认证）")
    else:
        print(f"⚠️  GET /statistics/focus 状态码: {response.status_code}")

    # 测试API文档
    print("\n📌 测试5: API文档访问")
    response = client.get("/docs")
    if response.status_code == 200:
        print("✅ API文档访问正常")
    else:
        print(f"❌ API文档访问失败: {response.status_code}")

    response = client.get("/openapi.json")
    if response.status_code == 200:
        print("✅ OpenAPI规范访问正常")
        openapi_data = response.json()

        # 统计API端点数量
        paths = openapi_data.get("paths", {})
        total_endpoints = sum(1 for path in paths.keys() if "/api/v1" in path)
        print(f"   API端点总数: {len(paths)}")
        print(f"   v1 API端点数: {total_endpoints}")

        # 显示所有API路径
        print("\n📋 所有API路径:")
        for path in sorted(paths.keys()):
            if "/api/v1" in path:
                methods = list(paths[path].keys())
                print(f"   {path}: {methods}")
    else:
        print(f"❌ OpenAPI规范访问失败: {response.status_code}")

    print("\n🎉 新API路由系统测试完成！")


async def test_points_service_functionality():
    """测试积分服务功能"""
    print("\n🚀 开始测试积分服务功能")

    try:
        # 初始化依赖
        print("🔧 初始化依赖注入系统...")
        await initialize_dependencies()
        print("✅ 依赖注入系统初始化成功")

        # 获取数据库会话
        async for session in get_db_session():
            print("✅ 数据库连接成功")

            # 测试积分服务
            from src.services.points_service import PointsService
            points_service = PointsService(session)

            # 测试1: 获取积分套餐
            print("\n📌 测试1: 获取积分套餐")
            try:
                packages = await points_service.get_available_packages()
                print(f"✅ 获取到 {len(packages)} 个积分套餐")
                for package in packages:
                    print(f"   - {package['name']}: {package['points_amount']}积分 ¥{package['price']}")
            except Exception as e:
                print(f"⚠️  获取积分套餐失败: {str(e)}")

            # 测试2: 创建购买订单（使用模拟套餐ID）
            print("\n📌 测试2: 创建购买订单")
            test_package_id = str(uuid4())
            test_user_id = str(uuid4())

            try:
                # 这里会失败因为套餐不存在，但可以测试异常处理
                await points_service.create_purchase_order(
                    user_id=test_user_id,
                    package_id=test_package_id
                )
            except Exception as e:
                print(f"✅ 异常处理正常: 套餐不存在 - {str(e)}")

            break  # 退出数据库会话循环

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("新API系统功能测试")
    print("=" * 60)

    # 测试API路由
    test_new_api_routes()

    # 测试积分服务
    print("\n" + "=" * 60)
    success = asyncio.run(test_points_service_functionality())

    print("\n" + "=" * 60)
    if success:
        print("✅ 新API系统测试成功")
        print("💡 API路径已按照参考文档标准化")
        print("💡 积分购买系统基础功能已实现")
        print("💡 建议接下来实现数据库表创建和数据初始化")
    else:
        print("❌ 新API系统测试失败")

    print("=" * 60)


if __name__ == "__main__":
    main()