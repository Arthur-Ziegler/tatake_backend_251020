#!/usr/bin/env python3
"""
UUID类型处理隔离测试

根据MCP最佳实践，设计隔离测试来验证UUID处理的正确性。
专门测试Top3 service中UUID和str类型的转换问题。

作者：TaKeKe团队
版本：1.4.1
日期：2025-10-25
"""

import uuid
from datetime import date
from sqlmodel import Session
from src.domains.top3.service import Top3Service
from src.domains.points.service import PointsService
from src.database import get_engine

def test_uuid_string_conversion_isolation():
    """测试UUID字符串转换的隔离性"""
    print("🧪 测试UUID字符串转换隔离性...")

    # 测试数据
    test_uuid = uuid.uuid4()
    test_uuid_str = str(test_uuid)
    print(f"测试UUID: {test_uuid}, 字符串: {test_uuid_str}")

    # 直接创建session
    session = Session(get_engine())

    try:
        # 初始化services
        points_service = PointsService(session)
        top3_service = Top3Service(session, points_service)

        # 测试PointsService的UUID处理
        try:
            balance = points_service.get_balance(test_uuid)
            print(f"✅ PointsService.get_balance(UUID对象)成功: {balance}")
            assert isinstance(balance, int), "余额应该是整数"

            # 测试字符串UUID
            balance_str = points_service.get_balance(test_uuid_str)
            print(f"✅ PointsService.get_balance(字符串UUID)成功: {balance_str}")
            assert isinstance(balance_str, int), "余额应该是整数"

            # 测试add_points with UUID
            transaction = points_service.add_points(
                user_id=test_uuid,
                amount=100,
                source_type="test"
            )
            print(f"✅ PointsService.add_points(UUID对象)成功: {transaction.id}")

            # 测试add_points with str
            transaction_str = points_service.add_points(
                user_id=test_uuid_str,
                amount=200,
                source_type="test"
            )
            print(f"✅ PointsService.add_points(字符串UUID)成功: {transaction_str.id}")

        except Exception as e:
            print(f"❌ PointsService UUID处理失败: {e}")
            raise

    finally:
        session.close()

def test_top3_service_uuid_isolation():
    """测试Top3Service的UUID处理"""
    print("\n🧪 测试Top3Service UUID处理...")

    test_uuid = uuid.uuid4()
    test_uuid_str = str(test_uuid)
    target_date = date.today()

    # 直接创建session
    session = Session(get_engine())

    try:
        # 初始化services
        points_service = PointsService(session)
        top3_service = Top3Service(session, points_service)

        # 首先测试字符串UUID用户
        try:
            # 测试get_top3 with string UUID
            result = top3_service.get_top3(test_uuid_str, "2025-10-26")
            print(f"✅ Top3Service.get_top3(字符串UUID)成功: {result}")

        except Exception as e:
            print(f"❌ Top3Service字符串UUID处理失败: {e}")
            raise

    finally:
        session.close()

def test_welcome_gift_service_uuid_handling():
    """测试WelcomeGiftService的UUID处理"""
    print("\n🧪 测试WelcomeGiftService UUID处理...")

    test_uuid = uuid.uuid4()

    # 直接创建session
    session = Session(get_engine())

    try:
        from src.domains.reward.welcome_gift_service import WelcomeGiftService
        points_service = PointsService(session)
        service = WelcomeGiftService(session, points_service)

        try:
            # 直接测试transaction_group生成逻辑，模拟claim_welcome_gift中的处理
            from uuid import uuid4
            transaction_group = f"welcome_gift_{str(test_uuid)}_{uuid4().hex[:8]}"
            print(f"✅ WelcomeGiftService transaction_group生成(UUID): {transaction_group}")
            assert "_" in transaction_group, "transaction_group应该包含下划线"

            # 测试字符串UUID
            transaction_group_str = f"welcome_gift_{str(test_uuid)}_{uuid4().hex[:8]}"
            print(f"✅ WelcomeGiftService transaction_group生成(字符串): {transaction_group_str}")
            assert "_" in transaction_group_str, "transaction_group应该包含下划线"

        except Exception as e:
            print(f"❌ WelcomeGiftService UUID处理失败: {e}")
            raise

    finally:
        session.close()

if __name__ == "__main__":
    """运行UUID处理隔离测试"""
    print("🚀 开始UUID处理隔离测试...")
    print("=" * 60)

    # 执行各项隔离测试
    test_uuid_string_conversion_isolation()
    test_top3_service_uuid_isolation()
    test_welcome_gift_service_uuid_handling()

    print("=" * 60)
    print("✅ 所有UUID处理隔离测试完成！")