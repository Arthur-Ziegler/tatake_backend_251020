#!/usr/bin/env python3
"""
测试执行脚本

提供标准化的测试执行接口，支持不同类型和级别的测试运行。

作者：TaTake团队
版本：1.0.0 - 标准化测试执行
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """测试运行器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> int:
        """执行命令"""
        if cwd is None:
            cwd = self.project_root

        print(f"执行命令: {' '.join(cmd)}")
        print(f"工作目录: {cwd}")
        print("-" * 80)

        try:
            result = subprocess.run(cmd, cwd=cwd, check=True)
            print("-" * 80)
            print("✅ 命令执行成功")
            return result.returncode
        except subprocess.CalledProcessError as e:
            print("-" * 80)
            print(f"❌ 命令执行失败，退出码: {e.returncode}")
            return e.returncode

    def run_unit_tests(self, coverage: bool = True, verbose: bool = True) -> int:
        """运行单元测试"""
        cmd = ["uv", "run", "pytest", "-m", "unit"]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=html:htmlcov/unit",
                "--cov-report=term-missing",
                "--cov-fail-under=95"
            ])

        cmd.extend([
            "--tb=short",
            "tests/unit"
        ])

        return self.run_command(cmd)

    def run_integration_tests(self, coverage: bool = True, verbose: bool = True) -> int:
        """运行集成测试"""
        cmd = ["uv", "run", "pytest", "-m", "integration"]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=html:htmlcov/integration",
                "--cov-report=term-missing",
                "--cov-fail-under=90"
            ])

        cmd.extend([
            "--tb=short",
            "tests/integration"
        ])

        return self.run_command(cmd)

    def run_functional_tests(self, coverage: bool = False, verbose: bool = True) -> int:
        """运行功能测试"""
        cmd = ["uv", "run", "pytest", "-m", "functional"]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=html:htmlcov/functional",
                "--cov-report=term-missing"
            ])

        cmd.extend([
            "--tb=short",
            "tests/functional"
        ])

        return self.run_command(cmd)

    def run_all_tests(self, coverage: bool = True, verbose: bool = True) -> int:
        """运行所有测试"""
        cmd = ["uv", "run", "pytest"]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=html:htmlcov/all",
                "--cov-report=term-missing",
                "--cov-fail-under=98"
            ])

        cmd.extend([
            "--tb=short",
            "tests"
        ])

        return self.run_command(cmd)

    def run_domain_tests(self, domain: str, test_type: str = "unit") -> int:
        """运行特定域的测试"""
        valid_domains = ["auth", "points", "reward", "task", "top3", "user", "chat", "focus"]
        valid_types = ["unit", "integration", "functional"]

        if domain not in valid_domains:
            print(f"❌ 无效的域: {domain}")
            print(f"有效的域: {', '.join(valid_domains)}")
            return 1

        if test_type not in valid_types:
            print(f"❌ 无效的测试类型: {test_type}")
            print(f"有效的类型: {', '.join(valid_types)}")
            return 1

        cmd = [
            "uv", "run", "pytest",
            "-m", f"{test_type} and {domain}",
            "-v",
            "--tb=short",
            f"tests/{test_type}/domains/{domain}"
        ]

        return self.run_command(cmd)

    def run_welcome_gift_tests(self) -> int:
        """运行欢迎礼包相关测试"""
        # 单元测试
        print("🎯 运行欢迎礼包单元测试...")
        unit_result = self.run_command([
            "uv", "run", "pytest",
            "-m", "unit and reward",
            "-v",
            "--tb=short",
            "tests/unit/domains/reward/test_welcome_gift*.py"
        ])

        if unit_result != 0:
            return unit_result

        # 集成测试
        print("🎯 运行欢迎礼包集成测试...")
        integration_result = self.run_command([
            "uv", "run", "pytest",
            "-m", "integration and reward",
            "-v",
            "--tb=short",
            "tests/integration/test_reward_*.py"
        ])

        return integration_result

    def run_coverage_report(self) -> int:
        """生成覆盖率报告"""
        cmd = [
            "uv", "run", "pytest",
            "--cov=src",
            "--cov-report=html:htmlcov/full",
            "--cov-report=xml",
            "--cov-report=term-missing",
            "--cov-fail-under=98",
            "tests"
        ]

        return self.run_command(cmd)

    def run_slow_tests(self) -> int:
        """运行慢速测试"""
        cmd = [
            "uv", "run", "pytest",
            "-m", "slow",
            "-v",
            "--tb=short"
        ]

        return self.run_command(cmd)

    def check_test_structure(self) -> int:
        """检查测试结构"""
        print("🔍 检查测试目录结构...")

        required_dirs = [
            "tests/unit",
            "tests/integration",
            "tests/functional",
            "tests/unit/domains/auth",
            "tests/unit/domains/points",
            "tests/unit/domains/reward",
            "tests/unit/domains/task",
            "tests/unit/domains/top3",
            "tests/unit/domains/user"
        ]

        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)

        if missing_dirs:
            print("❌ 缺少以下目录:")
            for dir_path in missing_dirs:
                print(f"   - {dir_path}")
            return 1

        print("✅ 测试目录结构正确")
        return 0

    def clean_test_artifacts(self) -> int:
        """清理测试产物"""
        print("🧹 清理测试产物...")

        artifacts = [
            ".pytest_cache",
            "htmlcov",
            ".coverage",
            "coverage.xml",
            "**/__pycache__",
            "**/*.pyc"
        ]

        for artifact in artifacts:
            if artifact.startswith("**"):
                # 递归删除
                for path in self.project_root.rglob(artifact[2:]):
                    if path.is_dir():
                        import shutil
                        shutil.rmtree(path)
                        print(f"   删除目录: {path}")
                    elif path.is_file():
                        path.unlink()
                        print(f"   删除文件: {path}")
            else:
                path = self.project_root / artifact
                if path.exists():
                    if path.is_dir():
                        import shutil
                        shutil.rmtree(path)
                        print(f"   删除目录: {path}")
                    else:
                        path.unlink()
                        print(f"   删除文件: {path}")

        print("✅ 测试产物清理完成")
        return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TaKeKe后端测试运行器")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(),
                       help="项目根目录 (默认: 当前目录)")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 单元测试
    subparsers.add_parser("unit", help="运行单元测试")

    # 集成测试
    subparsers.add_parser("integration", help="运行集成测试")

    # 功能测试
    subparsers.add_parser("functional", help="运行功能测试")

    # 所有测试
    subparsers.add_parser("all", help="运行所有测试")

    # 域测试
    domain_parser = subparsers.add_parser("domain", help="运行特定域的测试")
    domain_parser.add_argument("domain", help="域名 (auth/points/reward/task/top3/user/chat/focus)")
    domain_parser.add_argument("--type", default="unit",
                              choices=["unit", "integration", "functional"],
                              help="测试类型 (默认: unit)")

    # 欢迎礼包测试
    subparsers.add_parser("welcome-gift", help="运行欢迎礼包测试")

    # 覆盖率报告
    subparsers.add_parser("coverage", help="生成覆盖率报告")

    # 慢速测试
    subparsers.add_parser("slow", help="运行慢速测试")

    # 检查结构
    subparsers.add_parser("check", help="检查测试结构")

    # 清理产物
    subparsers.add_parser("clean", help="清理测试产物")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    runner = TestRunner(args.project_root)

    # 执行对应命令
    if args.command == "unit":
        return runner.run_unit_tests()
    elif args.command == "integration":
        return runner.run_integration_tests()
    elif args.command == "functional":
        return runner.run_functional_tests()
    elif args.command == "all":
        return runner.run_all_tests()
    elif args.command == "domain":
        return runner.run_domain_tests(args.domain, args.type)
    elif args.command == "welcome-gift":
        return runner.run_welcome_gift_tests()
    elif args.command == "coverage":
        return runner.run_coverage_report()
    elif args.command == "slow":
        return runner.run_slow_tests()
    elif args.command == "check":
        return runner.check_test_structure()
    elif args.command == "clean":
        return runner.clean_test_artifacts()
    else:
        print(f"❌ 未知命令: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())