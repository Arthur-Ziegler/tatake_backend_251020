"""Top3领域异常定义"""

from fastapi import status


class Top3Exception(Exception):
    """Top3基础异常"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class Top3AlreadyExistsException(Top3Exception):
    """Top3已存在"""
    def __init__(self, date: str):
        super().__init__(
            detail=f"{date}的Top3已设置，每天只能设置一次",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class Top3NotFoundException(Top3Exception):
    """Top3不存在"""
    def __init__(self, date: str):
        super().__init__(
            detail=f"{date}的Top3不存在",
            status_code=status.HTTP_404_NOT_FOUND
        )
