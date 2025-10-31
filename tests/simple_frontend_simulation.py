#!/usr/bin/env python3
"""
简化的Task微服务前端模拟测试

直接模拟前端用户的API调用，验证Task微服务代理架构的完整性。
绕过复杂的认证系统，直接测试微服务客户端和代理层。

使用方法：
python tests/simple_frontend_simulation.py

作者：TaKeKe团队
版本：1.0.0（简化前端模拟测试）
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
    from src.services.task_microservice_client import call_task_service, TaskMicroserviceError
    from src.domains.task.schemas import CreateTaskRequest, UpdateTaskRequest, TaskListQuery
    from src.domains.top3.schemas import SetTop3Request
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class SimpleFrontendSimulation:
    """简化的前端模拟测试类"""

    def __init__(self):
        self.test_user_id = str(uuid4())
        self.created_tasks: List[str] = []
        print(f"🧪 初始化前端模拟测试")
        print(f"👤 测试用户ID: {self.test_user_id}")

    async def test_task_crud_operations(self):
        """测试任务CRUD操作"""
        print("\n🔧 测试任务CRUD操作...")

        try:
            # 1. 创建任务
            print("  1️⃣ 创建任务...")
            create_data = {
                "title": "测试任务1",
                "description": "这是一个测试任务",
                "status": "pending",
                "priority": "high",
                "tags": ["测试", "重要"]
            }

            result = await call_task_service(
                method="POST",
                path="tasks",
                user_id=self.test_user_id,
                data=create_data
            )

            if result.get("success"):
                task = result["data"]
                task_id = task["id"]
                self.created_tasks.append(task_id)
                print(f"     ✅ 创建任务成功: {task_id[:8]}... - {task['title']}")
            else:
                print(f"     ❌ 创建任务失败: {result.get('message', '未知错误')}")
                return False

            # 2. 获取任务详情
            print("  2️⃣ 获取任务详情...")
            result = await call_task_service(
                method="GET",
                path=f"tasks/{task_id}",
                user_id=self.test_user_id
            )

            if result.get("success"):
                task = result["data"]
                print(f"     ✅ 获取任务成功: {task['title']} - 状态: {task['status']}")
            else:
                print(f"     ❌ 获取任务失败: {result.get('message', '未知错误')}")
                return False

            # 3. 更新任务
            print("  3️⃣ 更新任务...")
            update_data = {
                "title": "更新后的任务",
                "status": "in_progress",
                "description": "任务已开始进行"
            }

            result = await call_task_service(
                method="PUT",
                path=f"tasks/{task_id}",
                user_id=self.test_user_id,
                data=update_data
            )

            if result.get("success"):
                task = result["data"]
                print(f"     ✅ 更新任务成功: {task['title']} - 状态: {task['status']}")
            else:
                print(f"     ❌ 更新任务失败: {result.get('message', '未知错误')}")
                return False

            # 4. 获取任务列表
            print("  4️⃣ 获取任务列表...")
            list_params = {"page": 1, "page_size": 10}
            result = await call_task_service(
                method="GET",
                path="tasks",
                user_id=self.test_user_id,
                params=list_params
            )

            if result.get("success"):
                data = result["data"]
                tasks = data.get("tasks", [])
                pagination = data.get("pagination", {})
                print(f"     ✅ 获取任务列表成功: 共 {len(tasks)} 个任务")
                print(f"        📄 分页信息: 第 {pagination.get('current_page')} 页，每页 {pagination.get('page_size')} 个")
            else:
                print(f"     ❌ 获取任务列表失败: {result.get('message', '未知错误')}")
                return False

            # 5. 删除任务
            print("  5️⃣ 删除任务...")
            result = await call_task_service(
                method="DELETE",
                path=f"tasks/{task_id}",
                user_id=self.test_user_id
            )

            if result.get("success"):
                print(f"     ✅ 删除任务成功: {task_id[:8]}...")
                self.created_tasks.remove(task_id)
            else:
                print(f"     ❌ 删除任务失败: {result.get('message', '未知错误')}")
                return False

            return True

        except TaskMicroserviceError as e:
            print(f"     ❌ 微服务调用错误: {e}")
            return False
        except Exception as e:
            print(f"     ❌ 未知错误: {e}")
            return False

    async def test_top3_operations(self):
        """测试Top3操作"""
        print("\n🏆 测试Top3操作...")

        try:
            # 先创建一些任务作为Top3候选
            task_ids = []
            print("  📝 创建Top3候选任务...")
            for i in range(3):
                create_data = {
                    "title": f"Top3候选任务{i+1}",
                    "description": f"重要的任务{i+1}",
                    "priority": "high" if i < 2 else "medium"
                }

                result = await call_task_service(
                    method="POST",
                    path="tasks",
                    user_id=self.test_user_id,
                    data=create_data
                )

                if result.get("success"):
                    task_id = result["data"]["id"]
                    task_ids.append(task_id)
                    self.created_tasks.append(task_id)
                    print(f"     ✅ 创建候选任务{i+1}: {task_id[:8]}...")
                else:
                    print(f"     ❌ 创建候选任务{i+1}失败")
                    return False

            print(f"  ✅ 创建了 {len(task_ids)} 个候选任务")

            # 设置Top3
            print("  1️⃣ 设置Top3...")
            from datetime import date
            today = date.today().isoformat()

            top3_data = {
                "date": today,
                "task_ids": task_ids[:2]  # 选择前两个任务作为Top3
            }

            result = await call_task_service(
                method="POST",
                path="tasks/special/top3",
                user_id=self.test_user_id,
                data=top3_data
            )

            if result.get("success"):
                data = result["data"]
                print(f"     ✅ 设置Top3成功: {today}")
                print(f"        🎯 Top3任务数: {len(data.get('task_ids', []))}")
                print(f"        💰 消耗积分: {data.get('points_consumed', 0)}")
            else:
                print(f"     ❌ 设置Top3失败: {result.get('message', '未知错误')}")
                return False

            # 获取Top3
            print("  2️⃣ 获取Top3...")
            result = await call_task_service(
                method="GET",
                path=f"tasks/special/top3/{today}",
                user_id=self.test_user_id
            )

            if result.get("success"):
                data = result["data"]
                print(f"     ✅ 获取Top3成功: {data.get('date')}")
                print(f"        🎯 Top3任务数: {len(data.get('task_ids', []))}")
            else:
                print(f"     ❌ 获取Top3失败: {result.get('message', '未知错误')}")
                return False

            return True

        except TaskMicroserviceError as e:
            print(f"     ❌ 微服务调用错误: {e}")
            return False
        except Exception as e:
            print(f"     ❌ 未知错误: {e}")
            return False

    async def test_task_statistics(self):
        """测试任务统计"""
        print("\n📊 测试任务统计...")

        try:
            # 获取统计
            result = await call_task_service(
                method="GET",
                path="tasks/statistics",
                user_id=self.test_user_id
            )

            if result.get("success"):
                stats = result["data"]
                print(f"     ✅ 获取统计成功:")
                print(f"        📈 总任务数: {stats.get('total_tasks', 0)}")
                print(f"        ✅ 已完成: {stats.get('completed_tasks', 0)}")
                print(f"        🔄 进行中: {stats.get('in_progress_tasks', 0)}")
                print(f"        ⏳ 待处理: {stats.get('pending_tasks', 0)}")
                print(f"        📊 完成率: {stats.get('completion_rate', 0):.1f}%")
                return True
            else:
                print(f"     ❌ 获取统计失败: {result.get('message', '未知错误')}")
                return False

        except TaskMicroserviceError as e:
            print(f"     ❌ 微服务调用错误: {e}")
            return False
        except Exception as e:
            print(f"     ❌ 未知错误: {e}")
            return False

    async def test_error_handling(self):
        """测试错误处理"""
        print("\n⚠️ 测试错误处理...")

        try:
            # 测试获取不存在的任务
            print("  1️⃣ 测试获取不存在的任务...")
            fake_id = str(uuid4())
            result = await call_task_service(
                method="GET",
                path=f"tasks/{fake_id}",
                user_id=self.test_user_id
            )

            if not result.get("success"):
                print(f"     ✅ 正确处理任务不存在: {result.get('message', '未知错误')}")
            else:
                print("     ❌ 应该返回错误但返回了成功")
                return False

            # 测试无效的HTTP方法
            print("  2️⃣ 测试无效操作...")
            try:
                result = await call_task_service(
                    method="INVALID",
                    path="tasks",
                    user_id=self.test_user_id,
                    data={}
                )
                print("     ❌ 应该抛出异常但没有")
                return False
            except TaskMicroserviceError:
                print("     ✅ 正确处理无效HTTP方法")

            return True

        except Exception as e:
            print(f"     ❌ 测试错误处理时出现异常: {e}")
            return False

    async def cleanup(self):
        """清理测试数据"""
        print("\n🧹 清理测试数据...")

        if not self.created_tasks:
            print("     ℹ️  没有需要清理的任务")
            return

        cleaned = 0
        for task_id in self.created_tasks[:]:  # 使用副本进行迭代
            try:
                result = await call_task_service(
                    method="DELETE",
                    path=f"tasks/{task_id}",
                    user_id=self.test_user_id
                )

                if result.get("success"):
                    cleaned += 1
                    self.created_tasks.remove(task_id)
            except:
                pass  # 忽略清理错误

        print(f"     ✅ 清理完成，删除了 {cleaned} 个任务")

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Task微服务前端模拟测试")
        print("=" * 50)

        tests = [
            ("任务CRUD操作", self.test_task_crud_operations),
            ("Top3操作", self.test_top3_operations),
            ("任务统计", self.test_task_statistics),
            ("错误处理", self.test_error_handling),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                print(f"\n🧪 运行测试: {test_name}")
                if await test_func():
                    passed += 1
                    print(f"✅ {test_name} 测试通过")
                else:
                    print(f"❌ {test_name} 测试失败")
            except Exception as e:
                print(f"❌ {test_name} 测试异常: {e}")

        # 清理
        await self.cleanup()

        print("\n" + "=" * 50)
        print(f"📊 测试结果: {passed}/{total} 通过")

        if passed == total:
            print("🎉 所有测试通过！Task微服务代理架构工作正常")
            print("\n📝 测试总结:")
            print("- ✅ 任务CRUD操作正常")
            print("- ✅ Top3功能正常")
            print("- ✅ 统计功能正常")
            print("- ✅ 错误处理机制完善")
            print("\n🏗️ 架构验证:")
            print("- ✅ 微服务客户端功能正常")
            print("- ✅ 响应格式转换正确")
            print("- ✅ HTTP请求处理正常")
            print("- ✅ 错误映射机制完善")
            print("\n⚠️  注意:")
            print("- 微服务本身可能未启动，测试使用了Mock数据")
            print("- 如需完整测试，请启动Task微服务(localhost:20252)")
            return True
        else:
            print("❌ 部分测试失败，请检查实现")
            return False


async def main():
    """主函数"""
    simulator = SimpleFrontendSimulation()
    success = await simulator.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print("Task微服务前端模拟测试")
    print("正在测试微服务代理架构的完整性...\n")

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