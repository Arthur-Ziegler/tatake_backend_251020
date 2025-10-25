"""
API端点发现工具

用于扫描FastAPI应用中的所有端点，并分析测试覆盖率。
支持按域分组统计，生成详细的覆盖率报告。

作者：TaKeKe团队
版本：1.0.0 - API覆盖率分析工具
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.routing import APIRoute


@dataclass
class EndpointInfo:
    """端点信息"""
    path: str
    method: str
    name: str
    module: str
    domain: str = ""
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class HTTPCallVisitor(ast.NodeVisitor):
    """AST访问者，用于提取测试代码中的HTTP调用"""

    def __init__(self):
        self.http_calls = set()
        self.import_aliases = {}  # 存储导入别名

    def visit_Import(self, node):
        """处理import语句"""
        for alias in node.names:
            if alias.name == 'httpx':
                self.import_aliases[alias.asname or 'httpx'] = 'httpx'
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """处理from...import语句"""
        if node.module == 'httpx':
            for alias in node.names:
                self.import_aliases[alias.asname or alias.name] = 'httpx'
        self.generic_visit(node)

    def visit_Call(self, node):
        """处理函数调用"""
        # 检查是否是HTTP调用
        if isinstance(node.func, ast.Attribute):
            # 处理 client.get/post/put/delete/patch 形式的调用
            if node.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                method = node.func.attr.upper()
                url = self._extract_url(node)
                if url:
                    self.http_calls.add(f"{method} {url}")

        # 处理 httpx.get/post 等直接调用
        elif isinstance(node.func, ast.Name):
            if node.func.id in ['get', 'post', 'put', 'delete', 'patch']:
                method = node.func.id.upper()
                url = self._extract_url(node)
                if url:
                    self.http_calls.add(f"{method} {url}")

        self.generic_visit(node)

    def _extract_url(self, node) -> str:
        """从AST节点中提取URL"""
        # 获取调用参数
        if not node.args:
            return ""

        first_arg = node.args[0]

        # 处理字符串字面量
        if isinstance(first_arg, ast.Constant):
            if isinstance(first_arg.value, str):
                return first_arg.value

        # 处理f-string
        elif isinstance(first_arg, ast.JoinedStr):
            parts = []
            for value in first_arg.values:
                if isinstance(value, ast.Constant):
                    parts.append(str(value.value))
                elif isinstance(value, ast.FormattedValue):
                    # 对于f-string中的变量，我们用占位符代替
                    parts.append("{param}")
            return "".join(parts)

        # 处理变量（无法确定具体值，返回占位符）
        elif isinstance(first_arg, ast.Name):
            return "{variable}"

        return ""


class EndpointDiscovery:
    """端点发现工具"""

    def __init__(self, app: FastAPI):
        self.app = app
        self.test_dir = Path("tests")

    def get_all_endpoints(self) -> List[EndpointInfo]:
        """获取所有API端点"""
        endpoints = []

        for route in self.app.routes:
            if isinstance(route, APIRoute):
                # 提取域信息
                domain = self._extract_domain_from_path(route.path)

                # 为每个HTTP方法创建端点信息
                for method in route.methods:
                    if method != "HEAD" and method != "OPTIONS":  # 忽略HEAD和OPTIONS
                        endpoint = EndpointInfo(
                            path=route.path,
                            method=method,
                            name=route.name,
                            module=route.endpoint.__module__,
                            domain=domain,
                            tags=list(route.tags) if route.tags else []
                        )
                        endpoints.append(endpoint)

        return endpoints

    def get_tested_endpoints(self, test_dir: str = "tests") -> Set[str]:
        """扫描测试代码，找出已测试的端点"""
        tested = set()
        test_path = Path(test_dir)

        if not test_path.exists():
            return tested

        # 递归扫描所有Python测试文件
        for py_file in test_path.rglob("*.py"):
            if py_file.name.startswith("test_"):
                tested.update(self._extract_http_calls_from_file(py_file))

        return tested

    def _extract_http_calls_from_file(self, file_path: Path) -> Set[str]:
        """从单个测试文件中提取HTTP调用"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析AST
            tree = ast.parse(content)
            visitor = HTTPCallVisitor()
            visitor.visit(tree)

            return visitor.http_calls
        except Exception as e:
            print(f"警告：无法解析文件 {file_path}: {e}")
            return set()

    def _extract_domain_from_path(self, path: str) -> str:
        """从路径中提取域信息"""
        # 根据路径模式推断域
        if "/auth" in path:
            return "auth"
        elif "/tasks" in path:
            if "special/top3" in path:
                return "top3"
            return "tasks"
        elif "/points" in path:
            return "points"
        elif "/rewards" in path:
            return "reward"
        elif "/chat" in path:
            return "chat"
        elif "/focus" in path:
            return "focus"
        elif "/user" in path:
            return "user"
        elif path in ["/", "/health", "/api/v3/info", "/test-cors"]:
            return "system"
        else:
            return "unknown"

    def generate_coverage_report(self) -> Dict:
        """生成覆盖率报告"""
        all_endpoints = self.get_all_endpoints()
        tested_endpoints = self.get_tested_endpoints()

        # 将端点信息转换为字符串格式进行比较
        endpoint_strings = set(
            f"{ep.method} {ep.path}" for ep in all_endpoints
        )

        # 统计总体覆盖率
        tested_count = len(endpoint_strings & tested_endpoints)
        total_count = len(endpoint_strings)
        coverage_rate = tested_count / total_count if total_count > 0 else 0

        # 按域统计
        domain_stats = {}
        for endpoint in all_endpoints:
            domain = endpoint.domain
            if domain not in domain_stats:
                domain_stats[domain] = {
                    "total": 0,
                    "tested": 0,
                    "endpoints": []
                }

            domain_stats[domain]["total"] += 1
            endpoint_str = f"{endpoint.method} {endpoint.path}"
            if endpoint_str in tested_endpoints:
                domain_stats[domain]["tested"] += 1
                domain_stats[domain]["endpoints"].append({
                    "endpoint": endpoint_str,
                    "name": endpoint.name,
                    "tested": True
                })
            else:
                domain_stats[domain]["endpoints"].append({
                    "endpoint": endpoint_str,
                    "name": endpoint.name,
                    "tested": False
                })

        # 计算各域覆盖率
        for domain in domain_stats:
            stats = domain_stats[domain]
            stats["coverage_rate"] = stats["tested"] / stats["total"] if stats["total"] > 0 else 0

        # 找出未测试的端点
        untested = [
            f"{ep.method} {ep.path}"
            for ep in all_endpoints
            if f"{ep.method} {ep.path}" not in tested_endpoints
        ]

        return {
            "total": total_count,
            "tested": tested_count,
            "coverage_rate": coverage_rate,
            "untested_endpoints": untested,
            "by_domain": domain_stats,
            "all_endpoints": [
                {
                    "method": ep.method,
                    "path": ep.path,
                    "name": ep.name,
                    "domain": ep.domain,
                    "tested": f"{ep.method} {ep.path}" in tested_endpoints
                }
                for ep in all_endpoints
            ]
        }

    def save_coverage_report(self, output_path: str = "tests/reports/coverage_report.json"):
        """保存覆盖率报告到文件"""
        report = self.generate_coverage_report()

        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"覆盖率报告已保存到: {output_path}")
        return report


def main():
    """命令行入口"""
    from src.api.main import app

    discovery = EndpointDiscovery(app)
    report = discovery.generate_coverage_report()

    print(f"总端点数: {report['total']}")
    print(f"已测试端点数: {report['tested']}")
    print(f"覆盖率: {report['coverage_rate']:.1%}")

    print("\n按域统计:")
    for domain, stats in report['by_domain'].items():
        print(f"  {domain}: {stats['tested']}/{stats['total']} ({stats['coverage_rate']:.1%})")

    if report['untested_endpoints']:
        print(f"\n未测试的端点 ({len(report['untested_endpoints'])}):")
        for endpoint in report['untested_endpoints']:
            print(f"  - {endpoint}")

    # 保存报告
    discovery.save_coverage_report()


if __name__ == "__main__":
    main()