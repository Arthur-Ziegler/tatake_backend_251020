#!/usr/bin/env python3
"""
模块导入完整性测试

测试所有模块的导入完整性，确保没有遗留的导入错误。
特别针对Schema注册和OpenAPI生成进行测试。
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any
import importlib
import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ImportIntegrityTester:
    """模块导入完整性测试器"""

    def __init__(self):
        self.failed_imports: List[Tuple[str, str]] = []
        self.successful_imports: List[str] = []

    def test_all_domain_imports(self) -> bool:
        """测试所有域模块的导入"""
        print("🔍 测试所有域模块导入...")

        # 域模块列表
        domain_modules = [
            "src.domains.chat.schemas",
            "src.domains.chat.router",
            "src.domains.chat.models",
            "src.domains.chat.repository",
            "src.domains.chat.utils",
            "src.domains.task.schemas",
            "src.domains.task.router",
            "src.domains.focus.schemas",
            "src.domains.focus.router",
            "src.domains.focus.models",
            "src.domains.focus.repository",
            "src.domains.reward.schemas",
            "src.domains.reward.router",
            "src.domains.reward.models",
            "src.domains.reward.repository",
            "src.domains.top3.schemas",
            "src.domains.top3.router",
            "src.domains.user.schemas",
            "src.domains.user.router",
        ]

        success = True
        for module in domain_modules:
            if not self._test_import(module):
                success = False

        print(f"✅ 成功导入: {len(self.successful_imports)} 个模块")
        if self.failed_imports:
            print(f"❌ 导入失败: {len(self.failed_imports)} 个模块")
            for module, error in self.failed_imports:
                print(f"  - {module}: {error}")

        return success

    def test_schema_registry_imports(self) -> bool:
        """测试Schema注册表的导入"""
        print("🔍 测试Schema注册表导入...")

        try:
            from src.api.schema_registry import ALL_SCHEMAS, register_all_schemas_to_openapi
            print("✅ Schema注册表导入成功")

            # 验证所有Schema类都可以实例化
            for schema_name, schema_class in ALL_SCHEMAS.items():
                try:
                    # 尝试获取schema的json_schema
                    if hasattr(schema_class, 'model_json_schema'):
                        schema_class.model_json_schema()
                    print(f"  ✅ {schema_name}: Schema验证成功")
                except Exception as e:
                    print(f"  ❌ {schema_name}: Schema验证失败 - {e}")
                    return False

            return True
        except ImportError as e:
            print(f"❌ Schema注册表导入失败: {e}")
            return False

    def test_openapi_generation(self) -> bool:
        """测试OpenAPI生成"""
        print("🔍 测试OpenAPI生成...")

        try:
            # 使用子进程测试，避免影响当前环境
            result = subprocess.run([
                "python3", "-c",
                """
import sys
sys.path.insert(0, '.')
try:
    from src.api.main import app
    openapi_spec = app.openapi()
    print('SUCCESS: OpenAPI生成成功')
    print(f'Paths数量: {len(openapi_spec.get(\"paths\", {}))}')
    print(f'Schemas数量: {len(openapi_spec.get(\"components\", {}).get(\"schemas\", {}))}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"""
            ], capture_output=True, text=True, cwd=project_root)

            if result.returncode == 0:
                print("✅ OpenAPI生成成功")
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('SUCCESS') or line.startswith('Paths数量') or line.startswith('Schemas数量'):
                        print(f"  {line}")
                return True
            else:
                print(f"❌ OpenAPI生成失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ OpenAPI测试异常: {e}")
            return False

    def test_service_clients_imports(self) -> bool:
        """测试微服务客户端导入"""
        print("🔍 测试微服务客户端导入...")

        service_clients = [
            "src.services.chat_microservice_client",
            "src.services.task_microservice_client",
            "src.services.auth.client",
            "src.services.auth.jwt_validator",
            "src.services.auth.dev_jwt_validator",
        ]

        success = True
        for client in service_clients:
            if not self._test_import(client):
                success = False

        return success

    def test_main_application_import(self) -> bool:
        """测试主应用导入"""
        print("🔍 测试主应用导入...")

        return self._test_import("src.api.main")

    def _test_import(self, module_name: str) -> bool:
        """测试单个模块导入"""
        try:
            importlib.import_module(module_name)
            self.successful_imports.append(module_name)
            return True
        except Exception as e:
            self.failed_imports.append((module_name, str(e)))
            return False

    def run_all_tests(self) -> bool:
        """运行所有导入完整性测试"""
        print("=" * 60)
        print("🧪 开始模块导入完整性测试")
        print("=" * 60)

        tests = [
            ("域模块导入", self.test_all_domain_imports),
            ("Schema注册表导入", self.test_schema_registry_imports),
            ("微服务客户端导入", self.test_service_clients_imports),
            ("主应用导入", self.test_main_application_import),
            ("OpenAPI生成", self.test_openapi_generation),
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}测试:")
            try:
                result = test_func()
                results.append(result)
                print(f"{'✅ 通过' if result else '❌ 失败'}")
            except Exception as e:
                print(f"❌ 异常: {e}")
                results.append(False)

        print("\n" + "=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)

        passed = sum(results)
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0

        print(f"通过率: {passed}/{total} ({success_rate:.1f}%)")

        if passed == total:
            print("🎉 所有导入完整性测试通过！")
            return True
        else:
            print("🚨 部分测试失败，请检查上述错误信息")
            return False


def test_specific_imports():
    """pytest风格的测试函数"""
    tester = ImportIntegrityTester()

    # 测试关键模块导入
    assert tester._test_import("src.api.schema_registry"), "Schema注册表导入失败"
    assert tester._test_import("src.domains.chat.schemas"), "聊天schemas导入失败"
    assert tester._test_import("src.domains.chat.router"), "聊天router导入失败"


def test_openapi_generation():
    """测试OpenAPI生成"""
    result = subprocess.run([
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, '.')
try:
    from src.api.main import app
    openapi_spec = app.openapi()
    assert 'openapi' in openapi_spec
    assert 'paths' in openapi_spec
    assert 'components' in openapi_spec
    assert 'schemas' in openapi_spec['components']
    print('OpenAPI生成测试通过')
except Exception as e:
    print(f'OpenAPI生成测试失败: {e}')
    raise
"""
    ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

    assert result.returncode == 0, f"OpenAPI生成失败: {result.stderr}"


if __name__ == "__main__":
    tester = ImportIntegrityTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)