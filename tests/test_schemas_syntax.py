#!/usr/bin/env python3
"""
Schema 语法测试

TDD 测试：先写测试验证 schemas 语法正确性
"""

import pytest
import sys
import os
from typing import List, Dict, Any

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestSchemasSyntax:
    """Schema 语法测试类"""

    def test_import_task_schemas(self):
        """测试 task schemas 可以正常导入"""
        try:
            from src.domains.task.schemas import (
                CreateTaskRequest,
                UpdateTaskRequest,
                CompleteTaskRequest,
                TaskStatus,
                TaskPriority
            )
            assert CreateTaskRequest is not None
            assert UpdateTaskRequest is not None
            print("✅ Task schemas 导入成功")
        except Exception as e:
            pytest.fail(f"Task schemas 导入失败: {e}")

    def test_import_auth_schemas(self):
        """测试 auth schemas 可以正常导入"""
        try:
            from src.domains.auth.schemas import (
                WeChatRegisterRequest,
                WeChatLoginRequest,
                TokenRefreshRequest
            )
            assert WeChatRegisterRequest is not None
            assert WeChatLoginRequest is not None
            print("✅ Auth schemas 导入成功")
        except Exception as e:
            pytest.fail(f"Auth schemas 导入失败: {e}")

    def test_import_chat_schemas(self):
        """测试 chat schemas 可以正常导入"""
        try:
            from src.domains.chat.schemas import CreateSessionRequest
            assert CreateSessionRequest is not None
            print("✅ Chat schemas 导入成功")
        except Exception as e:
            pytest.fail(f"Chat schemas 导入失败: {e}")

    def test_validate_create_task_request(self):
        """测试 CreateTaskRequest 模型验证"""
        from src.domains.task.schemas import CreateTaskRequest

        # 测试有效的任务创建请求
        valid_data = {
            "title": "测试任务标题",
            "description": "测试任务描述",
            "status": "pending"
        }

        task = CreateTaskRequest(**valid_data)
        assert task.title == "测试任务标题"
        assert task.description == "测试任务描述"
        assert task.status == "pending"
        print("✅ CreateTaskRequest 模型验证成功")

    def test_validate_wechat_register(self):
        """测试 WeChatRegisterRequest 模型验证"""
        from src.domains.auth.schemas import WeChatRegisterRequest

        # 测试有效的微信注册请求
        valid_data = {
            "wechat_openid": "ox1234567890abcdef"
        }

        request = WeChatRegisterRequest(**valid_data)
        assert request.wechat_openid == "ox1234567890abcdef"
        print("✅ WeChatRegisterRequest 模型验证成功")

    def test_schema_has_examples(self):
        """测试所有 schema 都包含 example 参数"""
        schemas_to_check = [
            ("src.domains.auth.schemas", ["WeChatRegisterRequest", "WeChatLoginRequest", "TokenRefreshRequest"]),
            ("src.domains.task.schemas", ["CreateTaskRequest", "UpdateTaskRequest", "CompleteTaskRequest"]),
            ("src.domains.chat.schemas", ["CreateSessionRequest", "SendMessageRequest"])
        ]

        all_passed = True

        for module_path, model_names in schemas_to_check:
            try:
                module = __import__(module_path)

                for model_name in model_names:
                    model_class = getattr(module, model_name, None)
                    if model_class is None:
                        continue

                    # 检查模型是否有 example
                    schema = model_class.model_json_schema()
                    properties = schema.get("properties", {})

                    has_examples = False
                    for field_name, field_info in properties.items():
                        if "example" in field_info:
                            has_examples = True

                    if has_examples:
                        print(f"✅ {model_name} 包含示例数据")
                    else:
                        print(f"⚠️ {model_name} 缺少示例数据")
                        all_passed = False

            except ImportError:
                print(f"⚠️ 无法导入模块: {module_path}")
                all_passed = False

        assert all_passed, "部分模型缺少示例数据"

if __name__ == "__main__":
    print("🧪 运行 Schema 语法测试...")
    pytest.main([__file__, "-v"])
else:
    print("🧪 测试模块已导入")