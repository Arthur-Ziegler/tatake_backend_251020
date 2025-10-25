#!/usr/bin/env python3
"""
增强型测试系统实现

这是一个工程化的测试系统，专门针对运行时错误和API参数问题。
实现了多层次测试架构，确保类似BUG不会再出现。

作者：Claude AI Assistant
版本：1.0.0
"""

import os
import sys
import json
import inspect
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """测试状态枚举"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    status: TestStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None


class OpenAPIComplianceTest:
    """OpenAPI规范合规性测试"""

    def __init__(self, app):
        self.app = app

    def test_no_args_kwargs_parameters(self) -> TestResult:
        """确保所有接口都没有args/kwargs参数"""
        try:
            openapi_schema = self.app.openapi()
            violations = []

            for path, path_item in openapi_schema.get("paths", {}).items():
                for method, operation in path_item.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                        # 检查参数
                        params = operation.get("parameters", [])
                        for param in params:
                            param_name = param.get("name", "")
                            if param_name in ["args", "kwargs"]:
                                violations.append({
                                    "path": path,
                                    "method": method,
                                    "param_name": param_name,
                                    "location": param.get("in", "unknown")
                                })

                        # 检查请求体
                        request_body = operation.get("requestBody", {})
                        if request_body:
                            content = request_body.get("content", {})
                            for content_type, content_info in content.items():
                                schema = content_info.get("schema", {})
                                properties = schema.get("properties", {})
                                for prop_name in properties:
                                    if prop_name in ["args", "kwargs"]:
                                        violations.append({
                                            "path": path,
                                            "method": method,
                                            "param_name": prop_name,
                                            "location": "request_body",
                                            "content_type": content_type
                                        })

            if violations:
                return TestResult(
                    test_name="test_no_args_kwargs_parameters",
                    status=TestStatus.FAILED,
                    message=f"发现 {len(violations)} 个args/kwargs参数违规",
                    details={"violations": violations}
                )
            else:
                return TestResult(
                    test_name="test_no_args_kwargs_parameters",
                    status=TestStatus.PASSED,
                    message="所有接口都没有args/kwargs参数"
                )

        except Exception as e:
            return TestResult(
                test_name="test_no_args_kwargs_parameters",
                status=TestStatus.ERROR,
                message=f"测试执行失败: {str(e)}"
            )

    def test_parameter_consistency(self) -> TestResult:
        """确保参数定义的一致性"""
        try:
            openapi_schema = self.app.openapi()
            issues = []

            for path, path_item in openapi_schema.get("paths", {}).items():
                for method, operation in path_item.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                        # 检查参数定义的一致性
                        params = operation.get("parameters", [])
                        for param in params:
                            param_name = param.get("name", "")
                            param_type = param.get("schema", {}).get("type", "")
                            param_required = param.get("required", False)

                            # 检查参数名格式
                            if not param_name.isidentifier() and not param_name.startswith("$"):
                                issues.append({
                                    "path": path,
                                    "method": method,
                                    "issue": "参数名格式不正确",
                                    "param_name": param_name
                                })

                            # 检查必需参数的类型定义
                            if param_required and not param_type:
                                issues.append({
                                    "path": path,
                                    "method": method,
                                    "issue": "必需参数缺少类型定义",
                                    "param_name": param_name
                                })

            if issues:
                return TestResult(
                    test_name="test_parameter_consistency",
                    status=TestStatus.FAILED,
                    message=f"发现 {len(issues)} 个参数一致性问题",
                    details={"issues": issues}
                )
            else:
                return TestResult(
                    test_name="test_parameter_consistency",
                    status=TestStatus.PASSED,
                    message="所有参数定义都是一致的"
                )

        except Exception as e:
            return TestResult(
                test_name="test_parameter_consistency",
                status=TestStatus.ERROR,
                message=f"测试执行失败: {str(e)}"
            )


class DependencyInjectionTest:
    """FastAPI依赖注入系统测试"""

    def __init__(self, app):
        self.app = app

    def test_dependency_resolution(self) -> TestResult:
        """测试依赖解析的正确性"""
        try:
            from fastapi.routing import APIRoute
            issues = []

            for route in self.app.routes:
                if isinstance(route, APIRoute):
                    # 检查路由的依赖定义
                    sig = inspect.signature(route.endpoint)

                    for param_name, param in sig.parameters.items():
                        # 检查是否有未解析的依赖
                        if "Depends" in str(param.annotation):
                            try:
                                # 尝试获取依赖信息
                                if hasattr(param, 'default') and hasattr(param.default, 'dependency'):
                                    dependency = param.default.dependency
                                    if dependency is None:
                                        issues.append({
                                            "path": route.path,
                                            "method": list(route.methods)[0] if route.methods else "unknown",
                                            "param_name": param_name,
                                            "issue": "依赖解析为None"
                                        })
                            except Exception as e:
                                issues.append({
                                    "path": route.path,
                                    "method": list(route.methods)[0] if route.methods else "unknown",
                                    "param_name": param_name,
                                    "issue": f"依赖解析失败: {str(e)}"
                                })

            if issues:
                return TestResult(
                    test_name="test_dependency_resolution",
                    status=TestStatus.FAILED,
                    message=f"发现 {len(issues)} 个依赖解析问题",
                    details={"issues": issues}
                )
            else:
                return TestResult(
                    test_name="test_dependency_resolution",
                    status=TestStatus.PASSED,
                    message="所有依赖都能正确解析"
                )

        except Exception as e:
            return TestResult(
                test_name="test_dependency_resolution",
                status=TestStatus.ERROR,
                message=f"测试执行失败: {str(e)}"
            )

    def test_parameter_ordering(self) -> TestResult:
        """测试参数顺序的正确性"""
        try:
            from fastapi.routing import APIRoute
            issues = []

            for route in self.app.routes:
                if isinstance(route, APIRoute):
                    sig = inspect.signature(route.endpoint)
                    params = list(sig.parameters.values())

                    # 检查参数顺序：非默认参数不能在默认参数之后
                    found_default = False
                    for param in params:
                        has_default = param.default != inspect.Parameter.empty

                        if has_default:
                            found_default = True
                        elif found_default:
                            # 非默认参数在默认参数之后
                            issues.append({
                                "path": route.path,
                                "method": list(route.methods)[0] if route.methods else "unknown",
                                "param_name": param.name,
                                "issue": "非默认参数在默认参数之后"
                            })

            if issues:
                return TestResult(
                    test_name="test_parameter_ordering",
                    status=TestStatus.FAILED,
                    message=f"发现 {len(issues)} 个参数顺序问题",
                    details={"issues": issues}
                )
            else:
                return TestResult(
                    test_name="test_parameter_ordering",
                    status=TestStatus.PASSED,
                    message="所有参数顺序都是正确的"
                )

        except Exception as e:
            return TestResult(
                test_name="test_parameter_ordering",
                status=TestStatus.ERROR,
                message=f"测试执行失败: {str(e)}"
            )


class RuntimeErrorTest:
    """运行时错误检测测试"""

    def test_langgraph_type_safety(self) -> TestResult:
        """LangGraph类型安全测试"""
        try:
            # 设置测试环境
            os.environ.setdefault("OPENAI_API_KEY", "test-key")
            os.environ.setdefault("CHAT_DB_PATH", "data/test_chat_type_safety.db")

            from src.domains.chat.service import ChatService
            import uuid

            chat_service = ChatService()
            type_errors = []

            # 测试多种可能触发类型错误的场景
            test_scenarios = [
                ("正常消息", "你好，这是一个测试消息"),
                ("空消息", ""),
                ("特殊字符", "!@#$%^&*()"),
                ("长消息", "测试" * 1000),
                ("Unicode", "测试中文🚀表情符号"),
            ]

            for scenario_name, message in test_scenarios:
                try:
                    test_user_id = f"type-safety-test-{uuid.uuid4()}"
                    test_session_id = f"type-safety-session-{uuid.uuid4()}"

                    result = chat_service.send_message(
                        user_id=test_user_id,
                        session_id=test_session_id,
                        message=message
                    )

                    if result.get("status") != "success":
                        type_errors.append({
                            "scenario": scenario_name,
                            "error": f"处理失败: {result.get('message', 'unknown error')}"
                        })

                except Exception as e:
                    if "'>' not supported between instances of 'str' and 'int'" in str(e):
                        type_errors.append({
                            "scenario": scenario_name,
                            "error": "类型比较错误重现",
                            "details": str(e)
                        })
                    else:
                        # 其他错误记录但不作为主要问题
                        logger.warning(f"场景 {scenario_name} 出现其他错误: {e}")

            if type_errors:
                return TestResult(
                    test_name="test_langgraph_type_safety",
                    status=TestStatus.FAILED,
                    message=f"发现 {len(type_errors)} 个类型安全问题",
                    details={"type_errors": type_errors}
                )
            else:
                return TestResult(
                    test_name="test_langgraph_type_safety",
                    status=TestStatus.PASSED,
                    message="LangGraph类型安全测试通过"
                )

        except Exception as e:
            return TestResult(
                test_name="test_langgraph_type_safety",
                status=TestStatus.ERROR,
                message=f"测试执行失败: {str(e)}"
            )

    def test_checkpoint_version_consistency(self) -> TestResult:
        """Checkpoint版本一致性测试"""
        try:
            os.environ.setdefault("CHAT_DB_PATH", "data/test_checkpoint_consistency.db")

            from src.domains.chat.database import create_chat_checkpointer
            from langchain_core.messages import HumanMessage
            import uuid

            version_inconsistencies = []

            with create_chat_checkpointer() as checkpointer:
                # 创建测试配置
                config = {
                    "configurable": {
                        "thread_id": f"consistency-test-{uuid.uuid4()}",
                        "user_id": "test-user"
                    }
                }

                # 创建包含各种版本号类型的checkpoint
                test_checkpoints = [
                    {
                        "name": "正常版本号",
                        "checkpoint": {
                            "v": 1,
                            "id": str(uuid.uuid4()),
                            "ts": "2024-01-01T00:00:00.000000+00:00",
                            "channel_values": {"messages": [HumanMessage(content="测试")]},
                            "channel_versions": {
                                "__start__": 1,  # 整数
                                "messages": 2     # 整数
                            }
                        }
                    },
                    {
                        "name": "混合类型版本号",
                        "checkpoint": {
                            "v": 1,
                            "id": str(uuid.uuid4()),
                            "ts": "2024-01-01T00:00:00.000000+00:00",
                            "channel_values": {"messages": [HumanMessage(content="测试")]},
                            "channel_versions": {
                                "__start__": "00000000000000000000000000000002.0.243798848838515",  # 字符串
                                "messages": 1     # 整数
                            }
                        }
                    }
                ]

                for test_case in test_checkpoints:
                    try:
                        checkpointer.put(config, test_case["checkpoint"], {}, {})

                        # 立即读取验证
                        retrieved = checkpointer.get(config)
                        if retrieved:
                            channel_versions = retrieved.get("channel_versions", {})

                            # 检查所有版本号都是整数
                            for key, value in channel_versions.items():
                                if not isinstance(value, int):
                                    version_inconsistencies.append({
                                        "test_case": test_case["name"],
                                        "channel": key,
                                        "value": value,
                                        "type": type(value).__name__
                                    })

                    except Exception as e:
                        if "'>' not supported between instances of 'str' and 'int'" in str(e):
                            version_inconsistencies.append({
                                "test_case": test_case["name"],
                                "error": "类型比较错误重现",
                                "details": str(e)
                            })
                        else:
                            logger.warning(f"测试用例 {test_case['name']} 出现其他错误: {e}")

            if version_inconsistencies:
                return TestResult(
                    test_name="test_checkpoint_version_consistency",
                    status=TestStatus.FAILED,
                    message=f"发现 {len(version_inconsistencies)} 个版本一致性问题",
                    details={"inconsistencies": version_inconsistencies}
                )
            else:
                return TestResult(
                    test_name="test_checkpoint_version_consistency",
                    status=TestStatus.PASSED,
                    message="Checkpoint版本一致性测试通过"
                )

        except Exception as e:
            return TestResult(
                test_name="test_checkpoint_version_consistency",
                status=TestStatus.ERROR,
                message=f"测试执行失败: {str(e)}"
            )


class EnhancedTestSuite:
    """增强型测试套件"""

    def __init__(self):
        self.app = None
        self.results: List[TestResult] = []

    def setup(self):
        """设置测试环境"""
        try:
            # 导入应用
            from src.api.main import app
            self.app = app
            logger.info("✅ 测试环境设置完成")
            return True
        except Exception as e:
            logger.error(f"❌ 测试环境设置失败: {e}")
            return False

    def run_all_tests(self) -> List[TestResult]:
        """运行所有测试"""
        if not self.app:
            raise RuntimeError("测试环境未设置，请先调用setup()")

        logger.info("🚀 开始运行增强型测试套件...")

        # OpenAPI合规性测试
        openapi_tests = OpenAPIComplianceTest(self.app)
        self.results.append(openapi_tests.test_no_args_kwargs_parameters())
        self.results.append(openapi_tests.test_parameter_consistency())

        # 依赖注入测试
        dependency_tests = DependencyInjectionTest(self.app)
        self.results.append(dependency_tests.test_dependency_resolution())
        self.results.append(dependency_tests.test_parameter_ordering())

        # 运行时错误测试
        runtime_tests = RuntimeErrorTest()
        self.results.append(runtime_tests.test_langgraph_type_safety())
        self.results.append(runtime_tests.test_checkpoint_version_consistency())

        return self.results

    def generate_report(self) -> str:
        """生成测试报告"""
        if not self.results:
            return "没有测试结果"

        passed_count = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed_count = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        error_count = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        total_count = len(self.results)

        report = f"""
