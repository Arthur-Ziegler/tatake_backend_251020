"""
统一响应格式工具模块

基于v3 API方案的统一响应格式，支持：
- 标准成功响应格式
- 标准错误响应格式
- HTTP状态码映射
- 分页响应格式

设计原则：
1. 统一格式：所有API返回相同的响应结构
2. 类型安全：使用Pydantic确保响应格式正确
3. 错误处理：详细的错误信息和建议
4. 分页支持：标准化的分页响应结构

作者：TaTakeKe团队
版本：v1.0（Day3实施）
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import status


class ResponseCode:
    """响应状态码常量"""
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


def create_success_response(
    data: Any = None,
    message: str = "操作成功",
    code: int = ResponseCode.SUCCESS
) -> Dict[str, Any]:
    """
    创建成功响应

    Args:
        data: 响应数据
        message: 响应消息
        code: 响应状态码

    Returns:
        Dict[str, Any]: 标准响应格式
    """
    return {
        "code": code,
        "message": message,
        "data": data
    }


def create_error_response(
    message: str,
    code: int = ResponseCode.BAD_REQUEST,
    data: Any = None,
    detail: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建错误响应

    Args:
        message: 错误消息
        code: 错误状态码
        data: 错误数据
        detail: 详细错误信息

    Returns:
        Dict[str, Any]: 标准错误响应格式
    """
    return {
        "code": code,
        "message": message,
        "data": data or {}
    }


def create_pagination_response(
    items: list,
    current_page: int,
    total_pages: int,
    total_count: int,
    page_size: int = 20,
    message: str = "获取成功"
) -> Dict[str, Any]:
    """
    创建分页响应（严格按照v3文档格式）

    Args:
        items: 数据列表
        current_page: 当前页码
        total_pages: 总页数
        total_count: 总记录数
        page_size: 每页大小
        message: 响应消息

    Returns:
        Dict[str, Any]: 分页响应格式
    """
    return {
        "code": ResponseCode.SUCCESS,
        "message": message,
        "data": {
            "items": items,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "total_count": total_count
            }
        }
    }


def json_response(
    data: Any = None,
    message: str = "操作成功",
    code: int = ResponseCode.SUCCESS,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    创建JSON响应

    Args:
        data: 响应数据
        message: 响应消息
        code: 响应状态码
        status_code: HTTP状态码

    Returns:
        JSONResponse: FastAPI JSON响应
    """
    content = create_success_response(data=data, message=message, code=code)
    return JSONResponse(content=content, status_code=status_code)


def error_json_response(
    message: str,
    code: int = ResponseCode.BAD_REQUEST,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    data: Any = None
) -> JSONResponse:
    """
    创建错误JSON响应

    Args:
        message: 错误消息
        code: 错误状态码
        status_code: HTTP状态码
        data: 错误数据

    Returns:
        JSONResponse: FastAPI错误响应
    """
    content = create_error_response(message=message, code=code, data=data)
    return JSONResponse(content=content, status_code=status_code)


class StandardResponse:
    """标准响应类，提供静态方法创建响应"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        status_code: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """成功响应"""
        return json_response(
            data=data,
            message=message,
            code=ResponseCode.SUCCESS,
            status_code=status_code
        )

    @staticmethod
    def created(
        data: Any = None,
        message: str = "创建成功"
    ) -> JSONResponse:
        """创建成功响应"""
        return json_response(
            data=data,
            message=message,
            code=ResponseCode.CREATED,
            status_code=status.HTTP_201_CREATED
        )

    @staticmethod
    def bad_request(
        message: str = "请求参数错误",
        data: Any = None
    ) -> JSONResponse:
        """请求错误响应"""
        return error_json_response(
            message=message,
            code=ResponseCode.BAD_REQUEST,
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data
        )

    @staticmethod
    def unauthorized(
        message: str = "未授权访问"
    ) -> JSONResponse:
        """未授权响应"""
        return error_json_response(
            message=message,
            code=ResponseCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    @staticmethod
    def payment_required(
        message: str = "积分不足"
    ) -> JSONResponse:
        """积分不足响应"""
        return error_json_response(
            message=message,
            code=ResponseCode.PAYMENT_REQUIRED,
            status_code=status.HTTP_402_PAYMENT_REQUIRED
        )

    @staticmethod
    def forbidden(
        message: str = "禁止操作"
    ) -> JSONResponse:
        """禁止操作响应"""
        return error_json_response(
            message=message,
            code=ResponseCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN
        )

    @staticmethod
    def not_found(
        message: str = "资源不存在"
    ) -> JSONResponse:
        """资源不存在响应"""
        return error_json_response(
            message=message,
            code=ResponseCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND
        )

    @staticmethod
    def server_error(
        message: str = "服务器内部错误"
    ) -> JSONResponse:
        """服务器错误响应"""
        return error_json_response(
            message=message,
            code=ResponseCode.INTERNAL_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @staticmethod
    def paginated(
        items: list,
        current_page: int,
        total_pages: int,
        total_count: int,
        page_size: int = 20,
        message: str = "获取成功"
    ) -> JSONResponse:
        """分页响应"""
        content = create_pagination_response(
            items=items,
            current_page=current_page,
            total_pages=total_pages,
            total_count=total_count,
            page_size=page_size,
            message=message
        )
        return JSONResponse(content=content, status_code=status.HTTP_200_OK)


# 常用响应实例
response = StandardResponse()


def http_exception_handler(exc: HTTPException) -> JSONResponse:
    """
    HTTP异常处理器

    Args:
        exc: HTTPException

    Returns:
        JSONResponse: 标准错误响应
    """
    # 根据HTTP状态码映射到业务状态码
    status_code_mapping = {
        status.HTTP_400_BAD_REQUEST: ResponseCode.BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED: ResponseCode.UNAUTHORIZED,
        status.HTTP_402_PAYMENT_REQUIRED: ResponseCode.PAYMENT_REQUIRED,
        status.HTTP_403_FORBIDDEN: ResponseCode.FORBIDDEN,
        status.HTTP_404_NOT_FOUND: ResponseCode.NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR: ResponseCode.INTERNAL_ERROR,
    }

    response_code = status_code_mapping.get(exc.status_code, ResponseCode.INTERNAL_ERROR)

    return error_json_response(
        message=exc.detail or "请求失败",
        code=response_code,
        status_code=exc.status_code
    )


def validate_response_data(data: Any) -> bool:
    """
    验证响应数据格式

    Args:
        data: 响应数据

    Returns:
        bool: 数据格式是否有效
    """
    try:
        if data is None:
            return True

        if isinstance(data, (dict, list, str, int, float, bool)):
            return True

        # 如果是复杂对象，检查是否可以序列化
        import json
        json.dumps(data)
        return True

    except (TypeError, ValueError):
        return False