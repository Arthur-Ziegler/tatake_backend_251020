"""
API Schema模块

该模块包含所有API请求和响应的Pydantic模型定义。

目录结构:
- auth.py: 认证相关Schema
- tasks.py: 任务相关Schema (未来)
- focus.py: 专注相关Schema (未来)
- rewards.py: 奖励相关Schema (未来)
- chat.py: 对话相关Schema (未来)
- statistics.py: 统计相关Schema (未来)
- user.py: 用户相关Schema (未来)

Schema设计原则:
1. 严格的数据验证和类型检查
2. 清晰的字段描述和约束
3. 统一的响应格式
4. 完整的错误处理
5. 向后兼容的版本管理
"""

"""
API Schema模块

该模块包含所有API请求和响应的Pydantic模型定义。

目录结构:
- auth.py: 认证相关Schema
- tasks.py: 任务相关Schema (未来)
- focus.py: 专注相关Schema (未来)
- rewards.py: 奖励相关Schema (未来)
- chat.py: 对话相关Schema (未来)
- statistics.py: 统计相关Schema (未来)
- user.py: 用户相关Schema (未来)

Schema设计原则:
1. 严格的数据验证和类型检查
2. 清晰的字段描述和约束
3. 统一的响应格式
4. 完整的错误处理
5. 向后兼容的版本管理
"""

# 导入所有auth模块的类
from .auth import *

# 自动生成__all__列表，包含所有导出的类
import inspect
import api.schemas.auth as auth_module

# 获取auth模块中所有的公共类（排除私有类和模块级变量）
_public_classes = [
    name for name, obj in inspect.getmembers(auth_module)
    if inspect.isclass(obj) and not name.startswith('_')
]

# 设置__all__
__all__ = _public_classes