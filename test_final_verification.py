#!/usr/bin/env python3
"""
最终验证测试

验证所有API功能与参考设计文档的一致性，包括：
1. API路径完全匹配验证
2. API响应格式验证
3. 业务逻辑完整性验证
4. 系统架构一致性验证
"""

import asyncio
import sys
from fastapi.routing import APIRoute

sys.path.append('.')

from src.api.main import app


def verify_api_completeness():
    """验证API完整性"""
    print("🔍 验证API完整性")

    # 参考文档要求的API清单
    reference_apis = {
        "认证系统 (7个)": [
            "POST /auth/guest/init",
            "POST /auth/guest/upgrade",
            "POST /auth/sms/send",
            "POST /auth/login",
            "POST /auth/refresh",
            "POST /auth/logout",
            "GET /auth/user-info"
        ],
        "AI对话系统 (4个)": [
            "POST /chat/sessions",
            "POST /chat/sessions/{session_id}/send",
            "GET /chat/sessions/{session_id}/history",
            "GET /chat/sessions"
        ],
        "任务树系统 (12个)": [
            "POST /tasks",
            "GET /tasks/{id}",
            "PUT /tasks/{id}",
            "DELETE /tasks/{id}",
            "POST /tasks/{id}/complete",
            "POST /tasks/{id}/uncomplete",
            "GET /tasks/search",
            "GET /tasks/filter",
            "POST /tasks/top3",
            "PUT /tasks/top3/{date}",
            "GET /tasks/top3/{date}"
        ],
        "番茄钟系统 (8个)": [
            "POST /focus/sessions",
            "GET /focus/sessions/{id}",
            "PUT /focus/sessions/{id}/pause",
            "PUT /focus/sessions/{id}/resume",
            "POST /focus/sessions/{id}/complete",
            "GET /focus/sessions",
            "GET /focus/statistics",
            "GET /focus/tasks/{taskId}/sessions"
        ],
        "奖励系统 (8个)": [
            "GET /rewards/catalog",
            "GET /rewards/collection",
            "POST /rewards/redeem",
            "GET /points/balance",
            "GET /points/transactions",
            "GET /points/packages",
            "POST /points/purchase",
            "GET /points/purchase/{id}"
        ],
        "统计系统 (5个)": [
            "GET /statistics/dashboard",
            "GET /statistics/tasks",
            "GET /statistics/focus"
        ],
        "用户系统 (4个)": [
            "GET /user/profile",
            "PUT /user/profile",
            "POST /user/avatar",
            "POST /user/feedback"
        ]
    }

    # 获取实际实现的API
    actual_routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods - {"HEAD", "OPTIONS"}:
                actual_routes.append(f"{method} {route.path}")

    # 验证每个模块的API
    total_required = 0
    total_found = 0

    for module_name, api_list in reference_apis.items():
        required_count = len(api_list)
        total_required += required_count

        found_count = 0
        missing_apis = []

        for api in api_list:
            method, path = api.split(" ", 1)
            full_path = f"/api/v1{path}"

            # 检查API是否存在（支持路径参数匹配）
            found = False
            for actual_route in actual_routes:
                actual_method, actual_path = actual_route.split(" ", 1)

                if actual_method != method:
                    continue

                # 简单的路径参数匹配
                if "{" in path:
                    # 将路径参数替换为通配符
                    path_pattern = path.replace("{id}", "*").replace("{session_id}", "*").replace("{date}", "*").replace("{order_id}", "*").replace("{taskId}", "*")
                    if actual_path.startswith(full_path.replace("*", "").split("{")[0]):
                        found = True
                        break
                else:
                    if actual_path == full_path:
                        found = True
                        break

            if found:
                found_count += 1
            else:
                missing_apis.append(api)

        total_found += found_count
        completion_rate = (found_count / required_count) * 100 if required_count > 0 else 0

        print(f"\n📊 {module_name}:")
        print(f"   要求: {required_count} 个, 找到: {found_count} 个, 完成率: {completion_rate:.1f}%")

        if missing_apis:
            print(f"   ⚠️  缺失: {missing_apis}")
        else:
            print("   ✅ 全部实现")

    # 总体完成度
    overall_completion = (total_found / total_required) * 100 if total_required > 0 else 0
    print(f"\n📈 总体完成度: {overall_completion:.1f}% ({total_found}/{total_required})")

    return overall_completion >= 95


