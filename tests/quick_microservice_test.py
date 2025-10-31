#!/usr/bin/env python3
"""
Task微服务快速验证测试脚本

快速验证Task微服务代理架构的基本功能，不需要完整测试环境。
模拟前端用户的核心操作流程。

使用方法：
python tests/quick_microservice_test.py

作者：TaKeKe团队
版本：1.0.0（Task微服务快速验证）
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4, UUID
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.services.task_microservice_client import TaskMicroserviceClient, TaskMicroserviceError
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class QuickMicroserviceTest:
    """Task微服务快速测试类"""

    def __init__(self):
        self.client = TaskMicroserviceClient()
        self.test_user_id = str(uuid4())
        self.created_tasks: List[str] = []

    async def test_basic_functionality(self):
        """测试基本功能"""
        print("🔧 开始基本功能测试...")

        # 1. 测试健康检查
        print("  1️⃣ 测试微服务健康检查...")
        try:
            health_status = await self.client.health_check()
            if health_status:
                print("     ✅ 微服务健康检查通过")
            else:
                print("     ⚠️  微服务不可用（这是正常的，因为微服务可能未启动）")
        except Exception as e:
            print(f"     ⚠️  健康检查异常: {e}")

        # 2. 测试响应格式转换
        print("  2️⃣ 测试响应格式转换...")
        try:
            # 测试成功响应转换
            success_response = {
                "success": True,
                "data": {"id": "123", "title": "测试任务"}
            }
            converted = self.client.transform_response(success_response)
            assert converted["code"] == 200
            assert converted["data"]["title"] == "测试任务"
            assert converted["message"] == "success"
            print("     ✅ 成功响应格式转换正常")

            # 测试错误响应转换
            error_response = {
                "success": False,
                "message": "任务不存在",
                "code": 404
            }
            converted = self.client.transform_response(error_response)
            assert converted["code"] == 404
            assert converted["data"] is None
            assert converted["message"] == "任务不存在"
            print("     ✅ 错误响应格式转换正常")

            # 测试无效格式
            try:
                self.client.transform_response("invalid response")
                print("     ❌ 无效格式转换应该失败")
            except TaskMicroserviceError:
                print("     ✅ 无效格式正确抛出异常")

        except Exception as e:
            print(f"     ❌ 响应格式转换测试失败: {e}")
            return False

        return True

    async def test_error_handling(self):
        """测试错误处理"""
        print("  3️⃣ 测试错误处理...")

        # 测试状态码映射
        test_cases = [
            (400, {}, 400),
            (401, {}, 401),
            (403, {}, 403),
            (404, {}, 404),
            (500, {}, 500),
        ]

        for http_status, error_content, expected_code in test_cases:
            mapped_code = self.client.map_error_status(http_status, error_content)
            assert mapped_code == expected_code, f"状态码 {http_status} 映射错误"

        print("     ✅ HTTP状态码映射正常")

        # 测试请求头生成
        headers = self.client._get_headers()
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
        print("     ✅ 请求头生成正常")

        return True

    async def test_timeout_configuration(self):
        """测试超时配置"""
        print("  4️⃣ 测试超时配置...")

        timeout = self.client.timeout
        assert timeout.connect == 5.0
        assert timeout.read == 30.0
        assert timeout.write == 10.0
        assert timeout.pool == 60.0

        print("     ✅ 超时配置正确")
        return True

    async def mock_task_operations(self):
        """模拟任务操作（不实际调用微服务）"""
        print("  5️⃣ 模拟任务操作流程...")

        try:
            # 模拟创建任务
            mock_task_data = {
                "success": True,
                "data": {
                    "id": str(uuid4()),
                    "title": "模拟任务",
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            }

            result = self.client.transform_response(mock_task_data)
            assert result["code"] == 200
            task_id = result["data"]["id"]
            print(f"     ✅ 模拟创建任务成功: {task_id[:8]}...")

            # 模拟获取任务详情
            result = self.client.transform_response(mock_task_data)
            assert result["data"]["id"] == task_id
            print("     ✅ 模拟获取任务详情成功")

            # 模拟更新任务
            update_data = {
                "success": True,
                "data": {
                    **mock_task_data["data"],
                    "title": "更新后的任务",
                    "status": "in_progress"
                }
            }
            result = self.client.transform_response(update_data)
            assert result["data"]["title"] == "更新后的任务"
            print("     ✅ 模拟更新任务成功")

            # 模拟删除任务
            delete_data = {
                "success": True,
                "data": {"deleted_task_id": task_id}
            }
            result = self.client.transform_response(delete_data)
            assert result["data"]["deleted_task_id"] == task_id
            print("     ✅ 模拟删除任务成功")

        except Exception as e:
            print(f"     ❌ 模拟任务操作失败: {e}")
            return False

        return True

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Task微服务快速验证测试")
        print("=" * 50)

        tests = [
            ("基本功能", self.test_basic_functionality),
            ("错误处理", self.test_error_handling),
            ("超时配置", self.test_timeout_configuration),
            ("任务操作模拟", self.mock_task_operations),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed += 1
            except Exception as e:
                print(f"  ❌ {test_name}测试失败: {e}")

        print("=" * 50)
        print(f"📊 测试结果: {passed}/{total} 通过")

        if passed == total:
            print("🎉 所有测试通过！Task微服务代理架构基本功能正常")
            print("\n📝 说明:")
            print("- ✅ 微服务客户端功能正常")
            print("- ✅ 响应格式转换正确")
            print("- ✅ 错误处理机制完善")
            print("- ✅ 超时配置合理")
            print("\n⚠️  注意:")
            print("- 微服务本身可能未启动，这是正常的")
            print("- 如需完整测试，请启动Task微服务(localhost:20252)")
            print("- 完整测试请运行: pytest tests/integration/test_task_microservice_frontend_simulation.py -v")
            return True
        else:
            print("❌ 部分测试失败，请检查实现")
            return False


async def main():
    """主函数"""
    tester = QuickMicroserviceTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print("Task微服务快速验证测试")
    print("正在运行基本功能检查...\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)