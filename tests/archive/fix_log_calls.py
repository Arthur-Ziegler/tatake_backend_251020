#!/usr/bin/env python3
"""
修复_log_info调用的脚本
"""

import re

def fix_log_info_calls(file_path):
    """修复_log_info调用"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配_log_info调用模式
    pattern = r'self\._log_info\("([^"]+)", \s*\{\s*([^}]+)\s*\}\)'

    def replace(match):
        message = match.group(1)
        args_str = match.group(2).strip()

        # 转换参数格式
        args = []
        for line in args_str.split(','):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().strip('"\'')
                value = value.strip()
                args.append(f"{key}={value}")

        return f'self._log_info("{message}",\n                ' + ',\n                '.join(args) + '\n            )'

    content = re.sub(pattern, replace, content, flags=re.MULTILINE | re.DOTALL)

    # 修复多余的})模式
    content = re.sub(r'\)\s*\}\s*\)', ')', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix_log_info_calls('/Users/zalelee/Code/tatake_backend/src/services/auth_service.py')
    print("修复完成")