"""
统一API响应格式

只返回code、message、data三个字段，简化响应格式。
"""

from typing import Any, Dict, Optional
from fastapi import status
from fastapi.responses import JSONResponse


def create_success_response(
    data: Any = None,
    message: str = "success",
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """创建成功响应 - 只返回code、message、data三个字段"""
    response_data = {
        "code": status_code,
        "message": message,
        "data": data
    }
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def create_error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """创建错误响应 - 只返回code、message、data三个字段"""
    response_data = {
        "code": status_code,
        "message": message,
        "data": None
    }
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def create_not_found_response(
    message: str = "资源未找到"
) -> JSONResponse:
    """创建未找到响应 - 只返回code、message、data三个字段"""
    response_data = {
        "code": status.HTTP_404_NOT_FOUND,
        "message": message,
        "data": None
    }
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_404_NOT_FOUND
    )


def create_unauthorized_response(
    message: str = "未授权访问"
) -> JSONResponse:
    """创建未授权响应 - 只返回code、message、data三个字段"""
    response_data = {
        "code": status.HTTP_401_UNAUTHORIZED,
        "message": message,
        "data": None
    }
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_401_UNAUTHORIZED
    )


def create_forbidden_response(
    message: str = "禁止访问"
) -> JSONResponse:
    """创建禁止访问响应 - 只返回code、message、data三个字段"""
    response_data = {
        "code": status.HTTP_403_FORBIDDEN,
        "message": message,
        "data": None
    }
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_403_FORBIDDEN
    )