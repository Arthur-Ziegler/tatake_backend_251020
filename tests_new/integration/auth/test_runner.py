"""
认证系统测试运行器

提供测试执行、报告生成和质量分析功能：
1. 测试套件执行管理
2. 覆盖率分析
3. 性能基准测试
4. 测试结果报告
5. 质量指标评估

使用方法：
    python -m tests.integration.auth.test_runner
    或
    uv run python tests/integration/auth/test_runner.py

作者：TaTakeKe团队
版本：2.0.0 - 认证系统测试基础设施
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from coverage import Coverage


@dataclass
class TestResult:
    """测试结果数据结构"""
    name: str
    passed: int
    failed: int
    skipped: int
    errors: int
    total: int
    duration: float
    success_rate: float
    details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CoverageReport:
    """覆盖率报告数据结构"""
    total_lines: int
    covered_lines: int
    coverage_percent: float
    file_coverage: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""
    test_duration: float
    memory_usage: float
    cpu_usage: float
    test_throughput: float  # tests per second


@dataclass
class QualityReport:
    """质量报告数据结构"""
    test_results: List[TestResult]
    coverage_report: Optional[CoverageReport]
    performance_metrics: PerformanceMetrics
    quality_score: float
    recommendations: List[str]


class AuthTestRunner:
    """认证系统测试运行器"""

    def __init__(self, test_dir: str = None):
        """
        初始化测试运行器

        Args:
            test_dir: 测试目录路径
        """
        self.test_dir = test_dir or str(Path(__file__).parent)
        self.project_root = Path(__file__).parent.parent.parent.parent

        # 测试套件配置
        self.test_suites = {
            "sqlalchemy_compatibility": {
                "path": "test_sqlalchemy_compatibility.py",
                "description": "SQLAlchemy API兼容性测试",
                "critical": True
            },
            "boundary_conditions": {
                "path": "test_boundary_conditions.py",
                "description": "边界条件测试",
                "critical": True
            },
            "auth_integration": {
                "path": "test_auth_integration.py",
                "description": "认证系统集成测试",
                "critical": True
            }
        }

    def run_test_suite(self, suite_name: str, coverage_enabled: bool = True) -> TestResult:
        """
        运行单个测试套件

        Args:
            suite_name: 测试套件名称
            coverage_enabled: 是否启用覆盖率统计

        Returns:
            TestResult: 测试结果
        """
        if suite_name not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite_name}")

        suite_config = self.test_suites[suite_name]
        test_path = os.path.join(self.test_dir, suite_config["path"])

        # 准备pytest参数
        pytest_args = [
            test_path,
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=/tmp/test_report.json",
            f"--junitxml=/tmp/pytest_{suite_name}.xml"
        ]

        # 启用覆盖率统计
        cov = None
        if coverage_enabled:
            cov = Coverage(source=[f"src.domains.auth"])
            cov.start()

        # 执行测试
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        duration = time.time() - start_time

        # 收集覆盖率
        if coverage_enabled and cov:
            cov.stop()
            cov.save()

        # 解析测试报告
        result = self._parse_test_result(suite_name, exit_code, duration)

        return result

    def run_all_tests(self, coverage_enabled: bool = True) -> List[TestResult]:
        """
        运行所有测试套件

        Args:
            coverage_enabled: 是否启用覆盖率统计

        Returns:
            List[TestResult]: 所有测试结果
        """
        results = []

        print("🧪 开始运行认证系统测试套件...")
        print("=" * 60)

        for suite_name in self.test_suites:
            suite_config = self.test_suites[suite_name]
            print(f"\n📋 运行测试套件: {suite_name}")
            print(f"   描述: {suite_config['description']}")
            print(f"   关键: {'是' if suite_config['critical'] else '否'}")

            try:
                result = self.run_test_suite(suite_name, coverage_enabled)
                results.append(result)

                # 打印测试结果摘要
                status = "✅ 通过" if result.failed == 0 else "❌ 失败"
                print(f"   结果: {status}")
                print(f"   总计: {result.total}, 通过: {result.passed}, 失败: {result.failed}")
                print(f"   成功率: {result.success_rate:.1f}%")
                print(f"   耗时: {result.duration:.2f}s")

            except Exception as e:
                print(f"   ❌ 测试执行失败: {e}")
                # 创建失败结果
                failed_result = TestResult(
                    name=suite_name,
                    passed=0,
                    failed=1,
                    skipped=0,
                    errors=1,
                    total=1,
                    duration=0,
                    success_rate=0.0,
                    details=[{"error": str(e)}]
                )
                results.append(failed_result)

        return results

    def _parse_test_result(self, suite_name: str, exit_code: int, duration: float) -> TestResult:
        """
        解析测试结果

        Args:
            suite_name: 测试套件名称
            exit_code: pytest退出码
            duration: 执行时间

        Returns:
            TestResult: 解析后的测试结果
        """
        # 尝试读取JSON报告
        report_file = "/tmp/test_report.json"
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            summary = report_data.get('summary', {})
            tests = summary.get('total', 0)
            passed = summary.get('passed', 0)
            failed = summary.get('failed', 0)
            skipped = summary.get('skipped', 0)
            errors = summary.get('error', 0)

            # 计算成功率
            total_executed = passed + failed
            success_rate = (passed / total_executed * 100) if total_executed > 0 else 0

            # 收集详细信息
            details = []
            for test in report_data.get('tests', []):
                details.append({
                    'name': test.get('nodeid', ''),
                    'outcome': test.get('outcome', ''),
                    'duration': test.get('duration', 0),
                    'call': test.get('call', {})
                })

        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            # 如果无法读取报告，使用默认值
            tests = 1
            passed = 0 if exit_code != 0 else 1
            failed = 1 if exit_code != 0 else 0
            skipped = 0
            errors = 0
            success_rate = 0 if failed > 0 else 100
            details = []

        return TestResult(
            name=suite_name,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            total=tests,
            duration=duration,
            success_rate=success_rate,
            details=details
        )

    def generate_coverage_report(self) -> Optional[CoverageReport]:
        """
        生成覆盖率报告

        Returns:
            Optional[CoverageReport]: 覆盖率报告
        """
        try:
            coverage_file = "/tmp/.coverage"
            if not os.path.exists(coverage_file):
                return None

            from coverage import Coverage
            cov = Coverage(data_file=coverage_file)
            cov.load()

            # 获取总体覆盖率
            total_lines = 0
            covered_lines = 0
            file_coverage = {}

            for filename in cov.get_data().measured_files():
                if "src/domains/auth" in filename:
                    analysis = cov.analysis2(filename)
                    file_lines = analysis[1]  # 总行数
                    file_covered = analysis[2]  # 覆盖行数

                    total_lines += len(file_lines)
                    covered_lines += len(file_covered)

                    file_coverage[filename] = {
                        "total_lines": len(file_lines),
                        "covered_lines": len(file_covered),
                        "coverage_percent": len(file_covered) / len(file_lines) * 100 if file_lines else 0
                    }

            coverage_percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0

            return CoverageReport(
                total_lines=total_lines,
                covered_lines=covered_lines,
                coverage_percent=coverage_percent,
                file_coverage=file_coverage
            )

        except Exception as e:
            print(f"⚠️  覆盖率报告生成失败: {e}")
            return None

    def calculate_quality_score(self, test_results: List[TestResult], coverage_report: Optional[CoverageReport]) -> float:
        """
        计算质量评分

        Args:
            test_results: 测试结果列表
            coverage_report: 覆盖率报告

        Returns:
            float: 质量评分 (0-100)
        """
        score = 0.0

        # 测试通过率 (40分)
        total_tests = sum(r.total for r in test_results)
        total_passed = sum(r.passed for r in test_results)
        if total_tests > 0:
            pass_rate = (total_passed / total_tests) * 40
            score += pass_rate

        # 关键测试通过情况 (20分)
        critical_tests = [r for r in test_results if self.test_suites.get(r.name, {}).get('critical', False)]
        if critical_tests:
            critical_passed = sum(1 for r in critical_tests if r.failed == 0)
            critical_score = (critical_passed / len(critical_tests)) * 20
            score += critical_score
        else:
            score += 20  # 如果没有关键测试，给满分

        # 覆盖率 (30分)
        if coverage_report:
            coverage_score = min(coverage_report.coverage_percent / 100 * 30, 30)
            score += coverage_score
        else:
            score += 15  # 如果没有覆盖率数据，给一半分数

        # 测试稳定性 (10分) - 基于错误数量
        total_errors = sum(r.errors for r in test_results)
        if total_errors == 0:
            score += 10
        else:
            error_penalty = min(total_errors * 2, 10)
            score += max(10 - error_penalty, 0)

        return min(score, 100)  # 确保不超过100分

    def generate_recommendations(self, test_results: List[TestResult], coverage_report: Optional[CoverageReport]) -> List[str]:
        """
        生成改进建议

        Args:
            test_results: 测试结果列表
            coverage_report: 覆盖率报告

        Returns:
            List[str]: 改进建议列表
        """
        recommendations = []

        # 分析测试失败
        failed_tests = [r for r in test_results if r.failed > 0]
        if failed_tests:
            recommendations.append(f"🔧 修复 {len(failed_tests)} 个失败的测试套件")
            for test in failed_tests:
                recommendations.append(f"   - {test.name}: {test.failed} 个测试失败")

        # 分析覆盖率
        if coverage_report:
            if coverage_report.coverage_percent < 95:
                recommendations.append(f"📈 提高代码覆盖率 (当前: {coverage_report.coverage_percent:.1f}%, 目标: 95%)")

            # 找出覆盖率低的文件
            low_coverage_files = [
                (file, data['coverage_percent'])
                for file, data in coverage_report.file_coverage.items()
                if data['coverage_percent'] < 80
            ]
            if low_coverage_files:
                recommendations.append("📁 以下文件覆盖率较低，需要增加测试:")
                for file, cov in low_coverage_files:
                    recommendations.append(f"   - {file}: {cov:.1f}%")

        # 分析错误
        total_errors = sum(r.errors for r in test_results)
        if total_errors > 0:
            recommendations.append(f"🚨 解决 {total_errors} 个测试执行错误")

        # 分析性能
        total_duration = sum(r.duration for r in test_results)
        if total_duration > 30:  # 如果总执行时间超过30秒
            recommendations.append(f"⚡ 优化测试性能 (当前执行时间: {total_duration:.1f}s)")

        if not recommendations:
            recommendations.append("🎉 测试质量优秀，继续保持！")

        return recommendations

    def generate_quality_report(self) -> QualityReport:
        """
        生成综合质量报告

        Returns:
            QualityReport: 质量报告
        """
        print("\n📊 生成测试质量报告...")

        # 运行所有测试
        test_results = self.run_all_tests(coverage_enabled=True)

        # 生成覆盖率报告
        coverage_report = self.generate_coverage_report()

        # 计算性能指标
        total_duration = sum(r.duration for r in test_results)
        total_tests = sum(r.total for r in test_results)
        performance_metrics = PerformanceMetrics(
            test_duration=total_duration,
            memory_usage=0,  # TODO: 实现内存使用统计
            cpu_usage=0,     # TODO: 实现CPU使用统计
            test_throughput=total_tests / total_duration if total_duration > 0 else 0
        )

        # 计算质量评分
        quality_score = self.calculate_quality_score(test_results, coverage_report)

        # 生成改进建议
        recommendations = self.generate_recommendations(test_results, coverage_report)

        return QualityReport(
            test_results=test_results,
            coverage_report=coverage_report,
            performance_metrics=performance_metrics,
            quality_score=quality_score,
            recommendations=recommendations
        )

    def print_quality_report(self, report: QualityReport):
        """
        打印质量报告

        Args:
            report: 质量报告
        """
        print("\n" + "=" * 60)
        print("📋 认证系统测试质量报告")
        print("=" * 60)

        # 总体摘要
        total_tests = sum(r.total for r in report.test_results)
        total_passed = sum(r.passed for r in report.test_results)
        total_failed = sum(r.failed for r in report.test_results)
        total_errors = sum(r.errors for r in report.test_results)

        print(f"\n📊 测试摘要:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过: {total_passed}")
        print(f"   失败: {total_failed}")
        print(f"   错误: {total_errors}")
        print(f"   成功率: {(total_passed / total_tests * 100) if total_tests > 0 else 0:.1f}%")

        # 覆盖率信息
        if report.coverage_report:
            print(f"\n📈 代码覆盖率:")
            print(f"   总覆盖率: {report.coverage_report.coverage_percent:.1f}%")
            print(f"   总行数: {report.coverage_report.total_lines}")
            print(f"   覆盖行数: {report.coverage_report.covered_lines}")

        # 性能指标
        print(f"\n⚡ 性能指标:")
        print(f"   总执行时间: {report.performance_metrics.test_duration:.2f}s")
        print(f"   测试吞吐量: {report.performance_metrics.test_throughput:.1f} tests/s")

        # 质量评分
        print(f"\n🏆 质量评分: {report.quality_score:.1f}/100")

        # 评分等级
        if report.quality_score >= 90:
            grade = "优秀 🌟"
        elif report.quality_score >= 80:
            grade = "良好 ✅"
        elif report.quality_score >= 70:
            grade = "一般 ⚠️"
        else:
            grade = "需要改进 ❌"
        print(f"   评级: {grade}")

        # 改进建议
        print(f"\n💡 改进建议:")
        for recommendation in report.recommendations:
            print(f"   {recommendation}")

        print("\n" + "=" * 60)


def main():
    """主函数"""
    print("🚀 认证系统测试运行器")
    print("=" * 60)

    # 创建测试运行器
    runner = AuthTestRunner()

    try:
        # 生成质量报告
        report = runner.generate_quality_report()

        # 打印报告
        runner.print_quality_report(report)

        # 根据质量评分设置退出码
        if report.quality_score >= 80:
            exit_code = 0  # 成功
        elif report.quality_score >= 60:
            exit_code = 1  # 警告
        else:
            exit_code = 2  # 失败

        return exit_code

    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 测试运行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)