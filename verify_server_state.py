#!/usr/bin/env python3
"""
启动服务器并验证用户接口状态的脚本

这个脚本会：
1. 启动API服务器
2. 等待服务器就绪
3. 检查OpenAPI文档
4. 验证用户接口的参数定义
"""

import os
import sys
import time
import json
import subprocess
import requests
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_server():
    """启动FastAPI服务器"""
    print("🚀 启动FastAPI服务器...")

    # 设置环境变量
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "test-key")
    env.setdefault("PYTHONPATH", str(project_root))

    # 启动服务器
    cmd = [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(project_root)
    )

    return process

def wait_for_server(max_wait=30):
    """等待服务器启动"""
    print("⏳ 等待服务器启动...")

    for i in range(max_wait):
        try:
            response = requests.get("http://127.0.0.1:8000/health", timeout=1)
            if response.status_code == 200:
                print("✅ 服务器已就绪")
                return True
        except requests.exceptions.RequestException:
            pass

        time.sleep(1)
        print(f"   等待中... ({i+1}/{max_wait})")

    print("❌ 服务器启动超时")
    return False

def test_openapi_schema():
    """测试OpenAPI schema"""
    print("🔍 测试OpenAPI schema...")

    try:
        response = requests.get("http://127.0.0.1:8000/openapi.json", timeout=10)
        response.raise_for_status()

        schema = response.json()

        # 检查用户相关的路径
        user_paths = {}
        for path, path_item in schema.get("paths", {}).items():
            if "user" in path:
                user_paths[path] = path_item

        print(f"📋 发现 {len(user_paths)} 个用户相关路径:")

        args_kwargs_found = False

        for path, path_item in user_paths.items():
            for method, operation in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                    print(f"  {method.upper()} {path}")

                    # 检查参数
                    params = operation.get("parameters", [])
                    print(f"    参数数量: {len(params)}")

                    for param in params:
                        param_name = param.get("name", "unknown")
                        param_in = param.get("in", "unknown")
                        required = param.get("required", False)
                        print(f"      - {param_name} (in: {param_in}, required: {required})")

                        if param_name in ["args", "kwargs"]:
                            print(f"    🚨 发现问题参数: {param_name}")
                            args_kwargs_found = True

                    # 检查请求体
                    request_body = operation.get("requestBody")
                    if request_body:
                        content = request_body.get("content", {})
                        for content_type, content_info in content.items():
                            schema = content_info.get("schema", {})
                            if "properties" in schema:
                                for prop_name, prop_info in schema["properties"].items():
                                    if prop_name in ["args", "kwargs"]:
                                        print(f"    🚨 请求体中发现问题参数: {prop_name}")
                                        args_kwargs_found = True

        if args_kwargs_found:
            print("❌ 发现了args/kwargs问题参数")
        else:
            print("✅ 未发现args/kwargs问题参数")

        return args_kwargs_found

    except Exception as e:
        print(f"❌ OpenAPI测试失败: {type(e).__name__}: {e}")
        return None

def test_docs_page():
    """测试Swagger UI文档页面"""
    print("🔍 测试Swagger UI文档页面...")

    try:
        response = requests.get("http://127.0.0.1:8000/docs", timeout=10)
        response.raise_for_status()

        if "swagger" in response.text.lower():
            print("✅ Swagger UI页面可访问")

            # 检查页面中是否包含用户接口
            if "/user/" in response.text:
                print("✅ 用户接口在文档中可见")
            else:
                print("❌ 用户接口在文档中不可见")
        else:
            print("❌ Swagger UI页面异常")

        return True

    except Exception as e:
        print(f"❌ 文档页面测试失败: {type(e).__name__}: {e}")
        return False

def test_user_api_directly():
    """直接测试用户API接口"""
    print("🔍 直接测试用户API接口...")

    try:
        # 测试获取用户信息（应该返回401因为需要认证）
        response = requests.get("http://127.0.0.1:8000/user/profile", timeout=10)

        print(f"GET /user/profile: {response.status_code}")

        if response.status_code == 401:
            print("✅ 接口正常返回401（需要认证）")

            # 检查响应格式
            data = response.json()
            if "code" in data and "message" in data and "data" in data:
                print("✅ 响应格式正确")
            else:
                print("❌ 响应格式异常")
                print(f"   响应内容: {data}")
        else:
            print(f"❌ 意外的状态码: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}...")

        return True

    except Exception as e:
        print(f"❌ 用户API测试失败: {type(e).__name__}: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始服务器状态验证...")
    print("=" * 60)

    server_process = None

    try:
        # 启动服务器
        server_process = start_server()

        # 等待服务器就绪
        if not wait_for_server():
            return False

        print("\n" + "-" * 40)

        # 测试1: OpenAPI schema
        print("\n📋 测试1: OpenAPI schema")
        args_kwargs_found = test_openapi_schema()

        print("\n" + "-" * 40)

        # 测试2: 文档页面
        print("\n📋 测试2: Swagger UI文档页面")
        test_docs_page()

        print("\n" + "-" * 40)

        # 测试3: 直接API测试
        print("\n📋 测试3: 直接API测试")
        test_user_api_directly()

        print("\n" + "=" * 60)

        if args_kwargs_found:
            print("❌ 验证结果: 用户接口问题依然存在")
        else:
            print("✅ 验证结果: 用户接口问题已修复")

        return not args_kwargs_found

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断测试")
        return False

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理服务器进程
        if server_process:
            print("\n🛑 关闭服务器...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("✅ 服务器已关闭")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)