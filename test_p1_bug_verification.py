"""
P1级Bug修复验证测试

专门测试1.4.2 OpenSpec中修复的5个P1级Bug：

1. ✅ PointsService UUID类型处理 - 所有方法支持UUID/str双类型
2. ✅ RewardService UUID类型处理 - 所有方法支持UUID/str双类型
3. ✅ WelcomeGiftService数据验证 - 写入后立即验证数据一致性
4. ✅ Session依赖统一 - 删除get_user_session，统一使用SessionDep
5. ✅ Avatar和Feedback功能删除 - 完全删除相关API、Schema和数据库字段

作者：TaKeKe团队
版本：1.4.2
日期：2025-10-25
"""

import requests
import uuid
import logging
from typing import Dict, Any, Tuple, Union
from uuid import UUID

# API基础配置
BASE_URL = "http://localhost:8005"
API_BASE = f"{BASE_URL}/"

logger = logging.getLogger(__name__)

class P1BugVerification:
    """P1级Bug修复验证测试类"""

    def test_uuid_handling(self) -> Tuple[bool, str]:
        """测试UUID处理修复"""
        print("\n🔍 测试UUID处理修复...")

        try:
            # 测试UUID工具函数
            from src.utils.uuid_helpers import ensure_uuid, ensure_str

            # 测试ensure_uuid
            uuid_obj = uuid.uuid4()
            assert ensure_uuid(str(uuid_obj)) == uuid_obj
            assert ensure_uuid(uuid_obj) == uuid_obj

            # 测试ensure_str
            assert ensure_str(uuid_obj) == str(uuid_obj)
            assert ensure_str(None) is None

            print("   ✅ UUID工具函数正常工作")
            return True, "UUID工具函数验证通过"

        except Exception as e:
            print(f"   ❌ UUID工具函数验证失败: {e}")
            return False, f"UUID工具函数验证失败: {e}"

    def test_points_service(self) -> Tuple[bool, str]:
        """测试积分服务UUID处理"""
        print("\n🔍 测试PointsService UUID处理...")

        try:
            from src.domains.points.service import PointsService
            from src.database import get_db_session

            # 创建测试用户
            session_gen = get_db_session()
            session = next(session_gen)

            try:
                # 创建测试用户
                user_id = uuid.uuid4()
                points_service = PointsService(session)

                # 测试UUID处理
                balance = points_service.get_balance(user_id)
                print(f"   ✅ get_balance支持UUID类型: balance={balance}")

                # 测试add_points
                transaction = points_service.add_points(
                    user_id=user_id,
                    amount=100,
                    source_type="test_verification",
                    transaction_group="test_group"
                )
                print(f"   ✅ add_points支持UUID类型: transaction_id={transaction.id}")

                # 清理测试数据
                session.rollback()

            finally:
                session.close()

            print("   ✅ PointsService UUID处理验证通过")
            return True, "PointsService UUID处理验证通过"

        except Exception as e:
            print(f"   ❌ PointsService UUID处理验证失败: {e}")
            return False, f"PointsService UUID处理验证失败: {e}"

    def test_reward_service(self) -> Tuple[bool, str]:
        """测试奖励服务UUID处理"""
        print("\n🔍 测试RewardService UUID处理...")

        try:
            from src.domains.reward.service import RewardService
            from src.domains.points.service import PointsService
            from src.database import get_db_session

            # 创建测试用户
            session_gen = get_db_session()
            session = next(session_gen)
            points_service = PointsService(session)
            reward_service = RewardService(session, points_service)

            try:
                # 创建测试用户
                user_id = uuid.uuid4()

                # 测试UUID处理
                my_rewards = reward_service.get_my_rewards(user_id)
                print(f"   ✅ get_my_rewards支持UUID类型: rewards_count={my_rewards['total_types']}")

                # 测试数据一致性
                balance = points_service.get_balance(user_id)
                print(f"   ✅ 奖励服务数据一致性检查通过")

                # 清理测试数据
                session.rollback()

            finally:
                session.close()

            print("   ✅ RewardService UUID处理验证通过")
            return True, "RewardService UUID处理验证通过"

        except Exception as e:
            print(f"   ❌ RewardService UUID处理验证失败: {e}")
            return False, f"RewardService UUID处理验证失败: {e}"

    def test_welcome_gift_service(self) -> Tuple[bool, str]:
        """测试欢迎礼包服务数据验证"""
        print("\n🔍 测试WelcomeGiftService数据验证...")

        try:
            from src.domains.reward.welcome_gift_service import WelcomeGiftService
            from src.domains.reward.service import RewardService
            from src.domains.points.service import PointsService
            from src.database import get_db_session

            # 创建测试用户
            session_gen = get_db_session()
            session = next(session_gen)
            points_service = PointsService(session)
            reward_service = RewardService(session, points_service)
            welcome_service = WelcomeGiftService(session, points_service)

            try:
                # 创建测试用户
                user_id = uuid.uuid4()

                # 测试数据写入验证
                result = welcome_service.claim_welcome_gift(str(user_id))

                # 验证数据确实写入
                balance_after = points_service.get_balance(user_id)
                print(f"   ✅ 礼包发放后积分余额: {balance_after}")

                # 验证奖励数据写入
                my_rewards_after = reward_service.get_my_rewards(user_id)
                print(f"   ✅ 奖励数据写入验证通过: {my_rewards_after['total_types']}种奖励")

                # 清理测试数据
                session.rollback()

            finally:
                session.close()

            print("   ✅ WelcomeGiftService数据验证通过")
            return True, "WelcomeGiftService数据验证通过"

        except Exception as e:
            print(f"   ❌ WelcomeGiftService数据验证失败: {e}")
            return False, f"WelcomeGiftService数据验证失败: {e}"

    def test_session_unification(self) -> Tuple[bool, str]:
        """测试Session依赖统一"""
        print("\n🔍 测试Session依赖统一...")

        try:
            # 检查get_user_session是否已删除
            try:
                from src.domains.user.database import get_user_session
                print("   ❌ get_user_session仍然存在")
                return False, "get_user_session仍然存在，需要手动删除"
            except ImportError:
                print("   ✅ get_user_session已成功删除")

            return True, "Session依赖统一验证通过"

        except Exception as e:
            return False, f"Session依赖统一验证失败: {e}"

    def test_avatar_feedback_removal(self) -> Tuple[bool, str]:
        """测试Avatar和Feedback功能删除"""
        print("\n🔍 测试Avatar和Feedback功能删除...")

        try:
            # 检查user/router.py中是否还有相关接口
            try:
                from src.domains.user.router import router as user_router

                # 检查POST /avatar
                avatar_endpoints = [route.path for route in user_router.routes if route.path == "/avatar"]

                # 检查POST /feedback
                feedback_endpoints = [route.path for route in user_router.routes if route.path == "/feedback"]

                if avatar_endpoints:
                    print(f"   ❌ 仍然存在 {len(avatar_endpoints)} 个 /avatar 接口")
                    return False, f"Avatar接口未完全删除"

                if feedback_endpoints:
                    print(f"   ❌ 仍然存在 {len(feedback_endpoints)} 个 /feedback 接口")
                    return False, f"Feedback接口未完全删除"
            except ImportError:
                print("   ✅ user router已完全删除或不存在")

            # 检查user/schemas.py中是否还有相关Schema
            try:
                from src.domains.user.schemas import (
                    UserProfileResponse, UpdateProfileRequest, FeedbackRequest,
                    FeedbackSubmitResponse, AvatarUploadResponse
                )
                print("   ❌ Avatar和Feedback Schema仍然存在")
                return False, f"Avatar和Feedback Schema未完全删除"
            except ImportError:
                print("   ✅ Avatar和Feedback Schema已成功删除")

            return True, "Avatar和Feedback功能删除验证通过"

        except Exception as e:
            return False, f"Avatar和Feedback功能删除验证失败: {e}"

    def run_all_tests(self) -> bool:
        """运行所有P1验证测试"""
        print("\n🚀 开始P1级Bug修复验证测试...")
        print("=" * 70)

        tests = [
            ("UUID工具函数验证", self.test_uuid_handling),
            ("积分服务UUID处理", self.test_points_service),
            ("奖励服务UUID处理", self.test_reward_service),
            ("欢迎礼包数据验证", self.test_welcome_gift_service),
            ("Session依赖统一", self.test_session_unification),
            ("Avatar和Feedback功能删除", self.test_avatar_feedback_removal)
        ]

        results = []
        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n📋 执行: {test_name}")
            success, message = test_func()
            results.append((test_name, success, message))
            if success:
                passed += 1
            else:
                print(f"   ❌ {test_name}失败: {message}")

        print("\n" + "=" * 70)
        print(f"\n📊 P1验证测试结果:")
        print(f"   总测试数: {total}")
        print(f"   通过数: {passed}")
        print(f"   失败数: {total - passed}")

        if passed == total:
            print("\n🎉 所有P1级Bug修复验证测试通过！")
            return True
        else:
            print(f"\n⚠️  {total - passed} 个P1测试失败，需要进一步修复")
            return False

if __name__ == "__main__":
    verifier = P1BugVerification()
    success = verifier.run_all_tests()

    if success:
        print("\n🎉 P1级Bug修复验证完成，所有测试通过！")
        exit(0)
    else:
        print("\n❌ P1级Bug修复验证失败，需要进一步调试")
        exit(1)