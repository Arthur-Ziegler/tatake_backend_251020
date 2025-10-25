#!/usr/bin/env python3
"""
OpenAPI验证脚本

用于CI/CD流程中的自动化OpenAPI验证。
检查API参数正确性、一致性以及潜在的问题。

作者：TaTakeKe团队
版本：1.0.0
"""

import sys
import json
import requests
import argparse
from typing import Dict, Any, List
from pathlib import Path


class OpenAPIValidator:
    """OpenAPI验证器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.openapi_spec = None
        self.errors = []
        self.warnings = []

    def load_openapi_spec(self) -> bool:
        """加载OpenAPI规范"""
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            if response.status_code != 200:
                self.errors.append(f"无法获取OpenAPI规范: HTTP {response.status_code}")
                return False

            self.openapi_spec = response.json()
            return True

        except requests.exceptions.ConnectionError:
            self.errors.append("无法连接到API服务器")
            return False
        except requests.exceptions.Timeout:
            self.errors.append("API服务器响应超时")
            return False
        except json.JSONDecodeError as e:
            self.errors.append(f"OpenAPI JSON解析错误: {e}")
            return False

    def validate_no_args_kwargs(self) -> bool:
        """验证没有args/kwargs参数"""
        if not self.openapi_spec:
            return False

        paths = self.openapi_spec.get("paths", {})
        problematic_endpoints = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                parameters = operation.get("parameters", [])
                for param in parameters:
                    param_name = param.get("name", "")
                    if param_name in ["args", "kwargs"]:
                        problematic_endpoints.append({
                            "endpoint": f"{method.upper()} {path}",
                            "param_name": param_name,
                            "param_in": param.get("in", "unknown"),
                            "required": param.get("required", False)
                        })

        if problematic_endpoints:
            self.errors.append("发现args/kwargs参数:")
            for endpoint in problematic_endpoints:
                self.errors.append(
                    f"  - {endpoint['endpoint']}: "
                    f"参数 '{endpoint['param_name']}' "
                    f"({endpoint['param_in']}, required={endpoint['required']})"
                )
            return False

        return True

    def validate_schema_structure(self) -> bool:
        """验证schema结构"""
        if not self.openapi_spec:
            return False

        # 检查基本结构
        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in self.openapi_spec:
                self.errors.append(f"缺少必需字段: {field}")
                return False

        # 检查paths
        paths = self.openapi_spec["paths"]
        if not isinstance(paths, dict) or len(paths) == 0:
            self.errors.append("paths字段无效或为空")
            return False

        # 检查schemas
        components = self.openapi_spec.get("components", {})
        schemas = components.get("schemas", {})

        if schemas:
            for schema_name, schema_def in schemas.items():
                if not isinstance(schema_def, dict):
                    self.errors.append(f"Schema {schema_name} 不是有效的字典对象")
                    return False

        return True

    def validate_response_consistency(self) -> bool:
        """验证响应一致性"""
        if not self.openapi_spec:
            return False

        paths = self.openapi_spec.get("paths", {})
        inconsistent_endpoints = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete"]:
                    continue

                responses = operation.get("responses", {})
                success_response = responses.get("200") or responses.get("201")

                if not success_response:
                    # 没有成功响应定义
                    continue

                content = success_response.get("content", {})
                json_content = content.get("application/json", {})
                schema = json_content.get("schema", {})

                # 检查响应格式
                if not self._is_valid_response_schema(schema):
                    inconsistent_endpoints.append(f"{method.upper()} {path}")

        if inconsistent_endpoints:
            # 过滤掉允许的特殊端点
            allowed_exceptions = ["/health", "/docs", "/openapi.json", "/redoc"]
            filtered = [
                ep for ep in inconsistent_endpoints
                if not any(exc in ep for exc in allowed_exceptions)
            ]

            if filtered:
                self.warnings.append("以下端点响应格式可能不一致:")
                for endpoint in filtered:
                    self.warnings.append(f"  - {endpoint}")

        return True

    def _is_valid_response_schema(self, schema: Dict[str, Any]) -> bool:
        """检查响应schema是否有效"""
        if not isinstance(schema, dict):
            return False

        # 有$ref引用，认为是有效的
        if "$ref" in schema:
            return True

        # 有allOf定义，认为是有效的
        if "allOf" in schema:
            return True

        # 直接定义，检查是否包含基本字段
        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            # 理想的响应包含code, data, message
            return any(key in properties for key in ["code", "data", "message"])

        return True

    def validate_parameter_count(self) -> bool:
        """验证参数数量合理性"""
        if not self.openapi_spec:
            return False

        paths = self.openapi_spec.get("paths", {})
        high_param_endpoints = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete"]:
                    continue

                parameters = operation.get("parameters", [])
                param_count = len(parameters)

                # 排除查询端点
                if param_count > 5 and "list" not in path:
                    high_param_endpoints.append({
                        "endpoint": f"{method.upper()} {path}",
                        "count": param_count
                    })

        if high_param_endpoints:
            self.warnings.append("以下端点参数较多，建议简化:")
            for endpoint in high_param_endpoints:
                self.warnings.append(f"  - {endpoint['endpoint']}: {endpoint['count']} 个参数")

        return True

    def validate_duplicate_parameters(self) -> bool:
        """验证没有重复参数"""
        if not self.openapi_spec:
            return False

        paths = self.openapi_spec.get("paths", {})
        duplicate_endpoints = []

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete"]:
                    continue

                parameters = operation.get("parameters", [])
                param_names = [p.get("name") for p in parameters]

                seen = set()
                duplicates = set()
                for name in param_names:
                    if name in seen:
                        duplicates.add(name)
                    seen.add(name)

                if duplicates:
                    duplicate_endpoints.append({
                        "endpoint": f"{method.upper()} {path}",
                        "duplicates": list(duplicates)
                    })

        if duplicate_endpoints:
            self.errors.append("发现重复参数:")
            for endpoint in duplicate_endpoints:
                duplicates_str = ", ".join(endpoint["duplicates"])
                self.errors.append(f"  - {endpoint['endpoint']}: {duplicates_str}")
            return False

        return True

    def run_all_validations(self) -> bool:
        """运行所有验证"""
        print("🔍 开始OpenAPI验证...")

        # 加载OpenAPI规范
        if not self.load_openapi_spec():
            return False

        print(f"✅ 成功加载OpenAPI规范")

        # 运行各项验证
        validations = [
            ("基本结构验证", self.validate_schema_structure),
            ("args/kwargs参数检查", self.validate_no_args_kwargs),
            ("重复参数检查", self.validate_duplicate_parameters),
            ("响应一致性验证", self.validate_response_consistency),
            ("参数数量检查", self.validate_parameter_count),
        ]

        all_passed = True

        for validation_name, validation_func in validations:
            print(f"🧪 运行 {validation_name}...")
            if not validation_func():
                all_passed = False
                print(f"❌ {validation_name} 失败")
            else:
                print(f"✅ {validation_name} 通过")

        return all_passed

    def print_results(self):
        """打印验证结果"""
        if self.errors:
            print("\n❌ 验证失败:")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print("\n⚠️  警告:")
            for warning in self.warnings:
                print(f"  {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ 所有验证通过，OpenAPI规范正确！")

    def generate_report(self, output_file: str = None):
        """生成验证报告"""
        report = {
            "timestamp": str(Path.cwd()),
            "base_url": self.base_url,
            "validation_passed": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": {
                "error_count": len(self.errors),
                "warning_count": len(self.warnings),
                "total_issues": len(self.errors) + len(self.warnings)
            }
        }

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 验证报告已保存到: {output_file}")

        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenAPI验证工具")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API服务器地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--output",
        help="验证报告输出文件路径"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式，警告也视为失败"
    )

    args = parser.parse_args()

    # 创建验证器
    validator = OpenAPIValidator(args.base_url)

    # 运行验证
    validation_passed = validator.run_all_validations()

    # 打印结果
    validator.print_results()

    # 生成报告
    if args.output:
        validator.generate_report(args.output)

    # 根据结果决定退出码
    if args.strict:
        # 严格模式，警告也视为失败
        if validator.errors or validator.warnings:
            sys.exit(1)
    else:
        # 正常模式，只有错误才失败
        if validator.errors:
            sys.exit(1)

    print("\n🎉 OpenAPI验证完成！")
    sys.exit(0)


if __name__ == "__main__":
    main()