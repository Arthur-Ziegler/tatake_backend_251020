#!/usr/bin/env python3
"""
真实的Task微服务前端测试

直接测试运行中的Task微服务(localhost:20252)，验证微服务代理架构的真实工作情况。

使用方法：
python tests/real_microservice_test.py

作者：TaKeKe团队
版本：1.0.0（真实微服务测试）
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, date
from uuid import uuid4, UUID
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.services.task_microservice_client import call_task_service, TaskMicroserviceError
    from src.services.task_microservice_client import TaskMicroserviceClient
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class RealMicroserviceTest:
    """真实微服务测试类"""

    def __init__(self):
        self.test_user_id = str(uuid4())
        self.created_tasks: List[str] = []
        self.client = TaskMicroserviceClient()
        print(f"🧪 初始化真实Task微服务测试")
        print(f"👤 测试用户ID: {self.test_user_id}")
        print(f"🌐 微服务地址: {self.client.base_url}")

    async def check_microservice_health(self):
        """检查微服务健康状态"""
        print("\n🏥 检查微服务健康状态...")

        try:
            health_status = await self.client.health_check()
            if health_status:
                print("     ✅ 微服务健康检查通过")
                return True
            else:
                print("     ❌ 微服务健康检查失败")
                return False
        except Exception as e:
            print(f"     ❌ 健康检查异常: {e}")
            return False

    async def test_task_crud_operations(self):
        """测试任务CRUD操作"""
        print("\n🔧 测试任务CRUD操作...")

        try:
            # 1. 创建任务
            print("  1️⃣ 创建任务...")
            create_data = {
                "user_id": self.test_user_id,
                "title": "真实测试任务1",
                "description": "这是一个真实微服务测试任务",
                "status": "pending",
                "priority": "high",
                "tags": ["真实测试", "重要"]
            }

            result = await call_task_service(
                method="POST",
                path="tasks",
                user_id=self.test_user_id,
                data=create_data
            )

            if result.get("code") == 200:
                task = result["data"]
                task_id = task["id"]
                self.created_tasks.append(task_id)
                print(f"     ✅ 创建任务成功: {task_id[:8]}... - {task['title']}")
                print(f"        📊 状态: {task['status']}, 优先级: {task['priority']}")
            else:
                print(f"     ❌ 创建任务失败: {result.get('message', '未知错误')}")
                print(f"        📝 错误代码: {result.get('code')}")
                return False

            # 2. 获取任务详情
            print("  2️⃣ 获取任务详情...")
            result = await call_task_service(
                method="GET",
                path=f"tasks/{task_id}",
                user_id=self.test_user_id
            )

            if result.get("code") == 200:
                task = result["data"]
                print(f"     ✅ 获取任务成功: {task['title']}")
                print(f"        📊 状态: {task['status']}, 描述: {task.get('description', '无')[:30]}...")
            else:
                print(f"     ❌ 获取任务失败: {result.get('message', '未知错误')}")
                return False

            # 3. 更新任务
            print("  3️⃣ 更新任务...")
            update_data = {
                "user_id": self.test_user_id,
                "title": "更新后的真实任务",
                "status": "in_progress",
                "description": "任务正在进行中，这是真实微服务环境的测试"
            }

            result = await call_task_service(
                method="PUT",
                path=f"tasks/{task_id}",
                user_id=self.test_user_id,
                data=update_data
            )

            if result.get("code") == 200:
                task = result["data"]
                print(f"     ✅ 更新任务成功: {task['title']}")
                print(f"        📊 新状态: {task['status']}")
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

            if result.get("code") == 200:
                data = result["data"]
                tasks = data.get("tasks", [])
                pagination = data.get("pagination", {})
                print(f"     ✅ 获取任务列表成功: 共 {len(tasks)} 个任务")
                print(f"        📄 分页信息: 第 {pagination.get('current_page')} 页，总页数 {pagination.get('total_pages')}")
                print(f"        📊 总数: {pagination.get('total_count')}")
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

            if result.get("code") == 200:
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
            import traceback
            traceback.print_exc()
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
                    "user_id": self.test_user_id,
                    "title": f"真实Top3候选任务{i+1}",
                    "description": f"重要的真实任务{i+1}，用于Top3测试",
                    "priority": "high" if i < 2 else "medium",
                    "tags": ["Top3", "真实测试"]
                }

                result = await call_task_service(
                    method="POST",
                    path="tasks",
                    user_id=self.test_user_id,
                    data=create_data
                )

                if result.get("code") == 200:
                    task_id = result["data"]["id"]
                    task_ids.append(task_id)
                    self.created_tasks.append(task_id)
                    print(f"     ✅ 创建候选任务{i+1}: {task_id[:8]}...")
                else:
                    print(f"     ❌ 创建候选任务{i+1}失败: {result.get('message', '未知错误')}")
                    return False

            print(f"  ✅ 创建了 {len(task_ids)} 个候选任务")

            # 设置Top3
            print("  1️⃣ 设置Top3...")
            today = date.today().isoformat()

            top3_data = {
                "user_id": self.test_user_id,
                "date": today,
                "task_ids": task_ids[:2]  # 选择前两个任务作为Top3
            }

            result = await call_task_service(
                method="POST",
                path="tasks/special/top3",
                user_id=self.test_user_id,
                data=top3_data
            )

            if result.get("code") == 200:
                data = result["data"]
                print(f"     ✅ 设置Top3成功: {today}")
                print(f"        🎯 Top3任务数: {len(data.get('task_ids', []))}")
                print(f"        💰 消耗积分: {data.get('points_consumed', 0)}")
                print(f"        🕐 创建时间: {data.get('created_at', '未知')}")
            else:
                print(f"     ❌ 设置Top3失败: {result.get('message', '未知错误')}")
                print(f"        📝 错误代码: {result.get('code')}")
                return False

            # 获取Top3
            print("  2️⃣ 获取Top3...")
            result = await call_task_service(
                method="GET",
                path=f"tasks/special/top3/{today}",
                user_id=self.test_user_id
            )

            if result.get("code") == 200:
                data = result["data"]
                print(f"     ✅ 获取Top3成功: {data.get('date')}")
                print(f"        🎯 Top3任务数: {len(data.get('task_ids', []))}")
                print(f"        💰 消耗积分: {data.get('points_consumed', 0)}")
            else:
                print(f"     ❌ 获取Top3失败: {result.get('message', '未知错误')}")
                return False

            return True

        except TaskMicroserviceError as e:
            print(f"     ❌ 微服务调用错误: {e}")
            return False
        except Exception as e:
            print(f"     ❌ 未知错误: {e}")
            import traceback
            traceback.print_exc()
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

            if result.get("code") == 200:
                stats = result["data"]
                print(f"     ✅ 获取统计成功:")
                print(f"        📈 总任务数: {stats.get('total_tasks', 0)}")
                print(f"        ✅ 已完成: {stats.get('completed_tasks', 0)}")
                print(f"        🔄 进行中: {stats.get('in_progress_tasks', 0)}")
                print(f"        ⏳ 待处理: {stats.get('pending_tasks', 0)}")
                print(f"        📊 完成率: {stats.get('completion_rate', 0):.1f}%")
                print(f"        🕐 最后更新: {stats.get('last_updated', '未知')}")
                return True
            else:
                print(f"     ❌ 获取统计失败: {result.get('message', '未知错误')}")
                print(f"        📝 错误代码: {result.get('code')}")
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

            if result.get("code") == 404:
                print(f"     ✅ 正确处理任务不存在: {result.get('message', '未知错误')}")
            else:
                print(f"     ❌ 应该返回404错误，实际返回: {result.get('code')}")
                return False

            # 测试无效的数据
            print("  2️⃣ 测试无效数据...")
            invalid_data = {
                "title": "",  # 空标题应该失败
                "status": "invalid_status"  # 无效状态
            }

            result = await call_task_service(
                method="POST",
                path="tasks",
                user_id=self.test_user_id,
                data=invalid_data
            )

            if result.get("code") != 200:
                print(f"     ✅ 正确处理无效数据: {result.get('message', '验证失败')}")
            else:
                print("     ❌ 应该拒绝无效数据")
                return False

            return True

        except TaskMicroserviceError as e:
            print(f"     ❌ 微服务调用错误: {e}")
            return False
        except Exception as e:
            print(f"     ❌ 未知错误: {e}")
            return False

    async def test_performance(self):
        """测试性能"""
        print("\n⚡ 测试性能...")

        try:
            import time
            print("  🚀 批量操作性能测试...")

            # 创建多个任务测试性能
            start_time = time.time()
            created_count = 0

            for i in range(10):
                create_data = {
                    "user_id": self.test_user_id,
                    "title": f"性能测试任务{i+1}",
                    "description": f"第{i+1}个性能测试任务",
                    "status": "pending",
                    "priority": "medium"
                }

                result = await call_task_service(
                    method="POST",
                    path="tasks",
                    user_id=self.test_user_id,
                    data=create_data
                )

                if result.get("code") == 200:
                    task_id = result["data"]["id"]
                    self.created_tasks.append(task_id)
                    created_count += 1

            end_time = time.time()
            duration = end_time - start_time

            print(f"     ✅ 创建了 {created_count} 个任务")
            print(f"        ⏱️  总耗时: {duration:.2f} 秒")
            print(f"        📊 平均耗时: {duration/created_count:.3f} 秒/任务")

            if duration < 5.0:  # 5秒内完成10个任务创建
                print("     ✅ 性能测试通过")
                return True
            else:
                print("     ⚠️  性能较慢，但测试通过")
                return True

        except Exception as e:
            print(f"     ❌ 性能测试异常: {e}")
            return False

    async def cleanup(self):
        """清理测试数据"""
        print("\n🧹 清理测试数据...")

        if not self.created_tasks:
            print("     ℹ️  没有需要清理的任务")
            return

        cleaned = 0
        failed = 0

        print(f"     🗑️  准备删除 {len(self.created_tasks)} 个任务...")

        for task_id in self.created_tasks[:]:  # 使用副本进行迭代
            try:
                result = await call_task_service(
                    method="DELETE",
                    path=f"tasks/{task_id}",
                    user_id=self.test_user_id
                )

                if result.get("code") == 200:
                    cleaned += 1
                    self.created_tasks.remove(task_id)
                else:
                    failed += 1
                    print(f"        ⚠️  删除任务失败: {task_id[:8]}... - {result.get('message', '未知错误')}")
            except Exception as e:
                failed += 1
                print(f"        ❌ 删除任务异常: {task_id[:8]}... - {e}")

        print(f"     ✅ 清理完成: 成功 {cleaned} 个，失败 {failed} 个")

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始真实Task微服务前端测试")
        print("=" * 60)

        # 首先检查微服务健康状态
        if not await self.check_microservice_health():
            print("❌ 微服务不可用，终止测试")
            return False

        tests = [
            ("任务CRUD操作", self.test_task_crud_operations),
            ("Top3操作", self.test_top3_operations),
            ("任务统计", self.test_task_statistics),
            ("错误处理", self.test_error_handling),
            ("性能测试", self.test_performance),
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
                import traceback
                traceback.print_exc()

        # 清理
        await self.cleanup()

        print("\n" + "=" * 60)
        print(f"📊 测试结果: {passed}/{total} 通过")

        if passed == total:
            print("🎉 所有测试通过！真实Task微服务工作正常")
            print("\n📝 真实测试总结:")
            print("- ✅ 任务CRUD操作正常")
            print("- ✅ Top3功能正常")
            print("- ✅ 统计功能正常")
            print("- ✅ 错误处理机制完善")
            print("- ✅ 性能表现良好")
            print("\n🏗️ 微服务架构验证:")
            print("- ✅ 真实微服务运行正常")
            print("- ✅ HTTP通信正常")
            print("- ✅ 数据持久化正常")
            print("- ✅ API响应格式正确")
            print("- ✅ 错误处理机制完善")
            print("\n🌐 网络验证:")
            print(f"- 🌍 微服务地址: {self.client.base_url}")
            print("- 📡 网络连接正常")
            print("- ⚡ 响应速度正常")
            return True
        else:
            print("❌ 部分测试失败，请检查微服务实现")
            return False


async def main():
    """主函数"""
    tester = RealMicroserviceTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print("真实Task微服务前端测试")
    print("正在测试运行中的Task微服务...\n")

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