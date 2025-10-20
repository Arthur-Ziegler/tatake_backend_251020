#!/usr/bin/env python3
"""
修复AuthService中的repository访问方式
"""

import re

def fix_auth_service_repos():
    """修复auth_service.py中的repository访问"""
    with open('/Users/zalelee/Code/tatake_backend/src/services/auth_service.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换所有self.get_user_repository()为self._user_repo
    content = re.sub(r'self\.get_user_repository\(\)', 'self._user_repo', content)

    # 替换所有self.get_task_repository()为self._task_repo
    content = re.sub(r'self\.get_task_repository\(\)', 'self._task_repo', content)

    # 替换所有self.get_focus_repository()为self._focus_repo
    content = re.sub(r'self\.get_focus_repository\(\)', 'self._focus_repo', content)

    # 替换所有self.get_reward_repository()为self._reward_repo
    content = re.sub(r'self\.get_reward_repository\(\)', 'self._reward_repo', content)

    # 替换所有self.get_chat_repository()为self._chat_repo
    content = re.sub(r'self\.get_chat_repository\(\)', 'self._chat_repo', content)

    with open('/Users/zalelee/Code/tatake_backend/src/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix_auth_service_repos()
    print("修复完成")