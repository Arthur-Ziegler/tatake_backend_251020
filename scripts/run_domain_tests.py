#!/usr/bin/env python3
"""
领域测试启动脚本

为每个领域提供独立的测试运行功能，支持：
1. 单个领域测试运行
2. 覆盖率报告生成
3. 测试结果分析
4. 并行测试执行
5. 测试独立性验证

遵循OpenSpec rebuild-testing-infrastructure 要求：
- TDD测试驱动开发
- 模块化设计，避免大文件
- 简洁实用的实现

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import time


class DomainTestRunner:
    """领域测试运行器 - 遵循TDD和模块化设计原则"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.tests_dir = self.project_root / "tests" / "domains"
        self.available_domains = self._get_available_domains()

    def _get_available_domains(self) -> List[str]:
        """获取所有可用的测试领域"""
        if not self.tests_dir.exists():
            return []

        domains = []
        for item in self.tests_dir.iterdir():
            if item.is_dir() and not item.name.startswith("__"):
                # 检查是否有测试文件
                test_files = list(item.glob("test_*.py"))
                if test_files:
                    domains.append(item.name)

        return sorted(domains)

    def run_command(self, cmd: List[str], description: str = "", capture: bool = True) -> Tuple[bool, str, str]:
        """
        运行命令并返回结果

        Args:
            cmd: 要执行的命令
            description: 命令描述
            capture: 是否捕获输出

        Returns:
            Tuple[success, stdout, stderr]
        """
        print(f"🚀 {description}")
        print(f"执行: {' '.join(cmd)}")
        print("-" * 60)

        try:
            if capture:
                result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)

                if result.stdout:
                    print(result.stdout)

                if result.stderr and "warning" not in result.stderr.lower():
                    print("错误输出:")
                    print(result.stderr)

                success = result.returncode == 0
                status = "✅ 成功" if success else f"❌ 失败 (退出码: {result.returncode})"
                print(f"{status}")

                return success, result.stdout, result.stderr
            else:
                # 直接运行，不捕获输出
                result = subprocess.run(cmd, cwd=self.project_root)
                success = result.returncode == 0
                return success, "", ""

        except KeyboardInterrupt:
            print("⏹️ 命令被用户中断")
            return False, "", "中断"
        except Exception as e:
            print(f"❌ 执行命令时出错: {e}")
            return False, "", str(e)

    def verify_test_independence(self, domain: str) -> bool:
        """
        验证测试独立性 - 确保测试可以独立运行

        这是OpenSpec任务4.1的要求
        """
        print(f"🔍 验证 {domain} 领域测试独立性...")

        domain_path = self.tests_dir / domain
        test_files = list(domain_path.glob("test_*.py"))

        if not test_files:
            print(f"❌ {domain} 领域没有测试文件")
            return False

        independence_results = []

        for test_file in test_files:
            print(f"   测试文件: {test_file.name}")

            # 单独运行每个测试文件
            cmd = ["uv", "run", "pytest", str(test_file), "-v", "--tb=short"]
            success, stdout, stderr = self.run_command(
                cmd,
                f"验证 {test_file.name} 独立性",
                capture=True
            )

            independence_results.append((test_file.name, success))

            if not success:
                print(f"   ❌ {test_file.name} 无法独立运行")
            else:
                print(f"   ✅ {test_file.name} 可以独立运行")

        # 汇总结果
        passed = sum(1 for _, success in independence_results if success)
        total = len(independence_results)

        print(f"\n📊 {domain} 领域测试独立性验证结果:")
        print(f"   通过: {passed}/{total}")

        if passed == total:
            print(f"✅ {domain} 领域所有测试都可以独立运行")
            return True
        else:
            failed_files = [name for name, success in independence_results if not success]
            print(f"❌ {domain} 领域有 {total - passed} 个测试文件无法独立运行:")
            for name in failed_files:
                print(f"     • {name}")
            return False

    def get_domain_coverage(self, domain: str) -> Optional[Dict]:
        """获取指定领域的覆盖率信息"""
        coverage_file = self.project_root / "htmlcov" / domain / "index.html"

        if not coverage_file.exists():
            return None

        # 简单的覆盖率解析 - 实际项目中可以更复杂
        try:
            # 尝试从HTML文件中提取覆盖率信息
            with open(coverage_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找覆盖率百分比
            import re
            coverage_match = re.search(r'(\d+%)', content)
            if coverage_match:
                coverage_percent = coverage_match.group(1)
                return {
                    "domain": domain,
                    "coverage": coverage_percent,
                    "report_path": str(coverage_file)
                }
        except Exception:
            pass

        return None

    def run_domain_tests(
        self,
        domain: str,
        coverage: bool = False,
        verbose: bool = False,
        parallel: bool = False,
        marker: Optional[str] = None,
        verify_independence: bool = False
    ) -> bool:
        """
        运行指定领域的测试

        Args:
            domain: 领域名称
            coverage: 是否生成覆盖率报告
            verbose: 是否显示详细输出
            parallel: 是否并行执行
            marker: pytest标记过滤
            verify_independence: 是否验证测试独立性

        Returns:
            bool: 测试是否成功
        """
        if domain not in self.available_domains:
            print(f"❌ 领域 '{domain}' 不存在或没有测试文件")
            print(f"可用领域: {', '.join(self.available_domains)}")
            return False

        domain_test_path = self.tests_dir / domain
        print(f"🚀 开始运行 {domain} 领域测试...")
        print(f"📂 测试路径: {domain_test_path}")

        # 首先验证测试独立性（如果要求）
        if verify_independence:
            independence_ok = self.verify_test_independence(domain)
            if not independence_ok:
                print(f"❌ {domain} 领域测试独立性验证失败，停止执行")
                return False

        # 构建pytest命令
        cmd = ["uv", "run", "pytest", str(domain_test_path)]

        # 添加详细输出
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        # 添加覆盖率
        if coverage:
            cmd.extend([
                "--cov=src/domains/" + domain,
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/" + domain,
                "--cov-report=xml:coverage-" + domain + ".xml"
            ])

        # 添加并行执行
        if parallel:
            cmd.extend(["-n", "auto"])

        # 添加标记过滤
        if marker:
            cmd.extend(["-m", marker])

        # 添加其他有用的选项
        cmd.extend([
            "--tb=short",  # 简短的错误回溯
            "--strict-markers",  # 严格标记模式
            "--disable-warnings"  # 禁用警告
        ])

        # 运行测试
        description = f"运行 {domain} 领域测试" + ("并生成覆盖率报告" if coverage else "")
        success, stdout, stderr = self.run_command(cmd, description, capture=False)

        if success:
            print(f"✅ {domain} 领域测试通过!")
            if coverage:
                coverage_info = self.get_domain_coverage(domain)
                if coverage_info:
                    print(f"📊 覆盖率: {coverage_info['coverage']}")
                    print(f"📄 报告路径: {coverage_info['report_path']}")
        else:
            print(f"❌ {domain} 领域测试失败!")

        return success

    def run_all_domains(
        self,
        coverage: bool = False,
        verbose: bool = False,
        parallel: bool = False,
        marker: Optional[str] = None,
        fail_fast: bool = False,
        verify_independence: bool = False
    ) -> Dict[str, bool]:
        """
        运行所有领域的测试

        Args:
            coverage: 是否生成覆盖率报告
            verbose: 是否显示详细输出
            parallel: 是否并行执行
            marker: pytest标记过滤
            fail_fast: 是否在第一个失败时停止
            verify_independence: 是否验证测试独立性

        Returns:
            Dict[str, bool]: 各领域测试结果
        """
        print(f"🚀 开始运行所有 {len(self.available_domains)} 个领域的测试...")

        results = {}

        for domain in self.available_domains:
            print(f"\n{'='*60}")
            print(f"{'='*20} {domain.upper()} 领域 {'='*20}")

            success = self.run_domain_tests(
                domain=domain,
                coverage=coverage,
                verbose=verbose,
                parallel=parallel,
                marker=marker,
                verify_independence=verify_independence
            )
            results[domain] = success

            if not success and fail_fast:
                print(f"⏹️ 因 {domain} 测试失败而停止执行")
                break

        # 汇总结果
        passed = sum(results.values())
        total = len(results)

        print(f"\n{'='*60}")
        print(f"📋 测试结果汇总:")
        print(f"   总领域数: {total}")
        print(f"   通过: {passed}")
        print(f"   失败: {total - passed}")

        for domain, success in results.items():
            status = "✅ 通过" if success else "❌ 失败"
            print(f"   {domain}: {status}")

        if passed == total:
            print("🎉 所有领域测试都通过了!")
        else:
            failed_domains = [d for d, success in results.items() if not success]
            print(f"❌ 失败的领域: {', '.join(failed_domains)}")

        return results

    def list_domains(self):
        """列出所有可用的测试领域"""
        print(f"📋 可用的测试领域 ({len(self.available_domains)} 个):")
        for domain in self.available_domains:
            domain_path = self.tests_dir / domain
            test_files = list(domain_path.glob("test_*.py"))
            print(f"   • {domain} ({len(test_files)} 个测试文件)")

    def get_domain_info(self, domain: str) -> Dict:
        """获取指定领域的详细信息"""
        if domain not in self.available_domains:
            return {"error": f"领域 '{domain}' 不存在"}

        domain_path = self.tests_dir / domain
        test_files = list(domain_path.glob("test_*.py"))

        info = {
            "domain": domain,
            "path": str(domain_path),
            "test_files": [f.name for f in test_files],
            "test_count": len(test_files)
        }

        # 尝试统计测试数量
        try:
            cmd = ["uv", "run", "pytest", str(domain_path), "--collect-only", "-q"]
            success, stdout, stderr = self.run_command(
                cmd,
                f"收集 {domain} 领域测试信息",
                capture=True
            )

            if success and stdout:
                lines = stdout.strip().split('\n')
                for line in lines:
                    if "collected" in line and "items" in line:
                        # 提取测试数量
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.isdigit():
                                info["test_cases"] = int(part)
                                break
        except Exception:
            pass

        # 获取覆盖率信息（如果存在）
        coverage_info = self.get_domain_coverage(domain)
        if coverage_info:
            info["coverage"] = coverage_info["coverage"]
            info["coverage_report"] = coverage_info["report_path"]

        return info


# 为了向后兼容，保留旧函数的包装器
def run_all_domain_tests(coverage=False):
    """运行所有领域的测试 - 向后兼容包装器"""
    runner = DomainTestRunner()
    results = runner.run_all_domains(coverage=coverage)
    return all(results.values())


def run_domain_tests_legacy(domain, coverage=False):
    """向后兼容的函数包装器"""
    runner = DomainTestRunner()
    return runner.run_domain_tests(domain=domain, coverage=coverage)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="TaTakeKe 领域测试运行器 - OpenSpec rebuild-testing-infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 运行单个领域测试
  python scripts/run_domain_tests.py auth

  # 运行测试并生成覆盖率报告
  python scripts/run_domain_tests.py chat --coverage

  # 运行所有领域测试
  python scripts/run_domain_tests.py --all

  # 验证测试独立性
  python scripts/run_domain_tests.py auth --verify-independence

  # 并行运行所有测试
  python scripts/run_domain_tests.py --all --parallel

  # 只运行单元测试
  python scripts/run_domain_tests.py --all --marker unit

  # 列出所有可用领域
  python scripts/run_domain_tests.py --list

  # 获取领域详细信息
  python scripts/run_domain_tests.py auth --info
        """
    )

    parser.add_argument(
        "domain",
        nargs="?",
        help="要测试的领域名称 (如: auth, task, chat 等)"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有领域的测试"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的测试领域"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="显示领域的详细信息"
    )

    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="生成覆盖率报告"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出"
    )

    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="并行执行测试"
    )

    parser.add_argument(
        "--marker", "-m",
        help="pytest标记过滤 (如: unit, integration, slow)"
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="在第一个失败时停止执行"
    )

    parser.add_argument(
        "--verify-independence",
        action="store_true",
        help="验证测试独立性 (OpenSpec任务4.1要求)"
    )

    # 向后兼容参数
    parser.add_argument(
        "--domain", "-d",
        help=argparse.SUPPRESS  # 隐藏但支持向后兼容
    )

    parser.add_argument(
        "-a",
        action="store_true",
        help=argparse.SUPPRESS  # 隐藏但支持向后兼容
    )

    parser.add_argument(
        "-l",
        action="store_true",
        help=argparse.SUPPRESS  # 隐藏但支持向后兼容
    )

    args = parser.parse_args()

    # 处理向后兼容参数
    if hasattr(args, 'domain') and args.domain and not args.domain:
        args.domain = args.domain
    if args.a and not args.all:
        args.all = args.a
    if args.l and not args.list:
        args.list = args.l

    # 创建测试运行器
    runner = DomainTestRunner()

    try:
        if args.list:
            runner.list_domains()
        elif args.info:
            if not args.domain:
                print("❌ 请指定要查看的领域名称")
                sys.exit(1)

            info = runner.get_domain_info(args.domain)
            if "error" in info:
                print(f"❌ {info['error']}")
                sys.exit(1)

            print(f"📋 {info['domain']} 领域信息:")
            print(f"   路径: {info['path']}")
            print(f"   测试文件: {info['test_count']} 个")
            if "test_cases" in info:
                print(f"   测试用例: {info['test_cases']} 个")
            if "coverage" in info:
                print(f"   覆盖率: {info['coverage']}")
            print("   测试文件列表:")
            for test_file in info["test_files"]:
                print(f"     • {test_file}")

        elif args.all:
            results = runner.run_all_domains(
                coverage=args.coverage,
                verbose=args.verbose,
                parallel=args.parallel,
                marker=args.marker,
                fail_fast=args.fail_fast,
                verify_independence=args.verify_independence
            )

            # 返回适当的退出码
            failed_count = sum(1 for success in results.values() if not success)
            if failed_count > 0:
                sys.exit(1)

        elif args.domain:
            success = runner.run_domain_tests(
                domain=args.domain,
                coverage=args.coverage,
                verbose=args.verbose,
                parallel=args.parallel,
                marker=args.marker,
                verify_independence=args.verify_independence
            )

            if not success:
                sys.exit(1)

        else:
            runner.list_domains()

    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 执行过程中出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()