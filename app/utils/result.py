# -*- coding: utf-8 -*-
"""
统一响应结果封装 - 模仿Java风格

可直接返回给 FastAPI，自动序列化为 JSON。

使用示例:
    # 成功响应
    return Result.success(data=user)
    return Result.success(data=user, message="获取用户成功")
    
    # 失败响应
    return Result.error("系统异常")
    return Result.error(ResultCode.NOT_FOUND, "用户不存在")
    return Result.not_found("用户不存在")
    
    # 分页响应
    return Result.page(data=list_data, total=100, page=1, size=20)
    
    # 链式调用
    return Result.success().with_data(user).with_message("操作成功")
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from enum import Enum
from pydantic import BaseModel

T = TypeVar('T')


class ResultCode(Enum):
    """响应状态码枚举"""
    # 成功
    SUCCESS = ("0000", "操作成功")
    
    # 客户端错误 1xxx
    BAD_REQUEST = ("1000", "请求参数错误")
    UNAUTHORIZED = ("1001", "未授权")
    FORBIDDEN = ("1003", "禁止访问")
    NOT_FOUND = ("1004", "资源不存在")
    METHOD_NOT_ALLOWED = ("1005", "方法不允许")
    PARAM_VALID_ERROR = ("1006", "参数验证失败")
    
    # 业务错误 2xxx  
    BUSINESS_ERROR = ("2000", "业务处理失败")
    DATA_EXISTS = ("2001", "数据已存在")
    DATA_NOT_EXISTS = ("2002", "数据不存在")
    OPERATION_FAILED = ("2003", "操作失败")
    
    # 服务端错误 5xxx
    INTERNAL_ERROR = ("5000", "系统内部错误")
    SERVICE_UNAVAILABLE = ("5003", "服务不可用")
    GATEWAY_TIMEOUT = ("5004", "网关超时")
    
    # 第三方服务错误 6xxx
    THIRD_PARTY_ERROR = ("6000", "第三方服务异常")
    
    def __init__(self, code: str, message: str):
        self._code = code
        self._message = message
    
    @property
    def code(self) -> str:
        return self._code
    
    @property
    def message(self) -> str:
        return self._message


class Result(BaseModel, Generic[T]):
    """
    统一响应结果封装 - 可直接返回给 FastAPI
    
    Attributes:
        code: 状态码
        info: 提示信息
        data: 响应数据
    
    使用示例:
        # 直接返回，FastAPI 会自动序列化
        return Result.success(data=user)
        return Result.not_found("用户不存在")
    """
    code: str = ResultCode.SUCCESS.code
    info: str = ResultCode.SUCCESS.message
    data: Optional[T] = None
    
    model_config = {
        "populate_by_name": True,
        "by_alias": False
    }
    
    # ==================== 静态工厂方法 ====================
    
    @classmethod
    def success(cls, data: Optional[T] = None, message: str = None) -> "Result[T]":
        """
        成功响应
        
        Args:
            data: 响应数据
            message: 自定义消息（可选）
        
        Returns:
            Result实例
        """
        return cls(
            code=ResultCode.SUCCESS.code,
            info=message or ResultCode.SUCCESS.message,
            data=data
        )
    
    @classmethod
    def error(
        cls, 
        code: Union[ResultCode, str] = ResultCode.INTERNAL_ERROR,
        message: str = None
    ) -> "Result[T]":
        """
        错误响应
        
        Args:
            code: 错误码（可以是ResultCode枚举或字符串）
            message: 自定义错误消息
        
        Returns:
            Result实例
        """
        if isinstance(code, ResultCode):
            return cls(
                code=code.code,
                info=message or code.message
            )
        return cls(
            code=code,
            info=message or ResultCode.INTERNAL_ERROR.message
        )
    
    @classmethod
    def fail(
        cls,
        code: Union[ResultCode, str] = ResultCode.BUSINESS_ERROR,
        message: str = None
    ) -> "Result[T]":
        """
        业务失败响应（error的别名）
        
        Args:
            code: 错误码
            message: 错误消息
        
        Returns:
            Result实例
        """
        return cls.error(code, message)
    
    # ==================== 常用快捷方法 ====================
    
    @classmethod
    def bad_request(cls, message: str = None) -> "Result[T]":
        """请求参数错误"""
        return cls.error(ResultCode.BAD_REQUEST, message)
    
    @classmethod
    def unauthorized(cls, message: str = None) -> "Result[T]":
        """未授权"""
        return cls.error(ResultCode.UNAUTHORIZED, message)
    
    @classmethod
    def forbidden(cls, message: str = None) -> "Result[T]":
        """禁止访问"""
        return cls.error(ResultCode.FORBIDDEN, message)
    
    @classmethod
    def not_found(cls, message: str = None) -> "Result[T]":
        """资源不存在"""
        return cls.error(ResultCode.NOT_FOUND, message)
    
    @classmethod
    def param_error(cls, message: str = None) -> "Result[T]":
        """参数验证失败"""
        return cls.error(ResultCode.PARAM_VALID_ERROR, message)
    
    @classmethod
    def business_error(cls, message: str = None) -> "Result[T]":
        """业务处理失败"""
        return cls.error(ResultCode.BUSINESS_ERROR, message)
    
    @classmethod
    def internal_error(cls, message: str = None) -> "Result[T]":
        """系统内部错误"""
        return cls.error(ResultCode.INTERNAL_ERROR, message)
    
    # ==================== 分页响应 ====================
    
    @classmethod
    def page(
        cls,
        data: List[T] = None,
        total: int = 0,
        page: int = 1,
        size: int = 20,
        message: str = None
    ) -> "Result[Dict]":
        """
        分页响应
        
        Args:
            data: 数据列表
            total: 总数
            page: 当前页码
            size: 每页数量
            message: 提示消息
        
        Returns:
            Result实例，data包含分页信息
        """
        return cls.success(
            data={
                "list": data or [],
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size if size > 0 else 0
            },
            message=message
        )
    
    # ==================== 链式调用方法 ====================
    
    def with_data(self, data: T) -> "Result[T]":
        """设置数据（链式调用）"""
        self.data = data
        return self
    
    def with_message(self, message: str) -> "Result[T]":
        """设置消息（链式调用）"""
        self.info = message
        return self
    
    def with_code(self, code: Union[ResultCode, str]) -> "Result[T]":
        """设置状态码（链式调用）"""
        if isinstance(code, ResultCode):
            self.code = code.code
        else:
            self.code = code
        return self
    
    # ==================== 辅助方法 ====================
    
    def is_success(self) -> bool:
        """判断是否成功"""
        return self.code == ResultCode.SUCCESS.code
    
    def is_error(self) -> bool:
        """判断是否失败"""
        return self.code != ResultCode.SUCCESS.code


class PageResult(Result[List[T]]):
    """
    分页结果封装
    
    Attributes:
        code: 状态码
        info: 提示信息
        data: 数据列表
        total: 总数
        page: 当前页码
        size: 每页数量
    """
    total: int = 0
    page: int = 1
    size: int = 20
    
    @classmethod
    def of(
        cls,
        data: List[T] = None,
        total: int = 0,
        page: int = 1,
        size: int = 20,
        message: str = None
    ) -> "PageResult[T]":
        """
        创建分页结果
        
        Args:
            data: 数据列表
            total: 总数
            page: 当前页码
            size: 每页数量
            message: 提示消息
        
        Returns:
            PageResult实例
        """
        result = cls(
            code=ResultCode.SUCCESS.code,
            info=message or ResultCode.SUCCESS.message,
            data=data or []
        )
        result.total = total
        result.page = page
        result.size = size
        return result
    
    @property
    def pages(self) -> int:
        """总页数"""
        return (self.total + self.size - 1) // self.size if self.size > 0 else 0


__all__ = [
    "Result",
    "ResultCode",
    "PageResult"
]