#!/usr/bin/env python3
"""
Swagger UI 示例数据 TDD 测试

基于现有测试系统，专门测试 Field example 参数是否正确生成
TDD 原则：先写测试期望，再验证实现
"""

import pytest
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestSwaggerExamples:
    """Swagger UI 示例数据测试类"""

    def test_auth_schemas_have_examples(self):
        """测试 Auth schemas 都包含 example 参数"""
        from src.domains.auth.schemas import (
            WeChatRegisterRequest,
            WeChatLoginRequest,
            TokenRefreshRequest,
            GuestUpgradeRequest
        )

        auth_fields = [
            (WeChatRegisterRequest, "wechat_openid"),
            (WeChatLoginRequest, "wechat_openid"),
            (TokenRefreshRequest, "refresh_token"),
            (GuestUpgradeRequest, "wechat_openid")
        ]

        all_have_examples = True
        missing_examples = []

        for model_class, field_name in auth_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" not in field_info:
                    all_have_examples = False
                    missing_examples.append(f"{model_class.__name__}.{field_name}")

        print("🧪 Auth Schemas 示例检查:")
        for missing in missing_examples:
            print(f"   ❌ 缺少示例: {missing}")

        for model_class, field_name in auth_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" in field_info:
                    example = field_info["example"]
                    print(f"   ✅ {model_class.__name__}.{field_name}: {example}")

        assert all_have_examples, f"以下 Auth Schemas 缺少示例: {missing_examples}"

    def test_task_schemas_have_examples(self):
        """测试 Task schemas 都包含 example 参数"""
        from src.domains.task.schemas import (
            CreateTaskRequest,
            UpdateTaskRequest,
            CompleteTaskRequest,
            UncompleteTaskRequest
        )

        task_fields = [
            (CreateTaskRequest, "title"),
            (CreateTaskRequest, "description"),
            (CreateTaskRequest, "priority"),
            (CreateTaskRequest, "tags"),
            (UpdateTaskRequest, "title"),
            (CompleteTaskRequest, "task"),
            (CompleteTaskRequest, "mood_feedback")
        ]

        all_have_examples = True
        missing_examples = []

        for model_class, field_name in task_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" not in field_info:
                    all_have_examples = False
                    missing_examples.append(f"{model_class.__name__}.{field_name}")

        print("🧪 Task Schemas 示例检查:")
        for missing in missing_examples:
            print(f"   ❌ 缺少示例: {missing}")

        for model_class, field_name in task_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" in field_info:
                    example = field_info["example"]
                    print(f"   ✅ {model_class.__name__}.{field_name}: {example}")

        assert all_have_examples, f"以下 Task Schemas 缺少示例: {missing_examples}"

    def test_chat_schemas_have_examples(self):
        """测试 Chat schemas 都包含 example 参数"""
        from src.domains.chat.schemas import (
            CreateSessionRequest,
            SendMessageRequest
        )

        chat_fields = [
            (CreateSessionRequest, "title"),
            (SendMessageRequest, "message")
        ]

        all_have_examples = True
        missing_examples = []

        for model_class, field_name in chat_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" not in field_info:
                    all_have_examples = False
                    missing_examples.append(f"{model_class.__name__}.{field_name}")

        print("🧪 Chat Schemas 示例检查:")
        for missing in missing_examples:
            print(f"   ❌ 缺少示例: {missing}")

        for model_class, field_name in chat_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" in field_info:
                    example = field_info["example"]
                    print(f"   ✅ {model_class.__name__}.{field_name}: {example}")

        assert all_have_examples, f"以下 Chat Schemas 缺少示例: {missing_examples}"

    def test_focus_schemas_have_examples(self):
        """测试 Focus schemas 都包含 example 参数"""
        from src.domains.focus.schemas import (
            StartFocusRequest,
        FocusSessionResponse
        )

        focus_fields = [
            (StartFocusRequest, "task_id"),
            (FocusSessionResponse, "status")
        ]

        all_have_examples = True
        missing_examples = []

        for model_class, field_name in focus_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" not in field_info:
                    all_have_examples = False
                    missing_examples.append(f"{model_class.__name__}.{field_name}")

        print("🧪 Focus Schemas 示例检查:")
        for missing in missing_examples:
            print(f"   ❌ 缺少示例: {missing}")

        for model_class, field_name in focus_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" in field_info:
                    example = field_info["example"]
                    print(f"   ✅ {model_class.__name__}.{field_name}: {example}")

        assert all_have_examples, f"以下 Focus Schemas 缺少示例: {missing_examples}"

    def test_reward_schemas_have_examples(self):
        """测试 Reward schemas 都包含 example 参数"""
        from src.domains.reward.schemas import (
            RewardRedeemRequest,
            RedeemRecipeRequest,
            RecipeMaterial
        )

        reward_fields = [
            (RewardRedeemRequest, "recipe_id"),
            (RedeemRecipeRequest, "reward_id"),
            (RecipeMaterial, "quantity"),
            (RecipeMaterial, "reward_name")
        ]

        all_have_examples = True
        missing_examples = []

        for model_class, field_name in reward_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" not in field_info:
                    all_have_examples = False
                    missing_examples.append(f"{model_class.__name__}.{field_name}")

        print("🧪 Reward Schemas 示例检查:")
        for missing in missing_examples:
            print(f"   ❌ 缺少示例: {missing}")

        for model_class, field_name in reward_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" in field_info:
                    example = field_info["example"]
                    print(f"   ✅ {model_class.__name__}.{field_name}: {example}")

        assert all_have_examples, f"以下 Reward Schemas 缺少示例: {missing_examples}"

    def test_top3_schemas_have_examples(self):
        """测试 Top3 schemas 都包含 example 参数"""
        from src.domains.top3.schemas import (
            SetTop3Request,
            Top3Response,
            GetTop3Response
        )

        top3_fields = [
            (SetTop3Request, "date"),
            (SetTop3Request, "task_ids"),
            (Top3Response, "date"),
            (Top3Response, "points_consumed"),
            (GetTop3Response, "created_at")
        ]

        all_have_examples = True
        missing_examples = []

        for model_class, field_name in top3_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" not in field_info:
                    all_have_examples = False
                    missing_examples.append(f"{model_class.__name__}.{field_name}")

        print("🧪 Top3 Schemas 示例检查:")
        for missing in missing_examples:
            print(f"   ❌ 缺少示例: {missing}")

        for model_class, field_name in top3_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" in field_info:
                    example = field_info["example"]
                    print(f"   ✅ {model_class.__name__}.{field_name}: {example}")

        assert all_have_examples, f"以下 Top3 Schemas 缺少示例: {missing_examples}"

    def test_user_schemas_have_examples(self):
        """测试 User schemas 都包含 example 参数"""
        from src.domains.user.schemas import (
            UpdateProfileRequest,
            FeedbackRequest
        )

        user_fields = [
            (UpdateProfileRequest, "nickname"),
            (FeedbackRequest, "content")
        ]

        all_have_examples = True
        missing_examples = []

        for model_class, field_name in user_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" not in field_info:
                    all_have_examples = False
                    missing_examples.append(f"{model_class.__name__}.{field_name}")

        print("🧪 User Schemas 示例检查:")
        for missing in missing_examples:
            print(f"   ❌ 缺少示例: {missing}")

        for model_class, field_name in user_fields:
            schema = model_class.model_json_schema()
            properties = schema.get("properties", {})

            if field_name in properties:
                field_info = properties[field_name]
                if "example" in field_info:
                    example = field_info["example"]
                    print(f"   ✅ {model_class.__name__}.{field_name}: {example}")

        assert all_have_examples, f"以下 User Schemas 缺少示例: {missing_examples}"

if __name__ == "__main__":
    print("🧪 运行 Swagger UI 示例数据检查...")
    pytest.main([__file__, "-v"])
else:
    print("🧪 测试模块已导入")