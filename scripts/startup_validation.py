#!/usr/bin/env python3
"""
应用启动验证脚本

在应用启动时验证关键组件的完整性，
确保没有导入错误、配置缺失等问题。
"""

import sys
import logging
from typing import List, Tuple
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class StartupValidator:
    """应用启动验证器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """执行所有验证检查"""
        print("🔍 开始应用启动验证...")

        checks = [
            self.validate_domain_imports,
            self.validate_schema_imports,
            self.validate_config_completeness,
            self.validate_database_initialization,
            self.validate_microservice_clients,
            self.validate_openapi_generation,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.errors.append(f"验证检查失败 {check.__name__}: {e}")

        self._report_results()
        return len(self.errors) == 0

    def validate_domain_imports(self):
        """验证域模块导入"""
        print("  📦 验证域模块导入...")

        domains = [
            "src.domains.chat.schemas",
            "src.domains.chat.router",
            "src.domains.chat.models",
            "src.domains.chat.repository",
            "src.domains.task.schemas",
            "src.domains.task.router",
            "src.domains.focus.schemas",
            "src.domains.focus.router",
            "src.domains.reward.schemas",
            "src.domains.reward.router",
        ]

        for domain in domains:
            try:
                __import__(domain)
                print(f"    ✅ {domain}")
            except ImportError as e:
                error_msg = f"域模块导入失败: {domain} - {e}"
                self.errors.append(error_msg)
                print(f"    ❌ {domain} - {e}")

    def validate_schema_imports(self):
        """验证Schema导入"""
        print("  📋 验证Schema导入...")

        try:
            # 测试聊天Schema
            from src.domains.chat.schemas import (
                ChatMessageRequest, ChatHistoryResponse, DeleteSessionResponse,
                ChatHealthResponse, SessionListItem, ChatHistoryMessage
            )
            print("    ✅ 聊天Schema导入成功")
        except ImportError as e:
            error_msg = f"聊天Schema导入失败: {e}"
            self.errors.append(error_msg)
            print(f"    ❌ 聊天Schema - {e}")

        try:
            # 测试其他域Schema
            from src.domains.task.schemas import TaskResponse, CreateTaskRequest
            from src.domains.focus.schemas import FocusSessionResponse
            from src.domains.reward.schemas import RewardResponse

            print("    ✅ 其他域Schema导入成功")
        except ImportError as e:
            error_msg = f"其他域Schema导入失败: {e}"
            self.errors.append(error_msg)
            print(f"    ❌ 其他域Schema - {e}")

    def validate_config_completeness(self):
        """验证配置完整性"""
        print("  ⚙️ 验证配置完整性...")

        try:
            from src.api.config import config

            required_configs = [
                ("chat_service_url", "聊天微服务URL"),
                ("chat_service_timeout", "聊天微服务超时"),
                ("task_service_url", "Task微服务URL"),
                ("task_service_timeout", "Task微服务超时"),
                ("auth_microservice_url", "认证微服务URL"),
                ("auth_project", "认证项目标识"),
            ]

            for config_name, description in required_configs:
                if hasattr(config, config_name):
                    value = getattr(config, config_name)
                    if value:
                        print(f"    ✅ {description}: {value}")
                    else:
                        warning_msg = f"配置项为空: {config_name} ({description})"
                        self.warnings.append(warning_msg)
                        print(f"    ⚠️ {description} - 值为空")
                else:
                    error_msg = f"缺少配置项: {config_name} ({description})"
                    self.errors.append(error_msg)
                    print(f"    ❌ {description} - 不存在")

        except Exception as e:
            error_msg = f"配置验证失败: {e}"
            self.errors.append(error_msg)
            print(f"    ❌ 配置验证 - {e}")

    def validate_database_initialization(self):
        """验证数据库初始化"""
        print("  🗄️ 验证数据库初始化...")

        try:
            from src.domains.chat.models import init_chat_database
            from src.domains.focus.models import init_focus_database
            from src.domains.reward.models import init_reward_database

            # 不实际初始化，只验证模块导入
            print("    ✅ 数据库模块导入成功")
        except Exception as e:
            error_msg = f"数据库初始化验证失败: {e}"
            self.errors.append(error_msg)
            print(f"    ❌ 数据库 - {e}")

    def validate_microservice_clients(self):
        """验证微服务客户端"""
        print("  🌐 验证微服务客户端...")

        try:
            from src.services.chat_microservice_client import get_chat_microservice_client
            from src.services.task_microservice_client import get_task_microservice_client
            from src.api.auth import AuthMicroserviceClient

            print("    ✅ 微服务客户端导入成功")
        except Exception as e:
            error_msg = f"微服务客户端验证失败: {e}"
            self.errors.append(error_msg)
            print(f"    ❌ 微服务客户端 - {e}")

    def validate_openapi_generation(self):
        """验证OpenAPI生成"""
        print("  📖 验证OpenAPI生成...")

        try:
            from src.api.main import app

            # 尝试生成OpenAPI
            openapi_spec = app.openapi()

            if "openapi" in openapi_spec and "paths" in openapi_spec:
                print("    ✅ OpenAPI生成成功")
            else:
                error_msg = "OpenAPI格式不正确"
                self.errors.append(error_msg)
                print(f"    ❌ OpenAPI - {error_msg}")

        except Exception as e:
            error_msg = f"OpenAPI生成失败: {e}"
            self.errors.append(error_msg)
            print(f"    ❌ OpenAPI - {e}")

    def _report_results(self):
        """报告验证结果"""
        print("\n" + "="*50)
        print("📊 验证结果报告")
        print("="*50)

        if self.errors:
            print(f"❌ 发现 {len(self.errors)} 个错误:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        if self.warnings:
            print(f"⚠️ 发现 {len(self.warnings)} 个警告:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        if not self.errors and not self.warnings:
            print("🎉 所有验证检查都通过了！")
        elif not self.errors:
            print("✅ 核心功能正常，但有一些警告需要注意")
        else:
            print("🚨 发现严重问题，请修复后重试")


def main():
    """主函数"""
    validator = StartupValidator()

    if validator.validate_all():
        print("\n🚀 应用启动验证通过，可以安全启动！")
        sys.exit(0)
    else:
        print("\n💥 应用启动验证失败，请修复问题后重试！")
        sys.exit(1)


if __name__ == "__main__":
    main()