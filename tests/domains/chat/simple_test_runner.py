"""
简化的UltraThink测试运行器

运行已验证工作的测试组件，生成基本报告。
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# 导入已验证工作的组件
from tests.domains.chat.test_chat_tools_ultrathink import run_ultrathink_enhanced_tests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleTestRunner:
    """简化的测试运行器"""

    def __init__(self, output_dir: str = "tests/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"🚀 简化测试运行器已初始化，输出目录: {self.output_dir}")

    async def run_enhanced_tests_only(self):
        """只运行增强测试"""
        logger.info("🤖 开始运行UltraThink增强测试...")
        start_time = time.time()

        try:
            # 运行增强测试
            results = await run_ultrathink_enhanced_tests()

            duration = time.time() - start_time

            # 生成简单报告
            report = {
                "suite_name": "UltraThink增强聊天工具测试套件",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "total_duration": duration,
                "test_results": results,
                "summary": {
                    "ultrathink_enabled": bool(os.getenv('ULTRATHINK_API_KEY')),
                    "status": "completed"
                }
            }

            # 保存报告
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            report_file = self.output_dir / f"enhanced_test_report_{timestamp}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📄 测试报告已保存: {report_file}")
            logger.info("✅ UltraThink增强测试完成")

            return report

        except Exception as e:
            logger.error(f"❌ 测试执行失败: {e}")
            raise


async def main():
    """主函数"""
    runner = SimpleTestRunner()
    await runner.run_enhanced_tests_only()


if __name__ == "__main__":
    asyncio.run(main())