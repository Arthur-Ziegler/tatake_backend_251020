"""
验证番茄钟和UserReward代码清理工作

确保所有番茄钟相关字段和UserReward残留代码已被彻底清理。

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import pytest
import ast
import os
from pathlib import Path


class TestCodeCleanup:
    """验证代码清理工作"""

    def test_no_tomato_clock_fields_in_schemas(self):
        """验证schemas.py中没有番茄钟字段"""
        schemas_path = Path("src/domains/task/schemas.py")

        if not schemas_path.exists():
            pytest.skip("schemas.py文件不存在")

        with open(schemas_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有番茄钟相关字段
        forbidden_fields = [
            'estimated_pomodoros',
            'actual_pomodoros',
            'pomodoro_count',
            '番茄钟'
        ]

        for field in forbidden_fields:
            assert field not in content, f"发现禁用字段: {field} 仍然存在于 schemas.py 中"

    def test_no_tomato_clock_fields_in_service(self):
        """验证service.py中没有番茄钟字段"""
        service_path = Path("src/domains/task/service.py")

        if not service_path.exists():
            pytest.skip("service.py文件不存在")

        with open(service_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有番茄钟相关字段
        forbidden_fields = [
            'estimated_pomodoros',
            'actual_pomodoros',
            'pomodoro_count',
            '番茄钟'
        ]

        for field in forbidden_fields:
            assert field not in content, f"发现禁用字段: {field} 仍然存在于 service.py 中"

    def test_no_user_reward_imports_in_reward_service(self):
        """验证reward/service.py中没有UserReward导入"""
        reward_service_path = Path("src/domains/reward/service.py")

        if not reward_service_path.exists():
            pytest.skip("reward/service.py文件不存在")

        with open(reward_service_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有UserReward相关导入
        assert 'UserReward' not in content, "UserReward 仍然存在于 reward/service.py 中"

    def test_no_user_reward_in_task_schemas(self):
        """验证task/schemas.py中没有UserReward引用"""
        task_schemas_path = Path("src/domains/task/schemas.py")

        if not task_schemas_path.exists():
            pytest.skip("task/schemas.py文件不存在")

        with open(task_schemas_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有UserReward相关引用
        assert 'UserReward' not in content, "UserReward 仍然存在于 task/schemas.py 中"

    def test_no_user_reward_in_task_repository(self):
        """验证task/repository.py中没有UserReward导入"""
        task_repo_path = Path("src/domains/task/repository.py")

        if not task_repo_path.exists():
            pytest.skip("task/repository.py文件不存在")

        with open(task_repo_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有UserReward相关导入
        assert 'UserReward' not in content, "UserReward 仍然存在于 task/repository.py 中"

    def test_task_tree_structure_clean(self):
        """验证task树结构没有番茄钟字段"""
        test_file = Path("src/domains/task/tests/test_tree_structure.py")

        if not test_file.exists():
            pytest.skip("test_tree_structure.py文件不存在")

        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有番茄钟相关字段
        forbidden_fields = [
            'estimated_pomodoros',
            'actual_pomodoros',
            'pomodoro_count',
            '番茄钟'
        ]

        for field in forbidden_fields:
            assert field not in content, f"发现禁用字段: {field} 仍然存在于 test_tree_structure.py 中"

    def test_models_no_user_reward_class(self):
        """验证models.py中没有UserReward类定义"""
        models_path = Path("src/domains/user/models.py")

        if not models_path.exists():
            pytest.skip("user/models.py文件不存在，UserReward可能已被删除")

        with open(models_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有UserReward类定义
        assert 'class UserReward' not in content, "UserReward 类定义仍然存在于 user/models.py 中"

    def test_comprehensive_cleanup_verification(self):
        """综合验证：确保整个项目中没有残留的番茄钟和UserReward代码"""
        src_path = Path("src")

        # 需要检查的禁用模式
        forbidden_patterns = [
            'estimated_pomodoros',
            'actual_pomodoros',
            'UserReward'
        ]

        for pattern in forbidden_patterns:
            # 递归检查所有Python文件
            for py_file in src_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 跳过注释和文档字符串中的引用
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        # 跳过注释行
                        if line_stripped.startswith('#'):
                            continue
                        # 跳过文档字符串
                        if '"""' in line or "'''" in line:
                            continue

                        if pattern in line and not line_stripped.startswith('#'):
                            # 如果在非注释行发现模式，需要更详细的检查
                            if pattern == 'UserReward' and 'import' in line:
                                pytest.fail(f"发现 {pattern} 导入仍然存在于 {py_file}:{i+1}")
                            elif pattern == 'UserReward' and 'class' in line:
                                pytest.fail(f"发现 {pattern} 类定义仍然存在于 {py_file}:{i+1}")
                            elif pattern in ['estimated_pomodoros', 'actual_pomodoros']:
                                pytest.fail(f"发现 {pattern} 字段仍然存在于 {py_file}:{i+1}")

                except (UnicodeDecodeError, PermissionError):
                    # 跳过无法读取的文件
                    continue