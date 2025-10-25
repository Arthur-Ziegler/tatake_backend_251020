#!/usr/bin/env python3
"""
UUID类型处理隔离测试

根据MCP最佳实践，设计隔离测试来验证UUID处理的正确性。
专门测试Top3 service中UUID和str类型的转换问题。

作者：TaKeKe团队
版本：1.4.1
日期：2025-10-25
"""

import pytest
import uuid
from datetime import date
from sqlmodel import Session
from src.domains.top3.service import Top3Service
from src.domains.top3.models import TaskTop3
from src.domains.points.service import PointsService
from src.database import get_db_session as get_test_session

class TestUUIDHandling:
    """UUID处理隔离测试类"""

    def test_uuid_string_conversion_isolation(self):
        """测试UUID字符串转换的隔离性"""
        # 测试数据
        test_uuid = uuid.uuid4()
        test_uuid_str = str(test_uuid)
        print(f"测试UUID: {test_uuid}, 字符串: {test_uuid_str}")

        # 直接创建session，不使用上下文管理器
        from src.database import get_db_engine
        from sqlmodel import Session
        session = Session(get_db_engine())

        # 初始化services
        points_service = PointsService(session)
        top3_service = Top3Service(session, points_service)

        # 测试PointsService的UUID处理
        """测试UUID字符串转换的隔离性"""
        # 测试数据
        test_uuid = uuid.uuid4()
        test_uuid_str = str(test_uuid)

        # 直接创建session，不使用上下文管理器
        from src.database import get_db_engine
        from sqlmodel import Session
        session = Session(get_db_engine())

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

    def test_top3_service_uuid_isolation(self):
        """测试Top3Service的UUID处理"""
        test_uuid = uuid.uuid4()
        test_uuid_str = str(test_uuid)
        target_date = date.today()

        # 直接创建session，不使用上下文管理器
        from src.database import get_db_engine
        from sqlmodel import Session
        session = Session(get_db_engine())

        # 初始化services
        points_service = PointsService(session)
        top3_service = Top3Service(session, points_service)

        # 创建测试任务
        task_ids = [str(uuid.uuid4()) for _ in range(3)]

        # 首先测试字符串UUID用户
            try:
                # 测试get_top3 with string UUID
                result = top3_service.get_top3(test_uuid_str, target_date)
                print(f"✅ Top3Service.get_top3(字符串UUID)成功: {result}")

                # 测试is_task_in_today_top3 with string UUID
                is_in_top3 = top3_service.is_task_in_today_top3(test_uuid_str, task_ids[0])
                print(f"✅ Top3Service.is_task_in_today_top3(字符串UUID)成功: {is_in_top3}")

            except Exception as e:
                print(f"❌ Top3Service字符串UUID处理失败: {e}")
                raise
        """测试Top3Service的UUID处理"""
        test_uuid = uuid.uuid4()
        test_uuid_str = str(test_uuid)
        target_date = date.today()

        with get_test_session() as session:
            points_service = PointsService(session)
            top3_service = Top3Service(session, points_service)

            # 创建测试任务
            task_ids = [str(uuid.uuid4()) for _ in range(3)]

            # 首先测试字符串UUID用户
            try:
                # 测试get_top3 with string UUID
                result = top3_service.get_top3(test_uuid_str, target_date)
                print(f"✅ Top3Service.get_top3(字符串UUID)成功: {result}")

                # 测试is_task_in_today_top3 with string UUID
                is_in_top3 = top3_service.is_task_in_today_top3(test_uuid_str, task_ids[0])
                print(f"✅ Top3Service.is_task_in_today_top3(字符串UUID)成功: {is_in_top3}")

            except Exception as e:
                print(f"❌ Top3Service字符串UUID处理失败: {e}")
                raise

    def test_repository_layer_uuid_handling(self):
        """测试Repository层的UUID处理"""
        test_uuid = uuid.uuid4()
        target_date = date.today()

        with get_test_session() as session:
            from src.domains.top3.repository import Top3Repository
            repo = Top3Repository(session)

            try:
                # 测试repository的UUID处理
                result = repo.get_by_user_and_date(test_uuid, target_date)
                print(f"✅ Repository.get_by_user_and_date(UUID对象)成功: {result}")

                # 测试repository的字符串UUID处理
                result_str = repo.get_by_user_and_date(str(test_uuid), target_date)
                print(f"✅ Repository.get_by_user_and_date(字符串UUID)成功: {result_str}")

            except Exception as e:
                print(f"❌ Repository UUID处理失败: {e}")
                raise

    def test_welcome_gift_service_uuid_handling(self):
        """测试WelcomeGiftService的UUID处理"""
        test_uuid = uuid.uuid4()

        with get_test_session() as session:
            from src.domains.reward.welcome_gift_service import WelcomeGiftService
            service = WelcomeGiftService(session)

            try:
                # 测试generate_transaction_group方法
                transaction_group = service._WelcomeGiftService__generate_transaction_group(test_uuid)
                print(f"✅ WelcomeGiftService transaction_group生成(UUID): {transaction_group}")
                assert "_" in transaction_group, "transaction_group应该包含下划线"

                # 测试字符串UUID
                transaction_group_str = service._WelcomeGiftService__generate_transaction_group(str(test_uuid))
                print(f"✅ WelcomeGiftService transaction_group生成(字符串): {transaction_group_str}")
                assert "_" in transaction_group_str, "transaction_group应该包含下划线"

            except Exception as e:
                print(f"❌ WelcomeGiftService UUID处理失败: {e}")
                raise

if __name__ == "__main__":
    """运行UUID处理隔离测试"""
    test_instance = TestUUIDHandling()

    print("🧪 开始UUID处理隔离测试...")
    print("=" * 60)

    # 执行各项隔离测试
    test_instance.test_uuid_string_conversion_isolation()
    test_instance.test_top3_service_uuid_isolation()
    test_instance.test_repository_layer_uuid_handling()
    test_instance.test_welcome_gift_service_uuid_handling()

    print("=" * 60)
    print("✅ 所有UUID处理隔离测试通过！")