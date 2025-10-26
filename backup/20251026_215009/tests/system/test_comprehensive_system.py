"""
全面系统测试

运行所有系统测试，验证系统关键功能的完整性和一致性。

测试覆盖：
1. 任务缓存问题修复验证
2. 永久防刷机制验证
3. API响应格式统一验证
4. 数据一致性验证

作者：TaTakeKe团队
版本：v1.0
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from tests.system.tests.test_task_cache_fix import TestTaskCacheFix
from tests.system.tests.test_permanent_anti_spam import TestPermanentAntiSpam
from tests.system.tests.test_api_response_format import TestApiResponseFormat
from tests.system.tests.test_data_consistency import TestDataConsistency
from tests.system.conftest import print_test_header, print_success, print_error


class TestComprehensiveSystem:
    """全面系统测试类"""

    def test_all_system_fixes(self, authenticated_client):
        """
        运行所有系统测试

        验证所有关键修复：任务缓存、永久防刷、API格式、数据一致性。
        """
        print("\n" + "=" * 60)
        print("🚀 开始全面系统测试...")
        print("=" * 60)

        test_results = []

        # 实例化测试类
        cache_fix_test = TestTaskCacheFix()
        anti_spam_test = TestPermanentAntiSpam()
        api_format_test = TestApiResponseFormat()
        data_consistency_test = TestDataConsistency()

        # 测试1：任务缓存问题修复验证
        print("\n📋 测试1: 任务缓存问题修复验证")
        print("-" * 40)
        cache_test_result = cache_fix_test.test_task_cache_data_synchronization(authenticated_client)
        test_results.append(("任务缓存修复", cache_test_result))

        # 测试2：永久防刷机制验证
        print("\n📋 测试2: 永久防刷机制验证")
        print("-" * 40)
        anti_spam_test_result = anti_spam_test.test_permanent_anti_spam_mechanism(authenticated_client)
        test_results.append(("永久防刷机制", anti_spam_test_result))

        # 测试3：API响应格式统一验证
        print("\n📋 测试3: API响应格式统一验证")
        print("-" * 40)
        api_format_test_result = api_format_test.test_points_api_response_format(authenticated_client)
        test_results.append(("API响应格式", api_format_test_result))

        # 测试4：数据一致性验证
        print("\n📋 测试4: 数据一致性验证")
        print("-" * 40)
        consistency_test_result = data_consistency_test.test_api_database_data_consistency(authenticated_client)
        test_results.append(("数据一致性", consistency_test_result))

        # 总结测试结果
        print("\n" + "=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)

        passed = 0
        total = len(test_results)

        for test_name, result in test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status} {test_name}")
            if result:
                passed += 1

        print(f"\n总计: {passed}/{total} 测试通过")

        if passed == total:
            print("🎉 所有系统测试通过！")
            print("\n✅ 修复内容总结:")
            print("1. 任务缓存问题：Repository层添加commit()调用")
            print("2. 永久防刷机制：基于last_claimed_date的一次性奖励检查")
            print("3. API响应格式：积分API使用标准响应格式")
            print("4. 数据一致性：事务正确提交，数据实时同步")
            return True
        else:
            print("❌ 部分测试失败，需要进一步修复")
            return False


if __name__ == "__main__":
    # 独立运行时的入口
    pytest.main([__file__, "-v"])