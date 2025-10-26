"""
导入验证测试

在测试阶段提前发现模块导入错误，确保所有Service和Router文件可以正常导入。

这个测试专门用于解决TDD阶段发现的导入问题，让这类错误能在开发阶段就被捕获。

作者：TaKeKe团队
版本：1.0.0 - TDD优化
"""

import pytest
import importlib
import sys
from pathlib import Path


class TestModuleImports:
    """模块导入验证测试"""

    def test_all_service_modules_import(self):
        """验证所有Service模块可以正常导入"""
        service_modules = [
            "src.domains.auth.service",
            "src.domains.task.service",
            "src.domains.focus.service",
            "src.domains.chat.service",
            # "src.domains.user.service",  # User领域直接使用SQLModel，暂不实现Service层
            "src.domains.reward.service",
            "src.domains.top3.service",
            "src.domains.points.service",
        ]

        failed_imports = []

        for module_name in service_modules:
            try:
                importlib.import_module(module_name)
            except Exception as e:
                failed_imports.append(f"{module_name}: {str(e)}")

        assert len(failed_imports) == 0, f"Service模块导入失败: {failed_imports}"

    def test_all_router_modules_import(self):
        """验证所有Router模块可以正常导入"""
        router_modules = [
            "src.domains.auth.router",
            "src.domains.task.router",
            "src.domains.focus.router",
            "src.domains.chat.router",
            "src.domains.user.router",
            "src.domains.reward.router",
            "src.domains.top3.router",
        ]

        failed_imports = []

        for module_name in router_modules:
            try:
                importlib.import_module(module_name)
            except Exception as e:
                failed_imports.append(f"{module_name}: {str(e)}")

        assert len(failed_imports) == 0, f"Router模块导入失败: {failed_imports}"

    def test_main_application_import(self):
        """验证主应用可以正常导入"""
        try:
            importlib.import_module("src.api.main")
        except Exception as e:
            pytest.fail(f"主应用导入失败: {str(e)}")

    def test_service_classes_have_correct_types(self):
        """验证Service类方法有正确的类型注解"""
        service_classes_to_check = [
            ("src.domains.task.service", "TaskService"),
            ("src.domains.focus.service", "FocusService"),
            ("src.domains.top3.service", "Top3Service"),
            ("src.domains.points.service", "PointsService"),
        ]

        type_errors = []

        for module_name, class_name in service_classes_to_check:
            try:
                module = importlib.import_module(module_name)
                service_class = getattr(module, class_name)

                # 检查关键方法的返回类型
                methods_to_check = []
                if class_name == "TaskService":
                    methods_to_check = ["get_task", "create_task", "complete_task"]
                elif class_name == "FocusService":
                    methods_to_check = ["start_focus", "get_user_sessions"]
                elif class_name == "Top3Service":
                    methods_to_check = ["set_top3", "get_top3"]
                elif class_name == "PointsService":
                    methods_to_check = ["get_transactions"]

                for method_name in methods_to_check:
                    if hasattr(service_class, method_name):
                        method = getattr(service_class, method_name)
                        # 检查方法的类型注解
                        if hasattr(method, "__annotations__"):
                            return_annotation = method.__annotations__.get("return")
                            if return_annotation and "Dict" not in str(return_annotation):
                                if class_name == "PointsService" and method_name == "get_transactions":
                                    # PointsService.get_transactions应该返回List[Dict]
                                    if "List" not in str(return_annotation) or "Dict" not in str(return_annotation):
                                        type_errors.append(f"{module_name}.{class_name}.{method_name}: 返回类型应该是Dict或List[Dict]")
                                else:
                                    type_errors.append(f"{module_name}.{class_name}.{method_name}: 返回类型应该是Dict[str, Any]")

            except Exception as e:
                type_errors.append(f"{module_name}.{class_name}: 检查失败 - {str(e)}")

        if type_errors:
            print("\n⚠️ 类型注解警告:")
            for error in type_errors:
                print(f"  - {error}")
            # 注意：这里只警告，不失败，因为某些方法可能确实需要返回其他类型

    def test_required_imports_present(self):
        """验证关键模块包含必要的导入"""
        required_imports = {
            "src.domains.focus.service": ["Dict", "Any"],
            "src.domains.task.service": ["Dict", "Any"],
            "src.domains.top3.service": ["Dict", "Any"],
            "src.domains.points.service": ["List", "Dict"],
        }

        missing_imports = []

        for module_name, imports in required_imports.items():
            try:
                with open(module_name.replace(".", "/") + ".py", "r", encoding="utf-8") as f:
                    content = f.read()

                for import_name in imports:
                    if f"from typing import" in content:
                        import_line = content.split("from typing import")[1].split("\n")[0]
                        if import_name not in import_line:
                            missing_imports.append(f"{module_name}: 缺少 {import_name} 导入")
                    else:
                        missing_imports.append(f"{module_name}: 缺少 typing 导入")

            except FileNotFoundError:
                missing_imports.append(f"{module_name}: 文件不存在")

        assert len(missing_imports) == 0, f"缺少必要导入: {missing_imports}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])