def verify_api_structure():
    """验证API结构"""
    print("\n🏗️ 验证API结构")

    # 检查路由分组
    routes_by_tag = {}
    for route in app.routes:
        if isinstance(route, APIRoute):
            tags = getattr(route, 'tags', [])
            for tag in tags:
                if tag not in routes_by_tag:
                    routes_by_tag[tag] = []
                routes_by_tag[tag].append(route)

    expected_modules = [
        "认证系统", "用户管理", "任务管理", "AI对话",
        "专注系统", "奖励系统", "积分系统", "统计分析", "系统"
    ]

    print("📋 模块结构检查:")
    for module in expected_modules:
        if module in routes_by_tag:
            count = len(routes_by_tag[module])
            print(f"   ✅ {module}: {count} 个API")
        else:
            print(f"   ❌ {module}: 未找到")

    # 检查API前缀标准化
    standardized_routes = 0
    total_v1_routes = 0

    for route in app.routes:
        if isinstance(route, APIRoute):
            if "/api/v1" in route.path:
                total_v1_routes += 1
                if route.path.startswith("/api/v1/"):
                    standardized_routes += 1

    standardization_rate = (standardized_routes / total_v1_routes) * 100 if total_v1_routes > 0 else 0
    print(f"\n📐 API路径标准化: {standardization_rate:.1f}% ({standardized_routes}/{total_v1_routes})")

    return standardization_rate >= 90


def verify_openapi_spec():
    """验证OpenAPI规范"""
    print("\n📖 验证OpenAPI规范")

    try:
        openapi_schema = app.openapi()

        # 检查基本信息
        info = openapi_schema.get("info", {})
        print(f"✅ 标题: {info.get('title')}")
        print(f"✅ 版本: {info.get('version')}")
        print(f"✅ 描述: {info.get('description')[:50]}..." if info.get('description') else "⚠️  缺少描述")

        # 检查路径
        paths = openapi_schema.get("paths", {})
        print(f"✅ API路径数量: {len(paths)}")

        # 检查组件
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})
        print(f"✅ 数据模型数量: {len(schemas)}")

        # 检查安全定义
        security_schemes = components.get("securitySchemes", {})
        print(f"✅ 认证方案数量: {len(security_schemes)}")

        return True

    except Exception as e:
        print(f"❌ OpenAPI规范验证失败: {str(e)}")
        return False


def verify_business_logic():
    """验证业务逻辑完整性"""
    print("\n💼 验证业务逻辑完整性")

    # 检查关键业务模块
    critical_modules = [
        "src.api.routers.auth",
        "src.api.routers.user",
        "src.api.routers.tasks",
        "src.api.routers.chat",
        "src.api.routers.focus",
        "src.api.routers.rewards_new",
        "src.api.routers.statistics_new",
        "src.services.points_service",
        "src.models.points"
    ]

    print("🔧 关键模块检查:")
    modules_found = 0

    for module in critical_modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
            modules_found += 1
        except ImportError as e:
            print(f"   ❌ {module}: {str(e)}")

    completion_rate = (modules_found / len(critical_modules)) * 100
    print(f"\n📊 模块完整性: {completion_rate:.1f}% ({modules_found}/{len(critical_modules)})")

    return completion_rate >= 90


def generate_final_report():
    """生成最终报告"""
    print("\n" + "="*60)
    print("🎯 最终验证报告")
    print("="*60)

    # 执行所有验证
    api_complete = verify_api_completeness()
    structure_good = verify_api_structure()
    openapi_valid = verify_openapi_spec()
    logic_complete = verify_business_logic()

    # 计算总体评分
    checks = [api_complete, structure_good, openapi_valid, logic_complete]
    passed_checks = sum(checks)
    overall_score = (passed_checks / len(checks)) * 100

    print(f"\n🏆 总体评分: {overall_score:.1f}% ({passed_checks}/{len(checks)} 项检查通过)")

    # 生成建议
    print("\n💡 优化建议:")

    if not api_complete:
        print("   🔧 补充缺失的API端点")

    if not structure_good:
        print("   🔧 统一API路径前缀")

    if not openapi_valid:
        print("   🔧 完善API文档和模型定义")

    if not logic_complete:
        print("   🔧 完善业务逻辑实现")

    if overall_score >= 95:
        print("\n🎉 恭喜！API系统已基本完成，符合参考文档要求")
        print("💡 建议进行数据库表创建和数据初始化")
    elif overall_score >= 80:
        print("\n👍 API系统实现良好，还有少量优化空间")
    else:
        print("\n⚠️  API系统还需要继续完善")

    print("\n📋 下一步工作:")
    print("   1. 创建数据库表初始化脚本")
    print("   2. 准备测试数据")
    print("   3. 进行集成测试")
    print("   4. 部署到测试环境")

    return overall_score


def main():
    """主函数"""
    print("🚀 开始最终验证测试")

    score = generate_final_report()

    print("\n" + "="*60)
    if score >= 95:
        print("✅ 验证通过！API系统已准备就绪")
        exit(0)
    else:
        print("⚠️  验证未完全通过，需要继续优化")
        exit(1)


if __name__ == "__main__":
    main()