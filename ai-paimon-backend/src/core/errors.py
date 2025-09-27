"""
错误定义和处理模块
统一的错误码和异常处理
"""

import uuid
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """统一错误码"""

    # 客户端错误 4xx
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT = "RATE_LIMIT"

    # 服务端错误 5xx
    INTERNAL = "INTERNAL"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"

    # 业务错误
    ASR_ERROR = "ASR_ERROR"
    TTS_ERROR = "TTS_ERROR"
    DIALOG_ERROR = "DIALOG_ERROR"
    KB_ERROR = "KB_ERROR"
    VISEME_ERROR = "VISEME_ERROR"


class ErrorResponse(BaseModel):
    """统一错误响应格式"""
    ok: bool = False
    code: ErrorCode
    msg: str
    trace_id: str
    details: Optional[Dict[str, Any]] = None


class PaimonException(Exception):
    """基础业务异常类"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.details = details
        self.trace_id = trace_id or str(uuid.uuid4())
        super().__init__(self.message)

    def to_response(self) -> ErrorResponse:
        """转换为标准错误响应"""
        return ErrorResponse(
            code=self.code,
            msg=self.message,
            trace_id=self.trace_id,
            details=self.details
        )


class ValidationException(PaimonException):
    """数据验证异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details
        )


class ServiceException(PaimonException):
    """服务异常"""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        code_map = {
            "asr": ErrorCode.ASR_ERROR,
            "tts": ErrorCode.TTS_ERROR,
            "dialog": ErrorCode.DIALOG_ERROR,
            "kb": ErrorCode.KB_ERROR,
            "viseme": ErrorCode.VISEME_ERROR,
        }
        code = code_map.get(service, ErrorCode.INTERNAL)

        super().__init__(
            code=code,
            message=f"{service.upper()} service error: {message}",
            details=details
        )


class RateLimitException(PaimonException):
    """频率限制异常"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            code=ErrorCode.RATE_LIMIT,
            message=message
        )


def create_http_exception(error: PaimonException) -> HTTPException:
    """将业务异常转换为HTTP异常"""
    status_code_map = {
        ErrorCode.BAD_REQUEST: 400,
        ErrorCode.UNAUTHORIZED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.VALIDATION_ERROR: 422,
        ErrorCode.RATE_LIMIT: 429,
        ErrorCode.INTERNAL: 500,
        ErrorCode.SERVICE_UNAVAILABLE: 503,
        ErrorCode.TIMEOUT: 504,
        # 业务错误默认为500
        ErrorCode.ASR_ERROR: 500,
        ErrorCode.TTS_ERROR: 500,
        ErrorCode.DIALOG_ERROR: 500,
        ErrorCode.KB_ERROR: 500,
        ErrorCode.VISEME_ERROR: 500,
    }

    status_code = status_code_map.get(error.code, 500)
    return HTTPException(
        status_code=status_code,
        detail=error.to_response().model_dump()
    )