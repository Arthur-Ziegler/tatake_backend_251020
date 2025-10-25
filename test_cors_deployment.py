#!/usr/bin/env python3
"""
CORS 部署测试脚本

验证 API 是否可以被任何人从任何域名访问
"""

import requests
import json
from typing import Dict, Any

def test_cors_access(url: str, origin: str = None) -> Dict[str, Any]:
    """测试 CORS 访问"""
    headers = {}
    if origin:
        headers['Origin'] = origin

    try:
        # 测试健康检查
        response = requests.get(f"{url}/health", headers=headers, timeout=10)

        result = {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'cors_origin': response.headers.get('Access-Control-Allow-Origin', '未设置'),
            'cors_methods': response.headers.get('Access-Control-Allow-Methods', '未设置'),
            'cors_headers': response.headers.get('Access-Control-Allow-Headers', '未设置'),
            'error': None
        }

        # 如果响应是 JSON，解析内容
        try:
            result['response_data'] = response.json()
        except:
            result['response_data'] = response.text[:200] + '...' if len(response.text) > 200 else response.text

        return result

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': None,
            'cors_origin': None,
            'cors_methods': None,
            'cors_headers': None
        }

def test_cors_preflight(url: str, origin: str = None) -> Dict[str, Any]:
    """测试 CORS 预检请求"""
    headers = {
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Content-Type, Authorization'
    }
    if origin:
        headers['Origin'] = origin

    try:
        response = requests.options(f"{url}/health", headers=headers, timeout=10)

        return {
            'success': response.status_code in [200, 204],
            'status_code': response.status_code,
            'cors_origin': response.headers.get('Access-Control-Allow-Origin', '未设置'),
            'cors_methods': response.headers.get('Access-Control-Allow-Methods', '未设置'),
            'cors_headers': response.headers.get('Access-Control-Allow-Headers', '未设置'),
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': None,
            'cors_origin': None,
            'cors_methods': None,
            'cors_headers': None
        }

def main():
    """主测试函数"""
    import sys
    if len(sys.argv) < 2:
        print("用法: python test_cors_deployment.py <API_URL>")
        print("示例: python test_cors_deployment.py http://localhost:8001")
        print("示例: python test_cors_deployment.py https://your-server.com")
        return

    api_url = sys.argv[1].rstrip('/')

    print(f"🌐 测试 API CORS 配置: {api_url}")
    print("=" * 60)

    # 测试不同的 Origin
    test_origins = [
        "https://example.com",
        "https://www.google.com",
        "http://localhost:3000",
        "https://tatake.app",
        "https://subdomain.tatake.app"
    ]

    for origin in test_origins:
        print(f"\n🔍 测试 Origin: {origin}")
        print("-" * 40)

        # 测试预检请求
        print("  📡 预检请求 (OPTIONS):")
        preflight = test_cors_preflight(api_url, origin)
        print(f"     状态: {'✅ 成功' if preflight['success'] else '❌ 失败'}")
        print(f"     状态码: {preflight['status_code']}")
        print(f"     CORS-Origin: {preflight['cors_origin']}")
        print(f"     CORS-Methods: {preflight['cors_methods']}")
        if preflight['error']:
            print(f"     错误: {preflight['error']}")

        # 测试普通请求
        print("  📥 普通请求 (GET):")
        normal = test_cors_access(api_url, origin)
        print(f"     状态: {'✅ 成功' if normal['success'] else '❌ 失败'}")
        print(f"     状态码: {normal['status_code']}")
        print(f"     CORS-Origin: {normal['cors_origin']}")
        if normal['error']:
            print(f"     错误: {normal['error']}")

        # 验证 CORS 设置是否正确
        cors_ok = (
            normal['success'] and
            normal['cors_origin'] in [origin, '*'] and
            preflight['success']
        )
        print(f"  📊 CORS 配置: {'✅ 正确' if cors_ok else '❌ 需要修复'}")

    print("\n" + "=" * 60)
    print("🎯 验证指南:")
    print("✅ 所有测试成功 - CORS 配置正确，API 可以被任何人访问")
    print("❌ 有测试失败 - 需要检查 CORS 配置")
    print("🚀 关键检查点:")
    print("   - Access-Control-Allow-Origin 应该是 '*' 或具体的 Origin")
    print("   - OPTIONS 请求应该返回 200/204 状态码")
    print("   - 应该允许所有必要的 HTTP 方法和请求头")

if __name__ == "__main__":
    main()