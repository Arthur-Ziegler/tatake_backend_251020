"""
聊天工具测试运行器

运行所有聊天工具测试套件，包括：
1. 基础工具测试
2. CRUD工具测试
3. 搜索工具测试
4. 批量工具测试
5. 集成测试

使用方法：
python -m tests.domains.chat.run_all_tests

或者：
uv run python -m tests.domains.chat.run_all_tests

作者：TaKeKe团队
版本：1.0.0
"""

import sys
import os
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('chat_tools_test_results.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()

    def run_test_module(self, module_name: str, test_class_name: str) -> Dict[str, Any]:
        """运行单个测试模块"""
        logger.info(f"🔄 开始运行测试模块: {module_name}.{test_class_name}")

        try:
            # 动态导入测试模块
            module = __import__(module_name, fromlist=[test_class_name])
            test_class = getattr(module, test_class_name)

            # 实例化测试类
            test_instance = test_class()

            # 获取所有测试方法
            test_methods = [
                method for method in dir(test_instance)
                if method.startswith('test_') and callable(getattr(test_instance, method))
            ]

            passed_tests = 0
            failed_tests = []
            total_tests = len(test_methods)

            # 运行每个测试方法
            for method_name in test_methods:
                try:
                    method = getattr(test_instance, method_name)
                    method()
                    passed_tests += 1
                    logger.info(f"✅ {method_name} 通过")

                except Exception as e:
                    failed_tests.append({
                        'method': method_name,
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    })
                    logger.error(f"❌ {method_name} 失败: {e}")

            # 计算结果
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

            result = {
                'module': module_name,
                'class': test_class_name,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': len(failed_tests),
                'success_rate': success_rate,
                'failed_details': failed_tests,
                'status': 'PASSED' if len(failed_tests) == 0 else 'FAILED'
            }

            logger.info(f"📊 {module_name} 结果: {passed_tests}/{total_tests} 通过 ({success_rate:.1f}%)")

            return result

        except Exception as e:
            logger.error(f"💥 测试模块 {module_name} 运行失败: {e}")
            return {
                'module': module_name,
                'class': test_class_name,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 1,
                'success_rate': 0.0,
                'failed_details': [{'error': str(e), 'traceback': traceback.format_exc()}],
                'status': 'CRASHED'
            }

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("🚀 开始运行聊天工具完整测试套件")

        # 测试模块配置
        test_modules = [
            ('tests.domains.chat.test_chat_tools_basic', 'TestBasicTools'),
            ('tests.domains.chat.test_task_crud', 'TestTaskCrudTools'),
            ('tests.domains.chat.test_task_search', 'TestSearchTasks'),
            ('tests.domains.chat.test_task_batch', 'TestBatchCreateSubtasks'),
            ('tests.domains.chat.test_chat_tools_integration', 'TestCompleteWorkflow'),
            ('tests.domains.chat.test_chat_tools_integration', 'TestToolChaining'),
            ('tests.domains.chat.test_chat_tools_integration', 'TestErrorHandlingAndRecovery'),
            ('tests.domains.chat.test_chat_tools_integration', 'TestPerformanceIntegration'),
            ('tests.domains.chat.test_chat_tools_integration', 'TestRealWorldScenarios'),
            ('tests.domains.chat.test_chat_tools_integration', 'TestLangGraphIntegration')
        ]

        # 运行所有测试模块
        for module_name, class_name in test_modules:
            result = self.run_test_module(module_name, class_name)
            self.test_results.append(result)

            # 如果有测试失败，打印详细信息
            if result['failed_tests'] > 0:
                logger.error(f"❌ {module_name} 失败详情:")
                for failed in result['failed_details']:
                    method_name = failed.get('method', '未知方法')
                    error_msg = failed.get('error', '未知错误')
                    logger.error(f"   - {method_name}: {error_msg}")

        # 生成总体报告
        return self.generate_summary_report()

    def generate_summary_report(self) -> Dict[str, Any]:
        """生成测试总结报告"""
        total_modules = len(self.test_results)
        total_tests = sum(result['total_tests'] for result in self.test_results)
        total_passed = sum(result['passed_tests'] for result in self.test_results)
        total_failed = sum(result['failed_tests'] for result in self.test_results)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        passed_modules = sum(1 for result in self.test_results if result['status'] == 'PASSED')
        failed_modules = sum(1 for result in self.test_results if result['status'] == 'FAILED')
        crashed_modules = sum(1 for result in self.test_results if result['status'] == 'CRASHED')

        execution_time = datetime.now() - self.start_time

        summary = {
            'execution_info': {
                'start_time': self.start_time.isoformat(),
                'execution_time_seconds': execution_time.total_seconds(),
                'execution_time_formatted': str(execution_time).split('.')[0]
            },
            'module_summary': {
                'total_modules': total_modules,
                'passed_modules': passed_modules,
                'failed_modules': failed_modules,
                'crashed_modules': crashed_modules
            },
            'test_summary': {
                'total_tests': total_tests,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'overall_success_rate': overall_success_rate
            },
            'detailed_results': self.test_results,
            'overall_status': 'PASSED' if total_failed == 0 else 'FAILED'
        }

        return summary

    def print_summary_report(self, summary: Dict[str, Any]):
        """打印测试总结报告"""
        print("\n" + "="*80)
        print("🎯 聊天工具测试套件总结报告")
        print("="*80)

        # 执行信息
        exec_info = summary['execution_info']
        print(f"⏰ 执行时间: {exec_info['execution_time_formatted']}")
        print(f"🚀 开始时间: {exec_info['start_time'][:19]}")

        # 模块统计
        module_summary = summary['module_summary']
        print(f"\n📋 模块统计:")
        print(f"   总模块数: {module_summary['total_modules']}")
        print(f"   通过模块: {module_summary['passed_modules']} ✅")
        print(f"   失败模块: {module_summary['failed_modules']} ❌")
        print(f"   崩溃模块: {module_summary['crashed_modules']} 💥")

        # 测试统计
        test_summary = summary['test_summary']
        print(f"\n🧪 测试统计:")
        print(f"   总测试数: {test_summary['total_tests']}")
        print(f"   通过测试: {test_summary['total_passed']} ✅")
        print(f"   失败测试: {test_summary['total_failed']} ❌")
        print(f"   成功率: {test_summary['overall_success_rate']:.1f}%")

        # 详细结果
        print(f"\n📊 详细结果:")
        for result in summary['detailed_results']:
            status_emoji = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"   {status_emoji} {result['module']}: "
                  f"{result['passed_tests']}/{result['total_tests']} "
                  f"({result['success_rate']:.1f}%)")

        # 整体状态
        overall_status = summary['overall_status']
        status_emoji = "🎉" if overall_status == 'PASSED' else "❌"
        status_text = "所有测试通过" if overall_status == 'PASSED' else "存在测试失败"

        print(f"\n{status_emoji} 整体状态: {status_text}")
        print("="*80)

        # 保存详细报告到文件
        report_file = "chat_tools_test_report.json"
        try:
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"📄 详细报告已保存到: {report_file}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")


def main():
    """主函数"""
    runner = TestRunner()

    try:
        # 运行所有测试
        summary = runner.run_all_tests()

        # 打印总结报告
        runner.print_summary_report(summary)

        # 返回适当的退出码
        if summary['overall_status'] == 'PASSED':
            logger.info("🎉 所有聊天工具测试通过！")
            return 0
        else:
            logger.error("❌ 存在测试失败！")
            return 1

    except Exception as e:
        logger.error(f"💥 测试运行器崩溃: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)