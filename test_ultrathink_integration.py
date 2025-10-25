#!/usr/bin/env python3
"""
UltraThink集成测试脚本

测试UltraThink大模型集成和LLM响应模拟器的功能
"""

import asyncio
import logging
import os
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
import sys
sys.path.insert(0, str(project_root))

# 导入我们的模块
from tests.domains.chat.ultrathink_lm_integrator import (
    UltraThinkConfig,
    UltraThinkLMIntegrator,
    create_ultrathink_integrator,
    quick_ultrathink_call
)
from tests.domains.chat.llm_response_simulator import (
    LLMResponseSimulator,
    SimulationConfig,
    ResponseComplexity,
    ResponseStyle,
    create_simple_simulator,
    create_complex_simulator
)


async def test_ultrathink_integrator():
    """测试UltraThink集成器"""
    logger.info("🧪 开始测试UltraThink集成器...")

    try:
        # 创建集成器
        config = UltraThinkConfig(
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_tokens=1000
        )

        async with UltraThinkLMIntegrator(config) as integrator:
            # 测试连接
            logger.info("🔗 测试API连接...")
            connection_ok = await integrator.test_connection()
            logger.info(f"连接测试结果: {'✅ 成功' if connection_ok else '❌ 失败'}")

            if connection_ok:
                # 测试工具验证
                logger.info("🔧 测试工具验证...")
                validation_prompt = """
                请验证以下工具响应是否符合预期：

                工具名称：calculator
                工具响应：{"success": true, "data": "15", "timestamp": "2024-01-01T00:00:00Z"}

                请分析响应格式的正确性和数据的有效性。
                """

                response = await integrator.call_ultrathink(validation_prompt)
                logger.info(f"验证响应: {response.content[:200]}...")

                # 获取使用统计
                stats = integrator.get_usage_stats()
                logger.info(f"📊 使用统计: {stats}")

    except Exception as e:
        logger.error(f"❌ UltraThink集成器测试失败: {e}")
        return False

    return True


async def test_response_simulator():
    """测试响应模拟器"""
    logger.info("🎭 开始测试LLM响应模拟器...")

    try:
        # 创建简单模拟器
        simulator = create_simple_simulator()

        # 测试工具验证响应
        logger.info("🔧 测试工具验证响应...")
        validation_response = await simulator.simulate_tool_validation_response(
            tool_name="calculator",
            tool_response='{"success": true, "data": "15", "timestamp": "2024-01-01T00:00:00Z"}',
            is_success=True
        )
        logger.info(f"工具验证响应: {validation_response.content[:100]}...")

        # 测试查询理解响应
        logger.info("🔍 测试查询理解响应...")
        search_results = [
            {"id": "1", "title": "编程任务", "status": "pending"},
            {"id": "2", "title": "数据分析", "status": "completed"}
        ]
        query_response = await simulator.simulate_query_understanding_response(
            query="编程相关任务",
            search_results=search_results,
            filters_applied=["status=pending"]
        )
        logger.info(f"查询理解响应: {query_response.content[:100]}...")

        # 测试错误恢复响应
        logger.info("🛠️ 测试错误恢复响应...")
        error_response = await simulator.simulate_error_recovery_response(
            error_type="网络连接超时",
            recovery_action="重试连接",
            success=True
        )
        logger.info(f"错误恢复响应: {error_response.content[:100]}...")

        # 测试多工具链响应
        logger.info("🔗 测试多工具链响应...")
        tool_chain = [
            {"tool": "create_task", "success": True, "response_time": 1.2},
            {"tool": "get_task_detail", "success": True, "response_time": 0.8},
            {"tool": "update_task", "success": True, "response_time": 1.0}
        ]
        chain_response = await simulator.simulate_multi_tool_chain_response(
            tool_chain=tool_chain,
            overall_success=True
        )
        logger.info(f"多工具链响应: {chain_response.content[:100]}...")

        # 获取历史记录
        history = simulator.get_history()
        logger.info(f"📚 模拟器历史记录数量: {len(history)}")

    except Exception as e:
        logger.error(f"❌ 响应模拟器测试失败: {e}")
        return False

    return True


async def test_combined_functionality():
    """测试组合功能"""
    logger.info("🔄 开始测试组合功能...")

    try:
        # 创建复杂模拟器
        simulator = create_complex_simulator()

        # 模拟真实场景：工具调用 + 验证
        logger.info("🎯 模拟真实测试场景...")

        # 1. 模拟工具执行
        tool_response = '{"success": true, "data": {"task_id": "123"}, "timestamp": "2024-01-01T00:00:00Z"}'

        # 2. 模拟器生成验证响应
        mock_validation = await simulator.simulate_tool_validation_response(
            tool_name="create_task",
            tool_response=tool_response,
            is_success=True
        )

        logger.info(f"🔍 模拟验证结果: {mock_validation.analysis}")
        logger.info(f"💡 生成建议: {mock_validation.suggestions}")

        # 3. 如果有真实的UltraThink API，可以进行对比
        if os.getenv('ULTRATHINK_API_KEY'):
            logger.info("🤖 使用真实UltraThink进行对比测试...")
            try:
                real_validation = await quick_ultrathink_call(
                    f"请验证这个工具响应的质量：{tool_response}",
                    context="这是一个创建任务的工具响应"
                )
                logger.info(f"🤖 真实验证结果: {real_validation[:100]}...")
            except Exception as e:
                logger.warning(f"⚠️ 真实API调用失败: {e}")
        else:
            logger.info("ℹ️ 未配置ULTRATHINK_API_KEY，跳过真实API测试")

    except Exception as e:
        logger.error(f"❌ 组合功能测试失败: {e}")
        return False

    return True


async def main():
    """主测试函数"""
    logger.info("🚀 开始UltraThink增强测试系统集成测试...")

    test_results = {}

    # 测试UltraThink集成器
    test_results['ultrathink_integrator'] = await test_ultrathink_integrator()

    # 测试响应模拟器
    test_results['response_simulator'] = await test_response_simulator()

    # 测试组合功能
    test_results['combined_functionality'] = await test_combined_functionality()

    # 总结测试结果
    logger.info("\n" + "="*60)
    logger.info("📊 测试结果总结:")
    logger.info("="*60)

    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")

    passed_tests = sum(test_results.values())
    total_tests = len(test_results)

    logger.info(f"\n总计: {passed_tests}/{total_tests} 测试通过")

    if passed_tests == total_tests:
        logger.info("🎉 所有测试通过！UltraThink增强测试系统就绪。")
        return True
    else:
        logger.error("💥 部分测试失败，请检查配置和实现。")
        return False


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    exit(0 if success else 1)