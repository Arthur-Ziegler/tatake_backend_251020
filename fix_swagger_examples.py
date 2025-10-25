#!/usr/bin/env python3
"""
Swagger UI 示例数据修复脚本
为所有 Field 自动添加示例数据，解决 Swagger UI 只显示 "string" 的问题
"""

import re
import os
from typing import Dict, Any, List

def get_field_example(field_name: str, field_type: str, description: str = "") -> str:
    """根据字段名和类型生成示例数据"""
    field_name_lower = field_name.lower()

    # 基于字段名生成示例
    if "openid" in field_name_lower or "wechat" in field_name_lower:
        return "ox1234567890abcdef"
    elif field_name_lower in ["title", "name", "reward_name", "recipe_name"]:
        return "示例标题" if "title" in field_name_lower or "name" in field_name_lower else "示例奖品名称"
    elif field_name_lower in ["description", "note", "feedback", "comment"]:
        return "这是示例描述内容"
    elif field_name_lower in ["token", "refresh_token"]:
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example"
    elif "email" in field_name_lower:
        return "example@domain.com"
    elif "phone" in field_name_lower:
        return "13800138000"
    elif "password" in field_name_lower:
        return "password123"
    elif field_name_lower in ["amount", "quantity", "points"]:
        return 100
    elif field_name_lower in ["session_id", "task_id", "user_id", "reward_id", "recipe_id", "id"]:
        return "550e8400-e29b-41d4-a716-446655440000"
    elif "date" in field_name_lower or "time" in field_name_lower:
        return "2025-01-15"
    elif field_name_lower in ["status", "type", "priority", "difficulty"]:
        if field_name_lower == "status":
            return "active"
        elif field_name_lower == "type":
            return "focus"
        elif field_name_lower == "priority":
            return "high"
        elif field_name_lower == "difficulty":
            return "medium"
    elif field_name_lower in ["tags", "task_ids"]:
        if field_name_lower == "tags":
            return ["工作", "重要", "紧急"]
        elif field_name_lower == "task_ids":
            return ["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"]
    elif field_name_lower in ["content", "message", "user_message"]:
        return "这是示例消息内容"
    elif field_name_lower in ["duration", "minutes", "seconds"]:
        return 25
    elif field_name_lower in ["completed"]:
        return True
    elif field_name_lower in ["is_deleted", "deleted"]:
        return False

    # 默认示例
    if field_type == "str":
        return "示例文本"
    elif field_type == "int":
        return 100
    elif field_type == "bool":
        return True
    elif field_type == "List[str]" or "list" in field_type:
        return ["项目1", "项目2", "项目3"]
    else:
        return "示例值"

def fix_file_examples(file_path: str) -> bool:
    """修复单个文件的示例数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 匹配 Field 定义的正则表达式
        field_pattern = r'(\w+)\s*:\s*([A-Za-z_<>[\]]+)\s*=\s*Field\(\s*([^,]+),\s*description=[^)]+\)'

        def replace_field(match):
            field_name = match.group(1)
            field_type = match.group(2)
            other_params = match.group(3)

            # 跳过已经有示例的字段
            if 'example=' in other_params:
                return match.group(0)

            # 生成示例
            example = get_field_example(field_name, field_type)

            # 添加 example 参数
            if other_params.strip():
                new_params = other_params.rstrip() + f',\n        example="{example}"'
            else:
                new_params = f'example="{example}"'

            return f'{field_name}: {field_type} = Field({new_params}, description='

        # 应用替换
        new_content = re.sub(field_pattern, replace_field, content, flags=re.MULTILINE)

        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False

    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def main():
    """主修复函数"""
    # 需要修复的文件列表
    files_to_fix = [
        "src/domains/auth/schemas.py",
        "src/domains/task/schemas.py",
        "src/domains/chat/schemas.py",
        "src/domains/user/schemas.py",
        "src/domains/focus/schemas.py",
        "src/domains/reward/schemas.py",
        "src/domains/top3/schemas.py"
    ]

    total_fixes = 0

    print("🔧 开始修复 Swagger UI 示例数据...")
    print("=" * 60)

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"📝 修复文件: {file_path}")
            if fix_file_examples(file_path):
                total_fixes += 1
                print("   ✅ 修复成功")
            else:
                print("   ℹ️  无需修复或已是最新")
        else:
            print(f"   ❌ 文件不存在: {file_path}")

    print("=" * 60)
    print(f"🎉 修复完成！共修复了 {total_fixes} 个文件")
    print("🚀 重启服务后，Swagger UI 将显示正确的示例数据！")
    print("💡 运行: uv run -m src.api.main")

if __name__ == "__main__":
    main()