# 增强型测试套件报告

## 📊 测试概览
- 总测试数: {total_count}
- 通过: {passed_count}
- 失败: {failed_count}
- 错误: {error_count}
- 成功率: {(passed_count/total_count*100):.1f}%

## 📋 详细结果

"""

        for result in self.results:
            status_emoji = "✅" if result.status == TestStatus.PASSED else "❌"
            report += f"### {status_emoji} {result.test_name}\n"
            report += f"- 状态: {result.status.value}\n"
            report += f"- 消息: {result.message}\n"

            if result.details:
                report += f"- 详情:\n```json\n{json.dumps(result.details, indent=2, ensure_ascii=False)}\n```\n"

            report += "\n"

        # 总结和建议
        report += "## 💡 总结和建议\n"

        if failed_count == 0 and error_count == 0:
            report += "🎉 所有测试都通过了！系统质量良好。\n"
        else:
            report += "⚠️ 发现了一些问题，建议及时修复：\n\n"

            for result in self.results:
                if result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                    report += f"- **{result.test_name}**: {result.message}\n"

            report += "\n建议：\n"
            report += "1. 优先修复FAILED状态的测试\n"
            report += "2. 检查ERROR状态的测试是否需要调整测试环境\n"
            report += "3. 定期运行此测试套件确保代码质量\n"

        return report

    def save_report(self, filename: str = "test_report.md"):
        """保存测试报告"""
        report = self.generate_report()

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"📄 测试报告已保存到: {filename}")
        return filename


def main():
    """主函数"""
    print("🚀 启动增强型测试系统...")
    print("=" * 60)

    # 创建测试套件
    test_suite = EnhancedTestSuite()

    # 设置测试环境
    if not test_suite.setup():
        print("❌ 测试环境设置失败，退出")
        return False

    # 运行所有测试
    results = test_suite.run_all_tests()

    # 生成和保存报告
    report_file = test_suite.save_report()

    # 输出摘要
    passed_count = sum(1 for r in results if r.status == TestStatus.PASSED)
    total_count = len(results)
    success_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print("=" * 60)
    print(f"📊 测试完成: {passed_count}/{total_count} 通过 ({success_rate:.1f}%)")
    print(f"📄 详细报告: {report_file}")

    return success_rate == 100.0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)