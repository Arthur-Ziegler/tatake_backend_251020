#!/usr/bin/env python3
"""
修复OpenAPI模型注册功能的脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_improved_openapi_function():
    """创建改进的ensure_openapi_schemas函数"""
    
    new_function_code = '''
def ensure_openapi_schemas():
    """确保所有Pydantic模型都注册到OpenAPI components - 改进版本"""
    from fastapi.openapi.utils import get_openapi
    
    # 获取或生成OpenAPI模式
    if not app.openapi_schema:
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    
    # 确保components/schemas存在
    if "components" not in app.openapi_schema:
        app.openapi_schema["components"] = {}
    if "schemas" not in app.openapi_schema["components"]:
        app.openapi_schema["components"]["schemas"] = {}
    
    # 导入所有模型
    from src.domains.auth.schemas import (
        WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
        GuestUpgradeRequest, AuthTokenResponse
    )
    from src.domains.task.schemas import (
        CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
        UncompleteTaskRequest, TaskResponse, TaskListQuery
    )
    from src.domains.chat.schemas import (
        CreateSessionRequest, SendMessageRequest, ChatSessionResponse,
        MessageResponse, ChatHistoryResponse
    )
    from src.domains.focus.schemas import (
        StartFocusRequest, FocusSessionResponse, FocusOperationResponse
    )
    from src.domains.reward.schemas import (
        RewardRedeemRequest, RecipeMaterial, RecipeReward,
        RedeemRecipeResponse, UserMaterial
    )
    from src.domains.top3.schemas import (
        SetTop3Request, Top3Response, GetTop3Response
    )
    from src.domains.user.schemas import (
        UpdateProfileRequest, FeedbackRequest, UserProfileResponse
    )

    # 定义要注册的模型列表
    models = [
        WeChatRegisterRequest, WeChatLoginRequest, TokenRefreshRequest,
        GuestUpgradeRequest, AuthTokenResponse,
        CreateTaskRequest, UpdateTaskRequest, CompleteTaskRequest,
        UncompleteTaskRequest, TaskResponse, TaskListQuery,
        CreateSessionRequest, SendMessageRequest, ChatSessionResponse,
        MessageResponse, ChatHistoryResponse,
        StartFocusRequest, FocusSessionResponse, FocusOperationResponse,
        RewardRedeemRequest, RecipeMaterial, RecipeReward,
        RedeemRecipeResponse, UserMaterial,
        SetTop3Request, Top3Response, GetTop3Response,
        UpdateProfileRequest, FeedbackRequest, UserProfileResponse
    ]

    # 注册每个模型到OpenAPI组件
    registered_count = 0
    for model in models:
        try:
            # 使用Pydantic生成JSON模式
            if hasattr(model, 'model_json_schema'):
                # Pydantic v2
                schema_dict = model.model_json_schema()
            else:
                # Pydantic v1
                schema_dict = model.schema()
            
            # 添加到OpenAPI组件中
            app.openapi_schema["components"]["schemas"][model.__name__] = schema_dict
            registered_count += 1
            
        except Exception as e:
            print(f"⚠️ 模型 {model.__name__} 注册失败: {e}")
    
    print(f"✅ OpenAPI组件注册完成，共注册了 {registered_count} 个模型")
'''
    
    return new_function_code

def backup_original_file(file_path):
    """备份原始文件"""
    backup_path = f"{file_path}.backup"
    import shutil
    shutil.copy2(file_path, backup_path)
    print(f"📋 已备份原始文件到: {backup_path}")
    return backup_path

def update_main_py():
    """更新main.py文件中的ensure_openapi_schemas函数"""
    
    main_py_path = project_root / "src" / "api" / "main.py"
    
    if not main_py_path.exists():
        print(f"❌ 文件不存在: {main_py_path}")
        return False
    
    # 备份原始文件
    backup_path = backup_original_file(main_py_path)
    
    try:
        # 读取原始文件内容
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到ensure_openapi_schemas函数的开始和结束位置
        func_start = content.find('def ensure_openapi_schemas():')
        if func_start == -1:
            print("❌ 找不到ensure_openapi_schemas函数")
            return False
        
        # 找到函数的结束位置（通过查找下一个顶级函数定义或文件结束）
        func_end = len(content)
        next_func_pos = content.find('\ndef ', func_start + 1)
        if next_func_pos != -1:
            func_end = next_func_pos
        
        # 提取函数前的缩进
        lines = content[:func_start].split('\n')
        if lines:
            last_line = lines[-1]
            indent = len(last_line) - len(last_line.lstrip())
        else:
            indent = 0
        
        # 创建新的函数代码，保持原有缩进
        new_function_code = create_improved_openapi_function()
        
        # 调整新函数的缩进
        indented_new_function = ''
        for line in new_function_code.strip().split('\n'):
            if line.strip():
                indented_new_function += ' ' * indent + line + '\n'
            else:
                indented_new_function += '\n'
        
        # 替换函数内容
        new_content = content[:func_start] + indented_new_function + content[func_end:]
        
        # 写入新内容
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ 已成功更新ensure_openapi_schemas函数")
        print("📝 主要改进:")
        print("  - 使用fastapi.openapi.utils.get_openapi生成完整的OpenAPI模式")
        print("  - 直接修改app.openapi_schema['components']['schemas']")
        print("  - 正确处理Pydantic v1和v2的兼容性")
        print("  - 添加了详细的错误处理和注册统计")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新文件失败: {e}")
        print(f"🔄 正在从备份恢复...")
        
        # 从备份恢复
        import shutil
        shutil.copy2(backup_path, main_py_path)
        print("✅ 已从备份恢复原始文件")
        
        return False

def main():
    """主函数"""
    print("🔧 FastAPI OpenAPI模型注册修复工具")
    print("=" * 50)
    
    # 检查是否正在运行FastAPI应用
    print("🔍 检查应用状态...")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("⚠️  FastAPI应用正在运行，建议先停止应用再进行修改")
            print("   运行: pkill -f 'python -m src.api.main' 或按 Ctrl+C")
            response = input("是否继续? (y/N): ")
            if response.lower() != 'y':
                return 1
    except:
        print("✅ FastAPI应用未运行，可以安全修改")
    
    print("\n🚀 开始修复OpenAPI模型注册...")
    
    # 更新main.py文件
    success = update_main_py()
    
    if success:
        print("\n✅ 修复完成！")
        print("\n下一步:")
        print("1. 启动FastAPI应用: python -m src.api.main")
        print("2. 运行测试脚本: python test_openapi_registration.py")
        print("3. 访问Swagger UI: http://localhost:8000/docs")
        print("4. 检查模型是否正确显示在Schemas部分")
        return 0
    else:
        print("\n❌ 修复失败！")
        return 1

if __name__ == "__main__":
    sys.exit(main())