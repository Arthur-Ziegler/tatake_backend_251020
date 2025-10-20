#!/usr/bin/env python3
"""
修复AuthService中的_log_info调用
"""

import re

def fix_log_info_calls():
    """修复auth_service.py中的_log_info调用"""
    with open('/Users/zalelee/Code/tatake_backend/src/services/auth_service.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配模式：self._log_info("message", { ... })
    pattern = r'self\._log_info\("([^"]+)", \s*\{\s*([^}]+)\s*\}\)'

    def replace_match(match):
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

    # 应用替换
    content = re.sub(pattern, replace_match, content, flags=re.MULTILINE | re.DOTALL)

    with open('/Users/zalelee/Code/tatake_backend/src/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix_log_info_calls()
    print("修复完成")