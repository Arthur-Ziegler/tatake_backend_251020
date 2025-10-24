#!/usr/bin/env python3
"""
测试运行脚本

提供便捷的测试运行命令，支持：
1. 运行所有测试
2. 运行特定领域的测试
3. 运行特定类型的测试
4. 生成覆盖率报告

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并处理结果"""
    print(f"🚀 {description}")
    print(f"执行: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"✅ {description} - 成功")
    else:
        print(f"❌ {description} - 失败 (退出码: {result.returncode}")
        sys.exit(result.returncode)

    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TaKeKe后端测试运行器")
    parser.add_argument("--domain", "-d", help="运行特定领域的测试 (auth, task, reward, focus, chat, top3)")
    parser.add_argument("--type", "-t", help="运行特定类型的测试 (unit, integration, e2e, scenario)")
    parser.add_argument("--coverage", "-c", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--file", "-f", help="运行特定测试文件")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用的测试")

    args = parser.parse_args()

    # 基础pytest命令
    base_cmd = ["uv", "run", "pytest"]

    if args.verbose:
        base_cmd.append("-v")

    # 构建测试选择器
    test_path = "tests/"

    if args.domain:
        test_path += f"domains/{args.domain}/"
        description = f"运行 {args.domain} 领域测试"
    elif args.type:
        test_path += f"{args.type}/"
        description = f"运行 {args.type} 类型测试"
    elif args.file:
        test_path = args.file
        description = f"运行测试文件 {args.file}"
    elif args.list:
        description = "列出所有可用测试"
        cmd = base_cmd + ["--collect-only", "-q", "tests/"]
        run_command(cmd, description)
        return
    else:
        description = "运行所有测试"

    # 添加覆盖率选项
    if args.coverage:
        base_cmd.extend([
            "--cov=src",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml"
        ])
        description += " (包含覆盖率报告)"

    # 构建完整命令
    cmd = base_cmd + [test_path]

    # 运行测试
    run_command(cmd, description)

    # 如果生成了覆盖率报告，显示访问信息
    if args.coverage:
        print("\n📊 覆盖率报告已生成:")
        print("   - HTML报告: htmlcov/index.html")
        print("   - XML报告: coverage.xml")


def show_help():
    """显示帮助信息"""
    help_text = """
TaKeKe后端测试运行器使用指南:

基本用法:
  python scripts/run_tests.py                    # 运行所有测试
  python scripts/run_tests.py -v                 # 详细输出
  python scripts/run_tests.py -c                 # 运行测试并生成覆盖率报告

按领域运行:
  python scripts/run_tests.py -d auth           # 运行认证领域测试
  python scripts/run_tests.py -d task           # 运行任务领域测试
  python scripts/run_tests.py -d reward         # 运行奖励领域测试
  python scripts/run_tests.py -d focus          # 运行专注领域测试
  python scripts/run_tests.py -d chat           # 运行聊天领域测试
  python scripts/run_tests.py -d top3           # 运行Top3领域测试

按类型运行:
  python scripts/run_tests.py -t unit           # 运行单元测试
  python scripts/run_tests.py -t integration    # 运行集成测试
  python scripts/run_tests.py -t e2e            # 运行端到端测试
  python scripts/run_tests.py -t scenario       # 运行场景测试

运行特定文件:
  python scripts/run_tests.py -f tests/domains/auth/test_auth_models.py

列出所有测试:
  python scripts/run_tests.py -l

组合选项:
  python scripts/run_tests.py -d auth -c -v     # 运行认证测试，详细输出，生成覆盖率
"""
    print(help_text)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_help()
    else:
        main()