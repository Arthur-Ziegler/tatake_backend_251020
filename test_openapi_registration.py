#!/usr/bin/env python3
"""
测试OpenAPI模型注册功能
"""

import requests
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_openapi_registration():
    """测试OpenAPI模型注册"""
    try:
        # 获取OpenAPI文档
        response = requests.get("http://localhost:8000/openapi.json", timeout=10)
        response.raise_for_status()
        openapi_spec = response.json()
        
        # 检查组件中的模式
        components = openapi_spec.get("components", {})
        schemas = components.get("schemas", {})
        
        print(f"OpenAPI中注册的模式数量: {len(schemas)}")
        print("\n注册的模式名称:")
        for schema_name in sorted(schemas.keys()):
            print(f"  - {schema_name}")
        
        # 检查特定模型是否存在
        expected_models = [
            "AuthTokenResponse",
            "TaskResponse", 
            "ChatSessionResponse",
            "UserProfileResponse",
            "WeChatRegisterRequest",
            "CreateTaskRequest",
            "MessageResponse"
        ]
        
        print(f"\n关键模型检查:")
        all_found = True
        for model_name in expected_models:
            if model_name in schemas:
                print(f"✅ {model_name} 已注册")
            else:
                print(f"❌ {model_name} 未注册")
                all_found = False
        
        # 检查模式的详细内容
        if "AuthTokenResponse" in schemas:
            print(f"\nAuthTokenResponse模式详情:")
            auth_schema = schemas["AuthTokenResponse"]
            print(f"  类型: {auth_schema.get('type')}")
            print(f"  属性: {list(auth_schema.get('properties', {}).keys())}")
        
        return all_found
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到API服务器: {e}")
        print("请确保FastAPI应用正在运行 (python -m src.api.main)")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_swagger_ui():
    """测试Swagger UI可访问性"""
    try:
        # 测试Swagger UI
        response = requests.get("http://localhost:8000/docs", timeout=10)
        if response.status_code == 200:
            print("✅ Swagger UI (/docs) 可访问")
        else:
            print(f"❌ Swagger UI (/docs) 返回状态码: {response.status_code}")
        
        # 测试ReDoc
        response = requests.get("http://localhost:8000/redoc", timeout=10)
        if response.status_code == 200:
            print("✅ ReDoc (/redoc) 可访问")
        else:
            print(f"❌ ReDoc (/redoc) 返回状态码: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法测试UI界面: {e}")

def main():
    """主测试函数"""
    print("🧪 开始测试OpenAPI模型注册...")
    print("=" * 50)
    
    # 测试OpenAPI注册
    success = test_openapi_registration()
    
    print("\n" + "=" * 50)
    print("🌐 测试UI界面可访问性...")
    test_swagger_ui()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ OpenAPI模型注册测试通过！")
        return 0
    else:
        print("❌ OpenAPI模型注册测试失败！")
        return 1

if __name__ == "__main__":
    sys.exit(main())