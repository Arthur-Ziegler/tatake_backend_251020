#!/usr/bin/env python3
"""
测试奖励系统的三个微服务接口

通过微信登录获取JWT token，然后测试奖励系统的三个接口：
1. GET /rewards/prizes - 查看我的奖品
2. GET /rewards/points - 查看我的积分
3. POST /rewards/redeem - 充值界面（兑换奖品）

作者：TaTake团队
"""

import asyncio
import json
import logging
from typing import Dict, Any

import httpx

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API配置
BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = ""

class RewardInterfaceTester:
    """奖励接口测试器"""

    def __init__(self):
        self.base_url = BASE_URL
        self.api_prefix = API_PREFIX
        self.token = None
        self.user_id = None

    async def test_wechat_login(self) -> bool:
        """测试微信登录获取JWT token"""
        try:
            login_data = {
                "wechat_openid": "test_reward_user_123456"
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

    async def test_get_my_prizes(self) -> bool:
        """测试1. 查看我的奖品"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/rewards/prizes",
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info(f"查看我的奖品成功: {result.get('data')}")
                        return True
                    else:
                        logger.error(f"查看我的奖品失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"查看我的奖品HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"查看我的奖品异常: {e}")
            return False

    async def test_get_my_points(self) -> bool:
        """测试2. 查看我的积分"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/rewards/points",
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info(f"查看我的积分成功: {result.get('data')}")
                        return True
                    else:
                        logger.error(f"查看我的积分失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"查看我的积分HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"查看我的积分异常: {e}")
            return False

    async def test_redeem_prize(self) -> bool:
        """测试3. 兑值界面（兑换奖品）"""
        try:
            redeem_data = {
                "code": "points"  # 使用文档中的示例兑换码
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/rewards/redeem",
                    json=redeem_data,
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        logger.info(f"兑换奖品成功: {result.get('data')}")
                        return True
                    else:
                        logger.error(f"兑换奖品失败: {result.get('message')}")
                        return False
                else:
                    logger.error(f"兑换奖品HTTP错误: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"错误详情: {error_detail}")
                    except:
                        logger.error(f"响应内容: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"兑换奖品异常: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """运行所有奖励接口测试"""
        logger.info("=" * 60)
        logger.info("开始测试奖励系统3个核心接口")
        logger.info("=" * 60)

        # 首先进行微信登录
        if not await self.test_wechat_login():
            logger.error("微信登录失败，无法进行后续测试")
            return {}

        results = {}

        # 测试所有奖励接口
        test_methods = [
            ("查看我的奖品", self.test_get_my_prizes),
            ("查看我的积分", self.test_get_my_points),
            ("兑换奖品", self.test_redeem_prize)
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

        logger.info(f"\n总计: {success_count}/{total_count} 个奖励接口测试通过")

        if success_count == total_count:
            logger.info("🎉 所有奖励接口测试通过！")
        else:
            logger.warning(f"⚠️  有 {total_count - success_count} 个奖励接口测试失败")

        return results


async def main():
    """主函数"""
    tester = RewardInterfaceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())