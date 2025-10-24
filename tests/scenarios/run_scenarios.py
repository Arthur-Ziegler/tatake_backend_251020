#!/usr/bin/env python3
"""
场景测试运行脚本

提供便捷的场景测试运行方式，支持多种运行模式。

使用方法:
    python run_scenarios.py                 # 运行所有场景测试
    python run_scenarios.py --task          # 只运行任务流程测试
    python run_scenarios.py --top3          # 只运行Top3流程测试
    python run_scenarios.py --focus         # 只运行Focus流程测试
    python run_scenarios.py --combined      # 只运行跨模块组合测试
    python run_scenarios.py --priority a    # 运行A优先级测试
    python run_scenarios.py --fast          # 快速模式（跳过慢速测试）
    python run_scenarios.py --report        # 生成HTML报告
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def check_prerequisites():
    """检查运行前提条件"""
    print("🔍 检查运行前提条件...")

    # 检查是否在项目根目录
    if not Path("pyproject.toml").exists():
        print("❌ 错误: 请在项目根目录运行此脚本")
        return False

    # 检查后端服务是否运行
    import requests
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务运行正常")
        else:
            print(f"❌ 后端服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ 无法连接到后端服务，请确保服务运行在 http://localhost:8001")
        return False

    # 检查uv是否安装
    success, _, _ = run_command("uv --version")
    if success:
        print("✅ uv 包管理器已安装")
    else:
        print("❌ 错误: 请先安装 uv 包管理器")
        return False

    return True


def build_pytest_command(args):
    """构建pytest命令"""
    base_cmd = "uv run pytest tests/scenarios"

    # 添加详细输出
    if args.verbose:
        base_cmd += " -v -s"
    else:
        base_cmd += " -v"

    # 添加标记过滤
    if args.task:
        base_cmd += " -m task_flow"
    elif args.top3:
        base_cmd += " -m top3_flow"
    elif args.focus:
        base_cmd += " -m focus_flow"
    elif args.combined:
        base_cmd += " -m combined_flow"
    elif args.priority:
        priority_map = {
            "a": "task_flow or top3_flow",
            "b": "top3_flow",
            "c": "focus_flow",
            "d": "combined_flow"
        }
        if args.priority.lower() in priority_map:
            base_cmd += f" -m \"{priority_map[args.priority.lower()]}\""
    else:
        base_cmd += " -m scenario"

    # 添加报告选项
    if args.report:
        base_cmd += " --html=scenario_test_report.html --self-contained-html"

    # 添加并行选项
    if args.parallel:
        base_cmd += f" -n {args.parallel}"

    # 添加覆盖选项
    if args.cover:
        base_cmd += " --cov=src --cov-report=term-missing"

    # 添加失败时停止选项
    if args.failfast:
        base_cmd += " -x"

    # 添加重试选项
    if args.reruns:
        base_cmd += f" --reruns {args.reruns}"

    return base_cmd


def main():
    parser = argparse.ArgumentParser(
        description="运行TaKeKe API场景测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 运行所有场景测试
  %(prog)s --task                   # 只运行任务流程测试
  %(prog)s --priority a             # 运行A优先级测试
  %(prog)s --fast                   # 快速模式
  %(prog)s --report --parallel 4    # 并行运行并生成报告
        """
    )

    # 测试选择选项
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--task", action="store_true", help="只运行任务流程测试")
    test_group.add_argument("--top3", action="store_true", help="只运行Top3流程测试")
    test_group.add_argument("--focus", action="store_true", help="只运行Focus流程测试")
    test_group.add_argument("--combined", action="store_true", help="只运行跨模块组合测试")
    test_group.add_argument("--priority", choices=["a", "b", "c", "d"], help="按优先级运行测试")

    # 运行选项
    parser.add_argument("--fast", action="store_true", help="快速模式（跳过慢速测试）")
    parser.add_argument("--parallel", type=int, metavar="N", help="并行运行测试（N个进程）")
    parser.add_argument("--report", action="store_true", help="生成HTML测试报告")
    parser.add_argument("--cover", action="store_true", help="显示代码覆盖率")
    parser.add_argument("--failfast", "-x", action="store_true", help="遇到失败时立即停止")
    parser.add_argument("--reruns", type=int, metavar="N", help="失败测试重试次数")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    # 其他选项
    parser.add_argument("--skip-check", action="store_true", help="跳过前提条件检查")

    args = parser.parse_args()

    print("🧪 TaKeKe API场景测试运行器")
    print("=" * 50)

    # 检查前提条件
    if not args.skip_check:
        if not check_prerequisites():
            print("\n❌ 前提条件检查失败，请解决问题后重试")
            sys.exit(1)

    print()

    # 构建测试命令
    pytest_cmd = build_pytest_command(args)

    # 显示运行信息
    print("📋 运行配置:")
    if args.task:
        print("   • 测试范围: 任务流程测试")
    elif args.top3:
        print("   • 测试范围: Top3流程测试")
    elif args.focus:
        print("   • 测试范围: Focus流程测试")
    elif args.combined:
        print("   • 测试范围: 跨模块组合测试")
    elif args.priority:
        print(f"   • 测试范围: {args.priority.upper()}优先级测试")
    else:
        print("   • 测试范围: 所有场景测试")

    if args.parallel:
        print(f"   • 并行进程: {args.parallel}")
    if args.report:
        print("   • 生成报告: HTML")
    if args.cover:
        print("   • 代码覆盖率: 是")

    print()

    # 运行测试
    print("🚀 开始运行场景测试...")
    print(f"执行命令: {pytest_cmd}")
    print("-" * 50)

    success, stdout, stderr = run_command(pytest_cmd)

    # 显示结果
    print(stdout)
    if stderr:
        print("错误输出:")
        print(stderr)

    print("-" * 50)

    if success:
        print("✅ 场景测试运行完成！")
        if args.report:
            print("📊 HTML报告已生成: scenario_test_report.html")
    else:
        print("❌ 场景测试运行失败")
        sys.exit(1)


if __name__ == "__main__":
    main()