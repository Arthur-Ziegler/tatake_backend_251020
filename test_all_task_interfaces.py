#!/usr/bin/env python3
"""
测试当前实现的9个核心任务接口

通过微信登录获取JWT token，然后测试所有接口：
1. POST /tasks - 创建任务
2. GET /tasks - 查询所有任务
3. PUT /tasks/{task_id} - 修改任务
4. DELETE /tasks/{task_id} - 删除任务
5. POST /tasks/special/top3 - 设置Top3
6. GET /tasks/special/top3/{date} - 查看Top3
7. POST /tasks/{task_id}/complete - 任务完成
8. POST /tasks/focus-status - 发送专注状态
9. GET /tasks/pomodoro-count - 查看番茄钟计数
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import httpx

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API配置
BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = ""

class TaskInterfaceTester:
    """任务接口测试器"""

    def __init__(self):
        self.base_url = BASE_URL
        self.api_prefix = API_PREFIX
        self.token = None
        self.user_id = None
        self.created_task_id = None

    async def test_wechat_login(self) -> bool:
        """测试微信登录获取JWT token"""
        try:
            login_data = {
                "wechat_openid": "test_user_interface_123456"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/auth/wechat/login",
                    json=login_data
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        self.token = result["data"]["access_token"]
                        self.user_id = result["data"]["user_id"]
                        logger.info(f"微信登录成功，用户ID: {self.user_id}")
                        return True
                    else:
                        logger.error(f"微信登录失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"微信登录HTTP错误: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"微信登录异常: {e}")
            return False

    def get_headers(self) -> Dict[str, str]:
        """获取认证头"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def test_create_task(self) -> bool:
        """测试1. 创建任务"""
        try:
            task_data = {
                "title": "接口测试任务",
                "description": "用于测试接口的任务",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=1)).isoformat()
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/tasks",
                    json=task_data,
                    headers=self.get_headers()
                )

                if response.status_code == 201:
                    result = response.json()
                    if result.get("code") == 201:
                        self.created_task_id = result["data"]["id"]
                        logger.info(f"创建任务成功，任务ID: {self.created_task_id}")
                        return True
                    else:
                        logger.error(f"创建任务失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"创建任务HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"创建任务异常: {e}")
            return False

    async def test_get_tasks(self) -> bool:
        """测试2. 查询所有任务"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/tasks",
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        tasks = result["data"]["tasks"]
                        logger.info(f"查询任务成功，共{len(tasks)}个任务")
                        return True
                    else:
                        logger.error(f"查询任务失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"查询任务HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"查询任务异常: {e}")
            return False

    async def test_update_task(self) -> bool:
        """测试3. 修改任务"""
        if not self.created_task_id:
            logger.error("没有可用的任务ID进行修改测试")
            return False

        try:
            update_data = {
                "title": "修改后的接口测试任务",
                "description": "任务描述已修改",
                "priority": "medium"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    f"{self.base_url}{self.api_prefix}/tasks/{self.created_task_id}",
                    json=update_data,
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info("修改任务成功")
                        return True
                    else:
                        logger.error(f"修改任务失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"修改任务HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"修改任务异常: {e}")
            return False

    async def test_delete_task(self) -> bool:
        """测试4. 删除任务"""
        if not self.created_task_id:
            logger.error("没有可用的任务ID进行删除测试")
            return False

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}{self.api_prefix}/tasks/{self.created_task_id}",
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info("删除任务成功")
                        return True
                    else:
                        logger.error(f"删除任务失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"删除任务HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"删除任务异常: {e}")
            return False

    async def test_set_top3(self) -> bool:
        """测试5. 设置Top3"""
        try:
            top3_data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "task_ids": [self.created_task_id] if self.created_task_id else []
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/tasks/special/top3",
                    json=top3_data,
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info("设置Top3成功")
                        return True
                    else:
                        logger.error(f"设置Top3失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"设置Top3 HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"设置Top3异常: {e}")
            return False

    async def test_get_top3(self) -> bool:
        """测试6. 查看Top3"""
        try:
            date = datetime.now().strftime("%Y-%m-%d")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/tasks/special/top3/{date}",
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info("查看Top3成功")
                        return True
                    else:
                        logger.error(f"查看Top3失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"查看Top3 HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"查看Top3异常: {e}")
            return False

    async def test_complete_task(self) -> bool:
        """测试7. 任务完成"""
        if not self.created_task_id:
            # 创建一个新任务用于完成测试
            if not await self.test_create_task():
                logger.error("无法创建任务进行完成测试")
                return False

        try:
            complete_data = {
                "completion_type": "full",
                "completion_note": "接口测试完成"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/tasks/{self.created_task_id}/complete",
                    json=complete_data,
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info("任务完成成功")
                        return True
                    else:
                        logger.error(f"任务完成失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"任务完成HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"任务完成异常: {e}")
            return False

    async def test_send_focus_status(self) -> bool:
        """测试8. 发送专注状态"""
        try:
            focus_data = {
                "focus_status": "complete",
                "task_id": self.created_task_id,
                "duration_minutes": 30
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/tasks/focus-status",
                    json=focus_data,
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info("发送专注状态成功")
                        return True
                    else:
                        logger.error(f"发送专注状态失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"发送专注状态HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"发送专注状态异常: {e}")
            return False

    async def test_get_pomodoro_count(self) -> bool:
        """测试9. 查看番茄钟计数"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/tasks/pomodoro-count?date_filter=today",
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info("查看番茄钟计数成功")
                        return True
                    else:
                        logger.error(f"查看番茄钟计数失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"查看番茄钟计数HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"查看番茄钟计数异常: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """运行所有接口测试"""
        logger.info("=" * 60)
        logger.info("开始测试9个核心任务接口")
        logger.info("=" * 60)

        # 首先进行微信登录
        if not await self.test_wechat_login():
            logger.error("微信登录失败，无法进行后续测试")
            return {}

        results = {}

        # 测试所有接口
        test_methods = [
            ("创建任务", self.test_create_task),
            ("查询任务", self.test_get_tasks),
            ("修改任务", self.test_update_task),
            ("删除任务", self.test_delete_task),
            ("设置Top3", self.test_set_top3),
            ("查看Top3", self.test_get_top3),
            ("任务完成", self.test_complete_task),
            ("发送专注状态", self.test_send_focus_status),
            ("查看番茄钟计数", self.test_get_pomodoro_count)
        ]

        for test_name, test_method in test_methods:
            logger.info(f"\n测试接口: {test_name}")
            result = await test_method()
            results[test_name] = result
            status = "✅ 成功" if result else "❌ 失败"
            logger.info(f"结果: {status}")

        # 统计结果
        logger.info("\n" + "=" * 60)
        logger.info("测试结果汇总:")
        logger.info("=" * 60)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        for test_name, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"{status} {test_name}")

        logger.info(f"\n总计: {success_count}/{total_count} 个接口测试通过")

        if success_count == total_count:
            logger.info("🎉 所有接口测试通过！")
        else:
            logger.warning(f"⚠️  有 {total_count - success_count} 个接口测试失败")

        return results


async def main():
    """主函数"""
    tester = TaskInterfaceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())