#!/usr/bin/env python3
"""
测试覆盖率分析报告

生成各领域的详细覆盖率分析报告，帮助识别测试覆盖盲点。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, List, Any
import sys


def run_coverage_command(command: str) -> Dict[str, Any]:
    """运行覆盖率命令并解析结果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        if result.returncode != 0:
            print(f"命令执行失败: {command}")
            print(f"错误输出: {result.stderr}")
            return {}

        return {"stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return {}


def parse_coverage_output(coverage_text: str) -> Dict[str, Dict[str, int]]:
    """解析pytest覆盖率输出"""
    coverage_data = {}
    lines = coverage_text.strip().split('\n')

    for line in lines:
        if '%' in line and '.py' in line:
            parts = line.split()
            if len(parts) >= 5:
                try:
                    file_path = parts[0]
                    statements = int(parts[1])
                    missing = int(parts[2])
                    coverage = int(parts[3].rstrip('%'))

                    coverage_data[file_path] = {
                        "statements": statements,
                        "missing": missing,
                        "coverage_percent": coverage
                    }
                except (ValueError, IndexError):
                    continue

    return coverage_data


def generate_domain_report():
    """生成各领域覆盖率报告"""
    print("🔍 开始生成领域覆盖率报告...")

    # 各领域的测试路径
    domains = [
        "auth",
        "task",
        "reward",
        "focus",
        "top3",
        "points",
        "user",
        "chat"
    ]

    report = {
        "总体覆盖率": {},
        "各领域详情": {},
        "覆盖率排行": [],
        "建议改进": []
    }

    # 1. 获取总体覆盖率
    print("📊 计算总体覆盖率...")
    total_result = run_coverage_command(
        "uv run pytest --cov=src --cov-report=term-missing -q"
    )

    if total_result:
        total_lines = total_result["stdout"].strip().split('\n')
        for line in total_lines:
            if "TOTAL" in line and "%" in line:
                parts = line.split()
                if len(parts) >= 4:
                    total_statements = parts[0]
                    total_missing = parts[1]
                    total_coverage = parts[2]
                    report["总体覆盖率"] = {
                        "总语句数": total_statements,
                        "未覆盖语句数": total_missing,
                        "覆盖率百分比": total_coverage
                    }
                    print(f"   总体覆盖率: {total_coverage}")
                    break

    # 2. 分析各领域覆盖率
    print("\n📈 分析各领域覆盖率...")

    for domain in domains:
        print(f"   分析 {domain} 领域...")

        # 查找该领域的测试文件
        domain_test_path = f"tests/domains/{domain}"
        if os.path.exists(domain_test_path):
            # 运行该领域的测试覆盖率
            domain_result = run_coverage_command(
                f"uv run pytest {domain_test_path} --cov=src/domains/{domain} --cov-report=term-missing -q"
            )

            if domain_result:
                lines = domain_result["stdout"].strip().split('\n')
                for line in lines:
                    if "TOTAL" in line and "%" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            coverage_percent = parts[2]
                            report["各领域详情"][domain] = {
                                "覆盖率": coverage_percent,
                                "测试文件存在": True
                            }

                            # 保存到排行榜
                            try:
                                coverage_value = int(coverage_percent.rstrip('%'))
                                report["覆盖率排行"].append((domain, coverage_value))
                            except ValueError:
                                pass
                            break
                else:
                    report["各领域详情"][domain] = {
                        "覆盖率": "0%",
                        "测试文件存在": True,
                        "状态": "测试执行失败"
                    }
        else:
            report["各领域详情"][domain] = {
                "覆盖率": "0%",
                "测试文件存在": False,
                "状态": "无测试文件"
            }

    # 3. 排序覆盖率排行榜
    report["覆盖率排行"].sort(key=lambda x: x[1], reverse=True)

    # 4. 生成改进建议
    print("\n💡 生成改进建议...")
    suggestions = []

    # 基于覆盖率排行提供建议
    for domain, coverage in report["覆盖率排行"]:
        if coverage < 50:
            suggestions.append(f"{domain} 领域覆盖率过低 ({coverage}%)，建议增加单元测试")
        elif coverage < 80:
            suggestions.append(f"{domain} 领域覆盖率中等 ({coverage}%)，建议补充边界测试")

    # 检查哪些领域没有测试
    for domain, info in report["各领域详情"].items():
        if not info.get("测试文件存在", False):
            suggestions.append(f"{domain} 领域完全缺少测试，需要创建基础测试套件")

    report["建议改进"] = suggestions

    return report


def print_report(report: Dict[str, Any]):
    """打印格式化的覆盖率报告"""
    print("\n" + "="*60)
    print("📋 TaTakeKe 后端测试覆盖率分析报告")
    print("="*60)

    # 总体覆盖率
    print(f"\n📊 总体覆盖率: {report['总体覆盖率'].get('覆盖率百分比', 'N/A')}")
    if '总语句数' in report['总体覆盖率']:
        print(f"   总语句数: {report['总体覆盖率']['总语句数']}")
        print(f"   未覆盖语句数: {report['总体覆盖率']['未覆盖语句数']}")

    # 各领域详情
    print(f"\n📈 各领域覆盖率详情:")
    print("-" * 40)
    for domain, coverage in report["覆盖率排行"]:
        status = report["各领域详情"][domain].get("状态", "正常")
        print(f"   {domain:10} {coverage:3}% ({status})")

    # 覆盖率分析
    print(f"\n📊 覆盖率分析:")
    high_coverage = [(d, c) for d, c in report["覆盖率排行"] if c >= 80]
    medium_coverage = [(d, c) for d, c in report["覆盖率排行"] if 50 <= c < 80]
    low_coverage = [(d, c) for d, c in report["覆盖率排行"] if c < 50]

    print(f"   高覆盖率 (≥80%): {len(high_coverage)} 个领域")
    for domain, coverage in high_coverage:
        print(f"     ✅ {domain}: {coverage}%")

    print(f"   中等覆盖率 (50-79%): {len(medium_coverage)} 个领域")
    for domain, coverage in medium_coverage:
        print(f"     ⚠️  {domain}: {coverage}%")

    print(f"   低覆盖率 (<50%): {len(low_coverage)} 个领域")
    for domain, coverage in low_coverage:
        print(f"     ❌ {domain}: {coverage}%")

    # 改进建议
    if report["建议改进"]:
        print(f"\n💡 改进建议:")
        print("-" * 40)
        for i, suggestion in enumerate(report["建议改进"], 1):
            print(f"   {i}. {suggestion}")

    # 总结
    print(f"\n📋 总结:")
    total_domains = len(report["各领域详情"])
    tested_domains = sum(1 for info in report["各领域详情"].values() if info.get("测试文件存在", False))
    high_cov_domains = len(high_coverage)
    target_achieved = report["总体覆盖率"].get("覆盖率百分比", "0%").rstrip('%').isdigit() and int(report["总体覆盖率"]["覆盖率百分比"].rstrip('%')) >= 80

    print(f"   • 总领域数: {total_domains}")
    print(f"   • 有测试的领域: {tested_domains}")
    print(f"   • 高覆盖率领域: {high_cov_domains}")
    print(f"   • 80%目标达成: {'✅ 是' if target_achieved else '❌ 否'}")

    print("\n" + "="*60)


def save_report_to_file(report: Dict[str, Any], filename: str = "docs/测试结果/coverage_report.md"):
    """保存报告到文件"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# TaTakeKe 后端测试覆盖率分析报告\n\n")
        f.write(f"生成时间: {subprocess.run('date', shell=True, capture_output=True, text=True).stdout.strip()}\n\n")

        f.write("## 总体覆盖率\n\n")
        f.write(f"- **覆盖率**: {report['总体覆盖率'].get('覆盖率百分比', 'N/A')}\n")
        if '总语句数' in report['总体覆盖率']:
            f.write(f"- **总语句数**: {report['总体覆盖率']['总语句数']}\n")
            f.write(f"- **未覆盖语句数**: {report['总体覆盖率']['未覆盖语句数']}\n")

        f.write("\n## 各领域覆盖率详情\n\n")
        f.write("| 领域 | 覆盖率 | 状态 |\n")
        f.write("|------|--------|------|\n")

        for domain, coverage in report["覆盖率排行"]:
            status = report["各领域详情"][domain].get("状态", "正常")
            f.write(f"| {domain} | {coverage}% | {status} |\n")

        f.write("\n## 改进建议\n\n")
        for i, suggestion in enumerate(report["建议改进"], 1):
            f.write(f"{i}. {suggestion}\n")

        f.write("\n## 覆盖率分析\n\n")
        high_coverage = [(d, c) for d, c in report["覆盖率排行"] if c >= 80]
        medium_coverage = [(d, c) for d, c in report["覆盖率排行"] if 50 <= c < 80]
        low_coverage = [(d, c) for d, c in report["覆盖率排行"] if c < 50]

        f.write(f"- 高覆盖率 (≥80%): {len(high_coverage)} 个领域\n")
        for domain, coverage in high_coverage:
            f.write(f"  - {domain}: {coverage}%\n")

        f.write(f"- 中等覆盖率 (50-79%): {len(medium_coverage)} 个领域\n")
        for domain, coverage in medium_coverage:
            f.write(f"  - {domain}: {coverage}%\n")

        f.write(f"- 低覆盖率 (<50%): {len(low_coverage)} 个领域\n")
        for domain, coverage in low_coverage:
            f.write(f"  - {domain}: {coverage}%\n")

    print(f"📄 报告已保存到: {filename}")


def main():
    """主函数"""
    print("🚀 开始生成测试覆盖率分析报告...")

    try:
        # 生成报告
        report = generate_domain_report()

        # 打印报告
        print_report(report)

        # 保存报告到文件
        save_report_to_file(report)

        print(f"\n✅ 覆盖率报告生成完成!")

    except Exception as e:
        print(f"❌ 生成报告时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()