# Streamlit 模块导入问题修复指南

## 问题描述

当你运行 `uv run streamlit run streamlit_app/main.py` 时，遇到以下错误：

```
ModuleNotFoundError: No module named 'streamlit_app'
```

## 根本原因

这是一个经典的 Python 包导入问题。Python 需要识别 `streamlit_app` 作为一个包，但该目录缺少必要的 `__init__.py` 文件。

## 解决方案

### 1. 创建包初始化文件

在 `streamlit_app` 目录中创建 `__init__.py`：

```python
# streamlit_app/__init__.py
"""
Streamlit 测试面板包初始化文件
"""

__version__ = "1.0.0"
__author__ = "Claude Code Assistant"

from .config import api_client
from .state_manager import init_state, is_authenticated

__all__ = [
    "api_client",
    "init_state",
    "is_authenticated"
]
```

在 `streamlit_app/components` 目录中也创建 `__init__.py`：

```python
# streamlit_app/components/__init__.py
"""
Streamlit 测试面板组件包初始化文件
"""

from .json_viewer import render_json, render_api_response
from .error_handler import show_error, handle_api_response

__all__ = [
    "render_json",
    "render_api_response",
    "show_error",
    "handle_api_response"
]
```

### 2. 正确的启动方式

使用以下命令启动 Streamlit：

```bash
# 方法1: 设置 PYTHONPATH
PYTHONPATH=. uv run streamlit run streamlit_app/main.py

# 方法2: 使用启动脚本
./run_streamlit.sh 8503
```

### 3. 创建启动脚本

创建 `run_streamlit.sh` 文件：

```bash
#!/bin/bash
PORT=${1:-8503}
export PYTHONPATH=.
uv run streamlit run streamlit_app/main.py --server.port $PORT
```

然后添加执行权限：
```bash
chmod +x run_streamlit.sh
```

## 文件结构

修复后的目录结构应该是：

```
streamlit_app/
├── __init__.py          # ← 新增：包初始化文件
├── main.py
├── config.py
├── api_client.py
├── state_manager.py
├── components/
│   ├── __init__.py      # ← 新增：组件包初始化文件
│   ├── json_viewer.py
│   └── error_handler.py
└── pages/
    ├── 1_🏠_认证.py
    ├── 2_📋_任务管理.py
    ├── 4_🍅_番茄钟.py
    └── 7_⭐_Top3管理.py
```

## 验证修复

运行以下命令验证模块导入是否正常：

```bash
uv run python -c "import streamlit_app; print('✅ streamlit_app 模块导入成功!')"
```

## 常见问题

### Q: 为什么需要 __init__.py 文件？
A: Python 使用 `__init__.py` 文件来识别目录作为一个包（package）。没有这个文件，Python 不知道这个目录是一个可以被导入的模块。

### Q: PYTHONPATH 是做什么的？
A: PYTHONPATH 环境变量告诉 Python 在哪些目录中查找模块。设置 `PYTHONPATH=.` 让 Python 在当前目录中查找模块。

### Q: 为什么直接运行会有问题？
A: Streamlit 在运行页面时，会从不同的工作目录执行页面文件，如果 PYTHONPATH 不正确，就无法找到 `streamlit_app` 模块。

## 预防措施

1. **始终创建包初始化文件**：任何包含 Python 代码的目录都应该有 `__init__.py`
2. **使用相对导入**：在包内部使用 `from .module import function`
3. **设置正确的 PYTHONPATH**：确保 Python 能找到你的项目根目录
4. **使用启动脚本**：避免每次都手动设置环境变量

## 其他解决方案

如果你仍然遇到问题，可以尝试：

1. **使用 pip 安装本地包**：
   ```bash
   pip install -e .
   ```

2. **修改 sys.path**（不推荐）：
   ```python
   import sys
   sys.path.append('/path/to/project')
   ```

3. **使用 Docker**：确保运行环境一致

---

**记住**: Python 包导入问题是开发中常见的问题，正确理解包结构和导入机制是关键！